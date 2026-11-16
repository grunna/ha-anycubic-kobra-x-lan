from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import data as data_helpers
from .const import DOMAIN
from .coordinator import AnycubicKobraXLanCoordinator
from .entity import AnycubicKobraXLanEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AnycubicKobraXLanCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([AnycubicKobraXLanSpeedModeSelect(coordinator, entry)])


class AnycubicKobraXLanSpeedModeSelect(AnycubicKobraXLanEntity, SelectEntity):
    """Print speed mode. The printer only accepts a change during a job."""

    _attr_name = "Print speed mode"
    _attr_icon = "mdi:speedometer"

    def __init__(
        self,
        coordinator: AnycubicKobraXLanCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator, entry, "print_speed_mode_select")

    @property
    def available(self) -> bool:
        return super().available and data_helpers.print_in_progress(self.data)

    @property
    def options(self) -> list[str]:
        return list(data_helpers.speed_modes(self.data).values())

    @property
    def current_option(self) -> str | None:
        mode = data_helpers.print_settings(self.data).get("print_speed_mode")

        try:
            return data_helpers.speed_modes(self.data).get(int(mode))
        except (TypeError, ValueError):
            return None

    async def async_select_option(self, option: str) -> None:
        for mode, title in data_helpers.speed_modes(self.data).items():
            if title == option:
                await self.coordinator.async_set_print_speed_mode(mode)
                await self.coordinator.async_request_refresh()
                return

        raise HomeAssistantError(f"Unknown print speed mode: {option}")
