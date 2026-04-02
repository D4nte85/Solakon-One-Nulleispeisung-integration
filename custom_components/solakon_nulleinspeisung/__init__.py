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

_LOGGER = logging.getLogger(__name__)
PANEL_JS_URL = "/solakon_nulleinspeisung/panel.js"


# ── WebSocket Commands ────────────────────────────────────────────────────────

@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/get_config",
    vol.Required("entry_id"): str,
})
@websocket_api.async_response
async def _ws_get_config(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    coord = hass.data.get(DOMAIN, {}).get(msg["entry_id"])
    if coord:
        connection.send_result(msg["id"], coord.settings)
    else:
        connection.send_error(msg["id"], "not_found", "Coordinator not found")


@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/save_config",
    vol.Required("entry_id"): str,
    vol.Required("changes"): dict,
})
@websocket_api.async_response
async def _ws_save_config(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    coord = hass.data.get(DOMAIN, {}).get(msg["entry_id"])
    if coord:
        await coord.async_update_settings(msg["changes"])
        connection.send_result(msg["id"], {"success": True})
    else:
        connection.send_error(msg["id"], "not_found", "Coordinator not found")


@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/get_status",
    vol.Required("entry_id"): str,
})
@websocket_api.async_response
async def _ws_get_status(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    coord = hass.data.get(DOMAIN, {}).get(msg["entry_id"])
    if not coord:
        connection.send_error(msg["id"], "not_found", "Coordinator not found")
        return

    cfg = coord.entry.data

    def sv(eid: str, fb: str) -> str:
        s = hass.states.get(eid)
        return s.state if s and s.state not in ("unknown", "unavailable") else fb

    connection.send_result(msg["id"], {
        "zone":        coord.current_zone,
        "zone_label":  coord.zone_label,
        "mode_label":  coord.mode_label,
        "last_action": coord.last_action,
        "last_error":  coord.last_error,
        "integral":    round(coord.integral, 2),
        "grid_w":      sv(cfg.get("grid_power_sensor", ""), "—"),
        "solar_w":     sv(cfg.get("solar_power_sensor", ""), "—"),
        "soc_pct":     sv(cfg.get("soc_sensor", ""), "—"),
        "stddev":      coord.grid_stddev,
    })


# BUG FIX: Fehlender reset_integral Handler — Panel-Button hatte keinen Empfänger
@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/reset_integral",
    vol.Required("entry_id"): str,
})
@websocket_api.async_response
async def _ws_reset_integral(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    coord = hass.data.get(DOMAIN, {}).get(msg["entry_id"])
    if coord:
        coord.reset_integral()
        connection.send_result(msg["id"], {"success": True})
    else:
        connection.send_error(msg["id"], "not_found", "Coordinator not found")


# ── Setup ─────────────────────────────────────────────────────────────────────

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    from .coordinator import SolakonCoordinator
    coordinator = SolakonCoordinator(hass, entry)
    await coordinator.async_setup()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    panel_js_file = Path(__file__).parent / "frontend" / "solakon-panel.js"
    await hass.http.async_register_static_paths(
        [StaticPathConfig(PANEL_JS_URL, str(panel_js_file), False)]
    )

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

    websocket_api.async_register_command(hass, _ws_get_config)
    websocket_api.async_register_command(hass, _ws_save_config)
    websocket_api.async_register_command(hass, _ws_get_status)
    websocket_api.async_register_command(hass, _ws_reset_integral)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    from homeassistant.components.frontend import async_remove_panel

    # Sample-Task des Coordinators sauber beenden
    coord = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if coord:
        await coord.async_unload()

    async_remove_panel(hass, DOMAIN)
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unloaded
