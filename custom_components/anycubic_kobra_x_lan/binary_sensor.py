from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import data as data_helpers
from .const import DOMAIN
from .entity import async_add_per_box_entities, box_key, box_name
from .coordinator import AnycubicKobraXLanCoordinator


@dataclass(frozen=True, kw_only=True)
class AnycubicBinarySensorEntityDescription(BinarySensorEntityDescription):
    value_fn: Callable[[dict[str, Any]], bool | None]
    attr_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None


BINARY_SENSORS: tuple[AnycubicBinarySensorEntityDescription, ...] = (
    AnycubicBinarySensorEntityDescription(
        key="camera_available",
        name="Camera available",
        value_fn=lambda data: bool(_payload(data, "peripherie").get("camera")),
        attr_fn=lambda data: _camera_attributes(data),
    ),
    AnycubicBinarySensorEntityDescription(
        key="usb_available",
        name="USB available",
        value_fn=lambda data: bool(_payload(data, "peripherie").get("usb")),
    ),
    AnycubicBinarySensorEntityDescription(
        key="print_in_progress",
        name="Printing",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=data_helpers.print_in_progress,
    ),
    AnycubicBinarySensorEntityDescription(
        key="print_paused",
        name="Print paused",
        icon="mdi:pause-circle-outline",
        value_fn=data_helpers.print_paused,
    ),
    AnycubicBinarySensorEntityDescription(
        key="print_complete",
        name="Print complete",
        icon="mdi:check-circle-outline",
        value_fn=data_helpers.print_complete,
    ),
    AnycubicBinarySensorEntityDescription(
        key="print_failed",
        name="Print failed",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=data_helpers.print_failed,
        attr_fn=lambda data: {"error": data_helpers.last_print_error(data)},
    ),
    AnycubicBinarySensorEntityDescription(
        key="print_cancelled",
        name="Print cancelled",
        icon="mdi:cancel",
        value_fn=data_helpers.print_stopped,
    ),
    AnycubicBinarySensorEntityDescription(
        key="axis_moving",
        name="Axis moving",
        device_class=BinarySensorDeviceClass.MOVING,
        value_fn=lambda data: data_helpers.axis_move_state(data)
        not in (None, "done", "failed"),
        entity_registry_enabled_default=False,
    ),
    AnycubicBinarySensorEntityDescription(
        key="multi_color_box_available",
        name="Multi color box available",
        value_fn=lambda data: bool(
            _payload(data, "peripherie").get("multi_color_box")
            or _multi_color_box_available(data)
        ),
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
    async_add_entities([AnycubicKobraXLanConnectedSensor(coordinator, entry)])

    async_add_per_box_entities(
        coordinator,
        entry,
        async_add_entities,
        lambda box_index: [
            AnycubicKobraXLanBinarySensor(
                coordinator,
                entry,
                AnycubicBinarySensorEntityDescription(
                    key=box_key(box_index, "drying"),
                    name=box_name(box_index, "Drying"),
                    device_class=BinarySensorDeviceClass.HEAT,
                    value_fn=lambda data: data_helpers.is_drying(data, box_index),
                    attr_fn=lambda data: data_helpers.drying_status(data, box_index),
                ),
            )
        ],
    )


class AnycubicKobraXLanBinarySensor(
    CoordinatorEntity[AnycubicKobraXLanCoordinator],
    BinarySensorEntity,
):
    entity_description: AnycubicBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: AnycubicKobraXLanCoordinator,
        entry: ConfigEntry,
        description: AnycubicBinarySensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        # Stable key so dashboards/cards can find the entity whatever its name.
        self._attr_translation_key = description.key
        self._attr_has_entity_name = True
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.credentials["deviceId"])},
            "name": coordinator.credentials.get("modelName", "Anycubic Kobra X"),
            "manufacturer": "Anycubic",
            "model": coordinator.credentials.get("modelName", "Anycubic Kobra X"),
            "sw_version": _payload(coordinator.data or {}, "info").get("version"),
        }

    @property
    def is_on(self) -> bool | None:
        if not self.coordinator.data:
            return None

        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if not self.coordinator.data or self.entity_description.attr_fn is None:
            return None

        attributes = self.entity_description.attr_fn(self.coordinator.data)
        return attributes or None


class AnycubicKobraXLanConnectedSensor(
    CoordinatorEntity[AnycubicKobraXLanCoordinator],
    BinarySensorEntity,
):
    """On while the LAN MQTT connection to the printer is up."""

    _attr_has_entity_name = True
    _attr_name = "LAN connection"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: AnycubicKobraXLanCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_lan_connection"
        # Stable key so dashboards/cards can find the entity whatever its name.
        self._attr_translation_key = "lan_connection"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.credentials["deviceId"])},
        }

    @property
    def available(self) -> bool:
        # Must stay available to report the printer being offline.
        return True

    @property
    def is_on(self) -> bool:
        return self.coordinator.last_update_success and self.coordinator.mqtt_connected


def _camera_attributes(data: dict[str, Any]) -> dict[str, Any]:
    info = _payload(data, "info")
    urls = info.get("urls")

    attrs: dict[str, Any] = {
        "note": "The stream URL may contain a printer access token. Do not share it publicly.",
    }

    if isinstance(urls, dict):
        stream_url = urls.get("rtspUrl")

        if isinstance(stream_url, str) and stream_url:
            attrs["stream_url"] = stream_url
            attrs["stream_url_type"] = "printer_reported_rtsp_url"
            attrs["stream_format_note"] = (
                "AnycubicSlicerNext appears to treat this stream as FLV. "
                "Home Assistant's default camera card may not be able to play it directly."
            )

        file_upload_url = urls.get("fileUploadUrl") or urls.get("fileUploadurl")

        if isinstance(file_upload_url, str) and file_upload_url:
            attrs["file_upload_url_available"] = True

    return attrs


def _payload(data: dict[str, Any], query_type: str) -> dict[str, Any]:
    report = data.get(query_type)

    if not isinstance(report, dict):
        return {}

    payload = report.get("data")

    if isinstance(payload, dict):
        return payload

    return report


def _multi_color_box_available(data: dict[str, Any]) -> bool:
    multi_color_box = _payload(data, "multiColorBox")
    boxes = multi_color_box.get("multi_color_box")

    return isinstance(boxes, list) and len(boxes) > 0
