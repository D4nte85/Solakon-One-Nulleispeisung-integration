"""Config flow — only the 9 required Solakon entities. Everything else in sidebar."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_GRID_SENSOR, CONF_ACTUAL_SENSOR, CONF_SOLAR_SENSOR,
    CONF_SOC_SENSOR, CONF_TIMEOUT_COUNTDOWN, CONF_ACTIVE_POWER,
    CONF_DISCHARGE_CURRENT, CONF_TIMEOUT_SET, CONF_MODE_SELECT,
    REQUIRED_ENTITY_DEFAULTS,
)


def _schema(current: dict) -> vol.Schema:
    def _ent(domain: str, device_class: str | None = None) -> selector.EntitySelector:
        spec: dict = {"domain": domain}
        if device_class:
            spec["device_class"] = device_class
        # Nutze das dict-Format für den Selector, das ist im Config Flow oft am robustesten
        return selector.selector({"entity": spec})

    d = REQUIRED_ENTITY_DEFAULTS
    return vol.Schema({
        vol.Required(CONF_GRID_SENSOR,
                     default=current.get(CONF_GRID_SENSOR, "")): _ent("sensor", "power"),

        vol.Required(CONF_ACTUAL_SENSOR,
                     default=current.get(CONF_ACTUAL_SENSOR, d.get(CONF_ACTUAL_SENSOR, ""))): _ent("sensor", "power"),

        vol.Required(CONF_SOLAR_SENSOR,
                     default=current.get(CONF_SOLAR_SENSOR, d.get(CONF_SOLAR_SENSOR, ""))): _ent("sensor", "power"),

        vol.Required(CONF_SOC_SENSOR,
                     default=current.get(CONF_SOC_SENSOR, d.get(CONF_SOC_SENSOR, ""))): _ent("sensor", "battery"),

        # Fernsteuerung: Countdown (Meist ein reiner Sensor, evtl. device_class "duration" falls Solakon das so liefert)
        vol.Required(CONF_TIMEOUT_COUNTDOWN,
                     default=current.get(CONF_TIMEOUT_COUNTDOWN, d.get(CONF_TIMEOUT_COUNTDOWN, ""))): _ent("sensor"),

        # Fernsteuerung: Aktive Leistung (Number, gefiltert nach 'power')
        vol.Required(CONF_ACTIVE_POWER,
                     default=current.get(CONF_ACTIVE_POWER, d.get(CONF_ACTIVE_POWER, ""))): _ent("number", "power"),

        # Fernsteuerung: Entladestrom (Number, gefiltert nach 'current')
        vol.Required(CONF_DISCHARGE_CURRENT,
                     default=current.get(CONF_DISCHARGE_CURRENT, d.get(CONF_DISCHARGE_CURRENT, ""))): _ent("number", "current"),

        # Fernsteuerung: Timeout setzen (Number, meist ohne spezifische device_class)
        vol.Required(CONF_TIMEOUT_SET,
                     default=current.get(CONF_TIMEOUT_SET, d.get(CONF_TIMEOUT_SET, ""))): _ent("number"),

        # Fernsteuerung: Modus Auswahl (Select)
        vol.Required(CONF_MODE_SELECT,
                     default=current.get(CONF_MODE_SELECT, d.get(CONF_MODE_SELECT, ""))): _ent("select"),
    })


class SolakonConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Single-step config flow — just required entities. All params configured in sidebar."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> config_entries.FlowResult:
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            return self.async_create_entry(
                title="Solakon ONE Nulleinspeisung",
                data=user_input,
            )

        return self.async_show_form(
            step_id="user",
            data_schema=_schema({}),
            description_placeholders={
                "hint": "Alle weiteren Parameter (PI, Zonen, AC Laden, Tarif …) werden im Sidebar-Panel konfiguriert."
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(entry: config_entries.ConfigEntry) -> "SolakonOptionsFlow":
        return SolakonOptionsFlow(entry)


class SolakonOptionsFlow(config_entries.OptionsFlow):
    """Options flow — lets the user update entity assignments if hardware changes."""

    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self._entry = entry

    async def async_step_init(self, user_input: dict | None = None) -> config_entries.FlowResult:
        current = {**self._entry.data, **self._entry.options}
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=_schema(current),
        )
