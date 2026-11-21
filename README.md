# Automates du quartier – version iPhone / Android / navigateur

Le jeu tourne **entièrement dans le téléphone** : Python est exécuté dans le navigateur grâce à
[Pyodide](https://pyodide.org). Pas de serveur, pas d'App Store, gratuit.

Le moteur, les niveaux, le Ladder et le Grafcet (dossier `python/`) sont **les mêmes fichiers**
que la version PC. Seuls `pont.py` (le lien avec la page) et l'interface (`index.html`, `style.css`,
`app.js`) sont propres à cette version.

## Bon à savoir

- Les programmes et les niveaux réussis sont enregistrés **dans le téléphone** (pas sur Internet).
- Version de Python dans le navigateur : constante `PYODIDE` en haut de `app.js`.
- Un programme avec une boucle infinie (`while True:`) bloque la page : recharge-la.
