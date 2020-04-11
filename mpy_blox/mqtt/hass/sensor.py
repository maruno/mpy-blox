from mpy_blox.mqtt.hass.disco import MQTTDiscoverable


class MQTTSensor(MQTTDiscoverable):
    component_type = 'sensor'

    def __init__(self, name, unit, var_name,
                 device_class=None,
                 discovery_prefix = 'homeassistant'):
        super().__init__(name, discovery_prefix)
        self.unit = unit
        self.var_name = var_name
        self.dev_cls = device_class
        self.state = None
        self.disco_task = None

    @property
    def app_disco_config(self):
        disco_cfg = {
           'unit_of_measurement': self.unit,
           'value_template': "{{ value_json." + self.var_name + " }}"
        }

        if self.dev_cls:
           disco_cfg['device_class'] = self.dev_cls
        
        return disco_cfg

    def set_variable(self, var_value):
        self.var_value = var_value

    @property
    def app_state(self):
        return {
            self.var_name: self.var_value
        }
