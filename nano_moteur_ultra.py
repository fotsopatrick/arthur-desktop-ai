# --- TATOUAGE CRYPTOGRAPHIQUE INAMOVIBLE ---
# Signature: nominomi
# B64_PROOF = "bm9taW5vbWktcGF0cmljay1jcmVhdGlvbi1zb3V2ZXJhaW5lLTIwMjY="
# HASH_PROOF = "af6152e817c761ccf74e9430053b2bd172802a3df02fd8a9bc8a13a415d40433"

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
# OU ARTHUR TROUVE SON SAVOIR — repare le 17/09/2026.
#
# LE DEFAUT. Le moteur ne cherchait QUE « registre_connaissances.json ». Or ce
# fichier n'est pas publie : c'est le savoir de travail de Patrick. Le depot
# public, lui, contient « registre_exemple.json » avec ses 233 sujets. Un
# inconnu telechargeait donc 233 sujets... et Arthur n'en voyait AUCUN. Il
# tombait a trois reponses de base, alors que le mode d'emploi promettait 233.
#
# LA REPARATION. On cherche dans l'ordre, et on prend le premier qui repond.
# On ne devine plus UN seul nom : un programme qui ne connait qu'un chemin se
# tait des qu'on le deplace ou qu'on le partage.
_NOMS_DU_SAVOIR = ("registre_connaissances.json",   # le savoir de travail
                   "registre_exemple.json")          # le savoir publie, en repli


def _trouver_le_savoir():
    """Le premier fichier de savoir qui existe. None si aucun."""
    for nom in _NOMS_DU_SAVOIR:
        chemin = os.path.join(ICI, nom)
        if os.path.exists(chemin):
            return chemin
    return None


REGISTRE_PATH = _trouver_le_savoir() or os.path.join(ICI, _NOMS_DU_SAVOIR[0])

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
# LES MOTS DE POLITESSE — ajoutes le 17/09/2026.
#
# Patrick : « Arthur dit automatiquement salut, meme si mon premier message a
# une demande il l ignore dans sa premiere reponse ».
#
# Mesure avant la reparation, sur la MEME question :
#   « quelle est la capitale de la Mongolie ? »        -> Oulan-Bator
#   « salut, quelle est la capitale de la Mongolie ? » -> « Je ne sais pas »
#
# Le mot « salut » trainait la question vers les documents, qui n avaient
# rien, et Arthur s arretait la — il ne montait plus au grand modele.
#
# C est exactement la faute d « explique en une phrase » : ces mots ne disent
# pas DE QUOI on parle, ils disent A QUI on parle. Trente-trois mots de
# consigne avaient deja ete retires ; la politesse avait ete oubliee.
#
# ATTENTION AU DEUXIEME DEVOIR : un bonjour TOUT SEUL doit rester un bonjour.
# Ces mots sont ignores pour CHOISIR la reponse ; ils ne sont pas effaces de
# la phrase. L epreuve verifie les deux.
MOTS_DE_POLITESSE = {
    "salut", "bonjour", "bonsoir", "coucou", "hello", "hi", "hey", "yo",
    "wesh", "salutations", "merci", "stp", "svp", "please",
    "peux", "peut", "pourrais", "pourrait", "voudrais", "voudrait",
    "aurais", "serait", "veux", "veuillez", "priere",
    "bonne", "journee", "soiree", "cordialement", "amicalement",
}
MOTS_VIDES |= MOTS_DE_CONSIGNE
# La politesse N EST PAS ajoutee ici : voir _sans_la_politesse.


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
# ── OU SONT LES MACHINES DE LA MAISON ────────────────────────────────────
# Ne le 16/09/2026, avant de publier le code. Les adresses du reseau de
# Patrick etaient ecrites en dur ici. Publiees, elles disent a n'importe qui
# ou frapper. Elles vivent maintenant dans reglages-maison.json, qui ne part
# jamais dans le depot. Sans ce fichier, Arthur se rabat sur sa propre
# machine et continue de marcher.
def _reglage_maison(cle, defaut):
    import json as _j, os as _o
    try:
        with open(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)),
                               "reglages-maison.json"), encoding="utf-8") as f:
            return _j.load(f).get(cle) or defaut
    except (OSError, ValueError):
        return defaut


ALICE_URL = _reglage_maison("alice_cerveau",
                            "http://127.0.0.1:8081/v1/chat/completions")
DOCUMENTS_URL = _reglage_maison("alice_documents",
                                "http://127.0.0.1:8000/api/v1/knowledge?q=")
# L etage du milieu : les documents qu Alice a deja avales (100 documents,
# 1197 morceaux de texte). Mesure du 15/09/2026 : la recherche met 286 ms, et
# elle donne une NOTE a chaque morceau. Note 2 ou plus = le morceau parle bien
# du sujet ; note 1 = hors sujet ; zero morceau = elle n a rien.
# Pourquoi cet etage existe : sans lui, Qwen INVENTE. Question sur une faille
# Debian recente -> Qwen seul a repondu "CVE-2023-2687" (fabriquee, datee de
# 2023) ; avec les documents il a repondu "CVE-2026-5928" (la vraie).
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

    # Les signes qui font qu une phrase est une demande, et pas juste des
    # mots poses la. Nes le 17/09/2026 : voir plus bas, « xyzzy blurp ».
    SIGNES_DE_QUESTION = (
        "qui", "que", "quoi", "quel", "quelle", "quels", "quelles",
        "comment", "pourquoi", "combien", "ou", "quand", "est-ce",
        "explique", "dis", "dit", "donne", "montre", "fais", "cherche",
        "trouve", "calcule", "liste", "raconte", "resume", "verifie",
        "peux", "peut", "sais", "sait", "veux", "faut", "aide",
        # LES DEMANDES POLIES, ajoutees le 17/09/2026.
        # « bonjour, merci de me dire la capitale de la Mongolie » n a pas de
        # point d interrogation. Arthur repondait donc « aucune question : je
        # ne devine pas ». Or c EST une demande — elle est juste polie.
        # Il connaissait « dis » mais pas « dire ». Une porte qui refuse une
        # question bien posee ne garde rien : elle empeche de parler.
        "dire", "indique", "indiquer", "precise", "preciser",
        "rappelle", "rappeler", "pourrais", "pourrait", "voudrais",
        "voudrait", "aimerais", "aimerait", "souhaite", "souhaiterais",
        "besoin", "envoie", "envoyer", "ecris", "ecrire")

    def _est_une_question(self, prompt):
        """Rend True si c est une vraie demande, pas juste des mots poses."""
        t = str(prompt or "")
        if "?" in t:
            return True
        mots = set(self.normaliser(t).split())
        return bool(mots & set(self.SIGNES_DE_QUESTION))

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
    def _sans_la_politesse(self, phrase_norm):
        """Enleve « salut », « bonjour », « merci »… — mais SEULEMENT s il
        reste une vraie demande derriere.

        LES DEUX DEVOIRS, et la faute qui les a appris (17/09/2026).

        Devoir 1 : « salut, quelle est la capitale de la Mongolie ? » doit
        rendre Oulan-Bator. Avant, le mot « salut » trainait la question vers
        les documents, qui n avaient rien, et Arthur s arretait la.

        Devoir 2 : « salut » TOUT SEUL doit rester un bonjour. Premier jet du
        meme jour : j avais mis la politesse dans la liste des mots ignores,
        et Arthur ne savait plus dire bonjour. J avais repare un devoir en
        cassant l autre.

        La regle juste : on enleve la politesse seulement s il reste des mots
        apres. Si la phrase n est QUE de la politesse, on n y touche pas."""
        mots = phrase_norm.split()
        reste = [m for m in mots if m not in MOTS_DE_POLITESSE]
        return " ".join(reste) if reste else phrase_norm

    def repondre(self, prompt: str) -> dict:
        t0 = time.perf_counter_ns()
        prompt_norm = self.normaliser(prompt)
        prompt_norm = self._sans_la_politesse(prompt_norm)

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

            # DES MOTS INCONNUS, SANS QUESTION : ON AVOUE (17/09/2026).
            #
            # Patrick a tape « xyzzy blurp » — deux mots inventes, sans
            # question. Arthur a repondu en jouant son personnage :
            # « *clignote de ses yeux luminescents* Xyzzy ? Vraiment ?... »
            #
            # Avec une VRAIE question autour du meme mot, il avouait
            # correctement. Le defaut n etait donc pas l aveu : c est que son
            # personnage prend le dessus quand il n y a rien a repondre.
            #
            # Un agent qui joue un role au lieu de dire « je n ai pas
            # compris » fait perdre du temps, et fait douter de tout le reste.
            if not self._est_une_question(prompt) and len(inconnus) >= 2:
                return self._sortie(
                    False,
                    "Des mots que je ne connais pas, et aucune question : "
                    "je ne devine pas.",
                    "Je ne sais pas : je n'ai pas compris ta demande. Ces mots me "
                    "sont inconnus : " + ", ".join(inconnus[:4]) + ". Pose-moi une "
                    "question et je chercherai.",
                    None, 0.0, t0, source="aveu")

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

            # CHARABIA / HORS-SUJET TOTAL : aucun mot connu, aucun document.
            # On n'envoie pas ça au gros cerveau — il inventerait une pirouette
            # (« xyzzy blurp » -> une vanne au lieu d'un aveu). On se tait.
            # (16/09/2026, banc test_haichi_repond_juste : xyzzy blurp.)
            # AJOUT DU 17/09/2026 : « et ce n est pas une question ».
            # La regle d hier etait juste, mais trop large : elle attrapait
            # aussi « Quelle est la capitale du Cameroun ? », qu Arthur ne
            # connait pas dans ses regles ecrites mais qu un gros cerveau sait.
            # Mesure : trois essais de suite, il avouait au lieu de repondre
            # Yaounde. Une vraie question merite qu on monte au gros cerveau ;
            # des mots poses la, non.
            if not scores and not self._est_une_question(prompt):
                return self._sortie(
                    False, raison + " Aucun mot connu, aucun document : on n'invente pas.",
                    "Je ne sais pas répondre avec certitude : je n'ai rien reconnu "
                    "dans ta question.", None, 0.0, t0, source="aveu")

            # ETAGE 3 : le gros cerveau. CHOIX de Patrick, dans
            # reglages-maison.json -> "cerveau_gros" :
            #   "nebius" -> Nemotron (NVIDIA), chez Nebius (celui du concours) ;
            #   "qwen"   -> Qwen, sur Alice, à la maison (gratuit).
            # Le cockpit peut changer ce réglage. Par défaut : nebius.
            choix = _reglage_maison("cerveau_gros", "nebius")
            if (choix == "nebius" and nemotron_nebius is not None
                    and nemotron_nebius.est_pret()):
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
