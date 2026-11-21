"""
Langage LADDER (schéma à contacts), comme sur les automates industriels.

Un programme = une liste de BARREAUX, exécutés de haut en bas à chaque cycle.
Un barreau = des BRANCHES en parallèle (OU), chacune faite de CONTACTS en série (ET),
et une BOBINE à droite.

    contact : {"signal": "E.bp_marche", "inverse": False}
              inverse=False : contact ouvert au repos  —| |—  (passe si le signal est vrai)
              inverse=True  : contact fermé au repos   —|/|—  (passe si le signal est faux)
    bobine  : {"type": "normale" | "set" | "reset" | "tempo", "cible": "S.moteur", "duree": 6}
              normale  —( )—  la cible prend la valeur du courant
              set      —(S)—  met la cible à 1 quand le courant passe (elle y reste)
              reset    —(R)—  met la cible à 0 quand le courant passe
              tempo    —[TON]— la temporisation T.nom devient vraie après `duree` secondes de courant

Signaux utilisables : E.xxx (entrées), S.xxx (sorties), M.xxx (bits mémoire libres),
T.xxx (bit « temps écoulé » d'une temporisation).
"""
import re

from moteur import ErreurProgramme

NOM_LIBRE = re.compile(r"^[A-Za-z_][A-Za-z_0-9]*$")
TYPES_BOBINE = {"normale": "( )", "set": "(S)", "reset": "(R)", "tempo": "TON"}


def programme_vide():
    return {"barreaux": [{"branches": [[{"signal": "", "inverse": False}]],
                          "bobine": {"type": "normale", "cible": "", "duree": 1.0}}]}


# ====================================================================== VÉRIFICATION
def verifier(modele, classe):
    """Vérifie le programme. Lève ErreurProgramme avec un message clair en cas de problème."""
    barreaux = modele.get("barreaux") or []
    if not barreaux:
        raise ErreurProgramme("Le programme Ladder est vide : ajoute au moins un barreau.")
    for i, b in enumerate(barreaux, start=1):
        bobine = b.get("bobine") or {}
        if bobine.get("type") not in TYPES_BOBINE:
            raise ErreurProgramme(f"Barreau {i} : choisis le type de la bobine.")
        cible = bobine.get("cible", "")
        if not cible:
            raise ErreurProgramme(f"Barreau {i} : la bobine n'a pas de cible (une sortie S., une mémoire M. ou une tempo T.).")
        if bobine["type"] == "tempo":
            if not cible.startswith("T."):
                raise ErreurProgramme(f"Barreau {i} : une bobine de temporisation doit viser une tempo T.nom.")
            try:
                if float(bobine.get("duree", 0)) <= 0:
                    raise ValueError
            except (TypeError, ValueError):
                raise ErreurProgramme(f"Barreau {i} : la durée de la temporisation doit être un nombre positif.")
        else:
            if not (cible.startswith("S.") or cible.startswith("M.")):
                raise ErreurProgramme(f"Barreau {i} : une bobine commande une sortie S. ou une mémoire M. (pas {cible}).")
        _verifier_signal(cible, classe, f"Barreau {i}, bobine")
        branches = b.get("branches") or []
        if not branches or not any(branches):
            raise ErreurProgramme(f"Barreau {i} : il faut au moins un contact avant la bobine.")
        for j, branche in enumerate(branches, start=1):
            if not branche:
                raise ErreurProgramme(f"Barreau {i}, branche {j} : branche vide (ajoute un contact ou supprime-la).")
            for k, contact in enumerate(branche, start=1):
                _verifier_signal(contact.get("signal", ""), classe, f"Barreau {i}, branche {j}, contact {k}")


def _verifier_signal(signal, classe, ou):
    if not signal:
        raise ErreurProgramme(f"{ou} : choisis un signal.")
    if "." not in signal:
        raise ErreurProgramme(f"{ou} : « {signal} » doit commencer par E., S., M. ou T.")
    prefixe, nom = signal.split(".", 1)
    if prefixe == "E" and nom not in classe.ENTREES:
        raise ErreurProgramme(f"{ou} : l'entrée E.{nom} n'existe pas dans ce niveau.")
    if prefixe == "S" and nom not in classe.SORTIES:
        raise ErreurProgramme(f"{ou} : la sortie S.{nom} n'existe pas dans ce niveau.")
    if prefixe not in ("E", "S", "M", "T"):
        raise ErreurProgramme(f"{ou} : « {signal} » doit commencer par E., S., M. ou T.")
    if not NOM_LIBRE.match(nom):
        raise ErreurProgramme(f"{ou} : « {nom} » n'est pas un nom valable (lettres, chiffres, _).")


# ====================================================================== EXÉCUTION
def lire(signal, E, S, M):
    prefixe, nom = signal.split(".", 1)
    if prefixe == "E":
        return bool(getattr(E, nom))
    if prefixe == "S":
        return bool(getattr(S, nom))
    if prefixe == "M":
        return bool(getattr(M, "bit_" + nom))
    return bool(getattr(M, "tempo_" + nom))          # T.nom : bit « temps écoulé »


def courant_branche(branche, E, S, M):
    """Renvoie (courant au bout de la branche, liste « ce contact laisse passer ? »)."""
    passants = []
    courant = True
    for contact in branche:
        valeur = lire(contact["signal"], E, S, M)
        passe = (not valeur) if contact.get("inverse") else valeur
        passants.append(passe)
        courant = courant and passe
    return courant, passants


def compiler(modele, classe):
    """Transforme le schéma Ladder en fonction programme(E, S, M, T) pour le moteur d'automate."""
    verifier(modele, classe)
    barreaux = [dict(b) for b in modele["barreaux"]]

    def programme(E, S, M, T):
        for b in barreaux:
            courant = any(courant_branche(br, E, S, M)[0] for br in b["branches"])
            bobine = b["bobine"]
            prefixe, nom = bobine["cible"].split(".", 1)
            if bobine["type"] == "tempo":
                setattr(M, "tempo_" + nom, T.tempo("ladder_" + nom, courant, float(bobine["duree"])))
                continue
            if bobine["type"] == "normale":
                valeur = courant
            elif bobine["type"] == "set":
                if not courant:
                    continue
                valeur = True
            else:                                       # reset
                if not courant:
                    continue
                valeur = False
            if prefixe == "S":
                setattr(S, nom, valeur)
            else:
                setattr(M, "bit_" + nom, valeur)

    return programme


# ====================================================================== DESSIN
VERT_COURANT = "#4ade80"
FIL = "#8a94a6"


def dessiner(modele, E=None, S=None, M=None, largeur=640):
    """Schéma Ladder en SVG. Si E, S, M sont fournis, le courant est allumé en vert."""
    en_direct = E is not None
    barreaux = modele.get("barreaux") or []
    x_gauche, x_droite = 18, largeur - 18
    x_bobine = x_droite - 70
    pas_contact = 92
    y = 26
    morceaux = []
    hauteur_totale = 26
    for b in barreaux:
        hauteur_totale += 46 + 46 * max(1, len(b.get("branches") or [])) + 12
    hauteur_totale = max(hauteur_totale, 120)

    for i, b in enumerate(barreaux, start=1):
        branches = b.get("branches") or [[]]
        etats = []
        if en_direct:
            try:
                etats = [courant_branche(br, E, S, M) for br in branches]
            except Exception:
                etats = []
        courant_barreau = any(c for c, _ in etats) if etats else False
        morceaux.append(f'<text x="{x_gauche + 8}" y="{y}" font-size="12" fill="#facc15">Barreau {i}</text>')
        y_premier = y + 34
        for j, branche in enumerate(branches):
            yb = y_premier + j * 46
            x = x_gauche
            courant = True
            for k, contact in enumerate(branche):
                passe = etats[j][1][k] if etats else False
                couleur_avant = VERT_COURANT if en_direct and courant else FIL
                x_suivant = x + pas_contact
                morceaux.append(_fil(x, yb, x + 30, yb, couleur_avant))
                courant = courant and passe if en_direct else False
                morceaux.append(_contact(x + 30, yb, contact, passe and en_direct))
                morceaux.append(_fil(x + 62, yb, x_suivant, yb, VERT_COURANT if en_direct and courant else FIL))
                x = x_suivant
            fin = x_bobine - 30
            morceaux.append(_fil(x, yb, fin, yb, VERT_COURANT if en_direct and courant and branche else FIL))
            if j > 0:          # branche en parallèle : on la relie au fil principal
                morceaux.append(_fil(x_gauche + 8, y_premier, x_gauche + 8, yb, FIL))
                morceaux.append(_fil(fin, y_premier, fin, yb, FIL))
        bobine = b.get("bobine") or {}
        morceaux.append(_fil(x_bobine - 30, y_premier, x_bobine, y_premier,
                             VERT_COURANT if courant_barreau else FIL))
        morceaux.append(_bobine(x_bobine, y_premier, bobine, courant_barreau))
        morceaux.append(_fil(x_bobine + 44, y_premier, x_droite, y_premier, FIL))
        y += 46 + 46 * max(1, len(branches)) + 12

    rails = (f'<line x1="{x_gauche}" y1="8" x2="{x_gauche}" y2="{hauteur_totale - 8}" stroke="{VERT_COURANT if en_direct else "#c8ceda"}" stroke-width="4"/>'
             f'<line x1="{x_droite}" y1="8" x2="{x_droite}" y2="{hauteur_totale - 8}" stroke="#c8ceda" stroke-width="4"/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {largeur} {hauteur_totale}" '
            f'width="100%" style="background:#1f2430;border-radius:10px">{rails}{"".join(morceaux)}</svg>')


def _fil(x1, y1, x2, y2, couleur):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{couleur}" stroke-width="3"/>'


def _etiquette(x, y, texte_):
    texte_ = texte_ or "?"
    return (f'<text x="{x}" y="{y}" font-size="12" text-anchor="middle" fill="#e6eaf2" '
            f'font-family="Consolas, monospace">{texte_}</text>')


def _contact(x, y, contact, passe):
    couleur = VERT_COURANT if passe else "#e6eaf2"
    s = (f'<line x1="{x}" y1="{y - 13}" x2="{x}" y2="{y + 13}" stroke="{couleur}" stroke-width="3"/>'
         f'<line x1="{x + 32}" y1="{y - 13}" x2="{x + 32}" y2="{y + 13}" stroke="{couleur}" stroke-width="3"/>')
    if contact.get("inverse"):
        s += f'<line x1="{x + 6}" y1="{y + 11}" x2="{x + 26}" y2="{y - 11}" stroke="{couleur}" stroke-width="2.5"/>'
    return s + _etiquette(x + 16, y - 19, contact.get("signal", ""))


def _bobine(x, y, bobine, alimentee):
    couleur = VERT_COURANT if alimentee else "#e6eaf2"
    genre = bobine.get("type", "normale")
    if genre == "tempo":
        s = (f'<rect x="{x}" y="{y - 16}" width="44" height="32" rx="4" fill="none" stroke="{couleur}" stroke-width="2.5"/>'
             f'<text x="{x + 22}" y="{y + 5}" font-size="12" text-anchor="middle" fill="{couleur}" font-weight="700">TON</text>'
             f'<text x="{x + 22}" y="{y + 30}" font-size="11" text-anchor="middle" fill="#9aa4b6">{bobine.get("duree", "?")} s</text>')
    else:
        lettre = {"set": "S", "reset": "R"}.get(genre, "")
        s = (f'<path d="M{x + 12},{y - 15} q -12,15 0,30" fill="none" stroke="{couleur}" stroke-width="3"/>'
             f'<path d="M{x + 32},{y - 15} q 12,15 0,30" fill="none" stroke="{couleur}" stroke-width="3"/>'
             f'<text x="{x + 22}" y="{y + 5}" font-size="13" text-anchor="middle" fill="{couleur}" font-weight="700">{lettre}</text>')
    return s + _etiquette(x + 22, y - 21, bobine.get("cible", ""))
