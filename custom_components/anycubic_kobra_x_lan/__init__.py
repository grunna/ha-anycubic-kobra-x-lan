from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, PLATFORMS
from .coordinator import AnycubicKobraXLanCoordinator
from .frontend import async_register_frontend


SERVICE_REFRESH_DATA = "refresh_data"
SERVICE_RECONNECT = "reconnect"
SERVICE_MOVE_AXIS = "move_axis"
SERVICE_START_DRYING = "start_drying"
SERVICE_STOP_DRYING = "stop_drying"

_AXIS_IDS = {"x": 1, "y": 2, "z": 3}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = AnycubicKobraXLanCoordinator(hass, entry)

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    _async_register_services(hass)
    await async_register_frontend(hass)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = hass.data[DOMAIN].get(entry.entry_id)

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        if coordinator is not None:
            await coordinator.async_shutdown()

        hass.data[DOMAIN].pop(entry.entry_id, None)

        if not hass.data[DOMAIN]:
            for service in (
                SERVICE_REFRESH_DATA,
                SERVICE_RECONNECT,
                SERVICE_MOVE_AXIS,
                SERVICE_START_DRYING,
                SERVICE_STOP_DRYING,
            ):
                hass.services.async_remove(DOMAIN, service)

    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


def _async_register_services(hass: HomeAssistant) -> None:
    if not hass.services.has_service(DOMAIN, SERVICE_REFRESH_DATA):
        hass.services.async_register(
            DOMAIN,
            SERVICE_REFRESH_DATA,
            _make_coordinator_service_handler(
                hass,
                lambda coordinator, data: coordinator.async_request_refresh(),
            ),
            schema=_SERVICE_SCHEMA,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_RECONNECT):
        hass.services.async_register(
            DOMAIN,
            SERVICE_RECONNECT,
            _make_coordinator_service_handler(
                hass,
                lambda coordinator, data: coordinator.async_reconnect(),
            ),
            schema=_SERVICE_SCHEMA,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_MOVE_AXIS):
        hass.services.async_register(
            DOMAIN,
            SERVICE_MOVE_AXIS,
            _make_coordinator_service_handler(
                hass,
                lambda coordinator, data: coordinator.async_move_axis(
                    _AXIS_IDS[data["axis"]],
                    1 if data["distance"] >= 0 else 0,
                    abs(int(data["distance"])),
                ),
            ),
            schema=_MOVE_AXIS_SCHEMA,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_START_DRYING):
        hass.services.async_register(
            DOMAIN,
            SERVICE_START_DRYING,
            _make_coordinator_service_handler(
                hass,
                lambda coordinator, data: coordinator.async_set_drying(
                    data["box"] - 1,
                    True,
                    data.get("temperature"),
                    data.get("duration"),
                ),
            ),
            schema=_START_DRYING_SCHEMA,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_STOP_DRYING):
        hass.services.async_register(
            DOMAIN,
            SERVICE_STOP_DRYING,
            _make_coordinator_service_handler(
                hass,
                lambda coordinator, data: coordinator.async_set_drying(
                    data["box"] - 1,
                    False,
                ),
            ),
            schema=_STOP_DRYING_SCHEMA,
        )


_SERVICE_SCHEMA = vol.Schema(
    {
        vol.Optional("entry_id"): cv.string,
    }
)

_MOVE_AXIS_SCHEMA = _SERVICE_SCHEMA.extend(
    {
        vol.Required("axis"): vol.In(list(_AXIS_IDS)),
        vol.Required("distance"): vol.All(vol.Coerce(int), vol.Range(min=-100, max=100)),
    }
)

_STOP_DRYING_SCHEMA = _SERVICE_SCHEMA.extend(
    {
        vol.Optional("box", default=1): vol.All(vol.Coerce(int), vol.Range(min=1, max=4)),
    }
)

_START_DRYING_SCHEMA = _STOP_DRYING_SCHEMA.extend(
    {
        vol.Optional("temperature"): vol.All(vol.Coerce(int), vol.Range(min=35, max=70)),
        vol.Optional("duration"): vol.All(vol.Coerce(int), vol.Range(min=1, max=720)),
    }
)


def _make_coordinator_service_handler(
    hass: HomeAssistant,
    action,
):
    async def async_handle_service(call: ServiceCall) -> None:
        entry_id = call.data.get("entry_id")

        coordinators: list[AnycubicKobraXLanCoordinator] = []

        if entry_id:
            coordinator = hass.data.get(DOMAIN, {}).get(entry_id)

            if coordinator is not None:
                coordinators.append(coordinator)
        else:
            coordinators.extend(hass.data.get(DOMAIN, {}).values())

        for coordinator in coordinators:
            await action(coordinator, call.data)

    return async_handle_service
