#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
nano_moteur_ultra.py — le cerveau d'Haichi.

Il repond a partir de regles ecrites, jamais d'invention.
Trois regles de conduite, nees de trois fautes reelles du 15/09/2026 :
  1. Un mot cache dans un autre mot ne compte PAS ("tour" dans "detournement").
  2. Un mot peut appartenir a PLUSIEURS sujets : on les garde tous, on ne
     laisse pas le dernier charge ecraser les autres.
  3. Quand rien ne correspond, on dit "je ne sais pas". On n'invente pas.
"""

import time
import os
import json
import re
import difflib

# Les OUTILS : ils vont VOIR l etat reel (l heure, les modules allumes, la
# veille du matin) au lieu de reciter une regle qui ne change jamais.
try:
    import haichi_outils
except Exception:
    haichi_outils = None

# Le gros cerveau du concours : Nemotron, de NVIDIA, heberge chez Nebius.
# Il remplace Qwen QUAND SA CLE EST LA. Sinon Arthur garde Qwen, sur Alice.
# Aucune des deux n'est obligatoire : sans aucune, Arthur avoue, et c'est tout.
try:
    import nemotron_nebius
except Exception:
    nemotron_nebius = None

ICI = os.path.dirname(os.path.abspath(__file__))
REGISTRE_PATH = os.path.join(ICI, "registre_connaissances.json")

# Les mots qui ne designent aucun sujet : ils ne doivent jamais faire pencher
# la balance ("la", "de", "comment"...).
MOTS_VIDES = {
    "le", "la", "les", "un", "une", "des", "du", "de", "d", "l", "c", "s", "n",
    "et", "ou", "a", "au", "aux", "en", "par", "pour", "sur", "dans", "avec",
    "est", "ce", "cet", "cette", "que", "qu", "qui", "quoi", "quel", "quelle",
    "comment", "pourquoi", "ou", "quand", "je", "tu", "il", "elle", "on",
    "nous", "vous", "ils", "elles", "me", "te", "se", "moi", "toi", "mon",
    "ma", "mes", "ton", "ta", "tes", "son", "sa", "ses", "notre", "votre",
    "leur", "pas", "ne", "plus", "tout", "tous", "toute", "toutes", "y",
    "fait", "faire", "dis", "dit", "veux", "peux", "peut", "sais", "sait",
    # mots de question, trop banals : on les retrouve dans n importe quel texte
    # francais, donc ils ne prouvent rien. Sans eux, "Combien font 17 multiplie
    # par 4" partait chercher dans les documents pour rien (mesure du 15/09).
    "combien", "font", "donne", "donnent", "touche", "appelle", "sert", "servent",
    "existe", "trouve", "parle", "concerne", "signifie", "veut", "pense",
    # mots trop repandus : on les croise partout, ils ne prouvent rien non plus.
    # Sans eux, "le plus grand ocean du monde" allait lire les documents pour
    # rien (4,5 s au lieu de 2 s) — mesure du 15/09/2026.
    "grand", "grande", "grands", "petit", "petite", "monde", "chose", "choses",
    "annee", "annees", "jour", "jours", "temps", "gens", "personne", "personnes",
    "premier", "premiere", "dernier", "derniere", "autre", "autres", "meme",
}

# ── LES MOTS DE CONSIGNE ─────────────────────────────────────────────────────
# Ne le 16/09/2026. A « explique en une phrase ce qu'est un transistor »,
# Arthur sortait un circuit sur l'accueil des nouveaux. Pourquoi : « explique »
# et « phrase » se trouvent dans des circuits. Deux mots touches, c'est assez
# pour qu'un circuit gagne — et il gagnait.
#
# Or ces mots ne disent pas DE QUOI on parle, ils disent COMMENT repondre.
# « explique en une phrase » et « explique en trois lignes » parlent du meme
# sujet. Ils ne doivent donc jamais servir a choisir la reponse.
MOTS_DE_CONSIGNE = {
    "explique", "expliques", "expliquer", "explication",
    "resume", "resumes", "resumer", "decris", "decrire", "detaille",
    "raconte", "raconter", "dis", "dire", "redige", "rediger", "ecris",
    "phrase", "phrases", "ligne", "lignes", "mot", "mots",
    "court", "courte", "bref", "brievement", "simplement", "clairement",
    "vite", "rapidement", "exemple", "exemples",
}
MOTS_VIDES |= MOTS_DE_CONSIGNE


# Les sujets de base. Ils GAGNENT sur le registre : si le registre contient
# deja un sujet du meme nom, on garde la reponse d'ici et on ajoute ses mots.
BASE_INITIALE = {
    "salutations": {
        "mots": ["salut", "bonjour", "coucou", "hello", "hi", "bonsoir", "yo", "hey", "ca va", "wesh", "salutations"],
        "think": "Prise de contact et salutation chaleureuse.",
        "answer": "Salut Patrick ! 🔭 Je suis Haichi / Petit Braignak. Je reponds a partir de regles ecrites, en moins d'un millieme de seconde. Pose-moi une question sur nos agents, la tour, Docker ou nos circuits."
    },
    "docker_infra": {
        "mots": ["docker", "dokcer", "conteneur", "conteneurs", "docker-compose", "image docker", "cgroups"],
        "think": "Explication de la technologie de conteneurisation Docker sous Linux et son role sur La Tour.",
        "answer": "🐋 DOCKER & LES CONTENEURS DANS LA TOUR DE CONTRÔLE :\n\n• Concept : Docker isole les applications sous Linux via les namespaces et cgroups du noyau.\n• Avantage : Démarrage instantané et zéro surcharge par rapport à une VM.\n• Sur La Tour : nos services (Caddy, Odoo, PostgreSQL) tournent dans des conteneurs isolés supervisés."
    },
    "tour_presentation": {
        "mots": ["tour", "matourdecontrole", "tour de controle", "ma tour de controle", "c est quoi la tour"],
        "think": "Présentation générale de Ma Tour de Contrôle et de ses piliers.",
        "answer": "🗼 LA TOUR DE CONTRÔLE (matourdecontrole.fr) :\n\nPlateforme souveraine de pilotage et d'orchestration d'agents IA. Elle garantit qu'aucun agent n'agit sans preuve, sans test préalable et sans circuit validé. Tout y est mesuré et observable."
    },
}

# Haichi n'est pas fait pour les medecins. Ces sujets de sante restent dans le
# registre (rien n'est perdu) mais Haichi ne les lit pas et n'en parle jamais.
SUJETS_ECARTES = {
    "sante_prep_indetectable",
    "labo_vih_docking",
    "test_dynamique_hepatite_delta",
    "hepatite_c_epclusa",
}

# Haichi n'est pas fait pour les medecins (Patrick, 15/09/2026). Une question
# de sante ne part JAMAIS chez le renfort : le renfort, lui, y repondrait.
MOTS_SANTE = {
    "prep", "prp", "tpe", "vih", "sida", "hepatite", "hepatites", "virus",
    "viral", "virale", "serologie", "depistage", "preservatif", "tenofovir",
    "emtricitabine", "indetectable", "intransmissible", "charge virale",
    "maladie", "traitement", "medecin", "medecins", "symptome", "symptomes",
    "medicament", "medicaments", "infection", "contamination", "epidemie",
}

REFUS_SANTE = ("Je ne sais pas répondre avec certitude. Je ne traite pas les "
               "questions de santé — je suis fait pour la tour, pas pour les "
               "médecins.")

# ── LE RENFORT ────────────────────────────────────────────────────────────
# Quand Haichi ne sait pas, il ne devine pas : il demande a Qwen, le modele
# qui tourne sur Alice, l autre machine de la maison.
ALICE_URL = "http://192.168.1.61:8081/v1/chat/completions"
# L etage du milieu : les documents qu Alice a deja avales (100 documents,
# 1197 morceaux de texte). Mesure du 15/09/2026 : la recherche met 286 ms, et
# elle donne une NOTE a chaque morceau. Note 2 ou plus = le morceau parle bien
# du sujet ; note 1 = hors sujet ; zero morceau = elle n a rien.
# Pourquoi cet etage existe : sans lui, Qwen INVENTE. Question sur une faille
# Debian recente -> Qwen seul a repondu "CVE-2023-2687" (fabriquee, datee de
# 2023) ; avec les documents il a repondu "CVE-2026-5928" (la vraie).
DOCUMENTS_URL = "http://192.168.1.61:8000/api/v1/knowledge?q="
# La "note" rendue par la recherche n est PAS fiable : "17 multiplie par 4"
# obtient 2 et "le plus grand ocean" obtient 3, alors que les documents ne
# parlent ni de l un ni de l autre. Elle compte les mots qui se ressemblent.
# La regle qui marche, mesuree le 15/09/2026 : on compte combien de MOTS
# IMPORTANTS de la question se retrouvent vraiment dans les extraits.
#   17 multiplie par 4    -> 0 mot retrouve   -> on n utilise pas les documents
#   capitale du Cameroun  -> 1 mot            -> on n utilise pas
#   faille noyau Debian   -> 4 mots sur 4     -> on lit les documents
#   Anthropic emploi      -> 3 mots sur 3     -> on lit les documents
MOTS_RETROUVES_MINIMUM = 2
DOCUMENTS_PATIENCE = 20

# Quand la machine est seule (carte reseau debranchee), Alice est injoignable.
# Sans memoire, Haichi retentait a chaque question et faisait patienter
# 7 secondes pour rien (mesure du 15/09/2026). Il retient donc son echec
# pendant une demi-minute, et avoue tout de suite pendant ce temps.
ALICE_MUETTE_JUSQUA = [0.0]      # une case, partagee par tout le moteur
ALICE_REPOS = 30                 # secondes avant de retenter
ALICE_PATIENCE = 90          # secondes accordees a Alice
MOTS_INCONNUS_MAX = 1        # 2 mots longs inconnus ou plus -> Haichi se tait

# Le vocabulaire de la maison. Mesure du 15/09/2026 : Qwen sur Alice repond
# 0 fois juste sur 7 questions concernant la tour — et il INVENTE (il a dit
# que le "circuit Zorglub" etait une course automobile sur la tour Eiffel).
# Donc une question qui parle de la maison ne part JAMAIS chez Alice :
# soit Haichi sait, soit il avoue.
VOCABULAIRE_MAISON = {
    "tour", "tours", "circuit", "circuits", "agent", "agents", "cockpit",
    "vitrine", "braignak", "victor", "chloe", "clark", "alice", "mirline",
    "haichi", "competence", "competences", "garde", "gardes", "chantier",
    "livreur", "odoo", "vps", "matourdecontrole", "carte", "accueil",
    "equipe", "portes", "porte", "atelier", "beelzebuth", "salium",
}

CONSIGNE_ALICE = (
    "Reponds en francais, en trois phrases au maximum. "
    "Si tu ne connais pas la reponse avec certitude, dis simplement "
    "\"Je ne sais pas\" — n invente jamais."
)

REPLI = "Je ne sais pas répondre avec certitude. Aucune règle écrite ne correspond à ta question — tu peux en ajouter une dans le registre."


class NanoMoteurUltraEngine:
    def __init__(self):
        self.base = {}
        self.charger()

    # --- construction de la base -------------------------------------------
    def charger(self):
        # 1) le registre d'abord (les 233 savoirs et circuits)
        if os.path.exists(REGISTRE_PATH):
            try:
                data = json.load(open(REGISTRE_PATH, encoding="utf-8"))
                for k, v in data.items():
                    if k in SUJETS_ECARTES:
                        continue
                    if isinstance(v, dict) and "mots" in v and "answer" in v:
                        self.base[k] = dict(v)
            except Exception:
                pass
        # 2) les sujets de base PAR-DESSUS : leur reponse gagne, leurs mots
        #    s'ajoutent a ceux du registre.
        for k, v in BASE_INITIALE.items():
            mots = list(v["mots"])
            if k in self.base:
                for m in self.base[k].get("mots", []):
                    if m not in mots:
                        mots.append(m)
            self.base[k] = {"mots": mots, "think": v["think"], "answer": v["answer"]}
        self.reconstruire_index()

    def reconstruire_index(self):
        # un mot peut mener a PLUSIEURS sujets : on garde la liste entiere.
        brut = {}
        for cle, item in self.base.items():
            for m in item.get("mots", []):
                mn = self.normaliser(m)
                if mn and mn not in MOTS_VIDES:
                    brut.setdefault(mn, set()).add(cle)

        # Les mots-cles des 157 procedures ont ete ramasses automatiquement :
        # on y trouve des mots sans valeur comme "marche", "par" ou "sur".
        # Un mot present dans 3 procedures ou plus ne designe plus aucune
        # procedure — sinon "comment marche la prep" reveille n'importe quoi.
        self.index = {}
        for mot, cles in brut.items():
            circuits = {c for c in cles if c.startswith("circuit")}
            autres = cles - circuits
            garde = set(autres)
            if len(circuits) < 3:
                garde |= circuits
            if garde:
                self.index[mot] = garde
        # les mots simples servent au rattrapage des fautes de frappe
        self.mots_simples = [m for m in self.index if " " not in m and len(m) >= 5]

    @staticmethod
    def normaliser(texte: str) -> str:
        t = (texte or "").lower().strip()
        t = re.sub(r"[éèêë]", "e", t)
        t = re.sub(r"[àâä]", "a", t)
        t = re.sub(r"[ùûü]", "u", t)
        t = re.sub(r"[îï]", "i", t)
        t = re.sub(r"[ôö]", "o", t)
        t = re.sub(r"[ç]", "c", t)
        t = re.sub(r"[^\w\s]", " ", t)
        return " ".join(t.split())

    def mots_longs_inconnus(self, prompt_norm):
        """Les mots importants de la question qu'Haichi n'a jamais vus.
        Deux ou plus, et il ne sait pas de quoi on lui parle."""
        toks = [t for t in prompt_norm.split() if t not in MOTS_VIDES and len(t) >= 5]
        return [t for t in toks if t not in self.index]

    @staticmethod
    def alice_est_injoignable():
        return time.time() < ALICE_MUETTE_JUSQUA[0]

    @staticmethod
    def noter_alice_muette():
        ALICE_MUETTE_JUSQUA[0] = time.time() + ALICE_REPOS

    def chercher_dans_les_documents(self, question):
        if self.alice_est_injoignable():
            return None, 0
        """Rend (extraits, combien) ou (None, 0) si rien d assez pertinent."""
        import urllib.request, urllib.parse
        try:
            url = DOCUMENTS_URL + urllib.parse.quote(question[:300])
            d = json.loads(urllib.request.urlopen(url, timeout=DOCUMENTS_PATIENCE)
                           .read().decode("utf-8"))
        except Exception:
            self.noter_alice_muette()
            return None, 0
        morceaux = d.get("resultats", [])
        if not morceaux:
            return None, 0
        extraits = "\n\n".join((r.get("contenu") or "")[:700] for r in morceaux[:3])

        # Les extraits parlent-ils VRAIMENT de la question ?
        dedans = self.normaliser(extraits)
        importants = [m for m in self.normaliser(question).split()
                      if m not in MOTS_VIDES and len(m) >= 5]
        retrouves = [m for m in importants if m in dedans]
        if len(retrouves) < MOTS_RETROUVES_MINIMUM:
            return None, 0
        return extraits, len(retrouves)

    def demander_a_alice(self, question, extraits=None):
        if self.alice_est_injoignable():
            return None, "Alice est injoignable (constate il y a moins de 30 secondes)."
        """On passe la main a Qwen sur Alice. Rend (reponse, panne)."""
        import urllib.request
        consigne = CONSIGNE_ALICE
        if extraits:
            consigne += ("\n\nVoici des extraits de documents recents de la maison. "
                         "Reponds UNIQUEMENT a partir d eux, et cite les chiffres "
                         "exacts qu ils contiennent :\n" + extraits[:2600])
        charge = json.dumps({
            "model": "qwen",
            "messages": [
                {"role": "system", "content": consigne},
                {"role": "user", "content": question},
            ],
            "max_tokens": 200,
            "temperature": 0,
        }).encode("utf-8")
        req = urllib.request.Request(ALICE_URL, data=charge,
                                     headers={"Content-Type": "application/json"})
        try:
            d = json.loads(urllib.request.urlopen(req, timeout=ALICE_PATIENCE)
                           .read().decode("utf-8"))
            return d["choices"][0]["message"]["content"].strip(), None
        except Exception as e:
            self.noter_alice_muette()
            return None, str(e)[:120]

    # --- la reponse ---------------------------------------------------------
    def repondre(self, prompt: str) -> dict:
        t0 = time.perf_counter_ns()
        prompt_norm = self.normaliser(prompt)

        if not prompt_norm:
            return self._sortie(False, "Recherche vide.", "Pose-moi une question.", None, 0.0, t0)

        # ETAGE 0 : un OUTIL sait-il repondre ? Un outil va voir maintenant.
        # Il passe avant les regles, parce qu une regle ne connait pas l heure.
        if haichi_outils is not None:
            outil = haichi_outils.chercher_un_outil(prompt_norm)
            if outil is not None:
                try:
                    return self._sortie(True, "Je suis alle voir sur la machine.",
                                        outil(), "outil", 100, t0, source="outil")
                except Exception as e:
                    return self._sortie(False, "L outil n a pas repondu.",
                                        "Je n arrive pas a aller voir : " + str(e)[:80],
                                        None, 0.0, t0, source="aveu")

        tokens = [t for t in prompt_norm.split() if t not in MOTS_VIDES]
        scores = {}

        # Une question qui parle de procedure a le droit de reveiller les circuits.
        veut_circuit = any(t in ("circuit", "circuits", "procedure", "procedures",
                                 "etape", "etapes", "chaine") for t in tokens)

        def poids_sujet(cle):
            # Les 157 "circuits" sont des procedures internes. Ils ne doivent pas
            # repondre a une question de definition : on les met en second rang,
            # sauf si la question demande justement une procedure.
            if cle.startswith("circuit"):
                return 2 if veut_circuit else 1
            return 2

        def ajouter(cles, poids):
            for c in cles:
                scores[c] = scores.get(c, 0) + poids * poids_sujet(c)

        # 1) une EXPRESSION entiere presente dans la question : le signal le plus sur.
        for kw, cles in self.index.items():
            if " " in kw and kw in prompt_norm:
                ajouter(cles, 30 + 10 * len(kw.split()))

        # 2) un MOT ENTIER de la question qui est un mot-cle. Un mot RARE vaut
        #    plus qu'un mot banal : "beelzebuth" ne designe qu'un seul sujet,
        #    "tour" en designe 21, donc "beelzebuth" est bien plus parlant.
        for tok in tokens:
            cles = self.index.get(tok)
            if cles:
                # rarete du mot + longueur du mot. A rarete egale, le mot le
                # plus long est le plus precis : dans "les agents de la tour",
                # "agents" (6 lettres) l'emporte sur "tour" (4 lettres).
                ajouter(cles, max(2, round(60.0 / len(cles))) + len(tok))

        # 3) rattrapage des fautes de frappe, SEULEMENT si rien n'a marche.
        if not scores:
            for tok in tokens:
                if len(tok) < 5:
                    continue
                proches = difflib.get_close_matches(tok, self.mots_simples, n=1, cutoff=0.86)
                for pr in proches:
                    ajouter(self.index[pr], 5)

        # 4) Haichi sait-il seulement de quoi on lui parle ? Si deux mots
        #    importants de la question lui sont inconnus, il se tait et passe
        #    la main — meme si un mot de decor comme "tour" a fait du bruit.
        inconnus = self.mots_longs_inconnus(prompt_norm)
        if not scores or len(inconnus) > MOTS_INCONNUS_MAX:
            raison = ("Aucune règle écrite ne correspond." if not scores
                      else "Mots inconnus dans la question : " + ", ".join(inconnus[:4]))
            # Sante : on refuse net, avant meme de penser au renfort.
            mots_q = set(prompt_norm.split())
            if mots_q & MOTS_SANTE:
                return self._sortie(False, "Question de santé : hors de mon domaine.",
                                    REFUS_SANTE, None, 0.0, t0, source="aveu")

            # La question parle-t-elle de la maison ? Alors on n'ennuie pas
            # Alice : elle inventerait. On avoue.
            mots = set(prompt_norm.split())
            if mots & VOCABULAIRE_MAISON:
                quoi = ", ".join(sorted(mots & VOCABULAIRE_MAISON)[:3])
                return self._sortie(
                    False,
                    f"Question sur la maison ({quoi}) sans règle écrite. "
                    "Alice ne connaît pas la maison : on n'invente pas.",
                    "Je ne sais pas répondre avec certitude. C'est une question sur "
                    "la tour, et aucune règle écrite ne la couvre — tu peux en "
                    "ajouter une dans le registre.",
                    None, 0.0, t0, source="aveu")

            # ETAGE 2 : les documents deja avales. On ne monte au gros cerveau
            # qu apres avoir regarde si on a deja lu la reponse quelque part.
            extraits, combien = self.chercher_dans_les_documents(prompt)
            if extraits:
                reponse, panne = self.demander_a_alice(prompt, extraits)
                if reponse:
                    return self._sortie(
                        True,
                        raison + f" — {combien} document(s) trouve(s), lus avant de repondre.",
                        reponse, "documents", 0.0, t0, source="documents")

            # ETAGE 3 : le gros cerveau. Nemotron chez Nebius s'il a sa cle,
            # Qwen sur Alice sinon. Le concours exige Nemotron ; la maison
            # continue de marcher sans lui.
            if nemotron_nebius is not None and nemotron_nebius.est_pret():
                d = nemotron_nebius.demander(prompt)
                if d.get("reponse"):
                    return self._sortie(
                        True, raison + " — passe a Nemotron, chez Nebius.",
                        d["reponse"], "nemotron", 0.0, t0, source="nemotron")

            reponse, panne = self.demander_a_alice(prompt)
            if reponse:
                return self._sortie(True, raison + " — passé à Qwen sur Alice.",
                                    reponse, "alice", 0.0, t0, source="alice")
            raison += f" Alice n'a pas répondu ({panne})." if panne else ""
            return self._sortie(False, raison, REPLI, None, 0.0, t0, source="aveu")

        # a score egal, on tranche toujours pareil : le sujet de base d'abord,
        # puis l'ordre alphabetique. Jamais au hasard.
        def rang(cle):
            return (scores[cle], 1 if cle in BASE_INITIALE else 0, cle)
        meilleure = max(scores, key=rang)

        item = self.base[meilleure]
        return self._sortie(True, item.get("think", "Correspondance déterministe."),
                            item.get("answer", ""), meilleure, scores[meilleure], t0)

    @staticmethod
    def _sortie(matched, think, answer, cle, score, t0, source="haichi"):
        duree_us = (time.perf_counter_ns() - t0) / 1000.0
        return {
            "matched": matched,
            "raw_output": f"<think>{think}</think><answer>{answer}</answer>",
            "answer": answer,
            "thought": think,
            "score": score,
            "cle": cle,
            "latency_us": round(duree_us, 2),
            "latency_ms": round(duree_us / 1000.0, 4),
            "source": source,
        }


ENGINE = NanoMoteurUltraEngine()


def nano_moteur_ultra(prompt: str) -> dict:
    return ENGINE.repondre(prompt)


if __name__ == "__main__":
    for q in ["salut", "dokcer", "qu est ce que la tour", "les agents de la tour",
              "comment marche la prep", "la carte vivante", "xyzzy blurp", "le vih"]:
        r = nano_moteur_ultra(q)
        print(f"[{q}] -> {r['cle']} (score {r['score']}) : {r['answer'][:70]}")
