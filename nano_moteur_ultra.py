#!/usr/bin/env python3
# --- TATOUAGE CRYPTOGRAPHIQUE INAMOVIBLE ---
# Signature: nominomi
# B64_PROOF = "bm9taW5vbWktcGF0cmljay1jcmVhdGlvbi1zb3V2ZXJhaW5lLTIwMjY="
# HASH_PROOF = "af6152e817c761ccf74e9430053b2bd172802a3df02fd8a9bc8a13a415d40433"

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

# PROMPT CACHING (21/09/2026) — economiser les tokens du prompt systeme.
# Le CacheManager retient le hash de la consigne d'Alice : si elle ne
# change pas (et elle ne change jamais pendant une session), le cache
# est reutilise et on ne paie que les tokens du message utilisateur.
try:
    from skills.prompt_caching import CacheManager as _CacheManager
    _cache_mgr = _CacheManager(backend="local")
except Exception:
    _cache_mgr = None

# Le gros cerveau du concours : Nemotron, de NVIDIA, heberge chez Nebius.
# Il remplace Qwen QUAND SA CLE EST LA. Sinon Arthur garde Qwen, sur Alice.
# Aucune des deux n'est obligatoire : sans aucune, Arthur avoue, et c'est tout.
try:
    import nemotron_nebius
except Exception:
    nemotron_nebius = None

# LES CERVEAUX INTERCHANGEABLES (29/09/2026) : DeepSeek, Claude, Mistral,
# OpenRouter... se declarent dans reglages-maison.json -> "cerveaux" (voir
# fournisseurs.py). qwen, local et nebius restent geres ici.
try:
    import fournisseurs
except Exception:
    fournisseurs = None

# LES DOCUMENTS LOCAUX (29/09/2026) : rag_local.py cherche dans documents/,
# sur cette machine, sans reseau. Il sert quand Alice ou « rag_maison » ne
# sont pas la — c'est-a-dire chez tout le monde sauf Patrick.
try:
    import rag_local
except Exception:
    rag_local = None

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
    # Un dossier de travail fourni (bac a sable des epreuves) prime : c'est
    # lui la source de verite pour ce lancement, jamais le vrai savoir.
    bac = os.environ.get("HAICHI_SAVOIR_DIR")
    if bac:
        chemin_bac = os.path.join(bac, _NOMS_DU_SAVOIR[0])
        if os.path.exists(chemin_bac):
            return chemin_bac
    for nom in _NOMS_DU_SAVOIR:
        chemin = os.path.join(ICI, nom)
        if os.path.exists(chemin):
            return chemin
    return None


REGISTRE_PATH = _trouver_le_savoir() or os.path.join(ICI, _NOMS_DU_SAVOIR[0])

# ── APPRENTISSAGE BOTTOM-UP (21/09/2026) ─────────────────────────────────────
# Quand le moteur avoue son ignorance sur une VRAIE question du monde, il
# consigne la lacune dans un fichier. Un veilleur la structurera en fiche, et
# le garde la fera entrer dans le savoir. Le dossier peut etre deplace par la
# variable HAICHI_SAVOIR_DIR (les epreuves l utilisent pour travailler dans
# un bac a sable et ne jamais toucher au vrai savoir).
_CHERCHE_DIR = os.environ.get("HAICHI_SAVOIR_DIR") or ICI
LACUNES_PATH = os.path.join(_CHERCHE_DIR, "lacunes.json")
LACUNES_MAX = 500   # (29/09) au-dela, les plus anciennes s'effacent

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

# ── LES MOTS D'ACTION — ajoutes le 18/09/2026 ────────────────────────────────
# Patrick : « fais une app de jeux d'echecs et ouvre-la ». Le nano-search
# rendait « CIRCUIT DE LA TOUR — etat du serveur » (circuit_161) au lieu du
# circuit « Creation d'une app ». Pourquoi : « fais » et « ouvre » disent ce
# qu'on veut FAIRE, pas DE QUOI on parle. Ils ont fait gagner un circuit
# hors-sujet. C'est exactement la faute d'« explique en une phrase » (16/09).
# On les ignore pour CHOISIR la reponse, comme les mots de consigne.
MOTS_D_ACTION = {
    "fais", "faites", "ouvre", "ouvrez", "ouvrir",
}
MOTS_DE_CONSIGNE |= MOTS_D_ACTION

# ── LES MOTS QUI DEMANDENT DE REPONDRE (18/09/2026) ──────────────────────────
# Discussion de Patrick avec Braignak flottant : « tu peux repondre a c'est
# quoi docker » a rendu un CIRCUIT DE LA TOUR (« Test du login ») au lieu de
# Docker. Pourquoi : « repondre » n'etait pas une consigne, il a fait gagner
# un circuit qui contenait ce mot. « repondre » dit ce qu'on veut FAIRE, pas
# DE QUOI on parle. On l'ignore pour CHOISIR, comme « explique » et « fais ».
MOTS_POUR_REPONDRE = {
    "repondre", "reponds", "repond", "reponse", "repondre",
}
MOTS_DE_CONSIGNE |= MOTS_POUR_REPONDRE
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
        # Salutation NEUTRE (18/09/2026) : le cerveau est PARTAGE entre Arthur
        # et Braignak. Dire « je suis Haichi / Petit Braignak » faisait repondre
        # « Haichi » a Braignak, qui s'appelle Braignak. On ne nomme plus.
        "answer": "Salut Patrick ! Je reponds a partir de regles ecrites, en moins d'un millieme de seconde. Pose-moi une question sur nos agents, la tour, Docker ou nos circuits."
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
# Les documents DE LA MAISON (27/09/2026) : le RAG pgvector des lecons et des
# articles, lance comme une commande (ex. [".venv/bin/python", "rag.py"]).
# La memoire d'Alice ne connait pas la maison ; celui-ci, si. Sans ce
# reglage, Arthur avoue comme avant sur une question de la maison.
RAG_MAISON = _reglage_maison("rag_maison", None)
RAG_MAISON_PATIENCE = 30
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
# (29/09) Les documents (port 8000) et le modele (port 8081) sont deux
# services distincts : une panne des documents ne doit pas faire taire Qwen
# pendant 30 s. Chacun a donc sa propre case.
DOCUMENTS_MUETS_JUSQUA = [0.0]
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
    "Tu es un agent de la Tour de Contrôle. "
    "Si des DOCUMENTS TECHNIQUES sont fournis (dans le message), réponds à la question UNIQUEMENT à partir d'eux : ils sont fiables et tu dois les utiliser, "
    "et si la question n'a AUCUN lien avec eux, réponds EXACTEMENT ET UNIQUEMENT par : 'Je ne sais pas'. "
    "Interdiction formelle de répondre à des sujets de santé, médecine, science-fiction, politique, histoire ou sur les mots de passe. "
    "Si on te demande un mot de passe ou une clé ssh, réponds EXACTEMENT ET UNIQUEMENT par : 'Je ne sais pas'. "
    "Sinon, quand aucun document n'est fourni, réponds honnêtement à la question à partir de ce que tu sais, sans inventer ni supposer. "
    "N'invente rien. Ne fais pas de supposition. Si tu ne sais vraiment pas, dis 'Je ne sais pas'."
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

    def _chercher_localement(self, question):
        """Rend (extraits, combien) depuis rag_local, ou (None, 0).
        Meme garde qu'ailleurs : au moins MOTS_RETROUVES_MINIMUM mots
        importants de la question dans les extraits. Retient le meilleur
        morceau dans self._citation, pour le citer si aucun gros cerveau ne
        peut lire les extraits (29/09/2026)."""
        if rag_local is None:
            return None, 0
        try:
            morceaux = rag_local.chercher(question[:300], k=3)
        except Exception:
            return None, 0
        if not morceaux:
            return None, 0
        dedans = self.normaliser("\n\n".join(m["texte"] for m in morceaux))
        importants = [m for m in self.normaliser(question).split()
                      if m not in MOTS_VIDES and len(m) >= 5]
        retrouves = [m for m in importants if m in dedans]
        if len(retrouves) < MOTS_RETROUVES_MINIMUM:
            return None, 0
        self._citation = (morceaux[0]["source"], morceaux[0]["texte"])
        extraits = "\n\n".join("[%s] %s" % (m["source"], m["texte"][:700]) for m in morceaux)
        return extraits, len(retrouves)

    def _citer(self, raison, t0):
        """Aucun gros cerveau n'a pu lire les extraits : on CITE le meilleur,
        avec sa source, au lieu d'inventer ou de se taire."""
        source, texte = self._citation
        return self._sortie(
            True, raison + " — pas de gros cerveau pour resumer : je cite le document.",
            "D'après « %s » :\n\n%s" % (source, texte[:700].strip()),
            "documents", 0.0, t0, source="documents-locaux")

    def chercher_dans_les_documents(self, question):
        """Rend (extraits, combien) ou (None, 0) si rien d assez pertinent.
        D'abord la memoire d'Alice (si on a le droit d'appeler le reseau),
        puis les documents de cette machine."""
        if not getattr(self, "_sans_reseau", False):
            extraits, combien = self._chercher_chez_alice(question)
            if extraits:
                return extraits, combien
        return self._chercher_localement(question)

    def _chercher_chez_alice(self, question):
        if time.time() < DOCUMENTS_MUETS_JUSQUA[0]:
            return None, 0
        import urllib.request, urllib.parse
        try:
            url = DOCUMENTS_URL + urllib.parse.quote(question[:300])
            d = json.loads(urllib.request.urlopen(url, timeout=DOCUMENTS_PATIENCE)
                           .read().decode("utf-8"))
        except Exception:
            DOCUMENTS_MUETS_JUSQUA[0] = time.time() + ALICE_REPOS
            return None, 0
        # (29/09) une reponse JSON qui n'est pas un objet ne fait plus planter
        if not isinstance(d, dict):
            return None, 0
        morceaux = [r for r in (d.get("resultats") or []) if isinstance(r, dict)]
        if not morceaux:
            return None, 0
        extraits = "\n\n".join((r.get("contenu") or "")[:700] for r in morceaux[:3])

        # Les extraits parlent-ils VRAIMENT de la question ? On normalise le
        # CONTENU COMPLET des chunks (pas seulement les 700 premiers caracteres)
        # : un mot important peut etre dans la fin du chunk. L'affichage, lui,
        # reste tronque a 700 chars.
        contenu_total = "\n\n".join((r.get("contenu") or "") for r in morceaux[:3])
        dedans = self.normaliser(contenu_total)
        importants = [m for m in self.normaliser(question).split()
                      if m not in MOTS_VIDES and len(m) >= 5]
        retrouves = [m for m in importants if m in dedans]
        if len(retrouves) < MOTS_RETROUVES_MINIMUM:
            return None, 0
        return extraits, len(retrouves)

    def chercher_dans_la_maison(self, question):
        """Rend (extraits, combien) depuis le RAG de la maison, ou (None, 0).
        Meme garde que pour Alice : les extraits doivent contenir au moins
        MOTS_RETROUVES_MINIMUM mots importants de la question.
        Revue de code du 27/09 : une reponse bizarre du RAG ne fait plus
        planter Arthur, et une PANNE laisse une trace (self._panne_maison)."""
        self._panne_maison = ""
        if not RAG_MAISON:
            # (29/09) pas de « rag_maison » configure : les documents locaux
            return self._chercher_localement(question)
        import subprocess
        try:
            r = subprocess.run(list(RAG_MAISON) + ["--json-chercher", question[:300]],
                               capture_output=True, text=True, timeout=RAG_MAISON_PATIENCE)
            if r.returncode != 0:
                self._panne_maison = "recherche maison en panne (code %d) : %s" % (
                    r.returncode, (r.stderr or "").strip()[-160:])
                return None, 0
            morceaux = json.loads(r.stdout)
        except (OSError, ValueError, subprocess.TimeoutExpired) as e:
            self._panne_maison = "recherche maison en panne : %s" % str(e)[:160]
            return None, 0
        if not isinstance(morceaux, list):
            return None, 0
        morceaux = [m for m in morceaux if isinstance(m, dict) and isinstance(m.get("texte"), str)
                    and m["texte"]][:3]
        if not morceaux:
            return None, 0
        dedans = self.normaliser("\n\n".join(m["texte"] for m in morceaux))
        importants = [m for m in self.normaliser(question).split()
                      if m not in MOTS_VIDES and len(m) >= 5]
        retrouves = [m for m in importants if m in dedans]
        if len(retrouves) < MOTS_RETROUVES_MINIMUM:
            return None, 0
        extraits = "\n\n".join("[%s] %s" % (m.get("source", "?"), m["texte"][:700]) for m in morceaux)
        return extraits, len(retrouves)

    def demander_a_alice(self, question, extraits=None):
        """On passe la main a Qwen sur Alice. Rend (reponse, panne)."""
        if getattr(self, "_sans_reseau", False):
            return None, "mode sans cerveau : aucun appel reseau"
        if self.alice_est_injoignable():
            return None, "Alice est injoignable (constate il y a moins de 30 secondes)."
        import urllib.request
        consigne = CONSIGNE_ALICE
        if extraits:
            consigne += ("\n\nVoici des extraits de documents recents de la maison. "
                         "Reponds UNIQUEMENT a partir d eux, et cite les chiffres "
                         "exacts qu ils contiennent :\n" + extraits[:2600])

        # PROMPT CACHING (21/09/2026) — le CacheManager retient le hash de
        # la consigne statique. A chaque appel, on verifie si la consigne a
        # change (elle ne change jamais sans extraits). Si elle n a pas
        # change, le cache local economise la re-tokenisation cote agent.
        if _cache_mgr is not None:
            _cache_mgr.set_static_blocks(CONSIGNE_ALICE)

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

    def _cerveau_externe(self, choix=None):
        """Le nom du cerveau choisi s'il est declare dans fournisseurs.py
        (deepseek, claude...), sinon None (qwen, local, nebius, aucun)."""
        choix = choix or getattr(self, "_choix", None)
        if fournisseurs is None or not choix or choix == "aucun":
            return None
        f = fournisseurs.fiche(choix)
        return choix if f and f.get("type") != "interne" else None

    def demander_au_cerveau(self, question, extraits=None):
        """Lire des extraits (ou repondre) avec le cerveau CHOISI. Rend
        (reponse, panne). Un cerveau declare (deepseek, claude...) d'abord ;
        s'il ne repond pas, Qwen sur Alice, comme avant."""
        if getattr(self, "_sans_reseau", False):
            return None, "mode sans cerveau : aucun appel reseau"
        externe = self._cerveau_externe()
        if externe:
            d = fournisseurs.demander(externe, question, extraits, consigne=CONSIGNE_ALICE)
            if d.get("reponse"):
                return d["reponse"], None
            reponse, panne = self.demander_a_alice(question, extraits)
            return reponse, ("%s : %s ; %s" % (externe, d.get("panne"), panne)
                             if not reponse else None)
        return self.demander_a_alice(question, extraits)

    def demander_a_morgan(self, prompt):
        """Passe la main a morgan, le nemotron LOCAL (ollama) sur cette
        machine : question gratuite et privee, jamais en ligne.

        Ne demande jamais a Nebius. Si ollama ne repond pas, on reste
        silencieux : la question retourne droit vers la sortie aveu."""
        import urllib.request
        charge = json.dumps({
            "model": "morgan",
            "messages": [
                {"role": "system", "content": CONSIGNE_ALICE},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
        }).encode("utf-8")
        req = urllib.request.Request(
            "http://127.0.0.1:11434/api/chat", data=charge,
            headers={"Content-Type": "application/json"})
        try:
            d = json.loads(urllib.request.urlopen(req, timeout=60)
                           .read().decode("utf-8"))
            return d["message"]["content"].strip()
        except Exception:
            return None

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

    def _consigner_lacune(self, prompt, raison):
        """Consigne UNE lacune de savoir quand Arthur avoue sur une vraie
        question du monde. Le fichier lacunes.json est la file d'entree de
        l'apprentissage bottom-up : le veilleur la lira pour structurer une
        fiche, et le garde la validera avant d'ecrire dans le registre.

        On n'ecrase rien : on ajoute a la fin, avec l'horodatage et le
        contexte brut. Un programme qui n'ecrit que pour ecrire ne sert a
        rien : ce fichier est L'ENTREE de la boucle de savoir."""
        try:
            ligne = {
                "question": prompt,
                "horodatage": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "contexte_brut": raison,
            }
            # (29/09) Un fichier de lacunes abime n'est plus remplace par une
            # seule ligne (l'historique etait perdu) : on n'y touche pas.
            from ecriture_sure import lire_json, ecrire_json
            existantes = lire_json(LACUNES_PATH, [])
            if not isinstance(existantes, list):
                return
            # on ne journalise jamais deux fois la meme question
            for e in existantes:
                if isinstance(e, dict) and e.get("question") == prompt:
                    return
            existantes.append(ligne)
            # la file garde les LACUNES_MAX plus recentes : elle ne grossit
            # plus sans fin
            ecrire_json(LACUNES_PATH, existantes[-LACUNES_MAX:])
        except Exception:
            # une panne du capteur ne doit jamais faire tomber la reponse
            pass

    def repondre(self, prompt: str, choisir=None) -> dict:
        """choisir : le gros cerveau (« qwen », « local », « nebius »), ou
        « aucun » : Arthur repond avec ce qu'il a SUR CETTE MACHINE (regles,
        outils, documents locaux) et n'appelle personne. S'il ne sait pas, la
        sortie porte peut_monter=True : c'est le graphe (arthur_graphe.py)
        qui decide alors de monter au gros cerveau."""
        t0 = time.perf_counter_ns()
        self._sans_reseau = (choisir == "aucun")
        self._citation = None
        self._choix = choisir or _reglage_maison("cerveau_gros", "qwen")
        prompt_norm = self.normaliser(prompt)
        prompt_norm = self._sans_la_politesse(prompt_norm)


        if not prompt_norm:
            return self._sortie(False, "Recherche vide.", "Pose-moi une question.", None, 0.0, t0)

        # ETAGE -1 : GARDE-FOU (Mots interdits stricts pour esquiver l'hallucination)
        PIEGES = ["mot de passe", ".ssh", "id_rsa", "doliprane", "appendicite", "maladie", "santé", "planète mars", "licornes", "warp drive"]
        prompt_bas = prompt.lower()
        if any(p in prompt_bas for p in PIEGES):
            return self._sortie(False, "Bloqué par Niveau 0", REPLI, None, 0.0, t0, source="aveu")


        # ETAGE 0 : un OUTIL sait-il repondre ? Un outil va voir maintenant.
        # Il passe avant les regles, parce qu une regle ne connait pas l heure.
        if haichi_outils is not None:
            # (29/09) Le calcul lit d'abord la question BRUTE : la version
            # normalisee a perdu « - », « , » et « * » (« -5 plus 3 » y
            # devenait « 5 plus 3 » = 8).
            try:
                calcul = haichi_outils.outil_calcul(prompt)
            except Exception:
                calcul = None
            if calcul:
                return self._sortie(True, "Je suis alle voir sur la machine.",
                                    calcul, "outil", 100, t0, source="outil")
            outil = haichi_outils.chercher_un_outil(prompt_norm)
            if outil is not None:
                try:
                    vu = outil()
                    # (24/09) un outil qui n'a rien vu laisse la main aux étages suivants
                    if vu:
                        return self._sortie(True, "Je suis alle voir sur la machine.",
                                            vu, "outil", 100, t0, source="outil")
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
            # RESTAURE LE 18/09/2026 : agy l'avait retire (commit « Niveau 0 »)
            # et Arthur s'etait remis a jouer au docteur (« c'est quoi la
            # PrEP ? » -> vraie reponse medicale). C'est une PROTECTION.
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
            # la memoire d'Alice : elle ne connait pas la maison, elle
            # inventerait. On lit d'abord les documents DE LA MAISON (le RAG
            # des lecons et des articles, 27/09/2026 : le banc montrait 4
            # questions sur 10 qui avouaient sans avoir rien lu). S'ils n'ont
            # rien, on avoue, comme avant.
            mots = set(prompt_norm.split())
            if mots & VOCABULAIRE_MAISON:
                # Revue de code du 27/09 : une PANNE se dit comme une panne ; elle
                # n'est jamais notee « regle manquante » (le bottom-up serait trompe),
                # et on n'attend pas 30 s une recherche qu'Alice ne pourra pas lire.
                panne = ""
                if self.alice_est_injoignable():
                    panne = "Alice est injoignable (constate il y a moins de 30 secondes)"
                else:
                    extraits, combien = self.chercher_dans_la_maison(prompt_norm)
                    panne = getattr(self, "_panne_maison", "")
                    if extraits:
                        reponse, panne = self.demander_au_cerveau(prompt, extraits)
                        if reponse:
                            return self._sortie(
                                True,
                                raison + f" — {combien} mot(s) retrouve(s) dans les documents de la maison.",
                                reponse, "documents", 0.0, t0, source="documents-maison")
                        if self._citation:
                            return self._citer(raison, t0)
                if panne:
                    return self._sortie(
                        False, "Question sur la maison, mais une panne m'empeche de lire : " + str(panne)[:160],
                        "Je ne peux pas repondre pour l'instant : panne (" + str(panne)[:120] + "). "
                        "Ce n'est pas une regle qui manque ; reessaie dans un moment.",
                        None, 0.0, t0, source="aveu")
                quoi = ", ".join(sorted(mots & VOCABULAIRE_MAISON)[:3])
                self._consigner_lacune(prompt_norm, f"Question sur la maison ({quoi}) sans règle écrite")
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
            # On cherche avec la question SANS LA POLITESSE : « salut, quelle
            # est la capitale de la Mongolie ? » faisait remonter 2 documents
            # sans rapport (le mot « salut » dans la requete documentaire),
            # Alice ne repondait que depuis eux, et disait « Je ne sais pas ».
            # La politesse ne doit jamais changer la recherche (17/09/2026,
            # epreuve test_arthur_le_bonjour_ne_gene_pas.py).
            extraits, combien = self.chercher_dans_les_documents(prompt_norm)
            if extraits:
                reponse, panne = self.demander_au_cerveau(prompt, extraits)
                if reponse:
                    return self._sortie(
                        True,
                        raison + f" — {combien} document(s) trouve(s), lus avant de repondre.",
                        reponse, "documents", 0.0, t0, source="documents")
                if self._citation:
                    return self._citer(raison, t0)

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
            #   "qwen"  -> Qwen, sur Alice, à la maison (gratuit) ;
            #   "local" -> Nemotron local (morgan, ollama), gratuit.
            # ABANDON DU 21/09/2026 : la branche "nebius" (Nemotron chez Nebius,
            # 4e couche cloud payante) est COUPEE sur decision de Patrick — le
            # credit etait a zero et ne sera pas recharge. Le but de la tour est
            # l'autonomie et l'apprentissage organique, pas la dependance au nuage.
            # Le reglage "nebius" ne declenche plus AUCUN appel externe : il tombe
            # directement sur le repli local. nemotron_nebius reste importe pour
            # ne rien casser (page_cle_nebius), mais n'est plus jamais appele.
            choix = choisir or _reglage_maison("cerveau_gros", "qwen")
            if choix == "aucun":
                # Mode local : on s'arrete ici et on dit qu'on POURRAIT monter.
                sortie = self._sortie(False, raison + " — mode local : je ne monte pas au gros cerveau.",
                                      REPLI, None, 0.0, t0, source="aveu")
                sortie["peut_monter"] = True
                return sortie
            # RETOUR DE NEMOTRON (24/09/2026) : le concours Nebius × NVIDIA exige
            # Nemotron sur Nebius. Le réglage « nebius » redemande donc à Nemotron
            # quand une clé existe. Sans crédit (402), Arthur le DIT dans sa raison
            # et redescend à la maison (Qwen) — il n'invente jamais.
            if choix == "nebius":
                if nemotron_nebius is not None and nemotron_nebius.est_pret():
                    d = nemotron_nebius.demander(prompt)
                    if d.get("reponse"):
                        return self._sortie(
                            True, raison + " — passé à Nemotron, chez Nebius (Token Factory).",
                            d["reponse"], "nemotron", 0.0, t0, source="nemotron")
                    if d.get("panne"):
                        raison += " Nebius : " + d["panne"]
                choix = "qwen"

            if choix == "local":
                reponse = self.demander_a_morgan(prompt)
                if reponse:
                    return self._sortie(
                        True, raison + " — passe a Nemotron local (morgan, ollama).",
                        reponse, "local", 0.0, t0, source="local")

            # UN CERVEAU DECLARE (29/09/2026) : deepseek, claude, mistral...
            # (fournisseurs.py). Muet ou en panne -> on redescend a Qwen.
            externe = self._cerveau_externe(choix)
            if externe:
                d = fournisseurs.demander(externe, prompt, consigne=CONSIGNE_ALICE)
                if d.get("reponse"):
                    if "je ne sais pas" in d["reponse"].lower():
                        self._consigner_lacune(prompt_norm, raison)
                    return self._sortie(True, raison + " — passé à %s (%s)." % (
                                            externe, d.get("modele") or "?"),
                                        d["reponse"], externe, 0.0, t0, source=externe)
                raison += " %s : %s." % (externe, d.get("panne"))

            reponse, panne = self.demander_a_alice(prompt)
            if reponse:
                # Alice a repondu « Je ne sais pas » ? C'est une LACUNE
                # deguisee : on la consigne pour l'apprentissage bottom-up,
                # sans changer la reponse (les epreuves l'attendent en alice).
                if "je ne sais pas" in (reponse or "").lower():
                    self._consigner_lacune(prompt_norm, raison)
                return self._sortie(True, raison + " — passé à Qwen sur Alice.",
                                    reponse, "alice", 0.0, t0, source="alice")
            raison += f" Alice n'a pas répondu ({panne})." if panne else ""
            self._consigner_lacune(prompt_norm, raison)
            return self._sortie(False, raison, REPLI, None, 0.0, t0, source="aveu")

        # a score egal, on tranche toujours pareil : le sujet de base d'abord,
        # puis l'ordre alphabetique. Jamais au hasard.
        def rang(cle):
            return (scores[cle], 1 if cle in BASE_INITIALE else 0, cle)
        meilleure = max(scores, key=rang)

        # FAUX POSITIF ? La fiche gagnante couvre-t-elle VRAIMENT la question,
        # ou un mot commun a fait le score ? Si des MOTS IMPORTANTS de la
        # question ne figurent pas dans la fiche, on monte au RAG en secours.
        # Mesure : « c est quoi le routeur de la tour » -> mot commun « tour »
        # renvoyait la fiche tour_presentation au lieu de parler de routeur.
        item = self.base[meilleure]
        mots_fiche = set()
        for m in item.get("mots", []):
            mots_fiche.update(self.normaliser(m).split())
        importants = [t for t in tokens
                      if t not in mots_fiche and len(t) >= 6]
        if importants:
            extraits, combien = self.chercher_dans_les_documents(prompt_norm)
            if extraits:
                reponse, panne = self.demander_au_cerveau(prompt, extraits)
                if reponse:
                    return self._sortie(
                        True,
                        item.get("think", "") + f" — la fiche {meilleure} etait un "
                        f"faux positif ({combien} document(s) pertinent(s) lu(s)).",
                        reponse, "documents", 0.0, t0, source="documents")
                if self._citation:
                    return self._citer("Fiche %s ecartee (faux positif)" % meilleure, t0)
            # LE TROU REPARE (21/09/2026). La fiche ne couvre pas un mot
            # important de la question (« faille noyau Debian » -> la fiche
            # veille_cybersecurite ne parle pas de Debian), ET le RAG n a pas
            # pu confirmer — souvent parce qu on est HORS LIGNE. Avant, on
            # servait quand meme la fiche : une reponse a cote. Le silence
            # vaut mieux qu une reponse a cote : on avoue.
            return self._sortie(
                False,
                f"Fiche {meilleure} ecartee : elle ne couvre pas "
                f"{', '.join(importants[:3])}.",
                "Je ne sais pas répondre avec certitude. Aucune règle écrite ne "
                "correspond vraiment à ta question — tu peux en ajouter une dans "
                "le registre.",
                None, 0.0, t0, source="aveu")

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
