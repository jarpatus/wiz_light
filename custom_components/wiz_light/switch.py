"""WiZ Light integration."""
import logging

from pywizlight import PilotBuilder, wizlight
import voluptuous as vol

try:
    from homeassistant.components.switch import (DOMAIN, SwitchEntity)
except ImportError:
    from homeassistant.components.switch import (DOMAIN, SwitchDevice as SwitchEntity)
from homeassistant.components.switch import PLATFORM_SCHEMA
from homeassistant.const import CONF_HOST, CONF_NAME
import homeassistant.helpers.config_validation as cv
from homeassistant.util import slugify                                     

_LOGGER = logging.getLogger(__name__)

# Validation of the user's configuration

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {vol.Required(CONF_HOST): cv.string, vol.Required(CONF_NAME): cv.string}
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the WiZ switch platform."""
    # Assign configuration variables.
    # The configuration check takes care they are present.
    name = config[CONF_NAME]
    ip_address = config[CONF_HOST]
    switch = wizlight(ip_address)
    wizplug = WizPlug(switch, name)

    # Add devices
    async_add_entities([wizplug])
    
    # Handle events
    async def async_handle_event(event):
        ip = event.data.get("ip")
        if ip == ip_address:
            _LOGGER.debug("[wizlight %s] got first beat event", ip_address)
            await wizbulb.async_update()
            await wizbulb.async_update_ha_state();
    hass.bus.async_listen("wiz_light_first_beat", async_handle_event)

    # Register services
    async def async_update(call=None):
        """Trigger update."""
        _LOGGER.debug(
            "[wizlight %s] update requested",
            ip_address,
        )
        await wizplug.async_update()
        await wizplug.async_update_ha_state();
    service_name = slugify(f"{name} update")
    hass.services.async_register(DOMAIN, service_name, async_update)


class WizPlug(SwitchEntity):
    """Representation of WiZ Switch."""

    def __init__(self, switch, name):
        """Initialize an WiZLight."""
        self._switch = switch
        self._state = None
        self._name = name
        self._available = None
        self.async_update()

    @property
    def name(self):
        """Return the ip as name of the device if any."""
        return self._name

    @property
    def is_on(self):
        """Return true if switch is on."""
        return self._state

    @property
    def should_poll(self):
        """Retrun True to add to poll."""
        return True

    async def async_turn_on(self, **kwargs):
        """Instruct the switch to turn on."""
        await self._switch.turn_on(PilotBuilder())
        self._state = True
        self.schedule_update_ha_state()

    async def async_turn_off(self, **kwargs):
        """Instruct the switch to turn off."""
        await self._switch.turn_off()
        self._state = False
        self.schedule_update_ha_state()

    @property
    def available(self):
        """Return if switch is available."""
        return self._available

    async def async_update(self):
        """Fetch new state data for this light."""
        await self.update_state()

    async def update_state_available(self):
        """Update the state if bulb is available."""
        self._state = self._switch.status
        self._available = True
        _LOGGER.debug(
            "[wizlight %s] updated state: %s; available: %s",
            self._switch.ip,
            self._state,
            self._available,
        )

    async def update_state_unavailable(self):
        """Update the state if bulb is unavailable."""
        self._state = False
        self._available = False
        _LOGGER.debug(
            "[wizlight %s] updated state: %s; available: %s",
            self._switch.ip,
            self._state,
            self._available,
        )

    async def update_state(self):
        """Update the state."""
        try:
            _LOGGER.debug("[wizlight %s] updating state", self._switch.ip)
            await self._switch.updateState()
            if self._switch.state is None:
                await self.update_state_unavailable()
            else:
                await self.update_state_available()
        # pylint: disable=broad-except
        except Exception as ex:
            _LOGGER.error(ex)
            await self.update_state_unavailable()
        _LOGGER.debug("[wizlight %s] updated state: %s", self._switch.ip, self._state)
