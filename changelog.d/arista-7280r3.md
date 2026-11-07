### Added
- Arista, seven more 7280R3 models (#1204, slice 1), one device a front panel: the 7280PR3-24
  (`arista/7280pr3-24`, 24 x 400G OSFP), the 7280DR3-24 (`arista/7280dr3-24`, 24 x 400G QSFP-DD), the
  7280CR3-32P4 (`arista/7280cr3-32p4`, 32 x 100G QSFP and 4 x 400G OSFP), the 7280CR3-36S
  (`arista/7280cr3-36s`, 36 QSFP ports with the management ports on the front), the 7280SR3-48YC8
  (`arista/7280sr3-48yc8`, 48 x 25G SFP and 8 x 100G QSFP), the 7280SR3-40YC6 (`arista/7280sr3-40yc6`,
  40 x 25G SFP and 6 x 100G QSFP) and the 2RU 7280CR3-96 (`arista/7280cr3-96`, 96 x 100G QSFP). The 7280TR3-40C6
  is left out, because the guide has no front figure for it.
- The K, K-A and E-M builds of those models, each in its front-to-rear and rear-to-front airflow where the data
  sheet lists both, are orderable configurations with their own part numbers (for example DCS-7280PR3K-24-F,
  DCS-7280CR3K-36A-R, DCS-7280SR3K-48YC8A-F and DCS-7280SR3E-40YC6-M-R), and each model's DC build is a worked example.
- The field-replaceable modules of those models, family-prefixed: the PWR-511 supplies (AC and DC, red and blue),
  the PWR-1511 supplies (AC and DC) and the FAN-7011M fan modules (forward and reverse) as `arista/7280r3-*`. The
  PWR-1011 supplies, the FAN-7011H fan modules, the PWR-2411 supplies and the FAN-7012H fan module already in the
  library are reused by part number.
- The DCIM device types for each orderable configuration, in the NetBox and Nautobot exports, and the module types
  for the new supplies and fan modules.
