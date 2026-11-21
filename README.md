# Automates du quartier – version iPhone / Android / navigateur

Le jeu tourne **entièrement dans le téléphone** : Python est exécuté dans le navigateur grâce à
[Pyodide](https://pyodide.org). Pas de serveur, pas d'App Store, gratuit.

Le moteur, les niveaux, le Ladder et le Grafcet (dossier `python/`) sont **les mêmes fichiers**
que la version PC. Seuls `pont.py` (le lien avec la page) et l'interface (`index.html`, `style.css`,
`app.js`) sont propres à cette version.

## L'installer sur l'iPhone

1. Ouvre l'adresse dans **Safari** (la première fois, il faut Internet : environ 10 Mo pour Python).
2. Touche **Partager** (carré avec une flèche) → **Sur l'écran d'accueil** → **Ajouter**.
3. L'icône (engrenage jaune) apparaît : le jeu s'ouvre en plein écran, et marche ensuite sans connexion.

Sur Android : ouvre l'adresse dans Chrome → menu ⋮ → **Installer l'application**.

## Mettre à jour le jeu

1. Si tu as modifié le moteur ou les niveaux dans `automate/`, lance
   `python mettre_a_jour_appli_iphone.py` (dans le dossier `automate`) : il recopie les fichiers ici.
2. Augmente `VERSION` dans **app.js ET sw.js** (ex. `1.0.0` → `1.0.1`), sinon les téléphones gardent l'ancienne version.
3. GitHub Desktop : *Commit* puis *Push*. Les téléphones reçoivent la mise à jour au lancement suivant.


## Bon à savoir

- Les programmes et les niveaux réussis sont enregistrés **dans le téléphone** (pas sur Internet).
- Version de Python dans le navigateur : constante `PYODIDE` en haut de `app.js`.
- Un programme avec une boucle infinie (`while True:`) bloque la page : recharge-la.
