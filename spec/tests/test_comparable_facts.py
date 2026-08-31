"""The comparison layer, and the three rules it exists to enforce.

THE BUG THAT PROMPTED IT. A side-by-side of the MX204 and the S9510-28DC
printed "Max draw: 280 vs 137" - which reads as the UfiSpace box drawing half
what the Juniper does. It draws more: 306 W on DC and 301.2 on AC, under
`power-max-dc-w` and `power-max-ac-w`. The comparison asked for `power-max-w`,
did not find it, and reached for the nearest key that looked close, which was
the TYPICAL figure.

That is worth being precise about, because it decides what these tests guard.
The defect was not a missing number. It was a wrong number, produced by a
lookup that preferred an answer to no answer - and a reader had no way to see
it. So the tests below care less about coverage than about refusal: what the
resolver must decline to say.
"""
import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "spec" / "tools" / "portrayal"))
import comparable as F  # noqa: E402

LIB = ROOT / "library"


def dev(attrs=None, chassis=None, groups=None):
    return {"kind": "device", "name": "d",
            "chassis": chassis or {},
            "attrs": attrs or {},
            "groups": groups or {}}


def vals(res, name):
    return [r["value"] for r in res.get(name, {}).get("readings", [])]


# ---- rule 1: never fall back across concepts --------------------------------

def test_a_device_with_only_a_typical_figure_states_NO_peak():
    """THE REGRESSION. Absent means absent. The one thing the resolver must
    never do is answer a question about maximum draw with a typical figure."""
    res = F.resolve(dev({"power": {"power-typical-w": 137}}))
    assert "peak-power-w" not in res
    assert vals(res, "typical-power-w") == [137.0]


def test_a_split_ac_dc_maximum_is_both_readings_and_not_a_guess():
    """The S9510-28DC. Neither figure is "the" maximum, so it resolves to two
    readings carrying their basis rather than one number picked by the tool."""
    res = F.resolve(dev({"power": {"power-max-ac-w": 301.2, "power-max-dc-w": 306}}))
    got = {(r.get("basis"), r["value"]) for r in res["peak-power-w"]["readings"]}
    assert got == {("ac", 301.2), ("dc", 306.0)}


def test_no_fact_shares_a_source_key_with_another():
    """Rule 1 held structurally rather than by discipline. If two facts could
    ever claim one spelling, a fallback between concepts becomes expressible -
    which is how `typical` came to answer for `max` in the first place."""
    seen = {}
    for f in F.FACTS:
        for key, _, _ in f.sources:
            assert key not in seen, f"{key} claimed by {seen.get(key)} and {f.name}"
            seen[key] = f.name


def test_peak_and_typical_do_not_overlap_at_all():
    peak = {k for k, _, _ in F.BY_NAME["peak-power-w"].sources}
    typ = {k for k, _, _ in F.BY_NAME["typical-power-w"].sources}
    assert not peak & typ


# ---- rule 2: structured beats prose -----------------------------------------

def test_psu_redundancy_comes_from_the_group_and_not_from_prose():
    """The other half of the CSV. `power-envelope: fully-configured` appeared
    in a redundancy column - it is a scope qualifier for the max figure and is
    not a redundancy at all. A key that merely CONTAINS a matching word is not
    the fact."""
    d = dev(attrs={"power": {"power-envelope": "fully-configured",
                             "psus": "2x 400 W 1+1 redundant, hot-swappable"}},
            groups={"psus": {"term": "PSU", "role": "service",
                             "attrs": {"redundancy": "1+1",
                                       "redundancy-note": "2x 400 W 1+1 redundant"}}})
    res = F.resolve(d)
    assert vals(res, "psu-redundancy") == ["1+1"]
    assert "fully-configured" not in str(res["psu-redundancy"])


def test_the_redundancy_facts_accept_no_attrs_source_whatsoever():
    """Held structurally. As long as the source list is empty there is no
    spelling of prose that can reach the column."""
    assert F.BY_NAME["psu-redundancy"].sources == []
    assert F.BY_NAME["fan-redundancy"].sources == []


def test_a_fan_group_is_not_a_psu_group():
    """The contamination that started this whole convention: a fan tray's 5+1
    read as a power figure."""
    d = dev(groups={"fans": {"term": "Fan", "attrs": {"redundancy": "4+1"}}})
    res = F.resolve(d)
    assert vals(res, "fan-redundancy") == ["4+1"]
    assert "psu-redundancy" not in res


def test_a_group_called_furniture_does_not_match_re():
    """Whole words only. `re` is inside "furniture"."""
    d = dev(groups={"furniture": {"term": "Point", "attrs": {"redundancy": "1+1"}}})
    assert F.resolve(d) .get("psu-redundancy") is None


# ---- rule 3: unlike facts stay unlike ---------------------------------------

def test_throughput_and_switching_capacity_are_separate_facts():
    """Both are Gbps and they are not the same measurement. In this library
    they are also disjoint - the MX chassis state throughput, everyone else
    states switching capacity - so merging them would compare a forwarding rate
    against a line-rate sum on every Juniper-versus-anyone page."""
    assert "throughput-gbps" in F.BY_NAME and "switching-capacity-gbps" in F.BY_NAME
    a = F.resolve(dev({"performance": {"throughput": "400 Gbps (datasheet)"}}))
    b = F.resolve(dev({"performance": {"switching-capacity": "800 Gbps"}}))
    assert vals(a, "throughput-gbps") == [400.0] and "switching-capacity-gbps" not in a
    assert vals(b, "switching-capacity-gbps") == [800.0] and "throughput-gbps" not in b


# ---- readings keep the vendor's words ---------------------------------------

def test_a_number_is_parsed_but_the_sentence_is_kept():
    """"10.3 kg fully loaded, AC-powered chassis (Table 19)" is worth more than
    10.3, because the qualifier is what makes it true."""
    raw = "10.3 kg fully loaded, AC-powered chassis (Table 19)"
    res = F.resolve(dev({"physical": {"weight": raw}}))
    r = res["weight-kg"]["readings"][0]
    assert r["value"] == 10.3 and r["vendor"] == raw


def test_a_value_with_no_number_still_produces_a_reading():
    """A fact that cannot be plotted can still be read. Dropping it would make
    "not published" and "not parseable" look identical."""
    res = F.resolve(dev({"performance": {"switching-capacity": "line rate"}}))
    r = res["switching-capacity-gbps"]["readings"][0]
    assert r["value"] is None and r["vendor"] == "line rate"


def test_every_reading_says_where_it_came_from():
    res = F.resolve(dev({"power": {"power-max-w": 280}}))
    assert res["peak-power-w"]["readings"][0]["from"] == "power/power-max-w"


def test_a_fact_with_no_readings_is_omitted_not_emitted_empty():
    """"We found none" and "the vendor publishes none" are different claims and
    this layer is not entitled to make the second."""
    res = F.resolve(dev())
    assert "peak-power-w" not in res and "asic" not in res


# ---- weight has two homes ---------------------------------------------------

def test_chassis_weight_is_preferred_and_attrs_weights_are_qualifiers():
    """58 devices carry chassis.weight-kg and 25 more carry an attrs spelling.
    Treating them as rivals is how one device's shipping weight ends up
    compared against another's empty one."""
    d = dev(attrs={"physical": {"weight-shipping-kg": 7.2}}, chassis={"weight-kg": 4.9})
    rs = F.resolve(d)["weight-kg"]["readings"]
    assert rs[0]["value"] == 4.9 and rs[0]["from"] == "chassis.weight-kg"
    assert rs[1]["qualifier"] == "shipping"


# ---- against the real library -----------------------------------------------

def real(slug):
    return yaml.safe_load((LIB / "devices" / slug / "device.yaml").read_text())


def test_the_two_devices_from_the_csv_now_compare_correctly():
    """End to end, on the actual manifests."""
    mx = F.resolve(real("juniper/mx204"))
    s95 = F.resolve(real("ufispace/s9510-28dc"))

    # the inverted row: the UfiSpace box draws MORE, not half
    assert vals(mx, "peak-power-w") == [280.0]
    assert max(v for v in vals(s95, "peak-power-w")) > 280.0

    # the row that showed a scope qualifier against a blank
    assert vals(mx, "psu-redundancy") == ["1+1"]
    assert vals(s95, "psu-redundancy") == ["1+1"]

    # the row that compared two different measurements
    assert "throughput-gbps" in mx and "switching-capacity-gbps" not in mx
    assert "switching-capacity-gbps" in s95 and "throughput-gbps" not in s95


def test_no_device_resolves_a_peak_that_equals_its_own_typical_by_accident():
    """A cheap tripwire for rule 1 across the whole library: if a fallback ever
    creeps back in, the first symptom is a peak reading that IS the typical
    one, sourced from a typical key."""
    bad = []
    for f in sorted(LIB.glob("devices/**/device.yaml")):
        d = yaml.safe_load(f.read_text())
        if d.get("kind") != "device":
            continue
        for r in F.resolve(d).get("peak-power-w", {}).get("readings", []):
            if "typical" in r["from"]:
                bad.append(f"{f.parent.name}: {r['from']}")
    assert not bad, bad


def test_the_vocabulary_is_published_with_the_values():
    """A consumer should not have to hardcode the fact list to know what
    columns exist, nor guess which pairs may be compared."""
    import json
    p = LIB / "dist" / "comparable-facts.json"
    if not p.exists():
        import pytest
        pytest.skip("library/dist not built - run ./build.sh")
    doc = json.loads(p.read_text())
    assert set(doc["vocabulary"]) == set(F.BY_NAME)
    assert doc["vocabulary"]["throughput-gbps"]["note"]
    assert doc["devices"] and "unclaimed" in doc
