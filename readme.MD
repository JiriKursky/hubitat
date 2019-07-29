Homeassistant interface to Hubitat

# Look at the releases

supported Z-Wave devices:
- Fibaro Motion Sensor ZW5
- Fibaro Wall Plug

Using API interface. It is working but not fast. Using of switch on / switch off is slow - 10 seconds.

```yaml
hubitat:  
  gateways:
    url: http://192.168.0.xx/apps/api/NUM/
    access_token: 80176acf-3196-43c0-b439-943token
    entities: {"293": "koupelna_pracka_67", "225": "chodba_infra_chodba_133", "321":"garaz_zasuvka_garaz_62"}
```

