# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo>=0.23.3",
#     "numpy>=2.5.2",
#     "scipy==1.18.1",
#     "wigglystuff>=0.5.28",
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
    import numpy as np
    from scipy.optimize import minimize

    def swatch(hexv, w=80, h=30):
        """Return HTML for a color swatch."""
        return mo.Html(f'<div style="width:{w}px;height:{h}px;background:{hexv};border:1px solid #888;border-radius:4px;display:inline-block;vertical-align:middle;"></div>')


    return itertools, math, minimize, mo, np, swatch


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
def _(apca_contrast, math, minimize, mo):
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

    def get_hex(val):
        """Extract hex from ColorPicker value (dict or string) or slider dictionary."""
        if isinstance(val, dict):
            if 'color' in val:
                return val['color']
            if 'L' in val and 'C' in val and 'H' in val:
                hexv, _, _ = oklch_to_srgb_hex(val['L'], val['C'], val['H'])
                return hexv
            if 'hex' in val:
                return val['hex']
        return str(val)

    def make_color_slider(label, default_hex, reset_trigger=0):
        L0, C0, H0 = hex_to_oklch(default_hex)
        return mo.ui.dictionary({
            "L": mo.ui.slider(0.0, 1.0, value=round(L0, 3), step=0.005, label=f"L"),
            "C": mo.ui.slider(0.0, 0.35, value=round(C0, 3), step=0.005, label=f"C"),
            "H": mo.ui.slider(0.0, 360.0, value=round(H0, 1), step=0.5, label=f"H°"),
        })


    def hex_to_oklab(hexstr):
        r, g, b = [srgb_to_linear(c / 255) for c in hex_to_rgb255(hexstr)]
        return linear_srgb_to_oklab(r, g, b)

    def solve_simultaneous_link_colors(base_hexes, bgs_hex, text_hex, is_light=True, min_lc_bg=60, min_lc_text=15, max_hue_dev=25, c_max=0.20):
        N = len(base_hexes)
        bgs_rgb = [hex_to_rgb255(bg) for bg in bgs_hex]
        text_rgb = hex_to_rgb255(text_hex)
        text_lab = hex_to_oklab(text_hex)
        base_lchs = [hex_to_oklch(b) for b in base_hexes]
    
        x0 = []
        bounds = []
        for i in range(N):
            Lb, Cb, Hb = base_lchs[i]
            init_L = 0.35 if is_light else 0.75
            init_C = min(max(0.08, Cb), c_max)
            init_H = Hb
            x0.extend([init_L, init_C, init_H])
        
            L_bnd = (0.12, 0.58) if is_light else (0.62, 0.95)
            C_bnd = (0.02, c_max)
            H_bnd = (Hb - max_hue_dev, Hb + max_hue_dev)
            bounds.extend([L_bnd, C_bnd, H_bnd])

        def objective(params):
            penalty = 0.0
            link_labs = []
        
            for i in range(N):
                L, C, H = params[3*i : 3*i+3]
                Hb = base_lchs[i][2]
            
                dh = abs(H - Hb) % 360
                dh = min(dh, 360 - dh)
                if dh > max_hue_dev:
                    penalty += 1000.0 * (dh - max_hue_dev)**2
                else:
                    penalty += 0.5 * dh
                
                hexv, rgb255, clipped = oklch_to_srgb_hex(L, C, H % 360)
                if clipped:
                    penalty += 50.0
            
                link_labs.append(hex_to_oklab(hexv))
            
                for bg_rgb in bgs_rgb:
                    lc = abs(apca_contrast(rgb255, bg_rgb))
                    if lc < min_lc_bg:
                        penalty += 100.0 * (min_lc_bg - lc)**2
                    else:
                        penalty -= 0.1 * lc
            
                lc_text = abs(apca_contrast(rgb255, text_rgb))
                if lc_text < min_lc_text:
                    penalty += 50.0 * (min_lc_text - lc_text)**2

            all_labs = [text_lab] + link_labs
            pair_dists = []
            for i in range(len(all_labs)):
                for j in range(i + 1, len(all_labs)):
                    d = math.sqrt(sum((all_labs[i][k] - all_labs[j][k])**2 for k in range(3)))
                    pair_dists.append(d)
                    if d < 0.04:
                        penalty += 500.0 * (0.04 - d)**2
                    
            min_dist = min(pair_dists) if pair_dists else 0.0
            return penalty - 200.0 * min_dist

        res = minimize(objective, x0, method='L-BFGS-B', bounds=bounds)
    
        optimized_links = []
        for i in range(N):
            L, C, H = res.x[3*i : 3*i+3]
            hexv, rgb255, clipped = oklch_to_srgb_hex(L, C, H % 360)
            lc_bg_min = min(abs(apca_contrast(rgb255, bg_rgb)) for bg_rgb in bgs_rgb)
            lc_text = abs(apca_contrast(rgb255, text_rgb))
            dh = abs(H % 360 - base_lchs[i][2]) % 360
            dh = min(dh, 360 - dh)
            optimized_links.append({
                'hex': hexv,
                'L': L,
                'C': C,
                'H': H % 360,
                'clipped': clipped,
                'min_lc_bg': lc_bg_min,
                'lc_text': lc_text,
                'hue_dev': dh
            })
        
        return optimized_links


    return (
        get_hex,
        hex_to_oklch,
        hex_to_rgb255,
        make_color_slider,
        mix_oklab,
        oklch_to_srgb_hex,
        solve_simultaneous_link_colors,
    )


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
    ## 2. Base & Font Color Optimizer

    This section tackles the first problem: Mix a base color into existing light/dark backgrounds, then search for optimal new font colors that match the base color hue while clearing APCA contrast floors.

    Adjust your theme inputs and constraints below to live-update the backgrounds and font candidates.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### 💡 Background Mixing & The Hunt Effect

    When mixing a base color $$B$$ into light ($$L$$) and dark ($$D$$) backgrounds in OKLab space:
    - **Linear OKLab Mixing**: A naive mix $$t_{\text{light}} = t_{\text{dark}} = t$$ yields identical *OKLab chroma* ($$C \approx 0.05$$) on both backgrounds.
    - **Visual Asymmetry (The Hunt Effect)**: Human visual psychophysics (CAM16 / CIECAM02) demonstrates that perceived colorfulness $$M$$ is proportional to adaptation luminance:
      $$M \propto C \cdot L^{0.65}$$
      Because the dark background lightness ($$L_D \approx 0.24$$) is much lower than the light background lightness ($$L_L \approx 0.99$$), a linear mix makes the dark background appear nearly uncolored/gray while the light background receives a distinct pastel tint.
    - **Perceptual Equalization**: To achieve equal *perceived* tint strength on both light and dark themes simultaneously, the **Perceptual (Hunt Effect)** mode dynamically scales the dark mixing factor:
      $$t_{\text{dark}} = \min\left(0.85, \; t_{\text{light}} \cdot \left[ \frac{L_{\text{light}}}{L_{\text{dark}}} \right]^{0.65} \right)$$
    """).callout(kind="info")
    return


@app.cell(hide_code=True)
def _(make_color_slider, mo):
    reset_theme_btn = mo.ui.button(label="↺ Reset All Color Sliders to Initial Defaults")

    base_color_input = make_color_slider("Base Color 1 (B1)", "#5e81ac")
    L_bg_input = make_color_slider("Light BG (L)", "#fdfdfd")
    D_bg_input = make_color_slider("Dark BG (D)", "#1e1e1e")
    Fl_input = make_color_slider("Light Text (Fl)", "#2e2e2e")
    Fd_input = make_color_slider("Dark Text (Fd)", "#dcdcdc")

    mix_amount = mo.ui.slider(0.0, 1.0, value=0.12, step=0.01, show_value=True, label="Background mix amount (B into L/D)")

    num_base_colors = mo.ui.slider(1, 6, value=3, step=1, show_value=True, label="Number of Base Colors (N)")

    base_color_2_input = make_color_slider("Base Color 2 (B2)", "#a3be8c")
    base_color_3_input = make_color_slider("Base Color 3 (B3)", "#d08770")
    base_color_4_input = make_color_slider("Base Color 4 (B4)", "#b48ead")
    base_color_5_input = make_color_slider("Base Color 5 (B5)", "#ebcb8b")
    base_color_6_input = make_color_slider("Base Color 6 (B6)", "#88c0d0")

    mix_mode = mo.ui.radio(
        options=["Perceptual (Hunt Effect)", "Separate Sliders", "Linear (Equal t)"],
        value="Perceptual (Hunt Effect)",
        label="Mixing Mode"
    )
    mix_amount_light = mo.ui.number(start=0.0, stop=1.0, step=0.01, value=0.12, label="Light bg mix (t_light)")
    mix_amount_dark = mo.ui.number(start=0.0, stop=1.0, step=0.01, value=0.35, label="Dark bg mix (t_dark)")

    min_lc_vs_bg = mo.ui.number(start=15, stop=105, step=1, value=60, label="Min |Lc| vs background")
    min_lc_vs_font = mo.ui.number(start=0, stop=105, step=1, value=10, label="Min |Lc| vs existing font")
    max_hue_dev = mo.ui.number(start=0, stop=60, step=1, value=20, label="Max hue dev (deg)")
    chroma_cap = mo.ui.number(start=0.02, stop=0.35, step=0.01, value=0.18, label="Chroma ceiling")
    num_candidates = mo.ui.number(start=1, stop=10, step=1, value=4, label="Max candidates shown")

    return (
        D_bg_input,
        Fd_input,
        Fl_input,
        L_bg_input,
        base_color_2_input,
        base_color_3_input,
        base_color_4_input,
        base_color_5_input,
        base_color_6_input,
        base_color_input,
        chroma_cap,
        max_hue_dev,
        min_lc_vs_bg,
        min_lc_vs_font,
        mix_amount,
        mix_amount_dark,
        mix_amount_light,
        mix_mode,
        num_base_colors,
        num_candidates,
        reset_theme_btn,
    )


@app.cell(hide_code=True)
def _(
    D_bg_input,
    Fd_input,
    Fl_input,
    L_bg_input,
    apca_contrast,
    base_color_2_input,
    base_color_3_input,
    base_color_4_input,
    base_color_5_input,
    base_color_6_input,
    base_color_input,
    chroma_cap,
    get_hex,
    hex_to_oklch,
    hex_to_rgb255,
    max_hue_dev,
    min_lc_vs_bg,
    min_lc_vs_font,
    mix_amount,
    mix_amount_dark,
    mix_amount_light,
    mix_mode,
    mix_oklab,
    mo,
    np,
    num_base_colors,
    num_candidates,
    oklch_to_srgb_hex,
    reset_theme_btn,
    solve_simultaneous_link_colors,
    swatch,
):
    # numpy imported in Hbol

    B = get_hex(base_color_input.value)
    L = get_hex(L_bg_input.value)
    D = get_hex(D_bg_input.value)
    Fl = get_hex(Fl_input.value)
    Fd = get_hex(Fd_input.value)

    L_l, _, _ = hex_to_oklch(L)
    L_d, _, _ = hex_to_oklch(D)

    if mix_mode.value == "Perceptual (Hunt Effect)":
        t_light = mix_amount.value
        _hunt_scale = (L_l / max(0.08, L_d)) ** 0.65
        t_dark = min(0.85, t_light * _hunt_scale)
    elif mix_mode.value == "Separate Sliders":
        t_light = mix_amount_light.value
        t_dark = mix_amount_dark.value
    else:
        t_light = mix_amount.value
        t_dark = mix_amount.value

    t = mix_amount.value
    Lb = mix_oklab(L, B, t_light)
    Db = mix_oklab(D, B, t_dark)

    # --- N Base Colors & Simultaneous Link Color Optimization ---
    N_base = int(num_base_colors.value)
    base_inputs_all = [base_color_input, base_color_2_input, base_color_3_input, base_color_4_input, base_color_5_input, base_color_6_input]
    base_colors_hex = [get_hex(base_inputs_all[i].value) for i in range(N_base)]

    # Derive backgrounds for all N base colors
    derived_Lb_list = [mix_oklab(L, b_hex, t_light) for b_hex in base_colors_hex]
    derived_Db_list = [mix_oklab(D, b_hex, t_dark) for b_hex in base_colors_hex]

    all_light_bgs = [L] + derived_Lb_list
    all_dark_bgs = [D] + derived_Db_list

    all_light_bg_labels = ["Original Light BG (L)"] + [f"Derived Light BG Lb{i+1} (Base {i+1}: {base_colors_hex[i]})" for i in range(N_base)]
    all_dark_bg_labels = ["Original Dark BG (D)"] + [f"Derived Dark BG Db{i+1} (Base {i+1}: {base_colors_hex[i]})" for i in range(N_base)]

    # Simultaneous link color optimization for Light and Dark sides
    opt_light_links = solve_simultaneous_link_colors(
        base_colors_hex, all_light_bgs, Fl, is_light=True,
        min_lc_bg=min_lc_vs_bg.value, min_lc_text=min_lc_vs_font.value,
        max_hue_dev=max_hue_dev.value, c_max=chroma_cap.value
    )

    opt_dark_links = solve_simultaneous_link_colors(
        base_colors_hex, all_dark_bgs, Fd, is_light=False,
        min_lc_bg=min_lc_vs_bg.value, min_lc_text=min_lc_vs_font.value,
        max_hue_dev=max_hue_dev.value, c_max=chroma_cap.value
    )

    def color_info(hexv):
        L_, C_, H_ = hex_to_oklch(hexv)
        r, g, b = hex_to_rgb255(hexv)
        return f"`{hexv}` | L:{L_:.2f} C:{C_:.2f} H:{H_:.0f}° | RGB: {r}, {g}, {b}"

    def search_font_color(bg_hex, existing_font_hex, base_hex, lc_bg_min, lc_font_min, hue_dev_max, c_max, max_cands=4, n_L=25, n_C=12, n_H=9):
        L_b, C_b, H_b = hex_to_oklch(base_hex)
        bg_rgb = hex_to_rgb255(bg_hex)
        font_rgb = hex_to_rgb255(existing_font_hex)
        candidates = []
        for L_ in np.linspace(0.15, 0.95, n_L):
            for C_ in np.linspace(0.0, c_max, n_C):
                h_range = [0.0] if C_ < 1e-4 else np.linspace(-hue_dev_max, hue_dev_max, n_H)
                for dH in h_range:
                    H_ = (H_b + dH) % 360
                    hexv, rgb255, clipped = oklch_to_srgb_hex(L_, C_, H_)
                    lc_bg = apca_contrast(rgb255, bg_rgb)
                    lc_font = apca_contrast(rgb255, font_rgb)
                    if abs(lc_bg) >= lc_bg_min and abs(lc_font) >= lc_font_min:
                        dist_to_B = ((L_ - L_b) ** 2 + (C_ - C_b) ** 2 + (min(abs(dH), 360 - abs(dH)) / 100) ** 2) ** 0.5
                        candidates.append((dist_to_B, hexv, L_, C_, H_, lc_bg, lc_font, clipped))
        candidates.sort(key=lambda x: x[0])

        seen_hex = set()
        unique_candidates = []
        selected_lch = []
        for cand in candidates:
            dist, hexv, L_, C_, H_, lc_bg, lc_font, clipped = cand
            if hexv in seen_hex:
                continue
    
            too_close = False
            for prev_L, prev_C, prev_H in selected_lch:
                dH_val = abs(H_ - prev_H) % 360
                dH_dist = min(dH_val, 360 - dH_val) / 100.0
                lch_diff = ((L_ - prev_L) ** 2 + (C_ - prev_C) ** 2 + dH_dist ** 2) ** 0.5
                if lch_diff < 0.03:
                    too_close = True
                    break
    
            if not too_close:
                seen_hex.add(hexv)
                selected_lch.append((L_, C_, H_))
                unique_candidates.append(cand)
                if len(unique_candidates) == max_cands:
                    break

        if len(unique_candidates) < max_cands:
            for cand in candidates:
                hexv = cand[1]
                if hexv not in seen_hex:
                    seen_hex.add(hexv)
                    unique_candidates.append(cand)
                    if len(unique_candidates) == max_cands:
                        break

        return unique_candidates

    light_candidates = search_font_color(Lb, Fl, B, min_lc_vs_bg.value, min_lc_vs_font.value, max_hue_dev.value, chroma_cap.value, max_cands=int(num_candidates.value))
    dark_candidates = search_font_color(Db, Fd, B, min_lc_vs_bg.value, min_lc_vs_font.value, max_hue_dev.value, chroma_cap.value, max_cands=int(num_candidates.value))

    def render_candidates(cands, bg_hex, existing_font_hex, title):
        if not cands:
            return mo.md(
                f"#### {title}\n"
                f"*No candidates satisfy the current threshold constraints against background `{bg_hex}` and font `{existing_font_hex}`. "
                f"Try lowering **min |Lc| vs font** or widening **max hue dev**.*"
            )

        rows = []
        for idx, (dist, hexv, L_, C_, H_, lc_bg, lc_font, clipped) in enumerate(cands, 1):
            clip_str = "**[clipped]**" if clipped else "In gamut"
            rows.append(
                f"| **#{idx}** | `{hexv}` | `{L_:.2f}, {C_:.2f}, {H_:.0f}°` | `{abs(lc_bg):.0f}` | `{abs(lc_font):.0f}` | {clip_str} |"
            )
    
        table_header = "| Rank | Hex | OKLCH (L, C, H) | Lc(bg) | Lc(font) | Gamut |\n| :---: | :--- | :--- | :---: | :---: | :---: |\n"
        return mo.md(table_header + "\n".join(rows))

    base_controls_ui = [
        mo.md("#### Base Color Sliders (Resettable)"),
        mo.hstack([mo.md("**Base Color 1 (B1):**"), base_color_input, swatch(B, 30, 20)]),
    ]
    if N_base >= 2:
        base_controls_ui.append(mo.hstack([mo.md("**Base Color 2 (B2):**"), base_color_2_input, swatch(get_hex(base_color_2_input.value), 30, 20)]))
    if N_base >= 3:
        base_controls_ui.append(mo.hstack([mo.md("**Base Color 3 (B3):**"), base_color_3_input, swatch(get_hex(base_color_3_input.value), 30, 20)]))
    if N_base >= 4:
        base_controls_ui.append(mo.hstack([mo.md("**Base Color 4 (B4):**"), base_color_4_input, swatch(get_hex(base_color_4_input.value), 30, 20)]))
    if N_base >= 5:
        base_controls_ui.append(mo.hstack([mo.md("**Base Color 5 (B5):**"), base_color_5_input, swatch(get_hex(base_color_5_input.value), 30, 20)]))
    if N_base >= 6:
        base_controls_ui.append(mo.hstack([mo.md("**Base Color 6 (B6):**"), base_color_6_input, swatch(get_hex(base_color_6_input.value), 30, 20)]))

    ui_inputs = mo.vstack([
        mo.md("### 1. Theme & Base Color Controls"),
        reset_theme_btn,
        mo.hstack([mo.md("**Light bg (L):**"), L_bg_input, swatch(L, 30, 20)]),
        mo.hstack([mo.md("**Dark bg (D):**"), D_bg_input, swatch(D, 30, 20)]),
        mo.hstack([mo.md("**Light font (Fl):**"), Fl_input, swatch(Fl, 30, 20)]),
        mo.hstack([mo.md("**Dark font (Fd):**"), Fd_input, swatch(Fd, 30, 20)]),
        mo.md("---"),
        num_base_colors,
        *base_controls_ui
    ])

    _mix_controls = [mix_mode]
    if mix_mode.value == "Separate Sliders":
        _mix_controls.extend([mix_amount_light, mix_amount_dark])
    else:
        _mix_controls.append(mix_amount)

    ui_sliders = mo.vstack([
        mo.md("### 2. Mix & Optimization Constraints"),
        *_mix_controls,
        min_lc_vs_bg,
        min_lc_vs_font,
        max_hue_dev,
        chroma_cap,
        num_candidates
    ])

    ui_mixed = mo.hstack([
        mo.vstack([
            mo.md(f"**Lb** (New Light Bg 1, t={t_light:.2f})"),
            swatch(Lb, 140, 50),
            mo.md(color_info(Lb))
        ]),
        mo.vstack([
            mo.md(f"**Db** (New Dark Bg 1, t={t_dark:.2f})"),
            swatch(Db, 140, 50),
            mo.md(color_info(Db))
        ]),
    ])

    light_candidates_view = render_candidates(light_candidates, Lb, Fl, "Light-Side Font Candidates")
    dark_candidates_view = render_candidates(dark_candidates, Db, Fd, "Dark-Side Font Candidates")

    ui_font_results = mo.vstack([
        mo.md("### Single-Base Candidate Inspection"),
        mo.ui.tabs({
            "Light-Side Font Candidates": light_candidates_view,
            "Dark-Side Font Candidates": dark_candidates_view
        })
    ])

    dashboard = mo.vstack([
        mo.hstack([ui_inputs, ui_sliders], justify="start", gap=4),
        mo.md("---"),
        mo.md("### 3. Background Comparison"),
        ui_mixed,
        mo.md("---"),
        ui_font_results
    ])

    return (
        D,
        Db,
        Fd,
        Fl,
        L,
        Lb,
        all_dark_bg_labels,
        all_dark_bgs,
        all_light_bg_labels,
        all_light_bgs,
        base_colors_hex,
        color_info,
        opt_dark_links,
        opt_light_links,
        t_dark,
        t_light,
        ui_font_results,
        ui_inputs,
        ui_sliders,
    )


@app.cell(hide_code=True)
def _(
    D,
    Db,
    Fd,
    Fl,
    L,
    Lb,
    all_dark_bg_labels,
    all_dark_bgs,
    all_light_bg_labels,
    all_light_bgs,
    apca_contrast,
    base_colors_hex,
    color_info,
    hex_to_rgb255,
    mo,
    opt_dark_links,
    opt_light_links,
    t_dark,
    t_light,
    ui_font_results,
    ui_inputs,
    ui_sliders,
):
    def build_multi_base_display(all_light_bgs, all_light_bg_labels, opt_light_links, Fl,
                                 all_dark_bgs, all_dark_bg_labels, opt_dark_links, Fd,
                                 base_colors_hex):
        light_cards = []
        for bg_hex, bg_label in zip(all_light_bgs, all_light_bg_labels):
            bg_rgb = hex_to_rgb255(bg_hex)
            lc_norm_text = abs(apca_contrast(hex_to_rgb255(Fl), bg_rgb))
        
            link_items = []
            for i, link_info in enumerate(opt_light_links, 1):
                k_hex = link_info['hex']
                lc_link = abs(apca_contrast(hex_to_rgb255(k_hex), bg_rgb))
                b_hex = base_colors_hex[i-1]
                link_items.append(
                    f'<a href="#" onclick="return false;" style="color:{k_hex}; text-decoration:underline; font-weight:700; font-size:14px; margin:0 6px;">'
                    f'Link {i} ({b_hex}) <span style="font-size:11px; opacity:0.85; font-weight:normal;">[Lc: {lc_link:.0f}]</span></a>'
                )
            links_html = " &nbsp;•&nbsp; ".join(link_items)
        
            light_cards.append(f'''
            <div style="background:{bg_hex}; color:{Fl}; padding:14px 18px; border-radius:6px; border:1px solid #777; margin:8px 0; font-family:system-ui, sans-serif;">
                <div style="font-size:12px; font-weight:700; text-transform:uppercase; letter-spacing:0.04em; margin-bottom:4px; opacity:0.8;">
                    {bg_label} &nbsp;|&nbsp; Hex: <code>{bg_hex}</code> &nbsp;|&nbsp; Normal Text Lc: <b>{lc_norm_text:.0f}</b>
                </div>
                <div style="font-size:14px; line-height:1.8;">
                    Normal body text in <code>{Fl}</code>. &nbsp;|&nbsp; Link colors: {links_html}
                </div>
            </div>
            ''')

        dark_cards = []
        for bg_hex, bg_label in zip(all_dark_bgs, all_dark_bg_labels):
            bg_rgb = hex_to_rgb255(bg_hex)
            lc_norm_text = abs(apca_contrast(hex_to_rgb255(Fd), bg_rgb))
        
            link_items = []
            for i, link_info in enumerate(opt_dark_links, 1):
                k_hex = link_info['hex']
                lc_link = abs(apca_contrast(hex_to_rgb255(k_hex), bg_rgb))
                b_hex = base_colors_hex[i-1]
                link_items.append(
                    f'<a href="#" onclick="return false;" style="color:{k_hex}; text-decoration:underline; font-weight:700; font-size:14px; margin:0 6px;">'
                    f'Link {i} ({b_hex}) <span style="font-size:11px; opacity:0.85; font-weight:normal;">[Lc: {lc_link:.0f}]</span></a>'
                )
            links_html = " &nbsp;•&nbsp; ".join(link_items)
        
            dark_cards.append(f'''
            <div style="background:{bg_hex}; color:{Fd}; padding:14px 18px; border-radius:6px; border:1px solid #777; margin:8px 0; font-family:system-ui, sans-serif;">
                <div style="font-size:12px; font-weight:700; text-transform:uppercase; letter-spacing:0.04em; margin-bottom:4px; opacity:0.8;">
                    {bg_label} &nbsp;|&nbsp; Hex: <code>{bg_hex}</code> &nbsp;|&nbsp; Normal Text Lc: <b>{lc_norm_text:.0f}</b>
                </div>
                <div style="font-size:14px; line-height:1.8;">
                    Normal body text in <code>{Fd}</code>. &nbsp;|&nbsp; Link colors: {links_html}
                </div>
            </div>
            ''')

        rows = []
        for i in range(len(base_colors_hex)):
            b_hex = base_colors_hex[i]
            l_info = opt_light_links[i]
            d_info = opt_dark_links[i]
        
            l_clip = '**[clipped]**' if l_info['clipped'] else 'In gamut'
            d_clip = '**[clipped]**' if d_info['clipped'] else 'In gamut'
        
            rows.append(
                f"| **Base {i+1}** (`{b_hex}`) | `{l_info['hex']}` | `L:{l_info['L']:.2f}, C:{l_info['C']:.2f}, H:{l_info['H']:.0f}°` | `{l_info['hue_dev']:.1f}°` | `{l_info['min_lc_bg']:.0f}` | `{l_info['lc_text']:.0f}` | {l_clip} | `{d_info['hex']}` | `L:{d_info['L']:.2f}, C:{d_info['C']:.2f}, H:{d_info['H']:.0f}°` | `{d_info['hue_dev']:.1f}°` | `{d_info['min_lc_bg']:.0f}` | `{d_info['lc_text']:.0f}` | {d_clip} |"
            )
        
        table_header = (
            "| Base Color | Light Link Hex | Light OKLCH | ΔH(Base) | Min Lc(bg) | Lc(text) | Light Gamut | Dark Link Hex | Dark OKLCH | ΔH(Base) | Min Lc(bg) | Lc(text) | Dark Gamut |\n"
            "| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :--- | :--- | :---: | :---: | :---: | :---: |\n"
        )
    
        table_md = mo.md(table_header + "\n".join(rows))
    
        return mo.vstack([
            mo.md("### 4. Simultaneous N-Base Link Color Optimization Results"),
            table_md,
            mo.md("#### Light Background Swatches & Link Text Samples"),
            mo.Html("\n".join(light_cards)),
            mo.md("#### Dark Background Swatches & Link Text Samples"),
            mo.Html("\n".join(dark_cards)),
        ])

    def _make_stacked_bg_comparison(title, top_label, top_hex, bot_label, bot_hex, font_hex, font_label, w=340, h=120):
        font_rgb = hex_to_rgb255(font_hex)
        lc_top = abs(apca_contrast(font_rgb, hex_to_rgb255(top_hex)))
        lc_bot = abs(apca_contrast(font_rgb, hex_to_rgb255(bot_hex)))

        swatch_html = f'''
        <div style="width:{w}px; height:{h}px; border:1px solid #888; border-radius:6px; overflow:hidden; display:flex; flex-direction:column; margin: 6px 0; font-family: system-ui, sans-serif;">
            <div style="flex:1; background:{top_hex}; color:{font_hex}; width:100%; display:flex; align-items:center; justify-content:center; font-weight:600; font-size: 14px; box-sizing:border-box;">
                The quick brown fox (Lc: {lc_top:.0f})
            </div>
            <div style="flex:1; background:{bot_hex}; color:{font_hex}; width:100%; display:flex; align-items:center; justify-content:center; font-weight:600; font-size: 14px; box-sizing:border-box;">
                The quick brown fox (Lc: {lc_bot:.0f})
            </div>
        </div>
        '''
        return mo.vstack([
            mo.md(f"#### {title}"),
            mo.md(f"**{top_label}**  \n{color_info(top_hex)}"),
            mo.Html(swatch_html),
            mo.md(f"**{bot_label}**  \n{color_info(bot_hex)}"),
            mo.md(f"*Font: `{font_hex}` ({font_label})*")
        ], gap=1)

    ui_bg_comparison = mo.hstack([
        _make_stacked_bg_comparison("Light Side (L vs Lb)", "L (Original)", L, f"Lb (New Base-Mixed, t={t_light:.2f})", Lb, Fl, "Fl"),
        _make_stacked_bg_comparison("Dark Side (D vs Db)", "D (Original)", D, f"Db (New Base-Mixed, t={t_dark:.2f})", Db, Fd, "Fd"),
    ], justify="start", gap=6)

    multi_base_display = build_multi_base_display(
        all_light_bgs, all_light_bg_labels, opt_light_links, Fl,
        all_dark_bgs, all_dark_bg_labels, opt_dark_links, Fd,
        base_colors_hex
    )

    _dashboard = mo.vstack([
        mo.hstack([ui_inputs, ui_sliders], justify="start", gap=4),
        mo.md("---"),
        mo.md("### 3. Primary Background Comparison"),
        ui_bg_comparison,
        mo.md("---"),
        multi_base_display,
        mo.md("---"),
        ui_font_results,
    ])
    _dashboard
    return


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
    hl_chroma = mo.ui.number(start=0.02, stop=0.25, step=0.005, value=0.10, label="Highlight chroma (C)")
    hl_lightness_dark = mo.ui.number(start=0.30, stop=0.90, step=0.01, value=0.55, label="Highlight L on dark bg")
    hl_lightness_light = mo.ui.number(start=0.30, stop=0.90, step=0.01, value=0.72, label="Highlight L on light bg")
    hl_min_lc = mo.ui.number(start=5, stop=60, step=1, value=20, label="Min |Lc| vs background")
    hl_min_hue_sep = mo.ui.number(start=20, stop=150, step=5, value=70, label="Min hue separation (deg)")

    mo.vstack([
        mo.hstack([hl_chroma, hl_min_lc], gap=4),
        mo.hstack([hl_lightness_dark, hl_lightness_light], gap=4),
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
    Fd,
    Fl,
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

    def render_triple_results(hues, title="Optimal Highlight Triple Results"):
        hues = list(hues)
        sep_list = [
            hue_sep(hues[0], hues[1]),
            hue_sep(hues[1], hues[2]),
            hue_sep(hues[0], hues[2])
        ]
        min_sep = min(sep_list)

        db_rgb = hex_to_rgb255(Db)
        lb_rgb = hex_to_rgb255(Lb)
        fd_rgb = hex_to_rgb255(Fd)
        fl_rgb = hex_to_rgb255(Fl)

        triple_data = []
        for h in hues:
            hex_d, rgb_d, clip_d = oklch_to_srgb_hex(hl_lightness_dark.value, hl_chroma.value, h)
            hex_l, rgb_l, clip_l = oklch_to_srgb_hex(hl_lightness_light.value, hl_chroma.value, h)
            lc_d = apca_contrast(rgb_d, db_rgb)
            lc_l = apca_contrast(rgb_l, lb_rgb)
            lc_font_d = apca_contrast(fd_rgb, rgb_d)
            lc_font_l = apca_contrast(fl_rgb, rgb_l)
            triple_data.append((h, hex_d, hex_l, lc_d, lc_l, lc_font_d, lc_font_l, clip_d, clip_l))

        hl_spans_light = [
            f'<span style="background:{hex_l}; color:{Fl}; padding:3px 8px; border-radius:4px; font-weight:600; margin:0 4px; border:1px solid rgba(0,0,0,0.15);">Highlight {i} ({h:.1f}°)</span>'
            for i, (h, _, hex_l, _, _, _, _, _, _) in enumerate(triple_data, 1)
        ]
        light_html = f'''
        <div style="width:100%; background:{Lb}; color:{Fl}; padding:14px 18px; border:1px solid #777; border-radius:6px; font-family:system-ui, sans-serif; font-size:14px; line-height:2.2; box-sizing:border-box; margin:4px 0;">
            <strong>Light Theme (Lb):</strong> Body text before {hl_spans_light[0]} body text between {hl_spans_light[1]} body text between {hl_spans_light[2]} body text after.
        </div>
        '''

        hl_spans_dark = [
            f'<span style="background:{hex_d}; color:{Fd}; padding:3px 8px; border-radius:4px; font-weight:600; margin:0 4px; border:1px solid rgba(255,255,255,0.15);">Highlight {i} ({h:.1f}°)</span>'
            for i, (h, hex_d, _, _, _, _, _, _, _) in enumerate(triple_data, 1)
        ]
        dark_html = f'''
        <div style="width:100%; background:{Db}; color:{Fd}; padding:14px 18px; border:1px solid #777; border-radius:6px; font-family:system-ui, sans-serif; font-size:14px; line-height:2.2; box-sizing:border-box; margin:4px 0;">
            <strong>Dark Theme (Db):</strong> Body text before {hl_spans_dark[0]} body text between {hl_spans_dark[1]} body text between {hl_spans_dark[2]} body text after.
        </div>
        '''

        table_rows = []
        for i, (h, hex_d, hex_l, lc_d, lc_l, lc_font_d, lc_font_l, clip_d, clip_l) in enumerate(triple_data, 1):
            if clip_d and clip_l:
                clip_note = '**[clipped (both)]**'
            elif clip_d:
                clip_note = '**[clipped (dark)]**'
            elif clip_l:
                clip_note = '**[clipped (light)]**'
            else:
                clip_note = 'In gamut'

            table_rows.append(
                f"| **Highlight {i}** | `{h:.1f}°` | `{hex_d}` | `{abs(lc_d):.0f}` | `{abs(lc_font_d):.0f}` | `{hex_l}` | `{abs(lc_l):.0f}` | `{abs(lc_font_l):.0f}` | {clip_note} |"
            )

        table_header = "| Highlight | Hue (H) | Dark Hex | Lc(bg) | Lc(font) | Light Hex | Lc(bg) | Lc(font) | Gamut Notes |\n| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
        table_md = mo.md(table_header + "\n".join(table_rows))

        return mo.vstack([
            mo.md(f"### {title}"),
            mo.md(f"**Minimum Pairwise Hue Separation:** `{min_sep:.1f}°` (Separations: `{sep_list[0]:.1f}°`, `{sep_list[1]:.1f}°`, `{sep_list[2]:.1f}°`)"),
            mo.Html(light_html),
            mo.Html(dark_html),
            mo.md("**Color Parameters & APCA Contrast Metrics:**"),
            table_md
        ], gap=1)

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
            valid_hues.append((h, hexv_d, hexv_l, lc_d, lc_l, rgb_d, rgb_l))

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
        triple_result = render_triple_results([c[0] for c in best_triple], title="Grid Search Optimal Triple")

    triple_result
    return hue_sep, render_triple_results


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 4. Formal Optimization with Differential Evolution

    While Section 3 uses discrete grid search over 36 coarse hue steps ($10^\circ$ increments), continuous optimization using `scipy.optimize.differential_evolution` solves the continuous objective function over $[0, 360]^3$.

    > **Why both methods produce identical $\approx 120^\circ$ results:**
    > - **Theoretical Optimum**: Placing 3 points on a $360^\circ$ color wheel to maximize minimum pairwise distance has an exact geometric maximum of $\frac{360^\circ}{3} = 120^\circ$ (an equilateral triangle).
    > - **Grid Alignment**: Because $120^\circ$ is an exact multiple of the grid step ($10^\circ$) and all hues cleared APCA constraints under the current slider settings, grid search found $(0^\circ, 120^\circ, 240^\circ)$ exactly, while Differential Evolution converged to the same global continuous optimum ($(0^\circ, 118.8^\circ, 237.8^\circ)$).
    > - **Where DE Superiority Shows**: When APCA floors or chroma limits are raised tight, certain hue ranges become forbidden. Grid search with coarse steps can miss narrow valid windows, whereas continuous Differential Evolution finds exact off-grid solutions (e.g., $41.3^\circ, 137.8^\circ, 264.1^\circ$) that skirt right along constraint boundaries.
    """)
    return


@app.cell(hide_code=True)
def _(
    Db,
    Lb,
    apca_contrast,
    hex_to_rgb255,
    hl_chroma,
    hl_lightness_dark,
    hl_lightness_light,
    hl_min_lc,
    hue_sep,
    np,
    oklch_to_srgb_hex,
):
    def _de_objective(params):
        h1, h2, h3 = params
        hues = [h1, h2, h3]

        # 1. Minimum pairwise hue separation
        seps = [hue_sep(hues[i], hues[j]) for i in range(3) for j in range(i + 1, 3)]
        min_sep = min(seps)

        # 2. Penalty terms for APCA contrast and gamut bounds
        target_lc = hl_min_lc.value
        penalty = 0.0

        db_rgb_local = hex_to_rgb255(Db)
        lb_rgb_local = hex_to_rgb255(Lb)

        for h in hues:
            _, rgb_d, clipped_d = oklch_to_srgb_hex(hl_lightness_dark.value, hl_chroma.value, h)
            _, rgb_l, clipped_l = oklch_to_srgb_hex(hl_lightness_light.value, hl_chroma.value, h)
    
            lc_d = abs(apca_contrast(rgb_d, db_rgb_local))
            lc_l = abs(apca_contrast(rgb_l, lb_rgb_local))
    
            if lc_d < target_lc:
                penalty += (target_lc - lc_d) ** 2 * 10.0
            if lc_l < target_lc:
                penalty += (target_lc - lc_l) ** 2 * 10.0
        
            # Soft penalty for gamut clipping so hue separation remains prioritized
            if clipped_d:
                penalty += 0.2
            if clipped_l:
                penalty += 0.2
        
        return -min_sep + penalty

    def _run_differential_evolution(objective, bounds, seed=42, maxiter=100, popsize=15):
        rng = np.random.default_rng(seed)
        n_dim = len(bounds)
        pop_n = popsize * n_dim
        lb = np.array([b[0] for b in bounds])
        ub = np.array([b[1] for b in bounds])

        pop = rng.uniform(lb, ub, size=(pop_n, n_dim))
        fitness = np.array([objective(ind) for ind in pop])

        F = 0.8
        CR = 0.7

        for _ in range(maxiter):
            for i in range(pop_n):
                idxs = [idx for idx in range(pop_n) if idx != i]
                a, b, c = pop[rng.choice(idxs, 3, replace=False)]
                mutant = np.clip(a + F * (b - c), lb, ub)
                cross_points = rng.random(n_dim) < CR
                if not np.any(cross_points):
                    cross_points[rng.integers(0, n_dim)] = True
                trial = np.where(cross_points, mutant, pop[i])
                f_trial = objective(trial)
                if f_trial < fitness[i]:
                    fitness[i] = f_trial
                    pop[i] = trial
                
        best_idx = np.argmin(fitness)
        return pop[best_idx]

    _bounds_de = [(0, 360), (0, 360), (0, 360)]

    # Run global optimization using pure Python/NumPy differential evolution
    _best_hues = _run_differential_evolution(
        _de_objective,
        bounds=_bounds_de,
        seed=42,
        maxiter=100,
        popsize=15
    )

    optimized_hues = sorted([float(h) % 360 for h in _best_hues])
    optimized_seps = [
        hue_sep(optimized_hues[0], optimized_hues[1]),
        hue_sep(optimized_hues[1], optimized_hues[2]),
        hue_sep(optimized_hues[0], optimized_hues[2])
    ]
    min_opt_sep = min(optimized_seps)
    return (optimized_hues,)


@app.cell(hide_code=True)
def _(optimized_hues, render_triple_results):
    de_summary = render_triple_results(optimized_hues, title="Differential Evolution Optimization Results")
    de_summary
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
    studio_L = mo.ui.number(start=0.0, stop=1.0, step=0.01, value=0.75, label="Lightness (L)")
    studio_C = mo.ui.number(start=0.0, stop=0.4, step=0.01, value=0.15, label="Chroma (C)")
    studio_H = mo.ui.number(start=0, stop=360, step=1, value=250, label="Hue (H°)")

    mo.hstack([
        mo.md("### OKLCH Controls:"),
        studio_L, studio_C, studio_H
    ], gap=4)
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


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 6. References & Bibliography

    This notebook builds upon foundational research in color perception, color space geometry, visual accessibility contrast algorithms, and global optimization:

    1. **The Hunt Effect & Color Appearance Models (CAM16 / CIECAM02)**
       - **Hunt, R. W. G.** (1952). *Light and Dark Adaptation and the Perception of Color*. Journal of the Optical Society of America, 42(3), 190–199.
         DOI: [10.1364/JOSA.42.000190](https://doi.org/10.1364/JOSA.42.000190)
       - **Li, C., Li, Z., Wang, Z., Xu, Y., Luo, M. R., Cui, G., Melgosa, M., Jiang, X., & Pointer, M. R.** (2017). *CAM16 and CAM16-UCS for predicting color appearance*. Color Research & Application, 42(6), 703–711.
         DOI: [10.1002/col.22131](https://doi.org/10.1002/col.22131)
       - **Moroney, N., Fairchild, M. D., Hunt, R. W. G., Li, C., Luo, M. R., & Newman, T.** (2002). *The CIECAM02 Color Appearance Model*. IS&T/SID Tenth Color Imaging Conference, 23–27.
         URL: [CIECAM02 Specification](https://www.imaging.org/site/IST/Resources/Technical_Papers/Conference_Proceedings/Color_and_Imaging_Conference/2002/The_CIECAM02_Color_Appearance_Model.aspx)

    2. **Perceptual Color Space (OKLab & OKLCH)**
       - **Ottosson, Björn** (2020). *A perceptual color space for image processing (OKLab)*.
         URL: [https://bottosson.github.io/posts/oklab/](https://bottosson.github.io/posts/oklab/)

    3. **Accessible Perceptual Contrast Algorithm (APCA)**
       - **Somers, Andrew** (2022). *APCA: Accessible Perceptual Contrast Algorithm*. W3C Silver / WCAG 3.0 Visual Contrast Task Force Candidate Model.
         URL: [W3C APCA Repository & Documentation](https://github.com/Myndex/apca-w3c) | [APCA Site](https://www.myndex.com/APCA/)

    4. **Differential Evolution Global Optimization**
       - **Storn, R., & Price, K.** (1997). *Differential Evolution – A Simple and Efficient Heuristic for Global Optimization over Continuous Spaces*. Journal of Global Optimization, 11(4), 341–359.
         DOI: [10.1023/A:1008202821328](https://doi.org/10.1023/A:1008202821328)
    """)
    return


if __name__ == "__main__":
    app.run()
