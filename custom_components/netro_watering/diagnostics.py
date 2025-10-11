"""Diagnostics support for Netro Watering integration.

This module provides functions to collect and redact diagnostic data for
Netro Watering config entries, including coordinator, entities, and devices.
"""

from __future__ import annotations

from typing import Any

import homeassistant.helpers.device_registry as dr
import homeassistant.helpers.entity_registry as er
from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_SERIAL_NUMBER, DOMAIN

# Keys to automatically redact (values will be replaced with "***")
TO_REDACT = {
    "token",
    "api_key",
    "authorization",
    "Authorization",
    "access_token",
    "refresh_token",
    "password",
    "serial",  # conservative: if a generic "serial" key appears anywhere
    "serial_number",  # explicitly redact serial numbers if present as a field
}


def _safe(obj: Any) -> Any:
    """Return a JSON-serializable representation of obj (fallback to str)."""
    if isinstance(obj, (dict, list, str, int, float, bool)) or obj is None:
        return obj
    try:
        # Try a shallow conversion (e.g., attrs/pydantic-like)
        return dict(obj)  # type: ignore[arg-type]
    except Exception:  # noqa: BLE001 pylint: disable=broad-except
        return str(obj)


def _mask_token(s: str) -> str:
    """Mask a sensitive string keeping the last 2 characters for support correlation."""
    if not s:
        return s
    n = len(s)
    if n <= 2:
        return "★" * n
    return "★" * (n - 2) + s[-2:]


def _scrub_strings(obj: Any, secrets: set[str]) -> Any:
    """Recursively replace any occurrence of provided secrets inside strings.

    This also walks lists/tuples/dicts to scrub nested occurrences,
    which is useful when serial numbers appear inside unique_ids or identifiers.
    """
    if isinstance(obj, str):
        out = obj
        for secret in secrets:
            if not secret:
                continue
            if secret in out:
                out = out.replace(secret, _mask_token(secret))
        return out
    if isinstance(obj, list):
        return [_scrub_strings(x, secrets) for x in obj]
    if isinstance(obj, tuple):
        return tuple(_scrub_strings(list(obj), secrets))
    if isinstance(obj, dict):
        return {k: _scrub_strings(v, secrets) for k, v in obj.items()}
    return obj


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Build a diagnostics payload for a single Netro Watering config entry.

    This report intentionally avoids secrets and masks any discovered serial numbers,
    including those embedded in identifiers/unique_ids.
    """
    # Coordinator is stored directly under hass.data[DOMAIN][entry.entry_id]
    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)

    # --- Collect serial numbers to scrub later (wherever they appear as substrings) ---
    serial_secrets: set[str] = set()

    # From config entry data
    try:
        ce_serial = entry.data.get(CONF_SERIAL_NUMBER)
        if isinstance(ce_serial, (str, int)):
            serial_secrets.add(str(ce_serial))
    except Exception:  # noqa: BLE001 pylint: disable=broad-except
        pass

    # From coordinator attribute
    try:
        coord_serial = getattr(coordinator, "serial_number", None)
        if isinstance(coord_serial, (str, int)):
            serial_secrets.add(str(coord_serial))
    except Exception:  # noqa: BLE001 pylint: disable=broad-except
        pass

    # From device registry identifiers (DOMAIN, serial-like identifiers)
    device_registry = dr.async_get(hass)
    for dev in device_registry.devices.values():
        if entry.entry_id not in dev.config_entries:
            continue
        for dom, ident in dev.identifiers:
            if dom == DOMAIN and isinstance(ident, (str, int)):
                serial_secrets.add(str(ident))

    # --- Coordinator metadata (non-sensitive; serial will be redacted/scrubbed) ---
    coordinator_info: dict[str, Any] = {}
    coordinator_data: Any = None
    if coordinator is not None:
        coordinator_info = {
            "class": coordinator.__class__.__name__,
            "name": getattr(coordinator, "name", None),
            "update_interval": str(getattr(coordinator, "update_interval", None)),
            "last_update_success": getattr(coordinator, "last_update_success", None),
            "last_update_time": str(getattr(coordinator, "last_update_time", None)),
            # These may include serial-like data; they will be redacted/scrubbed later:
            "serial_number": getattr(coordinator, "serial_number", None),
            "device_type": getattr(coordinator, "device_type", None),
            "device_name": getattr(coordinator, "device_name", None),
            "hw_version": getattr(coordinator, "hw_version", None),
            "sw_version": getattr(coordinator, "sw_version", None),
        }
        coordinator_data = _safe(getattr(coordinator, "data", None))

    # --- Entities & devices attached to this entry ---
    entity_registry = er.async_get(hass)
    entities = []
    for ent in entity_registry.entities.values():
        if ent.config_entry_id != entry.entry_id or ent.platform != DOMAIN:
            continue
        state = hass.states.get(ent.entity_id)
        entities.append(
            {
                "entity_id": ent.entity_id,
                "unique_id": ent.unique_id,  # may contain serial; will be scrubbed
                "platform": ent.platform,
                "original_name": ent.original_name,
                "original_device_class": ent.original_device_class,
                "device_id": ent.device_id,
                "disabled_by": ent.disabled_by,
                "capabilities": ent.capabilities,
                "state": None if state is None else state.state,
                "attributes": None if state is None else _safe(state.attributes),
            }
        )

    devices = []
    for dev in device_registry.devices.values():
        if entry.entry_id not in dev.config_entries:
            continue
        # Keep only devices owned by this domain for a compact report
        if not any(idt[0] == DOMAIN for idt in dev.identifiers):
            continue
        devices.append(
            {
                "id": dev.id,  # HA-internal UUID, not sensitive
                "name": dev.name,
                "model": dev.model,
                "manufacturer": dev.manufacturer,
                "hw_version": dev.hw_version,
                "sw_version": dev.sw_version,
                # identifiers may embed serials; will be scrubbed
                "identifiers": [list(x) for x in dev.identifiers],
                "connections": [list(x) for x in dev.connections],
                "via_device_id": dev.via_device_id,  # HA-internal reference
                "area_id": dev.area_id,
            }
        )

    # --- Assemble payload before redaction ---
    payload: dict[str, Any] = {
        "entry": {
            "entry_id": entry.entry_id,
            "domain": entry.domain,
            "title": entry.title,
            "version": entry.version,
            "source": entry.source,
            "unique_id": entry.unique_id,
            "pref_disable_new_entities": entry.pref_disable_new_entities,
            "data": _safe(entry.data),
            "options": _safe(entry.options),
        },
        "coordinator": {
            "info": coordinator_info,
            "data": _safe(coordinator_data),
        },
        "entities": entities,
        "devices": devices,
    }

    # 1) Redact by key names (tokens, passwords, serial_number, etc.)
    payload = async_redact_data(payload, TO_REDACT)

    # 2) Scrub any serial strings discovered earlier wherever they appear in strings
    if serial_secrets:
        payload = _scrub_strings(payload, {str(s) for s in serial_secrets})

    return payload
