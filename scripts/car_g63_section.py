# ------------------------------------------------------------------ Mercedes-Benz G63 AMG (Sketchfab, CC-BY-4.0, Black Snow)
import numpy as np
ROOF_Z = 1.95
IMPACT = Vector((PIVOT.x, PIVOT.y, ROOF_Z))
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=os.path.join(A, "models", "g63", "scene.gltf"))
imported = [o for o in bpy.data.objects if o not in before]
meshes = [o for o in imported if o.type == 'MESH']
for o in meshes:
    mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw
for o in imported:
    if o.type != 'MESH':
        bpy.data.objects.remove(o, do_unlink=True)
for o in meshes:
    link(o, C_CAR)
    if o.data.users > 1:
        o.data = o.data.copy()
    mw = o.matrix_world.copy()
    o.data.transform(mw)
    if mw.determinant() < 0:
        o.data.flip_normals()
    o.matrix_world = Matrix.Identity(4)


def wbbox(o):
    n = len(o.data.vertices)
    if n == 0:
        return None
    a = np.empty(n * 3, dtype=np.float32); o.data.vertices.foreach_get("co", a); a = a.reshape(-1, 3)
    return Vector(a.min(0)), Vector(a.max(0))


glass_src, wheels_static, crush, static = [], [], [], []
# uziladigan qismlar: (nom, shart(c, size, materiallar, obyekt nomi), uzilish kadri +, turtki m/s, massa kg)
PART_RULES = [
    ("Mirror_L", lambda c, s, m, n: c.x > 0.9 and -0.9 < c.y < -0.4 and 1.1 < c.z < 1.55 and s < 1.0, 1, (2.6, -0.6, 1.4), 3),
    ("Mirror_R", lambda c, s, m, n: c.x < -0.9 and -0.9 < c.y < -0.4 and 1.1 < c.z < 1.55 and s < 1.0, 1, (-2.6, -0.6, 1.4), 3),
    ("Wipers", lambda c, s, m, n: any("wiper" in x.lower() for x in m) and c.y < -0.3, 1, (0.0, -0.8, 2.6), 1),
    ("Headlight_L", lambda c, s, m, n: 0.45 < c.x < 0.85 and c.y < -1.98 and 0.75 < c.z < 1.08 and s < 1.0, 2, (0.9, -2.2, 1.6), 4),
    ("Headlight_R", lambda c, s, m, n: -0.85 < c.x < -0.45 and c.y < -1.98 and 0.75 < c.z < 1.08 and s < 1.0, 2, (-0.9, -2.2, 1.6), 4),
    ("FenderLight_L", lambda c, s, m, n: 0.6 < c.x < 0.92 and -2.05 < c.y < -1.6 and 1.0 < c.z < 1.22 and s < 0.8, 2, (0.7, -0.9, 2.4), 1),
    ("FenderLight_R", lambda c, s, m, n: -0.92 < c.x < -0.6 and -2.05 < c.y < -1.6 and 1.0 < c.z < 1.22 and s < 0.8, 2, (-0.7, -0.9, 2.4), 1),
    ("Grille", lambda c, s, m, n: abs(c.x) < 0.5 and c.y < -2.05 and 0.62 < c.z < 1.1 and s < 1.3, 3, (0.0, -1.7, 1.0), 6),
    ("Taillight_L", lambda c, s, m, n: 0.5 < c.x < 0.9 and c.y > 1.95 and 0.68 < c.z < 0.9 and s < 1.0, 3, (0.7, 2.1, 1.3), 3),
    ("Taillight_R", lambda c, s, m, n: -0.9 < c.x < -0.5 and c.y > 1.95 and 0.68 < c.z < 0.9 and s < 1.0, 3, (-0.7, 2.1, 1.3), 3),
    ("SpareWheel", lambda c, s, m, n: abs(c.x) < 0.5 and c.y > 2.05 and 0.55 < c.z < 1.6 and s < 1.4, 4, (0.0, 1.8, 0.8), 30),
]
part_objs = {r[0]: [] for r in PART_RULES}
for o in meshes:
    bb = wbbox(o)
    if bb is None:
        bpy.data.objects.remove(o, do_unlink=True); continue
    lo, hi = bb; c = (lo + hi) / 2
    mnames = [m.name for m in o.data.materials if m]
    if any(n.startswith("IntWindows") for n in mnames):
        bpy.data.objects.remove(o, do_unlink=True); continue
    hit_rule = next((r for r in PART_RULES if r[1](c, (hi - lo).length, mnames, o.name)), None)
    if hit_rule:
        part_objs[hit_rule[0]].append(o); continue
    if any(n.startswith("G-class_glass") for n in mnames) and hi.z > 1.2 and "mirror" not in o.name.lower():
        glass_src.append(o); continue
    if abs(c.x) > 0.45 and (abs(c.y - 1.31) < 0.45 or abs(c.y + 1.47) < 0.45) and hi.z < 0.86 and (hi - lo).length < 1.2:
        wheels_static.append(o); continue
    # zarba zonasiga tegadigan qismlar -> bukiladigan korpus
    closest = Vector((min(max(IMPACT.x, lo.x), hi.x), min(max(IMPACT.y, lo.y), hi.y), min(max(1.7, lo.z), hi.z)))
    (crush if (closest - Vector((IMPACT.x, IMPACT.y, 1.7))).length < 2.1 else static).append(o)
print(f"G63: glass={len(glass_src)} wheels={len(wheels_static)} crush={len(crush)} static={len(static)}")
print("PARTS:", {k: len(v) for k, v in part_objs.items()})


def densify(o, max_len=0.06, iters=4):
    """Zarba zonasidagi uzun qirralarni bo'lish - bukilish silliq chiqishi uchun."""
    bm = bmesh.new(); bm.from_mesh(o.data)
    for _ in range(iters):
        long_e = [e for e in bm.edges if e.calc_length() > max_len and
                  ((e.verts[0].co + e.verts[1].co) / 2 - IMPACT).xy.length < 1.9 and
                  (e.verts[0].co.z + e.verts[1].co.z) / 2 > 1.0]
        if not long_e:
            break
        bmesh.ops.subdivide_edges(bm, edges=long_e, cuts=1, use_grid_fill=True)
    bm.to_mesh(o.data); bm.free()


for o in crush:
    densify(o)


def join(objs, name):
    tgt = objs[0]
    with bpy.context.temp_override(active_object=tgt, object=tgt, selected_objects=objs, selected_editable_objects=objs):
        bpy.ops.object.join()
    tgt.name = name; tgt.data.name = name
    return tgt


detach_parts = []
for name, test, off, kick, mass in PART_RULES:
    objs = part_objs[name]
    if not objs:
        continue
    po = join(objs, "G63_Part_" + name)
    vs = [v.co for v in po.data.vertices]
    cc = Vector([(min(v[i] for v in vs) + max(v[i] for v in vs)) / 2 for i in range(3)])
    po.data.transform(Matrix.Translation(-cc)); po.location = cc
    detach_parts.append((po, off, kick, mass))
crush_body = join(crush, "G63_Body_Crush")
static_body = join(static, "G63_Body_Static")
wheels_obj = join(wheels_static, "G63_Wheels")
for o in (crush_body, static_body):
    with bpy.context.temp_override(object=o, active_object=o, selected_objects=[o], selected_editable_objects=[o]):
        try:
            bpy.ops.mesh.customdata_custom_splitnormals_clear()
        except RuntimeError:
            pass
    try:
        o.data.set_sharp_from_angle(angle=math.radians(35))
    except Exception:
        pass
    o.data.polygons.foreach_set("use_smooth", [True] * len(o.data.polygons))
print("crush verts:", len(crush_body.data.vertices), "static verts:", len(static_body.data.vertices))

# --- oynalarni qalinlashtirish va mayda bo'laklarga parchalash
for g in glass_src:
    mod = g.modifiers.new("Thick", 'SOLIDIFY'); mod.thickness = 0.006; mod.offset = 0.0
    with bpy.context.temp_override(object=g, active_object=g, selected_objects=[g], selected_editable_objects=[g]):
        bpy.ops.object.modifier_apply(modifier=mod.name)
glass_frags = []
for g in glass_src:
    area = sum(p.area for p in g.data.polygons) / 2
    d = ((sum((v.co for v in g.data.vertices), Vector()) / len(g.data.vertices)) - IMPACT).length
    n = int(min(110, max(12, area * 140 * (1.6 if d < 1.2 else 1.0))))
    inner = M_GLASS_IN          # sinish yuzalari - tiniq, yaltiroq shisha
    glass_frags += fracture(g, n, C_FRAC, inner, bias=IMPACT)
C_ORIG = bpy.data.collections.new("Fracture_Source_Hidden"); C_FRAC.children.link(C_ORIG)
for o in glass_src:
    link(o, C_ORIG)
C_ORIG.hide_render = True; C_ORIG.hide_viewport = True
print(f"Glass shards: {len(glass_frags)} from {len(glass_src)} windows")

# --- yashirin "ezilish chegarasi" kolliderlari (shar korpusni shu chuqurlikkacha ezadi)
bm = bmesh.new(); add_box(bm, (0, 0.6, 0.80), (1.75, 2.9, 0.70))
col_cabin = new_obj("Crush_Collider_Cabin", bm, C_CAR)
bm = bmesh.new(); add_box(bm, (0, -1.53, 0.72), (1.75, 1.36, 0.56))
col_hood = new_obj("Crush_Collider_Hood", bm, C_CAR)
for o in (col_cabin, col_hood):
    o.display_type = 'WIRE'; o.hide_render = True

# --- sharning harakat yo'li (bake'dan keyin to'ldiriladi) + Geometry Nodes bukilish
path_me = bpy.data.meshes.new("Ball_Crush_Path")
path_me.from_pydata([(0, 0, 1000)], [], [])
path_me.attributes.new("frame", 'FLOAT', 'POINT').data[0].value = -1e6
ball_path = bpy.data.objects.new("Ball_Crush_Path", path_me); C_BALL.objects.link(ball_path)
ball_path.hide_render = True


def build_crush_nodes():
    ng = bpy.data.node_groups.new("G63_Crush_Deform", 'GeometryNodeTree')
    I = ng.interface
    I.new_socket("Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
    s = I.new_socket("Ball Radius", in_out='INPUT', socket_type='NodeSocketFloat'); s.default_value = BALL_R + 0.02
    s = I.new_socket("Bend Spread", in_out='INPUT', socket_type='NodeSocketInt'); s.default_value = 14
    s = I.new_socket("Wrinkles", in_out='INPUT', socket_type='NodeSocketFloat'); s.default_value = 0.35
    I.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    N = ng.nodes; L = ng.links
    gi = N.new("NodeGroupInput"); go = N.new("NodeGroupOutput")

    def vm(op, a, b=None, scale=None):
        n = N.new("ShaderNodeVectorMath"); n.operation = op
        L.new(a, n.inputs[0])
        if b is not None:
            L.new(b, n.inputs[1])
        if scale is not None:
            L.new(scale, n.inputs["Scale"])
        return n.outputs["Value"] if op == 'LENGTH' else n.outputs["Vector"]

    def fm(op, a, b):
        n = N.new("ShaderNodeMath"); n.operation = op
        for i, x in enumerate((a, b)):
            if isinstance(x, (int, float)):
                n.inputs[i].default_value = x
            else:
                L.new(x, n.inputs[i])
        return n.outputs[0]

    oi = N.new("GeometryNodeObjectInfo"); oi.transform_space = 'RELATIVE'
    oi.inputs["Object"].default_value = ball_path
    st = N.new("GeometryNodeInputSceneTime")
    na = N.new("GeometryNodeInputNamedAttribute"); na.data_type = 'FLOAT'; na.inputs["Name"].default_value = "frame"
    cmp = N.new("FunctionNodeCompare"); cmp.data_type = 'FLOAT'; cmp.operation = 'GREATER_THAN'
    L.new(na.outputs["Attribute"], cmp.inputs[0]); L.new(st.outputs["Frame"], cmp.inputs[1])
    dl = N.new("GeometryNodeDeleteGeometry"); dl.domain = 'POINT'
    L.new(oi.outputs["Geometry"], dl.inputs["Geometry"]); L.new(cmp.outputs["Result"], dl.inputs["Selection"])
    px = N.new("GeometryNodeProximity"); px.target_element = 'POINTS'
    L.new(dl.outputs["Geometry"], px.inputs[0])
    pos = N.new("GeometryNodeInputPosition").outputs[0]
    # Shar shu kadrgacha yetib borgan eng past nuqta: vertex ostidagi (z=-100) nuqtaga eng yaqin yo'l nuqtasi
    sp0 = N.new("ShaderNodeSeparateXYZ"); L.new(pos, sp0.inputs[0])
    q = N.new("ShaderNodeCombineXYZ"); L.new(sp0.outputs["X"], q.inputs["X"]); L.new(sp0.outputs["Y"], q.inputs["Y"])
    q.inputs["Z"].default_value = -100.0
    L.new(q.outputs[0], px.inputs["Sample Position"])
    cl = N.new("ShaderNodeSeparateXYZ"); L.new(px.outputs["Position"], cl.inputs[0])
    ddx = fm('SUBTRACT', sp0.outputs["X"], cl.outputs["X"]); ddy = fm('SUBTRACT', sp0.outputs["Y"], cl.outputs["Y"])
    r2 = fm('ADD', fm('MULTIPLY', ddx, ddx), fm('MULTIPLY', ddy, ddy))
    R2 = fm('MULTIPLY', gi.outputs["Ball Radius"], gi.outputs["Ball Radius"])
    inside = fm('GREATER_THAN', fm('SUBTRACT', R2, r2), 0.0)
    zcap = fm('SUBTRACT', cl.outputs["Z"], fm('SQRT', fm('MAXIMUM', fm('SUBTRACT', R2, r2), 0.0), 0.0))
    dz = fm('MULTIPLY', fm('MINIMUM', fm('SUBTRACT', zcap, sp0.outputs["Z"]), 0.0), inside)
    hc = N.new("ShaderNodeCombineXYZ"); L.new(dz, hc.inputs["Z"])
    hard = hc.outputs[0]          # shar teshib o'tgan ustundagi metall shar ostiga bosiladi (pastga bukiladi)
    blur = N.new("GeometryNodeBlurAttribute"); blur.data_type = 'FLOAT_VECTOR'
    L.new(hard, [s for s in blur.inputs if s.name == "Value" and s.enabled][0])
    L.new(gi.outputs["Bend Spread"], blur.inputs["Iterations"])
    soft = [s for s in blur.outputs if s.name == "Value" and s.enabled][0]
    is_hard = fm('GREATER_THAN', vm('LENGTH', hard), 0.002)
    mix = N.new("ShaderNodeMix"); mix.data_type = 'VECTOR'
    L.new(is_hard, mix.inputs[0]); L.new(soft, mix.inputs[4]); L.new(hard, mix.inputs[5])
    final = mix.outputs[1]                               # atrofidagi metall ham egiladi (bukilish)
    noise = N.new("ShaderNodeTexNoise"); noise.inputs["Scale"].default_value = 9.0
    noise.inputs["Detail"].default_value = 4.0
    L.new(pos, noise.inputs["Vector"])
    amp = fm('MULTIPLY', fm('MULTIPLY', fm('SUBTRACT', noise.outputs["Fac"], 0.5), vm('LENGTH', final)), gi.outputs["Wrinkles"])
    wr = vm('SCALE', N.new("GeometryNodeInputNormal").outputs["Normal"], scale=amp)   # g'ijimlanish burmalari
    # --- butun rama bukilishi: zarba nuqtasida o'rtasi cho'kadi, old/orqa uchlari ko'tariladi,
    #     eshiklar tashqariga bo'rtadi, kapot va orqa eshik g'ijimlanadi (Impact_Bend 0..1 animatsiya qilinadi)
    sep = N.new("ShaderNodeSeparateXYZ"); L.new(pos, sep.inputs[0])
    kval = N.new("ShaderNodeValue"); kval.name = "Impact_Bend"; kval.label = "Impact Bend (keyframed)"
    kval.outputs[0].default_value = 0.0
    K = kval.outputs[0]
    dy = fm('SUBTRACT', sep.outputs["Y"], PIVOT.y)

    def gauss(x, w):
        q = fm('DIVIDE', x, w)
        return fm('EXPONENT', fm('MULTIPLY', fm('MULTIPLY', q, q), -1.0), 0.0)

    def smooth(x, a, b, smoothstep=True):
        mr = N.new("ShaderNodeMapRange"); mr.clamp = True
        if smoothstep:
            mr.interpolation_type = 'SMOOTHSTEP'
        L.new(x, mr.inputs["Value"]); mr.inputs["From Min"].default_value = a; mr.inputs["From Max"].default_value = b
        return mr.outputs["Result"]
    q2 = fm('DIVIDE', dy, 2.3)
    zoff = fm('ADD', fm('MULTIPLY', gauss(dy, 1.1), -0.14), fm('MULTIPLY', fm('MULTIPLY', q2, q2), 0.04))
    xoff = fm('MULTIPLY', fm('MULTIPLY', fm('SIGN', sep.outputs["X"], 0.0), gauss(dy, 1.0)),
              fm('MULTIPLY', smooth(sep.outputs["Z"], 0.7, 1.7), 0.08))
    comb = N.new("ShaderNodeCombineXYZ"); L.new(xoff, comb.inputs["X"]); L.new(zoff, comb.inputs["Z"])
    nz2 = N.new("ShaderNodeTexNoise"); nz2.inputs["Scale"].default_value = 4.5; nz2.inputs["Detail"].default_value = 6.0
    L.new(pos, nz2.inputs["Vector"])
    bk = fm('MULTIPLY', fm('MULTIPLY', fm('SUBTRACT', nz2.outputs["Fac"], 0.5), smooth(fm('ABSOLUTE', dy, 0.0), 1.1, 2.1)),
            fm('MULTIPLY', smooth(sep.outputs["Z"], 0.75, 0.95, False), 0.09))
    buckle = vm('SCALE', N.new("GeometryNodeInputNormal").outputs["Normal"], scale=bk)
    glob = vm('SCALE', vm('ADD', comb.outputs[0], buckle), scale=K)
    sp = N.new("GeometryNodeSetPosition")
    L.new(gi.outputs[0], sp.inputs["Geometry"]); L.new(vm('ADD', vm('ADD', final, wr), glob), sp.inputs["Offset"])
    L.new(sp.outputs[0], go.inputs[0])
    return ng


crush_ng = build_crush_nodes()
for _o in (crush_body, static_body):
    _o.modifiers.new("Crush_Deform", 'NODES').node_group = crush_ng
