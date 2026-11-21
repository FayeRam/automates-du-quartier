"""
Les niveaux : chaque niveau simule une installation (physique), définit ses capteurs,
ses actionneurs, son cahier des charges, et les scénarios qui testent le programme du joueur.
"""
from moteur import Automate, ErreurProgramme, DUREE_CYCLE


class Niveau:
    NUMERO = 0
    TITRE = ""
    HISTOIRE = ""
    CONSIGNES = []
    ENTREES = {}          # nom -> description
    SORTIES = {}          # nom -> description
    COMMANDES = {}        # nom -> ("bouton" | "interrupteur", libellé) : ce que l'opérateur manipule
    NOTION = ""
    SCENARIOS = []

    def __init__(self, depart=None):
        self.actions = {nom: False for nom in self.COMMANDES}
        self.temps = 0.0
        self.reinitialiser(**(depart or {}))

    def reinitialiser(self, **depart):
        pass

    def capteurs(self):
        return {nom: self.actions.get(nom, False) for nom in self.ENTREES}

    def physique(self, sorties, dt):
        self.temps += dt

    def regles(self, sorties):
        """Règles de sécurité vérifiées à chaque cycle. Renvoie un message d'erreur ou None."""
        return None


# ===================================================================== NIVEAU 1
class Lampe(Niveau):
    NUMERO = 1
    TITRE = "La lampe du couloir"
    NOTION = "Entrées, sorties et le OU logique"
    HISTOIRE = ("Dans la maison de Tante Fatou, la lampe du couloir doit pouvoir s'allumer "
                "depuis le salon OU depuis l'entrée du couloir.")
    CONSIGNES = [
        "La lampe est allumée tant qu'on appuie sur le bouton du salon.",
        "La lampe est allumée tant qu'on appuie sur le bouton du couloir.",
        "Sans appui, la lampe est éteinte.",
    ]
    ENTREES = {"bp_salon": "Bouton du salon", "bp_couloir": "Bouton du couloir"}
    SORTIES = {"lampe": "Lampe du couloir"}
    COMMANDES = {"bp_salon": ("bouton", "Salon"), "bp_couloir": ("bouton", "Couloir")}

    def regles(self, s):
        attendu = self.actions["bp_salon"] or self.actions["bp_couloir"]
        if s["lampe"] != attendu:
            etat = lambda b: "appuyé" if b else "relâché"
            return (f"Salon {etat(self.actions['bp_salon'])}, couloir {etat(self.actions['bp_couloir'])} : "
                    f"la lampe devrait être {'allumée' if attendu else 'éteinte'}.")
        return None

    SCENARIOS = [
        {"nom": "Personne n'appuie", "duree": 1.0, "actions": []},
        {"nom": "Appui sur le bouton du salon", "duree": 2.0,
         "actions": [(0.2, "bp_salon", True), (1.2, "bp_salon", False)]},
        {"nom": "Appui sur le bouton du couloir", "duree": 2.0,
         "actions": [(0.2, "bp_couloir", True), (1.2, "bp_couloir", False)]},
        {"nom": "Les deux boutons en même temps", "duree": 2.0,
         "actions": [(0.2, "bp_salon", True), (0.2, "bp_couloir", True),
                     (1.0, "bp_salon", False), (1.5, "bp_couloir", False)]},
    ]


# ===================================================================== NIVEAU 2
class Moulin(Niveau):
    NUMERO = 2
    TITRE = "Le moteur du moulin à mil"
    NOTION = "La mémoire (auto-maintien) et l'arrêt prioritaire"
    HISTOIRE = ("Au moulin du quartier, on démarre le moteur avec un bouton MARCHE et on l'arrête "
                "avec un bouton ARRÊT. On ne reste pas le doigt sur le bouton pendant tout le broyage !")
    CONSIGNES = [
        "Un appui sur MARCHE démarre le moteur, et il continue de tourner quand on relâche.",
        "Un appui sur ARRÊT arrête le moteur.",
        "Si MARCHE et ARRÊT sont appuyés ensemble, le moteur doit être arrêté (sécurité).",
        "Le voyant de marche est allumé quand le moteur tourne, et seulement à ce moment-là.",
    ]
    ENTREES = {"bp_marche": "Bouton MARCHE", "bp_arret": "Bouton ARRÊT"}
    SORTIES = {"moteur": "Moteur du moulin", "voyant_marche": "Voyant vert de marche"}
    COMMANDES = {"bp_marche": ("bouton", "MARCHE"), "bp_arret": ("bouton", "ARRÊT")}

    def reinitialiser(self, **depart):
        self.rotation = 0.0
        self.vitesse = 0.0

    def physique(self, s, dt):
        super().physique(s, dt)
        cible = 1.0 if s["moteur"] else 0.0
        self.vitesse += (cible - self.vitesse) * min(1.0, dt * 3)
        self.rotation = (self.rotation + self.vitesse * 600 * dt) % 360

    def regles(self, s):
        if self.actions["bp_arret"] and s["moteur"]:
            return "On appuie sur ARRÊT et le moteur tourne encore : l'arrêt doit être prioritaire."
        if s["voyant_marche"] != s["moteur"]:
            return "Le voyant de marche doit être allumé exactement quand le moteur tourne."
        return None

    SCENARIOS = [
        {"nom": "Démarrage puis relâchement de MARCHE", "duree": 3.0,
         "actions": [(0.2, "bp_marche", True), (0.6, "bp_marche", False)],
         "verifs": [(2.5, lambda n, s: s["moteur"],
                     "Le moteur devrait encore tourner après avoir relâché MARCHE : il faut MÉMORISER la marche.")]},
        {"nom": "Démarrage puis arrêt", "duree": 4.0,
         "actions": [(0.2, "bp_marche", True), (0.6, "bp_marche", False),
                     (2.0, "bp_arret", True), (2.4, "bp_arret", False)],
         "verifs": [(1.5, lambda n, s: s["moteur"], "Le moteur devrait tourner après l'appui sur MARCHE."),
                    (3.5, lambda n, s: not s["moteur"],
                     "On a appuyé sur ARRÊT puis relâché : le moteur doit rester arrêté.")]},
        {"nom": "MARCHE et ARRÊT appuyés ensemble", "duree": 2.0,
         "actions": [(0.2, "bp_marche", True), (0.2, "bp_arret", True),
                     (1.0, "bp_marche", False), (1.0, "bp_arret", False)],
         "verifs": [(1.8, lambda n, s: not s["moteur"],
                     "Après un appui simultané, le moteur doit être resté arrêté.")]},
        {"nom": "Redémarrage après un arrêt", "duree": 5.0,
         "actions": [(0.2, "bp_marche", True), (0.5, "bp_marche", False),
                     (1.5, "bp_arret", True), (1.8, "bp_arret", False),
                     (3.0, "bp_marche", True), (3.3, "bp_marche", False)],
         "verifs": [(4.5, lambda n, s: s["moteur"], "Le moteur doit pouvoir redémarrer après un arrêt.")]},
    ]


# ===================================================================== NIVEAU 3
class Portail(Niveau):
    NUMERO = 3
    TITRE = "Le portail automatique"
    NOTION = "Fins de course, verrouillage et sécurité des personnes"
    HISTOIRE = ("Le portail coulissant de la villa doit s'ouvrir et se fermer tout seul. "
                "Attention : un enfant ou une voiture peut se trouver sur le passage !")
    CONSIGNES = [
        "Appui sur OUVRIR : le portail s'ouvre jusqu'au fin de course « ouvert », puis s'arrête.",
        "Appui sur FERMER : le portail se ferme jusqu'au fin de course « fermé », puis s'arrête.",
        "Jamais les deux moteurs (ouvrir et fermer) en même temps.",
        "Si la cellule détecte un obstacle pendant la fermeture : on arrête et on rouvre complètement.",
        "Le gyrophare clignote (est allumé) pendant que le portail bouge, et seulement là.",
    ]
    ENTREES = {"bp_ouvrir": "Bouton OUVRIR", "bp_fermer": "Bouton FERMER",
               "fdc_ouvert": "Fin de course : portail ouvert", "fdc_ferme": "Fin de course : portail fermé",
               "cellule": "Cellule photo : obstacle dans le passage"}
    SORTIES = {"moteur_ouvrir": "Moteur sens ouverture", "moteur_fermer": "Moteur sens fermeture",
               "gyrophare": "Gyrophare orange"}
    COMMANDES = {"bp_ouvrir": ("bouton", "OUVRIR"), "bp_fermer": ("bouton", "FERMER"),
                 "cellule": ("bouton", "Obstacle !")}
    VITESSE = 0.2       # le portail met 5 secondes pour s'ouvrir complètement

    def reinitialiser(self, position=0.0, **_):
        self.position = position         # 0 = fermé, 1 = ouvert
        self.force = 0.0                 # temps passé à forcer sur une butée

    def capteurs(self):
        c = super().capteurs()
        c["fdc_ouvert"] = self.position >= 0.999
        c["fdc_ferme"] = self.position <= 0.001
        return c

    def physique(self, s, dt):
        super().physique(s, dt)
        sens = (1 if s["moteur_ouvrir"] else 0) - (1 if s["moteur_fermer"] else 0)
        avant = self.position
        self.position = min(1.0, max(0.0, self.position + sens * self.VITESSE * dt))
        if sens != 0 and self.position == avant:
            self.force += dt
        else:
            self.force = 0.0

    def regles(self, s):
        if s["moteur_ouvrir"] and s["moteur_fermer"]:
            return "Les deux moteurs sont commandés en même temps : court-circuit !"
        if self.force > 0.15:
            return "Le moteur force contre la butée : il faut l'arrêter au fin de course."
        if self.actions["cellule"] and s["moteur_fermer"]:
            return "Obstacle dans le passage et le portail continue de fermer : danger !"
        if s["gyrophare"] != (s["moteur_ouvrir"] or s["moteur_fermer"]):
            return "Le gyrophare doit être allumé quand le portail bouge, et seulement à ce moment-là."
        return None

    SCENARIOS = [
        {"nom": "Ouverture complète", "duree": 7.5,
         "actions": [(0.2, "bp_ouvrir", True), (0.5, "bp_ouvrir", False)],
         "verifs": [(2.0, lambda n, s: s["moteur_ouvrir"],
                     "Le portail devrait être en train de s'ouvrir, même après avoir relâché OUVRIR : il faut mémoriser l'ordre."),
                    (7.0, lambda n, s: n.position >= 0.999, "Le portail devrait être complètement ouvert.")]},
        {"nom": "Fermeture complète", "duree": 7.5, "depart": {"position": 1.0},
         "actions": [(0.2, "bp_fermer", True), (0.5, "bp_fermer", False)],
         "verifs": [(7.0, lambda n, s: n.position <= 0.001, "Le portail devrait être complètement fermé.")]},
        {"nom": "Obstacle pendant la fermeture", "duree": 12.0, "depart": {"position": 1.0},
         "actions": [(0.2, "bp_fermer", True), (0.5, "bp_fermer", False),
                     (2.0, "cellule", True), (2.6, "cellule", False)],
         "verifs": [(3.5, lambda n, s: s["moteur_ouvrir"],
                     "Après l'obstacle, le portail doit se rouvrir (même quand l'obstacle est parti)."),
                    (11.5, lambda n, s: n.position >= 0.999,
                     "Après l'obstacle, le portail doit être complètement rouvert.")]},
        {"nom": "OUVRIR et FERMER appuyés ensemble", "duree": 3.0, "depart": {"position": 0.5},
         "actions": [(0.2, "bp_ouvrir", True), (0.2, "bp_fermer", True),
                     (0.8, "bp_ouvrir", False), (0.8, "bp_fermer", False)]},
    ]


# ===================================================================== NIVEAU 4
class Feux(Niveau):
    NUMERO = 4
    TITRE = "Les feux du carrefour"
    NOTION = "Les temporisations et les étapes"
    HISTOIRE = ("Au carrefour de la Patte d'Oie, les feux doivent changer tout seuls, "
                "et clignoter à l'orange la nuit.")
    CONSIGNES = [
        "Cycle normal : VERT 6 s, puis ORANGE 2 s, puis ROUGE 6 s, et on recommence au vert.",
        "Le cycle commence par le VERT.",
        "Jamais deux feux allumés en même temps.",
        "Mode nuit : seul l'ORANGE clignote (1 s allumé, 1 s éteint).",
        "En sortant du mode nuit, on repart au VERT.",
    ]
    ENTREES = {"mode_nuit": "Interrupteur mode nuit"}
    SORTIES = {"vert": "Feu vert", "orange": "Feu orange", "rouge": "Feu rouge"}
    COMMANDES = {"mode_nuit": ("interrupteur", "Mode nuit")}

    def regles(self, s):
        allumes = [n for n in ("vert", "orange", "rouge") if s[n]]
        if len(allumes) > 1:
            return f"Deux feux allumés en même temps ({' et '.join(allumes)}) : accident garanti !"
        if self.actions["mode_nuit"] and (s["vert"] or s["rouge"]):
            return "En mode nuit, seul l'orange doit clignoter."
        if not self.actions["mode_nuit"] and not allumes and self.temps > 0.15:
            return "En mode normal, il doit toujours y avoir un feu allumé."
        return None

    @staticmethod
    def _seul(couleur):
        return lambda n, s: s[couleur] and sum(s.values()) == 1

    SCENARIOS = [
        {"nom": "Deux cycles complets", "duree": 29.0, "actions": [],
         "verifs": [(3.0, _seul.__func__("vert"), "À 3 s, seul le VERT doit être allumé."),
                    (7.0, _seul.__func__("orange"), "À 7 s (après 6 s de vert), l'ORANGE doit être allumé."),
                    (11.0, _seul.__func__("rouge"), "À 11 s, le ROUGE doit être allumé (6 s, après 2 s d'orange)."),
                    (17.0, _seul.__func__("vert"), "À 17 s, on doit être revenu au VERT (2ᵉ cycle)."),
                    (21.0, _seul.__func__("orange"), "À 21 s, l'ORANGE du 2ᵉ cycle doit être allumé."),
                    (25.0, _seul.__func__("rouge"), "À 25 s, le ROUGE du 2ᵉ cycle doit être allumé.")]},
        {"nom": "Mode nuit puis retour au jour", "duree": 12.0,
         "actions": [(0.0, "mode_nuit", True), (6.0, "mode_nuit", False)],
         "verifs": [(0.5, lambda n, s: s["orange"], "Mode nuit : l'orange doit être allumé pendant la 1ʳᵉ seconde."),
                    (1.5, lambda n, s: not s["orange"], "Mode nuit : l'orange doit être éteint pendant la 2ᵉ seconde."),
                    (2.5, lambda n, s: s["orange"], "Mode nuit : l'orange doit se rallumer (clignotement)."),
                    (3.5, lambda n, s: not s["orange"], "Mode nuit : l'orange doit s'éteindre à nouveau."),
                    (8.0, _seul.__func__("vert"), "En sortant du mode nuit, on doit repartir au VERT.")]},
    ]


# ===================================================================== NIVEAU 5
class ChateauEau(Niveau):
    NUMERO = 5
    TITRE = "Le château d'eau du quartier"
    NOTION = "L'hystérésis (deux seuils) et l'arrêt d'urgence"
    HISTOIRE = ("Une pompe remplit le château d'eau à partir du forage. Le quartier consomme de l'eau "
                "toute la journée : il ne doit jamais être vide, ni déborder. Et la pompe s'use si elle "
                "démarre trop souvent !")
    CONSIGNES = [
        "Quand le niveau descend sous le capteur BAS, la pompe démarre.",
        "Elle continue de remplir jusqu'au capteur HAUT, puis s'arrête.",
        "Elle ne redémarre que lorsque le niveau est de nouveau sous le capteur BAS.",
        "Arrêt d'urgence enclenché : pompe arrêtée et alarme allumée.",
        "L'alarme est éteinte le reste du temps.",
    ]
    ENTREES = {"niveau_bas": "Capteur niveau BAS (25 %) : vrai si l'eau est en dessous",
               "niveau_haut": "Capteur niveau HAUT (85 %) : vrai si l'eau est au-dessus",
               "arret_urgence": "Arrêt d'urgence enclenché"}
    SORTIES = {"pompe": "Pompe du forage", "alarme": "Alarme rouge"}
    COMMANDES = {"arret_urgence": ("interrupteur", "Arrêt d'urgence")}
    SEUIL_BAS, SEUIL_HAUT = 25.0, 85.0
    DEBIT_POMPE = 6.0               # % par seconde

    def reinitialiser(self, niveau=50.0, consommation=2.5, **_):
        self.niveau = niveau
        self.consommation = consommation
        self.demarrages = 0
        self._pompe_avant = False

    def capteurs(self):
        c = super().capteurs()
        c["niveau_bas"] = self.niveau <= self.SEUIL_BAS
        c["niveau_haut"] = self.niveau >= self.SEUIL_HAUT
        return c

    def physique(self, s, dt):
        super().physique(s, dt)
        if s["pompe"] and not self._pompe_avant:
            self.demarrages += 1
        self._pompe_avant = s["pompe"]
        self.niveau += ((self.DEBIT_POMPE if s["pompe"] else 0.0) - self.consommation) * dt
        self.niveau = min(100.0, max(0.0, self.niveau))

    def regles(self, s):
        if self.niveau >= 99.0:
            return "Le château d'eau déborde ! La pompe aurait dû s'arrêter au niveau HAUT."
        if self.niveau <= 3.0:
            return "Le château d'eau est vide : le quartier n'a plus d'eau !"
        if self.actions["arret_urgence"] and s["pompe"]:
            return "Arrêt d'urgence enclenché et la pompe tourne encore : danger !"
        if s["alarme"] != self.actions["arret_urgence"]:
            return "L'alarme doit être allumée pendant l'arrêt d'urgence, et seulement là."
        minutes = max(self.temps, 1.0) / 60
        if self.demarrages > 3 and self.demarrages / minutes > 4:
            return (f"La pompe a démarré {self.demarrages} fois en {self.temps:.0f} s : elle va s'user ! "
                    "Elle doit remplir jusqu'au niveau HAUT avant de s'arrêter.")
        return None

    SCENARIOS = [
        {"nom": "Une journée normale", "duree": 90.0, "depart": {"niveau": 50.0, "consommation": 2.5},
         "actions": [],
         "verifs": [(89.0, lambda n, s: n.demarrages >= 1, "La pompe n'a jamais démarré.")]},
        {"nom": "Forte consommation (heure du repas)", "duree": 60.0,
         "depart": {"niveau": 40.0, "consommation": 4.5}, "actions": []},
        {"nom": "Arrêt d'urgence puis reprise", "duree": 45.0, "depart": {"niveau": 85.0, "consommation": 2.5},
         "actions": [(10.0, "arret_urgence", True), (25.0, "arret_urgence", False)],
         "verifs": [(24.5, lambda n, s: n.niveau < n.SEUIL_BAS,
                     "(scénario) le niveau aurait dû passer sous le seuil BAS pendant l'arrêt d'urgence."),
                    (27.0, lambda n, s: s["pompe"],
                     "Après l'arrêt d'urgence, le niveau est bas : la pompe doit redémarrer.")]},
    ]


NIVEAUX = [Lampe, Moulin, Portail, Feux, ChateauEau]


# ===================================================================== CORRECTEUR
def tester_scenario(classe, programme, scenario):
    """Joue un scénario rapidement (sans affichage). Renvoie (réussi, message, temps)."""
    niveau = classe(scenario.get("depart"))
    automate = Automate(niveau, programme)
    actions = sorted(scenario.get("actions", []), key=lambda a: a[0])
    verifs = sorted(scenario.get("verifs", []), key=lambda v: v[0])
    i_action = i_verif = 0
    while automate.temps < scenario["duree"] - 1e-9:
        while i_action < len(actions) and actions[i_action][0] <= automate.temps + 1e-9:
            _, nom, valeur = actions[i_action]
            niveau.actions[nom] = valeur
            i_action += 1
        try:
            sorties = automate.cycle()
        except ErreurProgramme as exc:
            return False, str(exc), automate.temps
        probleme = niveau.regles(sorties)
        if probleme:
            return False, f"À {automate.temps:.1f} s : {probleme}", automate.temps
        while i_verif < len(verifs) and verifs[i_verif][0] <= automate.temps + 1e-9:
            _, condition, message = verifs[i_verif]
            if not condition(niveau, sorties):
                return False, f"À {verifs[i_verif][0]:.1f} s : {message}", automate.temps
            i_verif += 1
    return True, "Réussi", automate.temps


def tester_niveau(classe, programme):
    """Teste tous les scénarios. Renvoie une liste de (nom, réussi, message)."""
    return [(sc["nom"], *tester_scenario(classe, programme, sc)[:2]) for sc in classe.SCENARIOS]
