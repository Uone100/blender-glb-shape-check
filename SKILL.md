---
name: blender-glb-shape-check
description: Compare a selected shape key in a Blender scene against a self-contained GLB animation clip when an expression, blink or other morph motion appears to be missing after export.
---

Identify the saved source scene and its evaluated frame range, the intended mesh and relative shape key, and the exported clip. Use the background Blender command in [TUTORIAL.md](TUTORIAL.md). Inventory both files if naming is unclear. Match a renamed node or target only when the mapping is known. Align the source's first frame to the correct time in the exported clip.

Distinguish missing targets, missing weight channels, a static exported weight and a timing or amplitude difference. A static source over the requested range is inconclusive evidence of export loss. Report source/export ranges and the frame with the largest difference when available. A match covers the sampled weight curve. If the symptom persists, the destination player or vertex deformation needs separate inspection.
