from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import data as data_helpers
from .const import DOMAIN
from .coordinator import AnycubicKobraXLanCoordinator
from .entity import (
    AnycubicKobraXLanEntity,
    async_add_per_box_entities,
    box_key,
    box_name,
)


@dataclass(frozen=True)
class AnycubicButtonDescription:
    key: str
    name: str
    press_fn: Callable[[AnycubicKobraXLanCoordinator], Awaitable[None]]
    icon: str | None = None
    available_fn: Callable[[dict[str, Any]], bool] | None = None
    entity_category: EntityCategory | None = None
    enabled_default: bool = True


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
    AnycubicButtonDescription(
        key="pause_print",
        name="Pause print",
        icon="mdi:pause",
        press_fn=lambda coordinator: coordinator.async_print_control("pause"),
        available_fn=lambda data: data_helpers.print_in_progress(data)
        and not data_helpers.print_paused(data),
    ),
    AnycubicButtonDescription(
        key="resume_print",
        name="Resume print",
        icon="mdi:play",
        press_fn=lambda coordinator: coordinator.async_print_control("resume"),
        available_fn=data_helpers.print_paused,
    ),
    AnycubicButtonDescription(
        key="cancel_print",
        name="Cancel print",
        icon="mdi:stop",
        press_fn=lambda coordinator: coordinator.async_print_control("stop"),
        available_fn=data_helpers.print_in_progress,
    ),
    AnycubicButtonDescription(
        key="home_all_axes",
        name="Home all axes",
        icon="mdi:home",
        press_fn=lambda coordinator: coordinator.async_home_all_axes(),
        available_fn=lambda data: not data_helpers.print_in_progress(data),
        enabled_default=False,
    ),
    AnycubicButtonDescription(
        key="home_xy",
        name="Home X/Y",
        icon="mdi:home-import-outline",
        press_fn=lambda coordinator: coordinator.async_move_axis(4, 2),
        available_fn=lambda data: not data_helpers.print_in_progress(data),
        enabled_default=False,
    ),
    AnycubicButtonDescription(
        key="home_z",
        name="Home Z",
        icon="mdi:arrow-collapse-down",
        press_fn=lambda coordinator: coordinator.async_move_axis(3, 2),
        available_fn=lambda data: not data_helpers.print_in_progress(data),
        enabled_default=False,
    ),
    AnycubicButtonDescription(
        key="motors_off",
        name="Disable motors",
        icon="mdi:engine-off-outline",
        press_fn=lambda coordinator: coordinator.async_motors_off(),
        available_fn=lambda data: not data_helpers.print_in_progress(data),
        enabled_default=False,
    ),
    AnycubicButtonDescription(
        key="query_axis_position",
        name="Read axis position",
        icon="mdi:axis-arrow",
        press_fn=lambda coordinator: coordinator.async_query_axis_position(),
        entity_category=EntityCategory.DIAGNOSTIC,
        enabled_default=False,
    ),
)


def _box_buttons(box_index: int) -> tuple[AnycubicButtonDescription, ...]:
    return (
        AnycubicButtonDescription(
            key=box_key(box_index, "drying_start"),
            name=box_name(box_index, "Start drying"),
            icon="mdi:heat-wave",
            press_fn=lambda coordinator: coordinator.async_set_drying(box_index, True),
            available_fn=lambda data: not data_helpers.is_drying(data, box_index),
        ),
        AnycubicButtonDescription(
            key=box_key(box_index, "drying_stop"),
            name=box_name(box_index, "Stop drying"),
            icon="mdi:stop-circle-outline",
            press_fn=lambda coordinator: coordinator.async_set_drying(box_index, False),
            available_fn=lambda data: bool(data_helpers.is_drying(data, box_index)),
        ),
        AnycubicButtonDescription(
            key=box_key(box_index, "retract_filament"),
            name=box_name(box_index, "Retract filament"),
            icon="mdi:tray-arrow-up",
            press_fn=lambda coordinator: coordinator.async_retract_filament(box_index),
            available_fn=lambda data: not data_helpers.print_in_progress(data),
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

    async_add_per_box_entities(
        coordinator,
        entry,
        async_add_entities,
        lambda box_index: (
            AnycubicKobraXLanButton(coordinator, entry, description)
            for description in _box_buttons(box_index)
        ),
    )


class AnycubicKobraXLanButton(AnycubicKobraXLanEntity, ButtonEntity):
    def __init__(
        self,
        coordinator: AnycubicKobraXLanCoordinator,
        entry: ConfigEntry,
        description: AnycubicButtonDescription,
    ) -> None:
        # Keep the unique_id scheme of the original two buttons.
        super().__init__(coordinator, entry, description.key)
        self._description = description
        self._attr_name = description.name
        self._attr_icon = description.icon
        self._attr_entity_category = description.entity_category
        self._attr_entity_registry_enabled_default = description.enabled_default

    @property
    def available(self) -> bool:
        if not super().available:
            return False

        if self._description.available_fn is None:
            return True

        return bool(self._description.available_fn(self.data))

    async def async_press(self) -> None:
        await self._description.press_fn(self.coordinator)
