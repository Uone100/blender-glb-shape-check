import struct
import unittest
from scripts.glb_weights import find_curve, Unsupported


def track(mode, values, names=("Jaw","Blink")):
    binary=struct.pack("<2f",0,1)+struct.pack(f"<{len(values)}f",*values)
    counts=(2,len(values))
    doc={"nodes":[{"name":"Face","mesh":0}],
         "meshes":[{"primitives":[{"targets":[{} for _ in names]}],"extras":{"targetNames":list(names)}}],
         "animations":[{"name":"Talk","channels":[{"target":{"node":0,"path":"weights"},"sampler":0}],
                        "samplers":[{"input":0,"output":1,"interpolation":mode}]}],
         "buffers":[{"byteLength":len(binary)}],
         "bufferViews":[{"buffer":0,"byteLength":8},{"buffer":0,"byteOffset":8,"byteLength":len(binary)-8}],
         "accessors":[{"bufferView":i,"componentType":5126,"type":"SCALAR","count":n} for i,n in enumerate(counts)]}
    return doc,binary

class Curves(unittest.TestCase):
    def test_selected_target(self):
        for mode,want in (("STEP",0),("LINEAR",0.5)):
            doc,data=track(mode,[1,0,0,1])
            _,sample=find_curve(doc,data,"Face","Blink","Talk")
            self.assertEqual([sample(0.5),sample(1),sample(2)],[want,1,1])

    def test_cubic_tangent_and_clamping(self):
        doc,data=track("CUBICSPLINE",[0,0,1,0,0,0,0,0,0,1,0,0])
        _,sample=find_curve(doc,data,"Face","Blink","Talk")
        self.assertAlmostEqual(sample(.25),.15625)
        self.assertEqual(sample(0),0)
        self.assertEqual(sample(2),1)

    def test_unmatched_mapping(self):
        doc,data=track("LINEAR",[1,0,0,1])
        self.assertEqual(find_curve(doc,data,"Face","Blink","Idle")[0],"missing-clip")
        del doc["meshes"][0]["extras"]
        with self.assertRaises(Unsupported):
            find_curve(doc,data,"Face","Blink","Talk")
