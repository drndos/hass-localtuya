"""Platform to locally control Tuya-based climate devices."""
import json
import logging
from functools import partial

import voluptuous as vol
from homeassistant.components.climate import (
    DEFAULT_MAX_TEMP,
    DEFAULT_MIN_TEMP,
    DOMAIN,
    ClimateEntity,
)
from homeassistant.components.climate.const import (
    HVAC_MODE_AUTO,
    HVAC_MODE_HEAT,
    HVAC_MODE_COOL, HVAC_MODE_DRY,
    HVAC_MODE_FAN_ONLY, FAN_AUTO, FAN_LOW, FAN_MEDIUM, FAN_HIGH,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    TEMP_CELSIUS,
)

from .common import LocalTuyaEntity, async_setup_entry
from .const import (
    CONF_CURRENT_TEMPERATURE_DP,
    CONF_AC_SPEED_AUTO,
    CONF_AC_SPEED_LOW,
    CONF_AC_SPEED_MEDIUM,
    CONF_AC_SPEED_HIGH,
    CONF_AC_MODE_COLD,
    CONF_AC_MODE_HOT,
    CONF_AC_MODE_AUTO,
    CONF_AC_MODE_SPEED,
    CONF_AC_MODE_DEHUMY,
    CONF_AC_SET_TEMP,
    CONF_CURRENT_HUMIDITY_DP,
    CONF_AC_SWITCH_ON,
    CONF_AC_SWITCH_OFF,
)

_LOGGER = logging.getLogger(__name__)


COMMAND = {
    "control": "send_ir",
    "head": "010ed80000000000040015003d00a900c8",
    "key1": "",
    "type": 0,
    "delay": 300
}

def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Optional(CONF_CURRENT_TEMPERATURE_DP): vol.In(dps),
        vol.Optional(CONF_CURRENT_HUMIDITY_DP): vol.In(dps),
        vol.Optional(CONF_AC_SWITCH_ON): str,
        vol.Optional(CONF_AC_SWITCH_OFF): str,
        vol.Optional(CONF_AC_SPEED_AUTO): str,
        vol.Optional(CONF_AC_SPEED_LOW): str,
        vol.Optional(CONF_AC_SPEED_MEDIUM): str,
        vol.Optional(CONF_AC_SPEED_HIGH): str,
        vol.Optional(CONF_AC_MODE_COLD): str,
        vol.Optional(CONF_AC_MODE_HOT): str,
        vol.Optional(CONF_AC_MODE_AUTO): str,
        vol.Optional(CONF_AC_MODE_SPEED): str,
        vol.Optional(CONF_AC_MODE_DEHUMY): str,
        vol.Optional(CONF_AC_SET_TEMP): str,
    }


class LocaltuyaIRClimate(LocalTuyaEntity, ClimateEntity):
    """Tuya IR climate device."""

    def __init__(
        self,
        device,
        config_entry,
        switchid,
        **kwargs,
    ):
        """Initialize a new LocaltuyaClimate."""
        super().__init__(device, config_entry, switchid, _LOGGER, **kwargs)
        self._state = None
        self._current_temperature = None
        self._current_temperature_dp = self._config.get(CONF_CURRENT_TEMPERATURE_DP)
        self._current_humidity = None
        self._current_humidity_dp = self._config.get(CONF_CURRENT_HUMIDITY_DP)
        self._fan_mode = None
        self._hvac_mode = None
        self._target_temperature = None
        # self._dp_id

        _LOGGER.debug("Initialized ir climate [%s]", self.name)

    @property
    def supported_features(self):
        """Flag supported features."""
        supported_features = 0
        return supported_features

    @property
    def precision(self):
        """Return the precision of the system."""
        return 0.1

    @property
    def target_precision(self):
        """Return the precision of the target."""
        return 1

    @property
    def temperature_unit(self):
        """Return the unit of measurement used by the platform."""
        return TEMP_CELSIUS

    @property
    def hvac_mode(self):
        """Return current operation ie. heat, cool, idle."""
        return self._hvac_mode

    @property
    def hvac_modes(self):
        """Return the list of available operation modes."""
        return [HVAC_MODE_AUTO,
                HVAC_MODE_HEAT,
                HVAC_MODE_COOL,
                HVAC_MODE_FAN_ONLY,
                HVAC_MODE_DRY,
                ]

    @property
    def hvac_action(self):
        """Return the current running hvac operation if supported.
        Need to be one of CURRENT_HVAC_*.
        """
        return None

    @property
    def preset_mode(self):
        """Return current preset."""
        return None

    @property
    def preset_modes(self):
        """Return the list of available presets modes."""
        return None

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._current_temperature

    @property
    def current_humidity(self):
        """Return the current humidity."""
        return self._current_humidity

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._target_temperature

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        return 1

    @property
    def fan_mode(self):
        """Return the fan setting."""
        return self._fan_mode

    @property
    def fan_modes(self):
        """Return the list of available fan modes."""
        return [FAN_AUTO, FAN_LOW, FAN_MEDIUM, FAN_HIGH]

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        if ATTR_TEMPERATURE in kwargs:
            temperature = round(kwargs[ATTR_TEMPERATURE])
            return NotImplementedError()

    def set_fan_mode(self, fan_mode):
        """Set new target fan mode."""
        # Set temperature command
        self._fan_mode = fan_mode
        return NotImplementedError()

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target operation mode."""
        self._hvac_mode = hvac_mode
        command = COMMAND
        if hvac_mode == HVAC_MODE_HEAT:
            command["key1"] = self._config.get(CONF_AC_MODE_HOT)
        elif hvac_mode == HVAC_MODE_COOL:
            command["key1"] = self._config(CONF_AC_MODE_COLD)
        elif hvac_mode == HVAC_MODE_AUTO:
            command["key1"] = self._config(CONF_AC_MODE_AUTO)
        elif hvac_mode == HVAC_MODE_DRY:
            command["key1"] = self._config(CONF_AC_MODE_DEHUMY)
        elif hvac_mode == HVAC_MODE_FAN_ONLY:
            command["key1"] = self._config(CONF_AC_MODE_SPEED)

        await self._device.set_dp(json.dumps(command), "201")

    async def async_turn_on(self):
        """Turn the entity on."""
        command = COMMAND
        command["key1"] = self._config(CONF_AC_SWITCH_ON)
        await self._device.set_dp(json.dumps(command), "201")

    async def async_turn_off(self):
        """Turn the entity off."""
        command = COMMAND
        command["key1"] = self._config(CONF_AC_SWITCH_OFF)
        await self._device.set_dp(json.dumps(command), "201")

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return DEFAULT_MIN_TEMP

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return DEFAULT_MAX_TEMP

    def status_updated(self):
        """Device status was updated."""
        self._state = self.dps(self._dp_id)

        if self.has_config(CONF_CURRENT_TEMPERATURE_DP):
            self._current_temperature = (
                self.dps_conf(CONF_CURRENT_TEMPERATURE_DP) * 0.1
            )

        if self.has_config(CONF_CURRENT_HUMIDITY_DP):
            self._current_humidity = (
                self.dps_conf(CONF_CURRENT_HUMIDITY_DP)
            )


async_setup_entry = partial(async_setup_entry, DOMAIN, LocaltuyaIRClimate, flow_schema)
