"""Measurement benchmarks: how well a machine reads a faceplate.

Seven experiments scoring OCR, object detection and vision-language models
against hand-made ground truth, so that a claim like "the tool can find the
ports" has a number behind it rather than an impression. `benchvlm` is
Apple-silicon only (`mlx-vlm`), which is why it is not in the `[bench]` extra
and why every tool that reaches for it imports it lazily.

`pip install -e ".[bench]"`. None of it is needed to lint, render or publish.
"""
