"""The exporter's register tables: the parts it labels, hands power on from, or names as
not exported.

Every change that adds a maker's part the exporter must name adds one entry to one of these
tables, so this file is merged by union (see .gitattributes and
spec/tests/test_shared_lists_merge.py): two changes that each add an entry at the same place
both keep theirs, with no conflict to settle. That is safe only for a file that is nothing but
appended entries, so it holds `NAME = <literal>` tables and no function, no import and no
computed value - logic belongs in dcim_export.py. Write an entry once: a key written twice
fails the same test.
"""

# THE CONNECTOR A `other` POWER PORT IS, for a reader who would otherwise see
# "Other". Only the parts above that have no upstream type are listed; a test
# holds the two tables to each other.
POWER_LABEL = {
    "std/eps12v-header": "EPS12V 8-pin (CPU 8-pin)",
    "std/pcie-8pin-header": "PCIe 8-pin (6+2)",
    "std/12vhpwr-header": "12VHPWR 16-pin",
    "std/12v-2x6-header": "12V-2x6 16-pin",
    "common/pla03-receptacle": "Positronic PCS PLA03 (3-position)",
    "oscilloquartz/osa542x-dc-header": "Latching power header (3-position, - Gnd +)",
    "juniper/jpsu-150-dc-header": "DC power connector block (3-position, + - earth)",
    "cisco/nxa-pdc-930w-dc-header": "DC power connector block (3-position, - DC + DC earth)",
    "cisco/a9k-dc-header": "DC power connector block (2-position, +DC -DC)",
    "juniper/qfx5200-48y-dc-header": "DC power header (3-position, RTN, -36 to -72 V, grounding)",
    "juniper/qfx5210-dc-header": "DC power header (3-position, cells 1 to 3)",
    "juniper/qfx524x-dc-header": "DC power connector (6-position, 2x3)",
    "juniper/qfx10002-dc-header": "DC power connector (D-sub 3W3, -48 V, return, ground)",
    "juniper/ex4400-dc-header": "DC power connector (D-sub 3W3, -48 V, return, ground)",
    "edgecore/dcs201-dc-header": "Pluggable DC terminal (3-position, earth - +)",
    "edgecore/amx-3200-dc-header": "DC power connector (3-pin)",
    "edgecore/agr560-dc-header": "DC power connector (2-socket)",
    "edgecore/ais800-64-dc-header": "DC power connector (6-socket)",
    "smartoptics/dcp-2-dc-header": "DC power connector (3-cell)",
    "cisco/nc5k-pdc-930w-dc-header": "DC power connector block (3-position, - DC + DC earth)",
    "ufispace/psu-242-dc-header": "DC input connector (6-position, two rows of three, V+ over V-)",
    "rittal/pdu-cord-cee-16a": "CEE (IEC 60309) 16 A plug, 3P+N+PE",
    "servertech/pro4x-cord-60309": "IEC 60309 3P+N+G 6h plug on a fixed cord",
    "servertech/pro3x-cord-60309": "IEC 60309 3P+G 9h plug on a fixed cord",
    "raritan/px3-cord-60309": "IEC 60309 2P+E 6h 32 A plug on a fixed cord",
    "eaton/tripplite-cord-l5-30p": "NEMA L5-30P locking plug on a fixed cord",
    "raritan/px4-universal-input": "Legrand Universal Input connector (keyed)",
    "raritan/px3-rear-cord-60309": "IEC 60309 2P+E 6h 32 A plug on a fixed cord",
    "panduit/g5-cord-60309-2pe-6h": "IEC 60309 2P+E 6h 32 A plug on a fixed cord",
    "panduit/g5-cord-60309-3pe-9h": "IEC 60309 3P+E 9h 60 A plug on a fixed cord",
}

PART_OUTLET = {
    # ONE OUTPUT CIRCUIT OF A BREAKER PANEL, a BATT screw over an RTN screw: the
    # two poles of one circuit, so one outlet, as one feed is one power port.
    # `dc-terminal` is an outlet type as well as a port type upstream.
    "amphenol-ns/output-terminal": "dc-terminal",
    # ITS CONNECTORIZED FORM, a two-pole P40 receptacle. Neither target has a
    # P40 (or any Anderson Powerpole) outlet type, so it is `other` with the
    # connector as its label - OTHER_LABEL's treatment of an interface whose
    # form factor upstream does not name.
    "amphenol-ns/output-p40": "other",
    # A RACK PDU'S OUTLETS. An IEC C13 is upstream's `iec-60320-c13`, and it is a
    # std/ part: its face is the standard's, whoever moulds it. Eaton's C39 takes
    # a C14 or a C20 plug and is no IEC sheet - it is Eaton's own, and both targets
    # name it, so it is `eaton-c39` rather than `other`.
    "std/c13-outlet": "iec-60320-c13",
    "eaton/c39-outlet": "eaton-c39",
    # A SERVER TECHNOLOGY HDOT Cx OUTLET, a hybrid of the C13 and C19 that takes a C14 or a
    # C20. Neither target names it, so it is `other` with its label, as the P40 above is.
    "servertech/hdot-cx-outlet": "other",
    # A RARITAN PX4'S LOCKING Cx OUTLET, 16 A. Neither target names it, so it is `other` with its label.
    "raritan/px4-cx-outlet": "other",
    # A C19 OUTLET, upstream's `iec-60320-c19`, and a NEMA 5-20R, upstream's
    # `nema-5-20r` (it takes a 5-15P as well; the type names the receptacle).
    "std/c19-outlet": "iec-60320-c19",
    "std/nema-5-20r": "nema-5-20r",
    # A NEMA 5-15R, upstream's `nema-5-15r`.
    "std/nema-5-15r": "nema-5-15r",
    # A RITTAL PDU'S CEE 7/3 EARTHING-PIN SOCKET. No upstream outlet type for it has been
    # read from a held source, so it is `other` with the connector as its label.
    "rittal/cee-7-3-outlet": "other",
}

# The label an `other` outlet carries, so it says what to plug into it.
# test_power_outlets.py holds both tables to OUTLET_TYPES (an assert here would
# run on import, which test_tools_layout forbids).
OUTLET_LABEL = {"amphenol-ns/output-p40": "P40", "servertech/hdot-cx-outlet": "HDOT Cx",
                "rittal/cee-7-3-outlet": "CEE 7/3", "raritan/px4-cx-outlet": "Cx locking"}

# EVERY PORT-CLASS PART THIS EXPORTER NEVER EMITS, AND WHY IT DOES NOT.
#
# THE TABLES IN dcim_export.py SAY WHAT A PART IS. This says what the silence means for the
# parts none of them name, and it exists because the two are indistinguishable
# from outside: a 76-port router exporting nothing and a device with no ports
# produce the same document, and it took a person reading an output and asking
# "is that number right?" to tell them apart (#251). A count cannot do that and
# neither can a green gate. A NAME can.
#
# THE ENTRY CONDITION IS MEASURED, NOT GUESSED: a part whose `class` is `port`
# or `inlet` and not ONE of whose placements anywhere in the library reaches
# either export. A part that types on some placements and not others is not
# here - `std/rj45` types 32 of its 178 and the other 146 are timing and serial
# jacks it is right to refuse, which is `iface_type`'s own rule and not silence.
#
# test_silent_drops.py holds this exhaustive. A new port-class part that exports
# nothing fails that test until whoever added it either gives it a row above or
# writes down here why it has none - which is the whole of what was missing when
# XFP, OSFP and 800G each cost the library several hundred interfaces in a row.
# Writing a reason is cheap; ten of these say "upstream has no type for this",
# which is a fine reason and a very different one from "nobody noticed".
NOT_A_DCIM_PORT = {
    # --- fibre ---------------------------------------------------------------
    # `common/lc-duplex-adapter` WAS HERE until the trunk (#246): a PPM's
    # paths ran front-to-front and nothing named its network side, so no
    # placement anywhere exported. The PPMs now state `optical.trunk` and
    # export front and rear ports, so the register's stale-entry test took the
    # entry off - and the placements that still export nothing, 117 on DCP
    # chassis and two on the A22, are named in their own type's comments by
    # `unexported_optical` instead of falling through in silence (#204).
    "std/lc-bore": "the rx/tx bore of a transceiver, not a port on anything - see PART_SKIP",
    "std/sc-bore": "the SC/APC optical ports of single-faced CH3000 back plates (commscope/bp-a5, "
                   "bp-f2, bp-f4) and the half-depth passives and switch (np3*, op3*, "
                   "os32m2b); a bore drawn inside an active part, with no glass modelled "
                   "behind it and no trunk to terminate on",
    "common/sc-apc": "PON; the connector is the same ferrule for xg-pon (10G/2.5G) and "
                     "xgs-pon (10G/10G), which upstream separates, so the ref cannot pick "
                     "one - a device placement that states `pon` does, and exports "
                     "(device_port_type)",

    # --- power: a connector no DCIM has a type for ---------------------------
    "cisco/rps2300-connector": "the RPS connector of the Catalyst 2960-S switches: the guide names it and "
                               "gives no connector type or pinout, and no DCIM has a power port type for "
                               "it, so it cannot be typed honestly",
    "cisco/flexstack-port": "the FlexStack stacking port of the Catalyst 2960-S module: a vendor stacking "
                            "interface no DCIM has a port type for, so it cannot be typed honestly",
    "juniper/ex3300-rps-port": "the redundant power system port of the Juniper EX3300 switches: the "
                               "guide names the port and gives no connector type or pinout, and no "
                               "DCIM has a power port type for an RPS connector, so it cannot be "
                               "typed honestly",
    "ubiquiti/usp-rps-input": "the USP-RPS DC input of the Ubiquiti UniFi rack switches and Dream "
                              "Machine gateways, for an external redundant supply: the data sheets "
                              "name the input (and the switch's rating, 52 V DC at 7.69 A) and no "
                              "connector type, so it cannot be typed honestly",
    "juniper/ex2200-rps-port": "the redundant power system port of the Juniper EX2200 switches: the "
                               "guide names the port and gives no connector type, and no DCIM has a "
                               "port type for it, so it presents nothing and cannot be typed "
                               "honestly",

    # --- USB: real ports, no device-type field to put them in ----------------
    # A DCIM device type has console ports, power ports and interfaces. A USB
    # data port is none of those unless it is a console, which std/usb-a is on
    # the placements device_console_row catches. The rest are storage, maintenance
    # and iDRAC Direct, and there is nowhere honest to put them.
    # `std/micro-usb` WAS HERE, as "USB maintenance port (iDRAC Direct); not a
    # console". That was true of the two Dell servers and false of 31 devices
    # whose micro-USB jack is labelled Console; #384 gave those a console-port
    # path (device_console_row), and iDRAC Direct moved to MGMT_NOT_A_DCIM_PORT.
    "common/usb-a": "USB storage/maintenance port; not a console - std/usb-a's console placements type via device_console_row",
    "common/usb-a-bezel": "the same USB storage/maintenance port as common/usb-a, in a taller panel bezel; split out of that name's @3 in #264 and it needs its own entry because this register keys on the NAME, not the major",
    "raritan/pxo-usb-b": "the USB-B jack of the Raritan PXO controller: a device-side port for a phone or tablet, a computer "
                         "link (command line, recovery) and cascading - no document names it a console, and a DCIM device type "
                         "has no field for a USB data port",
    # `std/usb-c` WAS HERE, as the GL-8xEP's USB-C power input. It was stale: the
    # DS6000, DS6001 and AS7326-56X have exported a USB-C console all along, and
    # test_silent_drops' mirror of `build` did not know the console exit, so it
    # could not tell (#384). The GL-8xEP's power input is not a management port
    # and the census does not ask about it; the storage USB-Cs are in
    # MGMT_NOT_A_DCIM_PORT.

    # --- connectors upstream has no type for ---------------------------------
    "common/db9-receptacle": "the placements left here are alarm relays, status and craft ports - "
                             "a dry-contact relay or a monitoring link, not an RS-232 console. Neither "
                             "library has an alarm port, and `de-9` would read as a console. A placement "
                             "that IS a console (id, role or function `console`) exports as `de-9` "
                             "through DB9_CONSOLE",
    "std/da15": "the 7750 SR-e CCM-e alarm connector - dry-contact relays and alarm inputs on a "
                "DA-15, not RS-232. Neither library has an alarm port, and no console type is a DA-15",
    "std/db25": "the 7750 SR-12 DC PEM-3 AC Supply Status port - an AC rectifier shelf's status "
                "signalling on a female DB-25, not RS-232. `db-25` upstream is a CONSOLE type and "
                "this is not a console; neither library has an alarm or status port",
    "common/terminal-header-508-2": "the AurCore AIS switches' RELAY output - a dry-contact alarm "
                                    "relay on a two-way pluggable terminal, not a network port or a "
                                    "console. Neither library has an alarm port (#737)",
    "juniper/ex4100-h-alarm-connector": "the EX4100-H switches' dry contact alarm connector - two alarm "
                                        "inputs and a relay output (NO, COM, NC) on a six-pole pluggable "
                                        "terminal, not a network port or a console. Neither library has an "
                                        "alarm port",
    "juniper/ex4100-h-terminal-pad": "one of the twelve wire terminals behind the EX4100-H-24MP and -24F "
                                     "terminal door - L, N and G for an AC supply, DC+, DC- and G for a DC "
                                     "supply, for the supply slot of the same number. One terminal is not a "
                                     "power port: the pair of poles a feed lands on is, and which feed a "
                                     "slot carries depends on the supply seated",
    "std/vga": "VGA; neither library has a video port type",
    "common/vhdci-receptacle": "a VHDCI fan-out carrying sixteen timing outputs to a patch panel "
                               "over one cable; neither library has a type for it, and one row "
                               "could not stand for the sixteen outputs it carries",
    "common/vga-receptacle": "VGA; neither library has a video port type",
    "common/rj11-jack": "FXS analogue telephone line. `rj-11` upstream is a CONSOLE type; "
                        "an FXS line is not a console and must not read as one",

    # The three timing jacks were here until #285 gave `build` a PART_RF path
    # and added them to it. They now export as `other` with their connector,
    # and the register's stale-entry test is what took them off.

    # --- power entry on a chassis ---------------------------------------------
    # `common/dc-barrel` was here until #286 gave `build` a power path; it now
    # exports, and the register's stale-entry test is what says so.
    "nokia/sr-1-dc-terminal-block": "the 7750 SR-1 DC chassis's fixed -48 V terminal block - a "
                                    "barrier strip with its switch and cover, bolted to the rear. "
                                    "Its feeds are the chassis power inputs, stated in the "
                                    "device's power attrs; no connector here has a DCIM type",
    "casa/c40g-ac-inlet-panel": "an inlet PANEL - a bolted assembly carrying the receptacles, "
                                "not a connector; the C40G's own inlets are not modelled yet",
    # `amphenol-ns/output-terminal` and `amphenol-ns/output-p40` were here, as
    # power OUTLETS the exporter had no design for, until #806 gave them one:
    # PART_OUTLET. The register's stale-entry test is what took them off.
    "amphenol-ns/nrg-ils-rear-block": "the rear centre of an nrgILS panel: two nrgNET RJ45s, a "
                                      "private bus between panels, a temperature probe jack and three "
                                      "unnamed headers; none is a network interface a DCIM has a type for",
    "amphenol-ns/nrg-rear-block": "the rear centre of a monitored breaker panel: alarm relay "
                                  "headers, two RS485 nrgNET terminal connectors and two "
                                  "temperature probe jacks. None is a network interface a DCIM "
                                  "has a type for; nrgNET is a private serial bus between panels",
    "amphenol-ns/alarm-card-307608": "Form C alarm relay contacts on wire-wrap headers - dry "
                                     "contacts for an external alarm loop; neither DCIM has a "
                                     "port type for an alarm contact",
    "common/micro-dsub-50-receptacle": "the 50-pin micro D-sub CO alarm connector of the Nokia NGFC-H and "
                                       "NGFC-G cards - external alarm inputs and relay contacts, not a "
                                       "network port or a console; neither DCIM has a port type for an "
                                       "alarm connector",
    "common/wire-wrap-header-6": "the six-pin wire-wrap BITS timing header of the Nokia NGFC-H and NGFC-G "
                                 "cards - the BITS cables are wrapped to bare pins, and neither DCIM has "
                                 "a port type for such a header",

    # --- Virtual Chassis ---------------------------------------------------------
    "juniper/ex4200-vcp-port": "the 68-pin Virtual Chassis port of an EX4200: a proprietary stacking "
                               "connector that presents the registered interface ex4200-vcp, and "
                               "neither DCIM has a port type for it; the guide names it only as a "
                               "68-pin connector",
    "cisco/stackwise-480-port": "the StackWise-480 stacking port of the Catalyst 9300: Cisco's own "
                                "stacking connector, which presents the registered interface "
                                "stackwise-480, and neither DCIM has a port type for it; the guide "
                                "names it only as a StackWise-480 port connector",
    "cisco/stackpower-port": "the StackPower connector of the Catalyst 9300 (S-PWR 1 and 2): a "
                             "power-sharing link between switches, not a power input; neither DCIM "
                             "has a type for it and a power port would read as a feed",
    "digi/microsd-socket": "the micro-SD socket of the Digi Connect EZ 16 and 32: a memory card "
                           "slot, not a network, console or power connection, and neither DCIM "
                           "has a port type for a storage card",

    # --- test points and a serial jack ---------------------------------------------
    "common/g-type-male-port": "the G-type male -20 dB RF test point of the CommScope CH3000 receivers: a "
                               "monitoring tap, not a network interface, and neither DCIM has a port type "
                               "for a G-type connector",
    "common/g-type-female-port": "the G-type female -20 dB RF test point of the CommScope CH3000 DR3600N: a "
                                 "monitoring tap, not a network interface, and neither DCIM has a port type "
                                 "for a G-type connector",
    "common/stereo-jack": "the stereo-jack style RS-232 port of the CommScope CH3000 CX3003C and CX3033N, "
                          "reserved for factory use: not a console a DCIM manages, and neither DCIM has a "
                          "port type for it",

    # `dell/rj45-port-14g` USED TO BE HERE, as "a modelling gap, not an exporter
    # one": the NDC's four jacks carried no speed, so the exporter could not say
    # which two were 10GBASE-T and rightly refused to guess. #287 closed it by
    # reading the labels Dell's own master prints between the jacks, and the four
    # placements now declare their speed. The entry had to go with it - a register
    # of parts that export nothing is wrong about one that does.
    "opengear/sim-slot-4ff": "the 4FF SIM card slot of the CM8000's cellular models; a card slot, not a port, and no device-type field holds a SIM slot",
    "zpe/nsc-hdmi": "the HDMI video output of the Nodegrid Serial Console S; a video jack, not a port, and no device-type field holds a video output",
    "vertiv/sd-card-slot": "the full-size SD card slot of the ACS8000; a card slot, not a port, and no device-type field holds a card slot",
}

# THE MANAGEMENT CLUSTER'S PORTS THAT DO NOT REACH A DCIM, AND WHY (#384).
#
# NOT_A_DCIM_PORT asks of a PART whether it exports anywhere. That cannot see a
# part that exports on some placements and is dropped on others, which is how
# the DCS511's micro-USB console went missing: `std/micro-usb` was registered as
# an iDRAC Direct port, and the 31 devices that label one Console inherited the
# silence. So the management cluster is also counted PER PLACEMENT:
# test_dcim_mgmt_ports.py asks `build` itself (its `trace`) about every
# port-class placement whose role is mgmt, console or aux, or whose group's
# role is `management`, and each one that exports nothing must either be a part
# NOT_A_DCIM_PORT already explains or match a (part, placement role) key here.
#
# NO KEY MAY NAME role mgmt, console OR aux. Those are the ports a DCIM exists to
# know about, so the test refuses an exemption for them outright: a management
# jack, an SFP management port or a console that does not export is a defect,
# never an entry. What is left is USB storage and service ports, which no
# device-type field holds - device_console_row takes a USB jack, on a card too,
# only when the device says it is a console, and that is the existing line,
# drawn in NOT_A_DCIM_PORT's USB block before this register - and three jacks
# whose job is not one a DCIM has a type for.
MGMT_NOT_A_DCIM_PORT = {
    ("std/usb-a", None): "a USB-A port the device gives no role - service and storage on servers "
                         "and switches alike; not a console, and no device-type field holds a USB "
                         "data port (NOT_A_DCIM_PORT's USB block)",
    ("std/usb-a", "storage"): "a USB storage port; not a console, and no device-type field holds a "
                              "USB data port (NOT_A_DCIM_PORT's USB block)",
    ("std/usb-a", "maintenance"): "a USB maintenance port; not a console, and no device-type field "
                                  "holds a USB data port (NOT_A_DCIM_PORT's USB block)",
    ("std/usb-a", "ilo-service"): "HPE iLO Service Port, a USB link to the BMC for a laptop or a "
                                  "key; not a console, and no device-type field holds it",
    ("std/micro-usb", None): "iDRAC Direct on the Dell R660 and R740xd - a USB maintenance link to "
                             "the BMC, not a console; no device-type field holds it",
    ("std/micro-usb", "storage"): "a micro-USB storage port (the EPS121/EPS122); not a console, and "
                                  "no device-type field holds a USB data port",
    ("std/usb-c", None): "the GL-12xB-240D's USB-C, printed USB beside the CONSOLE jack; its "
                         "device records a `usb-function` gap - console, storage or power is "
                         "unknown - and an unknown job is not exported as a console",
    ("std/usb-c", "storage"): "a USB-C storage port (the AIS800s, the CSR440); not a console, and no "
                              "device-type field holds a USB data port",
    ("std/usb-c", "time-of-day"): "the Arista 7280DR3A-36's Time-of-Day connector, a USB-C whose mate "
                                  "is the CAB-SYNCE-RJ adapter to two RJ-45; a timing input, not a "
                                  "console, and no device-type field holds it",
    ("std/rj45", None): "the MX104's ext-ref-clock, a bare RJ-48 timing input that states neither "
                        "a speed nor a timing word; iface_type's guard refuses it, and it has "
                        "never exported",
    ("std/rj45-ganged", "alarm"): "an alarm-contact jack (the CSR440); neither library has an alarm "
                                  "port, and rj-45 would read as a console",
    ("std/rj45-ganged", "timing"): "the CSR180's stack-a-upper, which its own device marks "
                                   "`timing: unidentified` - there is no true type to give a jack "
                                   "nobody has identified",
}
