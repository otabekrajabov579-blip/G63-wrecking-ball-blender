"""Topshirish uchun ixcham .blend: yangi ovoz, kichraytirilgan va ichiga joylangan teksturalar,
soddalashtirilgan ikkinchi darajali geometriya.
    E:\\blendr\\blender.exe -b wrecking_ball_scene.blend --python scripts\\optimize_blend.py -- OUT.blend [--free-cache] [--tex 1024] [--far 512]
"""
import bpy, os, sys

argv = sys.argv[sys.argv.index("--") + 1:]
OUT = argv[0]
FREE_CACHE = "--free-cache" in argv
TEX = int(argv[argv.index("--tex") + 1]) if "--tex" in argv else 1024
FAR = int(argv[argv.index("--far") + 1]) if "--far" in argv else 512
CRUSH_RATIO = float(argv[argv.index("--crush") + 1]) if "--crush" in argv else 0.45
S = bpy.context.scene
ROOT = bpy.path.abspath("//")
TMP = os.path.join(ROOT, "assets", "opt_textures"); os.makedirs(TMP, exist_ok=True)

# ---- 1) ovoz: eski sintez strip-lar o'rniga yakuniy miks (OGG)
se = S.sequence_editor
strips = se.strips if hasattr(se, "strips") else se.sequences
for st in list(strips):
    if st.type == 'SOUND':
        strips.remove(st)
ogg = os.path.join(ROOT, "assets", "sounds", "final_mix.ogg")
st = strips.new_sound("Final_Mix_BBC", ogg, 1, 1)
st.volume = 1.0
print("sound:", st.name, os.path.getsize(ogg) // 1024, "KB")

# ---- 2) teksturalar: kichraytirib, JPEG/HDR qilib, ichiga joylash
FAR_SETS = ("red_brick", "plywood", "corrugated", "container_side", "worn_planks", "concrete_tile_facade",
            "concrete_floor_damaged", "concrete_wall_008", "brown_mud_dry")
for im in list(bpy.data.images):
    if im.source != 'FILE' or im.size[0] == 0:
        continue
    name = os.path.splitext(os.path.basename(im.filepath or im.name))[0]
    is_hdr = im.filepath.lower().endswith(".hdr")
    lim = 1024 if is_hdr else (FAR if any(k in name for k in FAR_SETS) else TEX)
    w, h = im.size
    if max(w, h) > lim:
        f = lim / max(w, h)
        im.scale(max(1, int(w * f)), max(1, int(h * f)))
    if is_hdr:
        path = os.path.join(TMP, name + ".hdr"); im.file_format = 'HDR'
    else:
        path = os.path.join(TMP, name + ".jpg"); im.file_format = 'JPEG'
    S.render.image_settings.quality = 78
    im.save_render(path, scene=S) if False else None
    im.filepath_raw = path
    try:
        im.save(filepath=path, quality=78)
    except TypeError:
        im.save()
    cs = im.colorspace_settings.name
    im.source = 'FILE'; im.filepath = path; im.reload(); im.colorspace_settings.name = cs
bpy.ops.file.pack_all()

# ---- 2b) ishlatilmaydigan UV xaritalar va rang atributlarini o'chirish (ko'rinishga ta'sir qilmaydi)
def used_names(mats):
    uv, attr = set(), set()
    for m in mats:
        if not (m and m.node_tree):
            continue
        for n in m.node_tree.nodes:
            if n.bl_idname == 'ShaderNodeUVMap' and n.uv_map:
                uv.add(n.uv_map)
            if n.bl_idname == 'ShaderNodeNormalMap' and n.uv_map:
                uv.add(n.uv_map)
            if n.bl_idname in ('ShaderNodeVertexColor',):
                attr.add(n.layer_name or "*")
            if n.bl_idname == 'ShaderNodeAttribute':
                attr.add(n.attribute_name); uv.add(n.attribute_name)
    return uv, attr


uv_removed = col_removed = 0
for me in bpy.data.meshes:
    uv, attr = used_names(me.materials)
    keep_render = next((u.name for u in me.uv_layers if u.active_render), None)
    for u in list(me.uv_layers):
        if u.name != keep_render and u.name not in uv:
            me.uv_layers.remove(u); uv_removed += 1
    for ca in list(me.color_attributes):
        if "*" not in attr and ca.name not in attr:
            me.color_attributes.remove(ca); col_removed += 1
print("removed uv layers:", uv_removed, "color attrs:", col_removed)

# ---- 3) ikkinchi darajali geometriyani soddalashtirish (kadrda kichik ko'rinadigan qismlar)
def decimate(obj, ratio):
    if obj.type != 'MESH' or obj.data.users > 1 and obj.name.startswith("Crane2_"):
        return
    m = obj.modifiers.new("Opt_Decimate", 'DECIMATE'); m.ratio = ratio; m.use_collapse_triangulate = False
    # modifikatorni stek boshiga qo'yish va qo'llash
    with bpy.context.temp_override(object=obj, active_object=obj, selected_objects=[obj], selected_editable_objects=[obj]):
        bpy.ops.object.modifier_move_to_index(modifier=m.name, index=0)
        bpy.ops.object.modifier_apply(modifier=m.name)


before = sum(len(m.vertices) for m in bpy.data.meshes)
plan = {"G63_Wheels": 0.35, "G63_Part_Grille": 0.3, "G63_Body_Static": 0.55}
for name, r in plan.items():
    o = bpy.data.objects.get(name)
    if o:
        decimate(o, r)
# bukiladigan korpus: zarba zonasi (tom, ustunlar) to'liq zichlikda qoladi, qolgani soddalashtiriladi
crush = bpy.data.objects.get("G63_Body_Crush")
if crush:
    vg = crush.vertex_groups.new(name="Opt_Keep_ImpactZone")
    keep = [v.index for v in crush.data.vertices
            if ((v.co.x) ** 2 + (v.co.y - 0.35) ** 2) ** 0.5 < 1.7 and v.co.z > 1.15]
    vg.add(keep, 1.0, 'REPLACE')
    m = crush.modifiers.new("Opt_Decimate", 'DECIMATE'); m.ratio = CRUSH_RATIO
    m.vertex_group = vg.name; m.vertex_group_factor = 1000.0
    with bpy.context.temp_override(object=crush, active_object=crush, selected_objects=[crush], selected_editable_objects=[crush]):
        bpy.ops.object.modifier_move_to_index(modifier=m.name, index=0)
        bpy.ops.object.modifier_apply(modifier=m.name)
    print("crush verts:", len(crush.data.vertices), "kept zone:", len(keep))
# rekvizit modellari (bir nechta nusxa bir mesh'ni ishlatadi - mesh bir marta soddalashtiriladi)
done = set()
for o in bpy.data.objects:
    if o.type == 'MESH' and o.data.name not in done and len(o.data.vertices) > 8000 and \
            not o.name.startswith(("G63_Body_Crush", "Ground", "Building", "Crane", "City", "Site")) and "_frag_" not in o.name:
        me = o.data; done.add(me.name)
        tmp = bpy.data.objects.new("_dec_tmp", me); S.collection.objects.link(tmp)
        m = tmp.modifiers.new("d", 'DECIMATE'); m.ratio = 0.4
        dg = bpy.context.evaluated_depsgraph_get()
        newme = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
        for u in [x for x in bpy.data.objects if x.data == me and x is not tmp]:
            u.data = newme
        bpy.data.objects.remove(tmp); newme.name = me.name + "_lod"
after = sum(len(m.vertices) for m in bpy.data.meshes if m.users)

# ---- 4) Rigid Body keshini tozalash (ixtiyoriy) - ochilgach "Bake All" bilan qayta hisoblanadi
if FREE_CACHE:
    with bpy.context.temp_override(scene=S, point_cache=S.rigidbody_world.point_cache):
        bpy.ops.ptcache.free_bake()
for o in bpy.data.objects:
    for ps in o.particle_systems:
        with bpy.context.temp_override(scene=S, point_cache=ps.point_cache):
            bpy.ops.ptcache.free_bake()

bpy.data.orphans_purge(do_recursive=True)
S.render.filepath = "//render/frame_"
bpy.ops.wm.save_as_mainfile(filepath=OUT, copy=True, compress=True)
print(f"OPT OK verts {before} -> {after}; cache_freed={FREE_CACHE}; size={os.path.getsize(OUT)/1e6:.1f} MB")

# ---- 5) qayta ochib saqlash: bekor qilingan (orphan) ma'lumotlarni to'liq tozalaydi
bpy.ops.wm.open_mainfile(filepath=OUT)
bpy.data.orphans_purge(do_recursive=True)
bpy.ops.wm.save_mainfile(compress=True)
print(f"FINAL size={os.path.getsize(OUT)/1e6:.1f} MB")
