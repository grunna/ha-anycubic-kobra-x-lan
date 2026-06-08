from __future__ import annotations

import time
from typing import Any

from homeassistant.components.camera import Camera
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AnycubicKobraXLanCoordinator


CAMERA_START_DEBOUNCE_SECONDS = 10


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AnycubicKobraXLanCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([AnycubicKobraXLanCamera(coordinator, entry)])


class AnycubicKobraXLanCamera(
    CoordinatorEntity[AnycubicKobraXLanCoordinator],
    Camera,
):
    def __init__(
        self,
        coordinator: AnycubicKobraXLanCoordinator,
        entry: ConfigEntry,
    ) -> None:
        CoordinatorEntity.__init__(self, coordinator)
        Camera.__init__(self)

        self._entry = entry
        self._last_start_request = 0.0
        self._attr_unique_id = f"{entry.entry_id}_camera"
        self._attr_has_entity_name = True
        self._attr_name = "Camera"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.credentials["deviceId"])},
            "name": coordinator.credentials.get("modelName", "Anycubic Kobra X"),
            "manufacturer": "Anycubic",
            "model": coordinator.credentials.get("modelName", "Anycubic Kobra X"),
        }

    @property
    def is_on(self) -> bool:
        peripherie = _payload(self.coordinator.data or {}, "peripherie")
        return bool(peripherie.get("camera"))

    async def stream_source(self) -> str | None:
        if not self.is_on:
            return None

        stream_url = self._stream_url()

        if not stream_url:
            return None

        self._schedule_camera_stream_start()
        return stream_url

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        camera_stream = (self.coordinator.data or {}).get("camera_stream")

        attrs: dict[str, Any] = {
            "camera_available": self.is_on,
            "stream_source": "internal",
        }

        if isinstance(camera_stream, dict):
            attrs["stream_enabled"] = camera_stream.get("enabled")
            attrs["last_stream_action"] = camera_stream.get("last_action")
            attrs["last_stream_state"] = camera_stream.get("last_state")
            attrs["last_stream_code"] = camera_stream.get("last_code")

        return attrs

    def _schedule_camera_stream_start(self) -> None:
        now = time.monotonic()

        if now - self._last_start_request < CAMERA_START_DEBOUNCE_SECONDS:
            return

        self._last_start_request = now

        self.coordinator.hass.async_create_task(
            self.coordinator.async_set_camera_stream(True)
        )

    def _stream_url(self) -> str | None:
        info = _payload(self.coordinator.data or {}, "info")
        urls = info.get("urls")

        if not isinstance(urls, dict):
            return None

        stream_url = urls.get("rtspUrl")

        if not isinstance(stream_url, str) or not stream_url:
            return None

        return stream_url


def _payload(data: dict[str, Any], query_type: str) -> dict[str, Any]:
    report = data.get(query_type)

    if not isinstance(report, dict):
        return {}

    payload = report.get("data")

    if isinstance(payload, dict):
        return payload

    return report
