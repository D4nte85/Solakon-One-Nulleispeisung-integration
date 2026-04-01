"""Solakon ONE Nulleinspeisung — HACS custom integration."""
from __future__ import annotations

import logging
from pathlib import Path

import voluptuous as vol
from homeassistant.components import websocket_api, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .coordinator import SolakonCoordinator

_LOGGER = logging.getLogger(__name__)
PANEL_JS_URL = "/solakon_nulleinspeisung/panel.js"

# ── WebSocket Commands ───────────────────────────────────────────────────────

@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/get_config",
    vol.Required("entry_id"): str,
})
@websocket_api.async_response
async def _ws_get_config(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    """Sendet die aktuellen Einstellungen an das Panel."""
    coord: SolakonCoordinator = hass.data.get(DOMAIN, {}).get(msg["entry_id"])
    if coord:
        connection.send_result(msg["id"], coord.settings)
    else:
        connection.send_error(msg["id"], "not_found", f"Coordinator for {msg['entry_id']} not found")

@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/save_config",
    vol.Required("entry_id"): str,
    vol.Required("changes"): dict,
})
@websocket_api.async_response
async def _ws_save_config(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    """Speichert Änderungen aus dem Panel."""
    coord: SolakonCoordinator = hass.data.get(DOMAIN, {}).get(msg["entry_id"])
    if coord:
        try:
            await coord.async_update_settings(msg["changes"])
            _LOGGER.info("Solakon Einstellungen erfolgreich gespeichert: %s", msg["changes"])
            connection.send_result(msg["id"], {"success": True})
        except Exception as err:
            _LOGGER.error("Fehler beim Speichern der Solakon Einstellungen: %s", err)
            connection.send_error(msg["id"], "save_failed", str(err))
    else:
        connection.send_error(msg["id"], "not_found", "Coordinator not found")

@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/get_status",
    vol.Required("entry_id"): str,
})
@websocket_api.async_response
async def _ws_get_status(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    """Sendet Live-Daten an das Panel."""
    coord: SolakonCoordinator = hass.data.get(DOMAIN, {}).get(msg["entry_id"])
    if not coord:
        connection.send_error(msg["id"], "not_found", "Coordinator not found")
        return

    cfg = coord.entry.data
    def sv(eid, fallback):
        state = hass.states.get(eid)
        return state.state if state and state.state not in ('unknown', 'unavailable') else fallback

    connection.send_result(msg["id"], {
        "zone":              coord.current_zone,
        "zone_label":        coord.zone_label,
        "mode_label":        coord.mode_label,
        "last_action":       coord.last_action,
        "last_error":        coord.last_error,
        "integral":          round(coord.integral, 2),
        "grid_w":            sv(cfg.get("grid_power_sensor"), "—"),
        "solar_w":           sv(cfg.get("solar_power_sensor"), "—"),
        "output_w":          sv(cfg.get("actual_power_sensor"), "—"),
        "soc_pct":           sv(cfg.get("soc_sensor"), "—"),
    })

# ── Setup ────────────────────────────────────────────────────────────────────

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = SolakonCoordinator(hass, entry)
    await coordinator.async_setup()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # Statische Datei registrieren
    panel_js_file = Path(__file__).parent / "frontend" / "solakon-panel.js"
    await hass.http.async_register_static_paths(
        [StaticPathConfig(PANEL_JS_URL, str(panel_js_file), cache_headers=False)]
    )

    # Panel registrieren
    await panel_custom.async_register_panel(
        hass,
        webcomponent_name="solakon-panel",
        sidebar_title="Solakon ONE",
        sidebar_icon="mdi:solar-power",
        frontend_url_path=DOMAIN,
        module_url=PANEL_JS_URL,
        config={"entry_id": entry.entry_id},
        require_admin=False,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # WebSocket APIs
    websocket_api.async_register_command(hass, _ws_get_config)
    websocket_api.async_register_command(hass, _ws_save_config)
    websocket_api.async_register_command(hass, _ws_get_status)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    from homeassistant.components.frontend import async_remove_panel
    async_remove_panel(hass, DOMAIN)
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
