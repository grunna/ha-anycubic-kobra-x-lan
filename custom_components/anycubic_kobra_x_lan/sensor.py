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
    attr_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None


STATIC_SENSORS: tuple[AnycubicSensorEntityDescription, ...] = (
    AnycubicSensorEntityDescription(
        key="printer_state",
        name="Printer state",
        value_fn=lambda data: _payload(data, "status").get("state")
        or _payload(data, "info").get("state"),
    ),
    AnycubicSensorEntityDescription(
        key="model",
        name="Model",
        value_fn=lambda data: _payload(data, "info").get("model"),
    ),
    AnycubicSensorEntityDescription(
        key="ip",
        name="IP address",
        value_fn=lambda data: _payload(data, "info").get("ip"),
    ),
    AnycubicSensorEntityDescription(
        key="features",
        name="Features",
        value_fn=lambda data: _enabled_feature_count(data),
        attr_fn=lambda data: _features(data),
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
        key="multi_color_box_status",
        name="Multi color box status",
        value_fn=lambda data: _first_multi_color_box(data).get("status"),
        attr_fn=lambda data: _multi_color_box_attributes(data),
    ),
    AnycubicSensorEntityDescription(
        key="loaded_slot",
        name="Loaded slot",
        value_fn=lambda data: _first_multi_color_box(data).get("loaded_slot"),
    ),
)

# Kept for quick imports/tests. Dynamic slot sensors are added at setup time.
SENSORS = STATIC_SENSORS


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AnycubicKobraXLanCoordinator = hass.data[DOMAIN][entry.entry_id]

    descriptions = [
        *STATIC_SENSORS,
        *_slot_sensor_descriptions(coordinator.data or {}),
    ]

    async_add_entities(
        AnycubicKobraXLanSensor(coordinator, entry, description)
        for description in descriptions
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

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if not self.coordinator.data or self.entity_description.attr_fn is None:
            return None

        attributes = self.entity_description.attr_fn(self.coordinator.data)
        return attributes or None


def _slot_sensor_descriptions(data: dict[str, Any]) -> list[AnycubicSensorEntityDescription]:
    descriptions: list[AnycubicSensorEntityDescription] = []

    for box_index, box in enumerate(_multi_color_boxes(data)):
        slots = box.get("slots")

        if not isinstance(slots, list):
            continue

        for slot_index, slot in enumerate(slots):
            if not isinstance(slot, dict):
                continue

            box_number = box_index + 1
            slot_number = slot_index + 1
            key = f"box_{box_number}_slot_{slot_number}"

            descriptions.append(
                AnycubicSensorEntityDescription(
                    key=key,
                    name=f"Box {box_number} slot {slot_number}",
                    value_fn=_make_slot_value_fn(box_index, slot_index),
                    attr_fn=_make_slot_attr_fn(box_index, slot_index),
                )
            )

    return descriptions


def _make_slot_value_fn(
    box_index: int,
    slot_index: int,
) -> Callable[[dict[str, Any]], Any]:
    def value_fn(data: dict[str, Any]) -> Any:
        return _slot(data, box_index, slot_index).get("type")

    return value_fn


def _make_slot_attr_fn(
    box_index: int,
    slot_index: int,
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def attr_fn(data: dict[str, Any]) -> dict[str, Any]:
        slot = dict(_slot(data, box_index, slot_index))

        if not slot:
            return {}

        slot["box_index"] = box_index
        slot["box_number"] = box_index + 1
        slot["slot_index"] = slot_index
        slot["slot_number"] = slot_index + 1

        color = slot.get("color")

        if isinstance(color, list) and len(color) >= 3:
            slot["color_hex"] = _rgb_to_hex(color)

        return slot

    return attr_fn


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


def _features(data: dict[str, Any]) -> dict[str, Any]:
    features = _payload(data, "info").get("features")

    if isinstance(features, dict):
        return features

    return {}


def _enabled_feature_count(data: dict[str, Any]) -> int | None:
    features = _features(data)

    if not features:
        return None

    return sum(1 for value in features.values() if value is True)


def _multi_color_box_attributes(data: dict[str, Any]) -> dict[str, Any]:
    boxes = _multi_color_boxes(data)

    return {
        "box_count": len(boxes),
        "slot_count": sum(
            len(box.get("slots", []))
            for box in boxes
            if isinstance(box.get("slots"), list)
        ),
        "boxes": [
            {
                "box_index": index,
                "box_number": index + 1,
                "status": box.get("status"),
                "loaded_slot": box.get("loaded_slot"),
                "humidity": box.get("humidity"),
                "temp": box.get("temp"),
                "slot_count": len(box.get("slots", []))
                if isinstance(box.get("slots"), list)
                else 0,
            }
            for index, box in enumerate(boxes)
        ],
    }


def _first_multi_color_box(data: dict[str, Any]) -> dict[str, Any]:
    boxes = _multi_color_boxes(data)

    if boxes:
        return boxes[0]

    return {}


def _multi_color_boxes(data: dict[str, Any]) -> list[dict[str, Any]]:
    payload = _payload(data, "multiColorBox")
    boxes = payload.get("multi_color_box")

    if not isinstance(boxes, list):
        return []

    return [box for box in boxes if isinstance(box, dict)]


def _slot(data: dict[str, Any], box_index: int, slot_index: int) -> dict[str, Any]:
    boxes = _multi_color_boxes(data)

    if box_index < 0 or box_index >= len(boxes):
        return {}

    slots = boxes[box_index].get("slots")

    if not isinstance(slots, list):
        return {}

    if slot_index < 0 or slot_index >= len(slots):
        return {}

    slot = slots[slot_index]

    if isinstance(slot, dict):
        return slot

    return {}


def _rgb_to_hex(color: list[Any]) -> str | None:
    try:
        r = int(color[0])
        g = int(color[1])
        b = int(color[2])
    except (TypeError, ValueError, IndexError):
        return None

    r = max(0, min(255, r))
    g = max(0, min(255, g))
    b = max(0, min(255, b))

    return f"#{r:02x}{g:02x}{b:02x}"
