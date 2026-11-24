# ------------------------------------------------------------------ zarrachalar: tros uzilishidagi uchqunlar + mayda shisha zarralari
# impact_shake_section.py dan keyin exec qilinadi (ts(), TS_KEYS, glass_src, col_cabin... mavjud)


def particle_obj(name, mesh_mat, radius, deform=(1, 1, 1), subdiv=1):
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=radius)
    for v in bm.verts:
        v.co.x *= deform[0]; v.co.y *= deform[1]; v.co.z *= deform[2]
    o = new_obj(name, bm, C_FRAC, [mesh_mat], loc=(0, 0, -100))   # yer ostida - o'zi ko'rinmaydi
    return o


def add_particles(emitter, name, inst, count, f0, f1, life, size, size_rand, normal, rand, zvel=0.0, ang=10.0):
    mod = emitter.modifiers.new(name, 'PARTICLE_SYSTEM')
    ps = emitter.particle_systems[-1]; st = ps.settings; st.name = name
    st.count = count; st.frame_start = f0; st.frame_end = f1
    st.lifetime = life; st.lifetime_random = 0.4
    st.emit_from = 'FACE'; st.use_emit_random = True
    st.normal_factor = normal; st.factor_random = rand; st.object_align_factor = (0, 0, zvel)
    st.physics_type = 'NEWTON'; st.mass = 0.01
    st.render_type = 'OBJECT'; st.instance_object = inst
    st.particle_size = size; st.size_random = size_rand
    st.use_rotations = True; st.rotation_mode = 'NONE'; st.rotation_factor_random = 1.0
    st.angular_velocity_mode = 'RAND'; st.angular_velocity_factor = ang
    ps.point_cache.frame_start = 1; ps.point_cache.frame_end = END
    for f, v in TS_KEYS:            # slow-mo bilan bir xil vaqt oqimi
        st.time_tweak = v; st.keyframe_insert("time_tweak", frame=f)
    emitter.show_instancer_for_render = False
    return st


# zarrachalar yer va ezilish kolliderlariga urilib to'xtaydi
for o in (ground, col_cabin, col_hood):
    o.modifiers.new("Collision", 'COLLISION')
    o.collision.damping_factor = 0.6; o.collision.friction_factor = 0.6; o.collision.damping_random = 0.2

# 1) tros uzilishi - uchqunlar
M_SPARK = principled("Spark_Hot", (1.0, 0.5, 0.1), 0.0, 0.5, **{"Emission Color": (1.0, 0.45, 0.08, 1), "Emission Strength": 60.0})
spark = particle_obj("FX_Spark_Instance", M_SPARK, 1.0, (1, 1, 2.5), 0)
bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=1, radius=0.08)
hook_z = PIVOT.z - (L_CENTER - BALL_R - 0.125)
spark_em = new_obj("FX_Spark_Emitter", bm, C_CRANE, [M_SPARK], loc=(PIVOT.x, PIVOT.y, hook_z))
add_particles(spark_em, "Sparks", spark, 160, RELEASE_F, RELEASE_F + 2, 14, 0.012, 0.6, 3.0, 4.5, zvel=1.0, ang=0)

# 2) mayda shisha zarralari (oynalar sinishi bilan birga otiladi)
chip = particle_obj("FX_GlassChip_Instance", M_GLASS, 1.0, (1.0, 0.65, 0.3), 1)
em_objs = []
for g in glass_src:
    c = g.copy(); c.data = g.data.copy(); C_FRAC.objects.link(c); em_objs.append(c)
chip_em = em_objs[0]
with bpy.context.temp_override(active_object=chip_em, object=chip_em, selected_objects=em_objs, selected_editable_objects=em_objs):
    bpy.ops.object.join()
chip_em.name = "FX_GlassChip_Emitter"
chip_em.hide_viewport = False; chip_em.hide_render = False
add_particles(chip_em, "GlassChips", chip, 6500, IMPACT_F - 1, IMPACT_F + 4, 5000, 0.006, 0.85, 0.7, 2.2, zvel=0.6, ang=18)
print("FX: sparks + glass chips ready")
