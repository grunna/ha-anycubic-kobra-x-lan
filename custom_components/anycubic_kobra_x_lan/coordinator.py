from __future__ import annotations

import json
import socket
import ssl
import struct
import time
import uuid
from datetime import timedelta
from typing import Any
from urllib.parse import urlparse

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, QUERY_TYPES


class AnycubicKobraXLanCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            logger=None,
            name=DOMAIN,
            update_interval=timedelta(seconds=30),
        )
        self.entry = entry
        self.credentials: dict[str, Any] = entry.data["credentials"]

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.hass.async_add_executor_job(self._query_all)
        except Exception as err:
            raise UpdateFailed(str(err)) from err

    def _query_all(self) -> dict[str, Any]:
        mqtt = _RawMqttClient(self.credentials)
        return mqtt.query_all()


class _RawMqttClient:
    def __init__(self, credentials: dict[str, Any]) -> None:
        self.credentials = credentials

        parsed = urlparse(credentials["broker"])
        self.host = parsed.hostname or credentials["ip"]
        self.port = parsed.port or 9883

        self.username = credentials["username"]
        self.password = credentials["password"]
        self.device_id = credentials["deviceId"]
        self.mode_id = str(credentials.get("modeId") or credentials.get("modelId"))

    def query_all(self) -> dict[str, Any]:
        subscribe_topic = f"anycubic/anycubicCloud/v1/printer/+/{self.mode_id}/{self.device_id}/#"
        client_id = f"ha_readonly_{self.device_id[-8:]}"

        data: dict[str, Any] = {}

        context = ssl._create_unverified_context()

        with socket.create_connection((self.host, self.port), timeout=10) as raw:
            with context.wrap_socket(raw, server_hostname=self.host) as sock:
                sock.sendall(_connect_packet(client_id, self.username, self.password))
                packet_type, body = _read_packet(sock)

                if packet_type != 0x20 or len(body) < 2 or body[1] != 0:
                    raise RuntimeError(f"MQTT connection rejected: {body.hex()}")

                sock.sendall(_subscribe_packet(subscribe_topic))
                packet_type, body = _read_packet(sock)

                if packet_type != 0x90:
                    raise RuntimeError(f"MQTT subscribe failed: packet={packet_type!r}, body={body.hex()}")

                expected = set(QUERY_TYPES)

                for query_type in QUERY_TYPES:
                    publish_topic = f"anycubic/anycubicCloud/v1/web/printer/{self.mode_id}/{self.device_id}/{query_type}"
                    sock.sendall(_publish_packet(publish_topic, _build_query_payload(query_type)))

                sock.settimeout(8)

                end_time = time.monotonic() + 8

                while time.monotonic() < end_time and expected:
                    try:
                        packet_type, body = _read_packet(sock)
                    except TimeoutError:
                        break

                    if packet_type is None:
                        break

                    if (packet_type & 0xF0) != 0x30:
                        continue

                    topic, payload = _decode_publish(body)

                    if not isinstance(payload, dict):
                        continue

                    report_type = payload.get("type")

                    if not report_type:
                        report_type = _type_from_topic(topic)

                    if report_type in expected:
                        data[report_type] = payload
                        expected.remove(report_type)

        return data


def _enc_str(value: bytes) -> bytes:
    return struct.pack("!H", len(value)) + value


def _enc_remaining_length(length: int) -> bytes:
    out = bytearray()

    while True:
        digit = length % 128
        length //= 128

        if length:
            digit |= 0x80

        out.append(digit)

        if not length:
            return bytes(out)


def _packet(packet_type: int, body: bytes) -> bytes:
    return bytes([packet_type]) + _enc_remaining_length(len(body)) + body


def _read_exact(sock, length: int) -> bytes:
    body = b""

    while len(body) < length:
        chunk = sock.recv(length - len(body))

        if not chunk:
            raise ConnectionError("Socket closed while reading packet")

        body += chunk

    return body


def _read_remaining_length(sock) -> int:
    multiplier = 1
    value = 0

    while True:
        b = _read_exact(sock, 1)[0]
        value += (b & 127) * multiplier

        if (b & 128) == 0:
            return value

        multiplier *= 128

        if multiplier > 128 * 128 * 128:
            raise ValueError("Malformed MQTT remaining length")


def _read_packet(sock):
    first = sock.recv(1)

    if not first:
        return None, None

    packet_type = first[0]
    remaining = _read_remaining_length(sock)
    body = _read_exact(sock, remaining)

    return packet_type, body


def _connect_packet(client_id: str, username: str, password: str) -> bytes:
    body = (
        _enc_str(b"MQTT")
        + bytes([4, 0xC2])
        + struct.pack("!H", 60)
        + _enc_str(client_id.encode("utf-8"))
        + _enc_str(username.encode("utf-8"))
        + _enc_str(password.encode("utf-8"))
    )

    return _packet(0x10, body)


def _subscribe_packet(topic: str, packet_id: int = 1) -> bytes:
    body = (
        struct.pack("!H", packet_id)
        + _enc_str(topic.encode("utf-8"))
        + bytes([0])
    )

    return _packet(0x82, body)


def _publish_packet(topic: str, payload: dict[str, Any]) -> bytes:
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    body = _enc_str(topic.encode("utf-8")) + payload_bytes

    return _packet(0x30, body)


def _build_query_payload(query_type: str) -> dict[str, Any]:
    return {
        "type": query_type,
        "action": "getInfo" if query_type == "multiColorBox" else "query",
        "timestamp": int(time.time() * 1000),
        "msgid": str(uuid.uuid4()),
        "data": None,
    }


def _decode_publish(body: bytes):
    topic_len = struct.unpack("!H", body[:2])[0]
    topic = body[2 : 2 + topic_len].decode("utf-8", errors="replace")
    payload = body[2 + topic_len :]

    try:
        payload_text = payload.decode("utf-8")
        payload_value = json.loads(payload_text)
    except Exception:
        payload_value = payload.decode("utf-8", errors="replace")

    return topic, payload_value


def _type_from_topic(topic: str) -> str | None:
    parts = topic.split("/")

    if len(parts) >= 2 and parts[-1] == "report":
        return parts[-2]

    return None
