from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN

TO_REDACT = {
    "password",
    "username",
    "devicepk",
    "devicecrt",
    "token",
    "credentials",
    "fileUploadurl",
    "rtspUrl",
    "stream_url",
    "broker",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""

    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    entity_registry = er.async_get(hass)

    entities = [
        {
            "entity_id": entity.entity_id,
            "platform": entity.platform,
            "unique_id": entity.unique_id,
            "disabled_by": str(entity.disabled_by) if entity.disabled_by else None,
        }
        for entity in er.async_entries_for_config_entry(
            entity_registry,
            entry.entry_id,
        )
    ]

    data = coordinator.data if coordinator and coordinator.data else {}
    credentials = coordinator.credentials if coordinator else entry.data.get("credentials", {})

    diagnostics = {
        "entry": {
            "title": entry.title,
            "domain": entry.domain,
            "entry_id": entry.entry_id,
            "unique_id": entry.unique_id,
            "data": entry.data,
            "options": entry.options,
        },
        "integration": {
            "domain": DOMAIN,
            "name": "Anycubic Kobra X LAN",
        },
        "printer": _printer_summary(data, credentials),
        "mqtt": _mqtt_summary(coordinator),
        "entities": entities,
        "latest_reports": data,
        "features": _features(data),
        "multi_color_box": _multi_color_box_summary(data),
    }

    return async_redact_data(diagnostics, TO_REDACT)


def _printer_summary(
    data: dict[str, Any],
    credentials: dict[str, Any],
) -> dict[str, Any]:
    info = _payload(data, "info")

    return {
        "model_name": credentials.get("modelName") or info.get("model"),
        "model_id": credentials.get("modelId") or credentials.get("modeId"),
        "device_type": credentials.get("deviceType"),
        "device_id": credentials.get("deviceId"),
        "ip": credentials.get("ip") or info.get("ip"),
        "firmware_version": info.get("version"),
        "state": info.get("state") or _payload(data, "status").get("state"),
        "available_report_types": sorted(data.keys()),
    }


def _mqtt_summary(coordinator: Any) -> dict[str, Any]:
    mqtt = getattr(coordinator, "_mqtt", None)

    if mqtt is None:
        return {
            "available": False,
        }

    sock = getattr(mqtt, "_sock", None)
    latest = getattr(mqtt, "_latest", {})

    return {
        "available": True,
        "host": getattr(mqtt, "host", None),
        "port": getattr(mqtt, "port", None),
        "client_id": getattr(mqtt, "client_id", None),
        "subscribe_topic": getattr(mqtt, "subscribe_topic", None),
        "connected": sock is not None,
        "known_report_types": sorted(latest.keys()) if isinstance(latest, dict) else [],
    }


def _payload(data: dict[str, Any], query_type: str) -> dict[str, Any]:
    report = data.get(query_type)

    if not isinstance(report, dict):
        return {}

    payload = report.get("data")

    if isinstance(payload, dict):
        return payload

    return report


def _features(data: dict[str, Any]) -> dict[str, Any]:
    features = _payload(data, "info").get("features")

    if not isinstance(features, dict):
        return {
            "enabled_count": 0,
            "enabled": [],
            "all": {},
        }

    enabled = sorted(key for key, value in features.items() if value is True)

    return {
        "enabled_count": len(enabled),
        "enabled": enabled,
        "all": features,
    }


def _multi_color_box_summary(data: dict[str, Any]) -> dict[str, Any]:
    box = _multi_color_box(data)
    slots = box.get("slots")

    slot_summaries = []

    if isinstance(slots, list):
        for slot in slots:
            if not isinstance(slot, dict):
                continue

            slot_summaries.append(
                {
                    "index": slot.get("index"),
                    "type": slot.get("type"),
                    "status": slot.get("status"),
                    "consumables_percent": slot.get("consumables_percent"),
                    "weight": slot.get("weight"),
                    "color": slot.get("color"),
                    "sku": slot.get("sku"),
                }
            )

    return {
        "status": box.get("status"),
        "loaded_slot": box.get("loaded_slot"),
        "humidity": box.get("humidity"),
        "temp": box.get("temp"),
        "slots": slot_summaries,
    }


def _multi_color_box(data: dict[str, Any]) -> dict[str, Any]:
    payload = _payload(data, "multiColorBox")
    boxes = payload.get("multi_color_box")

    if isinstance(boxes, list) and boxes and isinstance(boxes[0], dict):
        return boxes[0]

    return {}
