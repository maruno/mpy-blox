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

    @property
    def app_disco_config(self):
        return {
           'device_class': self.dev_cls,
           'unit_of_measurement': self.unit,
           'value_template': "{{ value_json." + self.var_name + "}}"
        }

    def set_variable(self, var_value):
        self.var_value = var_value

    @property
    def app_state(self):
        return {
            self.var_name: self.var_value
        }