"""
Moteur d'automate : exécute le programme du joueur en « cycles », comme un vrai automate
programmable industriel (API) :

    1. lire les ENTRÉES (capteurs, boutons)
    2. exécuter le PROGRAMME
    3. écrire les SORTIES (moteurs, voyants, vannes)
    … et recommencer toutes les 50 millisecondes.

Le programme du joueur est une fonction :

    def programme(E, S, M, T):
        ...

  E : les entrées (lecture seule)        ex. E.bouton_marche
  S : les sorties (à écrire)             ex. S.moteur = True
  M : la mémoire (garde ses valeurs)     ex. M.etape = 2
  T : les temporisations                 ex. T.tempo("vert", M.etape == 1, 6)
"""
import importlib.util
import math
import traceback

DUREE_CYCLE = 0.05          # 50 ms, un cycle d'automate


class ErreurProgramme(Exception):
    """Erreur dans le programme du joueur, avec un message compréhensible."""


class Signaux:
    """Un ensemble de signaux aux noms fixés : une faute de frappe donne une erreur claire."""

    def __init__(self, genre, noms, lecture_seule=False):
        object.__setattr__(self, "_genre", genre)
        object.__setattr__(self, "_valeurs", {n: False for n in noms})
        object.__setattr__(self, "_lecture_seule", lecture_seule)

    def _verifier(self, nom):
        if nom not in self._valeurs:
            proches = sorted(self._valeurs, key=lambda n: _ressemblance(n, nom), reverse=True)[:2]
            conseil = f" Tu voulais peut-être dire : {', '.join(proches)} ?" if proches else ""
            raise ErreurProgramme(f"« {nom} » n'existe pas dans les {self._genre}.{conseil}")

    def __getattr__(self, nom):
        if nom.startswith("_"):
            raise AttributeError(nom)
        self._verifier(nom)
        return self._valeurs[nom]

    def __setattr__(self, nom, valeur):
        if self._lecture_seule:
            raise ErreurProgramme(
                f"On ne peut pas écrire dans les {self._genre} (E.{nom} = …) : "
                "un capteur se lit, il ne se commande pas.")
        self._verifier(nom)
        if not isinstance(valeur, bool):
            raise ErreurProgramme(f"S.{nom} doit valoir True ou False (pas {valeur!r}).")
        self._valeurs[nom] = valeur

    def mettre(self, valeurs):
        for nom, v in valeurs.items():
            self._valeurs[nom] = bool(v)

    def lire(self):
        return dict(self._valeurs)


class Memoire:
    """Variables libres du joueur. Une variable jamais écrite vaut 0."""

    def __getattr__(self, nom):
        if nom.startswith("_"):
            raise AttributeError(nom)
        return 0


class Temporisations:
    """Temporisations comme sur un automate.

    T.tempo("nom", condition, secondes) devient True quand la condition est vraie
    depuis au moins `secondes`. Elle se remet à zéro dès que la condition devient fausse, ou si elle
    n'est pas utilisée pendant un cycle.
    T.front("nom", signal) vaut True seulement au cycle où le signal passe de False à True.
    """

    def __init__(self):
        self.temps = 0.0
        self._debuts = {}
        self._precedents = {}
        self._utilisees = set()

    def fin_cycle(self):
        """Une tempo qui n'a pas été utilisée pendant ce cycle (par exemple parce qu'elle est
        dans un « if » qui n'a pas été exécuté) repart de zéro la prochaine fois."""
        for nom in list(self._debuts):
            if nom not in self._utilisees:
                del self._debuts[nom]
        self._utilisees.clear()

    def tempo(self, nom, condition, secondes):
        self._utilisees.add(nom)
        if condition:
            debut = self._debuts.setdefault(nom, self.temps)
            return self.temps - debut >= secondes - 1e-9
        self._debuts.pop(nom, None)
        return False

    def ecoule(self, nom):
        """Temps écoulé (secondes) d'une temporisation en cours, 0 sinon."""
        debut = self._debuts.get(nom)
        return 0.0 if debut is None else self.temps - debut

    def front(self, nom, signal):
        avant = self._precedents.get(nom, False)
        self._precedents[nom] = bool(signal)
        return bool(signal) and not avant


class Automate:
    """Fait tourner un programme joueur sur un niveau donné."""

    def __init__(self, niveau, programme):
        self.niveau = niveau
        self.programme = programme
        self.E = Signaux("entrées", niveau.ENTREES, lecture_seule=True)
        self.S = Signaux("sorties", niveau.SORTIES)
        self.M = Memoire()
        self.T = Temporisations()
        self.temps = 0.0

    def cycle(self):
        """Un cycle : lire les capteurs, exécuter le programme, renvoyer les sorties."""
        self.E.mettre(self.niveau.capteurs())
        self.T.temps = self.temps
        try:
            self.programme(self.E, self.S, self.M, self.T)
        except ErreurProgramme:
            raise
        except Exception as exc:
            raise ErreurProgramme(message_erreur(exc)) from exc
        self.T.fin_cycle()
        sorties = self.S.lire()
        self.niveau.physique(sorties, DUREE_CYCLE)
        self.temps += DUREE_CYCLE
        return sorties


def charger_programme(chemin):
    """Charge mes_programmes/niveau_N.py et renvoie sa fonction programme()."""
    try:
        spec = importlib.util.spec_from_file_location("programme_joueur", chemin)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except SyntaxError as exc:
        raise ErreurProgramme(f"Erreur de syntaxe ligne {exc.lineno} : {exc.msg}") from exc
    except Exception as exc:
        raise ErreurProgramme(message_erreur(exc)) from exc
    if not callable(getattr(module, "programme", None)):
        raise ErreurProgramme("Le fichier doit contenir une fonction : def programme(E, S, M, T):")
    return module.programme


def message_erreur(exc):
    """Transforme une erreur Python en phrase courte, avec la ligne du programme du joueur."""
    ligne = ""
    for cadre in traceback.extract_tb(exc.__traceback__):
        nom_fichier = cadre.filename.replace("\\", "/").rsplit("/", 1)[-1]
        if nom_fichier not in ("moteur.py", "niveaux.py", "main.py"):
            ligne = f" (ligne {cadre.lineno})"
    traductions = {
        "NameError": "Nom inconnu",
        "TypeError": "Type incorrect",
        "ZeroDivisionError": "Division par zéro",
        "IndentationError": "Mauvaise indentation",
    }
    genre = traductions.get(type(exc).__name__, type(exc).__name__)
    return f"{genre}{ligne} : {exc}"


def _ressemblance(a, b):
    """Score simple de ressemblance entre deux noms (lettres communes, même début)."""
    commun = len(set(a) & set(b)) / max(len(set(a) | set(b)), 1)
    debut = 0
    for x, y in zip(a, b):
        if x != y:
            break
        debut += 1
    return commun + debut * 0.2 - abs(len(a) - len(b)) * 0.02


__all__ = ["Automate", "ErreurProgramme", "charger_programme", "DUREE_CYCLE", "math"]
