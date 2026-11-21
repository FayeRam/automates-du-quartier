"""
Langage GRAFCET (étapes et transitions), comme en cours d'automatisme.

    étape      : {"num": 1, "initiale": False, "actions": [{"sortie": "S.vert", "si": ""}]}
                 une action met sa sortie à 1 tant que l'étape est active
                 (et que la condition « si » est vraie, si on en met une)
    transition : {"de": 1, "vers": 2, "condition": "E.bp_marche ET NON E.bp_arret", "duree": 0}
                 franchie quand l'étape « de » est active, que la condition est vraie
                 et que l'étape est active depuis au moins `duree` secondes

Dans les conditions on peut écrire : E.xxx, S.xxx, X1 (l'étape 1 est active), T.temps,
ET / OU / NON (ou and / or / not), des parenthèses. Une condition vide = toujours vraie.

À chaque cycle : 1) on franchit les transitions possibles, 2) on calcule les sorties.
Les sorties qui ne sont commandées par aucune étape active sont à 0.
"""
import re

from moteur import ErreurProgramme

MOTS = [(re.compile(r"\bET\b"), " and "), (re.compile(r"\bOU\b"), " or "), (re.compile(r"\bNON\b"), " not "),
        (re.compile(r"\bVRAI\b"), " True "), (re.compile(r"\bFAUX\b"), " False ")]
ETAPE = re.compile(r"\bX(\d+)\b")


def programme_vide():
    return {"etapes": [{"num": 0, "initiale": True, "actions": []},
                       {"num": 1, "initiale": False, "actions": []}],
            "transitions": [{"de": 0, "vers": 1, "condition": "", "duree": 0},
                            {"de": 1, "vers": 0, "condition": "", "duree": 0}]}


def traduire_condition(texte):
    """« E.a ET NON X2 » -> « E.a and not X(2) »"""
    texte = (texte or "").strip()
    if not texte:
        return "True"
    for motif, remplacement in MOTS:
        texte = motif.sub(remplacement, texte)
    return " ".join(ETAPE.sub(r"X(\1)", texte).split())


def _compiler_condition(texte, ou, classe):
    code = traduire_condition(texte)
    try:
        compile(code, ou, "eval")
    except SyntaxError:
        raise ErreurProgramme(f"{ou} : la condition « {texte} » est mal écrite.")
    for prefixe, nom in re.findall(r"\b([ES])\.([A-Za-z_][A-Za-z_0-9]*)", code):
        connus = classe.ENTREES if prefixe == "E" else classe.SORTIES
        if nom not in connus:
            genre = "l'entrée" if prefixe == "E" else "la sortie"
            raise ErreurProgramme(f"{ou} : {genre} {prefixe}.{nom} n'existe pas dans ce niveau.")
    return compile(code, ou, "eval")


# ====================================================================== VÉRIFICATION
def verifier(modele, classe):
    etapes = modele.get("etapes") or []
    if not etapes:
        raise ErreurProgramme("Le Grafcet est vide : ajoute au moins une étape.")
    numeros = [e.get("num") for e in etapes]
    if len(set(numeros)) != len(numeros):
        raise ErreurProgramme("Deux étapes ont le même numéro.")
    if not any(e.get("initiale") for e in etapes):
        raise ErreurProgramme("Il faut au moins une étape initiale (le double carré) pour démarrer.")
    for e in etapes:
        for a in e.get("actions") or []:
            sortie = a.get("sortie", "")
            if not sortie.startswith("S.") or sortie[2:] not in classe.SORTIES:
                raise ErreurProgramme(f"Étape {e['num']} : l'action « {sortie or '?'} » doit être une sortie S. de ce niveau.")
            _compiler_condition(a.get("si", ""), f"Étape {e['num']}, action {sortie}", classe)
    for t in modele.get("transitions") or []:
        ou = f"Transition {t.get('de')} → {t.get('vers')}"
        if t.get("de") not in numeros or t.get("vers") not in numeros:
            raise ErreurProgramme(f"{ou} : relie deux étapes qui existent.")
        try:
            if float(t.get("duree") or 0) < 0:
                raise ValueError
        except (TypeError, ValueError):
            raise ErreurProgramme(f"{ou} : la durée doit être un nombre positif ou 0.")
        code = traduire_condition(t.get("condition", ""))
        for n in ETAPE.findall(t.get("condition", "") or ""):
            if int(n) not in numeros:
                raise ErreurProgramme(f"{ou} : l'étape X{n} n'existe pas.")
        _compiler_condition(t.get("condition", ""), ou, classe)


# ====================================================================== EXÉCUTION
def compiler(modele, classe):
    """Transforme le Grafcet en fonction programme(E, S, M, T) pour le moteur d'automate."""
    verifier(modele, classe)
    etapes = {e["num"]: e for e in modele["etapes"]}
    initiales = {e["num"] for e in modele["etapes"] if e.get("initiale")}
    transitions = [dict(t, code=_compiler_condition(t.get("condition", ""), "transition", classe),
                        duree=float(t.get("duree") or 0)) for t in modele.get("transitions") or []]
    actions = {num: [(a["sortie"][2:], _compiler_condition(a.get("si", ""), "action", classe))
                     for a in e.get("actions") or []] for num, e in etapes.items()}

    def programme(E, S, M, T):
        etat = M.__dict__.get("grafcet")
        if etat is None:                                # premier cycle : étapes initiales actives
            etat = {"actives": set(initiales), "depuis": {n: T.temps for n in initiales}}
            M.grafcet = etat
        actives, depuis = etat["actives"], etat["depuis"]
        contexte = {"E": E, "S": S, "M": M, "T": T, "X": lambda n: n in actives}

        # 1) évolution : on franchit les transitions possibles (une seule par étape)
        franchies, deja = [], set()
        for t in transitions:
            if t["de"] in actives and t["de"] not in deja \
                    and T.temps - depuis.get(t["de"], 0) >= t["duree"] - 1e-9 \
                    and eval(t["code"], {"__builtins__": {"int": int, "abs": abs}}, contexte):
                franchies.append(t)
                deja.add(t["de"])
        for t in franchies:
            actives.discard(t["de"])
        for t in franchies:
            if t["vers"] not in actives:
                actives.add(t["vers"])
                depuis[t["vers"]] = T.temps

        # 2) actions : les sorties des étapes actives
        valeurs = {nom: False for nom in classe.SORTIES}
        for num in actives:
            for sortie, condition in actions.get(num, []):
                if eval(condition, {"__builtins__": {"int": int, "abs": abs}}, contexte):
                    valeurs[sortie] = True
        for nom, v in valeurs.items():
            setattr(S, nom, v)

    return programme


def etapes_actives(M):
    etat = M.__dict__.get("grafcet") if M is not None else None
    return set(etat["actives"]) if etat else set()


# ====================================================================== DESSIN
VERT = "#4ade80"
TRAIT = "#c8ceda"


def dessiner(modele, actives=None, largeur=640):
    """Dessin du Grafcet en SVG, à la façon des cours : étapes empilées, actions à droite,
    sous chaque étape une divergence en OU avec une branche par transition ;
    la transition vers l'étape suivante continue sur l'axe, les autres finissent par un renvoi « vers N ».
    Les étapes actives sont en vert, avec leur jeton."""
    actives = actives or set()
    etapes = modele.get("etapes") or []
    transitions = modele.get("transitions") or []
    x = 64                                        # axe vertical du Grafcet
    pas = 150
    car = 7.8                                     # largeur moyenne d'un caractère (13 px, Consolas)
    morceaux = []
    position = {e["num"]: 24 + i * pas for i, e in enumerate(etapes)}
    largeur_max = largeur

    for i, e in enumerate(etapes):
        y = position[e["num"]]
        active = e["num"] in actives
        bord = VERT if active else TRAIT
        fond = "#1f5133" if active else "#262c38"
        morceaux.append(f'<rect x="{x - 22}" y="{y}" width="44" height="44" fill="{fond}" stroke="{bord}" stroke-width="2.5"/>')
        if e.get("initiale"):
            morceaux.append(f'<rect x="{x - 17}" y="{y + 5}" width="34" height="34" fill="none" stroke="{bord}" stroke-width="2"/>')
        morceaux.append(f'<text x="{x}" y="{y + 28}" font-size="17" text-anchor="middle" fill="#f1f4f9" font-weight="700">{e["num"]}</text>')
        if active:
            morceaux.append(f'<circle cx="{x}" cy="{y + 37}" r="3.5" fill="{VERT}"/>')     # le jeton

        acts = e.get("actions") or []
        if acts:
            texte_actions = ", ".join(a["sortie"] + (f" si {a['si']}" if a.get("si") else "") for a in acts)
            largeur_boite = 16 + car * len(texte_actions)
            morceaux.append(f'<line x1="{x + 22}" y1="{y + 22}" x2="{x + 46}" y2="{y + 22}" stroke="{TRAIT}" stroke-width="2"/>')
            morceaux.append(f'<rect x="{x + 46}" y="{y + 8}" width="{largeur_boite:.0f}" height="28" fill="#2f3646" stroke="{bord}" stroke-width="2"/>')
            morceaux.append(f'<text x="{x + 54}" y="{y + 27}" font-size="13" fill="#f1f4f9" font-family="Consolas, monospace">{_echapper(texte_actions)}</text>')
            largeur_max = max(largeur_max, x + 60 + largeur_boite)

        suivante = etapes[i + 1]["num"] if i + 1 < len(etapes) else None
        sorties = [t for t in transitions if t.get("de") == e["num"]]
        sorties.sort(key=lambda t: t.get("vers") != suivante)            # la transition « dans l'axe » d'abord
        y_bas = y + 44
        y_div = y_bas + 14
        y_barre = y_bas + 46
        if not sorties:
            continue
        # position horizontale de chaque branche : la suivante sur l'axe, les renvois à droite
        positions, xb = [], x                    # la 1re branche est toujours sur l'axe
        for t in sorties:
            positions.append(xb)
            xb = xb + 40 + car * len(_etiquette(t))
        largeur_max = max(largeur_max, xb + 10)
        morceaux.append(f'<line x1="{x}" y1="{y_bas}" x2="{x}" y2="{y_div}" stroke="{TRAIT}" stroke-width="2"/>')
        if len(sorties) > 1:                     # divergence en OU : un seul trait horizontal
            morceaux.append(f'<line x1="{x}" y1="{y_div}" x2="{positions[-1]}" y2="{y_div}" stroke="{TRAIT}" stroke-width="2"/>')
        for k, (t, xb) in enumerate(zip(sorties, positions)):
            morceaux.append(f'<line x1="{xb}" y1="{y_div}" x2="{xb}" y2="{y_barre}" stroke="{TRAIT}" stroke-width="2"/>')
            morceaux.append(f'<line x1="{xb - 12}" y1="{y_barre}" x2="{xb + 12}" y2="{y_barre}" stroke="{TRAIT}" stroke-width="4"/>')
            morceaux.append(f'<text x="{xb + 18}" y="{y_barre + 5}" font-size="13" fill="#facc15" font-family="Consolas, monospace">{_echapper(_etiquette(t))}</text>')
            if t.get("vers") == suivante and xb == x:
                morceaux.append(f'<line x1="{x}" y1="{y_barre}" x2="{x}" y2="{position[suivante]}" stroke="{TRAIT}" stroke-width="2"/>')
            else:
                morceaux.append(f'<line x1="{xb}" y1="{y_barre}" x2="{xb}" y2="{y_barre + 20}" stroke="{TRAIT}" stroke-width="2"/>')
                morceaux.append(f'<polygon points="{xb - 6},{y_barre + 18} {xb + 6},{y_barre + 18} {xb},{y_barre + 28}" fill="{TRAIT}"/>')
                morceaux.append(f'<text x="{xb + 10}" y="{y_barre + 30}" font-size="12" fill="#9aa4b6">vers {t.get("vers")}</text>')

    hauteur = 40 + len(etapes) * pas
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {largeur_max:.0f} {hauteur}" width="100%" '
            f'style="background:#1f2430;border-radius:10px">{"".join(morceaux)}</svg>')


def _etiquette(t):
    condition = (t.get("condition") or "").strip()
    duree = float(t.get("duree") or 0)
    if duree > 0:
        temps = f"{duree:g} s/X{t.get('de')}"
        return f"{temps} ET {condition}" if condition else temps
    return condition or "1"


def _echapper(texte):
    return (texte.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
