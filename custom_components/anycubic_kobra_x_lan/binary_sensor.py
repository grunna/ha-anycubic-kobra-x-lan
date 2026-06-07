from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AnycubicKobraXLanCoordinator


@dataclass(frozen=True)
class AnycubicBinarySensorDescription:
    key: str
    name: str
    value_fn: Callable[[dict[str, Any]], bool | None]
    device_class: BinarySensorDeviceClass | None = None


BINARY_SENSORS: tuple[AnycubicBinarySensorDescription, ...] = (
    AnycubicBinarySensorDescription(
        key="camera_available",
        name="Camera available",
        value_fn=lambda data: _as_bool(_payload(data, "peripherie").get("camera")),
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
    ),
    AnycubicBinarySensorDescription(
        key="usb_available",
        name="USB available",
        value_fn=lambda data: _as_bool(_payload(data, "peripherie").get("udisk")),
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
    ),
    AnycubicBinarySensorDescription(
        key="multi_color_box_available",
        name="Multi color box available",
        value_fn=lambda data: _as_bool(_payload(data, "peripherie").get("multiColorBox")),
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AnycubicKobraXLanCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        AnycubicKobraXLanBinarySensor(coordinator, entry, description)
        for description in BINARY_SENSORS
    )


class AnycubicKobraXLanBinarySensor(
    CoordinatorEntity[AnycubicKobraXLanCoordinator],
    BinarySensorEntity,
):
    def __init__(
        self,
        coordinator: AnycubicKobraXLanCoordinator,
        entry: ConfigEntry,
        description: AnycubicBinarySensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_translation_key = description.key
        self._attr_has_entity_name = True
        self._attr_name = description.name
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.credentials["deviceId"])},
            "name": coordinator.credentials.get("modelName", "Anycubic Kobra X"),
            "manufacturer": "Anycubic",
            "model": coordinator.credentials.get("modelName", "Anycubic Kobra X"),
        }

    @property
    def is_on(self) -> bool | None:
        if not self.coordinator.data:
            return None

        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def device_class(self) -> BinarySensorDeviceClass | None:
        return self.entity_description.device_class


def _payload(data: dict[str, Any], query_type: str) -> dict[str, Any]:
    report = data.get(query_type)

    if not isinstance(report, dict):
        return {}

    payload = report.get("data")

    if isinstance(payload, dict):
        return payload

    return report


def _as_bool(value: Any) -> bool | None:
    if value is None:
        return None

    return bool(value)
