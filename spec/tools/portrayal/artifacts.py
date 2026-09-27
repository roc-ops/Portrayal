#!/usr/bin/env python3
"""Read a published Portrayal build the way a consumer outside this repo would.

THE POINT. The DCIM export knew the schema and also knew where the source tree
was, and only the first of those is essential. Everything it took off `library/`
is published: `<device>.source.json` is the whole device manifest (each
compiled SVG names it by digest in its `<metadata>`), components.json carries every contract field the export reads,
and vendors.json and overlays.json carry the rest. So the export can run against
`dist/` alone, which is what lets it live somewhere else - or be written by
somebody else, against a contract rather than against a checkout.

This module is that contract, in code. Nothing here opens a file under
`library/devices/` or `library/components/`.
"""
import functools
import json
from pathlib import Path


@functools.lru_cache(maxsize=None)
def _files_at(path, _mtime):
    idx = json.loads(Path(path).read_text())
    return {c["name"]: c.get("files") or {} for c in idx.get("configs") or []}


def _files(root, name):
    # keyed on the file's mtime too, so a build rewritten in place is re-read
    p = Path(root) / f"{name}.configs.json"
    try:
        return _files_at(str(p), p.stat().st_mtime_ns)
    except OSError:
        return {}


def face_file(root, name, config, view):
    """The compiled face `config` draws for `view`, or None where it draws none.

    Looked up in `<device>.configs.json` `configs[].files`, never built from
    the configuration's name: a drawing is written once and shared by every
    configuration that draws it identically (#665), so most configurations'
    faces carry another configuration's name.
    """
    f = _files(str(root), name).get(config, {}).get(view)
    return Path(root) / f if f else None


class Dist:
    """A published build. Everything the export needs, and nothing it does not."""

    def __init__(self, root):
        self.root = Path(root)
        self._devices = self._load("devices.json").get("devices") or []
        self._components = self._load("components.json").get("components") or []
        self._vendors = self._load("vendors.json")
        self._overlays = (self._load("overlays.json").get("overlays") or {})
        self._manifests = {}

    def _load(self, name):
        p = self.root / name
        if not p.exists():
            raise SystemExit(f"{p} is missing - run build.sh, or point --dist at a build")
        return json.loads(p.read_text())

    # ---- devices ------------------------------------------------------------

    @property
    def devices(self):
        """Index entries: name, ns, manufacturer, model, version, datasheet."""
        return list(self._devices)

    def device(self, name):
        for d in self._devices:
            if d.get("name") == name:
                return d
        raise SystemExit(f"no device {name!r} in {self.root}/devices.json")

    def manifest(self, name):
        """The device's own manifest - all six views, attrs, chassis,
        configurations, groups - as published in `<device>.source.json`.

        It used to be read back out of whichever drawing turned up first,
        because every face embedded it. They name it by digest now (#665) and
        it is published once per device. Memoised; it can run to 100 KB.
        """
        if name in self._manifests:
            return self._manifests[name]
        p = self.root / f"{name}.source.json"
        if not p.exists():
            raise SystemExit(f"{p} is missing - run build.sh, or point --dist at a build")
        src = json.loads(p.read_text())
        # the index carries what the manifest does not: `datasheet` is a
        # citation rather than geometry and is not part of the source
        idx = self.device(name)
        for k in ("datasheet", "ns"):
            if idx.get(k) and not src.get(k):
                src[k] = idx[k]
        self._manifests[name] = src
        return src

    # ---- components ---------------------------------------------------------

    @property
    def components(self):
        return list(self._components)

    def modules(self):
        """Component entries whose kind is `module`, with their namespace."""
        return [c for c in self._components if c.get("kind") == "module"]

    def module_models(self):
        """Every model the library carries as a MODULE, for telling a FRU part
        number from a chassis one."""
        out = set()
        for c in self.modules():
            m = str((c.get("attrs") or {}).get("model") or c.get("name") or "")
            if m:
                out.add(m)
        return out

    def component_by_ref(self, ref):
        """`common/mpo-adapter@2` -> its index entry, or None."""
        if not hasattr(self, "_by_ref"):
            self._by_ref = {
                f"{c.get('ns')}/{c.get('name')}@{str(c.get('major') or '')[1:]}": c
                for c in self._components}
        return self._by_ref.get(ref)

    def manufacturer_of(self, ns):
        """Which manufacturer ships a namespace.

        LEARNED FROM THE DEVICES FIRST, and that order is load-bearing rather
        than incidental: `dell` reports `Dell` from its devices and `Dell
        Technologies` from vendors.yaml, `juniper` reports `Juniper` against
        `Juniper Networks`, `edgecore` the same way. Looking in the registry
        first would rename the manufacturer on several hundred existing export
        files.

        THE REGISTRY IS THE FALLBACK, for a vendor that ships parts before it
        ships a chassis - FS sells cassettes that seat in an enclosure nothing
        has modelled yet, and requiring a device first is an accident of how
        this join was built rather than a statement about what is orderable.
        `common/` and `std/` stay absent because they are absent from
        vendors.yaml, so the rule this docstring used to state as a special case
        now holds by data.
        """
        for d in self._devices:
            if d.get("ns") == ns:
                return d.get("manufacturer")
        return (self.vendors.get(ns) or {}).get("display") or None

    # ---- registries ---------------------------------------------------------

    @property
    def vendors(self):
        return self._vendors.get("vendors") or {}

    def overlay(self, ns, model, profile):
        """A NOS overlay for a device, or None. Keyed <ns>/<model>."""
        if not profile:
            return None
        return (self._overlays.get(f"{ns}/{model}") or {}).get(profile)

    def profiles(self):
        """Every NOS some overlay in this build declares - the only NOSes an
        export can name interfaces for."""
        return {p for profs in self._overlays.values() for p in (profs or {})}
