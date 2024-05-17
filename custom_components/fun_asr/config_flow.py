import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow
from typing import Any ,Dict, Optional
from homeassistant.data_entry_flow import FlowResult
import aiohttp
import logging

from . import DOMAIN

MODELS = ['tiny', 'small', 'base', 'medium', 'large-v3']

_LOGGER = logging.getLogger(__name__)

async def validate_path(path: str) -> None:

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(path) as response:
                _LOGGER.info(f'response.status {response.status}')
                if response.status != 200:
                    raise ValueError
                await response.text()
    except Exception as e:
        _LOGGER.error('validate_path', e)
        raise ValueError

class ConfigFlowHandler(ConfigFlow, domain=DOMAIN):

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: Dict[str, str] = {}
        if user_input:
            try:
                await validate_path(user_input['server'])
            except Exception as e:
                _LOGGER.error('async_step_user', e)
                errors["base"] = "地址填写有误"
            if not errors:
                return self.async_create_entry(title="Fun Asr", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("server" ): str,
                    vol.Optional("model", default="base"): vol.In(MODELS),
                },
            ),
            errors=errors
        )
