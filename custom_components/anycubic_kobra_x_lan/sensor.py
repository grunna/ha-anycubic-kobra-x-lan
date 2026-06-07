from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AnycubicKobraXLanCoordinator


@dataclass(frozen=True, kw_only=True)
class AnycubicSensorEntityDescription(SensorEntityDescription):
    value_fn: Callable[[dict[str, Any]], Any]


SENSORS: tuple[AnycubicSensorEntityDescription, ...] = (
    AnycubicSensorEntityDescription(
        key="printer_state",
        name="Printer state",
        value_fn=lambda data: _payload(data, "status").get("state")
        or _payload(data, "info").get("state"),
    ),
    AnycubicSensorEntityDescription(
        key="nozzle_temperature",
        name="Nozzle temperature",
        value_fn=lambda data: _temperature(data).get("curr_nozzle_temp"),
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AnycubicSensorEntityDescription(
        key="bed_temperature",
        name="Bed temperature",
        value_fn=lambda data: _temperature(data).get("curr_hotbed_temp"),
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AnycubicSensorEntityDescription(
        key="target_nozzle_temperature",
        name="Target nozzle temperature",
        value_fn=lambda data: _temperature(data).get("target_nozzle_temp"),
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AnycubicSensorEntityDescription(
        key="target_bed_temperature",
        name="Target bed temperature",
        value_fn=lambda data: _temperature(data).get("target_hotbed_temp"),
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AnycubicSensorEntityDescription(
        key="fan_speed",
        name="Fan speed",
        value_fn=lambda data: _payload(data, "fan").get("fan_speed_pct"),
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AnycubicSensorEntityDescription(
        key="aux_fan_speed",
        name="Aux fan speed",
        value_fn=lambda data: _payload(data, "info").get("aux_fan_speed_pct"),
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AnycubicSensorEntityDescription(
        key="print_speed_mode",
        name="Print speed mode",
        value_fn=lambda data: _payload(data, "info").get("print_speed_mode"),
    ),
    AnycubicSensorEntityDescription(
        key="firmware_version",
        name="Firmware version",
        value_fn=lambda data: _payload(data, "info").get("version"),
    ),
    AnycubicSensorEntityDescription(
        key="camera_stream_url",
        name="Camera stream URL",
        value_fn=lambda data: _urls(data).get("rtspUrl"),
    ),
    AnycubicSensorEntityDescription(
        key="file_upload_url",
        name="File upload URL",
        value_fn=lambda data: _urls(data).get("fileUploadurl"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AnycubicKobraXLanCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        AnycubicKobraXLanSensor(coordinator, entry, description)
        for description in SENSORS
    )


class AnycubicKobraXLanSensor(
    CoordinatorEntity[AnycubicKobraXLanCoordinator],
    SensorEntity,
):
    entity_description: AnycubicSensorEntityDescription

    def __init__(
        self,
        coordinator: AnycubicKobraXLanCoordinator,
        entry: ConfigEntry,
        description: AnycubicSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_has_entity_name = True
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.credentials["deviceId"])},
            "name": coordinator.credentials.get("modelName", "Anycubic Kobra X"),
            "manufacturer": "Anycubic",
            "model": coordinator.credentials.get("modelName", "Anycubic Kobra X"),
            "sw_version": _payload(coordinator.data or {}, "info").get("version"),
        }

    @property
    def native_value(self) -> Any:
        if not self.coordinator.data:
            return None

        return self.entity_description.value_fn(self.coordinator.data)


def _payload(data: dict[str, Any], query_type: str) -> dict[str, Any]:
    report = data.get(query_type)

    if not isinstance(report, dict):
        return {}

    payload = report.get("data")

    if isinstance(payload, dict):
        return payload

    return report


def _temperature(data: dict[str, Any]) -> dict[str, Any]:
    tempature = _payload(data, "tempature")

    if tempature:
        return tempature

    info = _payload(data, "info")
    temp = info.get("temp")

    if isinstance(temp, dict):
        return temp

    return {}


def _urls(data: dict[str, Any]) -> dict[str, Any]:
    info = _payload(data, "info")
    urls = info.get("urls")

    if isinstance(urls, dict):
        return urls

    return {}
