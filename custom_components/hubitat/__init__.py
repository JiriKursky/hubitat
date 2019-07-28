"""
Component for interface Hubitat

Tested on under hass.io ver. 0.93.2 

Version 26.7.2019

"""

import logging
from collections import defaultdict
import async_timeout
import os
import sys

import voluptuous as vol
from homeassistant.const import (CONF_ACCESS_TOKEN, CONF_URL)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util
from homeassistant.core import split_entity_id
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers import discovery

ASYNC_TIMEOUT = 20 # Timeout for async courutine
CONF_GATEWAYS = 'gateways'

DOMAIN = 'hubitat'
ENTITY_ID_FORMAT = DOMAIN + '.{}'

from inspect import currentframe, getframeinfo
_LOGGER = logging.getLogger(__name__)

HUBITAT_CONTROLLERS = 'hubitat_controllers'
HUBITAT_DEVICES = 'hubitat_devices'
HUBITAT_COMPONENTS = ['binary_sensor']

def my_debug(s):
    cf = currentframe()
    line = cf.f_back.f_lineno
    if s is None:
            s = ''
    _LOGGER.debug("{} line: {} -> {}".format(DOMAIN, line, s))


# Validation of the user's configuration
CONFIG_SCHEMA = vol.Schema({
    DOMAIN: 
        vol.All({                        
            vol.Required(CONF_URL): cv.string,    
            vol.Required(CONF_ACCESS_TOKEN): cv.string })
    },  extra=vol.ALLOW_EXTRA)

GATEWAY_CONFIG = vol.Schema({
    vol.Required(CONF_URL): cv.url,
    vol.Required(CONF_ACCESS_TOKEN): cv.string,    
}, extra=vol.ALLOW_EXTRA)

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_GATEWAYS): vol.All(cv.ensure_list, [GATEWAY_CONFIG]),
    })
}, extra=vol.ALLOW_EXTRA)

class HubitatController():
    """Initiate Fibaro Controller Class."""

    def __init__(self, hass, config):
        self._client = HubitatClient(hass, config[CONF_URL], config[CONF_ACCESS_TOKEN])
        self.hubitat_devices = None
        self.hub_serial = "1"        

    async def async_connect(self):
        """Start the communication with the Hubitat controller."""                
        
        self.hubitat_devices = defaultdict(list)        
        devices = await self._client.async_read_list()        
        if devices is not None:
            for device in devices:                
                self.hubitat_devices['binary_sensor'].append(HubitatDevice(device, self))
            return True
        return False


async def async_setup(hass, base_config):
    gateways = base_config[DOMAIN][CONF_GATEWAYS]
    hass.data[HUBITAT_CONTROLLERS] = {}
    hass.data[HUBITAT_DEVICES] = {}
    for component in HUBITAT_COMPONENTS:
        hass.data[HUBITAT_DEVICES][component] = []
    for gateway in gateways:
        controller = HubitatController(hass, gateway)        
        if await controller.async_connect():
            hass.data[HUBITAT_CONTROLLERS][controller.hub_serial] = controller
            for component in HUBITAT_COMPONENTS:
                hass.data[HUBITAT_DEVICES][component].extend(
                    controller.hubitat_devices[component])
    if hass.data[HUBITAT_CONTROLLERS]:
        for component in HUBITAT_COMPONENTS:            
            discovery.load_platform(hass, component, DOMAIN, {},
                                    base_config)
    return True
    
class HubitatClient():
    """ Communication with hubitat - belongs to controller """
    def __init__(self, hass, url, access_token):
        self._url = url
        self._access_token = access_token        
        self._hass = hass                

    async def _async_get(self, ask):
        my_debug(ask)        
        websession = async_get_clientsession(self._hass)                
        value = None    
        ret_val = []        
        
        try: 
            with async_timeout.timeout(20):            
                response =  await websession.get(ask)                        
        except:
            response = None
                
        if response is not None:            
            value = await response.json()            
            if value is None:
                return ret_val
        my_debug(value)
        for item in value:
            ret_val.append(item)
            my_debug("Returned id: {}".format(item))                
        return ret_val

    async def async_read_list(self):        
        ask = "{}devices?access_token={}".format(self._url, self._access_token)
        ret_val = await self._async_get(ask)
        return ret_val

    async def async_get_device_info(self, device_id):
        ask = "{}devices/{}?access_token={}".format(self._url, device_id, self._access_token)
        ret_val = await self._async_get(ask)
        return ret_val

class HubitatDevice:
    """Representation of a Hubitat device entity. Defined in controller"""

    def __init__(self, hubitat_def, controller):
        self._hubitat_def = hubitat_def        
        self._controller = controller        
        
    def get_def(self, key):
        my_debug(self._hubitat_def[key])
        return self._hubitat_def[key]

class HubitatEntity(Entity):
    """Representation of a device entity. Will pass to binary_sensor and others"""

    def __init__(self, hubitat_device):
        """Initialize the device."""        
        self.hubitat_device = hubitat_device  
        self._device_id = hubitat_device.get_def('id')      
        self._name = hubitat_device.get_def('label')
        
        
    async def async_added_to_hass(self):
        """Call when entity is added to hass."""
        my_debug("Entity {} succesfully added".format(self.entity_id))        

    @property
    def should_poll(self):
        """Get polling requirement from hubitat device."""
        return False        

    @property
    def device_state_attributes(self):
        """Return the state attributes of the device."""
        attr = {}
        return attr

    @property
    def current_binary_state(self):
        """Return the current binary state."""
        """
        if self.fibaro_device.properties.value == 'false':
            return False
        if self.fibaro_device.properties.value == 'true' or \
                int(self.fibaro_device.properties.value) > 0:
            return True
        """
        return False
