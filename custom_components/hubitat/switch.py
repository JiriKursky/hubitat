import logging
from . import HUBITAT_DEVICES, HubitatEntity, DOMAIN, my_debug, HAT_SWITCH
from homeassistant.components.switch  import (ENTITY_ID_FORMAT, SwitchDevice)
from inspect import currentframe, getframeinfo
_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Perform the setup for Fibaro controller devices."""    
    if discovery_info is None:
        my_debug("Neobjeveno")
        return    
    
    add_entities(
        [HubitatSwitch(device)
         for device in hass.data[HUBITAT_DEVICES][HAT_SWITCH]], True)   

class HubitatSwitch(HubitatEntity, SwitchDevice):
    def __init__(self, hubitat_device):
        self._state = False
        super().__init__(hubitat_device)                             
        self.entity_id = ENTITY_ID_FORMAT.format(self.entity_id)      

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def is_on(self):
        """Return true if device is on."""
        return self._state

    def update(self):
        """Get the latest data and update the state."""
        self._state = self.current_binary_state

    def turn_on(self, **kwargs):
        """Turn device on."""
        my_debug("turn on")
        self.call_turn_on()
        self._state = True

    def turn_off(self, **kwargs):
        """Turn device off."""
        my_debug("turn off")
        self.call_turn_off()
        self._state = False