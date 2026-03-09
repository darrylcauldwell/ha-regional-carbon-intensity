#!/usr/bin/env python3
"""Deploy the Monthly Energy Bills dashboard to Home Assistant.

Connects via WebSocket, discovers the tariff_comparison entity ID,
substitutes it into the dashboard template, and pushes via
lovelace/dashboards/create + lovelace/config/save.

Usage:
    python3 scripts/deploy_energy_bills.py

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
DASHBOARD_URL_PATH = "energy-bills"
DASHBOARD_TITLE = "Octopus Monthly Insight"
DASHBOARD_ICON = "mdi:receipt-text"

ENTITY_MAP = {
    "ACCOUNT_tariff_comparison": r".*_tariff_comparison$",
}

PREFIX = "sensor.octopus_energy_"


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
        Path(__file__).resolve().parent.parent / "dashboards" / "energy-bills.yaml"
    )
    if not template_path.exists():
        print(f"ERROR: Dashboard template not found at {template_path}")
        sys.exit(1)
    return template_path.read_text()


def discover_entities(entities: list[dict]) -> dict[str, str]:
    """Map placeholder entity IDs to real entity IDs."""
    oe_sensors = sorted(
        e["entity_id"]
        for e in entities
        if e["entity_id"].startswith(PREFIX)
    )

    if not oe_sensors:
        print("ERROR: No sensor.octopus_energy_* entities found in HA")
        sys.exit(1)

    print(f"Found {len(oe_sensors)} Octopus Energy sensor entities")

    replacements: dict[str, str] = {}

    for placeholder, pattern in ENTITY_MAP.items():
        placeholder_full = f"{PREFIX}{placeholder}"
        matched = False
        for eid in oe_sensors:
            bare = eid[len(PREFIX):]
            if re.match(pattern, bare):
                replacements[placeholder_full] = eid
                print(f"  {placeholder} -> {eid}")
                matched = True
                break
        if not matched:
            print(f"  {placeholder} -> NOT FOUND (cards will show unavailable)")

    return replacements


def substitute_template(template: str, replacements: dict[str, str]) -> dict:
    """Replace placeholder entity IDs in the YAML template with real ones."""
    result = template
    for placeholder, real_id in replacements.items():
        result = result.replace(placeholder, real_id)

    remaining = re.findall(
        r"sensor\.octopus_energy_ACCOUNT_\w+",
        result,
    )
    if remaining:
        unique = sorted(set(remaining))
        print(f"\nWARNING: {len(unique)} unresolved placeholder(s):")
        for p in unique:
            print(f"  {p}")
        print("  Cards referencing these entities will show 'unavailable'")

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
        auth_req = json.loads(await ws.recv())
        if auth_req.get("type") != "auth_required":
            print(f"ERROR: Expected auth_required, got {auth_req.get('type')}")
            sys.exit(1)

        await ws.send(json.dumps({"type": "auth", "access_token": token}))
        auth_resp = json.loads(await ws.recv())
        if auth_resp.get("type") != "auth_ok":
            print(f"ERROR: Authentication failed: {auth_resp}")
            sys.exit(1)
        print("Authenticated with Home Assistant\n")

        entity_resp = await send(ws, {"type": "config/entity_registry/list"})
        if not entity_resp.get("success"):
            print(f"ERROR: Failed to list entities: {entity_resp}")
            sys.exit(1)

        replacements = discover_entities(entity_resp["result"])
        if not replacements:
            print("ERROR: Could not identify any Octopus Energy entities")
            sys.exit(1)

        template = load_template()
        dashboard_config = substitute_template(template, replacements)

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
