from __future__ import annotations

import os
from pathlib import Path

from opportunity_longitudinal import OpportunityMemory


root = Path(os.environ["OIE_STATE_DIR"])
memory = OpportunityMemory(root / "lifecycle_guard.sqlite")
event = memory.create_event({
    "first_seen_time": "2026-01-02T10:00:00Z",
    "symbol": "GUARD",
    "market": "US",
    "theme": "PIT guard",
    "price": 100,
    "snapshot": {},
})
event_id = event["event_id"]

# Backdated evidence cannot rewrite the episode timeline.
assert not memory.record_state(event_id, "PROVING", observed_at_utc="2026-01-01T10:00:00Z")
assert memory.states_frame(event_id).shape[0] == 1

# A terminal episode cannot be resurrected under the same immutable identity.
assert memory.record_state(event_id, "INVALIDATED", observed_at_utc="2026-01-03T10:00:00Z")
assert not memory.record_state(event_id, "HIGH_CONVICTION", observed_at_utc="2026-01-04T10:00:00Z")
assert memory.events_frame(active_only=True).empty

# A genuine recurrence receives a new identity and first-seen timestamp.
second = memory.create_event({
    "first_seen_time": "2026-02-01T10:00:00Z",
    "symbol": "GUARD",
    "market": "US",
    "theme": "PIT guard",
    "price": 120,
    "snapshot": {},
})
assert second["event_id"] != event_id
assert second["first_seen_time"].startswith("2026-02-01")

print("TEST_LIFECYCLE_PIT_GUARDS_V33_PASS")
