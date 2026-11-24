# ------------------------------------------------------------------ realistik qurilish maydoni (build_scene.py ichidan exec qilinadi)
from mathutils import noise as mnoise
rnd = random.Random(21)

M_BRICK = pbr_box("Brick_Red", "red_brick_03", scale=0.45)
M_PLYWOOD = pbr_box("Formwork_Plywood", "plywood", scale=0.5)
M_CORR = pbr_box("Fence_CorrugatedIron", "corrugated_iron_02", scale=0.5)
M_CONT = pbr_box("SiteOffice_Container", "container_side", scale=0.35)
M_PLANKS = pbr_box("Scaffold_Planks", "worn_planks", scale=0.6)
M_SLAB = pbr_box("Slab_Concrete", "concrete_floor_damaged_01", scale=0.25)
M_FACADE = pbr_box("City_Facade", "concrete_tile_facade", scale=0.12)
M_SCAFF = principled("Scaffold_Galvanized", (0.55, 0.56, 0.58), 0.9, 0.45)
M_WINDOW = principled("Window_DarkGlass", (0.02, 0.03, 0.035), 0.0, 0.05, **{"Specular IOR Level": 0.8})
M_NET = principled("Safety_Net_Green", (0.05, 0.35, 0.12), 0.0, 0.8, **{"Alpha": 0.55})
try:
    M_NET.surface_render_method = 'DITHERED'
except Exception:
    pass
M_PALLET = principled("Pallet_Wood", (0.45, 0.32, 0.18), 0.0, 0.85)
M_ORANGE = principled("Safety_Orange", (0.9, 0.25, 0.02), 0.0, 0.5)


# --- zamin materiali: shag'al-beton + quruq loy aralashmasi, ko'lmaklar
def ground_material():
    m = bpy.data.materials.new("Ground_Mud_Gravel_Puddles"); m.use_nodes = True
    N = m.node_tree.nodes; L = m.node_tree.links; b = N["Principled BSDF"]
    tc = N.new("ShaderNodeTexCoord")

    def texset(folder, scale):
        mp = N.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (scale,) * 3
        L.new(tc.outputs["Object"], mp.inputs["Vector"])
        out = {}
        for kind, cs in (("diff", "sRGB"), ("rough", "Non-Color"), ("nor_gl", "Non-Color")):
            t = N.new("ShaderNodeTexImage")
            t.image = img(os.path.join(A, "textures", folder, f"{folder}_{kind}_2k.jpg"), cs)
            L.new(mp.outputs["Vector"], t.inputs["Vector"]); out[kind] = t.outputs["Color"]
        return out
    g = texset("gravel_concrete", 0.25); d = texset("brown_mud_dry", 0.18)
    nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.035; nz.inputs["Detail"].default_value = 6
    L.new(tc.outputs["Object"], nz.inputs["Vector"])
    mask = N.new("ShaderNodeMapRange"); L.new(nz.outputs["Fac"], mask.inputs["Value"])
    mask.inputs["From Min"].default_value = 0.45; mask.inputs["From Max"].default_value = 0.6
    pud_n = N.new("ShaderNodeTexNoise"); pud_n.inputs["Scale"].default_value = 0.09; pud_n.inputs["Detail"].default_value = 3
    L.new(tc.outputs["Object"], pud_n.inputs["Vector"])
    pud = N.new("ShaderNodeMapRange"); L.new(pud_n.outputs["Fac"], pud.inputs["Value"])
    pud.inputs["From Min"].default_value = 0.63; pud.inputs["From Max"].default_value = 0.68

    def mix(kind, a, bb, fac, dtype='RGBA'):
        n = N.new("ShaderNodeMix"); n.data_type = dtype
        L.new(fac, n.inputs[0]); L.new(a, n.inputs[6]); L.new(bb, n.inputs[7]); return n.outputs[2]
    col = mix("c", g["diff"], d["diff"], mask.outputs["Result"])
    rough = mix("r", g["rough"], d["rough"], mask.outputs["Result"])
    nor = mix("n", g["nor_gl"], d["nor_gl"], mask.outputs["Result"])
    # ko'lmak: qorong'iroq, silliq, normal tekis
    dark = N.new("ShaderNodeMix"); dark.data_type = 'RGBA'; dark.blend_type = 'MULTIPLY'
    dark.inputs[0].default_value = 1.0; L.new(col, dark.inputs[6]); dark.inputs[7].default_value = (0.35, 0.33, 0.3, 1)
    col2 = mix("c2", col, dark.outputs[2], pud.outputs["Result"])
    r_p = N.new("ShaderNodeMix"); r_p.data_type = 'FLOAT'; L.new(pud.outputs["Result"], r_p.inputs[0])
    sep = N.new("ShaderNodeSeparateColor"); L.new(rough, sep.inputs[0])
    L.new(sep.outputs[0], r_p.inputs[2]); r_p.inputs[3].default_value = 0.04
    nm = N.new("ShaderNodeNormalMap"); L.new(nor, nm.inputs["Color"])
    st = N.new("ShaderNodeMath"); st.operation = 'SUBTRACT'; st.inputs[0].default_value = 1.0
    L.new(pud.outputs["Result"], st.inputs[1]); L.new(st.outputs[0], nm.inputs["Strength"])
    L.new(col2, b.inputs["Base Color"]); L.new(r_p.outputs[0], b.inputs["Roughness"]); L.new(nm.outputs["Normal"], b.inputs["Normal"])
    return m


M_GROUND2 = ground_material()

# --- fizik zamin (yashirin quti) + ko'rinadigan notekis zamin
bm = bmesh.new(); add_box(bm, (0, 0, -0.5), (300, 300, 1.0))
ground = new_obj("Ground_Physics", bm, C_ENV, [M_GROUND])
ground.hide_render = True; ground.display_type = 'WIRE'
bm = bmesh.new()
bmesh.ops.create_grid(bm, x_segments=160, y_segments=160, size=1.0)
_s = 150.0 / max(v.co.x for v in bm.verts)
for v in bm.verts:
    v.co.x *= _s; v.co.y *= _s
    r = v.co.xy.length
    amp = 0.0 if r < 14 else min(1.0, (r - 14) / 20) * 0.28
    v.co.z = amp * mnoise.noise(Vector((v.co.x * 0.06, v.co.y * 0.06, 0.5))) + amp * 0.4 * mnoise.noise(Vector((v.co.x * 0.25, v.co.y * 0.25, 2.0)))
ground_vis = new_obj("Ground", bm, C_ENV, [M_GROUND2], smooth=True)


# --- shag'al / qum uyumlari
def mound(name, loc, radius, height, mat):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=40, v_segments=20, radius=1.0)
    for v in bm.verts:
        if v.co.z < 0:
            v.co.z = 0
        n = 1 + 0.18 * mnoise.noise(v.co * 2.5)
        v.co.x *= radius * n; v.co.y *= radius * n; v.co.z *= height * n
    new_obj(name, bm, C_ENV, [mat], smooth=True, loc=loc)


mound("Pile_Gravel_A", (16, -9, -0.05), 3.2, 1.6, M_GROUND)
mound("Pile_Gravel_B", (19.5, -6, -0.05), 2.2, 1.1, M_GROUND)
mound("Pile_Sand", (-17, 12, -0.05), 3.0, 1.4, pbr_box("Sand_Mud", "brown_mud_dry", scale=0.3))


# --- binolar: beton karkas + g'isht devorlar (derazali), tepada opalubka/armatura, fasadda iskala va to'r
def building2(name, origin, nx, ny, floors, done, bay=6.0, fh=3.2, scaffold=False, net=False, face_dir=-1):
    ox, oy = origin
    W, D = nx * bay, ny * bay
    x0, y0 = ox - W / 2, oy - D / 2
    bmc, bms, bmb, bmw, bmp, bmr = (bmesh.new() for _ in range(6))   # kolonna, plita, g'isht, oyna, opalubka, armatura
    for f in range(floors + 1):
        z = f * fh
        if 0 < f <= done:
            add_box(bms, (ox, oy, z - 0.12), (W + 0.6, D + 0.6, 0.25))
        elif f == done + 1 and f <= floors:     # qisman quyilgan plita + fanera taxtasi
            add_box(bmp, (ox - W * 0.2, oy, z - 0.1), (W * 0.6, D, 0.04))
        if f >= floors:
            continue
        for i in range(nx + 1):
            for j in range(ny + 1):
                x = x0 + i * bay; y = y0 + j * bay
                if f < done:
                    add_box(bmc, (x, y, z + fh / 2), (0.45, 0.45, fh))
                else:
                    if rnd.random() < 0.3:
                        continue
                    h = fh * rnd.choice((0.45, 0.7, 1.0))
                    if rnd.random() < 0.45:     # kolonna atrofida opalubka qutisi
                        add_box(bmp, (x, y, z + fh / 2), (0.62, 0.62, fh))
                    else:
                        add_box(bmc, (x, y, z + h / 2), (0.45, 0.45, h))
                    for dx in (-0.13, 0.13):
                        for dy in (-0.13, 0.13):
                            add_beam(bmr, (x + dx, y + dy, z + h), (x + dx + rnd.uniform(-0.05, 0.05), y + dy, z + h + rnd.uniform(0.8, 1.4)), 0.025)
        # g'isht devorlar derazalar bilan (pastki qavatlar to'liq, keyingisi qisman)
        if f < done - 1 or (f == done - 1 and rnd.random() < 0.6):
            partial = f >= done - 2
            for side in range(4):
                n_b = nx if side < 2 else ny
                for k in range(n_b):
                    if partial and rnd.random() < 0.5:
                        continue
                    if side < 2:
                        yy = y0 if side == 0 else y0 + D
                        a = Vector((x0 + k * bay, yy, z)); dirv = Vector((1, 0, 0)); th = Vector((0, 0.25, 0))
                    else:
                        xx = x0 if side == 2 else x0 + W
                        a = Vector((xx, y0 + k * bay, z)); dirv = Vector((0, 1, 0)); th = Vector((0.25, 0, 0))
                    ww = bay - 0.45; s0 = a + dirv * 0.225
                    hw = fh - 0.25

                    def seg(u0, u1, z0, z1, mat_bm=bmb):
                        c = s0 + dirv * ((u0 + u1) / 2) + Vector((0, 0, (z0 + z1) / 2))
                        size = dirv * (u1 - u0) + th + Vector((0, 0, z1 - z0))
                        add_box(mat_bm, c, (max(abs(size.x), 0.02), max(abs(size.y), 0.02), size.z))
                    seg(0, ww, 0, 0.9)                       # deraza osti
                    seg(0, ww, hw - 0.5, hw)                 # deraza usti
                    for u0, u1 in ((0, 0.55), (ww / 2 - 0.4, ww / 2 + 0.4), (ww - 0.55, ww)):
                        seg(u0, u1, 0.9, hw - 0.5)          # devor ustunlari
                    if f < 2 and rnd.random() < 0.6:          # pastki qavatlarda oynalar o'rnatilgan
                        for u0, u1 in ((0.55, ww / 2 - 0.4), (ww / 2 + 0.4, ww - 0.55)):
                            c = s0 + dirv * ((u0 + u1) / 2) + Vector((0, 0, (0.9 + hw - 0.5) / 2))
                            sz = dirv * (u1 - u0) + Vector((0, 0, hw - 1.4)) + th * 0.1
                            add_box(bmw, c, (max(abs(sz.x), 0.02), max(abs(sz.y), 0.02), sz.z))
    for bm_, suf, mat in ((bmc, "_Frame", M_CONCRETE), (bms, "_Slabs", M_SLAB), (bmb, "_BrickWalls", M_BRICK),
                          (bmw, "_Windows", M_WINDOW), (bmp, "_Formwork", M_PLYWOOD), (bmr, "_Rebar", M_REBAR)):
        if bm_.verts:
            new_obj(name + suf, bm_, C_BLD, [mat])
        else:
            bm_.free()
    # iskala (lesa) fasad oldida
    if scaffold:
        bp, bk = bmesh.new(), bmesh.new()
        yf = (y0 - 1.3) if face_dir < 0 else (y0 + D + 1.3)
        top = min(floors, done + 1) * fh
        xs = [x0 - 1 + i * 2.0 for i in range(int((W + 2) / 2.0) + 1)]
        for x in xs:
            for dyy in (0.0, -1.1 * face_dir):
                add_beam(bp, (x, yf + dyy, 0), (x, yf + dyy, top + 1.0), 0.05)
        lv = 0.0
        while lv <= top:
            for dyy in (0.0, -1.1 * face_dir):
                add_beam(bp, (xs[0], yf + dyy, lv + 1.0), (xs[-1], yf + dyy, lv + 1.0), 0.045)
            add_box(bk, ((xs[0] + xs[-1]) / 2, yf - 0.55 * face_dir, lv + 0.02), (xs[-1] - xs[0], 1.0, 0.04))
            lv += 2.0
        for i in range(0, len(xs) - 2, 3):
            add_beam(bp, (xs[i], yf, 0), (xs[i + 2], yf, min(top, 8.0)), 0.04)
        new_obj(name + "_Scaffold", bp, C_BLD, [M_SCAFF]); new_obj(name + "_ScaffoldPlanks", bk, C_BLD, [M_PLANKS])
        if net:
            bn = bmesh.new()
            zn0 = top * 0.45
            add_box(bn, ((xs[0] + xs[-1]) / 2, yf + 0.15 * face_dir, (zn0 + top + 1.0) / 2), (xs[-1] - xs[0], 0.01, top + 1.0 - zn0))
            new_obj(name + "_SafetyNet", bn, C_BLD, [M_NET])


building2("Building_A", (-32, 42), 4, 3, 10, 8, scaffold=True, net=True)
building2("Building_B", (6, 55), 5, 3, 13, 10, scaffold=True)
building2("Building_C", (38, 40), 3, 3, 7, 5, scaffold=True, net=True)
building2("Building_D", (-60, 12), 3, 4, 8, 6)
building2("Building_E", (58, 8), 3, 3, 11, 7, scaffold=True)
building2("Building_F", (-12, 85), 6, 3, 15, 12)
building2("Building_G", (-62, -38), 4, 3, 9, 7, scaffold=True, net=True, face_dir=1)
building2("Building_H", (52, -45), 3, 3, 12, 9, face_dir=1)
building2("Building_I", (8, -70), 5, 3, 7, 4, scaffold=True, face_dir=1)

# --- uzoqdagi tayyor shahar binolari (umumiy planlarda gorizontni to'ldiradi)
bm = bmesh.new()
for i in range(26):
    a = i / 26 * 2 * math.pi + rnd.uniform(-0.08, 0.08)
    r = rnd.uniform(140, 210)
    w, d, h = rnd.uniform(14, 30), rnd.uniform(12, 24), rnd.uniform(18, 60)
    add_box(bm, (math.cos(a) * r, math.sin(a) * r, h / 2), (w, d, h))
new_obj("City_Distant_Blocks", bm, C_BLD, [M_FACADE])

# --- maydon to'sig'i (gofrirovka panellar + ustunlar)
bmf, bmfp = bmesh.new(), bmesh.new()
X0, X1, Y0, Y1 = -92, 92, -95, 112
for (ax, ay), (bx, by) in (((X0, Y0), (X1, Y0)), ((X1, Y0), (X1, Y1)), ((X1, Y1), (X0, Y1)), ((X0, Y1), (X0, Y0))):
    Lh = math.hypot(bx - ax, by - ay); n = int(Lh / 2.5)
    for k in range(n):
        t0, t1 = k / n, (k + 1) / n
        if (ax, ay) == (X0, Y0) and 0.45 < t0 < 0.55:      # darvoza ochig'i
            continue
        p0 = Vector((ax + (bx - ax) * t0, ay + (by - ay) * t0, 0)); p1 = Vector((ax + (bx - ax) * t1, ay + (by - ay) * t1, 0))
        c = (p0 + p1) / 2
        add_box(bmf, (c.x, c.y, 1.15), (max(abs(p1.x - p0.x), 0.04), max(abs(p1.y - p0.y), 0.04), 2.2))
        add_beam(bmfp, (p0.x, p0.y, 0), (p0.x, p0.y, 2.35), 0.08)
new_obj("Site_Fence_Panels", bmf, C_ENV, [M_CORR]); new_obj("Site_Fence_Posts", bmfp, C_ENV, [M_SCAFF])

# --- vagon-ofislar (konteynerlar, ikki qavat) va zinapoya
bm = bmesh.new()
for (cx, cy, cz, rz) in ((-26, -20, 0, 0), (-32.5, -20, 0, 0), (-29, -20, 2.65, 0), (24, 18, 0, 1), (24, 24.5, 0, 1)):
    if rz:
        add_box(bm, (cx, cy, cz + 1.3), (2.45, 6.05, 2.6))
    else:
        add_box(bm, (cx, cy, cz + 1.3), (6.05, 2.45, 2.6))
new_obj("Site_Offices", bm, C_ENV, [M_CONT])
bm = bmesh.new()
for (cx, cy, cz) in ((-26, -21.24, 1.4), (-32.5, -21.24, 1.4), (-29, -21.24, 4.05)):
    for dx in (-1.6, 1.6):
        add_box(bm, (cx + dx, cy, cz), (1.0, 0.02, 0.9))
new_obj("Site_Offices_Windows", bm, C_ENV, [M_WINDOW])

# --- g'isht palletlari, armatura bog'lamlari, ogohlantiruvchi konuslar
bmb, bmw_, bmr2, bmo = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
for (px, py) in ((11, -14), (12.4, -14), (11, -15.4), (12.4, -15.4), (-9, 17), (-10.4, 17)):
    add_box(bmw_, (px, py, 0.07), (1.2, 1.2, 0.14))
    add_box(bmb, (px, py, 0.14 + 0.45), (1.1, 1.1, 0.9))
for k in range(28):
    yy = 13 + (k % 7) * 0.06; zz = 0.1 + (k // 7) * 0.06
    add_beam(bmr2, (7, yy, zz), (15, yy, zz), 0.025)
for (px, py) in ((-3.5, -9), (-1.5, -10), (0.6, -10.5), (2.8, -10), (4.7, -9.2)):
    bc = bmesh.ops.create_cone(bmo, cap_ends=True, segments=16, radius1=0.18, radius2=0.03, depth=0.7)
    bmesh.ops.translate(bmo, vec=(px, py, 0.35), verts=bc["verts"])
new_obj("Brick_Pallets", bmb, C_ENV, [M_BRICK]); new_obj("Pallets_Wood", bmw_, C_ENV, [M_PALLET])
new_obj("Rebar_Bundle", bmr2, C_ENV, [M_REBAR]); new_obj("Traffic_Cones", bmo, C_ENV, [M_ORANGE], smooth=True)

# --- havo tumani (chuqurlik hissi)
# (Eevee'da world-volume HDRI va quyoshni yutib yuboradi, shuning uchun tuman - sahnani o'rab turgan kub)
M_HAZE = bpy.data.materials.new("Atmosphere_Haze"); M_HAZE.use_nodes = True
hn = M_HAZE.node_tree.nodes; hn.remove(hn["Principled BSDF"])
vol = hn.new("ShaderNodeVolumePrincipled"); vol.inputs["Density"].default_value = 0.0010
vol.inputs["Color"].default_value = (0.78, 0.82, 0.9, 1)
M_HAZE.node_tree.links.new(vol.outputs[0], hn["Material Output"].inputs["Volume"])
bm = bmesh.new(); add_box(bm, (0, 0, 45), (520, 520, 90))
haze = new_obj("Atmosphere_Haze_Volume", bm, C_ENV, [M_HAZE]); haze.display_type = 'BOUNDS'
