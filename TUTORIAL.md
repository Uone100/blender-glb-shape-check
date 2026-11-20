# Find out where an exported blink disappeared

Download the named ZIP from [Releases](https://github.com/Uone100/blender-glb-shape-check/releases/latest), extract it and open a terminal beside `SKILL.md`. You need Blender with its bundled glTF exporter. Run `blender --version`. If it is outside PATH, replace `blender` with the path to its executable (in PowerShell, use `& "C:/path/to/blender.exe"`).

## Compare three real exports

Create a fresh demo folder. The generator builds an eyelid, animates its Blink key from 0 to 1 and back, saves the source scene, and exports three GLBs using Blender.

```sh
blender -b --factory-startup --disable-autoexec --python-exit-code 2 -P examples/make_demo.py -- demo
blender -b --factory-startup --disable-autoexec demo/eyelid.blend --python-exit-code 2 -P scripts/check_shape.py -- demo/good.glb --inventory
blender -b --factory-startup --disable-autoexec demo/eyelid.blend --python-exit-code 2 -P scripts/check_shape.py -- demo/good.glb --object Eyelid --key Blink --clip Eyelid --frames 0 24
```

Look for the JSON line beginning with `SHAPE_CHECK`. Repeat the final command, changing only the GLB path.

| File | What to look for |
| --- | --- |
| good.glb | `match`. The exported blink reaches 1 near the middle of the one-second clip and returns to 0. |
| missing-target.glb | `missing-target`. Morph export was disabled. |
| static.glb | `export-static` or `missing-weights-channel`. The target remains but its animation was removed. The object still has a translation animation. |

To see the sample in Blender, open `eyelid.blend`, look at the mesh from the front and scrub from frame 0 to 24. The command measures the selected weight at every integer frame.

## Compare your own character

1. Save the source with the intended action or NLA performance active. Use the source scene and export from the same edit. Run the inventory command with your two paths.
2. Choose the source mesh object, relative shape key and exported clip using their exact names. If names changed, pass `--node NEW_OBJECT_NAME` or `--export-key NEW_TARGET_NAME`. Missing or ambiguous name metadata requires inspection.
3. Set `--frames FIRST LAST` to a span that includes movement. The first source frame maps to GLB time zero by default. If your first sample corresponds to 1/24 second in the GLB, pass `--clip-offset 0.041666667`. Use the scene's actual frame rate and export time origin.
4. Compare the ranges and worst frame. For example, `source_weight: 1.0` and `export_weight: 0.0` at peak blink explain a static export. A consistent timing shift merits checking the clip offset. `--tolerance 0.001` is the default absolute weight tolerance.

If the source is static, check the frame span, NLA state and drivers. The command disables embedded auto-execution. A file that needs a blocked scripted driver can produce an inconclusive result. A matching weight curve focuses the next investigation on mesh deformation or playback in the destination app. Subframe motion, absolute shape keys, unnamed morph mappings, sparse or externally stored animation samples are outside this comparison.

Exit code 0 means inventory or match, 1 means a difference or inconclusive result, and 2 indicates invalid input. For agent installation and an example prompt, see the [README](README.md).
