# Interface names for a general-purpose OS on a server (design record)

Status: a record of what is settled and what is not. It adds no schema key, no
library file and no export. `docs/listing-a-nos.md` is the mechanism it is
read against.

A Linux server has interface names too. They are a map from a physical
position to a logical name, the same shape as a switch's `port-4` to `swp4`.
This page records where that map fits the listing mechanism, where it does not,
and what a first entry may and may not claim.

## The line to hold

A **listing** files a device type under the software vendor. That vendor is on
the invoice: ArcOS, OcNOS and DriveNets sell the software with the box.
`docs/listing-a-nos.md` says what it exports: one device type per hardware
configuration, under the NOS vendor.

An operating system that is only what happens to be installed is not sold with
the box. Nobody sells "Ubuntu on an R640": the maker sells the server and
another company sells a support subscription. A listing under that company
would put a device type in a DCIM for a purchase that never happened, once per
hardware configuration it names.

So for a server OS the names may be recorded, and **no device type is exported
under the OS vendor**.

## What the names depend on

For a switch, the hardware and the NOS mostly fix the names. For Linux the
names also depend on the items below. A record may not claim to resolve them:

| depends on | effect |
|---|---|
| systemd and udev version | an older distribution gives `eth0`; predictable names came with systemd 197 |
| firmware | whether SMBIOS or ACPI gives an onboard index decides `eno1` against `enp3s0f0` |
| kernel command line | `net.ifnames=0` reverts to `eth0` |
| netplan or udev rules on the box | rename anything |

Two consequences follow. The OS version field stays free text. A record states
**which naming scheme applies and what it depends on**. A name that has a
firmware variable inside it is stated only with that dependence flagged in the
scheme record.

## What is stable enough to source

| name form | derived from | sourceable from |
|---|---|---|
| `eno<N>` | onboard index supplied by firmware | the maker's per-model manual |
| `ens<S>f<F>` | hotplug slot number | the maker's slot numbering for that model |
| `enp<B>s<D>f<F>` | PCI bus, slot, function | a dump from a live unit only |
| `eth<N>` | no predictable naming | nothing: it is order of discovery |

The `enp` form depends on PCI enumeration order. A manual cannot assert it. It
needs a committed, sanitised dump from a unit. That is how the ArcOS naming for
a white box is read: from a live capture, filed beside the hardware under
`dumps/`.

## What the library holds today

- A server is modelled once, under its maker. Seven Dell rack servers are in
  `library/devices/dell/`: `r660`, `r660xs`, `r6615`, `r6625`, `r740xd`,
  `r760` and `r960`. The R640 is not among them.
- Onboard ports are drawn as a module, for example
  `dell/lom-2x1g-16g` with ports `port-1` and `port-2`. A name rule would
  point at those ids.
- The only per-OS file kind is `kind: listing`, which exports under the
  software vendor. No file in the library says `kind: overlay`.
- No document held for Dell's rack servers states a Linux interface name. The
  held Dell manuals, specification sheets and technical guides were searched
  for `eno`, `ens`, `enp`, `systemd`, `udev` and `biosdevname`. They are kept in
  the intake corpus, not in this repository. The search finds nothing. So no
  `eno` or `ens` name has a source yet.

## Open

Each of these changes what a consumer reads, so none is settled here.

1. **File kind.** Record the names as a second kind of file that exports no
   device type, or as a listing flagged as exporting none. The first adds a
   file kind and a schema; the second changes what a listing promises. Both are
   one-way once published.
2. **The scheme record.** A field that names the scheme and what it depends
   on, in place of a bare `nos-versions` string.
3. **Slots.** An `ens` name needs the slot number of each card position, and
   an `enp` name the bus topology.
4. **First entry.** Ubuntu on one PowerEdge, with the `eno` and `ens` names
   taken only from a Dell document naming them. A model must be chosen and
   modelled first if it is not one of the seven.

## What a first entry may not do

- Export a device type under the OS vendor.
- Assert an `enp` name without a live dump.
- Derive one OS's names from another's, or one generation's from another's.
- Claim a name for a configuration where firmware, kernel options or local
  rules may change it, without saying so in the scheme record.
