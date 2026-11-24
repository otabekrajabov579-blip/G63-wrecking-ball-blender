# ------------------------------------------------------------------ zarba: silkinish, uziladigan qismlar, kamera titrashi
# Bu bo'lim build_scene.py ichidan exec qilinadi (rigid body sozlangandan keyin).
prefs_edit = bpy.context.preferences.edit
prefs_edit.keyframe_new_interpolation_type = 'LINEAR'


def ts(f):
    """Rigid Body Speed (time_scale) qiymati f kadrda - TS_KEYS bilan bir xil chiziqli interpolyatsiya."""
    ks = TS_KEYS
    if f <= ks[0][0]:
        return ks[0][1]
    for (f0, v0), (f1, v1) in zip(ks, ks[1:]):
        if f0 <= f <= f1:
            return v0 + (v1 - v0) * (f - f0) / max(1, f1 - f0)
    return ks[-1][1]


TAU = {}
_t = 0.0
for _f in range(IMPACT_F, END + 2):
    TAU[_f] = _t; _t += ts(_f) / FPS        # zarbadan keyingi "fizik vaqt" (slow-mo hisobga olingan)
SHAKE_PIVOT = Vector((0.0, 0.0, 0.45))


def shake(f, k=1.0):
    """Amortizator + kuzov tebranishi: keskin cho'kish, qaytish, old-orqa (pitch) va yon (roll) tebranish, so'nish."""
    if f < IMPACT_F:
        return Matrix.Identity(4)
    t = TAU[f]; e = math.exp; s = math.sin; P2 = 2 * math.pi
    z = -0.17 * e(-3.0 * t) * s(P2 * 1.4 * t) + 0.018 * e(-11 * t) * s(P2 * 11 * t)
    pitch = math.radians(-3.8) * e(-2.6 * t) * s(P2 * 1.2 * t) + math.radians(0.5) * e(-10 * t) * s(P2 * 9 * t + 1)
    roll = math.radians(1.4) * e(-2.8 * t) * s(P2 * 1.7 * t + 0.5) + math.radians(0.3) * e(-10 * t) * s(P2 * 13 * t)
    R = Matrix.Rotation(pitch * k, 4, 'X') @ Matrix.Rotation(roll * k, 4, 'Y')
    return Matrix.Translation((0, 0, z * k)) @ Matrix.Translation(SHAKE_PIVOT) @ R @ Matrix.Translation(-SHAKE_PIVOT)


def key_follow(obj, f_to, k=1.0, lin=None, ang=None):
    """obj ni f_to gacha mashina bilan birga silkitadi; oxirgi kadrda 'turtki' beradi -
    Animated o'chganda Bullet shu tezlikni meros qilib oladi (qism uchib ketadi)."""
    rest = obj.matrix_world.copy()
    f_from = min(IMPACT_F - 1, f_to - 1)
    for f in range(f_from, f_to + 1):
        m = shake(f, k) @ rest
        if f == f_to and (lin is not None or ang is not None):
            dt = ts(f) / FPS
            c = m.translation.copy()
            if ang is not None and ang.length > 0:
                m = Matrix.Translation(c) @ Matrix.Rotation(ang.length * dt, 4, ang.normalized()) @ Matrix.Translation(-c) @ m
            if lin is not None:
                m = Matrix.Translation(lin * dt) @ m
        obj.matrix_world = m
        obj.keyframe_insert("location", frame=f); obj.keyframe_insert("rotation_euler", frame=f)
    obj.matrix_world = rest


def set_layers(obj, layers):
    obj.rigid_body.collision_collections = [i in layers for i in range(20)]


# kolliziya qatlamlari: 0 = shar/oyna/ezilish kolliderlari, 1 = uzilgan qismlar (kuzov ichida tug'ilgani uchun kolliderlarni ko'rmaydi)
set_layers(ground, (0, 1)); set_layers(ball, (0, 1))
for o in props_rb:
    set_layers(o, (0, 1))

SHAKE_END = IMPACT_F + 125
# 1) kuzov va g'ildiraklar silkinadi
for o in (crush_body, static_body):
    key_follow(o, SHAKE_END)
key_follow(wheels_obj, SHAKE_END, k=0.25)
# 2) ezilish kolliderlari kuzov bilan birga harakatlanadi (Animated) - shar ham silkinadi
for c in (col_cabin, col_hood):
    c.rigid_body.kinematic = True
    set_layers(c, (0,))
    key_follow(c, SHAKE_END)
# 3) oyna bo'laklari: sinish to'lqini + mayda "portlash" turtkisi
rng = random.Random(5)
for o in glass_frags:
    rf = IMPACT_F - 1 + int((o.location - IMPACT).length * 1.2)
    d = (o.location - IMPACT); d.z = max(d.z, 0.0)
    v = d.normalized() * rng.uniform(0.4, 1.4) + Vector((0, 0, rng.uniform(0.2, 0.9)))
    w = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1))) * 8
    key_follow(o, rf - 1, lin=v, ang=w)
    o.rigid_body.kinematic = True;  o.keyframe_insert("rigid_body.kinematic", frame=rf - 1)
    o.rigid_body.kinematic = False; o.keyframe_insert("rigid_body.kinematic", frame=rf)
    set_layers(o, (0,))
# 4) uzilib uchadigan qismlar (ko'zgu, faralar, panjara, chiroqlar, zaxira g'ildirak, dvorniklar)
for o, off, kick, mass in detach_parts:
    rb(o, 'ACTIVE', 'CONVEX_HULL', mass=mass, friction=0.6, bounce=0.2, margin=0.01)
    o.rigid_body.linear_damping = 0.1; o.rigid_body.angular_damping = 0.2
    set_layers(o, (1,))
    rf = IMPACT_F + off
    w = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1))) * rng.uniform(4, 9)
    key_follow(o, rf - 1, lin=Vector(kick), ang=w)
    o.rigid_body.kinematic = True;  o.keyframe_insert("rigid_body.kinematic", frame=rf - 1)
    o.rigid_body.kinematic = False; o.keyframe_insert("rigid_body.kinematic", frame=rf)

# 5) butun ramaning bukilishi (GN ichidagi "Impact_Bend" qiymati)
kn = crush_ng.nodes["Impact_Bend"]
for f, v in ((IMPACT_F - 1, 0.0), (IMPACT_F + 1, 0.65), (IMPACT_F + 4, 1.0)):
    kn.outputs[0].default_value = v
    kn.outputs[0].keyframe_insert("default_value", frame=f)
prefs_edit.keyframe_new_interpolation_type = 'BEZIER'
