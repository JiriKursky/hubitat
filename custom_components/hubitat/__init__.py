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
from homeassistant.const import (CONF_ACCESS_TOKEN, CONF_URL, CONF_ENTITIES)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_call_later, call_later
from homeassistant.util import dt as dt_util
from homeassistant.core import split_entity_id
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers import discovery

HAT_BINARY_SENSOR = 'binary_sensor'
HAT_SWITCH = 'switch'
HUBITAT_ENTITY_ID = 'he_{}'

HUBITAT_TYPEMAP = {
    'Fibaro Motion Sensor ZW5': HAT_BINARY_SENSOR,
    'Fibaro Wall Plug': HAT_SWITCH    
}



ASYNC_TIMEOUT = 20 # Timeout for async courutine
CONF_GATEWAYS = 'gateways'

ATTR_ILLUMINANCE = 'illuminance'
ATTR_TYPE = 'type'

DOMAIN = 'hubitat'

from inspect import currentframe, getframeinfo
_LOGGER = logging.getLogger(__name__)

HUBITAT_CONTROLLERS = 'hubitat_controllers'
HUBITAT_DEVICES = 'hubitat_devices'

HUBITAT_COMPONENTS = [HAT_BINARY_SENSOR, HAT_SWITCH]

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

def check_map(value):
    return value

GATEWAY_CONFIG = vol.Schema({
    vol.Required(CONF_URL): cv.url,
    vol.Required(CONF_ACCESS_TOKEN): cv.string,    
    vol.Optional(CONF_ENTITIES): check_map
}, extra=vol.ALLOW_EXTRA)

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_GATEWAYS): vol.All(cv.ensure_list, [GATEWAY_CONFIG]),
    })
}, extra=vol.ALLOW_EXTRA)

class HubitatController():
    """Initiate Fibaro Controller Class."""

    def __init__(self, hass, config):
        self.client = HubitatClient(hass, config[CONF_URL], config[CONF_ACCESS_TOKEN])
        self.hubitat_devices = None
        self.entity_map = config.get(CONF_ENTITIES)
        self.hub_serial = "1"        

    async def async_connect(self):
        """Start the communication with the Hubitat controller."""                
        
        self.hubitat_devices = defaultdict(list)        
        devices = await self.client.async_read_list()        
        if devices is not None:
            for device in devices:
                hubitat_device = HubitatDevice(device, self)                
                hubitat_type = hubitat_device.get_def(ATTR_TYPE)
                if hubitat_type in HUBITAT_TYPEMAP:
                    ha_type = HUBITAT_TYPEMAP [hubitat_type]
                    self.hubitat_devices[ha_type].append(HubitatDevice(device, self))
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
        self._buffer = None                
        self._loop_instance = 0
        self._loop_start = True

    async def _async_get(self, ask):
        my_debug(ask)        
        websession = async_get_clientsession(self._hass)                
        ret_val = None            
        
        try: 
            with async_timeout.timeout(20):            
                response =  await websession.get(ask)                        
        except:
            response = None
                
        if response is not None:            
            ret_val = await response.json()            
        my_debug(ret_val)        
        return ret_val

    async def _async_get_all_info(self):
        ask = "{}devices/all?access_token={}".format(self._url, self._access_token)        
        response = await self._async_get(ask)
        if response is not None:
            self._buffer = response
        return response

    async def async_read_list(self):                
        response = await self._async_get_all_info()
        ret_val = None
        if response is not None:
            ret_val = []
            for item in response:
                ret_val.append(item)        
        if self._loop_start:
            self._loop_start = False
            async_call_later(self._hass, 5, self._loop)
        return ret_val

    async def async_get_device_info(self, device_id):
        # ask = "{}devices/{}?access_token={}".format(self._url, device_id, self._access_token)        
        
        if self._buffer is not None:            
            for item in self._buffer:
                if item['id'] == device_id:
                    return item
        return None
    
    async def _loop(self, _):        
        await self._async_get_all_info()
        async_call_later(self._hass, 0.2, self._loop)

class HubitatDevice:
    """Representation of a Hubitat device entity. Defined in controller"""

    def __init__(self, hubitat_def, controller):
        self._hubitat_def = hubitat_def        
        self.controller = controller   
        self._device_id = self.get_def('id')
        self._status = None
        self.hass = None
        self.entity_map = controller.entity_map
        self.properties = {'value': 'false', ATTR_ILLUMINANCE: 0}
        
    def get_def(self, key):
        my_debug(self._hubitat_def[key])
        return self._hubitat_def[key]
     
    async def update_status(self):
        response = await self.controller.client.async_get_device_info(self._device_id)        
        if response is not None:                        
            if response is None:
                return
            my_debug(response)
            attributes = response['attributes']
            my_debug(attributes)
            
            if ATTR_ILLUMINANCE in attributes:
                self.properties[ATTR_ILLUMINANCE] = attributes[ATTR_ILLUMINANCE]
            if 'motion' in attributes:
                self.properties['value'] = attributes['motion'] != 'inactive'                                                
            
    def send_command(self, command):
        pass


class HubitatEntity(Entity):
    """Representation of a device entity. Will pass to binary_sensor and others"""

    def __init__(self, hubitat_device):
        """Initialize the device."""        
        self.hubitat_device = hubitat_device  
        self._device_id = hubitat_device.get_def('id')      
        self._name = hubitat_device.get_def('label')
        self._attr = {}
        entity_map = hubitat_device.controller.entity_map
        my_debug(entity_map)
        if self._device_id in entity_map:   
            self.entity_id = entity_map[self._device_id]
        else:
            self.entity_id = HUBITAT_ENTITY_ID.format(self._device_id)
        
        
    async def async_added_to_hass(self):
        """Call when entity is added to hass."""
        my_debug("Entity {} succesfully added".format(self.entity_id))        
        self.hubitat_device.hass = self.hass
        async_call_later(self.hass, 1, self._update_status)

    async def _update_status(self, _):
        await self.hubitat_device.update_status()
        my_debug('Update')
        my_debug(self.hubitat_device.properties)
        self.schedule_update_ha_state(True)
        async_call_later(self.hass, 0.2, self._update_status)

    @property
    def should_poll(self):
        """Get polling requirement from hubitat device."""
        return False        

    @property
    def device_state_attributes(self):
        """Return the state attributes of the device."""
        return self._attr

    @property
    def current_binary_state(self):
        """Return the current binary state."""

        return  self.hubitat_device.properties['value']
    
    def action(self, command):        
        self.hubitat_device.send_command(command)

    def call_turn_on(self):
        """Turn on the Fibaro device."""
        self.action("on")

    def call_turn_off(self):
        """Turn off the Fibaro device."""
        self.action("off")