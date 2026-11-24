"""Bake qilingan sahnadan to'qnashuv parametrlarini o'lchash (hisobot uchun).
    E:\\blendr\\blender.exe -b wrecking_ball_scene.blend --python scripts\\measure_collisions.py -- out.json
"""
import bpy, sys, json, math
import numpy as np

out_path = sys.argv[sys.argv.index("--") + 1]
S = bpy.context.scene
FPS = S.render.fps
rbw = S.rigidbody_world
ball = bpy.data.objects["WreckingBall"]
R = {}

# --- har kadrdagi Speed (time_scale) va fizik vaqt
ts = {}
for f in range(1, S.frame_end + 1):
    S.frame_set(f); ts[f] = rbw.time_scale
IMPACT = 291; RELEASE = 240


def track(objs, f0, f1):
    P = {}
    for f in range(f0, f1 + 1):
        S.frame_set(f)
        P[f] = np.array([list(o.matrix_world.translation) for o in objs])
    return P


def vel(P, f):
    dt = ts[f] / FPS
    return (P[f] - P[f - 1]) / dt


# --- shar
P = track([ball], RELEASE - 1, S.frame_end)
zs = {f: P[f][0][2] for f in P}
v_pre = vel(P, IMPACT)[0]          # zarbagacha bo'lgan oxirgi qadam
v_list = {f: vel(P, f)[0] for f in range(RELEASE + 1, S.frame_end + 1)}
v_post_up = max(v_list[f][2] for f in range(IMPACT + 1, IMPACT + 30))
h_drop = zs[RELEASE] - 2.5
m = ball.rigid_body.mass
t_fall = None
for f in range(RELEASE, IMPACT + 2):
    if zs[f] - 0.55 <= 1.95:
        t_fall = (f - RELEASE) / FPS; break
R["ball"] = {
    "mass": m, "radius": 0.55, "z_release": zs[RELEASE], "drop_height": h_drop,
    "v_theory": math.sqrt(2 * 9.81 * h_drop), "v_pre_measured": float(np.linalg.norm(v_pre)),
    "t_fall_theory": math.sqrt(2 * h_drop / 9.81), "t_fall_measured": t_fall,
    "v_rebound_up": float(v_post_up), "z_rest": float(zs[S.frame_end]),
    "penetration_roof": 1.95 - (min(zs[f] for f in range(IMPACT, IMPACT + 40)) - 0.55),
    "z_track": {f: round(float(zs[f]), 3) for f in range(RELEASE, IMPACT + 40, 3)},
    "speed_track": {f: round(float(np.linalg.norm(v_list[f])), 2) for f in range(RELEASE + 1, IMPACT + 40, 3)},
}
vb = R["ball"]["v_pre_measured"]
R["ball"]["momentum_pre"] = m * vb
R["ball"]["ke_pre_kJ"] = 0.5 * m * vb * vb / 1000
R["ball"]["e_effective"] = v_post_up / vb

# --- shisha bo'laklari
shards = [o for o in bpy.data.objects if "_frag_" in o.name and o.rigid_body]
Ps = track(shards, IMPACT - 3, S.frame_end)
speeds = np.zeros((len(shards),))
for f in range(IMPACT, IMPACT + 120):
    v = np.linalg.norm(vel(Ps, f), axis=1)
    speeds = np.maximum(speeds, v)
start = Ps[IMPACT - 3]; end = Ps[S.frame_end]
disp_xy = np.linalg.norm(end[:, :2] - np.array([0.0, 0.35]), axis=1)
last_v = np.linalg.norm(vel(Ps, S.frame_end), axis=1)
masses = np.array([o.rigid_body.mass for o in shards])
R["shards"] = {
    "count": len(shards), "mass_each": float(masses.mean()),
    "v_max_mean": float(speeds.mean()), "v_max_median": float(np.median(speeds)), "v_max_max": float(speeds.max()),
    "dist_mean": float(disp_xy.mean()), "dist_median": float(np.median(disp_xy)), "dist_max": float(disp_xy.max()),
    "at_rest_pct": float((last_v < 0.05).mean() * 100),
    "on_ground_pct": float((end[:, 2] < 0.15).mean() * 100),
    "inside_car_pct": float(((end[:, 2] > 0.9) & (np.abs(end[:, 0]) < 1.0) & (np.abs(end[:, 1] - 0.35) < 2.3)).mean() * 100),
    "speed_bins": {k: int(((speeds >= a) & (speeds < b)).sum()) for k, (a, b) in
                   {"0-1": (0, 1), "1-3": (1, 3), "3-6": (3, 6), "6-10": (6, 10), ">10": (10, 1e9)}.items()},
    "dist_bins": {k: int(((disp_xy >= a) & (disp_xy < b)).sum()) for k, (a, b) in
                  {"0-1": (0, 1), "1-2": (1, 2), "2-4": (2, 4), "4-6": (4, 6), ">6": (6, 1e9)}.items()},
    "ke_max_total_J": float(0.5 * (masses * speeds ** 2).sum()),
}

# --- uzilib uchgan qismlar
parts = [o for o in bpy.data.objects if o.name.startswith("G63_Part_")]
Pp = track(parts, IMPACT - 1, S.frame_end)
R["parts"] = []
for i, o in enumerate(parts):
    vmax = max(float(np.linalg.norm(vel(Pp, f)[i])) for f in range(IMPACT + 1, IMPACT + 60))
    d = float(np.linalg.norm(Pp[S.frame_end][i][:2] - Pp[IMPACT - 1][i][:2]))
    R["parts"].append({"name": o.name.replace("G63_Part_", ""), "mass": o.rigid_body.mass, "v_max": vmax,
                       "distance": d, "p_max": vmax * o.rigid_body.mass})

# --- zarrachalar (mayda shisha) va uchqunlar
def psys_stats(objname, frames):
    o = bpy.data.objects[objname]; res = {}
    for f in frames:
        S.frame_set(f)
        ev = o.evaluated_get(bpy.context.evaluated_depsgraph_get())
        ps = ev.particle_systems[0]
        alive = [p for p in ps.particles if p.alive_state == 'ALIVE']
        if not alive:
            res[f] = {"alive": 0}; continue
        loc = np.array([list(p.location) for p in alive]); v = np.array([list(p.velocity) for p in alive])
        sp = np.linalg.norm(v, axis=1)
        r = np.linalg.norm(loc[:, :2] - np.array([0.0, 0.35]), axis=1)
        res[f] = {"alive": len(alive), "v_mean": float(sp.mean()), "v_max": float(sp.max()),
                  "r_mean": float(r.mean()), "r_max": float(r.max()),
                  "on_ground_pct": float((loc[:, 2] < 0.05).mean() * 100),
                  "on_collider_pct": float(((loc[:, 2] > 1.0) & (loc[:, 2] < 1.3)).mean() * 100),
                  "resting_pct": float((sp < 0.05).mean() * 100)}
    return res


R["chips"] = psys_stats("FX_GlassChip_Emitter", [IMPACT + 3, IMPACT + 15, IMPACT + 60, 450, S.frame_end])
R["sparks"] = psys_stats("FX_Spark_Emitter", [RELEASE + 1, RELEASE + 5, RELEASE + 10])
st = bpy.data.objects["FX_GlassChip_Emitter"].particle_systems[0].settings
R["chips_settings"] = {"count": st.count, "size": st.particle_size, "normal": st.normal_factor, "random": st.factor_random}
g = bpy.data.objects["Ground_Physics"]
R["collision_settings"] = {"damping": g.collision.damping_factor, "friction": g.collision.friction_factor}
R["world"] = {"substeps": rbw.substeps_per_frame, "iterations": rbw.solver_iterations,
              "ts_impact": ts[IMPACT + 5], "ts_late": ts[400]}
json.dump(R, open(out_path, "w"), indent=1, default=float)
print("MEASURE OK", out_path)
