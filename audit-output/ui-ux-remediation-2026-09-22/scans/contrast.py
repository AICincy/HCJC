#!/usr/bin/env python3
"""WCAG 2.x contrast computations for JCStream flagged elements. Evidence for the UI audit."""

def srgb(c):
    c /= 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def lum(rgb):
    r, g, b = rgb
    return 0.2126 * srgb(r) + 0.7152 * srgb(g) + 0.0722 * srgb(b)

def hex2rgb(h):
    h = h.lstrip('#')
    if len(h) == 3:
        h = ''.join(ch * 2 for ch in h)
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def blend(fg_hex, alpha, bg_hex):
    """Composite fg over bg with alpha, return hex."""
    f, b = hex2rgb(fg_hex), hex2rgb(bg_hex)
    out = tuple(round(f[i] * alpha + b[i] * (1 - alpha)) for i in range(3))
    return '#%02X%02X%02X' % out

def ratio(fg, bg):
    l1, l2 = sorted((lum(hex2rgb(fg)), lum(hex2rgb(bg))), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)

def r(fg, bg, label, need=4.5):
    v = ratio(fg, bg)
    ok = "PASS" if v >= need else ("PASS(large)" if v >= 3 else "FAIL")
    print(f"{label:58s} {fg} on {bg}  = {v:5.2f}:1  [{ok} @ {need}:1]")

print("=== LIGHT THEME (default :root) ===")
L = dict(accent='#B33A2A', accent_bg='#FDF5EE', surface='#FFFFFF', bg='#F6F5F3',
         fg='#1A1A1A', fg_soft='#333333', fg_muted='#5C5C5C', fg_dim='#6E6E6E',
         link='#2F5E8C', warn='#B33A2A', warn_bg='#FDF5EE',
         cat_family='#6B4E8E', cat_drugs='#4D7838', cat_theft='#1F6F6F',
         tier_f1='#6B1F14', tier_f1_ink='#FDF5EE', tier_f4='#D2722E', tier_f5='#D98840',
         tier_ink_lo='#1A1A1A', misd='#2F5E8C')
r(L['accent'], L['surface'], '.visit-card-kicker (non-primary)')
r(blend('#FFFFFF', 0.85, L['accent']), L['accent'], '.visit-card-primary kicker (.85 white)')
r(L['accent'], L['accent_bg'], '.visit-card-icon (non-primary)')
r('#FFFFFF', blend('#FFFFFF', 0.16, L['accent']), '.visit-card-primary .icon (white@.16 on accent)')
r(L['fg_muted'], L['surface'], '.kpi .label')
r(L['fg_muted'], L['bg'], '.kpi .label on page bg (alt)')
r(L['warn'], L['warn_bg'], '.alert.inline-alert strong:first-child')
r(L['cat_family'], L['surface'], '.chap-2919 (stats statbar-label) on surface')
r(L['cat_family'], L['bg'], '.chap-2919 on page bg')
r(L['cat_theft'], L['surface'], '.chap-2913 theft on surface')
r(L['tier_f1_ink'], L['tier_f1'], 'tier F1 badge ink')
r(L['tier_ink_lo'], L['tier_f4'], 'tier F4 badge ink')
r(L['tier_ink_lo'], L['tier_f5'], 'tier F5 badge ink')
r(L['misd'], L['surface'], 'tier M badge text (outline style) on surface')
r(L['fg_dim'], L['bg'], '--fg-dim stamps (claimed 4.7:1)')
r(L['link'], L['fg_soft'], 'LINK vs body text (1.4.1 needs 3:1)', need=3)

print()
print("=== DARK THEME (:root[data-theme=dark]) ===")
D = dict(accent='#F0433A', accent_bg='#2B1D19', surface='#1F232A', bg='#141619',
         fg='#EDEFF2', fg_soft='#C6CBD4', fg_muted='#A3ABB6', fg_dim='#98A1AD',
         link='#8FBCE8', warn='#F0433A', warn_bg='#2B1D19', cta='#C22525',
         cat_family='#A06BE8', tier_f1='#D92D20', tier_f2='#E04E1A', tier_f3='#F0761A',
         tier_f4='#F5A524', tier_f5='#FFC53D', f1_ink='#FFF7EF', ink_lo='#141619',
         misd_m1='#3F8FF0', misd_mm='#A8D4FF')
r(D['accent'], D['surface'], '.visit-card-kicker (non-primary)')
r(D['accent'], D['accent_bg'], '.visit-card-icon (non-primary)')
r(blend('#FFFFFF', 0.85, D['cta']), D['cta'], '.visit-card-primary kicker (.85 white)')
r('#FFFFFF', blend('#FFFFFF', 0.16, D['cta']), '.visit-card-primary .icon (white@.16)')
r(D['fg_muted'], D['surface'], '.kpi .label')
r(D['warn'], D['warn_bg'], '.alert.inline-alert strong:first-child')
r(D['cat_family'], D['surface'], '.chap-2919 on surface (stats)')
r(D['cat_family'], D['bg'], '.chap-2919 on bg')
r(D['f1_ink'], D['tier_f1'], 'tier F1 ink (claimed 4.6)')
r(D['ink_lo'], D['tier_f2'], 'tier F2 ink (claimed 4.6)')
r(D['ink_lo'], D['tier_f3'], 'tier F3 ink (claimed 6.3)')
r(D['ink_lo'], D['tier_f4'], 'tier F4 ink (claimed 8.9)')
r(D['ink_lo'], D['tier_f5'], 'tier F5 ink (claimed 11.5)')
r(D['misd_m1'], D['surface'], 'tier M1 outline text on surface')
r(D['misd_mm'], D['surface'], 'tier MM outline text on surface')
r(D['link'], D['fg_soft'], 'LINK vs body text (1.4.1 needs 3:1)', need=3)
r('#FFFFFF', D['cta'], 'status-pill-blocked white on #C22525')

print()
print("=== Reference checks ===")
r('#B33A2A', '#FBFAF9', 'accent on --bg-soft (fold-chrome?)')
