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
    CONF_CURRENT_HUMIDITY_DP,
)

_LOGGER = logging.getLogger(__name__)


COMMAND = {
    "control": "send_ir",
    "head": "010ed80000000000040015003d00a900c8",
    "key1": "",
    "type": 0,
    "delay": 300
}

STUDY_COMMAND = {
    "control": "",
}


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Optional(CONF_CURRENT_TEMPERATURE_DP): vol.In(dps),
        vol.Optional(CONF_CURRENT_HUMIDITY_DP): vol.In(dps),
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
        self._fan_mode = FAN_AUTO
        self._hvac_mode = HVAC_MODE_AUTO
        self._target_temperature = 17
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
            self._target_temperature = temperature
            await self._device.set_dp(json.dumps(self.encode()), "201")

    def set_fan_mode(self, fan_mode):
        """Set new target fan mode."""
        self._fan_mode = fan_mode
        await self._device.set_dp(json.dumps(self.encode()), "201")

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target operation mode."""
        self._hvac_mode = hvac_mode
        await self._device.set_dp(json.dumps(self.encode()), "201")

    async def async_turn_on(self):
        """Turn the entity on."""
        await self._device.set_dp(json.dumps(self.encode()), "201")

    async def async_turn_off(self):
        """Turn the entity off."""
        command = COMMAND
        command["key1"] = "002$$0030B24D7B84E01F@%"
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

        if self.dps("202"):
            self._state = self.dps("202")

        if self.has_config(CONF_CURRENT_TEMPERATURE_DP):
            self._current_temperature = (
                self.dps_conf(CONF_CURRENT_TEMPERATURE_DP) * 0.1
            )

        if self.has_config(CONF_CURRENT_HUMIDITY_DP):
            self._current_humidity = (
                self.dps_conf(CONF_CURRENT_HUMIDITY_DP)
            )

    def encode(self):
        key = "002$$0030B24DXFX0XXXX@%"
        key = self.encode_temperature(key)
        key = self.encode_fan_speed(key)
        key = self.encode_hvac_mode(key)
        command = COMMAND
        command["key1"] = key

        return command

    def encode_hvac_mode(self, key):
        hvac_mode = self._hvac_mode
        if hvac_mode == HVAC_MODE_AUTO:
            key = key[:18] + "8" + key[18+1:]
            key = key[:20] + "7" + key[20+1:]
        elif hvac_mode == HVAC_MODE_COOL:
            key = key[:18] + "0" + key[18+1:]
            key = key[:20] + "F" + key[20+1:]
        elif hvac_mode == HVAC_MODE_HEAT:
            key = key[:18] + "C" + key[18+1:]
            key = key[:20] + "3" + key[20+1:]
        elif hvac_mode == HVAC_MODE_DRY:
            key = key[:13] + "1" + key[13+1:]
            key = key[:15] + "E" + key[15+1:]
            key = key[:18] + "4" + key[18+1:]
            key = key[:20] + "B" + key[20+1:]
        elif hvac_mode == HVAC_MODE_FAN_ONLY:
            key = key[:17] + "E41B" + key[21:]
        return key

    def encode_fan_speed(self, key):
        fan_speed = self._fan_mode
        if fan_speed == FAN_AUTO:
            key = key[:13] + "B" + key[13+1:]
            key = key[:15] + "4" + key[15+1:]
        elif fan_speed == FAN_LOW:
            key = key[:13] + "9" + key[13+1:]
            key = key[:15] + "6" + key[15+1:]
        elif fan_speed == FAN_MEDIUM:
            key = key[:13] + "5" + key[13+1:]
            key = key[:15] + "A" + key[15+1:]
        elif fan_speed == FAN_HIGH:
            key = key[:13] + "3" + key[13+1:]
            key = key[:15] + "C" + key[15+1:]
        return key

    def encode_temperature(self, key):
        temperature = self._target_temperature
        if temperature == 17:
            key = key[:17] + "0" + key[17+1:]
            key = key[:19] + "F" + key[19+1:]
        elif temperature == 18:
            key = key[:17] + "1" + key[17+1:]
            key = key[:19] + "E" + key[19+1:]
        elif temperature == 19:
            key = key[:17] + "3" + key[17+1:]
            key = key[:19] + "C" + key[19+1:]
        elif temperature == 20:
            key = key[:17] + "2" + key[17+1:]
            key = key[:19] + "D" + key[19+1:]
        elif temperature == 21:
            key = key[:17] + "6" + key[17+1:]
            key = key[:19] + "9" + key[19+1:]
        elif temperature == 22:
            key = key[:17] + "7" + key[17+1:]
            key = key[:19] + "8" + key[19+1:]
        elif temperature == 23:
            key = key[:17] + "5" + key[17+1:]
            key = key[:19] + "A" + key[19+1:]
        elif temperature == 24:
            key = key[:17] + "4" + key[17+1:]
            key = key[:19] + "B" + key[19+1:]
        elif temperature == 25:
            key = key[:17] + "C" + key[17+1:]
            key = key[:19] + "3" + key[19+1:]
        elif temperature == 26:
            key = key[:17] + "D" + key[17+1:]
            key = key[:19] + "2" + key[19+1:]
        elif temperature == 27:
            key = key[:17] + "9" + key[17+1:]
            key = key[:19] + "6" + key[19+1:]
        elif temperature == 28:
            key = key[:17] + "8" + key[17+1:]
            key = key[:19] + "7" + key[19+1:]
        elif temperature == 29:
            key = key[:17] + "A" + key[17+1:]
            key = key[:19] + "5" + key[19+1:]
        elif temperature == 30:
            key = key[:17] + "B" + key[17+1:]
            key = key[:19] + "4" + key[19+1:]
        return key


async_setup_entry = partial(async_setup_entry, DOMAIN, LocaltuyaIRClimate, flow_schema)
