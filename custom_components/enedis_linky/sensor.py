"""Sensors on Linky."""
from datetime import timedelta
import logging
import serial
import threading

_LOGGER = logging.getLogger(__name__)

from homeassistant.components.sensor import (
    DEVICE_CLASS_POWER,
    DEVICE_CLASS_CURRENT,
    # DOMAIN,
)

from homeassistant.util import Throttle

from .const import (
    DOMAIN,
    CONF_DEVICE_PATH,
    CONF_DEVICE_NAME,
    CONF_DOMAIN_DEVICE,
)

from .const import DOMAIN as integration_DOMAIN

from homeassistant.const import (
    CONF_ATTRIBUTE,
    STATE_UNKNOWN,
    ATTR_ATTRIBUTION,
    POWER_WATT,
    POWER_KILO_WATT,
    POWER_VOLT_AMPERE,
    ELECTRIC_CURRENT_AMPERE,
    ENERGY_WATT_HOUR,
)
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.util.temperature import fahrenheit_to_celsius

from homeassistant.components.sensor import SensorEntity

from homeassistant.helpers.entity import Entity

# MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=1)
SCAN_INTERVAL = timedelta(seconds=10)

TELEINFO_AVAILABLE_VALUES = ["HCHC", "HCHP", "IINST", "IMAX", "PAPP", "ISOUSC"]

LINKY_ATTRIBUTES_UNIT = {
                            "PAPP"    : (POWER_VOLT_AMPERE          ,DEVICE_CLASS_POWER        ,"Puissance apparente triphasée soutirée"   ,int),
                            "IINST1"  : (ELECTRIC_CURRENT_AMPERE    ,DEVICE_CLASS_CURRENT      ,"Intensité Instantanée pour la phase 1"    ,int),
                            "IINST2"  : (ELECTRIC_CURRENT_AMPERE    ,DEVICE_CLASS_CURRENT      ,"Intensité Instantanée pour la phase 2"    ,int),
                            "IINST3"  : (ELECTRIC_CURRENT_AMPERE    ,DEVICE_CLASS_CURRENT      ,"Intensité Instantanée pour la phase 3"    ,int),
#                            "ADCO"    : (""     ,""             ,"Adresse du compteur"                      ,str),
#                            "OPTARIF" : (""     , ""            ,"Option tarifaire choisie"                 ,str),
                           "ISOUSC"  : (ELECTRIC_CURRENT_AMPERE    , DEVICE_CLASS_CURRENT     ,"Intensité souscrite"                      ,int),
                            "BASE"    : (ENERGY_WATT_HOUR           ,DEVICE_CLASS_POWER       ,"Index option Base"                        ,int),
#                            "PTEC"    : (""     , ""            ,"Période Tarifaire en cours"               ,str),
                           "IMAX1"   : (ELECTRIC_CURRENT_AMPERE    ,DEVICE_CLASS_CURRENT       ,"Intensité maximale phase 1"               ,int),
                           "IMAX2"   : (ELECTRIC_CURRENT_AMPERE    ,DEVICE_CLASS_CURRENT       ,"Intensité maximale phase 2"               ,int),
                           "IMAX3"   : (ELECTRIC_CURRENT_AMPERE    ,DEVICE_CLASS_CURRENT       ,"Intensité maximale phase 3"               ,int),
                            "PMAX"    : (POWER_WATT                 ,DEVICE_CLASS_POWER       ,"Puissance maximale triphasée atteinte"    ,int),
#                            "HHPHC"   : (""     , ""            ,"Horaire Heures Pleines Heures Creuses"    ,str),
#                            "MOTDETAT": (""     , ""            ,"Mot d'Etat du compteur "                  ,str),
#                            "PPOT"    : (""     , ""            ,"Présence des potentiels"                  ,str),
                            }


# CHANNEL_ST_HUMIDITY_CLUSTER = f"channel_0x{SMARTTHINGS_HUMIDITY_CLUSTER:04x}"
# STRICT_MATCH = functools.partial(ZHA_ENTITIES.strict_match, DOMAIN)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Zigbee Home Automation sensor from config entry."""
    # entities_to_create = hass.data[DATA_ZHA][DOMAIN]

    # unsub = async_dispatcher_connect(
    #     hass,
    #     SIGNAL_ADD_ENTITIES,
    #     functools.partial(
    #         discovery.async_add_entities, async_add_entities, entities_to_create
    #     ),
    # )
    # hass.data[DATA_ZHA][DATA_ZHA_DISPATCHERS].append(unsub)
    print(config_entry.data)

    teleinfo_data = None
    try:
        teleinfo_data = TeleinfoData(hass, config_entry)

    except Exception as err:
        print("Can't connect to teleinfo device: %s", str(err))
        _LOGGER.error("Can't connect to teleinfo device: %s", str(err))
        return False

    hass.data.setdefault(DOMAIN, {})[config_entry.entry_id] = teleinfo_data

    devices = []

    for linly_sensor in LINKY_ATTRIBUTES_UNIT:
        unit_of_measurement, device_class, _, _ = LINKY_ATTRIBUTES_UNIT[linly_sensor]
        devices.append(LinkySensor(linly_sensor, unit_of_measurement, device_class, teleinfo_data))


    async_add_entities(devices)

    return True

async def async_remove_entry(hass, config_entry) -> None:
    """Handle removal of an entry."""
    print("async_remove_entry")
    teleinfo_data = hass.data[DOMAIN][config_entry.entry_id]
    teleinfo_data.close()


class TeleinfoSensor(Entity):
    """Implementation of the Teleinfo sensor."""

    def __init__(self, teleinfo_data, name):
        """Initialize the sensor."""
        self._name = name
        self._unit_of_measurement = None
        self._state = STATE_UNKNOWN
        self._attributes = {}
        self._data = teleinfo_data

        self.manufacturername = "Enedis"
        self.productname = "Linky"
        self.swversion = "1.1.0"
        self.bridgeid = "0X00"

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    # @property
    # def device_info(self):
    #     return {
    #         "identifiers": {
    #             # Serial numbers are unique identifiers within a specific domain
    #             (integration_DOMAIN, self.unique_id)
    #         },
    #         "name": self.name,
    #         "manufacturer": self.manufacturername,
    #         "model": self.productname,
    #         "sw_version": self.swversion,
    #         "via_device": (integration_DOMAIN, self.bridgeid),
    #     }

    @property
    def unique_id(self):
        """Return a unique ID."""
        return "TeleinfoSensor"

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return self._unit_of_measurement

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        self._attributes[ATTR_ATTRIBUTION] = CONF_ATTRIBUTE
        return self._attributes

    def update(self):
        """Get the latest data from Teleinfo device and updates the state."""
        self._data.update()
        if not self._data.frame:
            _LOGGER.warn("Don't receive energy data from Teleinfo!")
            return
        # self._attributes = self._data.frame
        _LOGGER.info("Frame read: %s" % self._data.frame)
        for info in self._data.frame:
            if info["name"] in TELEINFO_AVAILABLE_VALUES:
                self._attributes[info["name"]] = int(info["value"])
            else:
                self._attributes[info["name"]] = info["value"]
        self._state = self._attributes["ADCO"]
        _LOGGER.debug(
            "Sensor: state=%s attributes=%s" % (self._state, self._attributes)
        )


class TeleinfoData(threading.Thread):
    """Get the latest data from Teleinfo."""

    def __init__(self, hass, config):
        """Initialize the data object."""
        self._device = config.data[CONF_DEVICE_PATH]
        self._frame = {}
        self._hass = hass

        self._teleinfo = serial.Serial(
            port=self._device,
            baudrate=1200,                  # 1200 bauds
            bytesize = serial.SEVENBITS,    # 7bits
            parity = serial.PARITY_EVEN,    # parité paire
            stopbits = serial.STOPBITS_ONE, # un bit de stop
            xonxoff = False,                # pas de contrôle de flux
            timeout = 1
            )

        self.connected = False
        threading.Thread.__init__(self,name="TeleinfoData")
        self.stop = False

        self.start()

    @property
    def teleinfo(self):
        """Retour Teleinfo object."""
        return self._teleinfo

    @property
    def frame(self):
        """Retour Teleinfo frame data."""
        return self._frame

    # @Throttle(MIN_TIME_BETWEEN_UPDATES)

    def run(self):
        """get data from Teleinfo device."""
        while not self.stop :
            try:
                buffer = self._teleinfo.readline()
                buffer = buffer.decode('utf-8').rstrip().split(' ')

                if buffer[0] in LINKY_ATTRIBUTES_UNIT:
                    linky_attribute = buffer[0]
                    linky_attribute_value = buffer[1]
                    type_value = LINKY_ATTRIBUTES_UNIT[linky_attribute][3]

                    self._frame[linky_attribute] = type_value(linky_attribute_value) #cast the value to the correct format and store it
                    self.connected = True

            except Exception as e:
                print("Error on TeleinfoData read frame %s " % (e))
                self.connected = False
                break
        #closing...
        self.connected = False

    def close(self):
        self._stop()

    def _stop(self):
        """HA is shutting down, close port."""
        self.stop = True


class LinkySensor(Entity):

    """Representation of a Sensor."""

    # The class of this device. Note the value should come from the homeassistant.const
    # module. More information on the available devices classes can be seen here:
    # https://developers.home-assistant.io/docs/core/entity/sensor
    should_poll = True

    def __init__(self, roller, unit_of_measurement, device_class, teleinfo_data):
        """Initialize the sensor."""
        self._data = teleinfo_data
        self._roller = roller
        self._unit_of_measurement = unit_of_measurement
        self._device_class = device_class

        self.manufacturername = "Enedis"
        self.productname = "Linky"
        self.swversion = "1.1.0"
        self.bridgeid = "0X00"


        self._available = False
        self._state = STATE_UNKNOWN

    # To link this entity to the cover device, this property must return an
    # identifiers value matching that used in the cover, but no other information such
    # as name. If name is returned, this entity will then also become a device in the
    # HA UI.
    @property
    def device_info(self):
        """Return information to link this entity with the correct device."""
        return {
            "identifiers": {
                # Serial numbers are unique identifiers within a specific domain
                (integration_DOMAIN, "DEVICE_ENEDIS_LINKY")
            },
            "name": "Enedis_Linky",
            "manufacturer": self.manufacturername,
            "model": self.productname,
            "sw_version": self.swversion,
            "via_device": (integration_DOMAIN, self.bridgeid),
        }

    # This property is important to let HA know if this entity is online or not.
    # If an entity is offline (return False), the UI will refelect this.
    @property
    def available(self) -> bool:
        """Return True if roller and hub is available."""
        return self._available

    # As per the sensor, this must be a unique value within this domain. This is done
    # by using the device ID, and appending "_battery"
    @property
    def unique_id(self):
        """Return Unique ID string."""
        return self._roller.lower()

    # The value of this sensor. As this is a DEVICE_CLASS_BATTERY, this value must be
    # the battery level as a percentage (between 0 and 100)
    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    # The unit of measurement for this entity. As it's a DEVICE_CLASS_BATTERY, this
    # should be UNIT_PERCENTAGE. A number of units are supported by HA, for some
    # examples, see:
    # https://developers.home-assistant.io/docs/core/entity/sensor#available-device-classes
    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit_of_measurement

    @property
    def device_class(self):
        """Return the device class."""
        return self._device_class

    # The same of this entity, as displayed in the entity UI.
    @property
    def name(self):
        """Return the name of the sensor."""
        return self._roller.upper()

    def setDisconected(self):
        self._state = STATE_UNKNOWN
        self._available = False

    def update(self):
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.

        Get the latest data from Teleinfo device and updates the state.
        """
        if self._data.connected :
            data = self._data.frame
            if data and self._roller in data:
                self._state = data[self._roller]
                self._available = True
            else:
                self.setDisconected()
        else:
            self.setDisconected()

    async def async_will_remove_from_hass(self) -> None:
        """Run when entity will be removed from hass.
        """
        self._data.close()