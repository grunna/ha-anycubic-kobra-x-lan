from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.number import NumberDeviceClass, NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AnycubicKobraXLanCoordinator


@dataclass(frozen=True)
class AnycubicNumberDescription:
    key: str
    name: str
    setting_key: str
    value_fn: Callable[[dict[str, Any]], Any]
    min_value: float
    max_value: float
    step: float
    unit: str
    device_class: NumberDeviceClass | None
    note: str


NUMBERS: tuple[AnycubicNumberDescription, ...] = (
    AnycubicNumberDescription(
        key="target_bed_temperature_control",
        name="Target bed temperature",
        setting_key="target_hotbed_temp",
        value_fn=lambda data: _temperature(data).get("target_hotbed_temp"),
        min_value=0,
        max_value=120,
        step=1,
        unit=UnitOfTemperature.CELSIUS,
        device_class=NumberDeviceClass.TEMPERATURE,
        note="Set to 0 to turn bed heating off.",
    ),
    AnycubicNumberDescription(
        key="target_nozzle_temperature_control",
        name="Target nozzle temperature",
        setting_key="target_nozzle_temp",
        value_fn=lambda data: _temperature(data).get("target_nozzle_temp"),
        min_value=0,
        max_value=300,
        step=1,
        unit=UnitOfTemperature.CELSIUS,
        device_class=NumberDeviceClass.TEMPERATURE,
        note="Set to 0 to turn nozzle heating off.",
    ),
    AnycubicNumberDescription(
        key="model_fan_speed_control",
        name="Model fan speed",
        setting_key="fan_speed_pct",
        value_fn=lambda data: _fan(data).get("fan_speed_pct"),
        min_value=0,
        max_value=100,
        step=10,
        unit=PERCENTAGE,
        device_class=None,
        note="Controls the model cooling fan speed.",
    ),
    AnycubicNumberDescription(
        key="aux_fan_speed_control",
        name="Aux fan speed",
        setting_key="aux_fan_speed_pct",
        value_fn=lambda data: _fan(data).get("aux_fan_speed_pct"),
        min_value=0,
        max_value=100,
        step=10,
        unit=PERCENTAGE,
        device_class=None,
        note="Controls the auxiliary fan speed.",
    ),
    AnycubicNumberDescription(
        key="box_fan_speed_control",
        name="Box fan speed",
        setting_key="box_fan_level",
        value_fn=lambda data: _fan(data).get("box_fan_level"),
        min_value=0,
        max_value=100,
        step=10,
        unit=PERCENTAGE,
        device_class=None,
        note="Controls the chamber/box fan speed.",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AnycubicKobraXLanCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        AnycubicKobraXLanNumber(coordinator, entry, description)
        for description in NUMBERS
    )


class AnycubicKobraXLanNumber(
    CoordinatorEntity[AnycubicKobraXLanCoordinator],
    NumberEntity,
):
    _attr_mode = "box"

    def __init__(
        self,
        coordinator: AnycubicKobraXLanCoordinator,
        entry: ConfigEntry,
        description: AnycubicNumberDescription,
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
        self._attr_native_unit_of_measurement = description.unit
        self._attr_device_class = description.device_class
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.credentials["deviceId"])},
            "name": coordinator.credentials.get("modelName", "Anycubic Kobra X"),
            "manufacturer": "Anycubic",
            "model": coordinator.credentials.get("modelName", "Anycubic Kobra X"),
        }

    @property
    def native_value(self) -> float | None:
        value = self._description.value_fn(self.coordinator.data or {})

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
            "note": self._description.note,
        }

    async def async_set_native_value(self, value: float) -> None:
        new_value = int(round(value))

        new_value = max(
            int(self._description.min_value),
            min(int(self._description.max_value), new_value),
        )

        await self.coordinator.async_set_print_setting(
            self._description.setting_key,
            new_value,
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


def _fan(data: dict[str, Any]) -> dict[str, Any]:
    fan = _payload(data, "fan")

    if fan:
        return fan

    info = _payload(data, "info")

    values: dict[str, Any] = {}

    for key in ("fan_speed_pct", "aux_fan_speed_pct", "box_fan_level"):
        if key in info:
            values[key] = info[key]

    return values


def _payload(data: dict[str, Any], query_type: str) -> dict[str, Any]:
    report = data.get(query_type)

    if not isinstance(report, dict):
        return {}

    payload = report.get("data")

    if isinstance(payload, dict):
        return payload

    return report
