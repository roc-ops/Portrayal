# Security

Portrayal is a library of hardware descriptions and the tools that compile them.
It runs no service and takes no untrusted input in production; the attack surface
is the tooling a contributor runs on their own machine and the data this
repository publishes.

## What counts as a security issue here

- A manifest, contract, dump or export that carries information it should not:
  a serial number, a MAC address, an IP address, a hostname, an SNMP community,
  or vendor material that is not ours to redistribute.
- A tool (`lint.py`, `render.py`, `dcim_export.py`, the intake scripts) that can
  be made to read or write outside the repository, or to execute content from a
  manifest or an SVG skin.
- A generated artifact (SVG, JSON, DCIM export) that would execute script or
  load a remote resource when a consumer embeds it.

## Reporting

While this repository is private, open an issue: only its collaborators can
read it, so the report is private by construction, and the maintainer is
notified. Once the repository is public, use GitHub's private vulnerability
reporting ("Report a vulnerability" under the Security tab) so the report is
not public until a fix is; if that form is unavailable to you, open an issue
that says only that you have a security report and how to reach you, and keep
the details out of it.

You will get an acknowledgement within a week. Leaked data is removed from the
tree and, where it matters, from history; tooling fixes ship as an ordinary
pull request once the report is understood.
