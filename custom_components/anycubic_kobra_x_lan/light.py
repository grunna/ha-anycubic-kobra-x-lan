from __future__ import annotations

from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AnycubicKobraXLanCoordinator


LIGHT_NAMES = {
    1: "Printhead light",
    2: "Chamber light",
    3: "Camera light",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AnycubicKobraXLanCoordinator = hass.data[DOMAIN][entry.entry_id]

    light_types = _reported_light_types(coordinator.data or {})

    if not light_types:
        light_types = [3]

    async_add_entities(
        AnycubicKobraXLanLight(coordinator, entry, light_type)
        for light_type in light_types
    )


class AnycubicKobraXLanLight(
    CoordinatorEntity[AnycubicKobraXLanCoordinator],
    LightEntity,
):
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}
    _attr_color_mode = ColorMode.BRIGHTNESS

    def __init__(
        self,
        coordinator: AnycubicKobraXLanCoordinator,
        entry: ConfigEntry,
        light_type: int,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._light_type = light_type
        self._attr_unique_id = f"{entry.entry_id}_light_{light_type}"
        self._attr_has_entity_name = True
        self._attr_name = LIGHT_NAMES.get(light_type, f"Light {light_type}")
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.credentials["deviceId"])},
            "name": coordinator.credentials.get("modelName", "Anycubic Kobra X"),
            "manufacturer": "Anycubic",
            "model": coordinator.credentials.get("modelName", "Anycubic Kobra X"),
        }

    @property
    def is_on(self) -> bool | None:
        light = self._light_data()

        if not light:
            return None

        return light.get("status") == 1

    @property
    def brightness(self) -> int | None:
        light = self._light_data()

        if not light:
            return None

        brightness_percent = light.get("brightness")

        if brightness_percent is None:
            return 255 if light.get("status") == 1 else 0

        try:
            brightness_percent = int(brightness_percent)
        except (TypeError, ValueError):
            return None

        brightness_percent = max(0, min(100, brightness_percent))

        return round(brightness_percent * 255 / 100)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        light = self._light_data()

        if not light:
            return {
                "light_type": self._light_type,
            }

        return {
            "light_type": self._light_type,
            "status": light.get("status"),
            "brightness_percent": light.get("brightness"),
            "raw": light,
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        brightness = kwargs.get(ATTR_BRIGHTNESS)

        if brightness is None:
            brightness_percent = 100
        else:
            brightness_percent = round(int(brightness) * 100 / 255)
            brightness_percent = max(1, min(100, brightness_percent))

        await self.coordinator.async_set_light(
            self._light_type,
            1,
            brightness_percent,
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_light(
            self._light_type,
            0,
            0,
        )
        await self.coordinator.async_request_refresh()

    def _light_data(self) -> dict[str, Any]:
        for light in _lights(self.coordinator.data or {}):
            if light.get("type") == self._light_type:
                return light

        return {}


def _reported_light_types(data: dict[str, Any]) -> list[int]:
    light_types = []

    for light in _lights(data):
        light_type = light.get("type")

        if isinstance(light_type, int):
            light_types.append(light_type)

    return sorted(set(light_types))


def _lights(data: dict[str, Any]) -> list[dict[str, Any]]:
    payload = _payload(data, "light")
    lights = payload.get("lights")

    if not isinstance(lights, list):
        return []

    return [light for light in lights if isinstance(light, dict)]


def _payload(data: dict[str, Any], query_type: str) -> dict[str, Any]:
    report = data.get(query_type)

    if not isinstance(report, dict):
        return {}

    payload = report.get("data")

    if isinstance(payload, dict):
        return payload

    return report
