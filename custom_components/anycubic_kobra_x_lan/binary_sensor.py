from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
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
