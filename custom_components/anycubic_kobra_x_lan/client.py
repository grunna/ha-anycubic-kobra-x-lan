from __future__ import annotations

import base64
import hashlib
import json
import logging
import secrets
import string
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


_LOGGER = logging.getLogger(__name__)


class AnycubicKobraXLanError(Exception):
    """Base exception for Anycubic Kobra X LAN errors."""


class AnycubicKobraXLanConnectionError(AnycubicKobraXLanError):
    """Raised when the printer cannot be reached."""


class AnycubicKobraXLanAuthError(AnycubicKobraXLanError):
    """Raised when LAN credential discovery fails."""


@dataclass(slots=True)
class AnycubicLanCredentials:
    broker: str
    device_id: str
    device_type: str
    devicecrt: str
    devicepk: str
    ip: str
    mode_id: str
    model_id: str
    model_name: str
    username: str
    password: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AnycubicLanCredentials":
        return cls(
            broker=data["broker"],
            device_id=data["deviceId"],
            device_type=data["deviceType"],
            devicecrt=data["devicecrt"],
            devicepk=data["devicepk"],
            ip=data["ip"],
            mode_id=str(data["modeId"]),
            model_id=str(data["modelId"]),
            model_name=data["modelName"],
            username=data["username"],
            password=data["password"],
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "broker": self.broker,
            "deviceId": self.device_id,
            "deviceType": self.device_type,
            "devicecrt": self.devicecrt,
            "devicepk": self.devicepk,
            "ip": self.ip,
            "modeId": self.mode_id,
            "modelId": self.model_id,
            "modelName": self.model_name,
            "username": self.username,
            "password": self.password,
        }


class AnycubicKobraXLanClient:
    def __init__(self, host: str, pc_device_id: str) -> None:
        self.host = host.strip()
        self.pc_device_id = pc_device_id.strip()

    def discover_credentials(self) -> AnycubicLanCredentials:
        _LOGGER.debug("Starting LAN credential discovery for host %s", self.host)

        info = self._get_info()

        _LOGGER.debug(
            "Received /info response from host %s: keys=%s model=%s model_id=%s ctrl_type=%s ctrl_url_present=%s token_present=%s",
            self.host,
            sorted(info.keys()),
            info.get("modelName"),
            info.get("modelId"),
            info.get("ctrlType"),
            bool(info.get("ctrlInfoUrl")),
            bool(info.get("token")),
        )

        try:
            token = info["token"]
            ctrl_url = info["ctrlInfoUrl"]
        except KeyError as err:
            raise AnycubicKobraXLanAuthError(
                f"/info response missing required field: {err.args[0]}"
            ) from err

        timestamp = str(int(time.time() * 1000))
        nonce = self._nonce(6)
        sign = self._md5_hex(self._md5_hex(token[:16]) + timestamp + nonce)

        ctrl_request_url = (
            ctrl_url
            + "?"
            + urllib.parse.urlencode(
                {
                    "ts": timestamp,
                    "nonce": nonce,
                    "sign": sign,
                    "did": self.pc_device_id,
                }
            )
        )

        _LOGGER.debug(
            "Requesting /ctrl for host %s with pc_device_id_present=%s",
            self.host,
            bool(self.pc_device_id),
        )

        ctrl = self._get_json(ctrl_request_url, method="POST")

        _LOGGER.debug(
            "Received /ctrl response from host %s: code=%s keys=%s data_keys=%s",
            self.host,
            ctrl.get("code"),
            sorted(ctrl.keys()),
            sorted(ctrl.get("data", {}).keys()) if isinstance(ctrl.get("data"), dict) else [],
        )

        if ctrl.get("code") != 200:
            raise AnycubicKobraXLanAuthError(f"/ctrl failed: {ctrl}")

        try:
            decrypted = self._decrypt_ctrl_info(
                cipher_b64=ctrl["data"]["info"],
                key=token[16:32],
                iv=ctrl["data"]["token"],
            )
        except KeyError as err:
            raise AnycubicKobraXLanAuthError(
                f"/ctrl response missing required field: {err.args[0]}"
            ) from err

        _LOGGER.debug(
            "Decrypted LAN credentials for host %s: keys=%s model=%s model_id=%s device_id_present=%s broker_present=%s username_present=%s password_present=%s",
            self.host,
            sorted(decrypted.keys()),
            decrypted.get("modelName"),
            decrypted.get("modelId") or decrypted.get("modeId"),
            bool(decrypted.get("deviceId")),
            bool(decrypted.get("broker")),
            bool(decrypted.get("username")),
            bool(decrypted.get("password") or decrypted.get("passWd")),
        )

        return AnycubicLanCredentials.from_dict(decrypted)

    def _get_info(self) -> dict[str, Any]:
        return self._get_json(f"http://{self.host}:18910/info")

    def _get_json(self, url: str, method: str = "GET") -> dict[str, Any]:
        request = urllib.request.Request(url, method=method)

        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return json.loads(response.read().decode("utf-8"))
        except OSError as err:
            raise AnycubicKobraXLanConnectionError(str(err)) from err
        except json.JSONDecodeError as err:
            raise AnycubicKobraXLanConnectionError("Invalid JSON response") from err

    @staticmethod
    def _md5_hex(value: str) -> str:
        return hashlib.md5(value.encode("utf-8")).hexdigest()

    @staticmethod
    def _nonce(length: int) -> str:
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(length))

    @staticmethod
    def _decrypt_ctrl_info(cipher_b64: str, key: str, iv: str) -> dict[str, Any]:
        encrypted = base64.b64decode(cipher_b64)

        cipher = Cipher(
            algorithms.AES(key.encode("utf-8")),
            modes.CBC(iv.encode("utf-8")),
        )

        decryptor = cipher.decryptor()
        padded = decryptor.update(encrypted) + decryptor.finalize()

        if not padded:
            raise AnycubicKobraXLanAuthError("Empty decrypted payload")

        padding_length = padded[-1]

        if padding_length < 1 or padding_length > 16:
            raise AnycubicKobraXLanAuthError("Invalid PKCS7 padding")

        plain = padded[:-padding_length]

        try:
            return json.loads(plain.decode("utf-8"))
        except json.JSONDecodeError as err:
            raise AnycubicKobraXLanAuthError("Invalid decrypted JSON") from err
