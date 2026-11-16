"""Print events: started, paused, resumed, finished, stopped, failed, error."""

from __future__ import annotations

from typing import Any

from homeassistant.components.event import EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, PRINT_EVENT_TYPES
from .coordinator import AnycubicKobraXLanCoordinator
from .entity import AnycubicKobraXLanEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AnycubicKobraXLanCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([AnycubicKobraXLanPrintEvent(coordinator, entry)])


class AnycubicKobraXLanPrintEvent(AnycubicKobraXLanEntity, EventEntity):
    """Something to hang a notification on.

    `error` fires once per fault the user did not cause (a clog, spaghetti),
    the others follow the job. Events carry `task`, `progress` and, when the
    printer gave one, `reason_code` and `reason`.
    """

    _attr_name = "Print event"
    _attr_icon = "mdi:printer-3d-nozzle-alert-outline"
    _attr_event_types = PRINT_EVENT_TYPES

    def __init__(
        self,
        coordinator: AnycubicKobraXLanCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator, entry, "print_event")

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            self.coordinator.async_add_event_listener(self._async_handle_event)
        )

    @callback
    def _async_handle_event(self, event_type: str, attributes: dict[str, Any]) -> None:
        self._trigger_event(
            event_type,
            {key: value for key, value in attributes.items() if value is not None},
        )
        self.async_write_ha_state()
