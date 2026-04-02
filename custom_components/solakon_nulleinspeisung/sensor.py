"""Sensor platform — zone, mode label, last action, grid std dev."""
from __future__ import annotations
from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import DOMAIN
from .coordinator import SolakonCoordinator
from .entity_base import SolakonEntity

_ZONE_ICONS = {
    0: "mdi:solar-power",
    1: "mdi:battery-high",
    2: "mdi:battery-medium",
    3: "mdi:battery-off-outline",
}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback) -> None:
    coord: SolakonCoordinator = hass.data[DOMAIN][entry.entry_id]
    add([
        ZoneSensor(coord),
        ModeTextSensor(coord),
        LastActionSensor(coord),
        GridStdDevSensor(coord),
    ])


class ZoneSensor(SolakonEntity, SensorEntity):
    _attr_name = "Aktuelle Zone"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coord: SolakonCoordinator) -> None:
        super().__init__(coord, "zone")

    @property
    def native_value(self) -> int:
        return self._coordinator.current_zone

    @property
    def icon(self) -> str:
        return _ZONE_ICONS.get(self._coordinator.current_zone, "mdi:layers")

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "zone_label":  self._coordinator.zone_label,
            "last_action": self._coordinator.last_action,
            "last_error":  self._coordinator.last_error,
            "integral":    round(self._coordinator.integral, 2),
        }


class ModeTextSensor(SolakonEntity, SensorEntity):
    """Vom Menschen lesbarer Betriebsmodus."""
    _attr_name = "Betriebsmodus"
    _attr_icon = "mdi:information-outline"

    def __init__(self, coord: SolakonCoordinator) -> None:
        super().__init__(coord, "mode_label")

    @property
    def native_value(self) -> str:
        return self._coordinator.mode_label


class LastActionSensor(SolakonEntity, SensorEntity):
    _attr_name = "Letzte Aktion"
    _attr_icon = "mdi:history"

    def __init__(self, coord: SolakonCoordinator) -> None:
        super().__init__(coord, "last_action")

    @property
    def native_value(self) -> str:
        return self._coordinator.last_action


class GridStdDevSensor(SolakonEntity, SensorEntity):
    """Standardabweichung der Netzleistung über das konfigurierte Zeitfenster."""
    _attr_name = "Netz Standardabweichung"
    _attr_icon = "mdi:chart-bell-curve-cumulative"
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coord: SolakonCoordinator) -> None:
        super().__init__(coord, "grid_stddev")

    @property
    def native_value(self) -> float:
        return self._coordinator.grid_stddev

    @property
    def extra_state_attributes(self) -> dict:
        from .const import S_STDDEV_WINDOW
        return {
            "window_seconds": self._coordinator.settings.get(S_STDDEV_WINDOW, 60),
            "sample_count":   len(self._coordinator._grid_buffer),
        }
