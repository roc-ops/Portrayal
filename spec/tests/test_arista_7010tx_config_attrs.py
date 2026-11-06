"""The Arista 7010TX-48C builds are configurations of their own, each stating its own memory,
minimum EOS release and DCIM description.

The 7010TX-48 and the 7010TX-48C are one front panel, one rear and one fan, and differ in system
memory (4 GB against 8 GB) and in the minimum EOS release (7010X Series Data Sheet, 03-0052-14,
Technical Specifications, PDF page 7). The exporter writes one device type per configuration,
so a -48C part number listed beside a -48 one in the same configuration was never exported.
Each -48C build is now a configuration of its own, and the figures the data sheet gives for it
are the configuration's `attrs`. Its power is not stated here: the 7010 Series 1RU Quick Start
Guide (PDOC-00061-08, Table 3) gives 75 W typical and 100 W maximum to every build, the data
sheet gives other figures and a "TBD", and the two stay recorded as the `power-draw` gap.
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DEV = LIB / "devices/arista/7010tx-48"

# -48C configuration -> (the -48 configuration it is the same build as, its part number,
# the minimum EOS release the data sheet prints for it)
C_BUILDS = {
    "ac-c-f": ("ac-f", "DCS-7010TX-48C-F", "4.31.1"),
    "ac-c-r": ("ac-r", "DCS-7010TX-48C-R", "4.31.1"),
    "dc-c-f": ("dc-f", "DCS-7010TX-48C-DC-F", "4.33.2"),
    "dc-c-r": ("dc-r", "DCS-7010TX-48C-DC-R", "4.33.2"),
}
# the -48 configurations and the one part number each orders under
PLAIN = {
    "ac-f": "DCS-7010TX-48-F",
    "ac-r": "DCS-7010TX-48-R",
    "dc-f": "DCS-7010TX-48-DC-F",
    "dc-r": "DCS-7010TX-48-DC-R",
}
TARGETS = ["netbox", "nautobot"]


def load():
    return yaml.safe_load((DEV / "device.yaml").read_text())


def export(target, pn):
    path = LIB / "exports" / target / "device-types/Arista" / f"{pn}.yaml"
    return yaml.safe_load(path.read_text())


def test_each_c_build_is_a_configuration_with_its_own_part_number_and_the_plain_builds_keep_theirs():
    cf = load()["configurations"]
    assert set(cf) == set(PLAIN) | set(C_BUILDS)
    for name, pn in PLAIN.items():
        assert list(cf[name]["part-numbers"]) == [pn], name
    for name, (_, pn, _) in C_BUILDS.items():
        assert cf[name]["kind"] == "orderable", name
        assert list(cf[name]["part-numbers"]) == [pn], name
        assert not cf[name].get("default"), name


def test_a_c_build_draws_what_its_plain_build_draws():
    cf = load()["configurations"]
    for name, (plain, _, _) in C_BUILDS.items():
        for key in ("power", "airflow", "views", "bay-attrs"):
            assert cf[name].get(key) == cf[plain].get(key), (name, key)


def test_a_c_build_states_8_gb_and_its_own_minimum_eos_and_no_power():
    d = load()
    cf = d["configurations"]
    for name, (_, _, eos) in C_BUILDS.items():
        attrs = cf[name]["attrs"]
        assert set(attrs) == {"platform", "features"}, name
        assert attrs["platform"] == {"memory": "8 GB (data sheet)"}, name
        assert set(attrs["features"]) == {"eos-license"}, name
        assert f"minimum EOS {eos}" in attrs["features"]["eos-license"], name
        assert "license group G2" in attrs["features"]["eos-license"], name
    # the plain builds state nothing of their own: the device's attrs are theirs
    for name in PLAIN:
        assert "attrs" not in cf[name], name
    # and no build states a power: the device's 75 W / 100 W (guide, Table 3) is every build's
    assert d["attrs"]["power"]["power-typical-w"] == 75
    assert d["attrs"]["power"]["power-max-w"] == 100


def test_the_device_states_the_plain_builds_memory_and_release_alone():
    attrs = load()["attrs"]
    assert attrs["platform"]["memory"] == "4 GB (data sheet)"
    eos = attrs["features"]["eos-license"]
    assert "minimum EOS 4.26.0" in eos
    assert "4.31.1" not in eos and "4.33.2" not in eos


def test_each_c_build_has_a_dcim_description_of_its_own_that_fits():
    cf = load()["configurations"]
    for name, (_, _, eos) in C_BUILDS.items():
        text = cf[name]["export-description"]
        assert len(text) <= 200, name
        assert text.startswith("Arista 7010TX-48C"), name
        assert "8 GB" in text and f"EOS {eos}" in text, name
        assert ("-48C-DC" in text) == name.startswith("dc"), name
    for name in PLAIN:
        assert "export-description" not in cf[name], name


def test_the_gap_that_a_configuration_cannot_say_it_is_closed_and_the_power_gap_stays():
    gaps = {g["what"]: g for g in load()["gaps"]}
    assert "config-scoped-device-attrs" not in gaps
    note = gaps["power-draw"]["note"]
    # the data sheet's own figures for the -48C stay recorded, with the "TBD" of the -48C-DC
    assert "83 W / 95 W" in note and "TBD" in note


@pytest.mark.parametrize("target", TARGETS)
def test_a_dcim_type_exists_for_every_c_build_and_describes_it(target):
    cf = load()["configurations"]
    for name, (_, pn, eos) in C_BUILDS.items():
        doc = export(target, pn)
        assert doc["model"] == pn and doc["manufacturer"] == "Arista"
        assert doc["description"] == cf[name]["export-description"], pn
        assert doc["u_height"] == 1.0
        comments = doc["comments"]
        assert "platform.memory: 8 GB (data sheet)" in comments, pn
        assert f"minimum EOS {eos}" in comments, pn
        # the figures it does not state are the device's: the guide's 75 W / 100 W
        assert "power.power-typical-w: 75" in comments and "power.power-max-w: 100" in comments, pn


@pytest.mark.parametrize("target", TARGETS)
def test_a_c_type_lists_the_ports_of_the_plain_type_it_is_a_build_of(target):
    for name, (plain, pn, _) in C_BUILDS.items():
        a, b = export(target, PLAIN[plain]), export(target, pn)
        for key in ("interfaces", "front-ports", "console-ports", "power-ports", "module-bays",
                    "u_height", "airflow", "is_full_depth"):
            assert a.get(key) == b.get(key), (pn, key)


@pytest.mark.parametrize("target", TARGETS)
def test_a_plain_type_states_4_gb_and_4_26_0_and_names_no_c_release(target):
    for name, pn in PLAIN.items():
        comments = export(target, pn)["comments"]
        assert "platform.memory: 4 GB (data sheet)" in comments, pn
        assert "minimum EOS 4.26.0" in comments, pn
        assert "4.31.1" not in comments and "4.33.2" not in comments, pn
        assert "DCS-7010TX-48C" not in comments, pn
