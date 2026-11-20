"""Create an original animated eyelid and three real Blender glTF exports in a new directory."""
from pathlib import Path
import sys
import bpy

folder=Path(sys.argv[sys.argv.index("--")+1]).resolve()
folder.mkdir(parents=True, exist_ok=False)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.name="EyeDemo"
scene.frame_start=0
scene.frame_end=24
scene.render.fps=24
mesh=bpy.data.meshes.new("EyelidMesh")
mesh.from_pydata([(-1,0,0),(0,0,-0.5),(1,0,0),(0,0,0.5)],[],[(0,1,2,3)])
mesh.update()
eye=bpy.data.objects.new("Eyelid",mesh)
scene.collection.objects.link(eye)
eye.shape_key_add(name="Basis")
blink=eye.shape_key_add(name="Blink")
for p in blink.data:
    p.co.z*=0.05
for frame,weight in ((0,0.0),(12,1.0),(24,0.0)):
    blink.value=weight
    blink.keyframe_insert(data_path="value",frame=frame)
    eye.location.x=0.1*weight
    eye.keyframe_insert(data_path="location",frame=frame)
scene.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(folder/"eyelid.blend"))

def export(name, **options):
    bpy.ops.export_scene.gltf(filepath=str(folder/(name+".glb")),export_animation_mode="SCENE",
                              export_format="GLB",**options)

export("good")
export("missing-target", export_morph=False)
mesh.shape_keys.animation_data_clear()
blink.value=0
scene.frame_set(0)
export("static")
