"""
Pont entre la page web (JavaScript) et le moteur du jeu (Python, exécuté dans le navigateur par Pyodide).

Le JavaScript appelle une seule fonction :  appel("nom_de_la_fonction", "[arguments en JSON]")
et reçoit une réponse en JSON. Le moteur, les niveaux, le Ladder et le Grafcet sont EXACTEMENT
les mêmes fichiers que la version PC (moteur.py, niveaux.py, ladder.py, grafcet.py, dessins_svg.py).
"""
import json
import os
import tempfile

import dessins_svg
import grafcet
import ladder
from moteur import Automate, ErreurProgramme, charger_programme
from niveaux import NIVEAUX, tester_niveau

PAR_NUMERO = {c.NUMERO: c for c in NIVEAUX}
MODULES = {"ladder": ladder, "grafcet": grafcet}
NOMS_LANGAGES = {"python": "Python", "ladder": "Ladder", "grafcet": "Grafcet"}
DOSSIER = os.path.join(tempfile.gettempdir(), "mes_programmes")
SVG_SCENE = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {l} {h}" width="100%" '
             'preserveAspectRatio="xMidYMid meet">{contenu}</svg>')


def modele_court(classe):
    entrees = ", ".join(f"E.{n}" for n in classe.ENTREES)
    sorties = ", ".join(f"S.{n}" for n in classe.SORTIES)
    return (f"# Niveau {classe.NUMERO} : {classe.TITRE}\n"
            f"# Entrées : {entrees}\n"
            f"# Sorties : {sorties}\n"
            "\n"
            "def programme(E, S, M, T):\n"
            "    # Écris ton programme ici, puis touche « Exécuter ».\n"
            "    pass\n")


class Partie:
    """Le niveau ouvert : installation simulée, automate, programme chargé."""

    def __init__(self, classe):
        self.classe = classe
        self.programme = None
        self.langage = "python"
        self.erreur = ""
        self.avertissement = ""
        self.en_marche = True
        self.redemarrer()

    def redemarrer(self):
        actions = getattr(self, "niveau", None) and dict(self.niveau.actions)
        self.niveau = self.classe()
        if actions:                                  # garde la position des interrupteurs
            for nom, (genre, _) in self.classe.COMMANDES.items():
                if genre == "interrupteur":
                    self.niveau.actions[nom] = actions.get(nom, False)
        self.automate = Automate(self.niveau, self.programme) if self.programme else None
        self.sorties = {n: False for n in self.classe.SORTIES}
        self.avertissement = ""

    def compiler(self, langage, source):
        self.langage = langage
        try:
            if langage == "python":
                os.makedirs(DOSSIER, exist_ok=True)
                chemin = os.path.join(DOSSIER, f"niveau_{self.classe.NUMERO}.py")
                with open(chemin, "w", encoding="utf-8") as f:
                    f.write(source)
                self.programme = charger_programme(chemin)
            else:
                self.programme = MODULES[langage].compiler(source, self.classe)
            self.erreur = ""
        except ErreurProgramme as exc:
            self.programme = None
            self.erreur = f"{NOMS_LANGAGES[langage]} : {exc}"
        self.redemarrer()

    def cycle(self):
        if not (self.en_marche and self.automate):
            return
        try:
            self.sorties = self.automate.cycle()
        except ErreurProgramme as exc:
            self.erreur = str(exc)
            self.automate = None
            return
        probleme = self.niveau.regles(self.sorties)
        if probleme:
            self.avertissement = probleme

    @property
    def temps(self):
        return self.automate.temps if self.automate else 0.0


partie = None


# ---------------------------------------------------------------- fonctions appelées par la page
def liste_niveaux():
    return [{
        "numero": c.NUMERO, "titre": c.TITRE, "notion": c.NOTION, "histoire": c.HISTOIRE,
        "consignes": list(c.CONSIGNES), "entrees": dict(c.ENTREES), "sorties": dict(c.SORTIES),
        "commandes": {n: list(v) for n, v in c.COMMANDES.items()},
        "modele_python": modele_court(c),
    } for c in NIVEAUX]


def programme_vide(langage):
    return MODULES[langage].programme_vide()


def ouvrir(numero):
    global partie
    partie = Partie(PAR_NUMERO[int(numero)])
    return True


def charger(langage, source):
    partie.compiler(langage, source)
    return {"erreur": partie.erreur}


def action(nom, valeur):
    partie.niveau.actions[nom] = bool(valeur)
    return True


def pause(en_marche):
    partie.en_marche = bool(en_marche)
    return True


def recommencer():
    partie.redemarrer()
    return True


def arreter():
    """Le schéma a changé : l'ancien programme ne tourne plus, il faudra ré-exécuter."""
    partie.programme = None
    partie.automate = None
    return True


def schema(langage, modele):
    """Schéma Ladder / Grafcet ; animé si ce programme tourne dans l'automate."""
    en_direct = partie is not None and partie.automate is not None and partie.langage == langage
    if langage == "ladder":
        if en_direct:
            a = partie.automate
            return ladder.dessiner(modele, a.E, a.S, a.M)
        return ladder.dessiner(modele)
    actives = grafcet.etapes_actives(partie.automate.M) if en_direct else set()
    return grafcet.dessiner(modele, actives)


def tic(cycles=1):
    """Fait tourner l'automate puis renvoie tout ce qu'il faut afficher."""
    for _ in range(int(cycles)):
        partie.cycle()
    capteurs = partie.niveau.capteurs()
    contenu = dessins_svg.DESSINS[partie.classe.NUMERO](partie.niveau, partie.sorties, partie.temps)
    return {
        "scene": SVG_SCENE.format(l=dessins_svg.L, h=dessins_svg.H, contenu=contenu),
        "entrees": {n: bool(capteurs[n]) for n in partie.classe.ENTREES},
        "sorties": {n: bool(partie.sorties.get(n, False)) for n in partie.classe.SORTIES},
        "temps": round(partie.temps, 2),
        "erreur": partie.erreur,
        "avertissement": partie.avertissement,
        "en_route": partie.automate is not None,
        "langage": partie.langage,
    }


def tester():
    if not partie.programme:
        return {"pret": False, "resultats": [], "reussi": False}
    resultats = tester_niveau(partie.classe, partie.programme)
    return {
        "pret": True,
        "resultats": [{"nom": n, "ok": bool(ok), "detail": d} for n, ok, d in resultats],
        "reussi": all(ok for _, ok, _ in resultats),
    }


FONCTIONS = {f.__name__: f for f in (liste_niveaux, programme_vide, ouvrir, charger, action, pause, arreter,
                                       recommencer, schema, tic, tester)}


def appel(nom, arguments="[]"):
    """Point d'entrée unique pour le JavaScript."""
    try:
        resultat = FONCTIONS[nom](*json.loads(arguments))
        return json.dumps({"ok": True, "valeur": resultat}, ensure_ascii=False)
    except Exception as exc:                      # une erreur interne ne doit jamais bloquer la page
        return json.dumps({"ok": False, "erreur": f"{type(exc).__name__} : {exc}"}, ensure_ascii=False)
