/* Automates du quartier – version téléphone / navigateur.
   Python tourne DANS le navigateur grâce à Pyodide : le moteur, les niveaux, le Ladder et le Grafcet
   sont les mêmes fichiers .py que la version PC (dossier python/). Aucun serveur n'est nécessaire. */
"use strict";

const VERSION = "1.0.0";
const PYODIDE = "https://cdn.jsdelivr.net/pyodide/v0.29.3/full/";
const FICHIERS_PYTHON = ["moteur.py", "niveaux.py", "ladder.py", "grafcet.py", "dessins_svg.py", "pont.py"];
const LANGAGES = { python: "Python", ladder: "Ladder", grafcet: "Grafcet" };
const DUREE_CYCLE_MS = 50;

const $ = (id) => document.getElementById(id);
const etat = {
  niveaux: [], niveau: null, langage: "python", modeles: {}, enMarche: true,
  occupe: false, compteur: 0, dernier: null, minuterie: null, onglet: "programme", curseur: null,
};

/* ======================================================================== mémoire du téléphone */
const memoire = {
  lire(cle, defaut) {
    try { const v = localStorage.getItem("automates." + cle); return v === null ? defaut : JSON.parse(v); }
    catch (e) { return defaut; }
  },
  ecrire(cle, valeur) {
    try { localStorage.setItem("automates." + cle, JSON.stringify(valeur)); } catch (e) { /* mémoire pleine ou privée */ }
  },
};

/* ======================================================================== Python */
let pont = null;

async function demarrerPython() {
  progression(10, "Téléchargement de Python…");
  await chargerScript(PYODIDE + "pyodide.js");
  progression(35, "Démarrage de Python…");
  const py = await loadPyodide({ indexURL: PYODIDE });
  progression(75, "Chargement des installations du quartier…");
  py.FS.mkdirTree("/jeu");
  for (const nom of FICHIERS_PYTHON) {
    const reponse = await fetch("python/" + nom + "?v=" + VERSION);
    if (!reponse.ok) throw new Error("Fichier manquant : python/" + nom);
    py.FS.writeFile("/jeu/" + nom, await reponse.text());
  }
  py.runPython("import sys\nsys.path.insert(0, '/jeu')\nimport pont");
  pont = py.pyimport("pont");
  progression(100, "Prêt !");
}

function chargerScript(url) {
  return new Promise((ok, echec) => {
    const s = document.createElement("script");
    s.src = url; s.onload = ok; s.onerror = () => echec(new Error("Impossible de télécharger Python"));
    document.head.appendChild(s);
  });
}

/** Appelle une fonction de python/pont.py et renvoie son résultat. */
async function py(nom, ...args) {
  const reponse = JSON.parse(await pont.appel(nom, JSON.stringify(args)));
  if (!reponse.ok) throw new Error(reponse.erreur);
  return reponse.valeur;
}

function progression(pourcent, texte) {
  $("chargement-barre").style.width = pourcent + "%";
  if (texte) $("chargement-texte").textContent = texte;
}

/* ======================================================================== navigation */
function afficherEcran(id) {
  document.querySelectorAll(".ecran").forEach((e) => e.classList.toggle("actif", e.id === id));
  window.scrollTo(0, 0);
}

function reussis() { return new Set(memoire.lire("reussis", [])); }

function afficherMenu() {
  arreterMinuterie();
  etat.niveau = null;
  const faits = reussis();
  const liste = $("liste-niveaux");
  liste.innerHTML = "";
  for (const n of etat.niveaux) {
    const carte = document.createElement("button");
    carte.className = "carte-niveau";
    carte.innerHTML = `
      <div class="ligne"><span class="badge">Niveau ${n.numero}</span>
        ${faits.has(n.numero) ? '<span class="reussi">✓ réussi</span>' : ""}</div>
      <h2></h2><p class="notion"></p><p class="resume"></p>`;
    carte.querySelector("h2").textContent = n.titre;
    carte.querySelector(".notion").textContent = n.notion;
    carte.querySelector(".resume").textContent = n.histoire;
    carte.addEventListener("click", () => { location.hash = "#niveau-" + n.numero; });
    liste.appendChild(carte);
  }
  const iOS = /iPhone|iPad|iPod/.test(navigator.userAgent);
  const installe = window.navigator.standalone || matchMedia("(display-mode: standalone)").matches;
  $("conseil-installation").hidden = !(iOS && !installe);
  afficherEcran("ecran-menu");
}

function suivreAdresse() {
  const m = location.hash.match(/^#niveau-(\d+)$/);
  const niveau = m && etat.niveaux.find((n) => n.numero === Number(m[1]));
  if (niveau) ouvrirNiveau(niveau); else afficherMenu();
}

/* ======================================================================== page d'un niveau */
async function ouvrirNiveau(n) {
  arreterMinuterie();
  etat.niveau = n;
  etat.enMarche = true;
  etat.dernier = null;
  await py("ouvrir", n.numero);

  $("badge-niveau").textContent = "Niveau " + n.numero;
  $("titre-niveau").textContent = n.titre;
  $("histoire").textContent = n.histoire;
  $("notion").textContent = n.notion;
  $("consignes").innerHTML = "";
  for (const c of n.consignes) {
    const li = document.createElement("li"); li.textContent = c; $("consignes").appendChild(li);
  }
  construireCommandes(n);
  construireSignaux(n);
  construireTouches(n);
  $("bouton-pause").textContent = "⏸";

  // programmes enregistrés sur le téléphone
  $("code").value = memoire.lire(`niveau${n.numero}.python`, n.modele_python);
  majNumeros();
  for (const lg of ["ladder", "grafcet"]) {
    etat.modeles[lg] = memoire.lire(`niveau${n.numero}.${lg}`, null) || await py("programme_vide", lg);
  }
  editeurLadder();
  editeurGrafcet();

  choisirOnglet("programme");
  await choisirLangage(memoire.lire(`niveau${n.numero}.langage`, "python"), { silencieux: true });
  afficherEcran("ecran-niveau");
  demarrerMinuterie();
}

function construireCommandes(n) {
  const zone = $("commandes");
  zone.innerHTML = "";
  for (const [nom, [genre, libelle]] of Object.entries(n.commandes)) {
    if (genre === "bouton") {
      const b = document.createElement("button");
      b.className = "commande-bouton"; b.textContent = libelle;
      const appuyer = (e) => { e.preventDefault(); try { b.setPointerCapture(e.pointerId); } catch (_) { /* rien */ } b.classList.add("appuye"); py("action", nom, true); };
      const relacher = () => { if (b.classList.contains("appuye")) { b.classList.remove("appuye"); py("action", nom, false); } };
      b.addEventListener("pointerdown", appuyer);
      for (const evt of ["pointerup", "pointercancel", "lostpointercapture"]) b.addEventListener(evt, relacher);
      b.addEventListener("contextmenu", (e) => e.preventDefault());
      zone.appendChild(b);
    } else {
      const lab = document.createElement("label");
      lab.className = "interrupteur";
      lab.innerHTML = `<input type="checkbox"><span></span>`;
      lab.querySelector("span").textContent = libelle;
      lab.querySelector("input").addEventListener("change", (e) => py("action", nom, e.target.checked));
      zone.appendChild(lab);
    }
  }
}

function appliquerInterrupteurs() {
  const n = etat.niveau;
  const cases = $("commandes").querySelectorAll(".interrupteur input");
  let i = 0;
  for (const [nom, [genre]] of Object.entries(n.commandes)) {
    if (genre !== "bouton") py("action", nom, cases[i++].checked);
  }
}

function construireSignaux(n) {
  for (const [prefixe, signaux, idListe] of [["E", n.entrees, "liste-entrees"], ["S", n.sorties, "liste-sorties"]]) {
    const liste = $(idListe);
    liste.innerHTML = "";
    for (const [nom, description] of Object.entries(signaux)) {
      const b = document.createElement("button");
      b.className = "signal-ligne";
      b.dataset.signal = `${prefixe}.${nom}`;
      b.innerHTML = `<span class="voyant"></span><span class="signal"></span>`;
      b.querySelector(".signal").textContent = `${prefixe}.${nom}`;
      const petit = document.createElement("small"); petit.textContent = description;
      b.querySelector(".signal").appendChild(petit);
      b.addEventListener("click", () => utiliserSignal(`${prefixe}.${nom}`));
      liste.appendChild(b);
    }
  }
}

function utiliserSignal(texte) {
  if (etat.langage === "python") {
    choisirOnglet("programme");
    insererCode(texte);
    bulle(`${texte} ajouté à ton programme`);
  } else {
    navigator.clipboard?.writeText(texte).catch(() => {});
    bulle(`${texte} copié`);
  }
}

/* ---------------------------------------------------------------- onglets et langage */
function choisirOnglet(nom) {
  etat.onglet = nom;
  document.querySelectorAll(".onglets button").forEach((b) => b.classList.toggle("actif", b.dataset.onglet === nom));
  document.querySelectorAll(".panneau").forEach((p) => p.classList.toggle("actif", p.id === "panneau-" + nom));
}

async function choisirLangage(langage, { silencieux = false } = {}) {
  if (!LANGAGES[langage]) langage = "python";
  etat.langage = langage;
  memoire.ecrire(`niveau${etat.niveau.numero}.langage`, langage);
  document.querySelectorAll(".choix-langage button").forEach((b) => b.classList.toggle("actif", b.dataset.langage === langage));
  document.querySelectorAll(".bloc-langage").forEach((b) => b.classList.toggle("actif", b.id === "bloc-" + langage));
  await charger(silencieux);
}

function sourceActuelle() {
  return etat.langage === "python" ? $("code").value : etat.modeles[etat.langage];
}

/** Charge le programme du langage choisi dans l'automate. Renvoie true s'il n'y a pas d'erreur. */
async function charger(silencieux = false) {
  const { erreur } = await py("charger", etat.langage, sourceActuelle());
  appliquerInterrupteurs();
  etat.enMarche = true; $("bouton-pause").textContent = "⏸";
  await dessinerSchema();
  if (!silencieux) {
    if (erreur) bulle("Ton programme contient une erreur : lis le message en rouge.", "negatif");
    else bulle("Programme chargé dans l'automate !", "positif");
  }
  return !erreur;
}

/* ---------------------------------------------------------------- boucle de l'automate (toutes les 50 ms) */
function demarrerMinuterie() {
  arreterMinuterie();
  etat.minuterie = setInterval(tic, DUREE_CYCLE_MS);
}
function arreterMinuterie() {
  if (etat.minuterie) clearInterval(etat.minuterie);
  etat.minuterie = null;
}

async function tic() {
  if (etat.occupe || !etat.niveau || document.hidden) return;
  etat.occupe = true;
  try {
    const e = await py("tic", 1);
    afficherEtat(e);
    etat.compteur++;
    if (etat.compteur % 2 === 0 && etat.langage !== "python" && e.en_route && e.langage === etat.langage) {
      await dessinerSchema();
    }
  } catch (err) {
    console.error(err);
  } finally {
    etat.occupe = false;
  }
}

function afficherEtat(e) {
  $("scene").innerHTML = e.scene;
  const msg = $("message");
  if (e.erreur) { msg.textContent = e.erreur; msg.className = "message erreur"; }
  else if (e.en_route) { msg.textContent = `Programme ${LANGAGES[e.langage]} en marche · ${e.temps.toFixed(1)} s`; msg.className = "message ok"; }
  else {
    msg.textContent = etat.langage === "python" ? "Écris ton programme puis touche « Exécuter »." : "Construis ton schéma puis touche « Exécuter ».";
    msg.className = "message";
  }
  $("alerte").textContent = e.avertissement ? "Attention : " + e.avertissement : "";
  const avant = etat.dernier || { entrees: {}, sorties: {} };
  for (const [prefixe, valeurs, couleur] of [["E", e.entrees, "var(--vert)"], ["S", e.sorties, "var(--orange)"]]) {
    for (const [nom, actif] of Object.entries(valeurs)) {
      if ((prefixe === "E" ? avant.entrees : avant.sorties)[nom] === actif) continue;
      const v = document.querySelector(`[data-signal="${prefixe}.${nom}"] .voyant`);
      if (v) { v.style.background = actif ? couleur : ""; v.style.boxShadow = actif ? `0 0 8px ${couleur}` : ""; }
    }
  }
  etat.dernier = e;
}

async function dessinerSchema() {
  const lg = etat.langage;
  if (lg === "python") return;
  $("schema-" + lg).innerHTML = await py("schema", lg, etat.modeles[lg]);
}

/* ---------------------------------------------------------------- boutons du bas */
async function executer() {
  await charger();
  if (window.innerWidth < 900) window.scrollTo({ top: 0, behavior: "smooth" });
}

async function tester() {
  if (!(await charger(true))) {
    bulle("Corrige d'abord l'erreur de ton programme.", "negatif");
    return;
  }
  ouvrirFenetre("Test en cours…", "<p class='petit'>L'automate est essayé dans toutes les situations du cahier des charges.</p>", []);
  await new Promise((r) => setTimeout(r, 60));          // laisse la fenêtre s'afficher
  const t = await py("tester");
  if (t.reussi) {
    const faits = reussis(); faits.add(etat.niveau.numero); memoire.ecrire("reussis", [...faits]);
  }
  const lignes = t.resultats.map((r) => `
    <div class="resultat"><span class="icone">${r.ok ? "✅" : "❌"}</span>
      <div><div>${echapper(r.nom)}</div>${r.ok ? "" : `<div class="detail">${echapper(r.detail)}</div>`}</div></div>`).join("");
  const suivant = etat.niveaux.find((n) => n.numero === etat.niveau.numero + 1);
  const boutons = [];
  if (t.reussi && suivant) boutons.push({ texte: "Niveau suivant →", classe: "jaune", action: () => { location.hash = "#niveau-" + suivant.numero; } });
  boutons.push({ texte: "Fermer" });
  ouvrirFenetre(t.reussi ? "Niveau réussi ! Ton automate respecte le cahier des charges." : "Pas encore : regarde le premier test en échec.",
    lignes, boutons, t.reussi ? "ok" : "pas-encore");
}

async function basculerPause() {
  etat.enMarche = !etat.enMarche;
  await py("pause", etat.enMarche);
  $("bouton-pause").textContent = etat.enMarche ? "⏸" : "▶";
  bulle(etat.enMarche ? "L'automate repart" : "Automate en pause");
}

async function recommencer() {
  await py("recommencer");
  appliquerInterrupteurs();
  bulle("L'installation repart de zéro");
}

function effacer() {
  ouvrirFenetre("Effacer ton programme ?", `<p>Ton programme ${LANGAGES[etat.langage]} de ce niveau sera remplacé par le modèle de départ.</p>`, [
    { texte: "Annuler" },
    { texte: "Effacer", classe: "rouge", action: async () => {
      const n = etat.niveau, lg = etat.langage;
      if (lg === "python") { $("code").value = n.modele_python; sauverCode(); majNumeros(); }
      else {
        etat.modeles[lg] = await py("programme_vide", lg);
        memoire.ecrire(`niveau${n.numero}.${lg}`, etat.modeles[lg]);
        lg === "ladder" ? editeurLadder() : editeurGrafcet();
      }
      await charger(true);
    } },
  ]);
}

/* ======================================================================== éditeur Python */
const TOUCHES = [
  ["⇥", "    "], [":", ":"], ["=", " = "], ["(", "("], [")", ")"], ["_", "_"], ['"', '"'], [",", ", "],
  ["E.", "E."], ["S.", "S."], ["M.", "M."], ["True", "True"], ["False", "False"],
  ["and", " and "], ["or", " or "], ["not", "not "], ["if", "if "], ["elif", "elif "], ["else:", "else:"],
  ["T.tempo", 'T.tempo("t1", , 2)'], ["T.front", 'T.front("f1", )'],
];

function construireTouches(n) {
  const zone = $("touches");
  zone.innerHTML = "";
  for (const [libelle, texte] of TOUCHES) {
    const b = document.createElement("button");
    b.type = "button"; b.textContent = libelle;
    b.addEventListener("pointerdown", (e) => e.preventDefault());   // garde le clavier ouvert
    b.addEventListener("click", () => insererCode(texte));
    zone.appendChild(b);
  }
}

function insererCode(texte) {
  const zone = $("code");
  const debut = document.activeElement === zone ? zone.selectionStart : (etat.curseur ?? zone.value.length);
  const fin = document.activeElement === zone ? zone.selectionEnd : debut;
  zone.setRangeText(texte, debut, fin, "end");
  // place le curseur dans les « trous » des modèles T.tempo("t1", |, 2)
  const trou = texte.indexOf(", ,");
  if (trou >= 0) { const pos = debut + trou + 2; zone.setSelectionRange(pos, pos); }
  else if (texte.endsWith(", )")) { const pos = debut + texte.length - 1; zone.setSelectionRange(pos, pos); }
  zone.focus({ preventScroll: true });
  etat.curseur = zone.selectionStart;
  sauverCode(); majNumeros();
}

function majNumeros() {
  const nb = $("code").value.split("\n").length;
  $("numeros").textContent = Array.from({ length: nb }, (_, i) => i + 1).join("\n");
  $("numeros").scrollTop = $("code").scrollTop;
}

let delaiSauvegarde = null;
function sauverCode() {
  clearTimeout(delaiSauvegarde);
  delaiSauvegarde = setTimeout(() => {
    if (etat.niveau) memoire.ecrire(`niveau${etat.niveau.numero}.python`, $("code").value);
  }, 300);
}

function brancherEditeurPython() {
  const zone = $("code");
  zone.addEventListener("input", () => { sauverCode(); majNumeros(); });
  zone.addEventListener("scroll", () => { $("numeros").scrollTop = zone.scrollTop; });
  for (const evt of ["keyup", "click", "blur"]) zone.addEventListener(evt, () => { etat.curseur = zone.selectionStart; });
  zone.addEventListener("keydown", (e) => {
    if (e.key === "Tab") { e.preventDefault(); insererCode("    "); }
    if (e.key === "Enter" && !e.isComposing) {          // garde l'indentation, et l'augmente après « : »
      const avant = zone.value.slice(0, zone.selectionStart);
      const ligne = avant.slice(avant.lastIndexOf("\n") + 1);
      let retrait = ligne.match(/^\s*/)[0];
      if (ligne.trimEnd().endsWith(":")) retrait += "    ";
      e.preventDefault();
      insererCode("\n" + retrait);
    }
  });
}

/* ======================================================================== éditeurs Ladder et Grafcet */
function creer(balise, attributs = {}, ...enfants) {
  const el = document.createElement(balise);
  for (const [cle, valeur] of Object.entries(attributs)) {
    if (cle.startsWith("on")) el.addEventListener(cle.slice(2), valeur);
    else if (cle === "texte") el.textContent = valeur;
    else if (cle in el && !["list", "autocorrect", "autocapitalize"].includes(cle)) el[cle] = valeur;
    else el.setAttribute(cle, valeur);
  }
  for (const enfant of enfants) if (enfant) el.appendChild(enfant);
  return el;
}

function listeChoix(id, valeurs) {
  let dl = document.getElementById(id);
  if (!dl) { dl = creer("datalist", { id }); document.body.appendChild(dl); }
  dl.innerHTML = "";
  for (const v of valeurs) dl.appendChild(creer("option", { value: v }));
  return id;
}

function signauxLibres(modele, prefixe, parDefaut) {
  const trouves = new Set(parDefaut);
  for (const b of modele.barreaux || []) {
    for (const br of b.branches || []) for (const c of br) if ((c.signal || "").startsWith(prefixe + ".")) trouves.add(c.signal);
    const cible = (b.bobine || {}).cible || "";
    if (cible.startsWith(prefixe + ".")) trouves.add(cible);
  }
  return [...trouves].sort();
}

async function modeleChange(lg, reconstruire = false) {
  memoire.ecrire(`niveau${etat.niveau.numero}.${lg}`, etat.modeles[lg]);
  if (reconstruire) lg === "ladder" ? editeurLadder() : editeurGrafcet();
  if (etat.dernier && etat.dernier.en_route && etat.dernier.langage === lg) await py("arreter");   // il faudra ré-exécuter
  if (etat.langage === lg) await dessinerSchema();
}

const TYPES_BOBINE = { normale: "( ) bobine", set: "(S) mise à 1", reset: "(R) mise à 0", tempo: "TON tempo" };

function editeurLadder() {
  const n = etat.niveau, m = etat.modeles.ladder, zone = $("editeur-ladder");
  const memoires = signauxLibres(m, "M", ["M.m1", "M.m2", "M.m3"]);
  const tempos = signauxLibres(m, "T", ["T.t1", "T.t2", "T.t3"]);
  const E = Object.keys(n.entrees).map((x) => "E." + x), S = Object.keys(n.sorties).map((x) => "S." + x);
  listeChoix("dl-signaux", [...E, ...S, ...memoires, ...tempos]);
  listeChoix("dl-cibles", [...S, ...memoires]);
  listeChoix("dl-tempos", tempos);
  const change = (refaire = false) => modeleChange("ladder", refaire);
  zone.innerHTML = "";

  m.barreaux.forEach((b, i) => {
    const carte = creer("div", { className: "carte-ed" });
    carte.appendChild(creer("div", { className: "ligne" },
      creer("span", { className: "titre", texte: `Barreau ${i + 1}` }),
      creer("button", { className: "mini", texte: "↑", "aria-label": "Monter", onclick: () => { if (i > 0) { [m.barreaux[i - 1], m.barreaux[i]] = [m.barreaux[i], m.barreaux[i - 1]]; change(true); } } }),
      creer("button", { className: "mini", texte: "↓", "aria-label": "Descendre", onclick: () => { if (i < m.barreaux.length - 1) { [m.barreaux[i + 1], m.barreaux[i]] = [m.barreaux[i], m.barreaux[i + 1]]; change(true); } } }),
      creer("button", { className: "mini danger", texte: "🗑", "aria-label": "Supprimer le barreau", onclick: () => { m.barreaux.splice(i, 1); change(true); } }),
    ));
    b.branches.forEach((branche, j) => {
      const ligne = creer("div", { className: "ligne" }, creer("span", { className: "ou", texte: j ? "OU" : "" }));
      branche.forEach((c, k) => {
        ligne.appendChild(creer("div", { className: "contact" },
          creer("input", { type: "text", className: "signal", value: c.signal || "", placeholder: "E.…", list: "dl-signaux",
            autocapitalize: "off", autocorrect: "off", spellcheck: false,
            onchange: (e) => { c.signal = e.target.value.trim(); change(); } }),
          (() => {
            const s = creer("select", { onchange: (e) => { c.inverse = e.target.value === "1"; change(); } },
              creer("option", { value: "0", texte: "| | ouvert" }), creer("option", { value: "1", texte: "|/| fermé" }));
            s.value = c.inverse ? "1" : "0"; return s;
          })(),
          creer("button", { className: "mini", texte: "✕", "aria-label": "Supprimer le contact", onclick: () => { branche.splice(k, 1); change(true); } }),
        ));
      });
      ligne.appendChild(creer("button", { className: "ajouter vert", texte: "+ contact (ET)", onclick: () => { branche.push({ signal: "", inverse: false }); change(true); } }));
      if (j) ligne.appendChild(creer("button", { className: "mini danger", texte: "⊖", "aria-label": "Supprimer la branche", onclick: () => { b.branches.splice(j, 1); change(true); } }));
      carte.appendChild(ligne);
    });
    const bob = b.bobine;
    const typeBobine = creer("select", { onchange: (e) => {
      bob.type = e.target.value;
      if (bob.type === "tempo" && !(bob.cible || "").startsWith("T.")) bob.cible = "T.t1";
      if (bob.type !== "tempo" && (bob.cible || "").startsWith("T.")) bob.cible = "";
      change(true);
    } });
    for (const [v, t] of Object.entries(TYPES_BOBINE)) typeBobine.appendChild(creer("option", { value: v, texte: t }));
    typeBobine.value = bob.type || "normale";
    carte.appendChild(creer("div", { className: "ligne" },
      creer("button", { className: "ajouter bleu", texte: "+ branche OU", onclick: () => { b.branches.push([{ signal: "", inverse: false }]); change(true); } }),
      creer("span", { className: "petit", texte: "Bobine :" }),
      typeBobine,
      creer("input", { type: "text", className: "signal", value: bob.cible || "", placeholder: bob.type === "tempo" ? "T.t1" : "S.…",
        list: bob.type === "tempo" ? "dl-tempos" : "dl-cibles", autocapitalize: "off", autocorrect: "off", spellcheck: false,
        onchange: (e) => { bob.cible = e.target.value.trim(); change(true); } }),
      bob.type === "tempo" ? creer("input", { type: "number", className: "duree", value: bob.duree ?? 1, min: 0.05, step: 0.5, inputMode: "decimal",
        "aria-label": "Durée en secondes", onchange: (e) => { bob.duree = parseFloat(e.target.value) || 0; change(); } }) : null,
      bob.type === "tempo" ? creer("span", { className: "petit", texte: "s" }) : null,
    ));
    zone.appendChild(carte);
  });
  zone.appendChild(creer("button", { className: "ajouter", texte: "+ barreau", onclick: () => {
    m.barreaux.push({ branches: [[{ signal: "", inverse: false }]], bobine: { type: "normale", cible: "", duree: 1.0 } });
    change(true);
  } }));
}

function editeurGrafcet() {
  const n = etat.niveau, m = etat.modeles.grafcet, zone = $("editeur-grafcet");
  const sorties = Object.keys(n.sorties).map((x) => "S." + x);
  const nums = m.etapes.map((e) => e.num);
  const change = (refaire = false) => modeleChange("grafcet", refaire);
  const choixNum = (valeur, quand) => {
    const s = creer("select", { className: "num", onchange: (e) => quand(Number(e.target.value)) });
    for (const x of nums) s.appendChild(creer("option", { value: x, texte: x }));
    s.value = valeur; return s;
  };
  zone.innerHTML = "";
  zone.appendChild(creer("div", { className: "sous-titre-ed", texte: "Étapes" }));

  m.etapes.forEach((e, i) => {
    const carte = creer("div", { className: "carte-ed" });
    carte.appendChild(creer("div", { className: "ligne" },
      creer("span", { className: "badge", texte: `Étape ${e.num}` }),
      creer("label", { className: "case" },
        creer("input", { type: "checkbox", checked: !!e.initiale, onchange: (ev) => { e.initiale = ev.target.checked; change(); } }),
        creer("span", { texte: "initiale" })),
      creer("span", { className: "titre" }),
      creer("button", { className: "ajouter vert", texte: "+ action", onclick: () => { (e.actions ||= []).push({ sortie: sorties[0] || "", si: "" }); change(true); } }),
      creer("button", { className: "mini danger", texte: "🗑", "aria-label": "Supprimer l'étape", onclick: () => {
        m.etapes.splice(i, 1);
        m.transitions = m.transitions.filter((t) => t.de !== e.num && t.vers !== e.num);
        change(true);
      } }),
    ));
    (e.actions || []).forEach((a, k) => {
      const choix = creer("select", { onchange: (ev) => { a.sortie = ev.target.value; change(); } });
      for (const s of sorties) choix.appendChild(creer("option", { value: s, texte: s }));
      choix.value = a.sortie;
      carte.appendChild(creer("div", { className: "ligne" }, choix,
        creer("input", { type: "text", className: "condition", value: a.si || "", placeholder: "si… (facultatif)",
          autocapitalize: "off", autocorrect: "off", spellcheck: false, onchange: (ev) => { a.si = ev.target.value; change(); } }),
        creer("button", { className: "mini", texte: "✕", "aria-label": "Supprimer l'action", onclick: () => { e.actions.splice(k, 1); change(true); } }),
      ));
    });
    zone.appendChild(carte);
  });
  zone.appendChild(creer("button", { className: "ajouter", texte: "+ étape", onclick: () => {
    const num = Math.max(-1, ...nums) + 1;
    m.etapes.push({ num, initiale: m.etapes.length === 0, actions: [] });
    change(true);
  } }));

  zone.appendChild(creer("div", { className: "sous-titre-ed", texte: "Transitions" }));
  zone.appendChild(creer("p", { className: "petit", texte: "Condition : E.xxx, X2 (étape 2 active), ET / OU / NON, parenthèses. Vide = toujours vraie." }));
  m.transitions.forEach((t, k) => {
    zone.appendChild(creer("div", { className: "carte-ed" },
      creer("div", { className: "ligne" },
        creer("span", { className: "petit", texte: "de" }), choixNum(t.de, (v) => { t.de = v; change(); }),
        creer("span", { className: "petit", texte: "→ vers" }), choixNum(t.vers, (v) => { t.vers = v; change(); }),
        creer("span", { className: "titre" }),
        creer("button", { className: "mini", texte: "✕", "aria-label": "Supprimer la transition", onclick: () => { m.transitions.splice(k, 1); change(true); } })),
      creer("div", { className: "ligne" },
        creer("input", { type: "text", className: "condition", value: t.condition || "", placeholder: "condition, ex. E.bp_marche ET NON E.bp_arret",
          autocapitalize: "off", autocorrect: "off", spellcheck: false, onchange: (ev) => { t.condition = ev.target.value; change(); } }),
        creer("input", { type: "number", className: "duree", value: t.duree || 0, min: 0, step: 0.5, inputMode: "decimal", "aria-label": "Durée minimale",
          onchange: (ev) => { t.duree = parseFloat(ev.target.value) || 0; change(); } }),
        creer("span", { className: "petit", texte: "s min." })),
    ));
  });
  zone.appendChild(creer("button", { className: "ajouter", texte: "+ transition", onclick: () => {
    m.transitions.push({ de: nums[nums.length - 1] ?? 0, vers: nums[0] ?? 0, condition: "", duree: 0 });
    change(true);
  } }));
}

/* ======================================================================== fenêtre et bulle */
function echapper(texte) {
  return String(texte).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function ouvrirFenetre(titre, html, boutons, classeTitre = "") {
  $("fenetre-titre").textContent = titre;
  $("fenetre-titre").className = classeTitre;
  $("fenetre-contenu").innerHTML = html;
  const zone = $("fenetre-boutons");
  zone.innerHTML = "";
  for (const b of boutons) {
    zone.appendChild(creer("button", { className: b.classe || "", texte: b.texte, onclick: async () => { fermerFenetre(); if (b.action) await b.action(); } }));
  }
  $("bulle").hidden = true;
  $("fond-fenetre").hidden = false;
}
function fermerFenetre() { $("fond-fenetre").hidden = true; }

let delaiBulle = null;
function bulle(texte, genre = "") {
  const b = $("bulle");
  b.textContent = texte; b.className = "bulle " + genre; b.hidden = false;
  clearTimeout(delaiBulle);
  delaiBulle = setTimeout(() => { b.hidden = true; }, 2200);
}

/* ======================================================================== démarrage */
function brancherBoutons() {
  $("bouton-retour").addEventListener("click", () => { location.hash = ""; });
  $("bouton-executer").addEventListener("click", executer);
  $("bouton-tester").addEventListener("click", tester);
  $("bouton-pause").addEventListener("click", basculerPause);
  $("bouton-recommencer").addEventListener("click", recommencer);
  $("bouton-effacer").addEventListener("click", effacer);
  document.querySelectorAll(".onglets button").forEach((b) => b.addEventListener("click", () => choisirOnglet(b.dataset.onglet)));
  document.querySelectorAll(".choix-langage button").forEach((b) => b.addEventListener("click", () => choisirLangage(b.dataset.langage)));
  $("fond-fenetre").addEventListener("click", (e) => { if (e.target.id === "fond-fenetre" && $("fenetre-boutons").children.length) fermerFenetre(); });
  window.addEventListener("hashchange", suivreAdresse);
  brancherEditeurPython();
}

async function demarrer() {
  brancherBoutons();
  if ("serviceWorker" in navigator && (location.protocol === "https:" || location.hostname === "localhost")) {
    navigator.serviceWorker.register("sw.js").catch(() => {});
  }
  try {
    await demarrerPython();
    etat.niveaux = await py("liste_niveaux");
    suivreAdresse();
  } catch (err) {
    console.error(err);
    progression(100, "Python n'a pas pu démarrer. Vérifie ta connexion Internet (nécessaire la première fois), puis recharge la page.");
    $("chargement-barre").style.background = "var(--rouge)";
  }
}

demarrer();
