"""Blend fayldagi eski sintez tovushlarni yakuniy BBC miksi bilan almashtiradi (geometriya/teksturaga tegmaydi).
    E:\\blendr\\blender.exe -b wrecking_ball_scene.blend --python scripts\\update_blend_audio.py -- OUT.blend
"""
import bpy, os, sys

OUT = sys.argv[sys.argv.index("--") + 1]
S = bpy.context.scene
root = bpy.path.abspath("//")
se = S.sequence_editor
strips = se.strips if hasattr(se, "strips") else se.sequences
for st in list(strips):
    if st.type == 'SOUND':
        strips.remove(st)
for snd in list(bpy.data.sounds):
    if snd.users == 0:
        bpy.data.sounds.remove(snd)
st = strips.new_sound("Final_Mix_BBC", os.path.join(root, "assets", "sounds", "final_mix.wav"), 1, 1)
st.volume = 1.0
S.render.use_sequencer = True
bpy.ops.wm.save_mainfile()                     # loyiha faylining o'zida ham yangi ovoz
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=OUT, copy=True, compress=True)
print("AUDIO OK", [s.name for s in bpy.data.sounds], "baked:", S.rigidbody_world.point_cache.is_baked,
      f"{os.path.getsize(OUT) / 1e6:.1f} MB")
