# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo>=0.23.3",
#     "numpy==2.5.2",
#     "wigglystuff==0.5.28",
# ]
# ///

import marimo

__generated_with = "0.24.0"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _():
    import marimo as mo
    import math
    import itertools
    from wigglystuff import ColorPicker

    def get_hex(val):
        """Extract hex from ColorPicker value (dict or string)."""
        if isinstance(val, dict):
            return val.get('color', '#000000')
        return val

    def swatch(hexv, w=80, h=30):
        """Return HTML for a color swatch."""
        return mo.Html(f'<div style="width:{w}px;height:{h}px;background:{hexv};border:1px solid #888;border-radius:4px;display:inline-block;vertical-align:middle;"></div>')

    return ColorPicker, get_hex, itertools, math, mo, swatch


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Obsidian Color Optimization Lab

    Two linked problems, both built on **OKLCH** (perceptually uniform color)
    and **APCA** (perceptually calibrated contrast).

    1. **Base-color-derived font colors.** Mix a base color `B` into existing
       light/dark backgrounds `L`/`D` to get new backgrounds `Lb`/`Db`, then pick
       new font colors that (a) resemble `B` and (b) have high APCA contrast
       against both the new background and the *existing* font color on that side.
    2. **Three highlight colors** that are mutually distinguishable, sit at
       acceptable APCA contrast against both a dark and a light background, and
       stay muted (bounded OKLCH chroma) rather than garish.

    All color math below is implemented directly from primary sources:
    Björn Ottosson's OKLab/OKLCH definitions and sRGB gamut-clipping method, and
    Andrew Somers' APCA formula (0.0.98G reference implementation).
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 1. Core color math (OKLCH \u2194 sRGB, gamut clipping, APCA)
    """)
    return


@app.cell(hide_code=True)
def _(math):
    # ---- sRGB <-> linear ----
    def linear_to_srgb(c):
        c = max(0.0, min(1.0, c))
        return 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055

    def srgb_to_linear(c):
        c = max(0.0, min(1.0, c))
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    # ---- OKLab <-> linear sRGB (Bjorn Ottosson) ----
    def oklab_to_linear_srgb(L, a, b):
        l_ = L + 0.3963377774 * a + 0.2158037573 * b
        m_ = L - 0.1055613458 * a - 0.0638541728 * b
        s_ = L - 0.0894841775 * a - 1.2914855480 * b
        l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
        r = 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
        g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
        bl = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
        return r, g, bl

    def _cbrt(x):
        return x ** (1 / 3) if x >= 0 else -(-x) ** (1 / 3)

    def linear_srgb_to_oklab(r, g, b):
        l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
        m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
        s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
        l_, m_, s_ = _cbrt(l), _cbrt(m), _cbrt(s)
        L = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
        A = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
        B = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
        return L, A, B

    def oklch_to_oklab(L, C, H_deg):
        h = math.radians(H_deg)
        return L, C * math.cos(h), C * math.sin(h)

    def oklab_to_oklch(L, a, b):
        C = math.hypot(a, b)
        H = math.degrees(math.atan2(b, a)) % 360
        return L, C, H

    def in_gamut(r, g, b, eps=1e-4):
        return -eps <= r <= 1 + eps and -eps <= g <= 1 + eps and -eps <= b <= 1 + eps

    # ---- sRGB gamut clipping in Oklab, preserving chroma direction ----
    # Method: "gamut_clip_preserve_chroma" from Bjorn Ottosson,
    # https://bottosson.github.io/posts/gamutclipping/
    def _compute_max_saturation(a, b):
        if -1.88170328 * a - 0.80936493 * b > 1:
            k0, k1, k2, k3, k4 = 1.19086277, 1.76576728, 0.59662641, 0.75515197, 0.56771245
            wl, wm, ws = 4.0767416621, -3.3077115913, 0.2309699292
        elif 1.81444104 * a - 1.19445276 * b > 1:
            k0, k1, k2, k3, k4 = 0.73956515, -0.45954404, 0.08285427, 0.12541070, 0.14503204
            wl, wm, ws = -1.2684380046, 2.6097574011, -0.3413193965
        else:
            k0, k1, k2, k3, k4 = 1.35733652, -0.00915799, -1.15130210, -0.50559606, 0.00692167
            wl, wm, ws = -0.0041960863, -0.7034186147, 1.7076147010

        S = k0 + k1 * a + k2 * b + k3 * a * a + k4 * a * b
        k_l = 0.3963377774 * a + 0.2158037573 * b
        k_m = -0.1055613458 * a - 0.0638541728 * b
        k_s = -0.0894841775 * a - 1.2914855480 * b

        l_ = 1 + S * k_l
        m_ = 1 + S * k_m
        s_ = 1 + S * k_s
        l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
        l_dS = 3 * k_l * l_ * l_
        m_dS = 3 * k_m * m_ * m_
        s_dS = 3 * k_s * s_ * s_
        l_dS2 = 6 * k_l * k_l * l_
        m_dS2 = 6 * k_m * k_m * m_
        s_dS2 = 6 * k_s * k_s * s_

        f = wl * l + wm * m + ws * s
        f1 = wl * l_dS + wm * m_dS + ws * s_dS
        f2 = wl * l_dS2 + wm * m_dS2 + ws * s_dS2
        S = S - f * f1 / (f1 * f1 - 0.5 * f * f2)
        return S

    def _find_cusp(a, b):
        S_cusp = _compute_max_saturation(a, b)
        r, g, bl = oklab_to_linear_srgb(1, S_cusp * a, S_cusp * b)
        L_cusp = (1.0 / max(r, g, bl)) ** (1 / 3)
        C_cusp = L_cusp * S_cusp
        return L_cusp, C_cusp

    def _find_gamut_intersection(a, b, L1, C1, L0):
        L_cusp, C_cusp = _find_cusp(a, b)
        if ((L1 - L0) * C_cusp - (L_cusp - L0) * C1) <= 0:
            t = C_cusp * L0 / (C1 * L_cusp + C_cusp * (L0 - L1))
        else:
            t = C_cusp * (L0 - 1) / (C1 * (L_cusp - 1) + C_cusp * (L0 - L1))
            dL = L1 - L0
            dC = C1
            k_l = 0.3963377774 * a + 0.2158037573 * b
            k_m = -0.1055613458 * a - 0.0638541728 * b
            k_s = -0.0894841775 * a - 1.2914855480 * b
            l_dt = dL + dC * k_l
            m_dt = dL + dC * k_m
            s_dt = dL + dC * k_s

            L = L0 * (1 - t) + t * L1
            C = t * C1
            l_ = L + C * k_l
            m_ = L + C * k_m
            s_ = L + C * k_s
            l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
            ldt = 3 * l_dt * l_ * l_
            mdt = 3 * m_dt * m_ * m_
            sdt = 3 * s_dt * s_ * s_
            ldt2 = 6 * l_dt * l_dt * l_
            mdt2 = 6 * m_dt * m_dt * m_
            sdt2 = 6 * s_dt * s_dt * s_

            r = 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s - 1
            r1 = 4.0767416621 * ldt - 3.3077115913 * mdt + 0.2309699292 * sdt
            r2 = 4.0767416621 * ldt2 - 3.3077115913 * mdt2 + 0.2309699292 * sdt2
            u_r = r1 / (r1 * r1 - 0.5 * r * r2)
            t_r = -r * u_r

            g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s - 1
            g1 = -1.2684380046 * ldt + 2.6097574011 * mdt - 0.3413193965 * sdt
            g2 = -1.2684380046 * ldt2 + 2.6097574011 * mdt2 - 0.3413193965 * sdt2
            u_g = g1 / (g1 * g1 - 0.5 * g * g2)
            t_g = -g * u_g

            bb = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s - 1
            b1 = -0.0041960863 * ldt - 0.7034186147 * mdt + 1.7076147010 * sdt
            b2 = -0.0041960863 * ldt2 - 0.7034186147 * mdt2 + 1.7076147010 * sdt2
            u_b = b1 / (b1 * b1 - 0.5 * bb * b2)
            t_b = -bb * u_b

            t_r = t_r if u_r >= 0 else float("inf")
            t_g = t_g if u_g >= 0 else float("inf")
            t_b = t_b if u_b >= 0 else float("inf")
            t += min(t_r, t_g, t_b)
        return t

    def gamut_clip_preserve_chroma(r, g, b):
        if in_gamut(r, g, b):
            return r, g, b
        L, a, bb = linear_srgb_to_oklab(r, g, b)
        C = max(1e-5, math.hypot(a, bb))
        a_, b_ = a / C, bb / C
        L0 = max(0.0, min(1.0, L))
        t = _find_gamut_intersection(a_, b_, L, C, L0)
        L_c = L0 * (1 - t) + t * L
        C_c = t * C
        return oklab_to_linear_srgb(L_c, C_c * a_, C_c * b_)

    def oklch_to_srgb_hex(L, C, H, clip=True):
        """OKLCH (L in 0..1, C typically 0..0.4, H in degrees) -> (#hex, (R,G,B), was_clipped)"""
        Lab = oklch_to_oklab(L, C, H)
        r, g, b = oklab_to_linear_srgb(*Lab)
        clipped = not in_gamut(r, g, b)
        if clipped:
            if clip:
                r, g, b = gamut_clip_preserve_chroma(r, g, b)
            else:
                r, g, b = min(max(r, 0), 1), min(max(g, 0), 1), min(max(b, 0), 1)
        R = max(0, min(255, round(linear_to_srgb(r) * 255)))
        G = max(0, min(255, round(linear_to_srgb(g) * 255)))
        B = max(0, min(255, round(linear_to_srgb(b) * 255)))
        return f"#{R:02x}{G:02x}{B:02x}", (R, G, B), clipped

    def hex_to_rgb255(hexstr):
        hexstr = hexstr.lstrip("#")
        return tuple(int(hexstr[i:i + 2], 16) for i in (0, 2, 4))

    def rgb255_to_oklch(rgb255):
        r, g, b = [srgb_to_linear(c / 255) for c in rgb255]
        L, a, bb = linear_srgb_to_oklab(r, g, b)
        return oklab_to_oklch(L, a, bb)

    def hex_to_oklch(hexstr):
        return rgb255_to_oklch(hex_to_rgb255(hexstr))

    def mix_oklab(hex_a, hex_b, t):
        """Mix two hex colors by fraction t (0=a, 1=b) in Oklab space (perceptually linear)."""
        ra, ga, ba = [srgb_to_linear(c / 255) for c in hex_to_rgb255(hex_a)]
        rb, gb, bb_ = [srgb_to_linear(c / 255) for c in hex_to_rgb255(hex_b)]
        La, Aa, Ba = linear_srgb_to_oklab(ra, ga, ba)
        Lb, Ab, Bb = linear_srgb_to_oklab(rb, gb, bb_)
        L = La * (1 - t) + Lb * t
        A = Aa * (1 - t) + Ab * t
        B = Ba * (1 - t) + Bb * t
        r, g, b = oklab_to_linear_srgb(L, A, B)
        clipped = not in_gamut(r, g, b)
        if clipped:
            r, g, b = gamut_clip_preserve_chroma(r, g, b)
        R = max(0, min(255, round(linear_to_srgb(r) * 255)))
        G = max(0, min(255, round(linear_to_srgb(g) * 255)))
        Bc = max(0, min(255, round(linear_to_srgb(b) * 255)))
        return f"#{R:02x}{G:02x}{Bc:02x}"

    return hex_to_oklch, hex_to_rgb255, mix_oklab, oklch_to_srgb_hex


@app.cell(hide_code=True)
def _():
    # ---- APCA (Accessible Perceptual Contrast Algorithm) ----
    # Reference implementation per Andrew Somers / Myndex (0.0.98G "simple" form),
    # as documented at https://github.com/xi/apca-introduction and git.apcacontrast.com
    def _srgb255_to_Y_apca(rgb255):
        r = (rgb255[0] / 255) ** 2.4
        g = (rgb255[1] / 255) ** 2.4
        b = (rgb255[2] / 255) ** 2.4
        y = 0.2126729 * r + 0.7151522 * g + 0.0721750 * b
        if y < 0.022:
            y += (0.022 - y) ** 1.414
        return y

    def apca_contrast(fg255, bg255):
        """Returns Lc, signed: positive = light bg/dark text, negative = dark bg/light text."""
        yfg = _srgb255_to_Y_apca(fg255)
        ybg = _srgb255_to_Y_apca(bg255)
        c = 1.14
        if ybg > yfg:
            c *= ybg ** 0.56 - yfg ** 0.57
        else:
            c *= ybg ** 0.65 - yfg ** 0.62
        if abs(c) < 0.1:
            return 0.0
        elif c > 0:
            c -= 0.027
        else:
            c += 0.027
        return c * 100

    # APCA Lc thresholds (Lc = |contrast|), for reference / guardrails.
    # See "APCA in a Nutshell": Lc 90 preferred body text, Lc 75 min body text,
    # Lc 60 min non-body content text, Lc 45 min large/heavy text,
    # Lc 30 absolute min any text, Lc 15 visibility floor for non-text (e.g. cursor/border).
    APCA_LC_BODY_PREFERRED = 90
    APCA_LC_BODY_MIN = 75
    APCA_LC_CONTENT_MIN = 60
    APCA_LC_LARGE_MIN = 45
    APCA_LC_ABSOLUTE_MIN_TEXT = 30
    APCA_LC_NONTEXT_VISIBILITY_FLOOR = 15
    return (apca_contrast,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 2. Inputs: your base color and existing theme colors

    Fill in your Obsidian theme's actual hex values here. Defaults are a
    reasonable dark/light editor pair to experiment with.
    """)
    return


@app.cell
def _(ColorPicker, mo):
    base_color_input = mo.ui.anywidget(ColorPicker(color="#5e81ac"))
    L_bg_input = mo.ui.anywidget(ColorPicker(color="#fdfdfd"))
    D_bg_input = mo.ui.anywidget(ColorPicker(color="#1e1e1e"))
    Fl_input = mo.ui.anywidget(ColorPicker(color="#2e2e2e"))
    Fd_input = mo.ui.anywidget(ColorPicker(color="#dcdcdc"))
    mix_amount = mo.ui.slider(0.0, 1.0, value=0.12, step=0.01, show_value=True, label="Background mix amount (B into L/D)")
    return (
        D_bg_input,
        Fd_input,
        Fl_input,
        L_bg_input,
        base_color_input,
        mix_amount,
    )


@app.cell
def _(mo):
    mo.md(r"""
    ### 2a. New backgrounds `Lb`, `Db` (B mixed into L, D)
    """)
    return


@app.cell(hide_code=True)
def _(
    D_bg_input,
    Fd_input,
    Fl_input,
    L_bg_input,
    base_color_input,
    get_hex,
    hex_to_oklch,
    hex_to_rgb255,
    mix_amount,
    mix_oklab,
    mo,
    swatch,
):
    B = get_hex(base_color_input.value)
    L = get_hex(L_bg_input.value)
    D = get_hex(D_bg_input.value)
    Fl = get_hex(Fl_input.value)
    Fd = get_hex(Fd_input.value)
    t = mix_amount.value

    def color_info(hexv):
        L_, C_, H_ = hex_to_oklch(hexv)
        r, g, b = hex_to_rgb255(hexv)
        return f"`{hexv}` | L:{L_:.2f} C:{C_:.2f} H:{H_:.0f}° | RGB: {r}, {g}, {b}"

    ui_inputs = mo.vstack([
        mo.md("Adjust the colors using the pickers below:"),
        mo.hstack([mo.md("**Base color B:**"), base_color_input, swatch(B, 30, 20), mo.md(color_info(B))]),
        mo.hstack([mo.md("**Light bg L:**"), L_bg_input, swatch(L, 30, 20), mo.md(color_info(L))]),
        mo.hstack([mo.md("**Dark bg D:**"), D_bg_input, swatch(D, 30, 20), mo.md(color_info(D))]),
        mo.hstack([mo.md("**Light font Fl:**"), Fl_input, swatch(Fl, 30, 20), mo.md(color_info(Fl))]),
        mo.hstack([mo.md("**Dark font Fd:**"), Fd_input, swatch(Fd, 30, 20), mo.md(color_info(Fd))]),
        mo.md("<br>"),
        mix_amount
    ])

    Lb = mix_oklab(L, B, t)
    Db = mix_oklab(D, B, t)

    ui_mixed = mo.hstack([
        mo.vstack([
            mo.md(f"**Lb** (New Light Bg)"),
            swatch(Lb, 140, 50),
            mo.md(color_info(Lb))
        ]),
        mo.vstack([
            mo.md(f"**Db** (New Dark Bg)"),
            swatch(Db, 140, 50),
            mo.md(color_info(Db))
        ]),
    ])

    ui_result = mo.vstack([ui_inputs, mo.md("---"), ui_mixed])
    return B, Db, Lb


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### 2b. Search for new font colors near `B`

    For each side, we scan hue/lightness/chroma variants **close to B in OKLCH**
    and keep only those whose APCA contrast clears your chosen thresholds against
    *both* (a) the new background (`Lb`/`Db`) and (b) the existing font color on
    that side (`Fl`/`Fd`) — since the new accent text will often appear near or
    interleaved with existing body text.

    "Similar to B" is enforced by capping hue deviation and OKLCH distance from B;
    "high contrast" is enforced with an APCA floor you can tune.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    min_lc_vs_bg = mo.ui.slider(15, 105, value=60, step=1, show_value=True, label="Min |Lc| vs new background")
    min_lc_vs_font = mo.ui.slider(15, 105, value=30, step=1, show_value=True, label="Min |Lc| vs existing font (avoid camouflage)")
    max_hue_dev = mo.ui.slider(0, 60, value=20, step=1, show_value=True, label="Max hue deviation from B (deg)")
    chroma_cap = mo.ui.slider(0.02, 0.35, value=0.18, step=0.01, show_value=True, label="Chroma ceiling (muted <= ~0.12-0.15)")
    mo.vstack([mo.hstack([min_lc_vs_bg, min_lc_vs_font]), mo.hstack([max_hue_dev, chroma_cap])])
    return chroma_cap, max_hue_dev, min_lc_vs_bg, min_lc_vs_font


@app.cell(hide_code=True)
def _(
    B,
    Db,
    Fd_input,
    Fl_input,
    Lb,
    apca_contrast,
    chroma_cap,
    get_hex,
    hex_to_oklch,
    hex_to_rgb255,
    max_hue_dev,
    min_lc_vs_bg,
    min_lc_vs_font,
    mo,
    oklch_to_srgb_hex,
):
    import numpy as np

    def search_font_color(bg_hex, existing_font_hex, base_hex, lc_bg_min, lc_font_min, hue_dev_max, c_max, n_L=25, n_C=12, n_H=9):
        _, C_b, H_b = hex_to_oklch(base_hex)
        bg_rgb = hex_to_rgb255(bg_hex)
        font_rgb = hex_to_rgb255(existing_font_hex)

        candidates = []
        for L_ in np.linspace(0.15, 0.95, n_L):
            for C_ in np.linspace(0.0, c_max, n_C):
                for dH in np.linspace(-hue_dev_max, hue_dev_max, n_H):
                    H_ = (H_b + dH) % 360
                    hexv, rgb255, clipped = oklch_to_srgb_hex(L_, C_, H_)
                    lc_bg = apca_contrast(rgb255, bg_rgb)
                    lc_font = apca_contrast(rgb255, font_rgb)
                    if abs(lc_bg) >= lc_bg_min and abs(lc_font) >= lc_font_min:
                        dist_to_B = ((L_ - hex_to_oklch(base_hex)[0]) ** 2 + (C_ - C_b) ** 2 + (min(abs(dH), 360 - abs(dH)) / 100) ** 2) ** 0.5
                        candidates.append((dist_to_B, hexv, L_, C_, H_, lc_bg, lc_font, clipped))
        candidates.sort(key=lambda x: x[0])
        return candidates[:8]

    light_candidates = search_font_color(Lb, get_hex(Fl_input.value), B, min_lc_vs_bg.value, min_lc_vs_font.value, max_hue_dev.value, chroma_cap.value)
    dark_candidates = search_font_color(Db, get_hex(Fd_input.value), B, min_lc_vs_bg.value, min_lc_vs_font.value, max_hue_dev.value, chroma_cap.value)

    def render_candidates(cands, bg_hex, existing_font_hex, title):
        if not cands:
            return mo.md(f"**{title}**: no candidates satisfy the current thresholds — relax the Lc minimums or chroma cap.")
        rows = []
        for dist, hexv, L_, C_, H_, lc_bg, lc_font, clipped in cands:
            r, g, b = hex_to_rgb255(hexv)
            swatch_html = f'<div style="display:inline-block;width:160px;height:40px;background:{bg_hex};color:{hexv};padding:10px;font-weight:600;border:1px solid #888;border-radius:4px;text-align:center;line-height:20px;">Sample Text</div>'
            info = f"`{hexv}`  |  OKLCH: {L_:.2f}, {C_:.2f}, {H_:.0f}°  |  RGB: {r}, {g}, {b}<br>Lc(bg)={lc_bg:.0f}  |  Lc(font)={lc_font:.0f} {'<span style=\"color:red\">[gamut-clipped]</span>' if clipped else ''}"
            rows.append(mo.hstack([mo.Html(swatch_html), mo.md(info)]))
        return mo.vstack([mo.md(f"**{title}** (against `{bg_hex}` and font `{existing_font_hex}`), sorted by similarity to B:"), *rows])

    mo.vstack([
        render_candidates(light_candidates, Lb, get_hex(Fl_input.value), "Light-side new font color candidates"),
        render_candidates(dark_candidates, Db, get_hex(Fd_input.value), "Dark-side new font color candidates"),
    ])
    return (np,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 3. Three mutually-distinguishable highlight colors

    Same idea, extended to a small combinatorial search: sample candidate hues
    around the color wheel at a fixed, muted chroma and a lightness tuned per
    background, then search for the best **triple** of hues such that:

    - each color clears an APCA floor against **both** the dark and light backgrounds
      (checked as a highlight background under body text, so this floor should be
      modest — think Lc 15–30 non-text visibility, not Lc 90 body-text legibility),
    - all three pairwise hue separations are large (mutual distinguishability),
    - chroma stays under your "muted" ceiling.

    This cell brute-forces hue combinations — replace with a proper optimizer in
    Section 4.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    hl_chroma = mo.ui.slider(0.02, 0.25, value=0.10, step=0.005, show_value=True, label="Highlight chroma (muted)")
    hl_lightness_dark = mo.ui.slider(0.3, 0.9, value=0.55, step=0.01, show_value=True, label="Highlight L on dark bg")
    hl_lightness_light = mo.ui.slider(0.3, 0.9, value=0.72, step=0.01, show_value=True, label="Highlight L on light bg")
    hl_min_lc = mo.ui.slider(5, 60, value=20, step=1, show_value=True, label="Min |Lc| of highlight vs each background")
    hl_min_hue_sep = mo.ui.slider(20, 150, value=70, step=5, show_value=True, label="Min pairwise hue separation (deg)")
    mo.vstack([
        mo.hstack([hl_chroma, hl_min_lc]),
        mo.hstack([hl_lightness_dark, hl_lightness_light]),
        hl_min_hue_sep,
    ])
    return (
        hl_chroma,
        hl_lightness_dark,
        hl_lightness_light,
        hl_min_hue_sep,
        hl_min_lc,
    )


@app.cell(hide_code=True)
def _(
    Db,
    Lb,
    apca_contrast,
    hex_to_rgb255,
    hl_chroma,
    hl_lightness_dark,
    hl_lightness_light,
    hl_min_hue_sep,
    hl_min_lc,
    itertools,
    mo,
    np,
    oklch_to_srgb_hex,
):
    def hue_sep(h1, h2):
        d = abs(h1 - h2) % 360
        return min(d, 360 - d)

    hue_grid = np.linspace(0, 360, 36, endpoint=False)
    db_rgb = hex_to_rgb255(Db)
    lb_rgb = hex_to_rgb255(Lb)

    valid_hues = []
    for h in hue_grid:
        hexv_d, rgb_d, _ = oklch_to_srgb_hex(hl_lightness_dark.value, hl_chroma.value, h)
        hexv_l, rgb_l, _ = oklch_to_srgb_hex(hl_lightness_light.value, hl_chroma.value, h)
        lc_d = apca_contrast(rgb_d, db_rgb)
        lc_l = apca_contrast(rgb_l, lb_rgb)
        if abs(lc_d) >= hl_min_lc.value and abs(lc_l) >= hl_min_lc.value:
            valid_hues.append((h, hexv_d, hexv_l, lc_d, lc_l))

    best_triple = None
    best_score = -1
    for combo in itertools.combinations(valid_hues, 3):
        hues = [c[0] for c in combo]
        seps = [hue_sep(a, b) for a, b in itertools.combinations(hues, 2)]
        if min(seps) >= hl_min_hue_sep.value:
            score = min(seps)
            if score > best_score:
                best_score = score
                best_triple = combo

    if best_triple is None:
        triple_result = mo.md(
            "No valid triple found under current constraints — try lowering "
            "**min hue separation** or **min Lc**, or raising chroma."
        )
    else:
        rows = []
        for h, hexv_d, hexv_l, lc_d, lc_l in best_triple:
            r_d, g_d, b_d = hex_to_rgb255(hexv_d)
            r_l, g_l, b_l = hex_to_rgb255(hexv_l)
            swatch_d = f'<div style="display:inline-block;width:120px;height:36px;background:{Db};color:{hexv_d};padding:8px;font-weight:600;border:1px solid #888;border-radius:4px;text-align:center;">Highlight</div>'
            swatch_l = f'<div style="display:inline-block;width:120px;height:36px;background:{Lb};color:{hexv_l};padding:8px;font-weight:600;border:1px solid #888;border-radius:4px;text-align:center;">Highlight</div>'
            info_d = f"`{hexv_d}` | RGB: {r_d}, {g_d}, {b_d} | Lc={lc_d:.0f}"
            info_l = f"`{hexv_l}` | RGB: {r_l}, {g_l}, {b_l} | Lc={lc_l:.0f}"

            rows.append(mo.hstack([
                mo.md(f"**H={h:.0f}°**"),
                mo.vstack([
                    mo.hstack([mo.Html(swatch_d), mo.md(f"Dark: {info_d}")]),
                    mo.hstack([mo.Html(swatch_l), mo.md(f"Light: {info_l}")])
                ])
            ]))
        triple_result = mo.vstack([
            mo.md(f"**Best triple** (min pairwise hue separation = {best_score:.0f}°):"),
            *rows,
        ])

    triple_result
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 4. Where to take this next (formal optimization)

    This notebook uses brute-force grid search / combinations, which is fine for
    exploration but doesn't scale well past 3–4 colors or finer grids. To turn
    this into a proper optimizer:

    - **Decision variables**: for Section 2, `(L, C, H)` per font color (2 colors);
      for Section 3, `(H1, H2, H3)` at fixed/shared `(L, C)` per background, or all
      9 values free.
    - **Objective**: maximize a soft combination of (min pairwise hue separation)
      and (margin above each APCA floor), e.g.
      `score = min(hue_seps) + lambda * min(0, Lc_i - Lc_floor)` summed over
      constraints, so the optimizer is rewarded for clearing floors comfortably,
      not just barely.
    - **Hard constraints**: APCA floors, chroma ceiling, gamut validity (reject or
      penalize any candidate that required heavy gamut clipping — track the
      `clipped` flag already returned by `oklch_to_srgb_hex`).
    - **Method**: since APCA and OKLCH→sRGB are nonlinear/non-smooth (due to
      `sign()` branches and gamut clipping), gradient-based methods need care.
      Practical options:
        - `scipy.optimize.differential_evolution` (derivative-free, handles
          nonsmooth constraints well) over the packed vector of all `(L, C, H)`
          tuples with penalty terms for constraint violations.
        - `scipy.optimize.minimize(method="Nelder-Mead")` for local refinement
          once you have a good grid-search starting point (e.g. `best_triple`
          above) — cheap and works without gradients.
        - `cma` (CMA-ES) if you want a more robust global search for 6–9 free
          parameters.
    - **Validation loop**: after optimizing, re-render swatches and re-check APCA
      both ways (`apca_contrast(fg, bg)` is *not* symmetric — always check the
      actual foreground/background pairing you'll ship), and eyeball them, since
      "mutually distinguishable" for color-vision-deficient users is only partly
      captured by hue separation in OKLCH.
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 5. Interactive OKLCH Color Inspector & Studio
    Fine-tune colors manually using OKLCH sliders and see their conversion and APCA contrasts in real time.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    studio_L = mo.ui.slider(0.0, 1.0, value=0.75, step=0.01, show_value=True, label="Lightness (L)")
    studio_C = mo.ui.slider(0.0, 0.4, value=0.15, step=0.01, show_value=True, label="Chroma (C)")
    studio_H = mo.ui.slider(0, 360, value=250, step=1, show_value=True, label="Hue (H°)")

    mo.vstack([
        mo.md("### OKLCH Sliders"),
        studio_L, studio_C, studio_H
    ])
    return studio_C, studio_H, studio_L


@app.cell(hide_code=True)
def _(
    Db,
    Lb,
    apca_contrast,
    hex_to_rgb255,
    mo,
    oklch_to_srgb_hex,
    studio_C,
    studio_H,
    studio_L,
    swatch,
):
    hex_val, rgb255, was_clipped = oklch_to_srgb_hex(studio_L.value, studio_C.value, studio_H.value, clip=True)
    r, g, b = rgb255

    lc_vs_db = apca_contrast(rgb255, hex_to_rgb255(Db))
    lc_vs_lb = apca_contrast(rgb255, hex_to_rgb255(Lb))

    clip_warning = mo.md("**⚠️ Out of sRGB Gamut (Clipped)**").callout(kind="warn") if was_clipped else mo.md("*(In Gamut)*")

    mo.hstack([
        mo.vstack([
            mo.md("### Resulting Color"),
            swatch(hex_val, 200, 100),
            clip_warning
        ]),
        mo.vstack([
            mo.md("### Color Numbers"),
            mo.md(f"**Hex:** `{hex_val}`"),
            mo.md(f"**RGB:** `{r}, {g}, {b}`"),
            mo.md(f"**OKLCH:** `L={studio_L.value:.2f}, C={studio_C.value:.2f}, H={studio_H.value:.0f}°`"),
            mo.md("### Contrast (APCA Lc)"),
            mo.md(f"Vs Dark Background (`{Db}`): **{lc_vs_db:.0f}**"),
            mo.md(f"Vs Light Background (`{Lb}`): **{lc_vs_lb:.0f}**"),
        ])
    ])
    return


if __name__ == "__main__":
    app.run()
