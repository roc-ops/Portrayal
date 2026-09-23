"""The adapters ship capped (B3, docs/pluggables-caps-design.md, "The shipped
default", "Which adapter ships which cap").

A dust cap is the shipped state of an idle fibre port, declared as a `default:`
on the part that presents the port. Which LEVEL ships it follows the product:

  - common/lc-duplex-adapter@6 (Smartoptics): a simplex cap in EACH bore;
  - common/lc-duplex-v-adapter@6 (FS FHD, stacked): ONE duplex cap across both
    ports, on the adapter's own slot;
  - common/sc-duplex-adapter@5 (FS FHD SC): a cap in each opening;
  - common/mpo-adapter@2 (FS's MTP panel tile, unplaced) and the FHD cassette
    rears' flanged bulkheads common/mpo-flange-adapter@2 and
    common/mpo24-flange-adapter@2: the MPO cap in the opening;
  - common/lc-duplex-shuttered-adapter@2: NOTHING - its shutters are the dust
    protection, and FS ships it empty.

WHAT IS CHECKED, ON REAL BUILDS:

  (a) THE CENSUS. Every slot these adapters present, on every face the library
      compiles - each component's own compiled face, as components.json writes
      it for the kit, front faces and cassette backs alike; every configuration
      of every device that reaches one, front and rear; and the FHD enclosure
      and the DCP-2's A22 carrier with EVERY module their bays accept - holds
      exactly one occupant, unconfigured, and it is the declared cap. The other
      level of the same adapter holds nothing, and a shuttered port holds
      nothing at either level. Each count is asserted equal to the number of
      such slots, and greater than zero.
  (b) NO PORT IS CAPPED TWICE: nothing classed `cap` is drawn on an adapter
      except inside an occupant.
  (c) A CONFIGURATION STILL WINS (P4/P5): `""` empties a shipped cap and a plug
      replaces it, on an FS port (front and rear) and a Smartoptics port; and
      the exclusion (L115) still refuses a duplex plug over capped bores.
  (d) THE SMARTOPTICS PPM-DCM MODULES, seated in the A22's bays, show their
      forwarded adapter's two bore caps; a bay module's OWN top-level default
      is still refused (Task 3's ruling).
  (e) L114 is clean on every new default, and finds a wrong one.

Each census is proved non-vacuous by a tmp copy of the adapter with its default
removed, which the same census has to fail.
"""
import re
import shutil
import xml.etree.ElementTree as ET
from collections import defaultdict

import pytest
import yaml

from test_nested_occupants import LIB
from test_slot_defaults import _copy, build, run

from portrayal import lint
from portrayal.manifest import load_yaml
from portrayal.render import Library, instance_group

LC_CAP = "common/lc-dust-cap@1"
DUPLEX_CAP = "common/lc-duplex-dust-cap@2"
SC_CAP = "common/sc-dust-cap@1"
MPO_CAP = "common/mpo-dust-cap@2"
LC = "generic/lc-plug@2"
DUPLEX = "generic/lc-duplex-plug@2"
MPO12 = "generic/mpo12-plug@1"

# adapter -> (the level that ships the cap, the cap). "self" is the adapter's
# own slot; "bores" is each of its two composed bores, `tx` and `rx`.
SHIPS = {
    "common/lc-duplex-adapter@6": ("bores", LC_CAP),
    "common/lc-duplex-v-adapter@6": ("self", DUPLEX_CAP),
    "common/sc-duplex-adapter@5": ("bores", SC_CAP),
    "common/mpo-adapter@2": ("self", MPO_CAP),
    "common/mpo-flange-adapter@2": ("self", MPO_CAP),
    "common/mpo24-flange-adapter@2": ("self", MPO_CAP),
}
SHUTTERED = "common/lc-duplex-shuttered-adapter@2"
ADAPTERS = tuple(SHIPS) + (SHUTTERED,)
BORES = ("tx", "rx")
REF = re.compile(r"^[a-z0-9-]+/[a-z0-9.+-]+@\d+$")


# --- reading a drawing ---------------------------------------------------------------

def _ref(el):
    return (el.get("data-ref") or "").rsplit(":", 1)[0]


def _path(el):
    return el.get("data-path") or el.get("data-of")


def _is_g(el):
    return el.tag.split("}")[-1] == "g"


def seats(root):
    """{host path: [what is seated on it]} - an occupant's ref, or its class
    where a projection has stripped the ref (a cassette's back on a rear)."""
    out = defaultdict(list)
    for el in root.iter():
        if _is_g(el) and el.get("data-for") is not None \
                and (_path(el) or "").endswith("-occupant"):
            out[el.get("data-for")].append(_ref(el) or el.get("data-class"))
    return out


def adapters_in(root, refs=ADAPTERS):
    """[(path, ref, element)] for every group drawing one of `refs`, EXCEPT the
    drawing's own root part: a component compiled alone has no composer, and a
    top-level default is its composer's to seat."""
    top = root if _is_g(root) else next((c for c in root if _is_g(c)), None)
    return [(el.get("data-path"), _ref(el), el) for el in root.iter()
            if _is_g(el) and el is not top and el.get("data-path")
            and _ref(el) in refs]


def rear_flanges(root):
    """[path] for every flanged MPO bulkhead on a PROJECTED cassette back,
    which a rear drawing draws without its refs: a port presenting `mpo`
    under a projection."""
    out = []
    for proj in root.iter():
        if not (_is_g(proj) and proj.get("data-projection")):
            continue
        for el in proj.iter():
            if (_is_g(el) and el.get("data-connector") == "mpo"
                    and el.get("data-class") == "port"
                    and not (el.get("data-of") or "").endswith("-occupant")
                    and "-occupant/" not in (el.get("data-of") or "")):
                out.append(el.get("data-of"))
    return out


def census_problems(root, ships=SHIPS, where=""):
    """Every adapter slot in one drawing, checked and counted: ({adapter ref:
    number of slots checked}, [every slot holding the wrong thing]).

    A slot that ships a cap holds exactly that cap; the adapter's OTHER level
    holds nothing; a shuttered adapter holds nothing at either level."""
    held = seats(root)
    counts = defaultdict(int)
    bad = []
    for path, ref, _el in adapters_in(root, tuple(ships) + (SHUTTERED,)):
        level, cap = ships.get(ref, (None, None))
        mine = {"self": [path], "bores": [f"{path}/{b}" for b in BORES]}
        want = {s: [] for s in mine["self"] + mine["bores"]}
        if level == "self":
            want[path] = [cap]
        elif level == "bores":
            want.update({s: [cap] for s in mine["bores"]})
        for slot, w in want.items():
            if ref.startswith("common/mpo") and slot != path:
                continue                        # an MPO port has no bores
            if held.get(slot, []) != w:
                bad.append((where, slot, ref, held.get(slot, []), w))
            if w:
                counts[ref] += 1
        if ref == SHUTTERED:
            counts[ref] += 3                    # the adapter and both bores, all empty
    return counts, bad


def census(root, ships=SHIPS, where=""):
    counts, bad = census_problems(root, ships, where)
    assert not bad, (len(bad), bad[:10])
    return counts


def no_drawn_cap_outside_an_occupant(root, where="", refs=ADAPTERS):
    """Nothing classed `cap` is drawn by an adapter: every `cap` element in an
    adapter's subtree is inside an occupant group in that subtree."""
    parents = {c: p for p in root.iter() for c in p}
    found = []
    for _path_, _ref_, a in adapters_in(root, refs):
        for el in a.iter():
            cls = (el.get("class") or "").split() + [el.get("data-class") or ""]
            if "cap" not in cls:
                continue
            node, inside = el, False
            while node is not None and node is not a:
                if node.get("data-for") is not None:
                    inside = True
                    break
                node = parents.get(node)
            if not inside:
                found.append((where, _path(el)))
    return found


# --- the library as a graph ----------------------------------------------------------

def _contract_path(ref, root=LIB):
    ns, rest = ref.split("/", 1)
    name, major = rest.split("@")
    return root / "components" / ns / name / f"v{major}" / "contract.yaml"


def _refs_in(obj):
    """Every whole-string ref anywhere in a parsed YAML tree - parts, bays'
    accepts and defaults, configurations' bays, faces - never a substring."""
    if isinstance(obj, dict):
        for v in obj.values():
            yield from _refs_in(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _refs_in(v)
    elif isinstance(obj, str):
        r = obj.split(":")[0]
        if REF.match(r) and _contract_path(r).exists():
            yield r


def _reach(start):
    seen, todo = set(), list(start)
    while todo:
        r = todo.pop()
        if r in seen:
            continue
        seen.add(r)
        todo.extend(_refs_in(load_yaml(_contract_path(r))))
    return seen


def every_component():
    return sorted(f"{p.parents[2].name}/{p.parents[1].name}@{p.parent.name[1:]}"
                  for p in (LIB / "components").glob("*/*/v*/contract.yaml"))


def components_reaching_adapters():
    return [r for r in every_component() if _reach([r]) & set(ADAPTERS)]


def devices_reaching_adapters():
    out = []
    for f in sorted((LIB / "devices").glob("*/*/device.yaml")):
        if _reach(_refs_in(load_yaml(f))) & set(ADAPTERS):
            out.append(f)
    return out


def compiled_face(ref, root=LIB):
    """The component's own compiled face, exactly as components_index writes
    it to components/<ns>--<name>--v<major>--default.svg for the kit."""
    lib = Library([str(root), str(LIB)] if root != LIB else [str(LIB)])
    data = lib.resolve(ref)[0]
    g, _ = instance_group(lib, ref, data["name"], [0, 0], None, None, None, None,
                          skin_name="default", palette={}, resolved={})
    return g


# --- (a) the census: compiled component faces ----------------------------------------

def test_each_adapter_declares_the_cap_its_product_ships():
    """The declarations themselves, at the level the product ships them."""
    for ref, (level, cap) in SHIPS.items():
        c = load_yaml(_contract_path(ref))
        bores = [q for q in c.get("parts") or [] if q.get("id") in BORES]
        if level == "self":
            assert c.get("default") == cap, ref
            assert all("default" not in q for q in bores), ref
        else:
            assert "default" not in c, ref
            assert [q.get("default") for q in bores] == [cap, cap], ref
    s = load_yaml(_contract_path(SHUTTERED))
    assert "default" not in s
    assert all("default" not in q for q in s["parts"])


def test_every_compiled_component_face_ships_its_ports_capped():
    """Every component the library holds that draws one of these adapters, at
    any depth - cassettes, cassette backs, the A22 carrier, the PPM modules -
    compiled as the kit fetches it. The walk follows parts, bays and faces."""
    comps = components_reaching_adapters()
    assert len(comps) > 40, comps
    total, bad_caps = defaultdict(int), []
    for ref in comps:
        g = compiled_face(ref)
        for k, n in census(g, where=ref).items():
            total[k] += n
        bad_caps += no_drawn_cap_outside_an_occupant(g, ref)
    assert not bad_caps, bad_caps[:10]
    # every family is exercised, and the shuttered ports are counted empty
    for ref in ("common/lc-duplex-adapter@6", "common/lc-duplex-v-adapter@6",
                "common/sc-duplex-adapter@5", "common/mpo-flange-adapter@2",
                "common/mpo24-flange-adapter@2", SHUTTERED):
        assert total[ref] > 0, (ref, dict(total))
    # AS MANY AS THE CONTRACTS COMPOSE: the drawing checked every slot the
    # parts graph says is there, and no fewer
    assert dict(total) == slots_by_contract(comps), dict(total)


def _composed(ref):
    """{adapter ref: instances} composed under `ref`, not counting `ref`
    itself - through parts, and through the bays a compiled face fills with
    their defaults."""
    out = defaultdict(int)
    c = load_yaml(_contract_path(ref))
    subs = [q["ref"].split(":")[0] for q in c.get("parts") or []]
    bays = c.get("bays") if isinstance(c.get("bays"), dict) else {}
    subs += [b["default"].split(":")[0] for b in bays.values() if b.get("default")]
    for r in subs:
        if r in ADAPTERS:
            out[r] += 1
        for k, n in _composed(r).items():
            out[k] += n
    return out


def slots_by_contract(comps):
    """The slots the census should find, counted off the contracts: two bores
    per bore-capped adapter, one slot per self-capped one, three empty slots
    per shuttered adapter."""
    per = {"bores": 2, "self": 1}
    total = defaultdict(int)
    for ref in comps:
        for k, n in _composed(ref).items():
            total[k] += n * (per[SHIPS[k][0]] if k in SHIPS else 3)
    return dict(total)


def test_the_census_fails_on_an_adapter_that_ships_nothing(tmp_path):
    """Non-vacuity: a copy of the FS LC cassette whose adapters are a copy of
    lc-duplex-v-adapter@5 WITHOUT its default. Told that copy ships the duplex
    cap, the census finds every port bare."""
    root = tmp_path / "lib"
    _copy(root, "common/lc-duplex-v-adapter", 5, "bare-v", lambda c: c.pop("default"))

    def repoint(c):
        for q in c["parts"]:
            if q["ref"] == "common/lc-duplex-v-adapter@6":
                q["ref"] = "test/bare-v@1"
    _copy(root, "fs/fhd-2mtp12-lc-os2-a", 3, "bare-cassette", repoint)
    g = compiled_face("test/bare-cassette@1", root)
    counts, bad = census_problems(g, {**SHIPS, "test/bare-v@1": ("self", DUPLEX_CAP)})
    assert counts["test/bare-v@1"] == len(bad) == 12, bad
    assert all(held == [] for _w, _s, _r, held, _want in bad)


def test_the_census_fails_on_a_cap_at_the_wrong_level(tmp_path):
    """Non-vacuity for the OTHER level: the FS adapter's bores capped as well
    as its own slot is refused by the build (L115), so the census is fed a
    copy capping the bores INSTEAD - and must call every one of them wrong."""
    root = tmp_path / "lib"

    def bores_instead(c):
        c.pop("default")
        for q in c["parts"]:
            if q.get("id") in BORES:
                q["default"] = LC_CAP
    _copy(root, "common/lc-duplex-v-adapter", 5, "bored-v", bores_instead)

    def repoint(c):
        for q in c["parts"]:
            if q["ref"] == "common/lc-duplex-v-adapter@6":
                q["ref"] = "test/bored-v@1"
    _copy(root, "fs/fhd-2mtp12-lc-os2-a", 3, "bored-cassette", repoint)
    g = compiled_face("test/bored-cassette@1", root)
    _counts, bad = census_problems(g, {**SHIPS, "test/bored-v@1": ("self", DUPLEX_CAP)})
    # each of the twelve adapters: its own slot bare, and both bores wrongly capped
    assert len(bad) == 12 * 3, len(bad)


def test_the_drawn_cap_check_finds_a_cap_the_adapter_draws(tmp_path):
    """Non-vacuity for (b): an element classed `cap` added to a copy of the
    Smartoptics adapter's skin is found, because no occupant holds it."""
    root = tmp_path / "lib"
    dst = _copy(root, "common/lc-duplex-adapter", 5, "drawn-cap", lambda c: None).parent
    skin = dst / "skins" / "default.svg"
    text = skin.read_text()
    assert text.count("</svg>") == 1
    skin.write_text(text.replace(
        "</svg>", '<rect id="drawn-cap" class="cap" x="1" y="3" width="4.7" height="4.7"/></svg>'))

    def repoint(c):
        c["parts"][0]["ref"] = "test/drawn-cap@1"
    _copy(root, "smartoptics/ppm-dcm-40", 1, "drawn-cap-dcm", repoint)
    g = compiled_face("test/drawn-cap-dcm@1", root)
    assert len(adapters_in(g, ("test/drawn-cap@1",))) == 1
    found = no_drawn_cap_outside_an_occupant(g, refs=("test/drawn-cap@1",))
    assert len(found) == 1, found
    # and the real adapter, whose caps are all occupants, is clean
    assert no_drawn_cap_outside_an_occupant(compiled_face("smartoptics/ppm-dcm-40@2")) == []


# --- (a) the census: real device builds ----------------------------------------------

def _faces(out, name, views=("front", "rear")):
    """Every front and rear a device build writes: each configuration's, and
    the device's own undecorated face."""
    return sorted(p for v in views
                  for p in [*out.glob(f"{name}.*.{v}.svg"), out / f"{name}.{v}.svg"]
                  if p.exists())


def test_every_device_that_reaches_an_adapter_ships_its_ports_capped(tmp_path):
    """Every configuration of every real device whose graph reaches one of these
    adapters, built for real, front and rear."""
    devs = devices_reaching_adapters()
    names = sorted(f.parent.name for f in devs)
    assert names == ["dcp-2", "dcp-m32-cso-zr", "dcp-r-34d-cs", "dcp-r-9d-cs",
                     "fhd-1ufce"], names
    total, bad_caps, rear_total = defaultdict(int), [], 0
    for f in devs:
        out = tmp_path / f.parent.name
        r = run(f, out, LIB)
        assert r.returncode == 0, r.stderr[-800:]
        faces = _faces(out, f.parent.name)
        assert faces, f
        for svg in faces:
            root = ET.parse(svg).getroot()
            for k, n in census(root, where=svg.name).items():
                total[k] += n
            bad_caps += no_drawn_cap_outside_an_occupant(root, svg.name)
            held = seats(root)
            for host in rear_flanges(root):
                assert held.get(host) == ["cap"], (svg.name, host, held.get(host))
                rear_total += 1
    assert not bad_caps, bad_caps[:10]
    assert dict(total) == EXPECTED_DEVICE_SLOTS, dict(total)
    assert rear_total == EXPECTED_DEVICE_REAR_SLOTS > 0


# Counted per face, 2026-09-23. Smartoptics, two bores per adapter, on each
# device's configured face AND its undecorated one: dcp-r-34d-cs 36 adapters,
# dcp-r-9d-cs 46, dcp-m32-cso-zr 35 - (36 + 46 + 35) x 2 x 2 = 468 - plus
# dcp-2's ila-node, the A22's three and the PPM-AD1-1510's two, 5 x 2 = 10.
# FS: the populated configuration's four fhd-1mtp6lcd-os2-a@3, six stacked
# adapters each, on the front; one MTP bulkhead each on the rear. The base
# configuration ships every bay empty, so it adds nothing.
EXPECTED_DEVICE_SLOTS = {"common/lc-duplex-adapter@6": 478,
                         "common/lc-duplex-v-adapter@6": 24}
EXPECTED_DEVICE_REAR_SLOTS = 4


def _fhd_bays():
    """Every cassette any FHD bay accepts."""
    d = load_yaml(LIB / "devices/fs/fhd-1ufce/device.yaml")
    accepts = set()
    for v in d["views"].values():
        for b in ((v or {}).get("components") or {}).get("bays") or []:
            accepts |= set(b.get("accepts") or [])
    return sorted(accepts)


def _chunks(xs, n):
    return [xs[i:i + n] for i in range(0, len(xs), n)]


FHD_CASSETTES = _fhd_bays()


@pytest.mark.parametrize("group", _chunks(FHD_CASSETTES, 4),
                         ids=lambda g: "+".join(r.split("/")[1] for r in g))
def test_every_fhd_cassette_ships_capped_front_and_rear(tmp_path, group):
    """The FHD enclosure with every cassette its bays accept, four at a time, in
    bays 1-4 of a tmp copy: each front port, and each rear MTP bulkhead the
    cassette's back carries, holds its cap - the shuttered ports nothing."""
    dev = shutil.copytree(LIB / "devices/fs/fhd-1ufce", tmp_path / "fhd-1ufce") / "device.yaml"
    d = yaml.safe_load(dev.read_text())
    bays = {f"bay-{i + 1}": ref for i, ref in enumerate(group)}
    d["configurations"]["base"]["bays"] = bays
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    out = build(dev, tmp_path / "o", LIB)
    front = ET.parse(out / "fhd-1ufce.base.front.svg").getroot()
    got = census(front, where="front")
    assert sum(got.values()) > 0, group
    assert not no_drawn_cap_outside_an_occupant(front, "front")
    # the rear: one cap per flanged bulkhead on each seated cassette's back,
    # counted from the backs' contracts, not from the drawing
    rear = ET.parse(out / "fhd-1ufce.base.rear.svg").getroot()
    held = seats(rear)
    want = []
    for bay, ref in bays.items():
        back = (load_yaml(_contract_path(ref)).get("faces") or {}).get("rear")
        back = back.get("ref") if isinstance(back, dict) else back
        if not back:
            continue
        for q in load_yaml(_contract_path(back.split(":")[0])).get("parts") or []:
            if q["ref"] in ("common/mpo-flange-adapter@2", "common/mpo24-flange-adapter@2"):
                want.append(f"{bay}/module/{q['id']}")
    assert sorted(rear_flanges(rear)) == sorted(want)
    assert all(held.get(h) == ["cap"] for h in want), {h: held.get(h) for h in want}


def test_every_fhd_cassette_is_covered():
    assert len(FHD_CASSETTES) > 20
    assert set(sum(_chunks(FHD_CASSETTES, 4), [])) == set(FHD_CASSETTES)


def _a22_modules():
    c = load_yaml(_contract_path("smartoptics/dcp-f-a22@2"))
    return sorted({r for b in c["bays"].values() for r in b.get("accepts") or []})


def _dcp2(tmp_path, bays, occupants=None):
    dev = shutil.copytree(LIB / "devices/smartoptics/dcp-2", tmp_path / "dcp-2") / "device.yaml"
    d = yaml.safe_load(dev.read_text())
    cfg = d["configurations"]["ila-node"]
    cfg["bays"] = {"slot-1": "smartoptics/dcp-f-a22@2", **bays,
                   "slot-2": "smartoptics/dcp-2-blank@1"}
    if occupants is not None:
        cfg["occupants"] = occupants
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    return dev


@pytest.mark.parametrize("pair", _chunks(_a22_modules(), 2),
                         ids=lambda g: "+".join(r.split("/")[1] for r in g))
def test_every_ppm_module_ships_capped_in_the_a22(tmp_path, pair):
    """The DCP-2 with the A22 carrier and every PPM module its two bays accept,
    two at a time: each module's composed adapters ship their bore caps."""
    bays = {f"slot-1/ppm-{i + 1}": ref for i, ref in enumerate(pair)}
    out = build(_dcp2(tmp_path, bays), tmp_path / "o", LIB)
    root = ET.parse(out / "dcp-2.ila-node.front.svg").getroot()
    got = census(root, where=str(pair))
    assert got["common/lc-duplex-adapter@6"] > 0
    assert not no_drawn_cap_outside_an_occupant(root)


# --- (d) the PPM-DCM modules ---------------------------------------------------------

DCMS = ["smartoptics/ppm-dcm-10@2", "smartoptics/ppm-dcm-20@2",
        "smartoptics/ppm-dcm-40@2", "smartoptics/ppm-dcm-80@2"]


def test_a_seated_dcm_shows_its_forwarded_adapters_two_bore_caps(tmp_path):
    """ppm-dcm-40 in ppm-1 and ppm-dcm-10 in ppm-2: each module composes ONE
    Smartoptics adapter (`dcm`) and forwards its `lc-duplex`, publishing no
    slot of its own - and each ships two simplex caps, one per bore, drawn in
    the module at `<bay>/module/dcm/tx|rx`, the adapter's own slot empty."""
    out = build(_dcp2(tmp_path, {"slot-1/ppm-1": DCMS[2], "slot-1/ppm-2": DCMS[0]}),
                tmp_path / "o", LIB)
    root = ET.parse(out / "dcp-2.ila-node.front.svg").getroot()
    held = seats(root)
    for bay in ("ppm-1", "ppm-2"):
        dcm = f"slot-1/module/{bay}/module/dcm"
        assert held.get(f"{dcm}/tx") == [LC_CAP], (dcm, dict(held))
        assert held.get(f"{dcm}/rx") == [LC_CAP]
        assert held.get(dcm, []) == []


def test_a_dcms_bore_cap_is_still_keyed_by_a_configuration(tmp_path):
    """The build can reach a DCM's bores by their deep key, although the kit
    cannot offer them (the module publishes no slot): `""` empties one, and a
    plug replaces the other."""
    out = build(_dcp2(tmp_path, {"slot-1/ppm-1": DCMS[2]},
                      {"slot-1/ppm-1/dcm/tx": "", "slot-1/ppm-1/dcm/rx": LC}),
                tmp_path / "o", LIB)
    held = seats(ET.parse(out / "dcp-2.ila-node.front.svg").getroot())
    dcm = "slot-1/module/ppm-1/module/dcm"
    assert held.get(f"{dcm}/tx", []) == []
    assert held.get(f"{dcm}/rx") == [LC]


def test_a_dcms_own_top_level_default_is_still_refused(tmp_path):
    """Task 3's ruling holds: a copy of ppm-dcm-40 declaring a top-level
    duplex cap, seated in an A22 bay, fails the build naming the default -
    a bay module's own slot has no key a configuration could empty."""
    root = tmp_path / "lib"
    _copy(root, "smartoptics/ppm-dcm-40", 1, "capped-dcm",
          lambda c: c.__setitem__("default", DUPLEX_CAP))
    _copy(root, "smartoptics/dcp-f-a22", 1, "a22-dcm",
          lambda c: [b["accepts"].append("test/capped-dcm@1") for b in c["bays"].values()])
    dev = shutil.copytree(LIB / "devices/smartoptics/dcp-2", tmp_path / "dcp-2") / "device.yaml"
    d = yaml.safe_load(dev.read_text())
    for v in d["views"].values():
        for b in ((v or {}).get("bays") or {}).values():
            if "smartoptics/dcp-f-a22@2" in (b.get("accepts") or []):
                b["accepts"].append("test/a22-dcm@1")
    d["configurations"]["ila-node"]["bays"] = {
        "slot-1": "test/a22-dcm@1", "slot-1/ppm-1": "test/capped-dcm@1",
        "slot-2": "smartoptics/dcp-2-blank@1"}
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    r = run(dev, tmp_path / "o", root)
    assert r.returncode != 0
    assert "test/capped-dcm@1" in r.stderr and DUPLEX_CAP in r.stderr, r.stderr[-600:]


# --- (c) a configuration still wins --------------------------------------------------

def test_an_fs_port_is_emptied_and_replaced_front_and_rear(tmp_path):
    """The FS 2 x MTP-12 LC cassette in bay-1. Front: lc01 emptied, lc02 given
    a duplex plug, lc03 emptied so a simplex plug takes its tx bore. Rear:
    mtp1 given an MPO plug, mtp2 emptied. Everything unkeyed keeps its cap."""
    occ = {"bay-1/lc01": "", "bay-1/lc02": DUPLEX,
           "bay-1/lc03": "", "bay-1/lc03/tx": LC,
           "bay-1/mtp1": MPO12, "bay-1/mtp2": ""}
    dev = shutil.copytree(LIB / "devices/fs/fhd-1ufce", tmp_path / "fhd-1ufce") / "device.yaml"
    d = yaml.safe_load(dev.read_text())
    d["configurations"]["base"]["bays"] = {"bay-1": "fs/fhd-2mtp12-lc-os2-a@4"}
    d["configurations"]["base"]["occupants"] = occ
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    out = build(dev, tmp_path / "o", LIB)
    front = seats(ET.parse(out / "fhd-1ufce.base.front.svg").getroot())
    m = "bay-1/module"
    assert front.get(f"{m}/lc01", []) == []
    assert front.get(f"{m}/lc02") == [DUPLEX]
    assert front.get(f"{m}/lc03", []) == [] and front.get(f"{m}/lc03/tx") == [LC]
    assert front.get(f"{m}/lc03/rx", []) == []
    capped = [h for h, v in front.items() if v == [DUPLEX_CAP]]
    assert len(capped) == 12 - 3 > 0, capped
    rear = seats(ET.parse(out / "fhd-1ufce.base.rear.svg").getroot())
    # the projection strips refs: the plug is a `connector`, the cap a `cap`
    assert rear.get(f"{m}/mtp1") != ["cap"] and len(rear.get(f"{m}/mtp1")) == 1
    assert rear.get(f"{m}/mtp2", []) == []


def test_a_smartoptics_port_is_emptied_and_replaced(tmp_path):
    """dcp-r-34d-cs: xc01's tx bore emptied and its rx bore given a plug;
    port-1510's two bores emptied so a duplex plug takes the adapter. Every
    other bore keeps its cap."""
    dev = shutil.copytree(LIB / "devices/smartoptics/dcp-r-34d-cs",
                          tmp_path / "dcp-r-34d-cs") / "device.yaml"
    d = yaml.safe_load(dev.read_text())
    assert not d.get("configurations")
    d["configurations"] = {"default": {"kind": "base", "default": True, "occupants": {
        "xc01/tx": "", "xc01/rx": LC,
        "port-1510/tx": "", "port-1510/rx": "", "port-1510": DUPLEX}}}
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    out = build(dev, tmp_path / "o", LIB)
    root = ET.parse(out / "dcp-r-34d-cs.default.front.svg").getroot()
    held = seats(root)
    assert held.get("xc01/tx", []) == [] and held.get("xc01/rx") == [LC]
    assert held.get("port-1510/tx", []) == [] and held.get("port-1510/rx", []) == []
    assert held.get("port-1510") == [DUPLEX]
    adapters = adapters_in(root, ("common/lc-duplex-adapter@6",))
    capped = [h for h, v in held.items() if v == [LC_CAP]]
    assert len(capped) == 2 * len(adapters) - 4 > 0


def test_a_duplex_plug_over_capped_bores_is_still_refused(tmp_path):
    """The exclusion (L115) now bites on the shipped state: a duplex plug on a
    Smartoptics adapter whose bores still hold their caps fails the build,
    naming the bore to empty."""
    dev = shutil.copytree(LIB / "devices/smartoptics/dcp-r-34d-cs",
                          tmp_path / "dcp-r-34d-cs") / "device.yaml"
    d = yaml.safe_load(dev.read_text())
    d["configurations"] = {"default": {"kind": "base", "default": True,
                                       "occupants": {"port-1510": DUPLEX}}}
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    r = run(dev, tmp_path / "o", LIB)
    assert r.returncode != 0
    assert "port-1510" in r.stderr and "cannot both be filled" in r.stderr, r.stderr[-600:]


def test_the_unplaced_mpo_tile_ships_its_cap_where_a_panel_composes_it(tmp_path):
    """common/mpo-adapter@2 is placed nowhere, so its default is proved on a
    tmp panel: a FS cassette copy whose lc01 and lc02 become MPO tiles - lc01
    left alone ships the cap on the tile's FORWARDED slot, lc02's composer
    entry empties it (P5)."""
    root = tmp_path / "lib"

    def tiles(c):
        for q in c["parts"]:
            if q["id"] == "lc01":
                q["ref"] = "common/mpo-adapter@2"
            if q["id"] == "lc02":
                q["ref"], q["default"] = "common/mpo-adapter@2", ""
    _copy(root, "fs/fhd-2mtp12-lc-os2-a", 3, "mpo-panel", tiles)
    g = compiled_face("test/mpo-panel@1", root)
    held = seats(g)
    tiles_ = adapters_in(g, ("common/mpo-adapter@2",))
    assert len(tiles_) == 2
    paths = {p.rsplit("/", 1)[1]: p for p, _r, _e in tiles_}
    assert held.get(paths["lc01"]) == [MPO_CAP]
    assert held.get(paths["lc02"], []) == []


# --- (e) L114 ------------------------------------------------------------------------

def _l110(f, roots):
    data = yaml.safe_load(f.read_text())
    with lint.collecting() as got:
        lint.lint_component_slot_defaults(f, data, roots)
    return [e for e in got.errors if "[L114]" in e]


@pytest.mark.parametrize("ref", sorted(SHIPS))
def test_lint_every_new_default_is_in_its_slots_accepts(ref):
    assert _l110(_contract_path(ref), [str(LIB)]) == []


@pytest.mark.parametrize("ref,wrong", [
    ("common/mpo-adapter@2", LC_CAP), ("common/mpo-flange-adapter@2", SC_CAP),
    ("common/lc-duplex-v-adapter@6", LC_CAP)])
def test_lint_finds_a_top_level_default_the_slot_does_not_take(tmp_path, ref, wrong):
    """Non-vacuity: L114 sees each adapter as a slot (the MPO tile through the
    aperture it forwards), so a cap of the wrong interface is found."""
    root = tmp_path / "lib"
    ns, rest = ref.split("/", 1)
    name, major = rest.split("@")
    f = _copy(root, f"{ns}/{name}", int(major), f"wrong-{name}",
              lambda c: c.__setitem__("default", wrong))
    got = _l110(f, [str(root), str(LIB)])
    assert got and wrong in got[0], got


@pytest.mark.parametrize("ref", ["common/lc-duplex-adapter@6", "common/sc-duplex-adapter@5"])
def test_lint_finds_a_bore_default_the_slot_does_not_take(tmp_path, ref):
    root = tmp_path / "lib"
    ns, rest = ref.split("/", 1)
    name, major = rest.split("@")

    def wrong(c):
        for q in c["parts"]:
            if q.get("id") in BORES:
                q["default"] = MPO_CAP
    f = _copy(root, f"{ns}/{name}", int(major), f"wrong-{name}", wrong)
    got = _l110(f, [str(root), str(LIB)])
    assert len(got) == 2 and MPO_CAP in got[0], got
