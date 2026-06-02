#!/usr/bin/env python3
"""Crop a headshot to a minimum 4:5 (width:height) ratio JPEG so the face stays fully visible.

- Flattens transparency onto white.
- If the source is WIDER than the target ratio (landscape/square), crops width only,
  centred on a face fraction, keeping full height (so the face is never cut vertically).
- Images already TALLER than the ratio are kept as-is (just re-encoded), per the ALPS rule
  "minimum 4:5, taller is fine".
- Downscales very tall images to --max-h.

Usage:
  crop_speaker_photo.py SRC OUT.jpg [--fx 0.5] [--ratio 0.8] [--max-h 1600] [--quality 88]

--fx   horizontal face centre as a fraction of width (0=left, 1=right). Set this for
       landscape/off-centre photos. Default 0.5 (centred).
--ratio  minimum width/height. 4:5 = 0.8 (default).

Install Pillow if missing:
  python3 -m pip install --user --break-system-packages pillow
"""
import argparse
import sys

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow missing — run: python3 -m pip install --user --break-system-packages pillow")


def main():
    ap = argparse.ArgumentParser(description="Crop a headshot to min 4:5 JPEG.")
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--fx", type=float, default=0.5, help="face x-centre fraction 0..1")
    ap.add_argument("--ratio", type=float, default=0.8, help="min width/height (4:5=0.8)")
    ap.add_argument("--max-h", type=int, default=1600)
    ap.add_argument("--quality", type=int, default=88)
    a = ap.parse_args()

    im = Image.open(a.src)
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
        im = Image.alpha_composite(bg, im).convert("RGB")
    else:
        im = im.convert("RGB")

    w, h = im.size
    if w / h > a.ratio + 1e-6:                 # wider than target -> crop width, keep height
        nw = round(h * a.ratio)
        left = round(a.fx * w - nw / 2)
        left = max(0, min(left, w - nw))
        im = im.crop((left, 0, left + nw, h))

    if im.size[1] > a.max_h:                    # downscale tall images
        nh = a.max_h
        nw = round(im.size[0] * nh / im.size[1])
        im = im.resize((nw, nh), Image.LANCZOS)

    im.save(a.out, "JPEG", quality=a.quality, optimize=True, progressive=True)
    fw, fh = im.size
    print(f"{a.src} {w}x{h} ({w/h:.3f}) -> {a.out} {fw}x{fh} ({fw/fh:.3f})  fx={a.fx}")


if __name__ == "__main__":
    main()
