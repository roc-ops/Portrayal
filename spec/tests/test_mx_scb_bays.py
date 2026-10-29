"""A Juniper MX chassis seats a Switch Control Board or a Routing Engine carrier only where its hardware guide puts one.

The MX240, MX480 and MX960 guides number the SCB slots apart from the line-card slots: the MX480 has SCB slots 0 and 1 and
DPC/MPC slots 0 to 5 (MX480 guide, pp. 189 and 451), and a line-card bay that accepts `juniper/scb-mx` lets a configuration seat
an SCB where a line card goes. Two slots are shared and take either: the MX240 multifunction slot 1/0 (MX240 guide, pp. 15, 122
and 173) and the MX960 multifunction slot 2/6 (MX960 guide, pp. 32, 81, 144 and 220). Those are the only exceptions.
"""
import pytest

from libdata import devices

# components whose job is control or switching, not traffic: they belong to the SCB, CB or RCB slots
CONTROL_PARTS = {
    "scb-mx", "scbe2-mx", "scbe3-mx", "re-s-1300", "re-s-2000", "mx104-re",
    "mx2000-cb-re-128g-v", "mx2000-cb-re-1800-v", "mx2000-cb-re-v", "mx2008-rcb-v",
}

# (device, bay id) -> the guide page that makes the slot shared
SHARED = {
    ("juniper/mx240", "scb1-dpc0"): "MX240 guide pp. 15, 122, 173 (multifunction slot 1/0 takes a DPC, MPC or SCB)",
    ("juniper/mx960", "fpc6"): "MX960 guide pp. 32, 81, 144, 220 (multifunction slot 2/6 takes a DPC, MPC or SCB)",
}


def _bays(node):
    if isinstance(node, dict):
        if "id" in node and "accepts" in node:
            yield node
        for v in node.values():
            yield from _bays(v)
    elif isinstance(node, list):
        for v in node:
            yield from _bays(v)


def _is_line_card_bay(bay):
    return any(a.split("@")[0].split("/")[1] not in CONTROL_PARTS and not a.split("/")[1].startswith(("mx", "psu"))
               for a in bay["accepts"]) and bay.get("group") not in ("scbs", "craft", "psus", "inlets", "cooling")


MX_DEVICES = [(s, d) for s, d in devices() if s.startswith("juniper/mx") and s != "juniper/mx80"]


@pytest.mark.parametrize("slug,doc", MX_DEVICES, ids=[s for s, _ in MX_DEVICES])
def test_line_card_bays_accept_no_control_board(slug, doc):
    bad = []
    for bay in _bays(doc.get("views", doc)):
        if (slug, bay["id"]) in SHARED or not _is_line_card_bay(bay):
            continue
        held = sorted(a for a in bay["accepts"] if a.split("@")[0].split("/")[1] in CONTROL_PARTS)
        if held:
            bad.append(f"{bay['id']}: {', '.join(held)}")
    assert not bad, f"{slug} line-card bays accept a control board the guide does not seat there: {'; '.join(bad)}"


@pytest.mark.parametrize("slug,bay_id", sorted(SHARED))
def test_shared_slot_still_takes_an_scb(slug, bay_id):
    doc = dict(devices())[slug]
    bay = next(b for b in _bays(doc.get("views", doc)) if b["id"] == bay_id)
    for board in ("juniper/scb-mx@3", "juniper/scbe2-mx@1", "juniper/scbe3-mx@1"):
        assert board in bay["accepts"], f"{slug} {bay_id}: {SHARED[(slug, bay_id)]}"
