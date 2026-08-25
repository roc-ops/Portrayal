#!/usr/bin/env python3
"""Export an Portrayal device manifest as a Nautobot devicetype-library YAML file.

Portrayal is the source of truth for the physical facts; a DCIM is one consumer of
them. This emits the schema used by github.com/nautobot/devicetype-library so a
device we have modelled can be loaded straight into Nautobot without anyone
re-typing port counts by hand.

Interface names come from a NOS profile, because they are a property of the
network OS rather than the hardware: the same AS7326-56X is swp1-swp56 under
ArcOS and Ethernet0/4/8... under SONiC.

  python3 nautobot_export.py DEVICE_YAML --nos arcos --out DIR
"""
import argparse
from pathlib import Path

import yaml

# Portrayal media/speed -> Nautobot interface type
IFACE_TYPE = {
    ("sfp", "25g"): "25gbase-x-sfp28",
    ("sfp", "10g"): "10gbase-x-sfpp",
    ("sfp", "1g"): "1000base-x-sfp",
    ("qsfp", "100g"): "100gbase-x-qsfp28",
    ("qsfp", "40g"): "40gbase-x-qsfpp",
    ("rj45", "1g"): "1000base-t",
}
AIRFLOW = {"front-to-back": "front-to-rear", "back-to-front": "rear-to-front"}


def nos_name(profile, kind, n):
    """Interface name for a port, per NOS convention."""
    if profile == "arcos":
        return {"switch": f"swp{n}", "mgmt": "ma1"}[kind]
    if profile == "sonic":                    # SONiC numbers by lane, not by port
        return {"switch": f"Ethernet{(n - 1) * 4}", "mgmt": "eth0"}[kind]
    raise SystemExit(f"unknown NOS profile: {profile}")


def build(dev, profile):
    ch = dev.get("chassis", {})
    attrs = dev.get("attrs", {})
    out = {
        "manufacturer": dev["manufacturer"],
        "model": dev["model"].split(" (")[0],
        "slug": dev["name"],
        "u_height": float(ch.get("ru", 1)),
        "is_full_depth": True,
    }
    pns = sorted((dev.get("part-numbers") or {}).values())
    if len(pns) == 1:
        out["part_number"] = pns[0]
    elif pns:                                  # many SKUs share one model: mask the tail
        common = pns[0]
        for q in pns[1:]:
            common = "".join(a for a, b in zip(common, q) if a == b)
        out["part_number"] = common + "x" * (len(pns[0]) - len(common))
    if ch.get("weight-kg"):
        out["weight"] = float(ch["weight-kg"])
        out["weight_unit"] = "kg"
    cfgs = dev.get("configurations") or {}
    flows = {AIRFLOW.get(c.get("airflow")) for c in cfgs.values() if c.get("airflow")}
    flows.discard(None)
    if len(flows) == 1:
        out["airflow"] = flows.pop()
    if dev.get("datasheet", {}).get("url"):
        out["comments"] = dev["datasheet"]["url"]

    console, mgmt_rj, mgmt_sfp, bays = [], [], [], []
    for view in (dev.get("views") or {}).values():
        for p in (view or {}).get("placements", []) or []:
            a = p.get("attrs") or {}
            role, media = a.get("role"), a.get("media")
            if role == "console" and media == "rj45-serial":
                console.append({"name": "Console", "type": "rj-45"})
            elif role == "console" and p["ref"].startswith("std/usb-c"):
                console.append({"name": "Console (USB-C)", "type": "usb-c"})
            elif role == "mgmt" and media == "rj45":
                mgmt_rj.append({"name": nos_name(profile, "mgmt", 0),
                                "type": "1000base-t", "mgmt_only": True})
            elif role == "mgmt" and a.get("speed") == "10g":
                # faceplate-numbered but not ASIC ports - ArcOS presents no swp for
                # these, so they keep their silkscreen label and say why
                mgmt_sfp.append({"name": p["id"].replace("port-", ""),
                                 "type": "10gbase-x-sfpp", "mgmt_only": True,
                                 "description": "10G management port (faceplate label; "
                                                "not presented as a switch interface)"})
        for b in (view or {}).get("bays", []) or []:
            if b.get("group") in ("psus", "fans"):
                bays.append({"name": b["id"].replace("psu-", "PSU ").replace("fan-", "Fan "),
                             "position": b["id"].rsplit("-", 1)[-1]})

    # management first, then switch ports ordered by faceplate number
    ifaces = mgmt_rj + sorted(mgmt_sfp, key=lambda i: i["name"])
    ports = []
    for view in (dev.get("views") or {}).values():
        for p in (view or {}).get("placements", []) or []:
            if not p["id"].startswith("port-"):
                continue
            a = p.get("attrs") or {}
            if a.get("role") in ("mgmt", "console"):
                continue
            ref = p["ref"]
            fam = ("qsfp" if "qsfp" in ref else
                   "rj45" if "rj45" in ref else
                   "sfp" if "sfp" in ref else None)
            if fam is None:
                continue
            speed = a.get("speed") or {"qsfp": "100g", "sfp": "25g", "rj45": "1g"}[fam]
            t = IFACE_TYPE.get((fam, speed))
            if t is None:                      # unknown combination: skip, do not guess
                continue
            try:
                n = int(p["id"].split("-")[1])
            except ValueError:
                continue
            ports.append((n, t))
    for n, t in sorted(set(ports)):
        ifaces.append({"name": nos_name(profile, "switch", n), "type": t})

    if console:
        out["console-ports"] = console
    if ifaces:
        out["interfaces"] = ifaces
    if bays:
        out["module-bays"] = sorted(bays, key=lambda b: (b["name"].split()[0], int(b["position"])))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("device")
    ap.add_argument("--nos", default="arcos")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    dev = yaml.safe_load(Path(args.device).read_text())
    doc = build(dev, args.nos)
    if not doc.get("interfaces"):
        print(f"skip {dev['name']}: no interfaces resolved for this profile")
        return
    out = Path(args.out) / dev["manufacturer"]
    out.mkdir(parents=True, exist_ok=True)
    f = out / f"{doc['model']}-{args.nos}.yaml"
    class Indented(yaml.SafeDumper):          # match the library's list indentation
        def increase_indent(self, flow=False, indentless=False):
            return super().increase_indent(flow, False)

    f.write_text("---\n" + yaml.dump(doc, Dumper=Indented, sort_keys=False,
                                     width=100, default_flow_style=False))
    print(f"{f}  ({len(doc.get('interfaces', []))} interfaces, "
          f"{len(doc.get('module-bays', []))} module bays)")


if __name__ == "__main__":
    main()
