#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""同济足协杯 · 视频片段裁切器

用法:
    python3 clips.py spec.json

spec.json:
  output.clip_dir : 片段输出目录（默认 "视频"）
  clips: [{"n": 1, "src": "录像.mp4", "start": "0:17", "end": "0:24",
           "crop": true}]

crop=true 时会自动检测手机录像的黑边并裁成横向画面，额外输出 视频N_横屏.mp4；
crop=false 只输出原样 视频N.mp4。
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

try:
    from PIL import Image
except ImportError:
    Image = None


def ffmpeg():
    p = shutil.which("ffmpeg")
    if p:
        return p
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        raise SystemExit("找不到 ffmpeg：请 apt install ffmpeg，或 pip install imageio-ffmpeg")


def secs(t):
    if isinstance(t, (int, float)):
        return float(t)
    parts = [float(x) for x in str(t).split(":")]
    v = 0.0
    for p in parts:
        v = v * 60 + p
    return v


def clean(ts):
    return f"{int(ts // 60)}:{ts % 60:04.1f}"


def detect_band(src, t):
    """返回画面真正内容的 (y0, y1)；没有黑边则返回 None。"""
    if Image is None:
        return None
    ff = ffmpeg()
    tmp = os.path.join(tempfile.mkdtemp(), "probe.png")
    subprocess.run([ff, "-hide_banner", "-v", "error", "-ss", str(t), "-i", src,
                    "-frames:v", "1", "-y", tmp], check=True)
    im = Image.open(tmp).convert("L")
    w, h = im.size
    px = im.load()
    rows = [y for y in range(h) if sum(px[x, y] for x in range(0, w, 8)) / (w / 8) > 32]
    if not rows:
        return None
    y0, y1 = min(rows), max(rows)
    if (y1 - y0 + 1) > h * 0.92:
        return None                     # 几乎没有黑边
    if (y1 - y0 + 1) < h * 0.25:
        return None
    if (y1 - y0) % 2 == 0:
        y1 -= 1
    return y0, y1


def cut(ff, src, start, end, out, crop=None):
    dur = max(0.5, end - start)
    cmd = [ff, "-hide_banner", "-v", "error", "-ss", f"{start:.2f}", "-i", src,
           "-t", f"{dur:.2f}"]
    if crop:
        y0, y1 = crop
        cmd += ["-vf", f"crop=iw:{y1 - y0 + 1}:0:{y0}"]
    cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", "-y", out]
    subprocess.run(cmd, check=True)
    return dur


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    with open(sys.argv[1], encoding="utf-8") as f:
        spec = json.load(f)
    ff = ffmpeg()
    base = os.path.dirname(os.path.abspath(sys.argv[1]))
    outdir = os.path.join(base, spec.get("output", {}).get("clip_dir", "视频"))
    os.makedirs(outdir, exist_ok=True)

    for c in spec.get("clips", []):
        src = c["src"]
        if not os.path.isabs(src):
            src = os.path.join(base, src)
        s, e = secs(c["start"]), secs(c["end"])
        n = c["n"]
        crop = detect_band(src, s + 1.0) if c.get("crop", True) else None
        o1 = os.path.join(outdir, f"视频{n}.mp4")
        dur = cut(ff, src, s, e, o1)
        msg = f"视频{n}.mp4  {clean(s)}–{clean(e)}  {dur:.1f}s"
        if crop:
            o2 = os.path.join(outdir, f"视频{n}_横屏.mp4")
            cut(ff, src, s, e, o2, crop)
            msg += f"  + 横屏版（裁黑边 y{crop[0]}–{crop[1]}）"
        print(msg)


if __name__ == "__main__":
    main()
