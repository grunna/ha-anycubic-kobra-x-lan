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
    AnycubicLanCredentials,
)
from .const import (
    CONF_HOST,
    CONF_PC_DEVICE_ID,
    CONF_POLLING_INTERVAL,
    DEFAULT_POLLING_INTERVAL,
    DOMAIN,
    MAX_POLLING_INTERVAL,
    MIN_POLLING_INTERVAL,
)


def _generate_pc_device_id() -> str:
    return secrets.token_hex(16).upper()


class AnycubicKobraXLanConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._pending_host: str | None = None
        self._pending_pc_device_id: str | None = None
        self._pending_credentials: AnycubicLanCredentials | None = None

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
                self._abort_if_unique_id_configured(
                    updates={
                        CONF_HOST: host,
                    }
                )

                self._pending_host = host
                self._pending_pc_device_id = pc_device_id
                self._pending_credentials = credentials

                return await self.async_step_confirm()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                }
            ),
            errors=errors,
        )

    async def async_step_confirm(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        if (
            self._pending_host is None
            or self._pending_pc_device_id is None
            or self._pending_credentials is None
        ):
            return await self.async_step_user()

        credentials = self._pending_credentials

        if user_input is not None:
            return self.async_create_entry(
                title=credentials.model_name,
                data={
                    CONF_HOST: self._pending_host,
                    CONF_PC_DEVICE_ID: self._pending_pc_device_id,
                    "credentials": credentials.as_dict(),
                },
                options={
                    CONF_POLLING_INTERVAL: DEFAULT_POLLING_INTERVAL,
                },
            )

        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema({}),
            description_placeholders={
                "name": credentials.model_name,
                "model": credentials.model_name,
                "ip": credentials.ip,
                "device_id": credentials.device_id,
            },
        )

    @staticmethod
    def _discover_credentials(host: str, pc_device_id: str) -> AnycubicLanCredentials:
        client = AnycubicKobraXLanClient(host, pc_device_id)
        return client.discover_credentials()

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return AnycubicKobraXLanOptionsFlowHandler(config_entry)


class AnycubicKobraXLanOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry) -> None:
        self.config_entry = config_entry

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_polling_interval = self.config_entry.options.get(
            CONF_POLLING_INTERVAL,
            DEFAULT_POLLING_INTERVAL,
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_POLLING_INTERVAL,
                        default=current_polling_interval,
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(
                            min=MIN_POLLING_INTERVAL,
                            max=MAX_POLLING_INTERVAL,
                        ),
                    ),
                }
            ),
        )
