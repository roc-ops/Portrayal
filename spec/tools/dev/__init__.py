"""Probes, converters and one-offs - everything the gates never run.

The compiler directory held these alongside the twenty modules `build.sh`,
`publish.sh` and CI actually reach: modelling probes written to answer one
question, a Visio stencil reader, a USD converter needing `usd-core`, an audit
of one device's rear face. A reader could not tell which twenty mattered, and
neither could a grep (#179).

Nothing here is imported by the compiler; the dependency runs one way, and a
test asserts it. `python -m portrayal_dev.<tool> --help` says what each is for.
"""
