"""
Component for interface Hubitat

Tested on under hass.io ver. 0.93.2 

Version 26.7.2019

"""

import logging
import datetime
from collections import defaultdict
import async_timeout
import os
import sys

import voluptuous as vol
from homeassistant.const import (CONF_ACCESS_TOKEN, CONF_ENTITIES, CONF_SCAN_INTERVAL, CONF_URL)
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
    'Fibaro Wall Plug': HAT_SWITCH,    
    'Virtual Switch': HAT_SWITCH,
    'Generic Z-Wave Lock': HAT_SWITCH
}

HUBITAT_CONTROL_MAP = {
    'Fibaro Motion Sensor ZW5': ['off', 'on'],
    'Fibaro Wall Plug': ['off', 'on'],
    'Virtual Switch': ['off', 'on'],
    'Generic Z-Wave Lock': ['unlock', 'lock']
}

CAP_MOTION_SENSOR = 'MotionSensor'
CAP_SWITCH = 'Switch'
CAP_LOCK = 'Lock'
ATTR_MOTION = 'motion'
ATTR_SWITCH = 'switch'
ATTR_LOCK = 'lock'

HH_MAP_DEVICE = {
    CAP_MOTION_SENSOR: ATTR_MOTION,
    CAP_SWITCH: ATTR_SWITCH,
    CAP_LOCK: ATTR_LOCK
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

FIB_STATES_ON = ['on', '1', 'active', 'true', 'locked', 'lock']

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
            vol.Required(CONF_ACCESS_TOKEN): cv.string,
            vol.Optional(CONF_SCAN_INTERVAL, default = 15): cv.positive_int })
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
    """Initiate Hubitat Controller Class."""

    def __init__(self, hass, config):
        scan_interval = config.get(CONF_SCAN_INTERVAL)
        if scan_interval is None: scan_interval = 15
        self.client = HubitatClient(hass, config[CONF_URL], config[CONF_ACCESS_TOKEN], scan_interval)
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
    def __init__(self, hass, url, access_token, scan_interval):
        self._url = url
        self._access_token = access_token        
        self._hass = hass
        self._buffer = None          
        self._command = {}      
        self._loop_instance = 0
        self._loop_start = True
        self._scan_interval = scan_interval

    async def _async_get(self, ask):
        # my_debug(ask)        
        websession = async_get_clientsession(self._hass)                
        ret_val = None            
        
        try: 
            with async_timeout.timeout(ASYNC_TIMEOUT):            
                response =  await websession.get(ask)                        
        except:
            response = None
                
        if response is not None:            
            ret_val = await response.json()            
        # my_debug(ret_val)        
        return ret_val

    def send_command(self, device_id, command):        
        self._command = { 'device_id': device_id, 'command': command }

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
            async_call_later(self._hass, self._scan_interval, self._loop)
        return ret_val

    async def async_get_device_info(self, device_id):
        # ask = "{}devices/{}?access_token={}".format(self._url, device_id, self._access_token)        
        
        if self._buffer is not None:            
            for item in self._buffer:
                if item['id'] == device_id:
                    return item
        return None
    
    async def _loop(self, _):        
        if self._command:
            # http://192.168.0.77/apps/api/194/devices/[Device ID]/commands?access_token=80176acf-3196-43c0-b439-943bc5be81ad
            ask = "{}devices/{}/{}?access_token={}".format(self._url, self._command['device_id'], self._command['command'],self._access_token)        
            my_debug(ask)
            await self._async_get(ask)
            self._command = {}
        await self._async_get_all_info()
        async_call_later(self._hass, 3, self._loop)



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
        self._was_change = True
        self._last_change = datetime.datetime.now()         

    def get_def(self, key):        
        return self._hubitat_def[key]
     
    async def update_status(self):        
        if self._was_change:
            just_now = datetime.datetime.now()
            dif = (just_now - self._last_change).total_seconds()
            if dif < 15.0:
                my_debug("Entity id: {} too early {}".format(self._device_id, dif))
                return
        response = await self.controller.client.async_get_device_info(self._device_id)  
        self._was_change = False
        self.properties['value']  = '0'

        if response is None:
                return            
            
        capabilities = response['capabilities']                        
        attributes = response['attributes']                        
        if ATTR_ILLUMINANCE in attributes:
            self.properties[ATTR_ILLUMINANCE] = attributes[ATTR_ILLUMINANCE]

        if CAP_MOTION_SENSOR in capabilities:                
            key = HH_MAP_DEVICE[CAP_MOTION_SENSOR]
            self.properties['value'] = attributes[key]
            return

        if CAP_LOCK in capabilities:              
            key = HH_MAP_DEVICE[CAP_LOCK]              
            self.properties['value'] = attributes[key]
            return        

        if CAP_SWITCH in capabilities:
            key = HH_MAP_DEVICE[CAP_SWITCH]
            self.properties['value'] = attributes[key]
            return
            
    def _reset_wait(self):
        self._was_change = True
        self._last_change = datetime.datetime.now() 

    def send_command(self, command):
        self._reset_wait()        
        self.controller.client.send_command(self._device_id, command)        

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
        dev_type = hubitat_device.get_def('type')
        if dev_type in HUBITAT_CONTROL_MAP:
            self._command_off = HUBITAT_CONTROL_MAP[dev_type][0]
            self._command_on = HUBITAT_CONTROL_MAP[dev_type][1]
        else:
            self._command_off = 'off'
            self._command_on = 'on'
    
        
        
    async def async_added_to_hass(self):
        """Call when entity is added to hass."""
        my_debug("Entity {} succesfully added".format(self.entity_id))        
        self.hubitat_device.hass = self.hass
        async_call_later(self.hass, 1, self._update_status)

    async def _update_status(self, _):
        await self.hubitat_device.update_status()        
        self.schedule_update_ha_state(True)
        async_call_later(self.hass, 1, self._update_status)

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
        if self.hubitat_device.properties['value'] in FIB_STATES_ON:
            return True
        else: 
            return False
        
    def action(self, command):        
        my_debug(command)
        self.hubitat_device.send_command(command)

    def call_turn_on(self):
        """Turn on the Fibaro device."""
        self.hubitat_device.properties['value'] = self._command_on
        self.action(self._command_on)

    def call_turn_off(self):
        """Turn off the Fibaro device."""
        self.hubitat_device.properties['value'] = self._command_off
        self.action(self._command_off)