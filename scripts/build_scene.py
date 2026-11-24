"""
"Kran shari G63 ga tushadi" (Mercedes-Benz G63 AMG modeli: Black Snow, Sketchfab, CC-BY-4.0) - 20 soniyalik sahna (480 kadr, 24 fps).
Blender 5.2 da ishga tushirish (loyiha papkasidan):
    E:\\blendr\\blender.exe -b --factory-startup --python scripts\\build_scene.py -- .
Natija: wrecking_ball_scene.blend (fizika bake qilingan, render qilinmagan).
"""
import bpy, bmesh, math, random, os, sys
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["."]
ROOT = os.path.abspath(argv[0])
A = os.path.join(ROOT, "assets")
DO_BAKE = "--nobake" not in argv

FPS, END = 24, 648      # 27 soniya
RELEASE_F = 240          # shar uzilishi (10.0 s)
IMPACT_F = 291           # zarba kadri (12.1 s) - 22.5 m real tezlikda ~51 kadr
FALL_SPEED = float(os.environ.get("FALL_SPEED", "1.0"))  # 47.75 m ni ~96 kadrda bosib o'tishi uchun
SLOWMO = 0.35
BALL_R = 0.55
PIVOT = Vector((0.0, 0.35, 34.0))   # kran aravachasi (trolley) nuqtasi
BALL_Z = 25.0
random.seed(11)
TS_KEYS = [(1, 1.0), (RELEASE_F - 1, 1.0), (RELEASE_F, FALL_SPEED), (IMPACT_F, FALL_SPEED),
           (IMPACT_F + 2, 0.25), (IMPACT_F + 70, 0.25), (IMPACT_F + 90, SLOWMO), (500, SLOWMO), (525, 1.0), (END, 1.0)]

# ------------------------------------------------------------------ tozalash
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.name = "WreckingBall"
scene.render.fps = FPS
scene.frame_start, scene.frame_end = 1, END
scene.unit_settings.system = 'METRIC'


def coll(name):
    c = bpy.data.collections.new(name)
    scene.collection.children.link(c)
    return c


C_ENV, C_BLD, C_CRANE, C_CAR, C_FRAC, C_BALL, C_PROPS, C_CAM = [coll(n) for n in (
    "Environment", "Buildings", "Crane", "Car", "Car_Fracture", "WreckingBall", "Props", "Camera_Lights")]


def link(obj, c):
    for u in obj.users_collection:
        u.objects.unlink(obj)
    c.objects.link(obj)
    return obj


def new_obj(name, bm, c, mats=(), smooth=False, loc=(0, 0, 0)):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    for m in mats:
        me.materials.append(m)
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    ob.location = loc
    c.objects.link(ob)
    return ob


# ------------------------------------------------------------------ geometriya yordamchilari
def add_box(bm, center, size, mat=0):
    cx, cy, cz = center; sx, sy, sz = (s / 2 for s in size)
    v = [bm.verts.new((cx + x * sx, cy + y * sy, cz + z * sz))
         for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
    for f in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)):
        face = bm.faces.new([v[i] for i in f]); face.material_index = mat


def add_beam(bm, a, b, s, mat=0):
    a, b = Vector(a), Vector(b)
    d = (b - a); L = d.length
    if L < 1e-6:
        return
    z = d.normalized()
    x = z.cross(Vector((0, 0, 1)) if abs(z.z) < 0.95 else Vector((1, 0, 0))).normalized()
    y = z.cross(x)
    h = s / 2
    v = []
    for p in (a, b):
        for cx, cy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            v.append(bm.verts.new(p + x * cx * h + y * cy * h))
    for f in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
        face = bm.faces.new([v[i] for i in f]); face.material_index = mat


def add_slab(bm, pts, thick, mat=0):
    """Tekis ko'pburchak (pts) dan qalinlikka ega plastina."""
    pts = [Vector(p) for p in pts]
    n = (pts[1] - pts[0]).cross(pts[2] - pts[0]).normalized()
    top = [bm.verts.new(p + n * thick / 2) for p in pts]
    bot = [bm.verts.new(p - n * thick / 2) for p in pts]
    bm.faces.new(top).material_index = mat
    bm.faces.new(list(reversed(bot))).material_index = mat
    k = len(pts)
    for i in range(k):
        j = (i + 1) % k
        bm.faces.new((bot[i], bot[j], top[j], top[i])).material_index = mat
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])


def add_prism(bm, profile_xz, y0, y1, mat=0):
    """XZ profilni Y bo'ylab cho'zish (mashina korpusi uchun)."""
    f0 = [bm.verts.new((x, y0, z)) for x, z in profile_xz]
    f1 = [bm.verts.new((x, y1, z)) for x, z in profile_xz]
    bm.faces.new(f0).material_index = mat
    bm.faces.new(list(reversed(f1))).material_index = mat
    k = len(profile_xz)
    for i in range(k):
        j = (i + 1) % k
        bm.faces.new((f0[i], f0[j], f1[j], f1[i])).material_index = mat
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])


# ------------------------------------------------------------------ materiallar
def principled(name, color=(0.8, 0.8, 0.8), metal=0.0, rough=0.5, **kw):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Metallic"].default_value = metal
    b.inputs["Roughness"].default_value = rough
    for k, v in kw.items():
        b.inputs[k].default_value = v
    m.diffuse_color = (*color, 1)
    return m


def img(path, colorspace="sRGB"):
    im = bpy.data.images.load(path, check_existing=True)
    im.colorspace_settings.name = colorspace
    return im


def pbr_box(name, folder, scale=1.0, tint=None, base=None):
    """Poly Haven teksturasi: Object koordinata + Box proyeksiya (UV shart emas)."""
    d = os.path.join(A, "textures", folder)
    m = base or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links
    b = N["Principled BSDF"]
    tc = N.new("ShaderNodeTexCoord"); mp = N.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (scale, scale, scale)
    L.new(tc.outputs["Object"], mp.inputs["Vector"])

    def tex(kind, cs):
        t = N.new("ShaderNodeTexImage")
        t.image = img(os.path.join(d, f"{folder}_{kind}_2k.jpg"), cs)
        t.projection = 'BOX'; t.projection_blend = 0.25
        L.new(mp.outputs["Vector"], t.inputs["Vector"])
        return t
    dif = tex("diff", "sRGB")
    if tint:
        mix = N.new("ShaderNodeMix"); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'
        mix.inputs["Factor"].default_value = 1.0
        mix.inputs[7].default_value = (*tint, 1)
        L.new(dif.outputs["Color"], mix.inputs[6]); L.new(mix.outputs[2], b.inputs["Base Color"])
    else:
        L.new(dif.outputs["Color"], b.inputs["Base Color"])
    L.new(tex("rough", "Non-Color").outputs["Color"], b.inputs["Roughness"])
    nm = N.new("ShaderNodeNormalMap")
    L.new(tex("nor_gl", "Non-Color").outputs["Color"], nm.inputs["Color"])
    L.new(nm.outputs["Normal"], b.inputs["Normal"])
    return m


M_GROUND = pbr_box("Ground_GravelConcrete", "gravel_concrete", scale=0.25)
M_CONCRETE = pbr_box("Building_Concrete", "concrete_wall_008", scale=0.3)
M_RUST = pbr_box("Ball_RustMetal", "rust_coarse_01", scale=0.8)
b = M_RUST.node_tree.nodes["Principled BSDF"]; b.inputs["Metallic"].default_value = 0.85
M_REBAR = principled("Rebar_Rust", (0.25, 0.1, 0.05), 0.7, 0.8)
M_CRANE = principled("Crane_YellowPaint", (0.85, 0.55, 0.02), 0.2, 0.45)
M_STEEL = principled("Steel_Cable", (0.35, 0.35, 0.37), 1.0, 0.35)
M_WEIGHT = principled("Counterweight_Concrete", (0.45, 0.44, 0.42), 0.0, 0.9)
M_PAINT = principled("Car_Paint_Blue", (0.02, 0.12, 0.45), 0.9, 0.22, **{"Coat Weight": 1.0, "Coat Roughness": 0.03})
M_INNER = principled("Car_Inner_Metal", (0.3, 0.3, 0.32), 1.0, 0.55)
M_GLASS = principled("Car_Glass", (0.6, 0.7, 0.72), 0.0, 0.02, **{"Transmission Weight": 1.0, "IOR": 1.5})
M_GLASS_IN = principled("Car_Glass_Edge", (0.55, 0.75, 0.7), 0.0, 0.08, **{"Transmission Weight": 1.0, "IOR": 1.5})
for gm in (M_GLASS, M_GLASS_IN):
    try:
        gm.surface_render_method = 'DITHERED'
    except Exception:
        pass
M_TIRE = principled("Tire_Rubber", (0.02, 0.02, 0.02), 0.0, 0.85)
M_RIM = principled("Rim_Chrome", (0.9, 0.9, 0.92), 1.0, 0.12)
M_BLACK = principled("Trim_BlackGloss", (0.01, 0.01, 0.01), 0.0, 0.15)
M_INTERIOR = principled("Interior_Fabric", (0.04, 0.04, 0.045), 0.0, 0.9)
M_HEAD = principled("Headlight_LED", (1, 1, 1), 0.0, 0.1, **{"Emission Color": (0.9, 0.95, 1, 1), "Emission Strength": 6.0})
M_TAIL = principled("Taillight_LED", (0.8, 0.02, 0.02), 0.0, 0.1, **{"Emission Color": (1, 0.02, 0.02, 1), "Emission Strength": 4.0})

# ------------------------------------------------------------------ dunyo (HDRI) va quyosh
world = bpy.data.worlds.new("HDRI_HilltopConstruction"); scene.world = world
world.use_nodes = True
wn = world.node_tree.nodes; wl = world.node_tree.links
env = wn.new("ShaderNodeTexEnvironment")
env.image = img(os.path.join(A, "hdri", "hilltop_construction_2k.hdr"), "Linear Rec.709")
wmap = wn.new("ShaderNodeMapping"); wtc = wn.new("ShaderNodeTexCoord")
wmap.inputs["Rotation"].default_value[2] = math.radians(110)
wl.new(wtc.outputs["Generated"], wmap.inputs["Vector"]); wl.new(wmap.outputs["Vector"], env.inputs["Vector"])
wl.new(env.outputs["Color"], wn["Background"].inputs["Color"])
wn["Background"].inputs["Strength"].default_value = 1.0

sun_d = bpy.data.lights.new("Sun", 'SUN'); sun_d.energy = 3.2; sun_d.angle = math.radians(1.5)
sun = bpy.data.objects.new("Sun", sun_d); C_CAM.objects.link(sun)
sun.rotation_euler = (math.radians(50), math.radians(10), math.radians(140))

# ------------------------------------------------------------------ zamin, binolar, maydon
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'environment_section.py'), encoding='utf-8').read())

# ------------------------------------------------------------------ minorali kran
MAST = Vector((PIVOT.x, 24.0, 0))
MH = PIVOT.z + 3.0
bm = bmesh.new(); s = 1.0
for k in range(int(MH / 2)):
    z0, z1 = k * 2.0, k * 2.0 + 2.0
    c = [(MAST.x + dx, MAST.y + dy) for dx, dy in ((-s, -s), (s, -s), (s, s), (-s, s))]
    for i in range(4):
        x0, y0 = c[i]; x1, y1 = c[(i + 1) % 4]
        add_beam(bm, (x0, y0, z0), (x0, y0, z1), 0.16)
        add_beam(bm, (x0, y0, z1), (x1, y1, z1), 0.08)
        add_beam(bm, (x0, y0, z0) if k % 2 else (x1, y1, z0), (x1, y1, z1) if k % 2 else (x0, y0, z1), 0.06)
# kabina va tepasi
add_box(bm, (MAST.x + 1.6, MAST.y, MH - 1.0), (1.8, 2.2, 2.2))
add_beam(bm, (MAST.x, MAST.y, MH), (MAST.x, MAST.y, MH + 7), 0.3)
# strela (jib) - uchburchak ferma, -Y tomonga
jt = MAST.y; je = PIVOT.y - 4.0; jz = PIVOT.z + 0.6
n_seg = int((jt - je) / 2)
for k in range(n_seg):
    y0, y1 = jt - k * 2, jt - (k + 1) * 2
    for dx in (-0.8, 0.8):
        add_beam(bm, (MAST.x + dx, y0, jz), (MAST.x + dx, y1, jz), 0.12)
        add_beam(bm, (MAST.x + dx, y0, jz), (MAST.x, y1 if k % 2 else y0, jz + 1.6), 0.06)
    add_beam(bm, (MAST.x, y0, jz + 1.6), (MAST.x, y1, jz + 1.6), 0.12)
    add_beam(bm, (MAST.x - 0.8, y1, jz), (MAST.x + 0.8, y1, jz), 0.06)
# qarshi strela + qarshi yuklar
add_beam(bm, (MAST.x - 0.8, jt, jz), (MAST.x - 0.8, jt + 14, jz), 0.14)
add_beam(bm, (MAST.x + 0.8, jt, jz), (MAST.x + 0.8, jt + 14, jz), 0.14)
# tortqi arqonlar
add_beam(bm, (MAST.x, MAST.y, MH + 7), (MAST.x, je + 6, jz + 1.6), 0.05)
add_beam(bm, (MAST.x, MAST.y, MH + 7), (MAST.x, jt + 13, jz), 0.05)
crane = new_obj("Crane_TowerCrane", bm, C_CRANE, [M_CRANE])
bm = bmesh.new()
for i in range(4):
    add_box(bm, (MAST.x, jt + 9 + i * 1.3, jz - 1.2), (2.4, 1.2, 2.0))
new_obj("Crane_Counterweights", bm, C_CRANE, [M_WEIGHT])
bm = bmesh.new(); add_box(bm, (MAST.x, MAST.y, -0.4 + 0.75), (6, 6, 1.5))
new_obj("Crane_Foundation", bm, C_CRANE, [M_CONCRETE])
# aravacha (trolley)
bm = bmesh.new(); add_box(bm, (PIVOT.x, PIVOT.y, PIVOT.z + 0.35), (1.9, 1.4, 0.5))
new_obj("Crane_Trolley", bm, C_CRANE, [M_CRANE])
# ikkinchi (fon) kran
for o in [o for o in C_CRANE.objects if o.type == 'MESH' and o.name.startswith("Crane_")]:
    c2 = o.copy(); C_CRANE.objects.link(c2); c2.name = o.name.replace("Crane_", "Crane2_")
    c2.matrix_world = (Matrix.Translation((46, 64, 0)) @ Matrix.Rotation(math.radians(-115), 4, 'Z') @ Matrix.Scale(1.25, 4)
                       @ Matrix.Translation(-MAST) @ o.matrix_world)

# ------------------------------------------------------------------ tebranuvchi tros + shar
pivot = bpy.data.objects.new("Cable_Pivot", None); pivot.location = PIVOT
pivot.empty_display_type = 'ARROWS'; C_CRANE.objects.link(pivot)
L_CENTER = PIVOT.z - BALL_Z
bm = bmesh.new()
add_beam(bm, (0.12, 0, 0), (0.12, 0, -(L_CENTER - BALL_R - 0.55)), 0.04)
add_beam(bm, (-0.12, 0, 0), (-0.12, 0, -(L_CENTER - BALL_R - 0.55)), 0.04)
add_box(bm, (0, 0, -(L_CENTER - BALL_R - 0.35)), (0.5, 0.35, 0.45))   # ilgak bloki
cable = new_obj("Crane_Cable_Hook", bm, C_CRANE, [M_STEEL])
cable.parent = pivot

bpy.ops.mesh.primitive_uv_sphere_add(radius=BALL_R, segments=48, ring_count=24, location=(PIVOT.x, 0, BALL_Z))
ball = bpy.context.active_object; ball.name = "WreckingBall"; link(ball, C_BALL)
ball.data.materials.append(M_RUST); bpy.ops.object.shade_smooth()
bpy.ops.mesh.primitive_torus_add(major_radius=0.3 * BALL_R, minor_radius=0.08 * BALL_R, location=(PIVOT.x, 0, BALL_Z + BALL_R + 0.12),
                                 rotation=(math.radians(90), 0, 0))
shackle = bpy.context.active_object; shackle.name = "WreckingBall_Shackle"; link(shackle, C_BALL)
shackle.data.materials.append(M_STEEL)
shackle.parent = ball; shackle.matrix_parent_inverse = ball.matrix_world.inverted()


def swing_angle(f):
    tsec = (f - 1) / FPS
    amp = math.radians(4.0) * max(0.0, 1 - tsec / 3.4)   # 82-kadrda to'liq to'xtaydi (uzilishda yon tezlik yo'q)
    return amp * math.sin(2 * math.pi * tsec / 6.0)


for f in range(1, RELEASE_F + 1, 3):
    a = swing_angle(f)
    pivot.rotation_euler = (0, a, 0); pivot.keyframe_insert("rotation_euler", frame=f)
    ball.location = PIVOT + Vector((-math.sin(a) * L_CENTER, 0, -math.cos(a) * L_CENTER))
    ball.rotation_euler = (0, a, 0)
    ball.keyframe_insert("location", frame=f); ball.keyframe_insert("rotation_euler", frame=f)
# tros uzilishi: ilgak va tros prujinadek yuqoriga sakraydi
for f, sz in ((RELEASE_F - 1, 1.0), (RELEASE_F + 1, 0.9), (RELEASE_F + 4, 1.035), (RELEASE_F + 8, 0.975),
              (RELEASE_F + 13, 1.012), (RELEASE_F + 20, 1.0)):
    cable.scale = (1, 1, sz); cable.keyframe_insert("scale", index=2, frame=f)
cable.scale = (1, 1, 1)
# sharda qolgan uzilgan tros bo'lagi (titilgan uchlari bilan) - faqat uzilgandan keyin ko'rinadi
scene.frame_set(1)
bm = bmesh.new(); top = Vector((PIVOT.x, PIVOT.y, BALL_Z + BALL_R + 0.2))
for dx in (-0.05, 0.05):
    add_beam(bm, top + Vector((dx, 0, 0)), top + Vector((dx * 1.5, 0, 0.42)), 0.035)
    for k in range(4):
        a = k / 4 * 2 * math.pi
        add_beam(bm, top + Vector((dx * 1.5, 0, 0.42)), top + Vector((dx * 1.5 + 0.06 * math.cos(a), 0.06 * math.sin(a), 0.5 + 0.04 * k)), 0.008)
stub = new_obj("Cable_Broken_Stub", bm, C_BALL, [M_STEEL])
stub.parent = ball; stub.matrix_parent_inverse = ball.matrix_world.inverted()
for f, h in ((RELEASE_F - 1, True), (RELEASE_F, False)):
    stub.hide_render = h; stub.hide_viewport = h
    stub.keyframe_insert("hide_render", frame=f); stub.keyframe_insert("hide_viewport", frame=f)
# tros uzilgandan keyin so'nib tebranadi
for f in range(RELEASE_F + 3, RELEASE_F + 90, 6):
    tt = (f - RELEASE_F) / FPS
    pivot.rotation_euler = (math.radians(1.5) * math.exp(-tt * 0.8) * math.sin(tt * 3.5), 0, 0)
    pivot.keyframe_insert("rotation_euler", frame=f)

# ------------------------------------------------------------------ Voronoi parchalash (Cell Fracture o'rnida)
def sample_surface_points(obj, count, bias_center=None, sigma=0.6):
    me = obj.data; mw = obj.matrix_world
    tris = []
    for p in me.polygons:
        vs = [mw @ me.vertices[i].co for i in p.vertices]
        for i in range(1, len(vs) - 1):
            a, b_, c = vs[0], vs[i], vs[i + 1]
            area = ((b_ - a).cross(c - a)).length / 2
            tris.append((area, a, b_, c, (mw.to_3x3() @ p.normal).normalized()))
    tris = [t for t in tris if t[0] > 1e-7]
    tot = sum(t[0] for t in tris)
    pts = []
    tries = 0
    while len(pts) < count and tries < count * 200:
        tries += 1
        r = random.random() * tot; acc = 0
        for area, a, b_, c, n in tris:
            acc += area
            if acc >= r:
                break
        u, v = random.random(), random.random()
        if u + v > 1:
            u, v = 1 - u, 1 - v
        p = a + (b_ - a) * u + (c - a) * v
        if bias_center is not None:
            d = (Vector((p.x, p.y, 0)) - Vector((bias_center.x, bias_center.y, 0))).length
            if random.random() > math.exp(-(d / (sigma * 2.2)) ** 2) + 0.25:
                continue
        pts.append(p - n * 0.01)
    return pts


def fracture(obj, count, target_coll, inner_mat, bias=None, neighbours=18):
    src = bmesh.new(); src.from_mesh(obj.data); src.transform(obj.matrix_world)
    pts = sample_surface_points(obj, count, bias)
    mats = list(obj.data.materials) + [inner_mat]
    inner_idx = len(mats) - 1
    pieces = []
    for i, p in enumerate(pts):
        bm = src.copy()
        near = sorted((q for j, q in enumerate(pts) if j != i), key=lambda q: (q - p).length)[:neighbours]
        for q in near:
            n = (q - p).normalized(); co = (p + q) / 2
            res = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:],
                                         plane_co=co, plane_no=n, clear_outer=True, dist=1e-5)
            cut = [e for e in res["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
            if cut:
                fr = bmesh.ops.holes_fill(bm, edges=cut, sides=0)
                for f in fr["faces"]:
                    f.material_index = inner_idx
            if len(bm.verts) < 4:
                break
        if len(bm.verts) < 4 or len(bm.faces) < 4:
            bm.free(); continue
        bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        cen = sum((v.co for v in bm.verts), Vector()) / len(bm.verts)
        bmesh.ops.translate(bm, vec=-cen, verts=bm.verts[:])
        ob = new_obj(f"{obj.name}_frag_{len(pieces):02d}", bm, target_coll, mats, loc=cen)
        pieces.append(ob)
    src.free()
    obj.hide_viewport = obj.hide_render = True
    link(obj, C_FRAC)
    return pieces


exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'car_g63_section.py'), encoding='utf-8').read())

# ------------------------------------------------------------------ rekvizitlar (Poly Haven glTF)
def import_gltf(name):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(A, "models", name, f"{name}_1k.gltf"))
    new = [o for o in bpy.data.objects if o not in before]
    for o in new:
        link(o, C_PROPS)
    return [o for o in new if o.type == 'MESH']


def place(src_objs, loc, rot_z=0.0):
    out = []
    for so in src_objs:
        o = so.copy(); C_PROPS.objects.link(o)
        o.parent = None
        o.location = Vector(loc) + so.matrix_world.translation
        o.rotation_euler = (*so.rotation_euler[:2], so.rotation_euler[2] + rot_z)
        out.append(o)
    return out


props_rb = []
for name, spots in {
    "concrete_road_barrier": [((-7.0, 3.5, 0), 0.3), ((3.5, -7.0, 0), -0.4), ((4.6, 3.5, 0), 1.6), ((6.0, -1.0, 0), 1.4)],
    "Barrel_01": [((3.6, -3.0, 0), 0), ((4.3, -2.6, 0), 1), ((3.9, -3.8, 0), 2)],
    "old_tyre": [((-3.5, 2.6, 0), 0), ((-3.4, 2.7, 0.25), 0.5)],
    "wooden_crate_01": [((-5.2, 1.0, 0), 0.2), ((-5.0, 1.1, 0.75), 0.9), ((-6.4, 0.6, 0), 0.6)],
    "wooden_ladder": [((-26.0, -18.6, 0), 0.0)],
    "plastic_crate_01": [((-23.0, -18.0, 0), 0.3), ((-22.3, -18.3, 0), 1.2)],
    "wooden_crate_02": [((9.0, -12.0, 0), 0.4), ((-11.5, 19.0, 0), 1.1)],
    "modular_industrial_pipes_01": [((-14.0, -15.0, 0), 0.2)],
    "metal_jerrycan": [((-23.6, -17.2, 0), 0.8), ((8.2, -11.4, 0), 2.0)],
}.items():
    base = import_gltf(name)
    for loc, rz in spots:
        props_rb += place(base, loc, rz)
    for o in base:
        bpy.data.objects.remove(o, do_unlink=True)
# Ctrl+A -> Apply Rotation & Scale (barcha obyektlar)
bpy.ops.object.select_all(action='DESELECT')
for o in scene.objects:
    if o.type == 'MESH' and o.parent is None and o.data.users == 1:
        o.select_set(True)
bpy.context.view_layer.objects.active = ball
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
bpy.ops.object.select_all(action='DESELECT')

# ------------------------------------------------------------------ Rigid Body fizika
bpy.ops.rigidbody.world_add()
rbw = scene.rigidbody_world
rbw.point_cache.frame_start = 1
rbw.point_cache.frame_end = END          # 288 da to'xtab qolmasligi uchun
rbw.substeps_per_frame = 20
rbw.solver_iterations = 20
rbw.collection = bpy.data.collections.new("RigidBodyWorld")


def origin_to_center(obj):
    """BOX/SPHERE fizik shakli origin atrofida quriladi -> origin geometriya markazida bo'lishi shart."""
    vs = [v.co for v in obj.data.vertices]
    c = Vector([(min(v[i] for v in vs) + max(v[i] for v in vs)) / 2 for i in range(3)])
    obj.data.transform(Matrix.Translation(-c)); obj.location += c


def rb(obj, kind, shape, mass=1.0, friction=0.6, bounce=0.1, margin=0.005):
    if shape in ('BOX', 'SPHERE', 'CYLINDER', 'CAPSULE', 'CONE'):
        origin_to_center(obj)
    with bpy.context.temp_override(object=obj, active_object=obj, selected_objects=[obj]):
        bpy.ops.rigidbody.object_add(type=kind)
    r = obj.rigid_body
    r.collision_shape = shape; r.mass = mass
    r.friction = friction; r.restitution = bounce
    r.use_margin = True; r.collision_margin = margin
    r.linear_damping = 0.08; r.angular_damping = 0.15
    return r


rb(ground, 'PASSIVE', 'BOX', margin=0.0)
for c in (col_cabin, col_hood):
    rb(c, 'PASSIVE', 'BOX', friction=0.9, bounce=1.0, margin=0.0)
    set_layers(c, (0,)) if 'set_layers' in globals() else None
for o in props_rb:
    rb(o, 'PASSIVE', 'CONVEX_HULL', margin=0.01)

r = rb(ball, 'ACTIVE', 'SPHERE', mass=1000.0, friction=0.8, bounce=0.22, margin=0.02)
r.kinematic = True;  ball.keyframe_insert("rigid_body.kinematic", frame=RELEASE_F - 1)
r.kinematic = False; ball.keyframe_insert("rigid_body.kinematic", frame=RELEASE_F)
r.use_deactivation = False
# zarbadan keyin shar dumalab ketmasligi uchun damping kalitlari
for f, ld, ad in ((1, 0.0, 0.1), (IMPACT_F + 2, 0.0, 0.1), (IMPACT_F + 12, 0.6, 0.9)):
    r.linear_damping = ld; r.angular_damping = ad
    ball.keyframe_insert("rigid_body.linear_damping", frame=f)
    ball.keyframe_insert("rigid_body.angular_damping", frame=f)

for o in glass_frags:
    rb(o, 'ACTIVE', 'CONVEX_HULL', mass=0.25, friction=0.5, bounce=0.15, margin=0.002)
    o.rigid_body.linear_damping = 0.3; o.rigid_body.angular_damping = 0.4
# Speed (time_scale) kalitlari: tushish -> zarbada slow-mo -> normal
bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
for f, v in TS_KEYS:
    rbw.time_scale = v; scene.keyframe_insert("rigidbody_world.time_scale", frame=f)

exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'impact_shake_section.py'), encoding='utf-8').read())
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fx_section.py'), encoding='utf-8').read())

# ------------------------------------------------------------------ kamera
cam_d = bpy.data.cameras.new("Camera"); cam_d.lens = 20; cam_d.clip_end = 1000
cam_d.dof.use_dof = False
cam = bpy.data.objects.new("Camera", cam_d); C_CAM.objects.link(cam); scene.camera = cam
target = bpy.data.objects.new("Camera_Target", None); C_CAM.objects.link(target)
target.empty_display_size = 0.5
target.location = (PIVOT.x, PIVOT.y, 1.3)
tc = cam.constraints.new('TRACK_TO'); tc.target = target
tc.track_axis = 'TRACK_NEGATIVE_Z'; tc.up_axis = 'UP_Y'
cl = target.constraints.new('COPY_LOCATION'); cl.target = ball; cl.name = "Follow_Ball"
for f, v in ((1, 1.0), (IMPACT_F + 10, 1.0), (IMPACT_F + 45, 0.0), (END, 0.0)):
    cl.influence = v; target.keyframe_insert('constraints["Follow_Ball"].influence', frame=f)
# kamera yo'li shar trayektoriyasiga bog'liq -> bake'dan keyin camera_section.py da yoziladi
# zarbada kamera titrashi (operator qo'li silkingandek)
rig = bpy.data.objects.new("Camera_Shake_Rig", None); C_CAM.objects.link(rig)
cam.parent = rig
bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
_r = random.Random(3)
for f in range(IMPACT_F - 1, IMPACT_F + 46):
    a = 0.0 if f < IMPACT_F else 0.07 * math.exp(-TAU[f] * 4.0)
    rig.location = (_r.uniform(-a, a), _r.uniform(-a, a), _r.uniform(-a, a) * 1.4)
    rig.keyframe_insert("location", frame=f)
rig.location = (0, 0, 0); rig.keyframe_insert("location", frame=IMPACT_F + 47)
bpy.context.preferences.edit.keyframe_new_interpolation_type = 'BEZIER'

# ------------------------------------------------------------------ tovushlar (Video Sequencer)
se = scene.sequence_editor_create()
strips = se.strips if hasattr(se, "strips") else se.sequences
S = os.path.join(A, "sounds")
for i, (fn, frame, ch, vol) in enumerate((
        ("ambient_construction_wind.wav", 1, 1, 0.6),
        ("crane_cable_creak.wav", 140, 2, 0.7),
        ("hook_release_snap.wav", RELEASE_F, 3, 0.9),
        ("ball_fall_whoosh.wav", RELEASE_F + 1, 4, 0.8),
        ("impact_crash_slowmo.wav", IMPACT_F, 5, 1.0),
        ("debris_settle.wav", IMPACT_F + 150, 6, 0.8))):
    st = strips.new_sound(fn.rsplit(".", 1)[0], os.path.join(S, fn), ch, frame)
    st.volume = vol
scene.render.use_sequencer = True   # faqat ovoz strip-lari -> 3D sahna renderlanadi

# ------------------------------------------------------------------ render sozlamalari (render qilinmaydi)
for eng in ('BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT'):
    try:
        scene.render.engine = eng; break
    except TypeError:
        pass
scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGB'
scene.render.filepath = "//render/frame_"
scene.render.use_motion_blur = True
try:
    scene.eevee.use_raytracing = True
    scene.eevee.taa_render_samples = 64
    scene.eevee.volumetric_end = 350.0
    scene.eevee.volumetric_tile_size = '8'
except Exception:
    pass
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'AgX - Medium High Contrast'
scene.view_settings.exposure = -0.45
scene.render.motion_blur_shutter = 0.3
scene.frame_set(1)

# ------------------------------------------------------------------ saqlash + bake
out = os.path.join(ROOT, "wrecking_ball_scene.blend")
bpy.ops.wm.save_as_mainfile(filepath=out)
bpy.ops.file.make_paths_relative()

if DO_BAKE:
    with bpy.context.temp_override(scene=scene):
        bpy.ops.ptcache.bake_all(bake=True)
    print("baked:", rbw.point_cache.is_baked)
    # zarba kadrini tekshirish
    hit = None
    roof_top = ROOF_Z
    for f in range(RELEASE_F, IMPACT_F + 60):
        scene.frame_set(f)
        z = ball.matrix_world.translation.z
        if hit is None and z - BALL_R <= roof_top:
            hit = f
        if f % 12 == 1 or f in (200, 210, 214, 216, 217, 218, 220, 230):
            print(f"f{f}: ball z={z:.2f}")
    print("IMPACT FRAME ~", hit)
    import statistics
    scene.frame_set(END)
    ds = sorted((o.matrix_world.translation.xy - IMPACT.xy).length for o in glass_frags)
    print(f"debris dist @480: median={statistics.median(ds):.1f} max={ds[-1]:.1f} >10m={sum(d > 10 for d in ds)}")
    for f in (250, 360, 480):
        scene.frame_set(f)
        zs = [o.matrix_world.translation for o in glass_frags[:5]]
        print(f"f{f}: ball={tuple(round(c, 2) for c in ball.matrix_world.translation)} frag0={tuple(round(c, 2) for c in zs[0])}")
    # sharning yo'lini GN va kamera uchun yozish (har kadr 4 ta oraliq nuqta)
    pts = []
    for f in range(RELEASE_F, END + 1):
        scene.frame_set(f); pts.append((f, ball.matrix_world.translation.copy()))
    verts, frames = [(0, 0, 1000)], [-1e6]
    for (f0, p0), (f1, p1) in zip(pts, pts[1:]):
        for k in range(4):
            verts.append(p0.lerp(p1, k / 4)); frames.append(f0 + k / 4)
    verts.append(pts[-1][1]); frames.append(float(pts[-1][0]))
    pm = bpy.data.meshes.new("Ball_Crush_Path"); pm.from_pydata(verts, [], [])
    pm.attributes.new("frame", 'FLOAT', 'POINT').data.foreach_set("value", frames)
    old = ball_path.data; ball_path.data = pm; bpy.data.meshes.remove(old); pm.name = "Ball_Crush_Path"
    exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'camera_section.py'), encoding='utf-8').read())
    for o, *_ in detach_parts:
        scene.frame_set(IMPACT_F + 8); a = o.matrix_world.translation.copy()
        scene.frame_set(IMPACT_F + 120); b = o.matrix_world.translation.copy()
        print(f"PART {o.name:18} @225={tuple(round(x, 2) for x in a)} @330={tuple(round(x, 2) for x in b)}")
    for f in (IMPACT_F + 2, IMPACT_F + 40, IMPACT_F + 150):
        scene.frame_set(f)
        print(f"f{f}: ball z={ball.matrix_world.translation.z:.2f}")
    scene.frame_set(IMPACT_F + 150)
    dg = bpy.context.evaluated_depsgraph_get()
    ev = crush_body.evaluated_get(dg).data
    n = len(ev.vertices); a = np.empty(n * 3, np.float32); ev.vertices.foreach_get("co", a)
    b = np.empty(len(crush_body.data.vertices) * 3, np.float32); crush_body.data.vertices.foreach_get("co", b)
    if len(a) == len(b):
        d = np.linalg.norm((a - b).reshape(-1, 3), axis=1)
        print(f"CRUSH @300: max={d.max():.2f}m moved>5cm={int((d > 0.05).sum())} verts")
    scene.frame_set(1)

bpy.ops.wm.save_as_mainfile(filepath=out)
print("SAVED", out)
