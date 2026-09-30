# -*- coding: utf-8 -*-
"""qualite/analyse.py — CE QUI POUVAIT TOURNER, ET CE QUI A TOURNE.

Pour chaque fichier d'Arthur :
  - les lignes EXECUTABLES : lues dans le code compile (dis.findlinestarts),
    pas devinees dans le texte ;
  - les FONCTIONS : lues dans l'arbre de syntaxe (ast), avec leurs lignes
    propres (sans celles des fonctions imbriquees) ;
  - les EXCLUSIONS, declarees et affichees : le bloc
    « if __name__ == "__main__": » (l'entree en ligne de commande) et toute
    instruction marquee « # pragma: no cover ».

Verdicts :
  couvert     >= SEUIL_COUVERT % des lignes executables ont tourne ;
  incomplet   au moins une ligne a tourne, mais moins que le seuil ;
  sans test   aucune ligne n'a tourne.
"""
import ast
import dis
import os
import types

SEUIL_COUVERT = 80.0


def lignes_executables(source, chemin):
    """Les numeros de ligne qui portent du code execute."""
    code = compile(source, chemin, "exec", dont_inherit=True)
    lignes, pile = set(), [code]
    while pile:
        c = pile.pop()
        for _, n in dis.findlinestarts(c):
            if n and n > 0:
                lignes.add(n)
        pile.extend(k for k in c.co_consts if isinstance(k, types.CodeType))
    return lignes


def _exclusions(arbre, source):
    """(lignes exclues, raisons) : le bloc __main__ et les « pragma: no cover »."""
    exclues, raisons = set(), []
    lignes_texte = source.splitlines()
    for noeud in arbre.body:
        if (isinstance(noeud, ast.If) and isinstance(noeud.test, ast.Compare)
                and isinstance(noeud.test.left, ast.Name) and noeud.test.left.id == "__name__"):
            exclues.update(range(noeud.lineno, noeud.end_lineno + 1))
            raisons.append({"lignes": [noeud.lineno, noeud.end_lineno],
                            "pourquoi": "entree en ligne de commande (__main__)"})
    for noeud in ast.walk(arbre):
        if not hasattr(noeud, "lineno") or not isinstance(noeud, ast.stmt):
            continue
        texte = lignes_texte[noeud.lineno - 1] if noeud.lineno <= len(lignes_texte) else ""
        if "pragma: no cover" in texte:
            exclues.update(range(noeud.lineno, noeud.end_lineno + 1))
            raisons.append({"lignes": [noeud.lineno, noeud.end_lineno],
                            "pourquoi": "marque « pragma: no cover »"})
    return exclues, raisons


def _fonctions(arbre):
    """[(nom qualifie, premiere ligne, derniere ligne, lignes des enfants)]."""
    sortie = []

    def visiter(noeud, prefixe):
        for enfant in ast.iter_child_nodes(noeud):
            if isinstance(enfant, (ast.FunctionDef, ast.AsyncFunctionDef)):
                nom = prefixe + enfant.name
                debut = min([d.lineno for d in enfant.decorator_list] + [enfant.lineno])
                imbriquees = set()
                for petit in ast.walk(enfant):
                    if petit is not enfant and isinstance(
                            petit, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                        if not isinstance(petit, ast.Lambda):
                            imbriquees.update(range(petit.lineno + 1, petit.end_lineno + 1))
                sortie.append((nom, debut, enfant.lineno, enfant.end_lineno, imbriquees))
                visiter(enfant, nom + ".")
            elif isinstance(enfant, ast.ClassDef):
                visiter(enfant, prefixe + enfant.name + ".")
            else:
                visiter(enfant, prefixe)

    visiter(arbre, "")
    return sortie


def verdict(pourcent, touchees):
    if not touchees:
        return "sans test"
    return "couvert" if pourcent >= SEUIL_COUVERT else "incomplet"


def analyser_fichier(chemin, racine, vues, tests_par_ligne=None):
    """Le bilan d'un fichier. vues : set des lignes qui ont tourne.
    tests_par_ligne : {ligne: set(noms de tests)} pour dire QUI couvre."""
    with open(chemin, encoding="utf-8", errors="replace") as f:
        source = f.read()
    relatif = os.path.relpath(chemin, racine)
    try:
        arbre = ast.parse(source, chemin)
        executables = lignes_executables(source, chemin)
    except SyntaxError as e:
        return {"fichier": relatif, "erreur": "syntaxe : %s" % e, "verdict": "sans test",
                "pourcent": 0.0, "executables": 0, "couvertes": 0, "fonctions": [],
                "manquees": [], "exclusions": [], "source": source.splitlines(),
                "tests": []}
    exclues, raisons = _exclusions(arbre, source)
    executables -= exclues
    couvertes = executables & set(vues)
    manquees = sorted(executables - couvertes)
    pourcent = round(100.0 * len(couvertes) / len(executables), 1) if executables else 100.0

    fonctions = []
    for nom, debut, ligne_def, fin, imbriquees in _fonctions(arbre):
        corps = {n for n in executables if ligne_def < n <= fin and n not in imbriquees}
        if not corps:
            continue
        faites = corps & couvertes
        p = round(100.0 * len(faites) / len(corps), 1)
        fonctions.append({"nom": nom, "ligne": ligne_def, "fin": fin,
                          "lignes": len(corps), "couvertes": len(faites), "pourcent": p,
                          "etat": "jamais appelee" if not faites else
                                  ("complete" if p >= 100 else "partielle")})

    qui = set()
    for n in couvertes:
        qui.update((tests_par_ligne or {}).get(n, ()))
    return {"fichier": relatif, "verdict": verdict(pourcent, couvertes),
            "pourcent": pourcent, "executables": len(executables),
            "couvertes": len(couvertes), "manquees": manquees,
            "lignes_couvertes": sorted(couvertes),
            "fonctions": fonctions, "exclusions": raisons,
            "tests": sorted(qui), "source": source.splitlines()}


def fichiers_d_arthur(racine):
    """Tous les fichiers .py d'Arthur a mesurer (le code, pas les tests)."""
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import traceur
    trouves = []
    for dossier, sous, noms in os.walk(racine):
        sous[:] = sorted(d for d in sous if not d.startswith(".") and d != "__pycache__")
        for nom in sorted(noms):
            chemin = os.path.join(dossier, nom)
            if traceur.fichier_suivi(chemin):
                trouves.append(chemin)
    return trouves
