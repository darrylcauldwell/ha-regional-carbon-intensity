/**
 * UK Carbon Intensity Comparison Card for Home Assistant
 *
 * Shows all 14 UK DNO regions side by side with current intensity,
 * 24h average, and 48h average. User's region is highlighted.
 */

const INTENSITY_COLORS = {
  "very low": "#1B9E77",
  "very_low": "#1B9E77",
  "low": "#66C2A5",
  "moderate": "#FFD92F",
  "high": "#FC8D62",
  "very high": "#E5584F",
  "very_high": "#E5584F",
};

function getIndexFromValue(value) {
  if (value < 40) return "very low";
  if (value < 80) return "low";
  if (value < 180) return "moderate";
  if (value < 280) return "high";
  return "very high";
}

function getColorFromValue(value) {
  return INTENSITY_COLORS[getIndexFromValue(value)] || "#999";
}

function getColorFromIndex(index) {
  if (!index) return "#999";
  return INTENSITY_COLORS[index.toLowerCase()] || "#999";
}

const SORT_MODES = [
  { key: "current", label: "Now" },
  { key: "avg_24h", label: "24h Avg" },
  { key: "avg_48h", label: "48h Avg" },
];

class UKCarbonComparisonCard extends HTMLElement {
  static getConfigElement() {
    return document.createElement("uk-carbon-comparison-card-editor");
  }

  static getStubConfig(hass) {
    const entities = Object.keys(hass.states).filter(
      (e) => e.startsWith("sensor.") && e.endsWith("_regional_comparison")
    );
    return { entity: entities[0] || "" };
  }

  constructor() {
    super();
    this._sortIndex = 0;
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  setConfig(config) {
    this._config = config;
    if (!this._config.entity) {
      this._autoDiscover = true;
    }
  }

  getCardSize() {
    return 10;
  }

  _getEntity() {
    if (!this._hass) return null;
    if (this._config.entity && this._hass.states[this._config.entity]) {
      return this._hass.states[this._config.entity];
    }
    if (this._autoDiscover) {
      const key = Object.keys(this._hass.states).find(
        (e) => e.startsWith("sensor.") && e.endsWith("_regional_comparison")
      );
      if (key) return this._hass.states[key];
    }
    return null;
  }

  _render() {
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
    }

    const entity = this._getEntity();

    if (
      !entity ||
      entity.state === "unavailable" ||
      entity.state === "unknown"
    ) {
      this.shadowRoot.innerHTML = `
        <ha-card>
          <style>
            .unavailable {
              padding: 24px;
              text-align: center;
              color: var(--secondary-text-color);
              font-size: 14px;
            }
          </style>
          <div class="unavailable">
            ${!entity ? "No regional comparison entity found" : "Data unavailable"}
          </div>
        </ha-card>
      `;
      return;
    }

    const attrs = entity.attributes || {};
    const regions = attrs.regions || [];
    const userRegionId = attrs.user_regionid;
    const sortMode = SORT_MODES[this._sortIndex];

    // Sort regions
    const sorted = [...regions].sort((a, b) => {
      const aVal = sortMode.key === "current" ? a.current : a[sortMode.key];
      const bVal = sortMode.key === "current" ? b.current : b[sortMode.key];
      return aVal - bVal;
    });

    this.shadowRoot.innerHTML = `
      <ha-card>
        <style>${this._getStyles()}</style>
        <div class="card-content">
          <div class="header">
            <div class="header-left">
              <svg class="header-icon" viewBox="0 0 24 24">
                <path fill="currentColor"
                  d="M12,2C8.13,2,5,5.13,5,9c0,5.25,7,13,7,13s7-7.75,7-13C19,5.13,15.87,2,12,2z
                     M12,11.5c-1.38,0-2.5-1.12-2.5-2.5s1.12-2.5,2.5-2.5s2.5,1.12,2.5,2.5
                     S13.38,11.5,12,11.5z"/>
              </svg>
              UK Regional Comparison
            </div>
            <button class="sort-btn" id="sort-toggle">
              Sort: ${sortMode.label} ▼
            </button>
          </div>
          <div class="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th class="col-region">Region</th>
                  <th class="col-value">Now</th>
                  <th class="col-value">24h Avg</th>
                  <th class="col-value">48h Avg</th>
                </tr>
              </thead>
              <tbody>
                ${sorted.map((r) => this._renderRow(r, userRegionId)).join("")}
              </tbody>
            </table>
          </div>
        </div>
      </ha-card>
    `;

    this.shadowRoot
      .getElementById("sort-toggle")
      .addEventListener("click", () => {
        this._sortIndex = (this._sortIndex + 1) % SORT_MODES.length;
        this._render();
      });
  }

  _renderRow(region, userRegionId) {
    const isUser = region.regionid === userRegionId;
    const rowClass = isUser ? "region-row user-region" : "region-row";
    const star = isUser ? "★ " : "";
    const currentColor = getColorFromIndex(region.index);
    const avg24Color = getColorFromValue(region.avg_24h);
    const avg48Color = getColorFromValue(region.avg_48h);

    return `
      <tr class="${rowClass}">
        <td class="col-region">${star}${region.shortname}</td>
        <td class="col-value">
          <span class="badge" style="background:${currentColor}">${region.current}</span>
        </td>
        <td class="col-value">
          <span class="badge" style="background:${avg24Color}">${Math.round(region.avg_24h)}</span>
        </td>
        <td class="col-value">
          <span class="badge" style="background:${avg48Color}">${Math.round(region.avg_48h)}</span>
        </td>
      </tr>
    `;
  }

  _getStyles() {
    return `
      :host {
        --ci-text: var(--primary-text-color, #333);
        --ci-text-secondary: var(--secondary-text-color, #666);
        --ci-divider: var(--divider-color, rgba(0,0,0,0.12));
      }
      .card-content {
        padding: 16px;
      }
      .header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 12px;
      }
      .header-left {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 16px;
        font-weight: 500;
        color: var(--ci-text);
      }
      .header-icon {
        width: 24px;
        height: 24px;
        color: #66C2A5;
      }
      .sort-btn {
        background: none;
        border: 1px solid var(--ci-divider);
        border-radius: 6px;
        padding: 4px 10px;
        font-size: 12px;
        color: var(--ci-text-secondary);
        cursor: pointer;
        font-family: inherit;
      }
      .sort-btn:hover {
        background: var(--ci-divider);
      }
      .table-wrapper {
        overflow-x: auto;
      }
      table {
        width: 100%;
        border-collapse: collapse;
        font-size: 13px;
      }
      thead th {
        text-align: center;
        font-size: 11px;
        font-weight: 600;
        color: var(--ci-text-secondary);
        text-transform: uppercase;
        letter-spacing: 0.5px;
        padding: 6px 4px;
        border-bottom: 2px solid var(--ci-divider);
      }
      thead th.col-region {
        text-align: left;
      }
      .region-row td {
        padding: 5px 4px;
        border-bottom: 1px solid var(--ci-divider);
      }
      .col-region {
        text-align: left;
        color: var(--ci-text);
        white-space: nowrap;
      }
      .col-value {
        text-align: center;
        width: 70px;
      }
      .user-region td {
        font-weight: 700;
        background: rgba(102, 194, 165, 0.12);
      }
      .user-region td.col-region {
        color: #1B9E77;
      }
      .badge {
        display: inline-block;
        min-width: 32px;
        padding: 2px 6px;
        border-radius: 8px;
        font-size: 12px;
        font-weight: 600;
        color: #fff;
        text-align: center;
        font-variant-numeric: tabular-nums;
      }
    `;
  }
}

// Card editor
class UKCarbonComparisonCardEditor extends HTMLElement {
  set hass(hass) {
    this._hass = hass;
    if (!this._rendered) this._render();
  }

  setConfig(config) {
    this._config = { ...config };
    if (this._rendered) this._render();
  }

  _render() {
    this._rendered = true;
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
    }
    this.shadowRoot.innerHTML = `
      <style>
        .editor { padding: 16px; }
        label { display: block; margin-bottom: 4px; font-weight: 500; font-size: 14px; }
        input {
          width: 100%;
          padding: 8px;
          border: 1px solid var(--divider-color, #ccc);
          border-radius: 4px;
          box-sizing: border-box;
          font-size: 14px;
          background: var(--card-background-color, #fff);
          color: var(--primary-text-color, #333);
        }
        .hint {
          font-size: 12px;
          color: var(--secondary-text-color, #666);
          margin-top: 4px;
        }
      </style>
      <div class="editor">
        <label>Entity</label>
        <input type="text"
               value="${this._config.entity || ""}"
               placeholder="sensor.uk_carbon_intensity_regional_comparison" />
        <div class="hint">Leave blank to auto-discover</div>
      </div>
    `;

    this.shadowRoot.querySelector("input").addEventListener("input", (e) => {
      this._config = { ...this._config, entity: e.target.value };
      this.dispatchEvent(
        new CustomEvent("config-changed", { detail: { config: this._config } })
      );
    });
  }
}

customElements.define("uk-carbon-comparison-card", UKCarbonComparisonCard);
customElements.define(
  "uk-carbon-comparison-card-editor",
  UKCarbonComparisonCardEditor
);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "uk-carbon-comparison-card",
  name: "UK Carbon Intensity (Regional Comparison)",
  description:
    "Compare carbon intensity across all 14 UK DNO regions with current, 24h and 48h averages.",
  preview: true,
  documentationURL:
    "https://www.home-assistant.io/integrations/uk_carbon_intensity",
});
