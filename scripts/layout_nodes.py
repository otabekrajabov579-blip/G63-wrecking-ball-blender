"""G63_Crush_Deform tugunlarini chapdan o'ngga ustunlarga joylashtiradi (o'qish oson bo'lishi uchun).
    E:\\blendr\\blender.exe -b wrecking_ball_scene.blend --python scripts\\layout_nodes.py
"""
import bpy

ng = bpy.data.node_groups["G63_Crush_Deform"]
inc = {n: [l.from_node for l in ng.links if l.to_node == n] for n in ng.nodes}
depth = {}


def d(n, stack=()):
    if n in depth:
        return depth[n]
    if n in stack:
        return 0
    depth[n] = 0 if not inc[n] else 1 + max(d(m, stack + (n,)) for m in inc[n])
    return depth[n]


for n in ng.nodes:
    d(n)
cols = {}
for n in sorted(ng.nodes, key=lambda n: (depth[n], n.name)):
    cols.setdefault(depth[n], []).append(n)
for c, nodes in cols.items():
    for i, n in enumerate(nodes):
        n.location = (c * 260.0, -i * 230.0 + len(nodes) * 115.0)
for n in ng.nodes:
    if n.type == 'VALUE':
        n.label = "Impact Bend (keyframed)"
bpy.ops.wm.save_mainfile()
print("LAYOUT OK", len(ng.nodes), "nodes in", len(cols), "columns")
