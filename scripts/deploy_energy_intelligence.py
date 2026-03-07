#!/usr/bin/env python3
"""Deploy the Energy Intelligence dashboard to Home Assistant.

Connects via WebSocket, discovers entities from multiple integrations
(Octopus Energy, SolaX, UK Carbon Intensity), substitutes placeholders
in the dashboard template, and pushes via lovelace/dashboards/create
+ lovelace/config/save.

Usage:
    python3 scripts/deploy_energy_intelligence.py

Requires: pip install websockets pyyaml
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path

try:
    import websockets
except ImportError:
    print("ERROR: websockets package required. Install with: pip3 install websockets")
    sys.exit(1)

try:
    import yaml
except ImportError:
    print("ERROR: pyyaml package required. Install with: pip3 install pyyaml")
    sys.exit(1)

HA_URL = "ws://192.168.1.227:8123/api/websocket"
DASHBOARD_URL_PATH = "energy-intelligence"
DASHBOARD_TITLE = "Energy Intelligence"
DASHBOARD_ICON = "mdi:flash-alert"

# Octopus Energy entity placeholders (same prefix pattern as deploy_dashboard.py)
OCTOPUS_PREFIX = "sensor.octopus_energy_"
OCTOPUS_MAP = {
    # Electricity import
    "OCTOPUS_IMPORT_current_rate": r"(?!.*export).*_current_rate$",
    "OCTOPUS_IMPORT_next_rate": r"(?!.*export).*_next_rate$",
    "OCTOPUS_IMPORT_previous_consumption": r"(?!.*export).*(?<!gas)_previous_(?:accumulative_)?consumption$",
    "OCTOPUS_IMPORT_previous_cost": r"(?!.*export).*(?<!gas)_previous_(?:accumulative_)?cost$",
    "OCTOPUS_IMPORT_standing_charge": r"(?!.*export).*(?<!gas)_(?:current_)?standing_charge$",
    # Electricity export
    "OCTOPUS_EXPORT_export_current_rate": r".*_export_current_rate$",
    "OCTOPUS_EXPORT_export_previous_consumption": r".*_export_previous_(?:accumulative_)?consumption$",
    "OCTOPUS_EXPORT_export_previous_cost": r".*_export_previous_(?:accumulative_)?cost$",
    # Gas
    "OCTOPUS_GAS_gas_previous_cost": r".*(?:gas).*_previous_(?:accumulative_)?cost$",
    "OCTOPUS_GAS_gas_standing_charge": r".*(?:gas).*_(?:current_)?standing_charge$",
    # Entry-level (custom integration only)
    "OCTOPUS_ENTRY_carbon_correlation": r".*_carbon_correlation$",
    "OCTOPUS_ENTRY_tariff_comparison": r".*_tariff_comparison$",
    "OCTOPUS_ENTRY_solar_estimate": r".*_solar_estimate$",
}

# SolaX entity placeholders — prefix discovered from entities matching solax_inverter_*
SOLAX_MAP = {
    "battery_state_of_charge": "battery_state_of_charge",
    "battery_power": "battery_power",
    "grid_power": "grid_power",
    "grid_import_export": "grid_import_export",
    "pv1_power": "pv1_power",
    "pv2_power": "pv2_power",
    "today_pv_energy": "today_pv_energy",
    "total_pv_energy": "total_pv_energy",
    "total_feed_in_energy": "total_feed_in_energy",
    "total_consumption": "total_consumption",
}


def load_token() -> str:
    """Read the HA long-lived access token."""
    token_path = Path(__file__).resolve().parent.parent / ".claude" / "accessToken"
    if not token_path.exists():
        print(f"ERROR: Token file not found at {token_path}")
        sys.exit(1)
    return token_path.read_text().strip()


def load_template() -> str:
    """Load the dashboard YAML template as a string."""
    template_path = (
        Path(__file__).resolve().parent.parent
        / "dashboards"
        / "energy-intelligence.yaml"
    )
    if not template_path.exists():
        print(f"ERROR: Dashboard template not found at {template_path}")
        sys.exit(1)
    return template_path.read_text()


def discover_octopus_entities(entities: list[dict]) -> dict[str, str]:
    """Discover Octopus Energy entities by regex matching."""
    oe_sensors = sorted(
        e["entity_id"]
        for e in entities
        if e["entity_id"].startswith(OCTOPUS_PREFIX)
    )

    if not oe_sensors:
        print("WARNING: No sensor.octopus_energy_* entities found")
        return {}

    print(f"\nOctopus Energy: found {len(oe_sensors)} entities")
    replacements: dict[str, str] = {}

    for placeholder, pattern in OCTOPUS_MAP.items():
        placeholder_full = f"{OCTOPUS_PREFIX}{placeholder}"
        for eid in oe_sensors:
            bare = eid[len(OCTOPUS_PREFIX):]
            if re.match(pattern, bare):
                replacements[placeholder_full] = eid
                print(f"  {placeholder} -> {eid}")
                break
        else:
            print(f"  {placeholder} -> NOT FOUND")

    return replacements


def discover_solax_entities(entities: list[dict]) -> dict[str, str]:
    """Discover SolaX entities by finding the inverter serial prefix."""
    # Find entities from solax_local platform (excludes old Modbus entities)
    solax_sensors = sorted(
        e["entity_id"]
        for e in entities
        if e.get("platform") == "solax_local"
        and e["entity_id"].startswith("sensor.")
    )

    # Fallback: match by known sensor pattern
    if not solax_sensors:
        solax_sensors = sorted(
            e["entity_id"]
            for e in entities
            if re.match(
                r"sensor\.solax_inverter_[a-z0-9]+_battery_state_of_charge$",
                e["entity_id"],
            )
        )

    if not solax_sensors:
        print("\nWARNING: No SolaX custom integration entities found")
        return {}

    # Extract prefix from a known sensor
    for eid in solax_sensors:
        match = re.match(
            r"(sensor\.solax_inverter_[a-z0-9]+_)battery_state_of_charge$", eid
        )
        if match:
            prefix = match.group(1)
            break
    else:
        # Derive prefix from first entity by removing the last segment
        first = solax_sensors[0]
        prefix = first.rsplit("_", 1)[0] + "_"
    print(f"\nSolaX: found {len(solax_sensors)} entities (prefix: {prefix})")

    all_entity_ids = {e["entity_id"] for e in entities}
    replacements: dict[str, str] = {}
    for placeholder, suffix in SOLAX_MAP.items():
        placeholder_full = f"sensor.SOLAX_{placeholder}"
        real_id = f"{prefix}{suffix}"
        if real_id in all_entity_ids:
            replacements[placeholder_full] = real_id
            print(f"  SOLAX_{placeholder} -> {real_id}")
        else:
            print(f"  SOLAX_{placeholder} -> NOT FOUND ({real_id})")

    return replacements


def substitute_template(template: str, replacements: dict[str, str]) -> dict:
    """Replace placeholder entity IDs in the YAML template with real ones."""
    result = template
    for placeholder, real_id in replacements.items():
        result = result.replace(placeholder, real_id)

    # Warn about remaining placeholders
    remaining = re.findall(
        r"sensor\.(?:octopus_energy_OCTOPUS_\w+|SOLAX_\w+)",
        result,
    )
    if remaining:
        unique = sorted(set(remaining))
        print(f"\nWARNING: {len(unique)} unresolved placeholder(s):")
        for p in unique:
            print(f"  {p}")

    return yaml.safe_load(result)


async def deploy(token: str) -> None:
    """Connect to HA WebSocket and deploy the dashboard."""
    msg_id = 1

    async def send(ws, payload: dict) -> dict:
        nonlocal msg_id
        payload["id"] = msg_id
        msg_id += 1
        await ws.send(json.dumps(payload))
        while True:
            resp = json.loads(await ws.recv())
            if resp.get("id") == payload["id"]:
                return resp

    async with websockets.connect(HA_URL) as ws:
        # Auth
        auth_req = json.loads(await ws.recv())
        if auth_req.get("type") != "auth_required":
            print(f"ERROR: Expected auth_required, got {auth_req.get('type')}")
            sys.exit(1)

        await ws.send(json.dumps({"type": "auth", "access_token": token}))
        auth_resp = json.loads(await ws.recv())
        if auth_resp.get("type") != "auth_ok":
            print(f"ERROR: Authentication failed: {auth_resp}")
            sys.exit(1)
        print("Authenticated with Home Assistant")

        # Discover entities
        entity_resp = await send(ws, {"type": "config/entity_registry/list"})
        if not entity_resp.get("success"):
            print(f"ERROR: Failed to list entities: {entity_resp}")
            sys.exit(1)

        all_entities = entity_resp["result"]
        replacements: dict[str, str] = {}
        replacements.update(discover_octopus_entities(all_entities))
        replacements.update(discover_solax_entities(all_entities))

        if not replacements:
            print("\nERROR: No entities discovered from any integration")
            sys.exit(1)

        # Generate final config
        template = load_template()
        dashboard_config = substitute_template(template, replacements)

        # Check if dashboard already exists
        resp = await send(ws, {"type": "lovelace/dashboards/list"})
        if not resp.get("success"):
            print(f"ERROR: Failed to list dashboards: {resp}")
            sys.exit(1)

        existing = [
            d for d in resp["result"] if d.get("url_path") == DASHBOARD_URL_PATH
        ]

        if existing:
            print(
                f"\nDashboard '{DASHBOARD_URL_PATH}' already exists, updating config..."
            )
        else:
            create_resp = await send(
                ws,
                {
                    "type": "lovelace/dashboards/create",
                    "url_path": DASHBOARD_URL_PATH,
                    "title": DASHBOARD_TITLE,
                    "icon": DASHBOARD_ICON,
                    "require_admin": False,
                    "show_in_sidebar": True,
                },
            )
            if not create_resp.get("success"):
                print(f"ERROR: Failed to create dashboard: {create_resp}")
                sys.exit(1)
            print(f"\nCreated dashboard at /{DASHBOARD_URL_PATH}")

        # Save the dashboard config
        save_resp = await send(
            ws,
            {
                "type": "lovelace/config/save",
                "url_path": DASHBOARD_URL_PATH,
                "config": dashboard_config,
            },
        )
        if not save_resp.get("success"):
            print(f"ERROR: Failed to save dashboard config: {save_resp}")
            sys.exit(1)

        print("Dashboard config saved successfully!")
        print(f"View at: http://192.168.1.227:8123/{DASHBOARD_URL_PATH}")


def main() -> None:
    token = load_token()
    asyncio.run(deploy(token))


if __name__ == "__main__":
    main()
