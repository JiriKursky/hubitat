# Hubitat Fibaro Z-Wave

# Interface from HA to Hubitat
See readme for supported devices. Fibaro, Danalock


{% if not installed %}
## Installation

1. Click install.
2. Add platform `hubitat:` to your HA configuration.

```yaml
hubitat:  
  gateways:
    url: http://192.168.0.xx/apps/api/NUM/
    access_token: 80176bjk-3196-47u0-b439-943token
    entities: {"293": "koupelna_pracka_67", "225": "chodba_infra_chodba_133", "321":"garaz_zasuvka_garaz_62"}
```
{% endif %}
