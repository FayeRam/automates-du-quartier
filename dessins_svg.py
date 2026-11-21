"""
Dessins des installations en SVG (pour la version web).
Chaque fonction reçoit le niveau (état physique), les sorties de l'automate et le temps,
et renvoie le contenu SVG d'une scène de 620 × 420.
"""
import math

L, H = 620, 420

JAUNE = "#f6c434"
VERT = "#40c46e"
ROUGE = "#e24840"
ORANGE = "#f49628"
BLEU_EAU = "#4096e6"
ETEINT = "#464c58"

DEFS = """<defs>
  <filter id="halo" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="6"/></filter>
  <linearGradient id="ciel" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#7fb2e5"/><stop offset="1" stop-color="#cfe3f5"/></linearGradient>
  <linearGradient id="metal" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#9aa3b0"/><stop offset="1" stop-color="#5c6472"/></linearGradient>
  <linearGradient id="eau" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#6cb4f0"/><stop offset="1" stop-color="#2a6fb8"/></linearGradient>
</defs>"""


def rect(x, y, w, h, fill, rx=0, stroke="none", sw=0, extra=""):
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" {extra}/>'


def cercle(cx, cy, r, fill, stroke="none", sw=0, extra=""):
    return f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" {extra}/>'


def ligne(x1, y1, x2, y2, couleur, ep=2, extra=""):
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{couleur}" stroke-width="{ep}" stroke-linecap="round" {extra}/>'


def texte(x, y, contenu, taille=14, couleur="#eef0f5", ancre="middle", gras=False):
    poids = "700" if gras else "400"
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{taille}" fill="{couleur}" text-anchor="{ancre}" '
            f'font-family="Segoe UI, Arial, sans-serif" font-weight="{poids}">{contenu}</text>')


def voyant(cx, cy, allume, couleur, r=9):
    s = ""
    if allume:
        s += cercle(cx, cy, r * 1.8, couleur, extra='opacity="0.55" filter="url(#halo)"')
    s += cercle(cx, cy, r, couleur if allume else ETEINT, "#14181e", 2)
    if allume:
        s += cercle(cx - r * 0.3, cy - r * 0.3, r * 0.3, "#ffffff", extra='opacity="0.6"')
    return s


def scene(contenu):
    return DEFS + contenu


# ------------------------------------------------------------------ niveau 1
def lampe(n, s, t):
    c = rect(0, 0, L, H, "#3a3430") + rect(0, H - 60, L, 60, "#60462f")
    c += rect(0, H - 64, L, 4, "#4a3626")
    cx = L / 2
    c += ligne(cx, 0, cx, 105, "#1e1e1e", 3)
    if s["lampe"]:
        c += cercle(cx, 140, 170, "#ffdc78", extra='opacity="0.18" filter="url(#halo)"')
        c += cercle(cx, 140, 90, "#ffe08c", extra='opacity="0.35" filter="url(#halo)"')
        c += f'<polygon points="{cx-40},{150} {cx+40},{150} {cx+220},{H-60} {cx-220},{H-60}" fill="#ffe8a0" opacity="0.12"/>'
    c += rect(cx - 14, 98, 28, 18, "#505050", 3)
    c += cercle(cx, 140, 30, "#ffe68c" if s["lampe"] else "#78786e", "#2a2a2a", 2)
    for i, (nom, libelle) in enumerate((("bp_salon", "Salon"), ("bp_couloir", "Couloir"))):
        x = 110 + i * (L - 220)
        c += rect(x - 24, 220, 48, 64, "#dcdcd2", 6, "#9a9a90", 2)
        c += voyant(x, 252, n.actions[nom], JAUNE, 11)
        c += texte(x, 306, libelle, 15)
    return scene(c)


# ------------------------------------------------------------------ niveau 2
def moulin(n, s, t):
    c = rect(0, 0, L, H, "#3e3631") + rect(0, H - 70, L, 70, "#5a4634")
    cx, cy = 230, 215
    c += f'<polygon points="{cx-70},{cy-90} {cx+70},{cy-90} {cx+30},{cy-165} {cx-30},{cy-165}" fill="#b49a6a" stroke="#6e5a3a" stroke-width="3"/>'
    for k in range(7):
        c += cercle(cx - 30 + k * 10, cy - 135 + (k % 2) * 7, 4, "#e2c06c")
    c += rect(cx - 115, cy - 92, 230, 185, "url(#metal)", 14, "#3c424c", 3)
    a = n.rotation
    c += f'<g transform="rotate({a:.1f} {cx} {cy})">'
    for k in range(6):
        ang = math.radians(k * 60)
        c += ligne(cx, cy, cx + math.cos(ang) * 58, cy + math.sin(ang) * 58, "#3a3e46", 7)
    c += '</g>'
    c += cercle(cx, cy, 62, "none", "#4c525e", 7) + cercle(cx, cy, 12, "#22262c")
    if n.vitesse > 0.3:
        for k in range(4):
            y = cy + 105 + ((t * 120 + k * 18) % 55)
            c += cercle(cx + 125 + k * 6, y, 4, "#f0ecdc")
    c += rect(cx + 100, cy + 88, 52, 18, "#d8d8cc", 3)
    bx = 470
    c += rect(bx, cy - 105, 110, 232, "#d0d0c4", 10, "#8a8a80", 2)
    c += voyant(bx + 55, cy - 70, s["voyant_marche"], VERT, 13)
    c += texte(bx + 55, cy - 42, "marche", 13, "#303030")
    c += cercle(bx + 55, cy + 5, 18, VERT if n.actions["bp_marche"] else "#2a7848", "#1c3a28", 3)
    c += texte(bx + 55, cy + 40, "MARCHE", 12, "#303030", gras=True)
    c += cercle(bx + 55, cy + 70, 18, ROUGE if n.actions["bp_arret"] else "#802a2a", "#401818", 3)
    c += texte(bx + 55, cy + 104, "ARRÊT", 12, "#303030", gras=True)
    return scene(c)


# ------------------------------------------------------------------ niveau 3
def portail(n, s, t):
    c = rect(0, 0, L, 210, "url(#ciel)") + rect(0, 210, L, H - 210, "#c2a27a")
    mur_g, mur_d = 120, L - 60
    ouverture = mur_d - mur_g - 30
    c += rect(0, 120, mur_g, 210, "#ddd2bc", 0, "#b8ab92", 2)
    c += rect(mur_d, 120, 60, 210, "#ddd2bc", 0, "#b8ab92", 2)
    c += ligne(0, 334, L, 334, "#5a5a5a", 5)
    capteurs = n.capteurs()
    xp = mur_g + 15 - n.position * ouverture
    c += rect(xp, 150, ouverture, 178, "#3c4650", 4, "#262c34", 2)
    for k in range(1, 12):
        x = xp + k * ouverture / 12
        c += ligne(x, 160, x, 318, "#66727e", 5)
    yc = 292
    c += rect(mur_g + 2, yc - 9, 10, 18, "#282828") + rect(mur_d - 12, yc - 9, 10, 18, "#282828")
    if n.actions["cellule"]:
        c += ligne(mur_g + 12, yc, mur_d - 12, yc, ROUGE, 2, 'stroke-dasharray="6 4"')
        c += cercle(L / 2 + 40, yc + 8, 26, "#e8742c", "#8a3e12", 3)
        c += texte(L / 2 + 40, yc + 54, "obstacle", 14, "#2a2a2a", gras=True)
    for nom, x, lib in (("fdc_ferme", mur_d - 22, "fermé"), ("fdc_ouvert", 26, "ouvert")):
        c += rect(x - 9, 340, 18, 14, VERT if capteurs[nom] else ETEINT, 3)
        c += texte(x, 372, lib, 13, "#2a2a2a")
    clignote = s["gyrophare"] and int(t * 4) % 2 == 0
    c += rect(mur_d + 18, 102, 24, 16, "#333", 3)
    c += voyant(mur_d + 30, 96, clignote, ORANGE, 13)
    return scene(c)


# ------------------------------------------------------------------ niveau 4
def feux(n, s, t):
    c = rect(0, 0, L, H, "#4a4e56") + rect(0, 250, L, 130, "#2e3034")
    for x in range(0, L, 64):
        c += rect(x, 312, 32, 6, "#e6e6dc")
    for k in range(6):
        c += rect(L / 2 - 170 + k * 50, 252, 30, 44, "#e6e6dc")
    cx = L / 2 + 170
    c += rect(cx - 6, 150, 12, 240, "#26282c")
    c += rect(cx - 44, 14, 88, 210, "#16181c", 16, "#2e3238", 3)
    for i, (nom, couleur) in enumerate((("rouge", ROUGE), ("orange", ORANGE), ("vert", VERT))):
        c += voyant(cx, 52 + i * 66, s[nom], couleur, 25)
    c += texte(95, 52, f"{t:4.1f} s", 22, "#eef0f5", gras=True)
    if n.actions["mode_nuit"]:
        c += texte(95, 86, "Mode nuit", 18, JAUNE, gras=True)
    return scene(c)


# ------------------------------------------------------------------ niveau 5
def chateau(n, s, t):
    c = rect(0, 0, L, 330, "url(#ciel)") + rect(0, 330, L, H - 330, "#c2a27a")
    cx0, cy0, w, h = 190, 28, 200, 190
    for dx in (24, w - 24):
        c += ligne(cx0 + dx, cy0 + h, cx0 + dx + (-30 if dx < w / 2 else 30), 330, "#707070", 9)
    c += rect(cx0, cy0, w, h, "#ccd0d6", 12, "#5a6068", 4)
    hauteur = (h - 8) * n.niveau / 100
    c += rect(cx0 + 4, cy0 + h - 4 - hauteur, w - 8, hauteur, "url(#eau)", 8)
    vague = cy0 + h - 4 - hauteur
    if hauteur > 6:
        c += f'<path d="M{cx0+4},{vague:.1f} q 24,{4*math.sin(t*3):.1f} 48,0 t 48,0 t 48,0 t 48,0" fill="none" stroke="#a8d4f8" stroke-width="2"/>'
    capteurs = n.capteurs()
    for nom, seuil, lib in (("niveau_haut", n.SEUIL_HAUT, "HAUT"), ("niveau_bas", n.SEUIL_BAS, "BAS")):
        y = cy0 + h - 4 - (h - 8) * seuil / 100
        c += ligne(cx0 + w, y, cx0 + w + 24, y, JAUNE, 2)
        c += voyant(cx0 + w + 36, y, capteurs[nom], JAUNE, 8)
        c += texte(cx0 + w + 52, y + 5, lib, 13, "#1e2a3a", "start", True)
    c += texte(cx0 + w / 2, cy0 + h / 2 + 10, f"{n.niveau:3.0f} %", 30, "#10243c", gras=True)
    px, py = 90, 360
    c += rect(px - 42, py, 84, 50, "#3c5a8c" if s["pompe"] else "#5a6068", 8, "#22262c", 2)
    c += texte(px, py + 30, "pompe", 14)
    c += ligne(px, py, px, cy0 + 12, "#707070", 9) + ligne(px, cy0 + 12, cx0, cy0 + 12, "#707070", 9)
    if s["pompe"]:
        hauteur_tuyau = py - cy0 - 12
        for k in range(6):
            y = cy0 + 12 + ((t * 140 + k * 40) % hauteur_tuyau)
            c += cercle(px, y, 4, BLEU_EAU)
    c += texte(420, 376, f"Démarrages : {n.demarrages}", 14, "#1e2a3a", "start")
    c += texte(420, 398, f"Consommation : {n.consommation:.1f} %/s", 14, "#1e2a3a", "start")
    c += voyant(L - 40, 40, s["alarme"] and int(t * 3) % 2 == 0, ROUGE, 16)
    return scene(c)


DESSINS = {1: lampe, 2: moulin, 3: portail, 4: feux, 5: chateau}
