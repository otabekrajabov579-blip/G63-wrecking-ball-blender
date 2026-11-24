"""PNG kadrlar + tovushlar -> MP4 (H.264 + AAC).
Ishga tushirish (loyiha papkasidan):
    E:\\blendr\\blender.exe -b wrecking_ball_scene.blend --python scripts\\make_video.py
"""
import bpy, os, glob

scene = bpy.context.scene
root = bpy.path.abspath("//")
frames = sorted(glob.glob(os.path.join(root, "render", "frame_*.png")))
assert frames, "render/ papkasida kadrlar yo'q"
print("frames:", len(frames))

se = scene.sequence_editor
strips = se.strips if hasattr(se, "strips") else se.sequences
im = strips.new_image("Rendered_Frames", frames[0], 7, 1)
for fp in frames[1:]:
    im.elements.append(os.path.basename(fp))
scene.frame_start, scene.frame_end = 1, len(frames)
scene.render.use_sequencer = True

s = scene.render.image_settings
try:
    s.media_type = 'VIDEO'
except Exception:
    pass
s.file_format = 'FFMPEG'
ff = scene.render.ffmpeg
ff.format = 'MPEG4'; ff.codec = 'H264'; ff.constant_rate_factor = 'HIGH'; ff.ffmpeg_preset = 'GOOD'
ff.audio_codec = 'AAC'; ff.audio_bitrate = 192; ff.audio_channels = 'STEREO'
scene.render.filepath = os.path.join(root, "render", "G63_WreckingBall.mp4")
scene.render.use_file_extension = False
bpy.ops.render.render(animation=True)
print("VIDEO:", scene.render.filepath)
