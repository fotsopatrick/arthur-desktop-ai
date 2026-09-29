#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rag_local.py — les documents d'Arthur, cherches SUR CETTE MACHINE.

Ne le 29/09/2026. Jusqu'ici, l'etage « documents » d'Arthur n'existait que
chez Patrick : il appelait la memoire d'Alice (une autre machine, port 8000)
ou une commande « rag_maison » absente du depot. Chez n'importe qui d'autre,
cet etage etait vide et Arthur avouait meme quand la reponse etait ecrite
dans un fichier a cote de lui.

Ce RAG-ci :
  - ne telecharge rien, n'appelle aucun serveur, n'a besoin d'aucun paquet ;
  - lit les fichiers .md et .txt du dossier documents/ (et des dossiers
    listes dans reglages-maison.json -> "rag_dossiers", ou dans la variable
    ARTHUR_DOCUMENTS, separes par « : ») ;
  - les coupe en morceaux et les classe par BM25 (le calcul des moteurs de
    recherche classiques : un mot rare pese plus qu'un mot banal) ;
  - rend les meilleurs morceaux AVEC leur source. Il ne repond pas lui-meme :
    c'est le moteur qui decide si les morceaux parlent vraiment de la
    question (MOTS_RETROUVES_MINIMUM), et qui avoue sinon.

Il parle le meme langage que « rag_maison » :
    python3 rag_local.py --json-chercher "ma question"
rend une liste JSON de {"source", "texte", "score"}.
"""
import json
import math
import os
import re
import sys
import unicodedata

ICI = os.path.dirname(os.path.abspath(__file__))
DOSSIER_PAR_DEFAUT = os.path.join(ICI, "documents")
EXTENSIONS = (".md", ".txt")
# Un LISEZ-MOI explique le dossier : ce n'est pas un savoir a chercher.
IGNORES = {"lisez-moi.md", "readme.md"}
TAILLE_MORCEAU = 700          # caracteres, comme les extraits d'Alice
K1, B = 1.5, 0.75             # les deux reglages classiques de BM25

MOTS_VIDES = {
    "le", "la", "les", "un", "une", "des", "du", "de", "d", "l", "c", "s", "n",
    "et", "ou", "a", "au", "aux", "en", "par", "pour", "sur", "dans", "avec",
    "est", "ce", "cet", "cette", "que", "qu", "qui", "quoi", "quel", "quelle",
    "quels", "quelles", "comment", "pourquoi", "quand", "je", "tu", "il",
    "elle", "on", "nous", "vous", "ils", "elles", "me", "te", "se", "mon",
    "ma", "mes", "ton", "ta", "tes", "son", "sa", "ses", "pas", "ne", "plus",
    "y", "sont", "etre", "fait", "faire", "the", "of", "and", "to", "is",
}


def normaliser(texte):
    """minuscules, sans accents, rien que des lettres et des chiffres."""
    t = unicodedata.normalize("NFD", str(texte or "").lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def mots_de(texte):
    return [m for m in normaliser(texte).split() if m not in MOTS_VIDES and len(m) > 1]


def dossiers():
    """Ou chercher, dans l'ordre : ARTHUR_DOCUMENTS, puis le reglage
    « rag_dossiers », puis documents/ a cote de ce fichier."""
    env = os.environ.get("ARTHUR_DOCUMENTS")
    if env:
        return [os.path.expanduser(d) for d in env.split(":") if d]
    try:
        with open(os.path.join(ICI, "reglages-maison.json"), encoding="utf-8") as f:
            liste = json.load(f).get("rag_dossiers")
        if isinstance(liste, list) and liste:
            return [os.path.expanduser(str(d)) for d in liste]
    except (OSError, ValueError, AttributeError):
        pass
    return [DOSSIER_PAR_DEFAUT]


def _fichiers(liste_dossiers):
    for dossier in liste_dossiers:
        if not os.path.isdir(dossier):
            continue
        for racine, _, noms in os.walk(dossier):
            for nom in sorted(noms):
                if nom.lower().endswith(EXTENSIONS) and nom.lower() not in IGNORES:
                    yield os.path.join(racine, nom)


def _decouper(texte):
    """Des morceaux d'environ TAILLE_MORCEAU caracteres, coupes aux
    paragraphes : une phrase n'est jamais coupee en deux si on peut l'eviter."""
    morceaux, courant = [], ""
    for para in re.split(r"\n\s*\n", texte):
        para = para.strip()
        if not para:
            continue
        if courant and len(courant) + len(para) + 2 > TAILLE_MORCEAU:
            morceaux.append(courant)
            courant = ""
        while len(para) > TAILLE_MORCEAU:        # un tres long paragraphe
            morceaux.append(para[:TAILLE_MORCEAU])
            para = para[TAILLE_MORCEAU:]
        courant = (courant + "\n\n" + para) if courant else para
    if courant:
        morceaux.append(courant)
    return morceaux


class Index:
    """L'index BM25 des morceaux. Refait tout seul quand un fichier change."""

    def __init__(self, liste_dossiers=None):
        self.liste_dossiers = liste_dossiers
        self._signature = None
        self.morceaux = []        # [(source, texte, compte_des_mots, longueur)]
        self.df = {}
        self.longueur_moyenne = 0.0

    def _signature_actuelle(self):
        sig = []
        for chemin in _fichiers(self.liste_dossiers or dossiers()):
            try:
                st = os.stat(chemin)
                sig.append((chemin, st.st_mtime_ns, st.st_size))
            except OSError:
                pass
        return tuple(sig)

    def _a_jour(self):
        sig = self._signature_actuelle()
        if sig == self._signature:
            return
        self.morceaux, self.df = [], {}
        for chemin, _, _ in sig:
            try:
                with open(chemin, encoding="utf-8", errors="strict") as f:
                    texte = f.read()
            except (OSError, UnicodeDecodeError):
                continue              # un fichier illisible ne casse pas l'index
            source = os.path.relpath(chemin, ICI) if chemin.startswith(ICI) else chemin
            for bout in _decouper(texte):
                mots = mots_de(bout)
                if not mots:
                    continue
                compte = {}
                for m in mots:
                    compte[m] = compte.get(m, 0) + 1
                self.morceaux.append((source, bout, compte, len(mots)))
                for m in compte:
                    self.df[m] = self.df.get(m, 0) + 1
        n = len(self.morceaux)
        self.longueur_moyenne = (sum(m[3] for m in self.morceaux) / n) if n else 0.0
        self._signature = sig

    def chercher(self, question, k=3):
        """Les k meilleurs morceaux : [{"source", "texte", "score"}], du
        meilleur au moins bon. Liste vide si rien ne partage un mot."""
        self._a_jour()
        termes = set(mots_de(question))
        n = len(self.morceaux)
        if not termes or not n:
            return []
        resultats = []
        for source, texte, compte, longueur in self.morceaux:
            score = 0.0
            for t in termes:
                tf = compte.get(t)
                if not tf:
                    continue
                idf = math.log(1 + (n - self.df[t] + 0.5) / (self.df[t] + 0.5))
                score += idf * tf * (K1 + 1) / (
                    tf + K1 * (1 - B + B * longueur / (self.longueur_moyenne or 1)))
            if score > 0:
                resultats.append({"source": source, "texte": texte,
                                  "score": round(score, 3)})
        resultats.sort(key=lambda r: (-r["score"], r["source"]))
        return resultats[:k]

    def taille(self):
        self._a_jour()
        return {"fichiers": len(self._signature or ()), "morceaux": len(self.morceaux)}


_INDEX = None


def chercher(question, k=3):
    """Raccourci : un index partage par tout le programme."""
    global _INDEX
    if _INDEX is None:
        _INDEX = Index()
    return _INDEX.chercher(question, k)


def main(argv):
    if "--json-chercher" in argv:
        i = argv.index("--json-chercher")
        question = argv[i + 1] if i + 1 < len(argv) else ""
        print(json.dumps(chercher(question), ensure_ascii=False))
        return 0
    if "--etat" in argv:
        idx = Index()
        print(json.dumps({"dossiers": dossiers(), **idx.taille()}, ensure_ascii=False))
        return 0
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
