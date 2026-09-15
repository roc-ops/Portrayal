#!/usr/bin/env python3
"""Read a published Portrayal build the way a consumer outside this repo would.

THE POINT. The DCIM export knew the schema and also knew where the source tree
was, and only the first of those is essential. Everything it took off `library/`
is published: the compiled SVG carries the whole device manifest in its
`<metadata>`, components.json carries every contract field the export reads,
and vendors.json and overlays.json carry the rest. So the export can run against
`dist/` alone, which is what lets it live somewhere else - or be written by
somebody else, against a contract rather than against a checkout.

This module is that contract, in code. Nothing here opens a file under
`library/devices/` or `library/components/`.
"""
import json
import re
from pathlib import Path
from xml.sax.saxutils import unescape

_META = re.compile(r"<metadata[^>]*>(.*?)</metadata>", re.S)


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
        """The device's own manifest, read back out of a drawing of it.

        Every compiled SVG embeds the source it was made from - all six views,
        attrs, chassis, configurations, groups - so ANY view of ANY configuration
        answers this. The first one found is used and the result memoised,
        because a 2 MB SVG is not a thing to parse twice.
        """
        if name in self._manifests:
            return self._manifests[name]
        for svg in sorted(self.root.glob(f"{name}.*.svg")) + \
                   sorted(self.root.glob(f"{name}.svg")):
            m = _META.search(svg.read_text())
            if not m:
                continue
            # THE MANIFEST LIVES INSIDE XML, SO IT ARRIVES ESCAPED. The
            # renderer writes JSON into a <metadata> text node and ElementTree
            # escapes &, < and > on the way in. Reading it back with a regex
            # gets those literally: an Edgecore compliance string came out as
            # "IEC/EN60950-1 &amp; IEC/EN 62368-1", which is not what any
            # consumer of the source ever saw. Caught by diffing this exporter's
            # output against the source-read version it replaces.
            src = (json.loads(unescape(m.group(1))) or {}).get("source")
            if src:
                # the index carries what the manifest does not: `datasheet` is a
                # citation rather than geometry and is not embedded in a drawing
                idx = self.device(name)
                for k in ("datasheet", "ns"):
                    if idx.get(k) and not src.get(k):
                        src[k] = idx[k]
                self._manifests[name] = src
                return src
        raise SystemExit(f"no drawing of {name!r} in {self.root} carries a manifest")

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
        """`common/mpo-adapter@1` -> its index entry, or None."""
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
