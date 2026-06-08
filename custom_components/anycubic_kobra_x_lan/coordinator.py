from __future__ import annotations

import json
import logging
import socket
import ssl
import struct
import threading
import time
import uuid
from datetime import timedelta
from typing import Any
from urllib.parse import urlparse

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_POLLING_INTERVAL, DEFAULT_POLLING_INTERVAL, DOMAIN, QUERY_TYPES

_LOGGER = logging.getLogger(__name__)


class AnycubicKobraXLanCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        polling_interval = entry.options.get(
            CONF_POLLING_INTERVAL,
            DEFAULT_POLLING_INTERVAL,
        )

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=polling_interval),
        )
        self.entry = entry
        self.credentials: dict[str, Any] = entry.data["credentials"]
        self._mqtt = _PersistentRawMqttClient(
            self.credentials,
            self._handle_report_from_thread,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.hass.async_add_executor_job(self._mqtt.query_all_and_wait)
        except Exception as err:
            raise UpdateFailed(str(err)) from err

    async def async_shutdown(self) -> None:
        await self.hass.async_add_executor_job(self._mqtt.stop)

    async def async_reconnect(self) -> None:
        await self.hass.async_add_executor_job(self._mqtt.reconnect)
        await self.async_request_refresh()

    async def async_set_light(
        self,
        light_type: int,
        status: int,
        brightness: int,
    ) -> None:
        await self.hass.async_add_executor_job(
            self._mqtt.set_light,
            light_type,
            status,
            brightness,
        )

    async def async_set_camera_stream(self, enabled: bool) -> None:
        action = "startCapture" if enabled else "stopCapture"

        await self.hass.async_add_executor_job(
            self._mqtt.set_camera_stream,
            action,
        )

        new_data = dict(self.data or {})
        camera_stream = dict(new_data.get("camera_stream") or {})
        camera_stream["enabled"] = enabled
        camera_stream["last_action"] = action
        camera_stream["optimistic"] = True
        new_data["camera_stream"] = camera_stream
        self.async_set_updated_data(new_data)

    async def async_set_target_temperature(
        self,
        setting_key: str,
        temperature: int,
    ) -> None:
        task_id = _task_id(self.data or {})
        settings = {
            setting_key: int(temperature),
        }

        await self.hass.async_add_executor_job(
            self._mqtt.set_print_settings,
            task_id,
            settings,
        )

        new_data = dict(self.data or {})
        tempature = dict(new_data.get("tempature") or {})
        temp_data = tempature.get("data")

        if isinstance(temp_data, dict):
            temp_data = dict(temp_data)
            temp_data[setting_key] = int(temperature)
            tempature["data"] = temp_data
        else:
            tempature[setting_key] = int(temperature)

        new_data["tempature"] = tempature
        self.async_set_updated_data(new_data)

    def _handle_report_from_thread(self, report_type: str, payload: dict[str, Any]) -> None:
        self.hass.loop.call_soon_threadsafe(
            self._handle_report_on_loop,
            report_type,
            payload,
        )

    def _handle_report_on_loop(self, report_type: str, payload: dict[str, Any]) -> None:
        new_data = dict(self.data or {})
        new_data[report_type] = payload

        if report_type == "video":
            self._update_camera_stream_state(new_data, payload)

        self.async_set_updated_data(new_data)

    def _update_camera_stream_state(
        self,
        data: dict[str, Any],
        payload: dict[str, Any],
    ) -> None:
        state = payload.get("state")
        action = payload.get("action")
        code = payload.get("code")

        camera_stream = dict(data.get("camera_stream") or {})
        camera_stream["last_action"] = action
        camera_stream["last_state"] = state
        camera_stream["last_code"] = code
        camera_stream["optimistic"] = False

        if state == "initSuccess":
            camera_stream["enabled"] = True
        elif state in ("pushStopped", "pushFailed", "initFailed"):
            camera_stream["enabled"] = False

        response_data = payload.get("data")

        if isinstance(response_data, dict):
            urls = response_data.get("urls")

            if isinstance(urls, dict):
                stream_url = urls.get("rtspUrl")

                if isinstance(stream_url, str) and stream_url:
                    camera_stream["stream_url_available"] = True

        data["camera_stream"] = camera_stream


class _PersistentRawMqttClient:
    def __init__(
        self,
        credentials: dict[str, Any],
        on_report,
    ) -> None:
        self.credentials = credentials
        self.on_report = on_report

        parsed = urlparse(credentials["broker"])
        self.host = parsed.hostname or credentials["ip"]
        self.port = parsed.port or 9883

        self.username = credentials["username"]
        self.password = credentials["password"]
        self.device_id = credentials["deviceId"]
        self.mode_id = str(credentials.get("modeId") or credentials.get("modelId"))

        self.subscribe_topic = f"anycubic/anycubicCloud/v1/printer/+/{self.mode_id}/{self.device_id}/#"
        self.client_id = f"ha_anycubic_{self.device_id[-8:]}"

        self._lock = threading.RLock()
        self._latest_lock = threading.RLock()
        self._latest: dict[str, Any] = {}

        self._sock = None
        self._stop_event = threading.Event()
        self._reader_thread: threading.Thread | None = None

    def start(self) -> None:
        with self._lock:
            if self._reader_thread and self._reader_thread.is_alive():
                return

            self._stop_event.clear()
            self._reader_thread = threading.Thread(
                target=self._reader_loop,
                name="anycubic-kobra-x-lan-mqtt",
                daemon=True,
            )
            self._reader_thread.start()

    def stop(self) -> None:
        self._stop_event.set()

        with self._lock:
            self._close_locked()

        if self._reader_thread and self._reader_thread.is_alive():
            self._reader_thread.join(timeout=5)

    def reconnect(self) -> None:
        with self._lock:
            self._close_locked()
            self._ensure_connected_locked()

    def query_all_and_wait(self) -> dict[str, Any]:
        self.start()
        self._ensure_connected()

        expected = set(QUERY_TYPES)

        for query_type in QUERY_TYPES:
            self._publish_query(query_type)

        end_time = time.monotonic() + 8

        while time.monotonic() < end_time:
            with self._latest_lock:
                if expected.issubset(self._latest.keys()):
                    return dict(self._latest)

            time.sleep(0.1)

        with self._latest_lock:
            return dict(self._latest)

    def _reader_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._ensure_connected()

                with self._lock:
                    sock = self._sock

                if sock is None:
                    time.sleep(1)
                    continue

                try:
                    packet_type, body = _read_packet(sock)
                except (TimeoutError, socket.timeout):
                    continue

                if packet_type is None:
                    self._mark_disconnected()
                    continue

                if (packet_type & 0xF0) != 0x30:
                    continue

                topic, payload = _decode_publish(body)

                if not isinstance(payload, dict):
                    continue

                report_type = payload.get("type")

                if not report_type:
                    report_type = _type_from_topic(topic)

                if not report_type:
                    continue

                with self._latest_lock:
                    self._latest[report_type] = payload

                self.on_report(report_type, payload)
            except Exception as err:
                _LOGGER.debug("MQTT reader error, reconnecting: %s", err)
                self._mark_disconnected()
                time.sleep(2)

    def set_light(
        self,
        light_type: int,
        status: int,
        brightness: int,
    ) -> None:
        publish_topic = f"anycubic/anycubicCloud/v1/web/printer/{self.mode_id}/{self.device_id}/light"
        payload = _build_light_control_payload(light_type, status, brightness)

        with self._lock:
            self._ensure_connected_locked()

            if self._sock is None:
                raise RuntimeError("MQTT socket is not connected")

            self._sock.sendall(_publish_packet(publish_topic, payload))

    def set_camera_stream(self, action: str) -> None:
        publish_topic = f"anycubic/anycubicCloud/v1/web/printer/{self.mode_id}/{self.device_id}/video"
        payload = _build_video_capture_payload(action)

        with self._lock:
            self._ensure_connected_locked()

            if self._sock is None:
                raise RuntimeError("MQTT socket is not connected")

            self._sock.sendall(_publish_packet(publish_topic, payload))

    def set_print_settings(
        self,
        task_id: str,
        settings: dict[str, Any],
    ) -> None:
        publish_topic = f"anycubic/anycubicCloud/v1/web/printer/{self.mode_id}/{self.device_id}/print"
        payload = _build_print_update_payload(task_id, settings)

        with self._lock:
            self._ensure_connected_locked()

            if self._sock is None:
                raise RuntimeError("MQTT socket is not connected")

            self._sock.sendall(_publish_packet(publish_topic, payload))

    def _publish_query(self, query_type: str) -> None:
        publish_topic = f"anycubic/anycubicCloud/v1/web/printer/{self.mode_id}/{self.device_id}/{query_type}"
        payload = _build_query_payload(query_type)

        with self._lock:
            self._ensure_connected_locked()

            if self._sock is None:
                raise RuntimeError("MQTT socket is not connected")

            self._sock.sendall(_publish_packet(publish_topic, payload))

    def _ensure_connected(self) -> None:
        with self._lock:
            self._ensure_connected_locked()

    def _ensure_connected_locked(self) -> None:
        if self._sock is not None:
            return

        context = ssl._create_unverified_context()

        raw = socket.create_connection((self.host, self.port), timeout=10)
        sock = context.wrap_socket(raw, server_hostname=self.host)
        sock.settimeout(10)

        try:
            sock.sendall(_connect_packet(self.client_id, self.username, self.password))
            packet_type, body = _read_packet(sock)

            if packet_type != 0x20 or len(body) < 2 or body[1] != 0:
                raise RuntimeError(f"MQTT connection rejected: {body.hex()}")

            sock.sendall(_subscribe_packet(self.subscribe_topic))
            packet_type, body = _read_packet(sock)

            if packet_type != 0x90:
                raise RuntimeError(f"MQTT subscribe failed: packet={packet_type!r}, body={body.hex()}")

            sock.settimeout(1)
            self._sock = sock
            _LOGGER.debug("Connected to Anycubic LAN MQTT broker")
        except Exception:
            try:
                sock.close()
            finally:
                raise

    def _mark_disconnected(self) -> None:
        with self._lock:
            self._close_locked()

    def _close_locked(self) -> None:
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            finally:
                self._sock = None


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


def _build_light_control_payload(
    light_type: int,
    status: int,
    brightness: int,
) -> dict[str, Any]:
    return {
        "type": "light",
        "action": "control",
        "timestamp": int(time.time() * 1000),
        "msgid": str(uuid.uuid4()),
        "data": {
            "type": light_type,
            "status": status,
            "brightness": brightness,
        },
    }


def _build_video_capture_payload(action: str) -> dict[str, Any]:
    return {
        "type": "video",
        "action": action,
        "timestamp": int(time.time() * 1000),
        "msgid": str(uuid.uuid4()),
        "data": None,
    }


def _build_print_update_payload(
    task_id: str,
    settings: dict[str, Any],
) -> dict[str, Any]:
    return {
        "type": "print",
        "action": "update",
        "timestamp": int(time.time() * 1000),
        "msgid": str(uuid.uuid4()),
        "data": {
            "taskid": str(task_id or ""),
            "settings": settings,
        },
    }


def _task_id(data: dict[str, Any]) -> str:
    info = data.get("info")

    if isinstance(info, dict):
        payload = info.get("data")

        if isinstance(payload, dict):
            project = payload.get("project")

            if isinstance(project, dict):
                task_id = project.get("task_id")

                if task_id is not None:
                    return str(task_id)

        project = info.get("project")

        if isinstance(project, dict):
            task_id = project.get("task_id")

            if task_id is not None:
                return str(task_id)

    return ""


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
