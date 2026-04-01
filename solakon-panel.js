// Solakon ONE Nulleinspeisung — Sidebar Panel
// Lit-based custom element registered as "solakon-panel"

const ZONE_COLORS = {
  0: "#f0ad4e",  // amber — surplus
  1: "#28a745",  // green — zone 1
  2: "#17a2b8",  // teal — zone 2
  3: "#dc3545",  // red  — zone 3
};

const ZONE_LABELS = {
  0: "Zone 0 — Überschuss-Einspeisung",
  1: "Zone 1 — Aggressive Entladung",
  2: "Zone 2 — Batterieschonend",
  3: "Zone 3 — Sicherheitsstopp",
};

const ZONE_ICONS = {
  0: "☀️", 1: "🔋", 2: "🔋", 3: "⛔",
};

class SolakonPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = null;
    this._config = null;
    this._entryId = null;
    this._pollInterval = null;
  }

  setConfig(config) {
    this._config = config;
    this._entryId = config?.entry_id ?? null;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._rendered) {
      this._render();
      this._rendered = true;
      this._startPolling();
    } else {
      this._update();
    }
  }

  connectedCallback() {
    this._startPolling();
  }

  disconnectedCallback() {
    this._stopPolling();
  }

  _startPolling() {
    if (this._pollInterval) return;
    this._pollInterval = setInterval(() => this._update(), 2000);
  }

  _stopPolling() {
    if (this._pollInterval) {
      clearInterval(this._pollInterval);
      this._pollInterval = null;
    }
  }

  // ── State helpers ─────────────────────────────────────────────────────────
  _stateVal(entityId, fallback = "—") {
    if (!this._hass || !entityId) return fallback;
    const s = this._hass.states[entityId];
    return s ? s.state : fallback;
  }

  _stateNum(entityId, decimals = 0, unit = "") {
    const v = parseFloat(this._stateVal(entityId, "0"));
    if (isNaN(v)) return "—";
    return v.toFixed(decimals) + (unit ? " " + unit : "");
  }

  _isOn(entityId) {
    return this._stateVal(entityId, "off") === "on";
  }

  // ── Find integration entities by unique_id pattern ─────────────────────────
  _findEntity(suffix) {
    if (!this._hass) return null;
    for (const [id, state] of Object.entries(this._hass.states)) {
      const uid = state.attributes?.unique_id;
      if (uid && this._entryId && uid === `${this._entryId}_${suffix}`) {
        return id;
      }
    }
    // Fallback: search by domain + object_id pattern
    const candidates = Object.keys(this._hass.states).filter(
      id => id.includes("solakon") && id.endsWith(suffix.replace(/_/g, "_"))
    );
    return candidates[0] ?? null;
  }

  _findEntities() {
    if (!this._hass || !this._entryId) return {};

    // Collect all entities belonging to our device
    const result = {};
    for (const [id, state] of Object.entries(this._hass.states)) {
      const uid = state.attributes?.unique_id ?? "";
      if (!uid.startsWith(this._entryId)) continue;

      if (uid.endsWith("_zone"))                result.zone = id;
      if (uid.endsWith("_last_action"))          result.lastAction = id;
      if (uid.endsWith("_integral"))             result.integral = id;
      if (uid.endsWith("_cycle_active"))         result.cycleActive = id;
      if (uid.endsWith("_surplus_active"))       result.surplusActive = id;
      if (uid.endsWith("_ac_charge_active"))     result.acActive = id;
      if (uid.endsWith("_tariff_charge_active")) result.tariffActive = id;
    }
    return result;
  }

  // ── Open integration config page ──────────────────────────────────────────
  _openConfig() {
    if (this._hass) {
      this._hass.callService("frontend", "navigate", {
        path: `/config/integrations/integration/solakon_nulleinspeisung`,
      });
    }
    history.pushState(null, "", `/config/integrations/integration/solakon_nulleinspeisung`);
    window.dispatchEvent(new CustomEvent("location-changed"));
  }

  // ── Render helpers ────────────────────────────────────────────────────────
  _badge(label, value, color = "var(--primary-color)") {
    return `
      <div class="badge" style="border-left: 4px solid ${color}">
        <span class="badge-label">${label}</span>
        <span class="badge-value">${value}</span>
      </div>`;
  }

  _pill(label, active, color = "#28a745") {
    const bg = active ? color : "var(--secondary-background-color)";
    const fg = active ? "#fff" : "var(--secondary-text-color)";
    return `<span class="pill" style="background:${bg};color:${fg}">${label}</span>`;
  }

  // ── Full render (first time) ───────────────────────────────────────────────
  _render() {
    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; font-family: var(--paper-font-body1_-_font-family, sans-serif); }

        .panel {
          max-width: 800px;
          margin: 0 auto;
          padding: 16px;
        }

        h1 {
          font-size: 1.4rem;
          font-weight: 600;
          color: var(--primary-text-color);
          margin: 0 0 4px 0;
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .subtitle {
          font-size: 0.85rem;
          color: var(--secondary-text-color);
          margin: 0 0 20px 0;
        }

        .card {
          background: var(--card-background-color, #fff);
          border-radius: 12px;
          box-shadow: var(--ha-card-box-shadow, 0 2px 8px rgba(0,0,0,.1));
          padding: 16px 20px;
          margin-bottom: 14px;
        }

        .card-title {
          font-size: 0.75rem;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: .06em;
          color: var(--secondary-text-color);
          margin: 0 0 12px 0;
        }

        .zone-banner {
          border-radius: 10px;
          padding: 18px 20px;
          margin-bottom: 14px;
          display: flex;
          align-items: center;
          gap: 14px;
        }

        .zone-icon { font-size: 2rem; }

        .zone-info { flex: 1; }
        .zone-name { font-size: 1.1rem; font-weight: 700; color: #fff; }
        .zone-sub  { font-size: 0.82rem; color: rgba(255,255,255,.85); }

        .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        .grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; }

        .badge {
          background: var(--secondary-background-color);
          border-radius: 8px;
          padding: 10px 14px;
          display: flex;
          flex-direction: column;
          gap: 2px;
        }
        .badge-label { font-size: 0.72rem; color: var(--secondary-text-color); text-transform: uppercase; letter-spacing: .04em; }
        .badge-value { font-size: 1.1rem; font-weight: 600; color: var(--primary-text-color); }

        .pills { display: flex; flex-wrap: wrap; gap: 8px; }
        .pill {
          border-radius: 20px;
          padding: 4px 12px;
          font-size: 0.8rem;
          font-weight: 600;
        }

        .action-text {
          font-size: 0.9rem;
          color: var(--primary-text-color);
          font-style: italic;
        }

        .cfg-btn {
          width: 100%;
          padding: 12px;
          border: none;
          border-radius: 8px;
          background: var(--primary-color);
          color: var(--text-primary-color, #fff);
          font-size: 0.95rem;
          font-weight: 600;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
          transition: opacity .15s;
        }
        .cfg-btn:hover { opacity: .88; }

        .divider { border: none; border-top: 1px solid var(--divider-color); margin: 12px 0; }
      </style>

      <div class="panel">
        <h1>⚡ Solakon ONE</h1>
        <p class="subtitle">Nulleinspeisung — PI-Regler mit SOC-Zonensteuerung</p>

        <div id="zone-banner" class="zone-banner card">Lädt…</div>

        <div class="grid-2">
          <div class="card" id="card-power">
            <div class="card-title">Leistung</div>
            <div id="power-badges"></div>
          </div>
          <div class="card" id="card-soc">
            <div class="card-title">Batterie & SOC</div>
            <div id="soc-badges"></div>
          </div>
        </div>

        <div class="card">
          <div class="card-title">Zustand</div>
          <div class="pills" id="status-pills"></div>
          <hr class="divider"/>
          <div class="card-title" style="margin-top:8px">Letzte Aktion</div>
          <div class="action-text" id="last-action">—</div>
        </div>

        <div class="card">
          <div class="card-title">PI-Regler</div>
          <div id="pi-badges"></div>
        </div>

        <div class="card">
          <button class="cfg-btn" id="cfg-btn">
            ⚙️ Einstellungen öffnen
          </button>
        </div>
      </div>
    `;

    this.shadowRoot.getElementById("cfg-btn").addEventListener("click", () => this._openConfig());
    this._update();
  }

  // ── Incremental update ────────────────────────────────────────────────────
  _update() {
    if (!this._hass || !this.shadowRoot.getElementById("zone-banner")) return;

    const ents = this._findEntities();

    // Zone
    const zoneNum = parseInt(this._stateVal(ents.zone, "3"), 10) || 3;
    const zoneColor = ZONE_COLORS[zoneNum] ?? "#6c757d";
    const zoneBanner = this.shadowRoot.getElementById("zone-banner");
    zoneBanner.style.background = `linear-gradient(135deg, ${zoneColor}dd, ${zoneColor}99)`;
    zoneBanner.innerHTML = `
      <div class="zone-icon">${ZONE_ICONS[zoneNum] ?? "❓"}</div>
      <div class="zone-info">
        <div class="zone-name">${ZONE_LABELS[zoneNum] ?? "Unbekannt"}</div>
        <div class="zone-sub">Zone ${zoneNum}</div>
      </div>
    `;

    // Status pills
    const pillsEl = this.shadowRoot.getElementById("status-pills");
    pillsEl.innerHTML = [
      this._pill("Zyklus aktiv",  this._isOn(ents.cycleActive),   "#28a745"),
      this._pill("Überschuss",    this._isOn(ents.surplusActive),  "#f0ad4e"),
      this._pill("AC Laden",      this._isOn(ents.acActive),       "#0066cc"),
      this._pill("Tarif-Laden",   this._isOn(ents.tariffActive),   "#1a7f1a"),
    ].join("");

    // Last action
    const laEl = this.shadowRoot.getElementById("last-action");
    laEl.textContent = this._stateVal(ents.lastAction, "—");

    // PI integral
    const piEl = this.shadowRoot.getElementById("pi-badges");
    const integralVal = parseFloat(this._stateVal(ents.integral, "0")).toFixed(1);
    const integralPct = Math.min(100, Math.abs(parseFloat(integralVal)) / 10);
    piEl.innerHTML = `
      <div class="badge" style="border-left: 4px solid var(--primary-color)">
        <span class="badge-label">Integral</span>
        <span class="badge-value">${integralVal}</span>
      </div>
    `;

    // Try to show grid / solar / output if we can find the sensors from config
    // (best-effort — these are the inverter sensors, not integration entities)
    const powerEl = this.shadowRoot.getElementById("power-badges");
    powerEl.innerHTML = `<div class="grid-2">
      <div class="badge" style="border-left:4px solid #e53935">
        <span class="badge-label">Netz</span>
        <span class="badge-value" id="v-grid">—</span>
      </div>
      <div class="badge" style="border-left:4px solid #ff9800">
        <span class="badge-label">PV</span>
        <span class="badge-value" id="v-solar">—</span>
      </div>
      <div class="badge" style="border-left:4px solid #4caf50">
        <span class="badge-label">WR-Ausgang</span>
        <span class="badge-value" id="v-output">—</span>
      </div>
      <div class="badge" style="border-left:4px solid #2196f3">
        <span class="badge-label">Modus</span>
        <span class="badge-value" id="v-mode">—</span>
      </div>
    </div>`;

    const socEl = this.shadowRoot.getElementById("soc-badges");
    socEl.innerHTML = `<div class="grid-2">
      <div class="badge" style="border-left:4px solid #7b1fa2">
        <span class="badge-label">SOC</span>
        <span class="badge-value" id="v-soc">—</span>
      </div>
      <div class="badge" style="border-left:4px solid #795548">
        <span class="badge-label">Integral</span>
        <span class="badge-value">${integralVal}</span>
      </div>
    </div>`;

    // Fill live sensor values if available from hass states
    // We try common entity IDs as fallback
    const tryFill = (elId, candidates, unit = " W") => {
      const el = this.shadowRoot.getElementById(elId);
      if (!el) return;
      for (const cand of candidates) {
        const s = this._hass.states[cand];
        if (s && !["unknown","unavailable"].includes(s.state)) {
          const v = parseFloat(s.state);
          el.textContent = isNaN(v) ? s.state : v.toFixed(0) + unit;
          return;
        }
      }
    };

    tryFill("v-soc",    ["sensor.solakon_one_batterie_ladestand"], " %");
    tryFill("v-solar",  ["sensor.solakon_one_pv_leistung"]);
    tryFill("v-output", ["sensor.solakon_one_leistung"]);

    const modeEl = this.shadowRoot.getElementById("v-mode");
    if (modeEl) {
      const modeMap = { "0": "Disabled", "1": "Entladen", "3": "Laden" };
      const s = this._hass.states["select.solakon_one_modus_fernsteuern"];
      modeEl.textContent = s ? (modeMap[s.state] ?? s.state) : "—";
    }
  }
}

customElements.define("solakon-panel", SolakonPanel);
window.customPanels = window.customPanels || [];
window.customPanels.push({
  name: "solakon-panel",
  url: "/solakon_nulleinspeisung/panel.js",
  embed_iframe: false,
});
