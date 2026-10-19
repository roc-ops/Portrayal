# Comparable facts, the second pass: breakout, compliance-programme, macsec, routing, service-port

Status: proposal, 2026-10-19. Nothing here is built, and nothing in the schemas,
the library, the tools or the tests changes with this note. It answers #112 (the
next pass of the census the comparison layer publishes, after #99) and ends in
nine questions, each answerable in one line.

Every count below was taken on `origin/main` at `76e66b639` by a read-only
script that walks `library/devices/*/*/device.yaml`, keeps the manifests whose
`kind` is `device` (258), flattens each one's `attrs` the way
`comparable._flat` does, and counts what `comparable.unclaimed` leaves
(`spec/tools/portrayal/comparable.py`). A "vendor" is the first directory under
`library/devices/`; its `manufacturer` strings agree with it for every device
named here. The script is not part of the commit. #112's own numbers are from an
earlier commit; where they differ the table below says so.

No outside document was needed. Every value quoted is a string a device already
carries, with its provenance in that device's file.

## The problem

#99 left the census open on purpose, and #112 names five spellings that recur and
have near-synonyms nothing reconciles: `breakout`, `compliance-programme`,
`macsec`, `routing` and `service-port`. On `main` the library has grown to 258
devices and the census to 454 unclaimed spellings, 160 of them on one device
(#99: 178, of which 102). The five are no longer at the head of it: their head
spellings rank 33, 118, 37, 49 and 195 (#112: 22, 30, 5, 6, 49), because the census
now carries the cable managers' and PDUs' keys (`material` 46, `mounting` 45,
`cooling` 41). The five families do still exist and still do not line up: the
recount finds 34, 57, 21, 31 and 27 devices under the spellings #112 lists. But
not one of them is a clean family. `port-modes-*` mostly states the rates a cage
runs, not a breakout; `encryption` on one of three devices is IPsec; `tpm` is a
platform module; two of the seven "routing" spellings carry management protocols
and a chip name; `service-port` is the word UfiSpace uses for a front-panel data
port. This note therefore proposes **three new facts and one extension, not five**
(`macsec`, `srv6`, `usb`, and two qualified readings on `nebs`), and leaves
`breakout` and the rest of `compliance-programme` alone.

## The counts, #112 against `main`

"Devices" is the number of devices carrying at least one of the family's
spellings, claimed or not. Vendors: #112 and the recount, both by directory.

| family | spellings | devices: #112 | devices: `main` | vendors: #112 | vendors: `main` |
|---|---|---|---|---|---|
| breakout | 12 listed (#112's text says 15) | 22 | 34 | celestica, edgecore, juniper, ufispace | + cisco |
| compliance-programme | 6 | 28 | 57 (17 once `nebs` is left out) | cisco, edgecore, ufispace | + amphenol-ns, eaton, oscilloquartz, supermicro, telco-systems |
| macsec | 3 | 12 | 21 (14 once `tpm` is left out) | celestica, edgecore, juniper, ufispace | + cisco, maiaedge; edgecore is `tpm` only |
| routing | 7 | 23 | 31 (19 for `routing`, `segment-routing`, `srv6`) | ufispace only | the 19 are still ufispace only; `protocols` and `forwarding` add eaton, nokia, oscilloquartz |
| service-port | 7 | 21 | 27 | juniper, ufispace | + celestica, cisco |

Where the spellings themselves differ:

| family | #112 | `main` |
|---|---|---|
| breakout | `port-modes-qsfp28` 7, `breakout` 5, `port-modes-sfp28` 4, `sfp28-sharing` 3, `zr-ports` 3, `port-modes-qsfpdd` 2, one each: `serdes-modes`, `combo-ports`, `rate-selectability`, `op2-option-ports`, `op2-disabled-ports`, `uplinks` (twelve spellings; the text says fifteen) | `port-modes-qsfp28` 12, `breakout` 11, `port-modes-sfp28` 6, `sfp28-sharing` 3, `zr-ports` 3, `port-modes-qsfpdd` 2, one each: the same six |
| compliance-programme | `nebs` 24, `nebs-emc-safety` 7, `nebs-physical` 7, `compliance-programme` 4, `other-approvals` 2, `certifications` 1 | `nebs` 50, `nebs-emc-safety` 7, `nebs-physical` 7, `certifications` 4, `compliance-programme` 4, `other-approvals` 2 |
| macsec | `macsec` 10, `encryption` 1, `tpm` 1 | `macsec` 11, `tpm` 7, `encryption` 3 |
| routing | `routing` 10, `segment-routing` 5, `srv6` 4, `tsn` 3, `flexe` 2, `forwarding` 2, `protocols` 1 | `routing` 10, `protocols` 7, `segment-routing` 5, `forwarding` 4, `srv6` 4, `tsn` 3, `flexe` 2 |
| service-port | `usb` 14, `service-port` 3, `sfp-plus-management` 2, one each: `inband`, `inband-mgmt`, `sfp-management`, `console-usb-driver` | `usb` 20, `service-port` 3, `sfp-plus-management` 2, one each: the same four |

Three things moved for a reason other than growth:

- `nebs` and `forwarding` are **claimed now** (`nebs` by #99; `forwarding` by
  `forwarding-rate`, `comparable.py`). #112 counted them as part of the family;
  they are not in the unclaimed census, and the 17 in the compliance row is the
  devices left on spellings nothing claims.
- `protocols` was one UfiSpace device (`m3000-14xc`, `CLI, SNMP, NETCONF`) and is
  now seven: that UfiSpace device, two Eaton PDUs and four Oscilloquartz clocks. It is
  management protocols, not routing.
- `oem-alias`, which #99 listed among the census's top, is not an `attrs` key on
  `main` (it appears only in `spec/tests/test_aliases.py`).

## What a promotion costs, mechanically

A fact is a `Fact(name, section, unit, kind, sources)` in `FACTS`
(`comparable.py`); `sources` is a list of `A(key, basis, qualifier)`. Adding one:

- `comparable_index.py` needs no change. It publishes the vocabulary from `FACTS`
  and the values from `resolve()`, and writes `comparable-facts.json` into
  `library/dist`. That file is a build output: `git ls-files library/dist` is empty,
  no manifest holds it, and `dcim_export.py` does not import `comparable`. So no
  lock moves and no export changes.
- `CLAIMED` grows by the claimed spellings, so `unclaimed()` stops listing them
  and lint L68 (`lint_library_comparable_facts`, `lint.py`) stops counting them in
  its warning. L68 builds its message from the census each run, so it needs no edit.
- `test_no_fact_shares_a_source_key_with_another` holds rule 1 structurally: a
  spelling belongs to one fact. Every option below keeps to it.
- L40 (`lint_device_port_optics`) reads `attrs` directly, not through
  `comparable`. Claiming a `port-modes-*` key would not change what L40 reports;
  it would change what the key *means*, which is the real overlap (see breakout).
- A fact may take its sources from more than one `attrs` section, but L68 holds
  each *key* to one section across the library. Every key proposed below is already
  in one section, so none trips it.

The three states a fact can be in (stated, vendor-silent through a `fact:<name>` gap,
omitted) apply to a new fact unchanged. A blank on a new column means nobody has
looked, not that the box lacks it.

## The proposal, one candidate at a time

| candidate | recommendation | result |
|---|---|---|
| breakout | **leave**; claim no `port-modes-*` key; wait for the structured field | no new fact |
| compliance-programme | **merge** `nebs-emc-safety` and `nebs-physical` into `nebs` as qualified readings; **leave** the other four spellings | `nebs` gains two sources |
| macsec | **promote** `macsec` | new fact `macsec`, 11 devices now, 13 after two renames |
| routing | **promote** one protocol fact, `srv6`, on three spellings; **leave** `flexe`, `tsn`, `protocols` | new fact `srv6`, 19 devices |
| service-port | **do not promote under this name**; **promote** the USB port as `usb`; **leave** the SFP+ management ports | new fact `usb`, 23 devices |

### 1. breakout: leave

#112 settles first that `breakout` overlaps L40, which governs `port-modes-*` and
`optics-*` and says "this rule harvests; it does not design". The recount shows
the overlap is deeper than the rule's wording.

The nine `port-modes-*` spellings on `main` (none claimed) carry 36 readings
across the library. **Eight say "breakout"**
(`port-modes-qsfp28` 4, `port-modes-qsfpdd` 2, `port-modes-osfp224` 2). The rest
state the rates a cage runs: `40/100G` on five UfiSpace boxes, `1/10/25G` on
five, "10, 40 and 100 Gigabit Ethernet" on two Cisco ones. That is a native-rate
fact, not a breakout, and it has a structured home since PR #1165 (merged
2026-10-18): a group's `speeds`, published as `data-speeds`
(`docs/format-stability.md`), "native rates only, no breakout". One device
carries `speeds` so far (`ufispace/s9600-72xc`), and `comparable.py` does not
read it. Claiming `port-modes-qsfp28` for a `breakout` fact would put
"40/100G" under the name of a breakout and make a comparison say that
`ufispace/s9110-32x` breaks out.

Two further findings the L40 rule hides:

- **The two spellings that carry breakout are off the cage vocabulary.**
  `PLUGGABLE_CAGES` (`lint.py`) names the media `qsfp-dd`, so L40 pairs it with
  `port-modes-qsfp-dd` (3 devices). `edgecore/cor580` and `dcs510`, the two boxes
  that state a QSFP-DD breakout, write `port-modes-qsfpdd`, which no group's media
  reaches. L40 does not warn about an unreachable `port-modes-*` key (it does for
  `optics-*`). `port-modes-osfp224` (2 devices) does not match the cage name
  `osfp` either.
- **Breakout is also said inside keys that are already claimed.** Six `optics-*`
  keys carry the word in their values (`optics-qsfp28` 5, `optics-sfp-plus` 4,
  `optics-sfp28` 3, `optics-qsfp-dd` 2, `optics-osfp` 1, `optics-qsfp112` 1).
  Five of them are claimed by their optics fact (`optics-qsfp112` is not). By rule 1
  they stay there, so a `breakout` fact built from keys could never see them.

The other spellings are not breakout either: `zr-ports`, `op2-option-ports` and
`op2-disabled-ports` are port sets and qualifiers (#112 already suspects the
last); `combo-ports` is an RJ45/SFP choice; `serdes-modes` is a SerDes rate;
`uplinks` on `s9725-64e` is two SFP+ management ports; `rate-selectability` is
one device. `sfp28-sharing` (3) is lane sharing, and the three S9600s that call it
`breakout` are lane sharing too.

The merged note `docs/breakout-design.md` (PR #1169, merged; `main` holds it)
covers the structured field and says breakout "belongs to the NOS layer": the
listing's `interfaces[].breakout.modes`. It also leaves this open as its question
6: whether a comparison fact for breakout reads only the structured rule. That
decides everything here, because `comparable.resolve(doc)` reads one device
manifest and a listing is a separate file. This note does not decide it.

**Options.**

- **A. One `breakout` fact absorbing the prose.** All twelve spellings, or just
  the `port-modes-*` and `breakout` ones. Costs a second answer to L40's
  question and puts native rates under a breakout name. Breaks "unlike facts stay
  unlike" for `zr-ports` and `combo-ports`. Not recommended.
- **B. A `breakout` fact on the key `breakout` alone.** 11 devices; 8 once the
  three S9600 keys are renamed to `sfp28-sharing` as `docs/breakout-design.md`
  proposes (its question 3). Eight devices, from Celestica and UfiSpace, in free
  prose ("4x25G", "8 x 100GbE, 4 x 200GbE or 2 x 400GbE per 800G port"). It would
  compare prose with prose and then be superseded if that note's question 6 is
  answered "read the structured rule".
- **C. Per-media `port-modes` facts, like the optics family.** One fact per
  media for the nine spellings: the native-rate question per cage, which is a
  different fact from breakout and is the one these keys mostly answer. Against
  it: rule 2 (structured beats prose) now has a structured home for native rates
  in `speeds`, so these would be prose facts for something the schema states;
  the `qsfpdd` spelling would need a library edit first; and coverage per
  spelling is 1 to 12 devices, mostly under the reach any promotion so far has
  had (question 1). The alternative is to treat the native-rate `port-modes-*`
  prose as superseded by `speeds` once groups carry it, as `SUPERSEDED` does for
  the redundancy prose; one device does so far.
- **D. Leave.** Claim nothing; the five readings stay in the census.

**Recommendation: D**, with C raised as question 2. It adds nothing a build would
have to take back, and it does not pre-empt the structured field.

### 2. compliance-programme: merge into `nebs` what is NEBS, leave the rest

#112's question: is what is left a fact about *programmes a box is accepted into*
rather than *specifications it meets*? Reading the 17 devices' values:

- `nebs-emc-safety` ("GR-1089-CORE: NEBS EMC and Safety") and `nebs-physical`
  ("GR-63-CORE: NEBS Physical Protection") are on seven Cisco ASR 9000 chassis
  (`asr-9006`, `9010`, `9904`, `9906`, `9910`, `9912`, `9922`), each of which also
  carries `nebs` ("SR-3580: NEBS Criteria Levels (Level 3)"). They are parts of
  the NEBS statement Cisco splits in three. The same mechanism handles it as the
  weight family: `A(key, qualifier=...)` gives a reading that is real but not the
  headline. Merged into `nebs` they would read as
  `nebs: Level 3 (headline); emc-safety: GR-1089; physical: GR-63`.
- `compliance-programme` (4 devices) is not one thing. One value is a programme
  ("OCP Accepted and TIP DCSG compliant", `s9500-30xs`). Three are conformance
  to standards ("IEEE 802.1CM fronthaul; ITU-T G.8273.2 T-BC Class C",
  `s9600-30dx`, `s9600-32x`, `s9600-72xc`), a timing and fronthaul profile that
  belongs beside `timing`, not with the paperwork. The key name is the
  misleading part. #112's suspicion is right for one device in four.
- `certifications` (4: three Eaton PDUs, `edgecore/as7946-74xksb`) and
  `other-approvals` (2: `s7801-54xs`, `s8901-54xc`, "MTCTE; NOM") are lists of
  marks and country approvals. `as7946-74xksb`'s sentence runs safety, EMC, CB,
  CE, FCC and RoHS together, so it spans `safety`, `emc` and
  `environmental-directives` and cannot be split without parsing.

**Options.**

- **A. A new fact `approvals`** on `certifications` and `other-approvals`, six
  devices. Under the reach of every earlier promotion, and the values mix
  safety marks, EMC standards and country approvals. Not recommended yet.
- **B. A new fact `compliance-programme`** on the four-device key. Four
  different claims under one name; the exact thing "unlike facts stay unlike"
  refuses.
- **C. Merge the Cisco pair into `nebs`; leave the rest.** Costs two
  `A(...)` lines. A comparison of the ASR 9000s with the others shows the
  headline unchanged and two more readings. Nothing breaks; a consumer that
  reads only `readings[0]` of `nebs` still gets the headline if `nebs` stays the
  first source.
- **D. Leave all.**

**Recommendation: C.** Whether the 802.1CM / G.8273.2 values belong to `timing`
is open (question 4); moving them is a library edit.

### 3. macsec: promote

`macsec` is on 11 devices from three vendors (Cisco `asr-9902`, Juniper `mx304`,
nine UfiSpace), all filed under `features`. Its values read as scope, not as
yes/no ("all forty-eight ports", "inline MACsec on all ports at all speeds",
"point-to-point MACsec", "supported; the two cyan-banded SFP+ ports 26-27 are the
MACsec pair"). The key being present is the statement. A reader should not be
shown a blank as "no MACsec"; the three-state rule already says so.

#112's fourth point holds:

- **`tpm` is not `macsec`** (7 Edgecore devices, `platform`). It stays out.
  It is a candidate for its own fact, shaped like `bmc`; seven devices is under the
  reach of anything promoted so far (question 1).
- **`encryption` is not one fact.** Its three devices are `celestica/es1000` and
  `es1010` ("256b MACsec") and `maiaedge/pbc-2000` ("aes-256-gcm-ipsec", IPsec).
  The two Celestica values are MACsec; the MaiaEdge one is not. Claiming the key
  for `macsec` would put an IPsec figure in a MACsec column, the failure the
  layer is built against. So `encryption` is not a source.

**Options.**

- **A. Source `macsec` only.** 11 devices, no library change, two-way. The two
  Celestica boxes compare as silent on MACsec though they state it.
- **B. Source `macsec`, and rename the two Celestica `encryption` keys to
  `macsec`** in a later step. 13 devices. A library edit: the attrs key changes,
  so the devices' exports' comments and the lock move (one-way, see below).
- **C. Source both keys and accept the IPsec reading.** Wrong; not recommended.

One more miss to report, not to fix: `ufispace/s9620-32e` names MACsec inside its
`forwarding` sentence ("... MACsec point-to-point ..."), and `forwarding` is
claimed by `forwarding-rate` (see routing). So the device compares as silent on
MACsec.

**Recommendation: A first, B as a separate later slice.**

### 4. routing: promote one protocol fact, under the standard's name

#112's third point: `routing` is a single-vendor vocabulary and a fact on it
risks encoding a vendor's marketing. The recount supports splitting the family:

- `routing` (10), `segment-routing` (5) and `srv6` (4) are **one claim on 19
  devices, all UfiSpace, no device carrying two of them**. Every value says
  Segment Routing over IPv6: "full Segment Routing over IPv6 (SRv6)", "full SRv6",
  "full Segment Routing over IPv6". `routing` is the key name that is generic;
  its content is not.
- `flexe` (2) and `tsn` (3) are not routing, as #112 says. `tsn` also sits on
  `s9620-40dg`, `s9620-54dc` and `s9600-64x` only; `flexe` is on `s9510-28dc` and
  `s9510-30xc` only. Both are under the reach of every earlier promotion.
- `protocols` (7) is **management protocols** (`SNMP`, `NETCONF`, `SSH`, `NTP`)
  on the UfiSpace M3000 and Eaton and Oscilloquartz gear. It is the sibling of
  `console` and `oob-management`, not routing, and the issue's "1 device" is
  now seven. It stays unclaimed.
- `forwarding` (4) is **already claimed** by `forwarding-rate`, and its values
  are not rates: `FP4` on `nokia/sr-1-ac` and `sr-1-dc` (a chip name), a feature
  sentence on `ufispace/s9620-32e` and `s9720-56ed` (which state SRv6 there, so
  they compare as silent on `srv6`). That is an existing wrong
  reading in the published layer, found by this recount and not decided here
  (question 5).

The fact would be named for the protocol (`srv6`, a standard), not for UfiSpace's
word. It is a statement that a box does the protocol, and a column of blanks for
every other vendor reads, by the three-state rule, as "nobody has looked".
Single-vendor coverage is real, though: a side-by-side of a UfiSpace box and a
Juniper one would show the second as blank until someone records it.

**Options.**

- **A. Promote `srv6` on three spellings, with a value test.** `A("routing")`,
  `A("segment-routing")`, `A("srv6")`, and a test over the library that every
  value of those keys names SRv6 or "Segment Routing over IPv6". 19 devices; no
  library edit; two-way. The test makes the hazard (`routing` later holding
  "BGP, OSPF") fail loudly, not silently.
- **B. Rename the 15 keys to `srv6` in the library, claim one spelling.** One
  spelling by construction, no value test needed. Fifteen devices' attrs change,
  so their exports' comments and the lock move: one-way.
- **C. A fact named `routing`.** Takes UfiSpace's key as the library's name for
  the fact. Not recommended.
- **D. Leave.**

**Recommendation: A**, with B as a later step only if the old spellings are to
go.

### 5. service-port: do not promote under that name; promote the USB port

`service-port` is a poor name for the fact, for a reason the census hides. In the
UfiSpace documents a *service port* is a front-panel data port: the same library
says "service ports 0-19 can individually break out" (`s9700-53dx`),
"400ZR and OpenZR+ run on six of the ten service ports" (`s9700-23d`), and
"four service ports are taken for statistics" (`s9710-76d`). The `service-port`
key here (3 devices) holds a **USB port** ("1x USB 3.0 Type-A maintenance port").
A canonical `service-port` would invite a reader to look for the data ports.

The 27 devices fall into two facts and a leftover (three devices, `s9700-23d`,
`s9700-53dx` and `s9725-64e`, are in both of the first two, so the groups sum
to 30):

- **The USB port.** `usb` (20 devices: Celestica, Cisco, Juniper, UfiSpace) and
  `service-port` (3 UfiSpace, all USB) are one claim on **23 devices**, no device
  carrying both, all filed under `management`. Every value names a USB port. The
  value varies in what it states (version, type, "maintenance port", "data only"),
  which is why it is `TEXT`.
- **In-band management SFP+ ports**: `sfp-plus-management` (2), `sfp-management`,
  `inband`, `inband-mgmt` and, from #112's breakout list, `uplinks` (1 each).
  Six UfiSpace devices. Under the reach of earlier promotions, and next to
  `oob-sfp` (claimed by `oob-management`). Left.
- `console-usb-driver` (1 device) names a USB-to-UART bridge chip. It is a
  console statement, not a port. Left.

**Options.**

- **A. A fact `service-port` on all seven spellings.** Mixes a USB port, an SFP+
  management port and a driver string; takes UfiSpace's ambiguous word. Not
  recommended.
- **B. A fact `usb` on `usb` and `service-port`.** 23 devices, no library edit,
  two-way. Names the thing.
- **C. B, and a second fact `inband-management` on the five SFP+ spellings.**
  Six devices, one vendor.
- **D. Leave.**

**Recommendation: B.**

## What changes when it is built

Nothing in this note is built. For the recommended set:

| change | where | one-way or two-way |
|---|---|---|
| Fact `macsec`, source `macsec` | `comparable.py` `FACTS` | two-way: a Python list entry, removable |
| Fact `srv6`, sources `routing`, `segment-routing`, `srv6` | `comparable.py` `FACTS` | two-way |
| Fact `usb`, sources `usb`, `service-port` | `comparable.py` `FACTS` | two-way |
| `nebs` gains `nebs-emc-safety` and `nebs-physical` as qualified readings | `comparable.py` `FACTS` | two-way |
| `CLAIMED` grows by 8 spellings (`macsec`, `routing`, `segment-routing`, `srv6`, `usb`, `service-port`, `nebs-emc-safety`, `nebs-physical`) | derived | two-way |
| `comparable-facts.json`: three more entries under `vocabulary`, more under `coverage`, eight fewer under `unclaimed`; seven devices gain readings under `nebs` | `library/dist` (not tracked) | **one-way for any consumer** that has started reading a fact name or a count: a name once published is a key somebody may rely on, and removing it breaks them. The file has no version key and `docs/format-stability.md` does not mention it, so nothing documents it as additive (question 6) |
| L68's warning reads 8 fewer spellings | `lint.py`, built from the census | two-way; no edit |
| The census gets a margin check: `test_the_long_tail_is_still_left_alone` asserts singletons exceed a third of the census; today 160 against 454 // 3 = 151, and after eight non-singleton spellings leave it, 160 against 446 // 3 = 148 | `spec/tests/test_comparable_facts.py` | two-way; the margin is thin and a later large promotion would trip it |
| Stale counts in two comments ("102 of 211") | `comparable.py` (promotion comment), `test_comparable_facts.py` (docstring) | two-way |
| **Later, optional:** rename the two Celestica `encryption` keys to `macsec` (macsec option B) | two device manifests | **one-way**: attrs text reaches the device type's `comments` in both DCIM exports, so exports and each device's `device.lock.json` change |
| **Later, optional:** rename fifteen `routing` and `segment-routing` keys to `srv6` (routing option B) | fifteen device manifests | **one-way**, same reason |
| **Later, from `docs/breakout-design.md`, not this note:** rename the three S9600 `breakout` keys to `sfp28-sharing` | three manifests | **one-way** |

No schema changes. No new lint rule is needed: L40 and L68 behave correctly
as they are; the rule that keeps a spelling in one fact is a test that exists
(`test_no_fact_shares_a_source_key_with_another`). No `library/` file moves in the
first slice, so no lock moves and no export changes.

## First build slice

Small and entirely two-way: the code and test change only, no library file.

- `spec/tools/portrayal/comparable.py`: add `macsec` (section `features`),
  `srv6` (`features`) and `usb` (`management`) as `TEXT` facts, add the two
  qualified `nebs` sources after the existing `A("nebs")`, and correct the stale
  comment count. Put each beside its neighbours in the file's sections.
- `spec/tests/test_comparable_facts.py`: reach floors in
  `test_the_promoted_facts_reach_the_devices_that_carry_them` for the three new
  facts at their `main` counts (`macsec` 11, `srv6` 19, `usb` 23); a test
  that `nebs` on an ASR 9000 returns the headline and two qualified readings; a
  test that every `routing`, `segment-routing` and `srv6` value in `library/`
  names SRv6, and that every `usb` and `service-port` value names USB (these
  walk `library/devices`, not `dist`, so they never skip); a test that
  `encryption` and `tpm` are not sources of `macsec`; the stale docstring.
- A changelog fragment if `spec/tests/test_changelog_fragments.py` asks for one.
- Gates: the comparable and changelog tests, preflight, and the full suite in CI.

It needs no `./publish.sh`, no export regeneration and no `devicelock --update`.
It rebases over the open PRs that edit `lint.py` and `lint-rules.md` (none
touches `comparable.py` or its test).

## Open questions

Each is answerable in one line.

1. **What is the least reach a fact needs?** The facts #99 promoted resolve on 20
   to 96 devices on `main` (the floors in
   `test_the_promoted_facts_reach_the_devices_that_carry_them` run 18 to 40, from
   `gnss` up). The proposal's `macsec` is 11 (13 later). Is 11 enough, or is the
   floor 18 and `macsec` waits?
2. **Per-media `port-modes` facts (breakout option C): build them, or let the
   merged `speeds` field carry native rates and supersede the prose?** Changes
   whether the native-rate question gets a prose column.
3. **Does a comparison fact for breakout read only the listing's structured rule
   (`docs/breakout-design.md`, its question 6)?** Changes whether any prose
   breakout fact is ever built, and whether `comparable.resolve` reads a listing.
4. **Do the three `compliance-programme` values "IEEE 802.1CM fronthaul; ITU-T
   G.8273.2 T-BC Class C" belong under `timing`?** Moving them is a library edit
   on three UfiSpace devices.
5. **Is `forwarding` meant for `forwarding-rate` at all?** Four of its readings
   (`nokia/sr-1-ac`, `sr-1-dc`, `ufispace/s9620-32e`, `s9720-56ed`) are a chip
   name or a feature sentence, not a rate. Changes: those four rows in
   published readings.
6. **Is `comparable-facts.json` a published, additive surface?** Nothing in
   `docs/format-stability.md` says. Changes whether a new fact name is a promise.
7. **May the two Celestica `encryption` keys be renamed to `macsec`** (a later
   slice, one-way: two exports and the lock)?
8. **Name the fact `srv6` or `segment-routing`?** The values say Segment Routing
   over IPv6 throughout; a plain MPLS Segment Routing would be another fact. Changes
   only the published name.
9. **Is a single-vendor fact acceptable** when the other vendors have not been
   looked at? Changes whether `srv6` waits for a second vendor's reading.

## Recommendations

These are recommendations, not decisions.

1. **Floor.** Accept 11 for `macsec` because it spans three vendors; leave `tpm`,
   `protocols`, `flexe`, `tsn` and the SFP+ management ports under the floor.
2. **Per-media `port-modes` facts.** Not now. Let `speeds` carry native rates, and
   fix the `qsfpdd` and `osfp224` spellings as a library edit with its own note.
3. **Breakout fact.** Wait for `docs/breakout-design.md`'s question 6. Claim no
   `port-modes-*` key meanwhile.
4. **802.1CM / G.8273.2.** Move to `timing` in its own change, if the answer to question 4 is yes.
5. **`forwarding`.** Raise as a defect in its own issue; do not fix it here.
6. **Published surface.** Treat the vocabulary names as additive and stable: add,
   never rename. Then record that in `docs/format-stability.md`.
7. **Renames.** Do the Celestica `encryption` to `macsec` rename only once it
   is worth a lock bump; the proposed slice does not need it.
8. **Name.** `srv6`.
9. **Single-vendor.** Accept: the layer's third state already means "nobody has
   looked".

## Sources

- #112 ("the next pass of the census"), #99 (the first promotion), #536 (a
  structured breakout field), and `docs/breakout-design.md` (PR #1169, merged).
  Read in full: bodies and comments; #112 and #99 have none.
- `spec/tools/portrayal/comparable.py`, `comparable_index.py`; `lint.py`
  `lint_device_port_optics` (L40), `lint_library_comparable_facts` (L68),
  `PLUGGABLE_CAGES`; `docs/lint-rules.md`; `docs/format-stability.md`;
  `docs/modelling-a-device.md`.
- `spec/tests/test_comparable_facts.py` (the tests that hold the census and rule
  1), and the device manifests named above under `library/devices/`.
- Layout follows `docs/pcie-two-slot-bays-design.md` and `docs/breakout-design.md`.
