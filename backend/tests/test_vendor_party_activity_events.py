"""Iter 113: VendorParty activity event emission tests."""
from __future__ import annotations

import pytest

from tests.conftest import make_test_vendor


async def _make_party(client, vendor_id: str, *, role: str = "SELLER") -> dict:
    resp = await client.post(
        f"/api/v1/vendors/{vendor_id}/parties",
        json={
            "role": role,
            "legal_name": "Event Test Party",
            "address": "Event Ave",
            "country": "SG",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _last_activity(client, entity_id: str) -> dict | None:
    resp = await client.get(f"/api/v1/activity/?limit=50")
    if resp.status_code != 200:
        return None
    events = resp.json()
    for ev in events:
        if ev.get("entity_id") == entity_id:
            return ev
    return None


@pytest.mark.asyncio
async def test_party_added_event_emitted(authenticated_client) -> None:
    vendor = await make_test_vendor(authenticated_client)
    party = await _make_party(authenticated_client, vendor["id"])

    # Verify via direct DB query pattern (activity_log row)
    resp = await authenticated_client.get(f"/api/v1/activity/?limit=100")
    assert resp.status_code == 200
    events = resp.json()
    added_events = [
        e for e in events
        if e.get("event") == "VENDOR_PARTY_ADDED" and e.get("entity_id") == party["id"]
    ]
    assert len(added_events) == 1
    ev = added_events[0]
    assert ev["entity_type"] == "VENDOR_PARTY"
    assert ev["target_role"] == "SM"


@pytest.mark.asyncio
async def test_party_updated_event_emitted(authenticated_client) -> None:
    vendor = await make_test_vendor(authenticated_client)
    party = await _make_party(authenticated_client, vendor["id"])

    await authenticated_client.patch(
        f"/api/v1/vendors/{vendor['id']}/parties/{party['id']}",
        json={"legal_name": "Updated Name"},
    )

    resp = await authenticated_client.get(f"/api/v1/activity/?limit=100")
    events = resp.json()
    updated_events = [
        e for e in events
        if e.get("event") == "VENDOR_PARTY_UPDATED" and e.get("entity_id") == party["id"]
    ]
    assert len(updated_events) == 1
    assert updated_events[0]["target_role"] == "SM"


@pytest.mark.asyncio
async def test_party_removed_event_emitted(authenticated_client) -> None:
    vendor = await make_test_vendor(authenticated_client)
    party = await _make_party(authenticated_client, vendor["id"])
    party_id = party["id"]

    await authenticated_client.delete(
        f"/api/v1/vendors/{vendor['id']}/parties/{party_id}"
    )

    resp = await authenticated_client.get(f"/api/v1/activity/?limit=100")
    events = resp.json()
    removed_events = [
        e for e in events
        if e.get("event") == "VENDOR_PARTY_REMOVED" and e.get("entity_id") == party_id
    ]
    assert len(removed_events) == 1
    assert removed_events[0]["target_role"] == "SM"
    assert removed_events[0]["entity_type"] == "VENDOR_PARTY"
