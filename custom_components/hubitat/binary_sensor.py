import logging
from . import HUBITAT_DEVICES, HubitatEntity, DOMAIN, my_debug, HAT_BINARY_SENSOR
from homeassistant.components.binary_sensor import (ENTITY_ID_FORMAT, BinarySensorDevice, DEVICE_CLASS_MOTION)
from inspect import currentframe, getframeinfo
_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Perform the setup for Fibaro controller devices."""    
    if discovery_info is None:
        my_debug("Neobjeveno")
        return    
    
    add_entities(
        [HubitatSensor(device)
         for device in hass.data[HUBITAT_DEVICES][HAT_BINARY_SENSOR]], True)   

class HubitatSensor(HubitatEntity, BinarySensorDevice):
    def __init__(self, hubitat_device):
        self._state = False
        super().__init__(hubitat_device)                             
        self.entity_id = ENTITY_ID_FORMAT.format(self.entity_id)      
                  
    @property
    def device_class(self):
        """Return the class of this sensor."""
        return DEVICE_CLASS_MOTION

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def is_on(self):
        """Return true if sensor is on."""
        return self._state

    def update(self):
        """Get the latest data and update the state."""
        self._state = self.current_binary_state