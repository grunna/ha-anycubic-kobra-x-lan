from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AnycubicKobraXLanCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AnycubicKobraXLanCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([AnycubicKobraXLanCameraStreamSwitch(coordinator, entry)])


class AnycubicKobraXLanCameraStreamSwitch(
    CoordinatorEntity[AnycubicKobraXLanCoordinator],
    SwitchEntity,
):
    def __init__(
        self,
        coordinator: AnycubicKobraXLanCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_camera_stream"
        self._attr_has_entity_name = True
        self._attr_name = "Camera stream"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.credentials["deviceId"])},
            "name": coordinator.credentials.get("modelName", "Anycubic Kobra X"),
            "manufacturer": "Anycubic",
            "model": coordinator.credentials.get("modelName", "Anycubic Kobra X"),
        }

    @property
    def is_on(self) -> bool | None:
        camera_stream = (self.coordinator.data or {}).get("camera_stream")

        if isinstance(camera_stream, dict) and "enabled" in camera_stream:
            return bool(camera_stream["enabled"])

        return None

    @property
    def available(self) -> bool:
        return bool(_payload(self.coordinator.data or {}, "peripherie").get("camera"))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        camera_stream = (self.coordinator.data or {}).get("camera_stream")

        attrs: dict[str, Any] = {
            "camera_available": self.available,
        }

        if isinstance(camera_stream, dict):
            attrs.update(camera_stream)

        return attrs

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_camera_stream(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_camera_stream(False)


def _payload(data: dict[str, Any], query_type: str) -> dict[str, Any]:
    report = data.get(query_type)

    if not isinstance(report, dict):
        return {}

    payload = report.get("data")

    if isinstance(payload, dict):
        return payload

    return report
