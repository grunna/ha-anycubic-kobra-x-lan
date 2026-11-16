from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import data as data_helpers
from .const import DOMAIN
from .coordinator import AnycubicKobraXLanCoordinator


class AnycubicKobraXLanEntity(CoordinatorEntity[AnycubicKobraXLanCoordinator]):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AnycubicKobraXLanCoordinator,
        entry: ConfigEntry,
        key: str,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        # Stable key so dashboards/cards can find the entity whatever its name.
        self._attr_translation_key = key
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.credentials["deviceId"])},
            "name": coordinator.credentials.get("modelName", "Anycubic Kobra X"),
            "manufacturer": "Anycubic",
            "model": coordinator.credentials.get("modelName", "Anycubic Kobra X"),
        }

    @property
    def data(self) -> dict[str, Any]:
        return self.coordinator.data or {}


def async_add_per_box_entities(
    coordinator: AnycubicKobraXLanCoordinator,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    factory: Callable[[int], Iterable[Entity]],
) -> None:
    """Add entities for every multi-color box (ACE), also ones reported later."""
    known: set[int] = set()

    @callback
    def _async_add_new_boxes() -> None:
        count = len(data_helpers.multi_color_boxes(coordinator.data or {}))
        new_indexes = [index for index in range(count) if index not in known]

        if not new_indexes:
            return

        known.update(new_indexes)
        entities: list[Entity] = []

        for box_index in new_indexes:
            entities.extend(factory(box_index))

        async_add_entities(entities)

    _async_add_new_boxes()
    entry.async_on_unload(coordinator.async_add_listener(_async_add_new_boxes))


def box_key(box_index: int, key: str) -> str:
    """Keep the first box's keys short, number the others."""
    return key if box_index == 0 else f"box_{box_index + 1}_{key}"


def box_name(box_index: int, name: str) -> str:
    return name if box_index == 0 else f"Box {box_index + 1} {name[0].lower()}{name[1:]}"
