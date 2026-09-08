# /// script
# dependencies = [
#     "marimo",
#     "numpy==2.5.2",
#     "scipy==1.18.1",
# ]
# requires-python = ">=3.12"
# ///

import marimo

__generated_with = "0.24.0"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _():
    import itertools
    import math
    import numpy as np
    from scipy.optimize import minimize
    import marimo as mo

    def swatch(hexv, w=80, h=30):
        """Return HTML for a color swatch."""
        return mo.Html(
            f'<div style="width:{w}px;height:{h}px;background:{hexv};border:1px solid #888;border-radius:4px;display:inline-block;vertical-align:middle;"></div>'
        )


    return math, minimize, mo, swatch


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Obsidian Theme Background & Link Color Optimizer

    Given a light theme and dark theme (with base text, link, and background colors), this notebook provides an interactive studio comparing **two optimization methods**:

    ### **Method 1: Fixed Base Colors + Link Optimization**
    - **Base Colors ($B_1 \dots B_N$)**: Selected directly by the user via color controls.
    - **Backgrounds ($Lb_k, Db_k$)**: Derived by mixing base colors into light/dark theme backgrounds with optional **Hunt Effect** visual luminance compensation ($t_{\text{dark}} = \min(0.85, t_{\text{light}} \cdot [L_L / L_D]^{0.65})$).
    - **Link Colors ($L_k, D_k$)**: Simultaneously optimized to stay close to base color hues, clear APCA contrast floors against all backgrounds, and remain distinguishable from each other, normal text, and the default theme link color.

    ---

    ### **Method 2: Advanced Joint Optimization (Base Colors + Backgrounds + Links)**
    - **Base Colors ($B_1 \dots B_N$)**: Included in the global optimization search, fine-tuning base hues and mixing parameters starting from user inputs.
    - **Background Distinguishability**: Explicitly enforces that all generated light backgrounds ($Lb_1 \dots Lb_N$) and dark backgrounds ($Db_1 \dots Db_N$) are **mutually distinguishable** from each other ($\Delta E_{\text{OKLab}} \ge 0.02$) and from original theme backgrounds.
    - **Default Link Readability**: Guarantees the default theme link color ($Kl_0$ / $Kd_0$) achieves required APCA contrast ($|Lc| \ge Lc_{\text{min\_bg}}$) against **ALL** generated backgrounds.
    - **Full Link Distinguishability**: Optimizes all generated link colors ($L_1 \dots L_N$ / $D_1 \dots D_N$) to be mutually distinguishable from each other, from normal body text, AND from the default theme link color across all backgrounds.

    ---
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

    # ---- OKLab <-> linear sRGB (Björn Ottosson) ----
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

    # ---- sRGB gamut clipping preserving chroma direction (Björn Ottosson) ----
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
            g1 = -1.2684380046 * ldt + 2.6097574011 * mdt + 0.3413193965 * sdt
            g2 = -1.2684380046 * ldt2 + 2.6097574011 * mdt2 + 0.3413193965 * sdt2
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
        hexstr = str(hexstr).lstrip("#")
        return tuple(int(hexstr[i:i + 2], 16) for i in (0, 2, 4))

    def hex_to_oklab(hexstr):
        r, g, b = [srgb_to_linear(c / 255) for c in hex_to_rgb255(hexstr)]
        return linear_srgb_to_oklab(r, g, b)

    def rgb255_to_oklch(rgb255):
        r, g, b = [srgb_to_linear(c / 255) for c in rgb255]
        L, a, bb = linear_srgb_to_oklab(r, g, b)
        return oklab_to_oklch(L, a, bb)

    def hex_to_oklch(hexstr):
        return rgb255_to_oklch(hex_to_rgb255(hexstr))

    def mix_oklab(hex_a, hex_b, t):
        ra, ga, ba = [srgb_to_linear(c / 255) for c in hex_to_rgb255(hex_a)]
        rb, gb, bb_ = [srgb_to_linear(c / 255) for c in hex_to_rgb255(hex_b)]
        La, Aa, Ba = linear_srgb_to_oklab(ra, ga, ba)
        Lb, Ab, Bb = linear_srgb_to_oklab(rb, gb, bb_)
        L = La * (1 - t) + Lb * t
        A = Aa * (1 - t) + Ab * t
        B = Ba * (1 - t) + Bb * t
        r, g, b = oklab_to_linear_srgb(L, A, B)
        if not in_gamut(r, g, b):
            r, g, b = gamut_clip_preserve_chroma(r, g, b)
        R = max(0, min(255, round(linear_to_srgb(r) * 255)))
        G = max(0, min(255, round(linear_to_srgb(g) * 255)))
        Bc = max(0, min(255, round(linear_to_srgb(b) * 255)))
        return f"#{R:02x}{G:02x}{Bc:02x}"

    def _srgb255_to_Y_apca(rgb255):
        r = (rgb255[0] / 255) ** 2.4
        g = (rgb255[1] / 255) ** 2.4
        b = (rgb255[2] / 255) ** 2.4
        y = 0.2126729 * r + 0.7151522 * g + 0.0721750 * b
        if y < 0.022:
            y += (0.022 - y) ** 1.414
        return y

    def apca_contrast(fg255, bg255):
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


    return (
        apca_contrast,
        gamut_clip_preserve_chroma,
        hex_to_oklab,
        hex_to_oklch,
        hex_to_rgb255,
        in_gamut,
        linear_to_srgb,
        mix_oklab,
        oklab_to_linear_srgb,
        oklch_to_oklab,
        oklch_to_srgb_hex,
    )


@app.cell(hide_code=True)
def _(
    apca_contrast,
    gamut_clip_preserve_chroma,
    hex_to_oklab,
    hex_to_oklch,
    hex_to_rgb255,
    in_gamut,
    linear_to_srgb,
    math,
    minimize,
    mix_oklab,
    oklab_to_linear_srgb,
    oklch_to_oklab,
    oklch_to_srgb_hex,
):
    def solve_simultaneous_link_colors(
        base_hexes,
        bgs_hex,
        text_hex,
        default_link_hex=None,
        is_light=True,
        min_lc_bg=60,
        min_lc_text=15,
        max_hue_dev=25,
        c_max=0.20,
    ):
        N = len(base_hexes)
        bgs_rgb = [hex_to_rgb255(bg) for bg in bgs_hex]
        text_rgb = hex_to_rgb255(text_hex)
        text_lab = hex_to_oklab(text_hex)

        fixed_labs = [text_lab]
        fixed_rgbs = [text_rgb]
        if default_link_hex:
            default_link_rgb = hex_to_rgb255(default_link_hex)
            fixed_labs.append(hex_to_oklab(default_link_hex))
            fixed_rgbs.append(default_link_rgb)

        base_lchs = [hex_to_oklch(b) for b in base_hexes]

        x0 = []
        bounds = []
        for i in range(N):
            Lb, Cb, Hb = base_lchs[i]
            # Lightness bounds: prevent collapse into pitch black on light bg (L >= 0.32)
            init_L = (0.34 + 0.10 * i) if is_light else (0.72 + 0.08 * i)
            init_C = min(max(0.08, Cb), c_max)
            init_H = Hb
            x0.extend([init_L, init_C, init_H])

            L_bnd = (0.32, 0.55) if is_light else (0.65, 0.90)
            C_bnd = (0.05, c_max)
            H_bnd = (Hb - max_hue_dev, Hb + max_hue_dev)
            bounds.extend([L_bnd, C_bnd, H_bnd])

        def objective(params):
            penalty = 0.0
            link_rgbs = []
            link_labs = []
            link_lchs = []

            for i in range(N):
                L, C, H = params[3 * i : 3 * i + 3]
                Hb = base_lchs[i][2]

                dh = abs(H - Hb) % 360
                dh = min(dh, 360 - dh)
                if dh > max_hue_dev:
                    penalty += 1000.0 * (dh - max_hue_dev) ** 2
                else:
                    penalty += 0.2 * dh

                Lab = oklch_to_oklab(L, C, H)
                link_labs.append(Lab)
                link_lchs.append((L, C, H % 360))

                r, g, b = oklab_to_linear_srgb(*Lab)
                g_err = max(0, -r) + max(0, r - 1) + max(0, -g) + max(0, g - 1) + max(0, -b) + max(0, b - 1)
                penalty += 500.0 * g_err

                clipped_rgb = gamut_clip_preserve_chroma(r, g, b) if not in_gamut(r, g, b) else (r, g, b)
                R = max(0, min(255, round(linear_to_srgb(clipped_rgb[0]) * 255)))
                G = max(0, min(255, round(linear_to_srgb(clipped_rgb[1]) * 255)))
                B_val = max(0, min(255, round(linear_to_srgb(clipped_rgb[2]) * 255)))
                rgb255 = (R, G, B_val)
                link_rgbs.append(rgb255)

                for bg_rgb in bgs_rgb:
                    lc = abs(apca_contrast(rgb255, bg_rgb))
                    if lc < min_lc_bg:
                        penalty += 300.0 * (min_lc_bg - lc) ** 2
                    else:
                        penalty -= 0.05 * lc

                lc_text = abs(apca_contrast(rgb255, text_rgb))
                if lc_text < min_lc_text:
                    penalty += 100.0 * (min_lc_text - lc_text) ** 2

            # Lightness Staggering Penalty (|L_i - L_j| >= 0.10 on light bg)
            if is_light and N > 1:
                for i in range(N):
                    for j in range(i + 1, N):
                        dL = abs(link_lchs[i][0] - link_lchs[j][0])
                        if dL < 0.10:
                            penalty += 2000.0 * (0.10 - dL) ** 2

            # Perceptual OKLab Distance
            all_labs = fixed_labs + link_labs
            pair_dists = []
            for i in range(len(all_labs)):
                for j in range(i + 1, len(all_labs)):
                    d = math.sqrt(sum((all_labs[i][k] - all_labs[j][k]) ** 2 for k in range(3)))
                    pair_dists.append(d)
                    if d < 0.08:
                        penalty += 1500.0 * (0.08 - d) ** 2

            min_dist = min(pair_dists) if pair_dists else 0.0
            penalty -= 50.0 * min_dist

            # Contrast Staggering on Backgrounds
            for bg_rgb in bgs_rgb:
                fixed_lcs = [abs(apca_contrast(frgb, bg_rgb)) for frgb in fixed_rgbs]
                link_lcs = [abs(apca_contrast(rgb255, bg_rgb)) for rgb255 in link_rgbs]

                for lc in link_lcs:
                    for flc in fixed_lcs:
                        diff_f = abs(lc - flc)
                        if diff_f < 10.0:
                            penalty += 30.0 * (10.0 - diff_f) ** 2

                for i in range(len(link_lcs)):
                    for j in range(i + 1, len(link_lcs)):
                        diff_p = abs(link_lcs[i] - link_lcs[j])
                        if diff_p < 12.0:
                            penalty += 50.0 * (12.0 - diff_p) ** 2

            return penalty

        res = minimize(objective, x0, method="L-BFGS-B", bounds=bounds)

        optimized_links = []
        for i in range(N):
            L, C, H = res.x[3 * i : 3 * i + 3]
            hexv, rgb255, clipped = oklch_to_srgb_hex(L, C, H % 360)
            lc_bg_min = min(abs(apca_contrast(rgb255, bg_rgb)) for bg_rgb in bgs_rgb)
            lc_text = abs(apca_contrast(rgb255, text_rgb))
            dh = abs(H % 360 - base_lchs[i][2]) % 360
            dh = min(dh, 360 - dh)
            optimized_links.append({
                "hex": hexv,
                "L": L,
                "C": C,
                "H": H % 360,
                "clipped": clipped,
                "min_lc_bg": lc_bg_min,
                "lc_text": lc_text,
                "hue_dev": dh,
            })

        return optimized_links


    def solve_advanced_joint_optimization(
        user_base_hexes,
        L0_hex, Fl_hex, Kl0_hex,
        D0_hex, Fd_hex, Kd0_hex,
        t_light_init=0.12,
        t_dark_init=0.35,
        min_lc_bg=60,
        min_lc_text=15,
        max_hue_dev=25,
        c_max=0.20,
    ):
        N = len(user_base_hexes)
        L0_rgb = hex_to_rgb255(L0_hex)
        Fl_rgb = hex_to_rgb255(Fl_hex)
        Kl0_rgb = hex_to_rgb255(Kl0_hex)

        D0_rgb = hex_to_rgb255(D0_hex)
        Fd_rgb = hex_to_rgb255(Fd_hex)
        Kd0_rgb = hex_to_rgb255(Kd0_hex)

        user_base_lchs = [hex_to_oklch(b) for b in user_base_hexes]

        x0 = []
        bounds = []
        for k in range(N):
            Lb_init, Cb_init, Hb_init = user_base_lchs[k]

            x0.extend([Hb_init, t_light_init, t_dark_init])
            bounds.extend([(Hb_init - 20.0, Hb_init + 20.0), (0.05, 0.25), (0.15, 0.50)])

            init_Ll = 0.34 + 0.10 * k
            x0.extend([init_Ll, min(max(0.08, Cb_init), c_max), Hb_init])
            bounds.extend([(0.32, 0.55), (0.05, c_max), (Hb_init - max_hue_dev, Hb_init + max_hue_dev)])

            init_Ld = 0.72 + 0.08 * k
            x0.extend([init_Ld, min(max(0.08, Cb_init), c_max), Hb_init])
            bounds.extend([(0.65, 0.90), (0.05, c_max), (Hb_init - max_hue_dev, Hb_init + max_hue_dev)])

        def objective(params):
            penalty = 0.0

            gen_base_hexes = []
            gen_light_bgs_hex = [L0_hex]
            gen_dark_bgs_hex = [D0_hex]

            light_link_rgbs = []
            dark_link_rgbs = []

            light_link_labs = []
            dark_link_labs = []
            light_link_lchs = []

            for k in range(N):
                idx = 9 * k
                H_base, t_l, t_d = params[idx : idx + 3]
                L_ll, C_ll, H_ll = params[idx + 3 : idx + 6]
                L_dl, C_dl, H_dl = params[idx + 6 : idx + 9]

                Hb_user = user_base_lchs[k][2]
                Cb_user = user_base_lchs[k][1]

                dh_b = abs(H_base - Hb_user) % 360
                dh_b = min(dh_b, 360 - dh_b)
                penalty += 5.0 * dh_b ** 2

                base_hex, _, _ = oklch_to_srgb_hex(0.50, min(Cb_user, c_max), H_base % 360)
                gen_base_hexes.append(base_hex)

                Lb_k = mix_oklab(L0_hex, base_hex, t_l)
                Db_k = mix_oklab(D0_hex, base_hex, t_d)
                gen_light_bgs_hex.append(Lb_k)
                gen_dark_bgs_hex.append(Db_k)

                hex_ll, rgb_ll, clip_ll = oklch_to_srgb_hex(L_ll, C_ll, H_ll % 360)
                light_link_rgbs.append(rgb_ll)
                light_link_labs.append(hex_to_oklab(hex_ll))
                light_link_lchs.append((L_ll, C_ll, H_ll % 360))

                hex_dl, rgb_dl, clip_dl = oklch_to_srgb_hex(L_dl, C_dl, H_dl % 360)
                dark_link_rgbs.append(rgb_dl)
                dark_link_labs.append(hex_to_oklab(hex_dl))

            # Lightness Staggering Penalty on Light Background
            if N > 1:
                for i in range(N):
                    for j in range(i + 1, N):
                        dL = abs(light_link_lchs[i][0] - light_link_lchs[j][0])
                        if dL < 0.10:
                            penalty += 2000.0 * (0.10 - dL) ** 2

            # Background distinguishability
            light_bg_labs = [hex_to_oklab(bg) for bg in gen_light_bgs_hex]
            dark_bg_labs = [hex_to_oklab(bg) for bg in gen_dark_bgs_hex]

            for i in range(len(light_bg_labs)):
                for j in range(i + 1, len(light_bg_labs)):
                    d_l = math.sqrt(sum((light_bg_labs[i][m] - light_bg_labs[j][m]) ** 2 for m in range(3)))
                    if d_l < 0.02:
                        penalty += 5000.0 * (0.02 - d_l) ** 2

                    d_d = math.sqrt(sum((dark_bg_labs[i][m] - dark_bg_labs[j][m]) ** 2 for m in range(3)))
                    if d_d < 0.02:
                        penalty += 5000.0 * (0.02 - d_d) ** 2

            # Default link readability
            light_bg_rgbs = [hex_to_rgb255(bg) for bg in gen_light_bgs_hex]
            dark_bg_rgbs = [hex_to_rgb255(bg) for bg in gen_dark_bgs_hex]

            for bg_rgb in light_bg_rgbs:
                lc_kl = abs(apca_contrast(Kl0_rgb, bg_rgb))
                if lc_kl < min_lc_bg:
                    penalty += 500.0 * (min_lc_bg - lc_kl) ** 2

            for bg_rgb in dark_bg_rgbs:
                lc_kd = abs(apca_contrast(Kd0_rgb, bg_rgb))
                if lc_kd < min_lc_bg:
                    penalty += 500.0 * (min_lc_bg - lc_kd) ** 2

            # Generated link readability
            for k in range(N):
                rgb_ll = light_link_rgbs[k]
                for bg_rgb in light_bg_rgbs:
                    lc = abs(apca_contrast(rgb_ll, bg_rgb))
                    if lc < min_lc_bg:
                        penalty += 200.0 * (min_lc_bg - lc) ** 2

                rgb_dl = dark_link_rgbs[k]
                for bg_rgb in dark_bg_rgbs:
                    lc = abs(apca_contrast(rgb_dl, bg_rgb))
                    if lc < min_lc_bg:
                        penalty += 200.0 * (min_lc_bg - lc) ** 2

            # Link distinguishability (including Fl, Fd, Kl0, Kd0)
            fixed_light_labs = [hex_to_oklab(Fl_hex), hex_to_oklab(Kl0_hex)]
            all_l_labs = fixed_light_labs + light_link_labs
            for i in range(len(all_l_labs)):
                for j in range(i + 1, len(all_l_labs)):
                    d = math.sqrt(sum((all_l_labs[i][m] - all_l_labs[m][m]) ** 2 for m in range(3)))
                    if d < 0.06:
                        penalty += 1500.0 * (0.06 - d) ** 2

            fixed_dark_labs = [hex_to_oklab(Fd_hex), hex_to_oklab(Kd0_hex)]
            all_d_labs = fixed_dark_labs + dark_link_labs
            for i in range(len(all_d_labs)):
                for j in range(i + 1, len(all_d_labs)):
                    d = math.sqrt(sum((all_d_labs[i][m] - all_d_labs[j][m]) ** 2 for m in range(3)))
                    if d < 0.06:
                        penalty += 1500.0 * (0.06 - d) ** 2

            return penalty

        res = minimize(objective, x0, method="L-BFGS-B", bounds=bounds)

        gen_bases = []
        gen_light_bgs = [L0_hex]
        gen_dark_bgs = [D0_hex]
        opt_light_links = []
        opt_dark_links = []

        for k in range(N):
            idx = 9 * k
            H_base, t_l, t_d = res.x[idx : idx + 3]
            L_ll, C_ll, H_ll = res.x[idx + 3 : idx + 6]
            L_dl, C_dl, H_dl = res.x[idx + 6 : idx + 9]

            Cb_user = user_base_lchs[k][1]
            base_hex, _, _ = oklch_to_srgb_hex(0.50, min(Cb_user, c_max), H_base % 360)
            gen_bases.append(base_hex)

            Lb_k = mix_oklab(L0_hex, base_hex, t_l)
            Db_k = mix_oklab(D0_hex, base_hex, t_d)
            gen_light_bgs.append(Lb_k)
            gen_dark_bgs.append(Db_k)

            hex_ll, rgb_ll, clip_ll = oklch_to_srgb_hex(L_ll, C_ll, H_ll % 360)
            hex_dl, rgb_dl, clip_dl = oklch_to_srgb_hex(L_dl, C_dl, H_dl % 360)

            lc_l_min = min(abs(apca_contrast(rgb_ll, hex_to_rgb255(bg))) for bg in gen_light_bgs)
            lc_d_min = min(abs(apca_contrast(rgb_dl, hex_to_rgb255(bg))) for bg in gen_dark_bgs)

            opt_light_links.append({"hex": hex_ll, "L": L_ll, "C": C_ll, "H": H_ll % 360, "clipped": clip_ll, "min_lc_bg": lc_l_min})
            opt_dark_links.append({"hex": hex_dl, "L": L_dl, "C": C_dl, "H": H_dl % 360, "clipped": clip_dl, "min_lc_bg": lc_d_min})

        return {
            "gen_bases": gen_bases,
            "gen_light_bgs": gen_light_bgs,
            "gen_dark_bgs": gen_dark_bgs,
            "opt_light_links": opt_light_links,
            "opt_dark_links": opt_dark_links,
        }


    return solve_advanced_joint_optimization, solve_simultaneous_link_colors


@app.cell(hide_code=True)
def _(mo):
    num_base_colors = mo.ui.slider(
        1, 6, value=3, step=1, show_value=True, label="Number of Base Colors (N)"
    )

    L_bg_input = mo.ui.text(value="#fdfdfd", label="Light Theme BG (L0)")
    Fl_input = mo.ui.text(value="#2e2e2e", label="Light Theme Normal Text (Fl)")
    Kl_input = mo.ui.text(value="#1d63ed", label="Light Theme Default Link (Kl0)")

    D_bg_input = mo.ui.text(value="#1e1e1e", label="Dark Theme BG (D0)")
    Fd_input = mo.ui.text(value="#dcdcdc", label="Dark Theme Normal Text (Fd)")
    Kd_input = mo.ui.text(value="#5294e2", label="Dark Theme Default Link (Kd0)")

    _base_defaults = ["#5e81ac", "#a3be8c", "#d08770", "#b48ead", "#ebcb8b", "#88c0d0"]
    base_color_inputs = mo.ui.array([
        mo.ui.text(value=hexv, label=f"Base Color B{i+1}")
        for i, hexv in enumerate(_base_defaults)
    ])

    mix_mode = mo.ui.radio(
        options=["Perceptual (Hunt Effect)", "Separate Sliders", "Linear (Equal t)"],
        value="Perceptual (Hunt Effect)",
        label="Mixing Mode",
    )
    mix_amount = mo.ui.slider(
        0.0, 0.40, value=0.12, step=0.01, show_value=True, label="Mix Amount (t)"
    )
    mix_amount_light = mo.ui.slider(
        0.0, 0.40, value=0.12, step=0.01, show_value=True, label="Light Mix (t_light)"
    )
    mix_amount_dark = mo.ui.slider(
        0.0, 0.60, value=0.35, step=0.01, show_value=True, label="Dark Mix (t_dark)"
    )

    min_lc_vs_bg = mo.ui.number(
        start=30, stop=95, step=1, value=60, label="Min APCA |Lc| vs Backgrounds"
    )
    min_lc_vs_font = mo.ui.number(
        start=0, stop=50, step=1, value=15, label="Min APCA |Lc| vs Normal Text"
    )
    max_hue_dev = mo.ui.number(
        start=0, stop=60, step=1, value=25, label="Max Hue Dev (°)"
    )
    chroma_cap = mo.ui.number(
        start=0.02, stop=0.30, step=0.01, value=0.20, label="Chroma Ceiling (C_max)"
    )

    return (
        D_bg_input,
        Fd_input,
        Fl_input,
        Kd_input,
        Kl_input,
        L_bg_input,
        base_color_inputs,
        chroma_cap,
        max_hue_dev,
        min_lc_vs_bg,
        min_lc_vs_font,
        mix_amount,
        mix_amount_dark,
        mix_amount_light,
        mix_mode,
        num_base_colors,
    )


@app.cell(hide_code=True)
def _(
    D_bg_input,
    Fd_input,
    Fl_input,
    Kd_input,
    Kl_input,
    L_bg_input,
    base_color_inputs,
    chroma_cap,
    max_hue_dev,
    min_lc_vs_bg,
    min_lc_vs_font,
    mix_amount,
    mix_amount_dark,
    mix_amount_light,
    mix_mode,
    mo,
    num_base_colors,
    swatch,
):
    _N_curr = int(num_base_colors.value)
    _active_base_controls = [
        mo.hstack([base_color_inputs[i], swatch(base_color_inputs.value[i], 32, 22)], gap=2)
        for i in range(_N_curr)
    ]

    _theme_col = mo.vstack([
        mo.md("### 1. Theme & Base Color Controls"),
        num_base_colors,
        mo.hstack([L_bg_input, swatch(L_bg_input.value, 32, 22)], gap=2),
        mo.hstack([Fl_input, swatch(Fl_input.value, 32, 22)], gap=2),
        mo.hstack([Kl_input, swatch(Kl_input.value, 32, 22)], gap=2),
        mo.hstack([D_bg_input, swatch(D_bg_input.value, 32, 22)], gap=2),
        mo.hstack([Fd_input, swatch(Fd_input.value, 32, 22)], gap=2),
        mo.hstack([Kd_input, swatch(Kd_input.value, 32, 22)], gap=2),
        mo.md("**Base Colors:**"),
        *_active_base_controls,
    ])

    _mix_ui = [mix_mode]
    if mix_mode.value == "Separate Sliders":
        _mix_ui.extend([mix_amount_light, mix_amount_dark])
    else:
        _mix_ui.append(mix_amount)

    _opt_col = mo.vstack([
        mo.md("### 2. Mix & Optimization Constraints"),
        *_mix_ui,
        mo.md("---"),
        min_lc_vs_bg,
        min_lc_vs_font,
        max_hue_dev,
        chroma_cap,
    ])

    ui_form = mo.hstack([_theme_col, _opt_col], gap=6, justify="start")
    ui_form

    return


@app.cell(hide_code=True)
def _(
    D_bg_input,
    Fd_input,
    Fl_input,
    Kd_input,
    Kl_input,
    L_bg_input,
    base_color_inputs,
    chroma_cap,
    hex_to_oklch,
    max_hue_dev,
    min_lc_vs_bg,
    min_lc_vs_font,
    mix_amount,
    mix_amount_dark,
    mix_amount_light,
    mix_mode,
    mix_oklab,
    num_base_colors,
    solve_advanced_joint_optimization,
    solve_simultaneous_link_colors,
):
    N = int(num_base_colors.value)
    base_hexes = [str(base_color_inputs.value[i]) for i in range(N)]

    L = str(L_bg_input.value)
    Fl = str(Fl_input.value)
    Kl = str(Kl_input.value)

    D = str(D_bg_input.value)
    Fd = str(Fd_input.value)
    Kd = str(Kd_input.value)

    L_l, _, _ = hex_to_oklch(L)
    L_d, _, _ = hex_to_oklch(D)

    if mix_mode.value == "Perceptual (Hunt Effect)":
        t_light = float(mix_amount.value)
        _hunt_scale = (L_l / max(0.08, L_d)) ** 0.65
        t_dark = min(0.85, t_light * _hunt_scale)
    elif mix_mode.value == "Separate Sliders":
        t_light = float(mix_amount_light.value)
        t_dark = float(mix_amount_dark.value)
    else:
        t_light = float(mix_amount.value)
        t_dark = float(mix_amount.value)

    # --- Method 1 Computation ---
    m1_derived_Lb_list = [mix_oklab(L, b_hex, t_light) for b_hex in base_hexes]
    m1_derived_Db_list = [mix_oklab(D, b_hex, t_dark) for b_hex in base_hexes]

    m1_light_bgs = [L] + m1_derived_Lb_list
    m1_dark_bgs = [D] + m1_derived_Db_list

    m1_light_labels = ["Original Light Theme (L0)"] + [
        f"Derived Light Bg Lb{i+1} (Base {i+1}: {base_hexes[i]})" for i in range(N)
    ]
    m1_dark_labels = ["Original Dark Theme (D0)"] + [
        f"Derived Dark Bg Db{i+1} (Base {i+1}: {base_hexes[i]})" for i in range(N)
    ]

    m1_light_links = solve_simultaneous_link_colors(
        base_hexes,
        m1_light_bgs,
        Fl,
        default_link_hex=Kl,
        is_light=True,
        min_lc_bg=min_lc_vs_bg.value,
        min_lc_text=min_lc_vs_font.value,
        max_hue_dev=max_hue_dev.value,
        c_max=chroma_cap.value,
    )

    m1_dark_links = solve_simultaneous_link_colors(
        base_hexes,
        m1_dark_bgs,
        Fd,
        default_link_hex=Kd,
        is_light=False,
        min_lc_bg=min_lc_vs_bg.value,
        min_lc_text=min_lc_vs_font.value,
        max_hue_dev=max_hue_dev.value,
        c_max=chroma_cap.value,
    )

    # --- Method 2 Computation (Advanced Joint Optimization) ---
    m2_res = solve_advanced_joint_optimization(
        base_hexes,
        L, Fl, Kl,
        D, Fd, Kd,
        t_light_init=t_light,
        t_dark_init=t_dark,
        min_lc_bg=min_lc_vs_bg.value,
        min_lc_text=min_lc_vs_font.value,
        max_hue_dev=max_hue_dev.value,
        c_max=chroma_cap.value,
    )

    m2_gen_bases = m2_res["gen_bases"]
    m2_light_bgs = m2_res["gen_light_bgs"]
    m2_dark_bgs = m2_res["gen_dark_bgs"]
    m2_light_links = m2_res["opt_light_links"]
    m2_dark_links = m2_res["opt_dark_links"]

    m2_light_labels = ["Original Light Theme (L0)"] + [
        f"Joint Light Bg Lb{i+1} (Base {i+1}: {m2_gen_bases[i]})" for i in range(N)
    ]
    m2_dark_labels = ["Original Dark Theme (D0)"] + [
        f"Joint Dark Bg Db{i+1} (Base {i+1}: {m2_gen_bases[i]})" for i in range(N)
    ]

    return (
        Fd,
        Fl,
        Kd,
        Kl,
        N,
        base_hexes,
        m1_dark_bgs,
        m1_dark_labels,
        m1_dark_links,
        m1_light_bgs,
        m1_light_labels,
        m1_light_links,
        m2_dark_bgs,
        m2_dark_labels,
        m2_dark_links,
        m2_gen_bases,
        m2_light_bgs,
        m2_light_labels,
        m2_light_links,
    )


@app.cell(hide_code=True)
def _(
    Fd,
    Fl,
    Kd,
    Kl,
    N,
    apca_contrast,
    base_hexes,
    hex_to_rgb255,
    m1_dark_bgs,
    m1_dark_labels,
    m1_dark_links,
    m1_light_bgs,
    m1_light_labels,
    m1_light_links,
    mo,
):
    _table_rows = []
    for _i in range(N):
        _b_hex = base_hexes[_i]
        _l_info = m1_light_links[_i]
        _d_info = m1_dark_links[_i]

        _table_rows.append({
            "Base Color": f"B{_i+1} ({_b_hex})",
            "Light Link Hex": _l_info['hex'],
            "Light OKLCH": f"L:{_l_info['L']:.2f} C:{_l_info['C']:.2f} H:{_l_info['H']:.0f}°",
            "Light ΔH(Base)": f"{_l_info['hue_dev']:.1f}°",
            "Light Lc(bg)": f"{_l_info['min_lc_bg']:.0f}",
            "Dark Link Hex": _d_info['hex'],
            "Dark OKLCH": f"L:{_d_info['L']:.2f} C:{_d_info['C']:.2f} H:{_d_info['H']:.0f}°",
            "Dark ΔH(Base)": f"{_d_info['hue_dev']:.1f}°",
            "Dark Lc(bg)": f"{_d_info['min_lc_bg']:.0f}",
        })

    m1_summary_table = mo.ui.table(_table_rows, selection=None, pagination=False)

    # Light Theme Cards
    _m1_light_cards = []
    for _bg_hex, _bg_label in zip(m1_light_bgs, m1_light_labels):
        _bg_rgb = hex_to_rgb255(_bg_hex)
        _lc_norm = abs(apca_contrast(hex_to_rgb255(Fl), _bg_rgb))
        _lc_def = abs(apca_contrast(hex_to_rgb255(Kl), _bg_rgb))

        _spans = [
            f'<span style="color:{Kl}; text-decoration:underline; font-weight:700; font-size:14px; margin:0 6px;">'
            f'Default Link ({Kl}) <span style="font-size:11px; opacity:0.85; font-weight:normal;">[Lc: {_lc_def:.0f}]</span></span>'
        ]
        for _idx, _l_info in enumerate(m1_light_links, 1):
            _k_hex = _l_info["hex"]
            _lc_link = abs(apca_contrast(hex_to_rgb255(_k_hex), _bg_rgb))
            _b_hex = base_hexes[_idx - 1]
            _spans.append(
                f'<span style="color:{_k_hex}; text-decoration:underline; font-weight:700; font-size:14px; margin:0 6px;">'
                f'Link {_idx} ({_k_hex}) <span style="font-size:11px; opacity:0.85; font-weight:normal;">[Base: {_b_hex} | Lc: {_lc_link:.0f}]</span></span>'
            )
        _links_str = " • ".join(_spans)

        _card_html = (
            f'<div style="background:{_bg_hex}; color:{Fl}; padding:14px 18px; border-radius:6px; border:1px solid #777; margin:8px 0; font-family:system-ui, sans-serif;">'
            f'<div style="font-size:12px; font-weight:700; text-transform:uppercase; letter-spacing:0.04em; margin-bottom:6px; opacity:0.85;">'
            f'{_bg_label} | Hex: <code>{_bg_hex}</code> | Normal Text Lc: <b>{_lc_norm:.0f}</b>'
            f'</div>'
            f'<div style="font-size:14px; line-height:1.8;">'
            f'Normal body text in <code>{Fl}</code>. | Links: {_links_str}'
            f'</div>'
            f'</div>'
        ).strip()
        _m1_light_cards.append(mo.Html(_card_html))

    # Dark Theme Cards
    _m1_dark_cards = []
    for _bg_hex, _bg_label in zip(m1_dark_bgs, m1_dark_labels):
        _bg_rgb = hex_to_rgb255(_bg_hex)
        _lc_norm = abs(apca_contrast(hex_to_rgb255(Fd), _bg_rgb))
        _lc_def = abs(apca_contrast(hex_to_rgb255(Kd), _bg_rgb))

        _spans = [
            f'<span style="color:{Kd}; text-decoration:underline; font-weight:700; font-size:14px; margin:0 6px;">'
            f'Default Link ({Kd}) <span style="font-size:11px; opacity:0.85; font-weight:normal;">[Lc: {_lc_def:.0f}]</span></span>'
        ]
        for _idx, _d_info in enumerate(m1_dark_links, 1):
            _k_hex = _d_info["hex"]
            _lc_link = abs(apca_contrast(hex_to_rgb255(_k_hex), _bg_rgb))
            _b_hex = base_hexes[_idx - 1]
            _spans.append(
                f'<span style="color:{_k_hex}; text-decoration:underline; font-weight:700; font-size:14px; margin:0 6px;">'
                f'Link {_idx} ({_k_hex}) <span style="font-size:11px; opacity:0.85; font-weight:normal;">[Base: {_b_hex} | Lc: {_lc_link:.0f}]</span></span>'
            )
        _links_str = " • ".join(_spans)

        _card_html = (
            f'<div style="background:{_bg_hex}; color:{Fd}; padding:14px 18px; border-radius:6px; border:1px solid #777; margin:8px 0; font-family:system-ui, sans-serif;">'
            f'<div style="font-size:12px; font-weight:700; text-transform:uppercase; letter-spacing:0.04em; margin-bottom:6px; opacity:0.85;">'
            f'{_bg_label} | Hex: <code>{_bg_hex}</code> | Normal Text Lc: <b>{_lc_norm:.0f}</b>'
            f'</div>'
            f'<div style="font-size:14px; line-height:1.8;">'
            f'Normal body text in <code>{Fd}</code>. | Links: {_links_str}'
            f'</div>'
            f'</div>'
        ).strip()
        _m1_dark_cards.append(mo.Html(_card_html))

    mo.vstack([
        mo.md("## 3. Method 1 Outputs (Fixed Base Colors)"),
        mo.md("In **Method 1**, base colors $B_k$ are fixed to user inputs, backgrounds are derived via mixing, and link colors are optimized."),
        m1_summary_table,
        mo.md(f"#### Method 1 Light Background Note Swatches"),
        *_m1_light_cards,
        mo.md(f"#### Method 1 Dark Background Note Swatches"),
        *_m1_dark_cards,
    ])

    return


@app.cell(hide_code=True)
def _(
    Fd,
    Fl,
    Kd,
    Kl,
    N,
    apca_contrast,
    base_hexes,
    hex_to_rgb255,
    m2_dark_bgs,
    m2_dark_labels,
    m2_dark_links,
    m2_gen_bases,
    m2_light_bgs,
    m2_light_labels,
    m2_light_links,
    mo,
):
    _table_rows = []
    for _i in range(N):
        _user_b = base_hexes[_i]
        _gen_b = m2_gen_bases[_i]
        _l_info = m2_light_links[_i]
        _d_info = m2_dark_links[_i]

        _table_rows.append({
            "User Base": f"B{_i+1} ({_user_b})",
            "Opt Base Color": f"{_gen_b}",
            "Opt Light Link Hex": _l_info['hex'],
            "Light OKLCH": f"L:{_l_info['L']:.2f} C:{_l_info['C']:.2f} H:{_l_info['H']:.0f}°",
            "Light Lc(bg)": f"{_l_info['min_lc_bg']:.0f}",
            "Opt Dark Link Hex": _d_info['hex'],
            "Dark OKLCH": f"L:{_d_info['L']:.2f} C:{_d_info['C']:.2f} H:{_d_info['H']:.0f}°",
            "Dark Lc(bg)": f"{_d_info['min_lc_bg']:.0f}",
        })

    m2_summary_table = mo.ui.table(_table_rows, selection=None, pagination=False)

    # Light Theme Cards
    _m2_light_cards = []
    for _bg_hex, _bg_label in zip(m2_light_bgs, m2_light_labels):
        _bg_rgb = hex_to_rgb255(_bg_hex)
        _lc_norm = abs(apca_contrast(hex_to_rgb255(Fl), _bg_rgb))
        _lc_def = abs(apca_contrast(hex_to_rgb255(Kl), _bg_rgb))

        _spans = [
            f'<span style="color:{Kl}; text-decoration:underline; font-weight:700; font-size:14px; margin:0 6px;">'
            f'Default Link ({Kl}) <span style="font-size:11px; opacity:0.85; font-weight:normal;">[Lc: {_lc_def:.0f}]</span></span>'
        ]
        for _idx, _l_info in enumerate(m2_light_links, 1):
            _k_hex = _l_info["hex"]
            _lc_link = abs(apca_contrast(hex_to_rgb255(_k_hex), _bg_rgb))
            _b_hex = m2_gen_bases[_idx - 1]
            _spans.append(
                f'<span style="color:{_k_hex}; text-decoration:underline; font-weight:700; font-size:14px; margin:0 6px;">'
                f'Link {_idx} ({_k_hex}) <span style="font-size:11px; opacity:0.85; font-weight:normal;">[Base: {_b_hex} | Lc: {_lc_link:.0f}]</span></span>'
            )
        _links_str = " • ".join(_spans)

        _card_html = (
            f'<div style="background:{_bg_hex}; color:{Fl}; padding:14px 18px; border-radius:6px; border:1px solid #777; margin:8px 0; font-family:system-ui, sans-serif;">'
            f'<div style="font-size:12px; font-weight:700; text-transform:uppercase; letter-spacing:0.04em; margin-bottom:6px; opacity:0.85;">'
            f'{_bg_label} | Hex: <code>{_bg_hex}</code> | Normal Text Lc: <b>{_lc_norm:.0f}</b>'
            f'</div>'
            f'<div style="font-size:14px; line-height:1.8;">'
            f'Normal body text in <code>{Fl}</code>. | Links: {_links_str}'
            f'</div>'
            f'</div>'
        ).strip()
        _m2_light_cards.append(mo.Html(_card_html))

    # Dark Theme Cards
    _m2_dark_cards = []
    for _bg_hex, _bg_label in zip(m2_dark_bgs, m2_dark_labels):
        _bg_rgb = hex_to_rgb255(_bg_hex)
        _lc_norm = abs(apca_contrast(hex_to_rgb255(Fd), _bg_rgb))
        _lc_def = abs(apca_contrast(hex_to_rgb255(Kd), _bg_rgb))

        _spans = [
            f'<span style="color:{Kd}; text-decoration:underline; font-weight:700; font-size:14px; margin:0 6px;">'
            f'Default Link ({Kd}) <span style="font-size:11px; opacity:0.85; font-weight:normal;">[Lc: {_lc_def:.0f}]</span></span>'
        ]
        for _idx, _d_info in enumerate(m2_dark_links, 1):
            _k_hex = _d_info["hex"]
            _lc_link = abs(apca_contrast(hex_to_rgb255(_k_hex), _bg_rgb))
            _b_hex = m2_gen_bases[_idx - 1]
            _spans.append(
                f'<span style="color:{_k_hex}; text-decoration:underline; font-weight:700; font-size:14px; margin:0 6px;">'
                f'Link {_idx} ({_k_hex}) <span style="font-size:11px; opacity:0.85; font-weight:normal;">[Base: {_b_hex} | Lc: {_lc_link:.0f}]</span></span>'
            )
        _links_str = " • ".join(_spans)

        _card_html = (
            f'<div style="background:{_bg_hex}; color:{Fd}; padding:14px 18px; border-radius:6px; border:1px solid #777; margin:8px 0; font-family:system-ui, sans-serif;">'
            f'<div style="font-size:12px; font-weight:700; text-transform:uppercase; letter-spacing:0.04em; margin-bottom:6px; opacity:0.85;">'
            f'{_bg_label} | Hex: <code>{_bg_hex}</code> | Normal Text Lc: <b>{_lc_norm:.0f}</b>'
            f'</div>'
            f'<div style="font-size:14px; line-height:1.8;">'
            f'Normal body text in <code>{Fd}</code>. | Links: {_links_str}'
            f'</div>'
            f'</div>'
        ).strip()
        _m2_dark_cards.append(mo.Html(_card_html))

    mo.vstack([
        mo.md("## 4. Method 2 Outputs (Advanced Joint Optimization)"),
        mo.md("In **Method 2**, base colors $B_k$, light/dark backgrounds, and link colors are **jointly optimized** so that all backgrounds are mutually distinguishable, default links remain readable, and link colors stay distinct."),
        m2_summary_table,
        mo.md(f"#### Method 2 Light Background Note Swatches"),
        *_m2_light_cards,
        mo.md(f"#### Method 2 Dark Background Note Swatches"),
        *_m2_dark_cards,
    ])

    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 6. References & Mathematical Methods Bibliography

    This notebook relies on primary research in color perception, color space geometry, visual contrast psychophysics, and bound-constrained numerical optimization:

    1. **Perceptual Color Space (OKLab & OKLCH)**
       - **Ottosson, Björn** (2020). *A perceptual color space for image processing (OKLab)*.
         URL: [https://bottosson.github.io/posts/oklab/](https://bottosson.github.io/posts/oklab/)
       - **Ottosson, Björn** (2021). *sRGB gamut clipping in Oklab preserving chroma*.
         URL: [https://bottosson.github.io/posts/gamutclipping/](https://bottosson.github.io/posts/gamutclipping/)

    2. **Accessible Perceptual Contrast Algorithm (APCA)**
       - **Somers, Andrew** (2022). *APCA: Accessible Perceptual Contrast Algorithm*. W3C Silver / WCAG 3.0 Visual Contrast Task Force Candidate Model.
         URL: [W3C APCA Repository & Documentation](https://github.com/Myndex/apca-w3c) | [APCA Main Site](https://www.myndex.com/APCA/)

    3. **The Hunt Effect & Color Appearance Models (CAM16 / CIECAM02)**
       - **Hunt, R. W. G.** (1952). *Light and Dark Adaptation and the Perception of Color*. Journal of the Optical Society of America, 42(3), 190–199.
         DOI: [10.1364/JOSA.42.000190](https://doi.org/10.1364/JOSA.42.000190)
       - **Moroney, N., Fairchild, M. D., Hunt, R. W. G., Li, C., Luo, M. R., & Newman, T.** (2002). *The CIECAM02 Color Appearance Model*. IS&T/SID Tenth Color Imaging Conference, 23–27.
         URL: [CIECAM02 Paper](https://www.imaging.org/site/IST/Resources/Technical_Papers/Conference_Proceedings/Color_and_Imaging_Conference/2002/The_CIECAM02_Color_Appearance_Model.aspx)
       - **Li, C., Li, Z., Wang, Z., Xu, Y., Luo, M. R., Cui, G., Melgosa, M., Jiang, X., & Pointer, M. R.** (2017). *CAM16 and CAM16-UCS for predicting color appearance*. Color Research & Application, 42(6), 703–711.
         DOI: [10.1002/col.22131](https://doi.org/10.1002/col.22131)

    4. **Bound-Constrained Quasi-Newton Optimization (L-BFGS-B)**
       - **Byrd, R. H., Lu, P., Nocedal, J., & Zhu, C.** (1995). *A Limited Memory Algorithm for Bound Constrained Optimization*. SIAM Journal on Scientific Computing, 16(5), 1190–1208.
         DOI: [10.1137/0916069](https://doi.org/10.1137/0916069)
       - **Zhu, C., Byrd, R. H., Lu, P., & Nocedal, J.** (1997). *Algorithm 778: L-BFGS-B: Fortran subroutines for large-scale bound-constrained optimization*. ACM Transactions on Mathematical Software, 23(4), 550–560.
         DOI: [10.1145/279232.279236](https://doi.org/10.1145/279232.279236)
    """)
    return


if __name__ == "__main__":
    app.run()
