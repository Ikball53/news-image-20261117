#!/usr/bin/env python3
"""The World in One Picture -- Tuesday 17 November 2026.

Pure-standard-library front-page generator. It composites pre-rendered
RGBA PNG assets (text, icons, dotted map, page furniture) onto a cream
front page and writes entry.png next to this file.

No Pillow, no network, no clock, no randomness: the output is fully
deterministic, so running this twice produces byte-identical files.

Layout (860 x 1024, matching the reference front page):
  red kicker + "16 STORIES" line, big navy date title, red rule,
  lead story #1 on the left with a dotted world map on the right,
  numbered cards 2-16 in a 3-column grid, AND FINALLY strip, sources.
"""
import os
import struct
import zlib

BASE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(BASE, "assets")

PAGE_W = 860
PAGE_H = 1024
RED = (192, 22, 42, 255)

# Grid geometry for cards 2..16: three columns, five rows.
COL_X = (30, 302, 574)
ROW_Y = (306, 435, 564, 693, 822)
CARD_W = 256
CARD_H = 120


# ---------------------------------------------------------------- PNG codec
def _paeth(left, up, up_left):
    """PNG Paeth predictor, straight from the spec."""
    p = left + up - up_left
    pa, pb, pc = abs(p - left), abs(p - up), abs(p - up_left)
    if pa <= pb and pa <= pc:
        return left
    if pb <= pc:
        return up
    return up_left


def decode_png(data):
    """Decode an 8-bit non-interlaced PNG into (width, height, RGBA bytes)."""
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG file")
    pos = 8
    idat = bytearray()
    palette = None
    trans = None
    width = height = None
    bit_depth = colour = None
    while pos < len(data):
        size = int.from_bytes(data[pos:pos + 4], "big")
        kind = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + size]
        if kind == b"IHDR":
            width = int.from_bytes(body[0:4], "big")
            height = int.from_bytes(body[4:8], "big")
            bit_depth, colour = body[8], body[9]
            if bit_depth != 8 or body[12] != 0:
                raise ValueError("only 8-bit non-interlaced PNGs")
        elif kind == b"PLTE":
            palette = body
        elif kind == b"tRNS":
            trans = body
        elif kind == b"IDAT":
            idat += body
        elif kind == b"IEND":
            break
        pos += 12 + size
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[colour]
    raw = zlib.decompress(bytes(idat))
    stride = width * channels
    out = bytearray(width * height * 4)
    prev = bytearray(stride)
    p = 0
    for y in range(height):
        ftype = raw[p]
        p += 1
        line = bytearray(raw[p:p + stride])
        p += stride
        if ftype == 1:  # Sub
            for i in range(channels, stride):
                line[i] = (line[i] + line[i - channels]) & 255
        elif ftype == 2:  # Up
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 255
        elif ftype == 3:  # Average
            for i in range(stride):
                a = line[i - channels] if i >= channels else 0
                line[i] = (line[i] + ((a + prev[i]) >> 1)) & 255
        elif ftype == 4:  # Paeth
            for i in range(stride):
                a = line[i - channels] if i >= channels else 0
                b = prev[i]
                c = prev[i - channels] if i >= channels else 0
                line[i] = (line[i] + _paeth(a, b, c)) & 255
        for x in range(width):
            o = (y * width + x) * 4
            s = x * channels
            if colour == 6:
                out[o:o + 4] = line[s:s + 4]
            elif colour == 2:
                out[o:o + 3] = line[s:s + 3]
                out[o + 3] = 255
            elif colour == 0:
                out[o] = out[o + 1] = out[o + 2] = line[s]
                out[o + 3] = 255
            elif colour == 4:
                out[o] = out[o + 1] = out[o + 2] = line[s]
                out[o + 3] = line[s + 1]
            else:  # palette
                idx = line[s]
                out[o:o + 3] = palette[idx * 3:idx * 3 + 3]
                out[o + 3] = trans[idx] if trans and idx < len(trans) else 255
        prev = line
    return width, height, bytes(out)


def _chunk(kind, body):
    out = struct.pack(">I", len(body)) + kind + body
    out += struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)
    return out


def encode_png(width, height, rgba):
    """Encode RGBA bytes as a PNG. Filter 0 rows, fixed zlib level."""
    raw = bytearray()
    stride = width * 4
    for y in range(height):
        raw.append(0)
        raw += rgba[y * stride:(y + 1) * stride]
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n"
            + _chunk(b"IHDR", ihdr)
            + _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + _chunk(b"IEND", b""))


# ------------------------------------------------------------------ canvas
def load_asset(name):
    with open(os.path.join(ASSETS, name), "rb") as handle:
        return decode_png(handle.read())


def paste(canvas, img, img_w, img_h, dx, dy):
    """Source-over composite of an RGBA asset onto the RGBA canvas."""
    for y in range(img_h):
        ty = dy + y
        if ty < 0 or ty >= PAGE_H:
            continue
        for x in range(img_w):
            tx = dx + x
            if tx < 0 or tx >= PAGE_W:
                continue
            si = (y * img_w + x) * 4
            alpha = img[si + 3]
            if alpha == 0:
                continue
            di = (ty * PAGE_W + tx) * 4
            if alpha == 255:
                canvas[di:di + 4] = img[si:si + 4]
            else:
                a = alpha / 255.0
                for k in range(3):
                    canvas[di + k] = round(img[si + k] * a
                                           + canvas[di + k] * (1.0 - a))
                canvas[di + 3] = 255
    return canvas


def place(canvas, name, x, y):
    """Paste an asset at (x, y); return its (width, height)."""
    w, h, img = load_asset(name)
    paste(canvas, img, w, h, x, y)
    return w, h


def place_right(canvas, name, right, y):
    """Paste an asset with its right edge at x = right."""
    w, h, img = load_asset(name)
    paste(canvas, img, w, h, right - w, y)
    return w, h


def place_centred(canvas, name, x0, x1, y):
    """Paste an asset centred between x0 and x1."""
    w, h, img = load_asset(name)
    paste(canvas, img, w, h, x0 + (x1 - x0 - w) // 2, y)
    return w, h


def fill_rect(canvas, x, y, w, h, colour):
    for yy in range(y, y + h):
        for xx in range(x, x + w):
            i = (yy * PAGE_W + xx) * 4
            canvas[i:i + 4] = bytes(colour)


# ------------------------------------------------------------------- build
def _require_assets():
    """Fail fast with a clear list if any pre-rendered asset is missing."""
    names = ["bg.png", "card.png", "map.png"]
    names += ["badges/b%02d.png" % n for n in range(1, 17)]
    names += ["icons/i%02d.png" % n for n in range(2, 17)]
    names += ["text/kicker.png", "text/topright.png", "text/title.png",
              "text/lead_region.png", "text/lead_head.png", "text/lead_sum.png",
              "text/map_label.png", "text/finally.png", "text/sources.png"]
    names += ["text/c%02d_%s.png" % (n, part)
              for n in range(2, 17) for part in ("region", "head", "sum")]
    missing = [n for n in names
               if not os.path.exists(os.path.join(ASSETS, n))]
    if missing:
        raise SystemExit("missing assets: " + ", ".join(missing))


def build_page():
    _require_assets()
    width, height, page = load_asset("bg.png")
    canvas = bytearray(page)

    # Header: kicker left, story count right, big date title, red rule.
    place(canvas, "text/kicker.png", 30, 28)
    place_right(canvas, "text/topright.png", 830, 30)
    place(canvas, "text/title.png", 30, 54)
    fill_rect(canvas, 30, 118, 800, 4, RED)

    # Lead story #1 (left) and the dotted world map (right).
    place(canvas, "badges/b01.png", 30, 130)
    place(canvas, "text/lead_region.png", 68, 138)
    _, head_h = place(canvas, "text/lead_head.png", 30, 164)
    place(canvas, "text/lead_sum.png", 30, 164 + head_h + 6)
    place(canvas, "map.png", 545, 130)
    place_centred(canvas, "text/map_label.png", 545, 830, 256)

    # Cards 2..16 in the 3-column grid.
    for n in range(2, 17):
        slot = n - 2
        cx = COL_X[slot % 3]
        cy = ROW_Y[slot // 3]
        place(canvas, "card.png", cx, cy)
        place(canvas, "badges/b%02d.png" % n, cx + 12, cy + 10)
        place(canvas, "text/c%02d_region.png" % n, cx + 42, cy + 14)
        place(canvas, "icons/i%02d.png" % n, cx + 214, cy + 9)
        _, head_h = place(canvas, "text/c%02d_head.png" % n, cx + 12, cy + 40)
        place(canvas, "text/c%02d_sum.png" % n, cx + 12, cy + 40 + head_h + 4)

    # Footer: AND FINALLY strip and the sources line.
    place(canvas, "text/finally.png", 30, 954)
    place(canvas, "text/sources.png", 30, 982)
    return bytes(canvas)


def main():
    pixels = build_page()
    data = encode_png(PAGE_W, PAGE_H, pixels)
    out_path = os.path.join(BASE, "entry.png")
    with open(out_path, "wb") as handle:
        handle.write(data)
    print("wrote %s: %d x %d, %d bytes" % (out_path, PAGE_W, PAGE_H,
                                          len(data)))


if __name__ == "__main__":
    main()
