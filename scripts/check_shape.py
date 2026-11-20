"""Run inside Blender's background process; evaluate source frames and read a GLB."""
import argparse
import json
import math
import struct
from pathlib import Path
import sys

import bpy
sys.path.insert(0, str(Path(__file__).resolve().parent))
from glb_weights import find_curve, load_glb, Unsupported


def compare(args):
    doc, binary = load_glb(args.glb)
    if args.inventory:
        return {"status":"inventory", "source_meshes":{
            o.name: list(o.data.shape_keys.key_blocks.keys())
            for o in bpy.context.scene.objects if o.type=="MESH" and o.data.shape_keys},
            "exported_mesh_nodes":[n.get("name") for n in doc.get("nodes",[]) if "mesh" in n],
            "exported_clips":[a.get("name") for a in doc.get("animations",[])]}
    if not (args.object and args.key and args.clip and args.frames):
        raise ValueError("Supply --object, --key, --clip and --frames FIRST LAST or use --inventory")
    first,last=args.frames
    if last<=first or not math.isfinite(args.tolerance) or args.tolerance<=0 or not math.isfinite(args.clip_offset) or args.clip_offset<0:
        raise ValueError("Choose an increasing frame range, positive tolerance and nonnegative clip offset")
    obj = bpy.context.scene.objects.get(args.object)
    if obj is None or obj.type!="MESH" or not obj.data.shape_keys or args.key not in obj.data.shape_keys.key_blocks:
        raise Unsupported("Source mesh or shape key not found; check --inventory")
    if not obj.data.shape_keys.use_relative or obj.data.shape_keys.key_blocks[args.key].mute:
        raise Unsupported("Select an enabled relative shape key")
    scene=bpy.context.scene
    samples=[]
    for frame in range(first,last+1):
        scene.frame_set(frame)
        evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        samples.append(float(evaluated.data.shape_keys.key_blocks[args.key].value))
    if getattr(bpy.app, "autoexec_fail", False):
        raise Unsupported("A driver or script was blocked while evaluating the source")
    if not all(map(math.isfinite,samples)):
        raise Unsupported("Source evaluation produced a non-finite weight")
    report={"object":args.object,"shape_key":args.key,"clip":args.clip,"frames":[first,last],
            "source_range":[min(samples),max(samples)]}
    if max(samples)-min(samples)<=args.tolerance:
        return dict(report,status="source-static",detail="Check the source action, NLA state, drivers and frame range")
    state,curve=find_curve(doc,binary,args.node or args.object,args.export_key or args.key,args.clip)
    if curve is None:
        return dict(report,status=state)
    fps=scene.render.fps/scene.render.fps_base
    actual=[curve(args.clip_offset+i/fps) for i in range(len(samples))]
    errors=[abs(a-b) for a,b in zip(samples,actual)]
    worst=errors.index(max(errors))
    state="match" if max(errors)<=args.tolerance else "weights-differ"
    if state!="match" and max(actual)-min(actual)<=args.tolerance:
        state="export-static"
    return dict(report,status=state,export_range=[min(actual),max(actual)],max_error=max(errors),
                worst_frame=first+worst,source_weight=samples[worst],export_weight=actual[worst])


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("glb", type=Path)
    p.add_argument("--inventory",action="store_true")
    p.add_argument("--object")
    p.add_argument("--key")
    p.add_argument("--node")
    p.add_argument("--export-key")
    p.add_argument("--clip")
    p.add_argument("--frames",type=int,nargs=2,metavar=("FIRST","LAST"))
    p.add_argument("--clip-offset",type=float,default=0.0)
    p.add_argument("--tolerance",type=float,default=0.001)
    args=p.parse_args(sys.argv[sys.argv.index("--")+1:])
    try:
        report=compare(args)
    except Unsupported as exc:
        report={"status":"inconclusive","detail":str(exc)}
    except (OSError, ValueError, KeyError, IndexError, TypeError, RuntimeError, struct.error) as exc:
        report={"status":"invalid-input","detail":str(exc)}
    print("SHAPE_CHECK "+json.dumps(report,allow_nan=False),flush=True)
    sys.exit(0 if report["status"] in {"match","inventory"} else 2 if report["status"]=="invalid-input" else 1)
