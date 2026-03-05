/**
 * UK Carbon Intensity Card for Home Assistant
 *
 * A custom Lovelace card that displays UK carbon intensity data
 * with a gauge, forecast timeline, and generation mix donut chart.
 *
 * Uses Lit (bundled with HA) for rendering. No external dependencies.
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

const FUEL_COLORS = {
  wind: "#26A69A",
  solar: "#FFD600",
  nuclear: "#7E57C2",
  gas: "#EF5350",
  biomass: "#8D6E63",
  imports: "#78909C",
  hydro: "#42A5F5",
  coal: "#424242",
  other: "#BDBDBD",
};

const FUEL_ORDER = [
  "gas",
  "wind",
  "biomass",
  "nuclear",
  "imports",
  "solar",
  "hydro",
  "coal",
  "other",
];

function getIntensityColor(index) {
  if (!index) return "#999";
  return INTENSITY_COLORS[index.toLowerCase()] || "#999";
}

function formatIndex(index) {
  if (!index) return "";
  return index.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatTime(isoStr) {
  const d = new Date(isoStr);
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

class UKCarbonIntensityCard extends HTMLElement {
  static getConfigElement() {
    return document.createElement("uk-carbon-intensity-card-editor");
  }

  static getStubConfig(hass) {
    const entities = Object.keys(hass.states).filter(
      (e) =>
        e.startsWith("sensor.") && e.endsWith("_regional_carbon_intensity")
    );
    return { entity: entities[0] || "" };
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  setConfig(config) {
    this._config = config;
    if (!this._config.entity) {
      // Auto-discover
      this._autoDiscover = true;
    }
  }

  getCardSize() {
    return 6;
  }

  _getEntity() {
    if (!this._hass) return null;
    if (this._config.entity && this._hass.states[this._config.entity]) {
      return this._hass.states[this._config.entity];
    }
    if (this._autoDiscover) {
      const key = Object.keys(this._hass.states).find(
        (e) =>
          e.startsWith("sensor.") && e.endsWith("_regional_carbon_intensity")
      );
      if (key) return this._hass.states[key];
    }
    return null;
  }

  _getNationalEntity() {
    if (!this._hass) return null;
    const key = Object.keys(this._hass.states).find(
      (e) =>
        e.startsWith("sensor.") && e.endsWith("_national_carbon_intensity")
    );
    return key ? this._hass.states[key] : null;
  }

  _render() {
    const entity = this._getEntity();

    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
    }

    if (!entity || entity.state === "unavailable" || entity.state === "unknown") {
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
            ${!entity ? "No UK Carbon Intensity entity found" : "Data unavailable"}
          </div>
        </ha-card>
      `;
      return;
    }

    const attrs = entity.attributes || {};
    const intensity = parseInt(entity.state, 10);
    const index = attrs.region
      ? this._getRegionalIndex()
      : "";
    const region = attrs.region || "";
    const forecast = attrs.forecast || [];
    const generationmix = attrs.generationmix || [];
    const national = this._getNationalEntity();
    const nationalIntensity = national ? parseInt(national.state, 10) : null;
    const nationalIndex = this._getNationalIndex();

    // Compute low-carbon and fossil percentages
    const lowCarbonFuels = ["wind", "solar", "nuclear", "hydro", "biomass"];
    const fossilFuels = ["gas", "coal", "other"];
    let lowCarbon = 0;
    let fossil = 0;
    for (const g of generationmix) {
      if (lowCarbonFuels.includes(g.fuel)) lowCarbon += g.perc;
      if (fossilFuels.includes(g.fuel)) fossil += g.perc;
    }

    // Find lowest forecast period
    let lowestPeriod = null;
    if (forecast.length > 0) {
      lowestPeriod = forecast.reduce((min, p) =>
        p.forecast < min.forecast ? p : min
      );
    }

    this.shadowRoot.innerHTML = `
      <ha-card>
        <style>${this._getStyles()}</style>
        <div class="card-content">
          ${this._renderHeader(region)}
          ${this._renderGaugeRow(
            intensity,
            index,
            nationalIntensity,
            nationalIndex,
            lowestPeriod,
            lowCarbon,
            fossil
          )}
          ${forecast.length > 0 ? this._renderForecast(forecast) : ""}
          ${generationmix.length > 0 ? this._renderGenerationMix(generationmix) : ""}
        </div>
      </ha-card>
    `;
  }

  _getRegionalIndex() {
    if (!this._hass) return "";
    const key = Object.keys(this._hass.states).find(
      (e) => e.startsWith("sensor.") && e.endsWith("_regional_carbon_index")
    );
    return key ? this._hass.states[key].state : "";
  }

  _getNationalIndex() {
    if (!this._hass) return "";
    const key = Object.keys(this._hass.states).find(
      (e) => e.startsWith("sensor.") && e.endsWith("_national_carbon_index")
    );
    return key ? this._hass.states[key].state : "";
  }

  _getStyles() {
    return `
      :host {
        --ci-bg: var(--ha-card-background, var(--card-background-color, #fff));
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
        margin-bottom: 16px;
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
      .region-label {
        font-size: 13px;
        color: var(--ci-text-secondary);
        font-weight: 400;
      }
      .gauge-row {
        display: flex;
        align-items: center;
        gap: 24px;
        margin-bottom: 16px;
      }
      .gauge-container {
        flex-shrink: 0;
      }
      .stats-panel {
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 6px;
        font-size: 13px;
        color: var(--ci-text);
        min-width: 0;
      }
      .stat-row {
        display: flex;
        align-items: center;
        gap: 6px;
        white-space: nowrap;
      }
      .stat-label {
        color: var(--ci-text-secondary);
      }
      .stat-badge {
        display: inline-block;
        padding: 1px 6px;
        border-radius: 8px;
        font-size: 11px;
        font-weight: 500;
        color: #fff;
      }
      .section {
        border-top: 1px solid var(--ci-divider);
        padding-top: 12px;
        margin-top: 12px;
      }
      .section-title {
        font-size: 12px;
        font-weight: 500;
        color: var(--ci-text-secondary);
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 8px;
      }
      .forecast-chart {
        width: 100%;
        overflow: hidden;
      }
      .forecast-chart svg {
        width: 100%;
        display: block;
      }
      .mix-row {
        display: flex;
        align-items: flex-start;
        gap: 16px;
      }
      .donut-container {
        flex-shrink: 0;
      }
      .mix-legend {
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 4px;
        font-size: 12px;
        min-width: 0;
      }
      .legend-item {
        display: flex;
        align-items: center;
        gap: 6px;
      }
      .legend-swatch {
        width: 10px;
        height: 10px;
        border-radius: 2px;
        flex-shrink: 0;
      }
      .legend-fuel {
        flex: 1;
        color: var(--ci-text);
        text-transform: capitalize;
      }
      .legend-perc {
        color: var(--ci-text-secondary);
        min-width: 38px;
        text-align: right;
      }
      .legend-bar-bg {
        width: 50px;
        height: 6px;
        background: var(--ci-divider);
        border-radius: 3px;
        overflow: hidden;
        flex-shrink: 0;
      }
      .legend-bar-fill {
        height: 100%;
        border-radius: 3px;
      }
    `;
  }

  _renderHeader(region) {
    return `
      <div class="header">
        <div class="header-left">
          <svg class="header-icon" viewBox="0 0 24 24">
            <path fill="currentColor"
              d="M12,2C6.48,2,2,6.48,2,12s4.48,10,10,10,10-4.48,10-10S17.52,2,12,2Z
                 M12,20c-4.41,0-8-3.59-8-8s3.59-8,8-8,8,3.59,8,8-3.59,8-8,8Z
                 M12.5,7H11v6l5.25,3.15.75-1.23-4.5-2.67Z"/>
          </svg>
          UK Carbon Intensity
        </div>
        ${region ? `<span class="region-label">${region}</span>` : ""}
      </div>
    `;
  }

  _renderGaugeRow(
    intensity,
    index,
    nationalIntensity,
    nationalIndex,
    lowestPeriod,
    lowCarbon,
    fossil
  ) {
    const color = getIntensityColor(index);
    const gauge = this._renderGaugeSVG(intensity, index, color);

    const natBadge =
      nationalIntensity !== null
        ? `<span class="stat-badge" style="background:${getIntensityColor(nationalIndex)}">${formatIndex(nationalIndex)}</span>`
        : "";
    const lowestText = lowestPeriod
      ? `${lowestPeriod.forecast} at ${formatTime(lowestPeriod.from)}`
      : "N/A";
    const lowestBadge = lowestPeriod
      ? `<span class="stat-badge" style="background:${getIntensityColor(lowestPeriod.index)}">${formatIndex(lowestPeriod.index)}</span>`
      : "";

    return `
      <div class="gauge-row">
        <div class="gauge-container">${gauge}</div>
        <div class="stats-panel">
          <div class="stat-row">
            <span class="stat-label">National:</span>
            <strong>${nationalIntensity !== null ? nationalIntensity : "N/A"}</strong>
            ${natBadge}
          </div>
          <div class="stat-row">
            <span class="stat-label">Lowest:</span>
            <strong>${lowestText}</strong>
            ${lowestBadge}
          </div>
          <div class="stat-row">
            <span style="color:#66C2A5">&#9881;</span>
            <span class="stat-label">Low carbon:</span>
            <strong>${lowCarbon.toFixed(1)}%</strong>
          </div>
          <div class="stat-row">
            <span style="color:#EF5350">&#9881;</span>
            <span class="stat-label">Fossil:</span>
            <strong>${fossil.toFixed(1)}%</strong>
          </div>
        </div>
      </div>
    `;
  }

  _renderGaugeSVG(value, index, color) {
    // Arc gauge: 180-degree arc from -90 to 90
    const maxVal = 500;
    const clamped = Math.min(Math.max(value, 0), maxVal);
    const pct = clamped / maxVal;
    const r = 50;
    const cx = 60;
    const cy = 60;

    // Arc path helper (SVG arc from startAngle to endAngle in degrees)
    const arcPath = (startDeg, endDeg, radius) => {
      const startRad = ((startDeg - 90) * Math.PI) / 180;
      const endRad = ((endDeg - 90) * Math.PI) / 180;
      const x1 = cx + radius * Math.cos(startRad);
      const y1 = cy + radius * Math.sin(startRad);
      const x2 = cx + radius * Math.cos(endRad);
      const y2 = cy + radius * Math.sin(endRad);
      const large = endDeg - startDeg > 180 ? 1 : 0;
      return `M ${x1} ${y1} A ${radius} ${radius} 0 ${large} 1 ${x2} ${y2}`;
    };

    // Background arc: -135 to 135 (270 degrees)
    const startAngle = -135;
    const endAngle = 135;
    const range = endAngle - startAngle;
    const valueAngle = startAngle + range * pct;

    return `
      <svg width="120" height="90" viewBox="0 0 120 90">
        <!-- Background arc -->
        <path d="${arcPath(startAngle, endAngle, r)}"
              fill="none" stroke="var(--ci-divider)" stroke-width="8"
              stroke-linecap="round"/>
        <!-- Value arc -->
        ${
          pct > 0
            ? `<path d="${arcPath(startAngle, valueAngle, r)}"
              fill="none" stroke="${color}" stroke-width="8"
              stroke-linecap="round"/>`
            : ""
        }
        <!-- Value text -->
        <text x="${cx}" y="${cy - 4}" text-anchor="middle"
              font-size="22" font-weight="700"
              fill="var(--ci-text)">${value}</text>
        <!-- Index label -->
        <text x="${cx}" y="${cy + 14}" text-anchor="middle"
              font-size="11" font-weight="500"
              fill="${color}">${formatIndex(index)}</text>
      </svg>
    `;
  }

  _renderForecast(forecast) {
    // Bar chart: each period is a bar colored by index
    const svgW = 480;
    const svgH = 80;
    const barGap = 1;
    const n = forecast.length;
    const barW = Math.max((svgW - (n - 1) * barGap) / n, 2);
    const maxVal = Math.max(...forecast.map((p) => p.forecast), 100);
    const topPad = 4;
    const bottomPad = 18;
    const chartH = svgH - topPad - bottomPad;

    let bars = "";
    for (let i = 0; i < n; i++) {
      const p = forecast[i];
      const x = i * (barW + barGap);
      const h = (p.forecast / maxVal) * chartH;
      const y = topPad + chartH - h;
      const col = getIntensityColor(p.index);
      bars += `<rect x="${x}" y="${y}" width="${barW}" height="${h}" fill="${col}" rx="1"/>`;
    }

    // Time labels (show ~5 evenly spaced)
    let labels = "";
    const labelCount = Math.min(6, n);
    const step = Math.floor(n / labelCount);
    for (let i = 0; i < n; i += step) {
      const p = forecast[i];
      const x = i * (barW + barGap) + barW / 2;
      labels += `<text x="${x}" y="${svgH - 2}" text-anchor="middle"
                       font-size="9" fill="var(--ci-text-secondary)">${formatTime(p.from)}</text>`;
    }

    const totalW = n * (barW + barGap) - barGap;

    return `
      <div class="section">
        <div class="section-title">24h Forecast</div>
        <div class="forecast-chart">
          <svg viewBox="0 0 ${totalW} ${svgH}" preserveAspectRatio="none">
            ${bars}
            ${labels}
          </svg>
        </div>
      </div>
    `;
  }

  _renderGenerationMix(generationmix) {
    // Sort by percentage descending, filter to non-zero
    const sorted = FUEL_ORDER
      .map((fuel) => {
        const match = generationmix.find((g) => g.fuel === fuel);
        return match || { fuel, perc: 0 };
      })
      .filter((g) => g.perc > 0);

    const donut = this._renderDonutSVG(sorted);
    const maxPerc = Math.max(...sorted.map((g) => g.perc), 1);

    let legendItems = "";
    for (const g of sorted) {
      const col = FUEL_COLORS[g.fuel] || "#BDBDBD";
      const barPct = (g.perc / maxPerc) * 100;
      legendItems += `
        <div class="legend-item">
          <div class="legend-swatch" style="background:${col}"></div>
          <span class="legend-fuel">${g.fuel}</span>
          <span class="legend-perc">${g.perc.toFixed(1)}%</span>
          <div class="legend-bar-bg">
            <div class="legend-bar-fill" style="width:${barPct}%;background:${col}"></div>
          </div>
        </div>
      `;
    }

    return `
      <div class="section">
        <div class="section-title">Generation Mix</div>
        <div class="mix-row">
          <div class="donut-container">${donut}</div>
          <div class="mix-legend">${legendItems}</div>
        </div>
      </div>
    `;
  }

  _renderDonutSVG(fuels) {
    const cx = 50;
    const cy = 50;
    const r = 38;
    const innerR = 24;
    const total = fuels.reduce((s, g) => s + g.perc, 0);
    if (total === 0) return "";

    let segments = "";
    let startAngle = -90;

    for (const g of fuels) {
      const sweep = (g.perc / total) * 360;
      if (sweep < 0.5) continue;
      const endAngle = startAngle + sweep;
      const startRad = (startAngle * Math.PI) / 180;
      const endRad = (endAngle * Math.PI) / 180;

      const x1o = cx + r * Math.cos(startRad);
      const y1o = cy + r * Math.sin(startRad);
      const x2o = cx + r * Math.cos(endRad);
      const y2o = cy + r * Math.sin(endRad);
      const x1i = cx + innerR * Math.cos(endRad);
      const y1i = cy + innerR * Math.sin(endRad);
      const x2i = cx + innerR * Math.cos(startRad);
      const y2i = cy + innerR * Math.sin(startRad);

      const large = sweep > 180 ? 1 : 0;
      const col = FUEL_COLORS[g.fuel] || "#BDBDBD";

      segments += `<path d="M ${x1o} ${y1o}
                            A ${r} ${r} 0 ${large} 1 ${x2o} ${y2o}
                            L ${x1i} ${y1i}
                            A ${innerR} ${innerR} 0 ${large} 0 ${x2i} ${y2i}
                            Z"
                        fill="${col}"/>`;
      startAngle = endAngle;
    }

    return `
      <svg width="100" height="100" viewBox="0 0 100 100">
        ${segments}
      </svg>
    `;
  }
}

// Card editor for the visual editor
class UKCarbonIntensityCardEditor extends HTMLElement {
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
               placeholder="sensor.uk_carbon_intensity_regional_carbon_intensity" />
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

customElements.define("uk-carbon-intensity-card", UKCarbonIntensityCard);
customElements.define(
  "uk-carbon-intensity-card-editor",
  UKCarbonIntensityCardEditor
);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "uk-carbon-intensity-card",
  name: "UK Carbon Intensity",
  description:
    "Displays UK carbon intensity with gauge, forecast timeline, and generation mix.",
  preview: true,
  documentationURL:
    "https://www.home-assistant.io/integrations/uk_carbon_intensity",
});
