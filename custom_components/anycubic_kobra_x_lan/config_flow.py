from __future__ import annotations

import secrets
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .client import (
    AnycubicKobraXLanAuthError,
    AnycubicKobraXLanClient,
    AnycubicKobraXLanConnectionError,
)
from .const import CONF_HOST, CONF_PC_DEVICE_ID, DOMAIN


def _generate_pc_device_id() -> str:
    return secrets.token_hex(16).upper()


class AnycubicKobraXLanConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            pc_device_id = _generate_pc_device_id()

            try:
                credentials = await self.hass.async_add_executor_job(
                    self._discover_credentials,
                    host,
                    pc_device_id,
                )
            except AnycubicKobraXLanConnectionError:
                errors["base"] = "cannot_connect"
            except AnycubicKobraXLanAuthError:
                errors["base"] = "auth_failed"
            except Exception:
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(credentials.device_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=credentials.model_name,
                    data={
                        CONF_HOST: host,
                        CONF_PC_DEVICE_ID: pc_device_id,
                        "credentials": credentials.as_dict(),
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                }
            ),
            errors=errors,
        )

    @staticmethod
    def _discover_credentials(host: str, pc_device_id: str):
        client = AnycubicKobraXLanClient(host, pc_device_id)
        return client.discover_credentials()

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return AnycubicKobraXLanOptionsFlowHandler(config_entry)


class AnycubicKobraXLanOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        return self.async_create_entry(title="", data={})
