# ------------------------------------------------------------------ kamera yo'li (bake'dan keyin, shar trayektoriyasi bo'yicha)
# 1)   1-132  : mashina atrofida 360 daraja aylanish (butun G63)
# 2) 132-204  : kamera tik yuqoriga - kran va ilgakdagi sharga ko'tariladi
# 3) 204-240  : shar ilgakda osilib turadi, 240-kadrda uziladi
# 4) 240-291  : kamera shar bilan birga tushadi (shar ham, pastdagi mashina ham kadrda)
# 5) 291-600  : zarba + slow-mo parchalanish, mashina atrofida aylanish
# 6) 600-648  : uzoqlashib umumiy reja
ballpos = {f: p.copy() for f, p in pts}
C = Vector((PIVOT.x, PIVOT.y, 1.3))
OFF = Vector((-5.5, -7.0, 0.0))
B0 = Vector((PIVOT.x, PIVOT.y, BALL_Z))
ORBIT1_END, RISE_END = 132, 204
edit = bpy.context.preferences.edit
fl = target.constraints["Follow_Ball"]


def key(f, loc, lens):
    cam.location = loc; cam.keyframe_insert("location", frame=f)
    cam_d.lens = lens; cam_d.keyframe_insert("lens", frame=f)


def look(f, w):
    fl.influence = w; target.keyframe_insert('constraints["Follow_Ball"].influence', frame=f)


def sstep(u):
    u = min(max(u, 0.0), 1.0); return u * u * (3 - 2 * u)


def aim_w(campos, b, lens):
    """Follow_Ball ta'siri: shar kadrning yuqori qismida qoladi, mashina sig'sa - pastdan kadrga kiradi."""
    if b.z - C.z < 0.3:
        return 1.0
    d = (b.xy - campos.xy).length
    half = math.atan((36 * 9 / 16) / 2 / lens)
    a_b = math.atan2(b.z - campos.z, d); a_c = math.atan2(C.z - campos.z, d)
    a = max((a_b + a_c) / 2, a_b - 0.6 * half)
    z_aim = campos.z + d * math.tan(a)
    return min(1.0, max(0.0, (z_aim - C.z) / (b.z - C.z)))


edit.keyframe_new_interpolation_type = 'LINEAR'
# 1) mashina atrofida aylanish - oxirida OFF yo'nalishiga keladi
R1, H1 = OFF.xy.length, 1.5
a_end = math.atan2(OFF.y, OFF.x)
for f in range(1, ORBIT1_END + 1, 3):
    u = sstep((f - 1) / (ORBIT1_END - 1))
    a = a_end - 2 * math.pi * (1 - u)
    key(f, C + Vector((math.cos(a) * R1, math.sin(a) * R1, H1)), 28)
look(1, 0.0); look(ORBIT1_END, 0.0)
# 2) tik yuqoriga ko'tarilish (kamera mashinadan sharga qaraydi)
z0, z1 = C.z + H1, B0.z + 1.5
for f in range(ORBIT1_END + 3, RISE_END + 1, 3):
    u = sstep((f - ORBIT1_END) / (RISE_END - ORBIT1_END))
    p = Vector((C.x + OFF.x, C.y + OFF.y, z0 + (z1 - z0) * u))
    lens = 28 - 6 * u
    key(f, p, lens)
    # avval mashinaga, so'ng asta sharga qarab ko'tariladi
    look(f, aim_w(p, B0, lens) * sstep((f - ORBIT1_END) / 30))
# 3) ilgakdagi shar - biroz yaqinlashish
key(RELEASE_F - 1, B0 + OFF * 0.9 + Vector((0, 0, 1.5)), 22)
look(RELEASE_F - 1, 1.0)
# 4) tushish: kamera shar bilan birga, oxirida yumshoq to'xtaydi; shar va mashina orasiga qaraydi
for f in range(RELEASE_F, IMPACT_F + 1, 2):
    b = ballpos[f]
    zz = b.z + 1.5
    z = 3.0 + 0.8 * math.log1p(math.exp((zz - 3.0) / 0.8))
    u = (f - RELEASE_F) / (IMPACT_F - RELEASE_F)
    o = OFF * (0.9 + 0.1 * u)
    p = Vector((b.x + o.x, b.y + o.y, z)); lens = 20 + 4 * sstep(u)
    # uzilish lahzasi ko'rinishi uchun kamera ~10 kadr ushlanib turadi, keyin shar ortidan tushadi
    kk = sstep((f - RELEASE_F) / 10)
    hold = B0 + OFF * 0.9 + Vector((0, 0, 1.5))
    p = hold.lerp(p, kk); lens = 22 + (lens - 22) * kk
    key(f, p, lens)
    look(f, 1.0 + (aim_w(p, b, lens) - 1.0) * kk)
look(IMPACT_F + 10, 1.0); look(IMPACT_F + 45, 0.0); look(END, 0.0)
# 5) parchalanish: mashina atrofida aylanish va yaqinlashish
start = cam.location.copy()
v = start - C
r0 = v.xy.length; a0 = math.atan2(v.y, v.x); h0 = v.z
ORBIT_END = 600
for f in range(IMPACT_F + 4, ORBIT_END + 1, 6):
    u = sstep((f - IMPACT_F) / (ORBIT_END - IMPACT_F))
    a = a0 + math.radians(150) * u
    r = r0 + (6.4 - r0) * u
    h = h0 + (1.0 - h0) * u
    key(f, C + Vector((math.cos(a) * r, math.sin(a) * r, h)), 24 + 6 * u)
# 6) umumiy reja
edit.keyframe_new_interpolation_type = 'BEZIER'
end_dir = (cam.location - C); end_dir.z = 0; end_dir.normalize()
key(END, C + end_dir * 26 + Vector((0, 0, 8.0)), 24)
scene.frame_set(1)
print("camera keys done; impact cam =", tuple(round(x, 2) for x in start))
