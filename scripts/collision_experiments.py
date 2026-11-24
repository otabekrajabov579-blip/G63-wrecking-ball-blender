"""To'qnashuv parametrlari tajribalari (hisobotning tahlil bo'limi uchun).
    E:\\blendr\\blender.exe -b --factory-startup --python scripts\\collision_experiments.py -- out.json
A) Tiklanish koeffitsiyenti (Bounciness) -> sharning qaytish tezligi va balandligi
B) Bo'lak massasi -> to'qnashuvdan keyingi bo'lak tezligi va sochilish masofasi
C) Shar massasi -> shar tezligining yo'qotilishi (impuls uzatilishi)
D) Collision damping -> zarrachalarning qaytish balandligi
"""
import bpy, bmesh, sys, json, math
import numpy as np
from mathutils import Vector

out_path = sys.argv[sys.argv.index("--") + 1]
FPS = 24


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene; s.render.fps = FPS; s.frame_start = 1; s.frame_end = 250
    bpy.ops.rigidbody.world_add()
    w = s.rigidbody_world; w.substeps_per_frame = 20; w.solver_iterations = 20
    w.point_cache.frame_end = 250; w.collection = bpy.data.collections.new("RBW")
    return s


def box(name, loc, size):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= size[0]; v.co.y *= size[1]; v.co.z *= size[2]
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); o.location = loc; bpy.context.scene.collection.objects.link(o); return o


def sphere(name, loc, r):
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=r)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); o.location = loc; bpy.context.scene.collection.objects.link(o); return o


def rb(o, kind, shape, mass=1.0, e=0.0, fr=0.5, margin=0.004):
    with bpy.context.temp_override(object=o, active_object=o, selected_objects=[o]):
        bpy.ops.rigidbody.object_add(type=kind)
    r = o.rigid_body; r.collision_shape = shape; r.mass = mass; r.restitution = e; r.friction = fr
    r.use_margin = True; r.collision_margin = margin; r.linear_damping = 0.0; r.angular_damping = 0.1
    return r


def run(s, objs, f1):
    P = {}
    for f in range(1, f1 + 1):
        s.frame_set(f); P[f] = np.array([list(o.matrix_world.translation) for o in objs])
    return P


R = {}
# ---------------- A) tiklanish koeffitsiyenti
R["A"] = []
for e in (0.0, 0.22, 0.5, 0.8):
    s = reset()
    g = box("G", (0, 0, -0.5), (40, 40, 1)); rb(g, 'PASSIVE', 'BOX', e=1.0, margin=0.0)
    b = sphere("B", (0, 0, 25.0), 0.55); rb(b, 'ACTIVE', 'SPHERE', mass=1000, e=e)
    P = run(s, [b], 160)
    z = np.array([P[f][0][2] for f in range(1, 161)])
    h0 = 25.0 - 0.55
    c = int(np.argmin(z[:75]))                                    # birinchi tegish (eng past nuqta)
    v_in = math.sqrt(2 * 9.81 * h0)
    h_up = max(float(z[c:c + 100].max() - 0.55), 0.0)
    e_m = math.sqrt(h_up / h0)
    R["A"].append({"e": e, "contact_frame": c + 1, "v_in": v_in, "v_out": e_m * v_in, "h_rebound": h_up,
                   "e_measured": e_m, "ke_loss_pct": (1 - e_m ** 2) * 100})


# ---------------- B/C) bo'laklar qatlami: shar 21 m/s tezlikda "oyna" qatlamini yorib o'tadi
def shard_test(shard_mass, ball_mass):
    """Shar 21 m/s tezlik bilan (kinematic -> dynamic, tezlik meros) 10x10 bo'lak qatlamini yorib o'tadi.
    Aniq o'lchash uchun zarba atrofida vaqt 10 marta sekinlashtiriladi (time_scale = 0.1)."""
    s = reset(); s.frame_end = 400
    w = s.rigidbody_world; w.point_cache.frame_end = 400
    bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
    for f, v in ((1, 0.1), (90, 0.1), (110, 1.0), (400, 1.0)):
        w.time_scale = v; s.keyframe_insert("rigidbody_world.time_scale", frame=f)
    g = box("G", (0, 0, -0.5), (60, 60, 1)); rb(g, 'PASSIVE', 'BOX', e=0.3, margin=0.0)
    V0, dz = 21.0, 21.0 * 0.1 / FPS                    # 1 kadrda 0.0875 m
    b = sphere("B", (0, 0, 6.0), 0.55); r = rb(b, 'ACTIVE', 'SPHERE', mass=ball_mass, e=0.2)
    for f in (1, 20):
        b.location = (0, 0, 6.0 - dz * (f - 1)); b.keyframe_insert("location", frame=f)
    r.kinematic = True; b.keyframe_insert("rigid_body.kinematic", frame=19)
    r.kinematic = False; b.keyframe_insert("rigid_body.kinematic", frame=20)
    sh = []
    n = 10; a = 0.16
    for i in range(n):
        for j in range(n):
            o = box(f"S{i}_{j}", ((i - n / 2 + 0.5) * a, (j - n / 2 + 0.5) * a, 2.0), (a * 0.98, a * 0.98, 0.02))
            rr = rb(o, 'ACTIVE', 'BOX', mass=shard_mass, e=0.15, fr=0.5, margin=0.002)
            rr.linear_damping = 0.05
            rr.kinematic = True; o.keyframe_insert("rigid_body.kinematic", frame=36)
            rr.kinematic = False; o.keyframe_insert("rigid_body.kinematic", frame=37)
            sh.append(o)
    ts = {}
    P = {}
    for f in range(1, 401):
        s.frame_set(f); ts[f] = w.time_scale
        P[f] = np.array([list(o.matrix_world.translation) for o in [b] + sh])

    def vz(f):
        return -(P[f][0][2] - P[f - 1][0][2]) / (ts[f] / FPS)
    k = next(f for f in range(2, 400) if P[f][0][2] - 0.55 <= 2.01)
    v_before = float(np.mean([vz(f) for f in range(k - 4, k - 1)]))
    after = [f for f in range(k + 8, k + 20) if P[f][0][2] - 0.55 > 0.15]
    v_after_raw = float(np.mean([vz(f) for f in after]))
    # o'lchash oraliqlari orasida gravitatsiya qo'shgan tezlikni ayirish: dv = g * dt
    t_b = np.mean([sum(ts[x] for x in range(2, f + 1)) / FPS for f in range(k - 4, k - 1)])
    t_a = np.mean([sum(ts[x] for x in range(2, f + 1)) / FPS for f in after])
    v_after = v_after_raw - 9.81 * (t_a - t_b)
    sp = np.zeros(len(sh))
    for f in range(k, k + 60):
        d = np.linalg.norm(P[f + 1][1:] - P[f][1:], axis=1) / (ts[f + 1] / FPS)
        sp = np.maximum(sp, d)
    dist = np.linalg.norm(P[400][1:, :2], axis=1)
    p_ball = ball_mass * (v_before - v_after); p_sh = float(shard_mass * len(sh) * sp.mean())
    return {"shard_mass": shard_mass, "ball_mass": ball_mass, "v_ball_before": v_before, "v_ball_after": v_after,
            "ball_speed_loss_pct": (1 - v_after / v_before) * 100, "shard_vmax_mean": float(sp.mean()),
            "shard_vmax_max": float(sp.max()), "shard_dist_mean": float(dist.mean()), "shard_dist_max": float(dist.max()),
            "dp_ball": p_ball, "p_shards_total": p_sh}


R["B"] = [shard_test(m, 1000) for m in (0.1, 0.25, 1.0, 5.0)]
R["C"] = [shard_test(0.25, M) for M in (20, 100, 1000, 5000)]

# ---------------- D) zarrachalar: collision damping
R["D"] = []
for damp in (0.0, 0.3, 0.6, 0.9):
    s = reset()
    g = box("G", (0, 0, -0.5), (20, 20, 1)); g.modifiers.new("C", 'COLLISION')
    g.collision.damping_factor = damp; g.collision.friction_factor = 0.6
    em = box("E", (0, 0, 2.0), (1, 1, 0.01))
    em.modifiers.new("P", 'PARTICLE_SYSTEM'); st = em.particle_systems[0].settings
    st.count = 400; st.frame_start = 1; st.frame_end = 2; st.lifetime = 300
    st.normal_factor = 0.0; st.factor_random = 0.0; st.physics_type = 'NEWTON'; st.particle_size = 0.01
    em.particle_systems[0].point_cache.frame_end = 250
    zmax_after = None; z_hist = []
    for f in range(1, 120):
        s.frame_set(f)
        ev = em.evaluated_get(bpy.context.evaluated_depsgraph_get()); ps = ev.particle_systems[0]
        z = np.array([p.location.z for p in ps.particles if p.alive_state == 'ALIVE'])
        vz = np.array([p.velocity.z for p in ps.particles if p.alive_state == 'ALIVE'])
        z_hist.append((float(z.mean()) if len(z) else 2.0, float(np.abs(vz).mean()) if len(vz) else 0.0))
    zs = np.array([h[0] for h in z_hist])
    i_hit = int(np.argmin(zs[:40]))
    reb = float(zs[i_hit:].max() - zs[i_hit])
    rest = next((i + 1 for i in range(i_hit, len(z_hist)) if z_hist[i][1] < 0.02), None)
    R["D"].append({"damping": damp, "rebound_height": reb, "e_equiv": math.sqrt(max(reb, 0) / 2.0),
                   "frames_to_rest": rest})

json.dump(R, open(out_path, "w"), indent=1)
print("EXPERIMENTS OK")
