"""L198: a build's airflow agrees with the fans and supplies it seats.

L120 holds a configuration's `power` against the supplies it seats; this holds
its `airflow` the same way. The build reads the configuration's `airflow`, else
`chassis.airflow` (manifest.config_airflow), and a fan or supply may state
`attrs.airflow` on its contract. The rule speaks only when both sides say one
of the two canonical directions and they differ. It never maps a vendor word
(`exhaust`, `intake`, a sentence) to a direction, so a part that says one of
those, a part that says nothing, and a build with no front-to-back or
back-to-front airflow are all quiet.
"""
import yaml

from portrayal import lint

F2B, B2F = "front-to-back", "back-to-front"


def library(tmp_path, **parts):
    """A library with one component per keyword: name -> (class, attrs)."""
    for name, (cls, attrs) in parts.items():
        d = tmp_path / "components" / "test" / name / "v1"
        d.mkdir(parents=True)
        contract = {"class": cls}
        if attrs is not None:
            contract["attrs"] = attrs
        (d / "contract.yaml").write_text(yaml.safe_dump(contract))
    return [str(tmp_path)]


def device(configs, chassis_airflow=F2B, default="test/fan-a@1", maturity="modelled"):
    return {"maturity": maturity,
            "chassis": {"airflow": chassis_airflow} if chassis_airflow else {},
            "views": {"rear": {"components": {"bays": [
                {"id": "fan-0", "default": default}]}}},
            "configurations": configs}


def findings(doc, roots):
    with lint.collecting() as found:
        lint.lint_device_airflow_agrees("device.yaml", doc, roots)
    return found


def l198(found):
    return [m for m in found.errors + found.warnings if "[L198]" in m]


def test_a_front_to_back_build_seating_a_back_to_front_fan_is_reported(tmp_path):
    roots = library(tmp_path, **{"fan-a": ("fan", {"airflow": B2F})})
    got = l198(findings(device({"base": {"kind": "base"}}), roots))
    assert len(got) == 1
    assert "'base'" in got[0] and "fan-0" in got[0] and "test/fan-a@1" in got[0]
    assert F2B in got[0] and B2F in got[0]
    assert "component-attrs" in got[0]


def test_a_supply_is_held_to_the_build_the_same_way(tmp_path):
    roots = library(tmp_path, **{"psu-ac": ("psu", {"airflow": B2F})})
    doc = device({"base": {"kind": "base"}}, default="test/psu-ac@1")
    doc["views"]["rear"]["components"]["bays"][0]["id"] = "psu-0"
    assert len(l198(findings(doc, roots))) == 1


def test_the_configurations_own_airflow_wins_over_the_chassis(tmp_path):
    roots = library(tmp_path, **{"fan-a": ("fan", {"airflow": B2F})})
    doc = device({"base": {"kind": "base"}, "rev": {"kind": "orderable", "airflow": B2F}})
    got = l198(findings(doc, roots))
    assert len(got) == 1 and "'base'" in got[0]


def test_a_matching_build_is_quiet(tmp_path):
    roots = library(tmp_path, **{"fan-a": ("fan", {"airflow": F2B})})
    assert not findings(device({"base": {"kind": "base"}}), roots).warnings


def test_a_seated_part_can_be_swapped_for_the_matching_one(tmp_path):
    roots = library(tmp_path, **{"fan-a": ("fan", {"airflow": F2B}),
                                 "fan-rev": ("fan", {"airflow": B2F})})
    doc = device({"base": {"kind": "base"},
                  "rev": {"kind": "orderable", "airflow": B2F,
                          "bays": {"fan-0": "test/fan-rev@1"}}})
    assert not l198(findings(doc, roots))


def test_a_vendor_word_is_not_a_direction(tmp_path):
    for word in ("exhaust", "intake", "port-side intake", "side-to-side",
                 "air leaves at the rear, drawn in at the front"):
        roots = library(tmp_path / word.split()[0], **{"fan-a": ("fan", {"airflow": word})})
        assert not l198(findings(device({"base": {"kind": "base"}}, chassis_airflow=B2F), roots)), word


def test_a_part_that_states_no_airflow_is_quiet(tmp_path):
    roots = library(tmp_path, **{"fan-a": ("fan", {"watts": "40"})})
    assert not l198(findings(device({"base": {"kind": "base"}}), roots))
    roots = library(tmp_path / "bare", **{"fan-a": ("fan", None)})
    assert not l198(findings(device({"base": {"kind": "base"}}), roots))


def test_a_build_with_no_canonical_airflow_is_quiet(tmp_path):
    roots = library(tmp_path, **{"fan-a": ("fan", {"airflow": B2F})})
    for chassis in (None, "side", "passive"):
        assert not l198(findings(device({"base": {"kind": "base"}}, chassis_airflow=chassis), roots)), chassis


def test_a_component_attrs_override_that_agrees_is_quiet(tmp_path):
    roots = library(tmp_path, **{"fan-a": ("fan", {"airflow": F2B})})
    cfg = {"rev": {"kind": "orderable", "airflow": B2F,
                   "component-attrs": {"fan-a": {"airflow": B2F}}}}
    assert not l198(findings(device(cfg), roots))
    # by bay id as well as by component name
    cfg = {"rev": {"kind": "orderable", "airflow": B2F,
                   "component-attrs": {"fan-0": {"airflow": B2F}}}}
    assert not l198(findings(device(cfg), roots))


def test_a_component_attrs_override_that_disagrees_is_reported(tmp_path):
    roots = library(tmp_path, **{"fan-a": ("fan", {"airflow": F2B})})
    cfg = {"base": {"kind": "base", "component-attrs": {"fan-a": {"airflow": B2F}}}}
    assert len(l198(findings(device(cfg), roots))) == 1


def test_a_part_that_is_neither_fan_nor_supply_is_not_read(tmp_path):
    roots = library(tmp_path, **{"module-a": ("line-card", {"airflow": B2F})})
    doc = device({"base": {"kind": "base"}}, default="test/module-a@1")
    doc["views"]["rear"]["components"]["bays"][0]["id"] = "slot-0"
    assert not l198(findings(doc, roots))


def test_it_warns_at_modelled_and_fails_at_verified(tmp_path):
    roots = library(tmp_path, **{"fan-a": ("fan", {"airflow": B2F})})
    soft = findings(device({"base": {"kind": "base"}}), roots)
    assert len(soft.warnings) == 1 and not soft.errors
    hard = findings(device({"base": {"kind": "base"}}, maturity="verified"), roots)
    assert len(hard.errors) == 1 and not hard.warnings
