"""Read one named morph target and its animation in a self-contained GLB 2.0."""
import bisect
import json
import math
import struct


class Unsupported(ValueError):
    """The available data cannot establish a named comparison."""


def entry(items, index):
    if type(index) is not int or not 0 <= index < len(items):
        raise ValueError("Out-of-range glTF reference")
    return items[index]


def load_glb(path):
    with path.open("rb") as stream:
        header = stream.read(12)
        if len(header) != 12 or struct.unpack("<4sII", header) != (b"glTF", 2, path.stat().st_size):
            raise ValueError("Expected a complete binary glTF 2.0 file")
        chunks = {}
        while chunk := stream.read(8):
            length, kind = struct.unpack("<I4s", chunk)
            data = stream.read(length)
            if len(data) != length or kind in chunks:
                raise ValueError("Incomplete or duplicate GLB chunk")
            chunks[kind] = data
    return json.loads(chunks[b"JSON"]), chunks.get(b"BIN\0", b"")


def scalar_values(doc, binary, index):
    a = entry(doc["accessors"],index)
    if a.get("type") != "SCALAR" or a.get("componentType") != 5126 or "sparse" in a:
        raise Unsupported("Expected dense FLOAT SCALAR animation samples")
    view = entry(doc["bufferViews"],a["bufferView"])
    if view["buffer"] != 0 or "uri" in doc["buffers"][0]:
        raise Unsupported("Animation uses a separate buffer")
    start = view.get("byteOffset", 0)
    offset = a.get("byteOffset", 0)
    stride = view.get("byteStride", 4)
    count = a["count"]
    limit=min(len(binary),doc["buffers"][0]["byteLength"])
    if min(start, offset) < 0 or count < 1 or stride < 4 or start + view["byteLength"] > limit:
        raise ValueError("Invalid animation buffer view")
    if offset + (count - 1) * stride + 4 > view["byteLength"]:
        raise ValueError("Animation samples exceed their buffer view")
    data = [struct.unpack_from("<f", binary, start + offset + i * stride)[0] for i in range(count)]
    if not all(map(math.isfinite, data)):
        raise ValueError("Non-finite animation data")
    return data


def find_curve(doc, binary, node_name, key, clip):
    nodes = [(i, n) for i, n in enumerate(doc.get("nodes", [])) if n.get("name") == node_name and "mesh" in n]
    if len(nodes) != 1:
        raise Unsupported(f"Expected one mesh node named {node_name!r}; found {len(nodes)}")
    ni, node = nodes[0]
    mesh = entry(doc["meshes"],node["mesh"])
    counts = {len(p.get("targets", [])) for p in mesh["primitives"]}
    if counts == {0}:
        return "missing-target", None
    names = mesh.get("extras", {}).get("targetNames")
    if not names or counts != {len(names)} or len(names) != len(set(names)):
        raise Unsupported("Exported target names are absent, ambiguous or inconsistent")
    if key not in names:
        return "missing-target", None
    clips = [a for a in doc.get("animations", []) if a.get("name") == clip]
    if not clips:
        return "missing-clip", None
    if len(clips) != 1:
        raise Unsupported("Multiple animation clips have the requested name")
    channels = [c for c in clips[0]["channels"] if c["target"].get("node") == ni and c["target"].get("path") == "weights"]
    if not channels:
        return "missing-weights-channel", None
    if len(channels) != 1:
        raise Unsupported("Multiple weight channels target the selected node in one clip")
    sampler = entry(clips[0]["samplers"],channels[0]["sampler"])
    mode = sampler.get("interpolation", "LINEAR")
    if mode not in {"STEP", "LINEAR", "CUBICSPLINE"}:
        raise Unsupported("Unknown interpolation " + mode)
    times = scalar_values(doc, binary, sampler["input"])
    if times[0] < 0 or any(b <= a for a, b in zip(times, times[1:])):
        raise ValueError("Animation times must be nonnegative and strictly increasing")
    values = scalar_values(doc, binary, sampler["output"])
    width = len(names)
    lanes = 3 if mode == "CUBICSPLINE" else 1
    if len(values) != len(times) * lanes * width:
        raise ValueError("Weight sample count does not match target count")
    selected = values[names.index(key)::width]

    def sample(t):
        # glTF holds the endpoint values outside a sampler's key range.
        i = max(0, bisect.bisect_right(times, t) - 1)
        if mode == "CUBICSPLINE":
            v = selected[3*i+1]
        else:
            v = selected[i]
        if t <= times[0] or i == len(times)-1 or mode == "STEP":
            return v
        dt = times[i+1] - times[i]
        u = (t-times[i])/dt
        if mode == "LINEAR":
            return v + u * (selected[i+1]-v)
        w = selected[3*(i+1)+1]
        return ((2*u**3-3*u*u+1)*v + (u**3-2*u*u+u)*dt*selected[3*i+2]
                + (-2*u**3+3*u*u)*w + (u**3-u*u)*dt*selected[3*(i+1)])
    return "available", sample
