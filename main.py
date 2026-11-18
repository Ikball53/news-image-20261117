#!/usr/bin/env python3
"""The World in One Picture - Tuesday 17 November 2026.

Pure-standard-library generator: draws the front page from scratch and
writes /output/entry.png. No Pillow, no network, no randomness, no time.
Text, icons and flags are pre-rendered RGBA PNGs under assets/ (rendered
offline with PIL); this file only blits them, draws shapes, resamples the
illustrations and the world map with integer fixed-point math, and writes
the PNG itself. Two runs produce byte-identical output.
"""
import os
import struct
import sys
import zlib
from math import isqrt
from pathlib import Path

# ---------------------------------------------------------------- palette
BG = (246, 241, 231)
WHITE = (255, 255, 255)
BORDER = (227, 220, 203)
NAVY = (27, 42, 74)
RED = (192, 57, 43)
PINK = (232, 175, 168)
TINT = (243, 237, 224)

# ---------------------------------------------------------------- geometry
# Whole design is the 1080x1276 v2 front page scaled by S = 1024/1276.
PAGE_W = 867
PAGE_H = 1024
MARGIN = 21
CW = 825
RULE_Y = 111
RULE_H = 2
TOP_Y = 124
TOP_H = 270
LEFT_CARD = (21, 124, 520, 270)
RIGHT_CARD = (554, 124, 292, 270)
ILL_MAIN = (27, 130, 202, 257)
ILL_MAIN_FOCUS = 620  # permille
BADGE1 = (242, 137, 24)  # x, y, diameter
MAP_BOX = (565, 161, 270, 173)
SEC_Y = 407
SEC_H = 258
CARD_W = 266
CARD_XS = [21, 300, 579]
BANNER = (254, 95)
BANNER_FOCUS = 450  # permille
ALSO = (21, 678, 825, 301)  # x, y, w, h

# Pre-rendered text lines: (asset path, x, y). Positions come from the
# offline layout pass (greedy wrap by pixel width at the scaled sizes).
TEXT = [
    ("text/header_left.png", 21, 24),
    ("text/header_right.png", 634, 24),
    ("text/title.png", 21, 48),
    ("text/m1_head_0.png", 242, 171),
    ("text/m1_head_1.png", 242, 202),
    ("text/m1_head_2.png", 242, 233),
    ("text/m1_cap_0.png", 242, 269),
    ("text/m1_cap_1.png", 242, 287),
    ("text/m1_region.png", 274, 140),
    ("text/map_title.png", 565, 135),
    ("text/map_date.png", 766, 136),
    ("text/map_note0.png", 565, 342),
    ("text/map_note1.png", 565, 358),
    ("text/c2_region.png", 60, 522),
    ("text/c2_head_0.png", 32, 548),
    ("text/c2_head_1.png", 32, 570),
    ("text/c2_cap_0.png", 32, 595),
    ("text/c2_cap_1.png", 32, 610),
    ("text/c3_region.png", 339, 522),
    ("text/c3_head_0.png", 311, 548),
    ("text/c3_head_1.png", 311, 570),
    ("text/c3_cap_0.png", 311, 595),
    ("text/c3_cap_1.png", 311, 610),
    ("text/c4_region.png", 618, 522),
    ("text/c4_head_0.png", 590, 548),
    ("text/c4_head_1.png", 590, 570),
    ("text/c4_head_2.png", 590, 592),
    ("text/c4_cap_0.png", 590, 617),
    ("text/c4_cap_1.png", 590, 632),
    ("text/also_header.png", 34, 688),
    ("text/a01_0.png", 92, 713),
    ("text/a01_1.png", 92, 728),
    ("text/a02_0.png", 363, 713),
    ("text/a02_1.png", 363, 728),
    ("text/a03_0.png", 634, 713),
    ("text/a03_1.png", 634, 728),
    ("text/a04_0.png", 92, 777),
    ("text/a04_1.png", 92, 792),
    ("text/a05_0.png", 363, 777),
    ("text/a06_0.png", 634, 777),
    ("text/a07_0.png", 92, 841),
    ("text/a07_1.png", 92, 856),
    ("text/a08_0.png", 363, 841),
    ("text/a08_1.png", 363, 856),
    ("text/a09_0.png", 634, 841),
    ("text/a09_1.png", 634, 856),
    ("text/a10_0.png", 92, 905),
    ("text/a10_1.png", 92, 920),
    ("text/a11_0.png", 363, 905),
    ("text/a11_1.png", 363, 920),
    ("text/a12_0.png", 634, 905),
    ("text/a12_1.png", 634, 920),
    ("text/footer.png", 46, 992),
]

# Second-row cards: (illustration asset, badge number digit asset).
SECOND_CARDS = [
    ("ill_tankers.png", "text/digit_2_11.png"),
    ("ill_summit.png", "text/digit_3_11.png"),
    ("ill_jets.png", "text/digit_4_11.png"),
]

# ALSO grid: (icon asset, flag codes, tile x, tile y).
ALSO_ITEMS = [
    ("columns", ["UK"], 34, 710),
    ("megaphone", ["FR"], 305, 710),
    ("screen", ["US"], 576, 710),
    ("alert", ["UK", "US"], 34, 774),
    ("bitcoin", ["US"], 305, 774),
    ("jet", ["KR"], 576, 774),
    ("medcross", ["US"], 34, 838),
    ("plane", ["RU"], 305, 838),
    ("doc", ["UK"], 576, 838),
    ("gavel", ["MZ"], 34, 902),
    ("globe", ["SD"], 305, 902),
    ("chip", ["US"], 576, 902),
]

# Map overlays. Longitudes/latitudes in milli-degrees; ellipse radii in px.
MAP_ELLIPSES = [
    (-100000, 40000, 42, 27),
    (-100, 51500, 10, 6),
    (2350, 48850, 11, 8),
    (30000, 13000, 22, 19),
    (35500, -18700, 19, 16),
]
MAP_DOTS = [
    (34000, 45300),
    (50600, 26200),
    (114100, 22500),
    (138000, 36000),
    (-77000, 38900),
    (128000, 36500),
    (86100, 55400),
    (35500, -18700),
    (30000, 13000),
    (-100, 51500),
    (2350, 48850),
]
DOT_R = 5
PINK_ALPHA = 78


# ---------------------------------------------------------------- PNG read
def _paeth(a, b, c):
    p = a + b - c
    pa = p - a if p >= a else a - p
    pb = p - b if p >= b else b - p
    pc = p - c if p >= c else c - p
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def read_png(path):
    """Read an 8-bit non-interlaced PNG (colour types 2 RGB, 6 RGBA).

    Returns (width, height, bytearray of RGBA pixels)."""
    with open(path, "rb") as fh:
        data = fh.read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG: %s" % path)
    pos = 8
    width = height = 0
    bitdepth = 0
    colortype = 0
    idat = bytearray()
    while pos < len(data):
        ln = struct.unpack(">I", data[pos:pos + 4])[0]
        typ = data[pos + 4:pos + 8]
        chunk = data[pos + 8:pos + 8 + ln]
        if typ == b"IHDR":
            width, height, bitdepth, colortype = struct.unpack(">IIBB", chunk[:10])
            if bitdepth != 8 or colortype not in (2, 6):
                raise ValueError("unsupported PNG %s: depth %d type %d"
                                 % (path, bitdepth, colortype))
        elif typ == b"IDAT":
            idat += chunk
        elif typ == b"IEND":
            break
        pos += 12 + ln
    bpp = 3 if colortype == 2 else 4
    stride = width * bpp
    raw = zlib.decompress(bytes(idat))
    out = bytearray(width * height * 4)
    rgb_all = bytearray(width * height * 3) if colortype == 2 else None
    prev = bytearray(stride)
    for y in range(height):
        base = y * (stride + 1)
        ftype = raw[base]
        row = bytearray(raw[base + 1:base + 1 + stride])
        if ftype == 1:
            for i in range(bpp, stride):
                row[i] = (row[i] + row[i - bpp]) & 255
        elif ftype == 2:
            for i in range(stride):
                row[i] = (row[i] + prev[i]) & 255
        elif ftype == 3:
            for i in range(stride):
                a = row[i - bpp] if i >= bpp else 0
                row[i] = (row[i] + ((a + prev[i]) >> 1)) & 255
        elif ftype == 4:
            for i in range(stride):
                a = row[i - bpp] if i >= bpp else 0
                b = prev[i]
                c = prev[i - bpp] if i >= bpp else 0
                row[i] = (row[i] + _paeth(a, b, c)) & 255
        elif ftype != 0:
            raise ValueError("bad PNG filter %d" % ftype)
        prev = row
        if colortype == 2:
            rgb_all[y * stride:(y + 1) * stride] = row
        else:
            out[y * width * 4:(y + 1) * width * 4] = row
    if colortype == 2:
        # RGB -> RGBA by C-speed slice assignment (alpha channel all 255).
        n = width * height
        out[0::4] = rgb_all[0::3]
        out[1::4] = rgb_all[1::3]
        out[2::4] = rgb_all[2::3]
        out[3::4] = b"\xff" * n
    return width, height, out


# ---------------------------------------------------------------- PNG write
def _chunk(typ, payload):
    out = struct.pack(">I", len(payload)) + typ + payload
    out += struct.pack(">I", zlib.crc32(typ + payload) & 0xFFFFFFFF)
    return out


def _filter_row(ftype, row, prev, bpp):
    n = len(row)
    out = bytearray(n)
    if ftype == 0:
        out[:] = row
    elif ftype == 1:
        for i in range(n):
            a = row[i - bpp] if i >= bpp else 0
            out[i] = (row[i] - a) & 255
    elif ftype == 2:
        for i in range(n):
            out[i] = (row[i] - prev[i]) & 255
    elif ftype == 4:
        for i in range(n):
            a = row[i - bpp] if i >= bpp else 0
            b = prev[i]
            c = prev[i - bpp] if i >= bpp else 0
            out[i] = (row[i] - _paeth(a, b, c)) & 255
    return out


def write_png(path, width, height, rgb):
    """Write an 8-bit RGB PNG, zlib level 9, best per-row filter of 0/1/2/4."""
    stride = width * 3
    body = bytearray()
    prev = bytes(stride)
    for y in range(height):
        row = rgb[y * stride:(y + 1) * stride]
        best_type = 0
        best_data = None
        best_score = None
        for ftype in (0, 1, 2, 4):
            cand = _filter_row(ftype, row, prev, 3)
            score = 0
            for v in cand:
                score += v - 128 if v >= 128 else 128 - v
            if best_score is None or score < best_score:
                best_score = score
                best_type = ftype
                best_data = cand
        body.append(best_type)
        body += best_data
        prev = row
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", ihdr)
    png += _chunk(b"IDAT", zlib.compress(bytes(body), 9))
    png += _chunk(b"IEND", b"")
    with open(path, "wb") as fh:
        fh.write(png)


# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, width, height, bg):
        self.w = width
        self.h = height
        self.px = bytearray(width * height * 3)
        self.fill_rect(0, 0, width, height, bg)

    def _idx(self, x, y):
        return (y * self.w + x) * 3

    def fill_rect(self, x, y, w, h, color):
        r, g, b = color
        x0 = x if x > 0 else 0
        y0 = y if y > 0 else 0
        x1 = x + w if x + w < self.w else self.w
        y1 = y + h if y + h < self.h else self.h
        for yy in range(y0, y1):
            base = (yy * self.w + x0) * 3
            for xx in range(x0, x1):
                o = base + (xx - x0) * 3
                self.px[o] = r
                self.px[o + 1] = g
                self.px[o + 2] = b

    def _row_spans(self, x, y, w, h, r):
        """Per-row (x0, x1) spans of a rounded rect, via integer sqrt."""
        spans = []
        for yy in range(y, y + h):
            dtop = yy - y
            dbot = (y + h - 1) - yy
            d = dtop if dtop < dbot else dbot
            if d < r:
                k = r - 1 - d
                inset = r - isqrt(r * r - k * k)
            else:
                inset = 0
            spans.append((x + inset, x + w - inset))
        return spans

    def rounded_fill(self, x, y, w, h, r, color):
        cr, cg, cb = color
        for yy, (x0, x1) in enumerate(self._row_spans(x, y, w, h, r)):
            if x0 >= x1:
                continue
            base = ((y + yy) * self.w + x0) * 3
            for xx in range(x0, x1):
                o = base + (xx - x0) * 3
                self.px[o] = cr
                self.px[o + 1] = cg
                self.px[o + 2] = cb

    def rounded_card(self, x, y, w, h, r, border, fill, thick):
        self.rounded_fill(x, y, w, h, r, border)
        inner_r = r - thick if r > thick else 0
        self.rounded_fill(x + thick, y + thick, w - 2 * thick, h - 2 * thick,
                          inner_r, fill)

    def blend_pixel(self, x, y, color, alpha):
        if alpha <= 0 or x < 0 or y < 0 or x >= self.w or y >= self.h:
            return
        o = (y * self.w + x) * 3
        inv = 255 - alpha
        self.px[o] = (color[0] * alpha + self.px[o] * inv) // 255
        self.px[o + 1] = (color[1] * alpha + self.px[o + 1] * inv) // 255
        self.px[o + 2] = (color[2] * alpha + self.px[o + 2] * inv) // 255

    def fill_ellipse(self, cx, cy, rx, ry, color, alpha=255):
        if rx <= 0 or ry <= 0:
            return
        rx2 = rx * rx
        for dy in range(-ry, ry + 1):
            hw = isqrt(rx2 - (rx2 * dy * dy) // (ry * ry))
            yy = cy + dy
            if yy < 0 or yy >= self.h:
                continue
            x0 = cx - hw
            x1 = cx + hw
            if x0 < 0:
                x0 = 0
            if x1 >= self.w:
                x1 = self.w - 1
            if alpha == 255:
                base = (yy * self.w + x0) * 3
                for xx in range(x0, x1 + 1):
                    o = base + (xx - x0) * 3
                    self.px[o] = color[0]
                    self.px[o + 1] = color[1]
                    self.px[o + 2] = color[2]
            else:
                for xx in range(x0, x1 + 1):
                    self.blend_pixel(xx, yy, color, alpha)

    def blit(self, img, dx, dy):
        """Alpha-composite an RGBA image (w, h, bytearray) at (dx, dy)."""
        iw, ih, data = img
        for y in range(ih):
            ty = dy + y
            if ty < 0 or ty >= self.h:
                continue
            for x in range(iw):
                tx = dx + x
                if tx < 0 or tx >= self.w:
                    continue
                s = (y * iw + x) * 4
                a = data[s + 3]
                if a == 0:
                    continue
                o = (ty * self.w + tx) * 3
                if a == 255:
                    self.px[o] = data[s]
                    self.px[o + 1] = data[s + 1]
                    self.px[o + 2] = data[s + 2]
                else:
                    inv = 255 - a
                    self.px[o] = (data[s] * a + self.px[o] * inv) // 255
                    self.px[o + 1] = (data[s + 1] * a + self.px[o + 1] * inv) // 255
                    self.px[o + 2] = (data[s + 2] * a + self.px[o + 2] * inv) // 255

    def paste_cover(self, img, dx, dy, dw, dh, radius, focus, cover=True):
        """Bilinear cover-crop resample of an RGBA image into a box.

        focus is a permille (0..1000) biasing the vertical crop window.
        radius clips the result to a rounded rect. With cover=False the
        whole source is stretched into the box instead. All math is
        integer fixed-point (16.16), so the result is deterministic."""
        sw, sh, data = img
        if cover and sw * dh > dw * sh:
            # Source is wider than the box: crop the width.
            crop_w = (sh * dw) // dh
            crop_h = sh
            sx0 = (sw - crop_w) // 2
            sy0 = 0
        elif cover:
            # Source is taller than the box: crop the height.
            crop_w = sw
            crop_h = (sw * dh) // dw
            sx0 = 0
            sy0 = ((sh - crop_h) * focus) // 1000
        else:
            # Stretch the whole source into the box (used for the map,
            # whose dot projection assumes the full cropped image).
            crop_w = sw
            crop_h = sh
            sx0 = 0
            sy0 = 0
        if crop_w <= 0 or crop_h <= 0:
            return
        spans = None
        if radius:
            spans = self._row_spans(dx, dy, dw, dh, radius)
        for j in range(dh):
            ty = dy + j
            if ty < 0 or ty >= self.h:
                continue
            if spans is not None:
                x0, x1 = spans[j]
            else:
                x0, x1 = dx, dx + dw
            if x0 < 0:
                x0 = 0
            if x1 > self.w:
                x1 = self.w
            sy_fp = (sy0 << 16) + ((j << 16) * crop_h) // dh
            sy = sy_fp >> 16
            fy = sy_fp & 0xFFFF
            sy1 = sy + 1 if sy + 1 < sh else sh - 1
            w_top = 65536 - fy
            for i in range(x0 - dx, x1 - dx):
                sx_fp = (sx0 << 16) + ((i << 16) * crop_w) // dw
                sx = sx_fp >> 16
                fx = sx_fp & 0xFFFF
                sx1 = sx + 1 if sx + 1 < sw else sw - 1
                o00 = (sy * sw + sx) * 4
                o10 = (sy * sw + sx1) * 4
                o01 = (sy1 * sw + sx) * 4
                o11 = (sy1 * sw + sx1) * 4
                w00 = (65536 - fx) * w_top
                w10 = fx * w_top
                w01 = (65536 - fx) * fy
                w11 = fx * fy
                r = (data[o00] * w00 + data[o10] * w10
                     + data[o01] * w01 + data[o11] * w11) >> 32
                g = (data[o00 + 1] * w00 + data[o10 + 1] * w10
                     + data[o01 + 1] * w01 + data[o11 + 1] * w11) >> 32
                b = (data[o00 + 2] * w00 + data[o10 + 2] * w10
                     + data[o01 + 2] * w01 + data[o11 + 2] * w11) >> 32
                a = (data[o00 + 3] * w00 + data[o10 + 3] * w10
                     + data[o01 + 3] * w01 + data[o11 + 3] * w11) >> 32
                o = (ty * self.w + dx + i) * 3
                if a == 255:
                    self.px[o] = r
                    self.px[o + 1] = g
                    self.px[o + 2] = b
                elif a:
                    inv = 255 - a
                    self.px[o] = (r * a + self.px[o] * inv) // 255
                    self.px[o + 1] = (g * a + self.px[o + 1] * inv) // 255
                    self.px[o + 2] = (b * a + self.px[o + 2] * inv) // 255


# ---------------------------------------------------------------- page
def build_page(assets):
    cv = Canvas(PAGE_W, PAGE_H, BG)
    # Navy rule under the title.
    cv.fill_rect(MARGIN, RULE_Y, CW, RULE_H, NAVY)
    # Top row: main story card + map card.
    cv.rounded_card(LEFT_CARD[0], LEFT_CARD[1], LEFT_CARD[2], LEFT_CARD[3],
                    11, BORDER, WHITE, 2)
    cv.rounded_card(RIGHT_CARD[0], RIGHT_CARD[1], RIGHT_CARD[2], RIGHT_CARD[3],
                    11, BORDER, WHITE, 2)
    cv.paste_cover(read_png(str(assets / "ill_bridge.png")),
                   ILL_MAIN[0], ILL_MAIN[1], ILL_MAIN[2], ILL_MAIN[3],
                   8, ILL_MAIN_FOCUS)
    # Red badge with white "1".
    bx, by, bd = BADGE1
    cv.fill_ellipse(bx + bd // 2, by + bd // 2, bd // 2, bd // 2, RED)
    digit = read_png(str(assets / "text" / "digit_1_13.png"))
    cv.blit(digit, bx + (bd - digit[0]) // 2, by + (bd - digit[1]) // 2)
    # World map: resize into its box, pink ellipses, then red dots.
    mx, my, mw, mh = MAP_BOX
    cv.paste_cover(read_png(str(assets / "map.png")), mx, my, mw, mh, 0, 500,
                   cover=False)
    for lon_m, lat_m, rx, ry in MAP_ELLIPSES:
        ex = mx + ((lon_m + 180000) * mw) // 360000
        ey = my + ((83000 - lat_m) * mh) // 138000
        cv.fill_ellipse(ex, ey, rx, ry, PINK, PINK_ALPHA)
    for lon_m, lat_m in MAP_DOTS:
        px = mx + ((lon_m + 180000) * mw) // 360000
        py = my + ((83000 - lat_m) * mh) // 138000
        cv.fill_ellipse(px, py, DOT_R + 2, DOT_R + 2, WHITE)
        cv.fill_ellipse(px, py, DOT_R, DOT_R, RED)
    # Second row: three cards with banner, badge, region, headline, caption.
    for i, (ill, digit_file) in enumerate(SECOND_CARDS):
        cx0 = CARD_XS[i]
        cv.rounded_card(cx0, SEC_Y, CARD_W, SEC_H, 11, BORDER, WHITE, 2)
        cv.paste_cover(read_png(str(assets / ill)),
                       cx0 + 6, SEC_Y + 6, BANNER[0], BANNER[1], 8, BANNER_FOCUS)
        bx = cx0 + 11
        by = SEC_Y + 112
        cv.fill_ellipse(bx + 10, by + 10, 10, 10, RED)
        digit = read_png(str(assets / digit_file))
        cv.blit(digit, bx + (21 - digit[0]) // 2, by + (21 - digit[1]) // 2)
    # ALSO section: card, icon tiles, icons, flag strips.
    ax, ay, aw, ah = ALSO
    cv.rounded_card(ax, ay, aw, ah, 11, BORDER, WHITE, 2)
    for icon, flags, tx0, ty0 in ALSO_ITEMS:
        cv.rounded_fill(tx0, ty0, 48, 48, 8, TINT)
        cv.blit(read_png(str(assets / "icons" / (icon + ".png"))),
                tx0 + 8, ty0 + 2)
        if len(flags) == 1:
            cv.blit(read_png(str(assets / "flags" / (flags[0] + ".png"))),
                    tx0 + 12, ty0 + 37)
        else:
            cv.blit(read_png(str(assets / "flags" / (flags[0] + "_s.png"))),
                    tx0 + 12, ty0 + 37)
            cv.blit(read_png(str(assets / "flags" / (flags[1] + "_s.png"))),
                    tx0 + 25, ty0 + 37)
    # All pre-rendered text lines on top.
    for rel, tx, ty in TEXT:
        cv.blit(read_png(str(assets / rel)), tx, ty)
    return cv


def main():
    here = Path(__file__).resolve().parent
    assets = here / "assets"
    outdir = Path("/output")
    outdir.mkdir(parents=True, exist_ok=True)
    cv = build_page(assets)
    out = outdir / "entry.png"
    write_png(str(out), cv.w, cv.h, cv.px)
    print("wrote %s %dx%d %d bytes" % (out, cv.w, cv.h, os.path.getsize(out)))


if __name__ == "__main__":
    sys.exit(main())
