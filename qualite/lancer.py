#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""qualite/lancer.py — TOUS les tests d'Arthur, leur couverture, un tableau.

    python3 qualite/lancer.py              tout, puis le tableau de bord
    python3 qualite/lancer.py --vite       seulement tests/ (pytest)
    python3 qualite/lancer.py --serie X    une seule serie (nom de fichier)
    python3 qualite/lancer.py --page       refaire la page depuis le dernier resultat

Resultat : qualite/rapport/index.html (a ouvrir dans un navigateur, sans
internet) et qualite/rapport/resultats.json.

TOUT EST DANS LE DEPOT. pytest vient de vendor/, la mesure de couverture est
ecrite avec la bibliotheque standard (qualite/traceur.py). Chaque serie tourne
dans son propre processus, avec un HOME jetable : aucun test ne touche aux
vrais ~/.secrets, ~/.config ou ~/.claude de la machine.
"""
import concurrent.futures
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

QUALITE = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(QUALITE)
VENDOR = os.path.join(RACINE, "vendor")
AMORCE = os.path.join(QUALITE, "amorce")
RAPPORT = os.path.join(QUALITE, "rapport")
PATIENCE = 300

sys.path.insert(0, QUALITE)
import analyse  # noqa: E402

# Une serie ROUGE parce qu'il manque une chose EXTERIEURE au depot n'est pas
# une regression : on la classe « sautee » et on nomme ce qui manque. Seule
# une serie deja rouge est reclassee (meme regle que tous-les-tests.sh).
BESOINS = [
    (re.compile(r"errno 111\] connection refused", re.I), "le cockpit local (127.0.0.1:8790)"),
    (re.compile(r"pas pu lancer la connexion"), "un acces ssh a la tour"),
    (re.compile(r"No module named 'gi'|cannot import name '_gi'"), "GTK (python3-gi)"),
    (re.compile(r"outils/pilote-page\.py"), "~/outils/pilote-page.py"),
    (re.compile(r"registre_connaissances\.json'"), "le registre de travail prive"),
    (re.compile(r"9222/json/version|navigateur.*pas ouvert", re.I), "un navigateur ouvert"),
    (re.compile(r"pas d'image .* \(ni docker\)"), "docker"),
    (re.compile(r"le compagnon Haichi n est pas lance"), "un bureau graphique avec l'avatar lance"),
]

EPREUVE = re.compile(r"^\s*(VERT|ROUGE|OK|RATE|✓|✗|~)\s{1,}(.+?)\s*$")


def decouvrir(vite=False, seule=None):
    """Les series de tests, dans l'ordre : pytest (parallele), puis scripts."""
    series = []
    dossier = os.path.join(RACINE, "tests")
    for nom in sorted(os.listdir(dossier)):
        if nom.startswith("test_") and nom.endswith(".py"):
            series.append({"id": "tests/" + nom, "type": "pytest",
                           "chemin": os.path.join(dossier, nom), "parallele": True})
    if not vite:
        for nom in sorted(os.listdir(RACINE)):
            chemin = os.path.join(RACINE, nom)
            if nom.startswith("test_") and nom.endswith(".py"):
                series.append({"id": nom, "type": "script", "chemin": chemin, "parallele": False})
            elif nom.startswith("test_") and nom.endswith(".sh"):
                series.append({"id": nom, "type": "shell", "chemin": chemin, "parallele": False})
    if seule:
        series = [s for s in series if seule in s["id"]]
    return series


def _environnement(serie, dossier_couv, home):
    env = dict(os.environ)
    chemins = [AMORCE, VENDOR, RACINE] + [p for p in env.get("PYTHONPATH", "").split(os.pathsep) if p]
    env.update({"PYTHONPATH": os.pathsep.join(chemins),
                "ARTHUR_COUV_DOSSIER": dossier_couv,
                "ARTHUR_COUV_TEST": serie["id"],
                "HOME": home,
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTEST_ADDOPTS": "",
                # aucun greffon pytest installe sur la machine n'est charge :
                # seul le pytest de vendor/ tourne (independant du systeme)
                "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"})
    return env


def _commande(serie, junit):
    if serie["type"] == "pytest":
        return [sys.executable, "-m", "pytest", "-q", "-rs", "-p", "no:cacheprovider",
                "--rootdir", RACINE, "--junitxml", junit, serie["chemin"]]
    if serie["type"] == "shell":
        return ["bash", serie["chemin"]]
    return [sys.executable, serie["chemin"]]


def _epreuves_junit(junit):
    try:
        racine = ET.parse(junit).getroot()
    except (OSError, ET.ParseError):
        return []
    sortie = []
    for cas in racine.iter("testcase"):
        etat, detail = "vert", ""
        for enfant in cas:
            if enfant.tag in ("failure", "error"):
                etat, detail = "rouge", (enfant.get("message") or "")[:300]
            elif enfant.tag == "skipped":
                etat, detail = "saute", (enfant.get("message") or "")[:300]
        sortie.append({"nom": cas.get("name"), "etat": etat, "detail": detail,
                       "duree": round(float(cas.get("time") or 0), 3)})
    return sortie


def _epreuves_texte(sortie):
    liste = []
    for ligne in sortie.splitlines():
        m = EPREUVE.match(ligne)
        if m:
            mot = m.group(1)
            etat = {"VERT": "vert", "OK": "vert", "✓": "vert",
                    "ROUGE": "rouge", "RATE": "rouge", "✗": "rouge"}.get(mot, "saute")
            liste.append({"nom": m.group(2)[:160], "etat": etat, "detail": "", "duree": 0})
    return liste


def _bilan_rouges(sortie):
    """Nombre de rouges annonces par le bilan d'un script, ou None."""
    trouves = re.findall(r"([0-9]+) (?:rouge|ratees?)", sortie, re.I)
    if trouves:
        return int(trouves[-1])
    if re.search(r"^Ran [0-9]+ tests? in", sortie, re.M):
        return 0 if re.search(r"^OK( \(|$)", sortie, re.M) else 1
    return None


def executer(serie, base):
    ident = re.sub(r"[^A-Za-z0-9_.-]", "_", serie["id"])
    dossier_couv = os.path.join(base, "couv", ident)
    home = os.path.join(base, "home", ident)
    os.makedirs(home, exist_ok=True)
    junit = os.path.join(base, ident + ".xml")
    t0 = time.time()
    try:
        r = subprocess.run(_commande(serie, junit), cwd=RACINE, capture_output=True, text=True,
                           env=_environnement(serie, dossier_couv, home), timeout=PATIENCE)
        code, sortie = r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired as e:
        code = -9
        sortie = ((e.stdout or b"").decode("utf-8", "replace") if isinstance(e.stdout, bytes)
                  else (e.stdout or "")) + "\n[plus de %d s : arretee]" % PATIENCE
    duree = round(time.time() - t0, 1)

    epreuves = _epreuves_junit(junit) if serie["type"] == "pytest" else _epreuves_texte(sortie)
    rouges = _bilan_rouges(sortie) if serie["type"] != "pytest" else None
    # pytest rend 5 quand il n'y a rien a lancer (module entierement saute)
    code_ok = code == 0 or (serie["type"] == "pytest" and code == 5)
    rouge = not code_ok or (rouges or 0) > 0 or any(e["etat"] == "rouge" for e in epreuves)
    etat, raison = ("rouge" if rouge else "vert"), ""
    if code == -9:
        raison = "trop long (plus de %d s)" % PATIENCE
    if rouge:
        for motif, besoin in BESOINS:
            if motif.search(sortie):
                etat, raison = "saute", "a besoin de " + besoin
                break
    if serie["type"] == "pytest" and not rouge and epreuves and \
            all(e["etat"] == "saute" for e in epreuves):
        m = re.search(r"^SKIPPED \[\d+\] [^:]+(?::\d+)?: (.+)$", sortie, re.M)
        etat, raison = "saute", (m.group(1) if m else epreuves[0]["detail"]) or "tout est saute"

    return {"id": serie["id"], "type": serie["type"], "etat": etat, "raison": raison,
            "code": code, "duree": duree, "epreuves": epreuves,
            "sortie": sortie[-6000:], "resume": _resume(serie["chemin"]),
            "dossier_couv": dossier_couv}


def _resume(chemin):
    """La premiere phrase de la docstring (ou du commentaire d'en-tete)."""
    try:
        with open(chemin, encoding="utf-8", errors="replace") as f:
            tete = f.read(3000)
    except OSError:
        return ""
    m = re.search(r'"""\s*(.+?)(?:\n\s*\n|""")', tete, re.S)
    if m:
        texte = m.group(1)
    else:
        texte = " ".join(l.lstrip("# ").strip() for l in tete.splitlines()[1:6]
                         if l.startswith("#") and not l.startswith("#!"))
    return re.sub(r"\s+", " ", texte).strip()[:220]


def _lire_couverture(resultats):
    """{fichier: {ligne: set(series)}} a partir des traces de chaque serie."""
    carte = {}
    for res in resultats:
        dossier = res.pop("dossier_couv")
        if not os.path.isdir(dossier):
            continue
        for nom in os.listdir(dossier):
            try:
                with open(os.path.join(dossier, nom), encoding="utf-8") as f:
                    d = json.load(f)
            except (OSError, ValueError):
                continue
            for fichier, lignes in d.get("lignes", {}).items():
                par_ligne = carte.setdefault(fichier, {})
                for n in lignes:
                    par_ligne.setdefault(n, set()).add(res["id"])
    return carte


def _groupe(relatif):
    tete = relatif.split(os.sep)[0]
    if tete.endswith(".py"):
        return "coeur"
    return tete


def construire(resultats, duree_totale):
    carte = _lire_couverture(resultats)
    modules = []
    for chemin in analyse.fichiers_d_arthur(RACINE):
        par_ligne = carte.get(os.path.abspath(chemin), {})
        m = analyse.analyser_fichier(chemin, RACINE, set(par_ligne), par_ligne)
        if not m["executables"] and not m.get("erreur"):
            continue            # un fichier sans code (__init__.py vide) : rien a tester
        m["groupe"] = _groupe(m["fichier"])
        modules.append(m)
    total_exe = sum(m["executables"] for m in modules)
    total_cou = sum(m["couvertes"] for m in modules)
    fonctions = [f for m in modules for f in m["fonctions"]]
    epreuves = [e for r in resultats for e in r["epreuves"]]
    return {
        "date": datetime.datetime.now().isoformat(timespec="seconds"),
        "duree": round(duree_totale, 1),
        "python": sys.version.split()[0],
        "seuil": analyse.SEUIL_COUVERT,
        "totaux": {
            "pourcent": round(100.0 * total_cou / total_exe, 1) if total_exe else 0.0,
            "lignes": total_exe, "couvertes": total_cou,
            "modules": len(modules),
            "couverts": sum(m["verdict"] == "couvert" for m in modules),
            "incomplets": sum(m["verdict"] == "incomplet" for m in modules),
            "sans_test": sum(m["verdict"] == "sans test" for m in modules),
            "fonctions": len(fonctions),
            "fonctions_jamais": sum(f["etat"] == "jamais appelee" for f in fonctions),
            "series": len(resultats),
            "series_vertes": sum(r["etat"] == "vert" for r in resultats),
            "series_rouges": sum(r["etat"] == "rouge" for r in resultats),
            "series_sautees": sum(r["etat"] == "saute" for r in resultats),
            "epreuves": len(epreuves),
            "epreuves_vertes": sum(e["etat"] == "vert" for e in epreuves),
        },
        "modules": modules,
        "series": resultats,
    }


def _lire_historique():
    try:
        with open(os.path.join(RAPPORT, "historique.json"), encoding="utf-8") as f:
            h = json.load(f)
        return h if isinstance(h, list) else []
    except (OSError, ValueError):
        return []


def _historique(donnees):
    chemin = os.path.join(RAPPORT, "historique.json")
    try:
        with open(chemin, encoding="utf-8") as f:
            histo = json.load(f)
        if not isinstance(histo, list):
            histo = []
    except (OSError, ValueError):
        histo = []
    t = donnees["totaux"]
    histo.append({"date": donnees["date"], "pourcent": t["pourcent"],
                  "vertes": t["series_vertes"], "rouges": t["series_rouges"]})
    histo = histo[-60:]
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(histo, f)
    return histo


def main(argv):
    if "--page" in argv:
        # refaire seulement la page a partir du dernier resultats.json
        import tableau
        with open(os.path.join(RAPPORT, "resultats.json"), encoding="utf-8") as f:
            print(tableau.ecrire(json.load(f), os.path.join(RAPPORT, "index.html")))
        return 0
    vite = "--vite" in argv
    seule = argv[argv.index("--serie") + 1] if "--serie" in argv else None
    series = decouvrir(vite, seule)
    if not series:
        print("Aucune serie de tests trouvee.")
        return 1
    base = tempfile.mkdtemp(prefix="arthur-tests-")
    print("Arthur : %d series de tests (pytest depuis vendor/, couverture stdlib)" % len(series))
    t0 = time.time()
    resultats = []

    def afficher(r):
        signe = {"vert": "✓", "rouge": "✗", "saute": "~"}[r["etat"]]
        print("  %s %-46s %6.1f s  %s" % (signe, r["id"], r["duree"], r["raison"]), flush=True)

    paralleles = [s for s in series if s["parallele"]]
    sequentielles = [s for s in series if not s["parallele"]]
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(6, os.cpu_count() or 2)) as pool:
        for r in pool.map(lambda s: executer(s, base), paralleles):
            afficher(r)
            resultats.append(r)
    for s in sequentielles:
        r = executer(s, base)
        afficher(r)
        resultats.append(r)

    donnees = construire(resultats, time.time() - t0)
    os.makedirs(RAPPORT, exist_ok=True)
    # l'historique ne garde que les mesures COMPLETES (pas --vite ni --serie) :
    # sinon la courbe melangerait des mesures partielles
    donnees["historique"] = _historique(donnees) if not (vite or seule) else _lire_historique()
    with open(os.path.join(RAPPORT, "resultats.json"), "w", encoding="utf-8") as f:
        json.dump(donnees, f, ensure_ascii=False)
    import tableau
    page = tableau.ecrire(donnees, os.path.join(RAPPORT, "index.html"))
    shutil.rmtree(base, ignore_errors=True)

    t = donnees["totaux"]
    print()
    print("  Couverture : %.1f %%  (%d lignes sur %d)" % (t["pourcent"], t["couvertes"], t["lignes"]))
    print("  Modules    : %d couverts · %d incomplets · %d sans test (sur %d)"
          % (t["couverts"], t["incomplets"], t["sans_test"], t["modules"]))
    print("  Series     : %d vertes · %d rouges · %d sautees"
          % (t["series_vertes"], t["series_rouges"], t["series_sautees"]))
    print("  Tableau    : %s" % page)
    return 1 if t["series_rouges"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
