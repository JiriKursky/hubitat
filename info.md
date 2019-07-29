# Hubitat

# Interface from HA to Hubitat
Just now supporting only two Z-Wave Fibaro devices. Motion and Wall plug


{% if not installed %}
## Installation

1. Click install.
2. Add platform `hubitat:` to your HA configuration.

```yaml
hubitat:  
  gateways:
    url: http://192.168.0.xx/apps/api/NUM/
    access_token: 80176acf-3196-43c0-b439-943token
    entities: {"293": "koupelna_pracka_67", "225": "chodba_infra_chodba_133", "321":"garaz_zasuvka_garaz_62"}
```
{% endif %}
