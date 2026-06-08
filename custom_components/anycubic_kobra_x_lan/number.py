from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.number import NumberDeviceClass, NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AnycubicKobraXLanCoordinator


@dataclass(frozen=True)
class AnycubicTemperatureNumberDescription:
    key: str
    name: str
    setting_key: str
    min_value: float
    max_value: float
    step: float


NUMBERS: tuple[AnycubicTemperatureNumberDescription, ...] = (
    AnycubicTemperatureNumberDescription(
        key="target_bed_temperature_control",
        name="Target bed temperature",
        setting_key="target_hotbed_temp",
        min_value=0,
        max_value=120,
        step=1,
    ),
    AnycubicTemperatureNumberDescription(
        key="target_nozzle_temperature_control",
        name="Target nozzle temperature",
        setting_key="target_nozzle_temp",
        min_value=0,
        max_value=300,
        step=1,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AnycubicKobraXLanCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        AnycubicKobraXLanTemperatureNumber(coordinator, entry, description)
        for description in NUMBERS
    )


class AnycubicKobraXLanTemperatureNumber(
    CoordinatorEntity[AnycubicKobraXLanCoordinator],
    NumberEntity,
):
    _attr_device_class = NumberDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_mode = "box"

    def __init__(
        self,
        coordinator: AnycubicKobraXLanCoordinator,
        entry: ConfigEntry,
        description: AnycubicTemperatureNumberDescription,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_has_entity_name = True
        self._attr_name = description.name
        self._attr_native_min_value = description.min_value
        self._attr_native_max_value = description.max_value
        self._attr_native_step = description.step
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.credentials["deviceId"])},
            "name": coordinator.credentials.get("modelName", "Anycubic Kobra X"),
            "manufacturer": "Anycubic",
            "model": coordinator.credentials.get("modelName", "Anycubic Kobra X"),
        }

    @property
    def native_value(self) -> float | None:
        value = _temperature(self.coordinator.data or {}).get(
            self._description.setting_key
        )

        if value is None:
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "setting_key": self._description.setting_key,
            "note": "Set to 0 to turn heating off.",
        }

    async def async_set_native_value(self, value: float) -> None:
        temperature = int(round(value))

        temperature = max(
            int(self._description.min_value),
            min(int(self._description.max_value), temperature),
        )

        await self.coordinator.async_set_target_temperature(
            self._description.setting_key,
            temperature,
        )


def _temperature(data: dict[str, Any]) -> dict[str, Any]:
    tempature = _payload(data, "tempature")

    if tempature:
        return tempature

    info = _payload(data, "info")
    temp = info.get("temp")

    if isinstance(temp, dict):
        return temp

    return {}


def _payload(data: dict[str, Any], query_type: str) -> dict[str, Any]:
    report = data.get(query_type)

    if not isinstance(report, dict):
        return {}

    payload = report.get("data")

    if isinstance(payload, dict):
        return payload

    return report
