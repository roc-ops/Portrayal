# Instructions for GitHub Copilot

This repository's instructions for any assistant are in
[`AGENTS.md`](../AGENTS.md). Read it first.

The skills under `.claude/skills/` are plain Markdown. A person or an assistant
can follow them by hand.

Three rules that sank a first contribution:

1. **The sign-off needs the human's yes.** Only the human contributor can agree
   to the Developer Certificate of Origin. Ask them to read it and to say they
   agree. Add the `Signed-off-by:` line only after they have. See step 7 of the
   Submit table in
   [the model-device skill](../.claude/skills/portrayal-model-device/SKILL.md).
2. **`draft` is a welcome claim.** A device that is not yet `modelled` may say
   `maturity: draft`. A draft is a fine thing to submit, and welcome. Declare
   the faces with no source in `gaps:`. See the maturity table in
   [the model-device skill](../.claude/skills/portrayal-model-device/SKILL.md)
   and the `maturity` entry in [`CONTRIBUTING.md`](../CONTRIBUTING.md).
3. **`empty:` is only for a face with nothing on it.** It claims that you
   searched and the face carries nothing. A face that carries something you have
   not drawn is a gap, and the device stays `draft`. See
   [Every face](../docs/modelling-a-device.md#every-face) in the modelling guide
   and [deliberately-empty-faces.md](../docs/deliberately-empty-faces.md).

The gate commands are in 'The gates' in [`AGENTS.md`](../AGENTS.md).
