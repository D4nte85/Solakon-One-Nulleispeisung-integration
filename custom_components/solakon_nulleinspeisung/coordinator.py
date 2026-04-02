"""Coordinator — all zone/PI/offset logic + settings management."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.storage import Store

from .const import (
    DOMAIN, STORAGE_VERSION, SETTINGS_DEFAULTS,
    CONF_GRID_SENSOR, CONF_ACTUAL_SENSOR, CONF_SOLAR_SENSOR,
    CONF_SOC_SENSOR, CONF_TIMEOUT_COUNTDOWN, CONF_ACTIVE_POWER,
    CONF_DISCHARGE_CURRENT, CONF_TIMEOUT_SET, CONF_MODE_SELECT,
    S_P_FACTOR, S_I_FACTOR, S_TOLERANCE, S_WAIT_TIME,
    S_ZONE1_LIMIT, S_ZONE3_LIMIT, S_DISCHARGE_MAX,
    S_OFFSET_1, S_OFFSET_2, S_PV_RESERVE, S_HARD_LIMIT,
    S_SURPLUS_ENABLED, S_SURPLUS_SOC_THRESHOLD, S_SURPLUS_SOC_HYST, S_SURPLUS_PV_HYST,
    S_AC_ENABLED, S_AC_SOC_TARGET, S_AC_POWER_LIMIT, S_AC_HYSTERESIS,
    S_AC_OFFSET, S_AC_P_FACTOR, S_AC_I_FACTOR,
    S_TARIFF_ENABLED, S_TARIFF_PRICE_SENSOR, S_TARIFF_CHEAP_THRESHOLD,
    S_TARIFF_EXP_THRESHOLD, S_TARIFF_SOC_TARGET, S_TARIFF_POWER,
    S_NIGHT_ENABLED
)

_LOGGER = logging.getLogger(__name__)

class SolakonCoordinator:
    """Zentrale Logik-Klasse zur Steuerung der Nulleinspeisung."""

    def __init__(self, hass: HomeAssistant, entry: Any) -> None:
        self.hass = hass
        self.entry = entry
        self.settings = SETTINGS_DEFAULTS.copy()
        self._store = Store(hass, STORAGE_VERSION, f"{DOMAIN}_{entry.entry_id}")
        
        # Laufzeit-Zustände (Runtime States)
        self.current_zone = 2
        self.zone_label = "Initialisierung..."
        self.mode_label = "Warten auf Daten"
        self.last_action = "Keine"
        self.last_error = ""
        self.integral = 0.0
        
        # Status-Flags für Sensoren/Switches
        self.cycle_active = False
        self.surplus_active = False
        self.ac_charge_active = False
        self.tariff_charge_active = False
        
        self._listeners = []

    async def async_setup(self) -> None:
        """Initialisiert den Coordinator und lädt gespeicherte Einstellungen."""
        stored = await self._store.async_load()
        if stored:
            # Bestehende Werte mit Defaults mergen (falls Felder in const.py neu dazukamen)
            self.settings = {**SETTINGS_DEFAULTS, **stored}
            _LOGGER.debug("Solakon: Einstellungen aus Speicher geladen")
        else:
            self.settings = SETTINGS_DEFAULTS.copy()
            _LOGGER.info("Solakon: Keine Speicherdatei gefunden, nutze Standardwerte")

        # Startwert für das Integral aus dem Helper lesen, falls möglich
        cfg = self.entry.data
        int_state = self.hass.states.get(cfg.get(CONF_ACTIVE_POWER, ""))
        if int_state and int_state.state not in ("unknown", "unavailable"):
            try:
                self.integral = float(int_state.state)
            except ValueError:
                self.integral = 0.0

    async def async_update_settings(self, changes: dict[str, Any]) -> None:
        """Wird vom WebSocket aufgerufen, wenn im Panel 'Speichern' geklickt wird."""
        self.settings.update(changes)
        await self._store.async_save(self.settings)
        _LOGGER.info("Solakon: Einstellungen erfolgreich gespeichert")
        self.notify_listeners()

    def register_entity_listener(self, cb: Callable[[], None]) -> None:
        """Registriert HA-Entitäten (Sensoren), damit sie bei Updates triggern."""
        self._listeners.append(cb)

    def unregister_entity_listener(self, cb: Callable[[], None]) -> None:
        """Entfernt Registrierung."""
        if cb in self._listeners:
            self._listeners.remove(cb)

    def notify_listeners(self) -> None:
        """Aktualisiert alle verknüpften Entitäten in HA."""
        for cb in self._listeners:
            cb()

    def reset_integral(self) -> None:
        """Setzt den I-Anteil des Reglers zurück."""
        self.integral = 0.0
        self.last_action = "Integral manuell zurückgesetzt"
        self.notify_listeners()

    # --- Hilfsfunktionen für die Berechnung ---

    def _flt(self, entity_id: str, default: float = 0.0) -> float:
        """Holt einen Float-Wert sicher aus einem HA State."""
        state = self.hass.states.get(entity_id)
        if state is None or state.state in ("unknown", "unavailable"):
            return default
        try:
            return float(state.state)
        except ValueError:
            return default

    def _get_mode(self) -> str:
        """Liest den aktuellen Betriebsmodus vom Wechselrichter (select)."""
        state = self.hass.states.get(self.entry.data.get(CONF_MODE_SELECT, ""))
        return state.state if state else "unknown"

    # HIER KÖNNTE DEINE RECHENLOGIK (PI-REGELUNG) EINGEFÜGT WERDEN
    # Die Methode async_loop() oder ähnlich würde dann periodisch triggern.
