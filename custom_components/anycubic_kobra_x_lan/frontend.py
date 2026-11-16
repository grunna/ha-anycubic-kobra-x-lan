"""Serve the bundled Lovelace card and load it on every dashboard."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from homeassistant.core import HomeAssistant

from .const import CARD_FILENAME, DOMAIN, FRONTEND_URL_BASE

_LOGGER = logging.getLogger(__name__)
_REGISTERED = f"{DOMAIN}_frontend_registered"


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Register the card once per Home Assistant run.

    The URL carries the integration version so browsers pick up a new card
    after an update instead of serving a cached one.
    """
    if hass.data.get(_REGISTERED):
        return

    hass.data[_REGISTERED] = True
    directory = Path(__file__).parent / "frontend"

    try:
        from homeassistant.components.frontend import add_extra_js_url
        from homeassistant.components.http import StaticPathConfig

        await hass.http.async_register_static_paths(
            [StaticPathConfig(FRONTEND_URL_BASE, str(directory), False)]
        )
        manifest = await hass.async_add_executor_job(
            (Path(__file__).parent / "manifest.json").read_text
        )
        version = json.loads(manifest).get("version", "0")
        add_extra_js_url(hass, f"{FRONTEND_URL_BASE}/{CARD_FILENAME}?v={version}")
    except Exception as err:  # noqa: BLE001 - the card is optional
        hass.data[_REGISTERED] = False
        _LOGGER.warning("Could not register the Kobra X printer card: %s", err)
