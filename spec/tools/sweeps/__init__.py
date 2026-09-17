"""Corrective migrations, each one paired with the lint rule that finds its work.

A sweep is the REMEDY for a rule, not a second opinion about it: `sweep_ids`
takes its replacement name from L62, `sweep_alignment` applies the arithmetic
L61 already printed, `sweep_rj45` asks `lint.rj45_wants_lamps` which part a jack
should take. Each docstring says so, because two spellings of one intent is
exactly the divergence those rules exist to stop.

KEPT RATHER THAN DELETED AFTER THEIR MERGE. #179 offered both, and the baseline
answers it: L61 stands at 645 warnings and L62 at 23, so two of these are live
remedies for a backlog still being worked. L76 reads 0 - `sweep_rj45` has
finished the devices in the library - and it stays because the next device
modelled in the old shape needs the same 589 lines, which are an argument about
textual rewriting as much as a script.
"""
