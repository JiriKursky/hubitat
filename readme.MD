Homeassistant interface to Hubitat

# Look at the releases

supported Z-Wave devices:
- Fibaro Motion Sensor ZW5
- Fibaro Wall Plug
- Generic Z-Wave Lock (tested on Danalock)
- Virtual Switch

Using API interface. It is working but not fast. Using of switch on / switch off is slow - 10 seconds.

```yaml
hubitat:  
  gateways:
    url: http://192.168.0.xx/apps/api/NUM/
    access_token: 80176acf-3196-43c7-b439-943token
    scan_interval: 20
    entities: {"293": "bathroom_light", "225": "corridor_motion", "321":"garage_wall_plug"}
```
<link href="https://fonts.googleapis.com/css?family=Lato&subset=latin,latin-ext" rel="stylesheet"><a class="bmc-button" target="_blank" href="https://www.buymeacoffee.com/JiriKursky"><img src="https://bmc-cdn.nyc3.digitaloceanspaces.com/BMC-button-images/BMC-btn-logo.svg" alt="Buy me a coffee"><span style="margin-left:5px">Buy me a coffee</span></a>
