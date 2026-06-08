from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AnycubicKobraXLanCoordinator


@dataclass(frozen=True)
class AnycubicButtonDescription:
    key: str
    name: str
    press_fn: Callable[[AnycubicKobraXLanCoordinator], Awaitable[None]]


BUTTONS: tuple[AnycubicButtonDescription, ...] = (
    AnycubicButtonDescription(
        key="refresh_data",
        name="Refresh data",
        press_fn=lambda coordinator: coordinator.async_request_refresh(),
    ),
    AnycubicButtonDescription(
        key="reconnect",
        name="Reconnect LAN connection",
        press_fn=lambda coordinator: coordinator.async_reconnect(),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AnycubicKobraXLanCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        AnycubicKobraXLanButton(coordinator, entry, description)
        for description in BUTTONS
    )


class AnycubicKobraXLanButton(
    CoordinatorEntity[AnycubicKobraXLanCoordinator],
    ButtonEntity,
):
    def __init__(
        self,
        coordinator: AnycubicKobraXLanCoordinator,
        entry: ConfigEntry,
        description: AnycubicButtonDescription,
    ) -> None:
        super().__init__(coordinator)
        self._description = description
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_has_entity_name = True
        self._attr_name = description.name
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.credentials["deviceId"])},
            "name": coordinator.credentials.get("modelName", "Anycubic Kobra X"),
            "manufacturer": "Anycubic",
            "model": coordinator.credentials.get("modelName", "Anycubic Kobra X"),
        }

    async def async_press(self) -> None:
        await self._description.press_fn(self.coordinator)
