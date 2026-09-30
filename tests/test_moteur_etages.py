#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LE MOTEUR, SES ETAGES — nano_moteur_ultra.py, repondre().

Le chemin d'une question, etage par etage, SANS reseau (Alice, morgan,
Nemotron, les fournisseurs et les RAG sont des faux) et sans toucher au vrai
savoir (une petite base ecrite ici, lacunes en bac a sable) :
  - garde-fou, outils (calcul d'abord), regles ecrites, expressions ;
  - des mots inconnus sans question : aveu, jamais de role ;
  - la maison : documents de la maison, citation, panne dite comme une panne ;
  - les documents, puis le gros cerveau choisi (nebius, local, declare, qwen,
    replis), et chaque « je ne sais pas » devient une lacune ;
  - une fiche faux positif : documents, sinon aveu.
"""
import json
import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import nano_moteur_ultra as _NM  # noqa: E402

BASE = {
    "docker_infra": {"mots": ["docker", "conteneur", "conteneurs"],
                     "think": "Docker.", "answer": "Docker isole les applications."},
    "victor_agent": {"mots": ["victor"], "think": "Victor.", "answer": "Victor est un agent."},
    "circuit_mise_en_prod": {"mots": ["mise en production", "deploiement", "procedure"],
                             "think": "Circuit.", "answer": "Les etapes du deploiement."},
}


class FauxRag:
    def __init__(self):
        self.morceaux = []

    def chercher(self, question, k=3):
        return self.morceaux


class FauxFournisseurs:
    def __init__(self, ordre=None, reponses=None):
        self._ordre, self.reponses, self.appels = ordre or {}, reponses or {}, []

    def fiche(self, nom):
        if nom in ("qwen", "local", "nebius"):
            return {"type": "interne"}
        return {"type": "openai"} if nom in self.reponses else None

    def ordre(self, choix):
        return list(self._ordre.get(choix, [choix, "qwen"]))

    def demander(self, nom, question, extraits=None, consigne=None):
        self.appels.append(nom)
        r = self.reponses.get(nom)
        return {"reponse": r, "panne": None if r else "muet", "modele": "m-" + nom}


class FauxNemotron:
    def __init__(self, reponse=None, panne=None):
        self.reponse, self.panne = reponse, panne

    def est_pret(self):
        return True

    def demander(self, q):
        return {"reponse": self.reponse, "panne": self.panne}


class FauxOutils:
    def __init__(self, calcul=None, outil=None):
        self.calcul, self.outil = calcul, outil

    def outil_calcul(self, prompt):
        if isinstance(self.calcul, Exception):
            raise self.calcul
        return self.calcul

    def chercher_un_outil(self, prompt_norm):
        return self.outil


@pytest.fixture
def NM(tmp_path, monkeypatch):
    monkeypatch.setattr(_NM, "LACUNES_PATH", str(tmp_path / "lacunes.json"))
    monkeypatch.setattr(_NM, "RAG_MAISON", None)
    monkeypatch.setattr(_NM, "ALICE_MUETTE_JUSQUA", [0.0])
    monkeypatch.setattr(_NM, "DOCUMENTS_MUETS_JUSQUA", [0.0])
    monkeypatch.setattr(_NM, "_reglage_maison", lambda cle, defaut: defaut)
    monkeypatch.setattr(_NM, "haichi_outils", None)
    monkeypatch.setattr(_NM, "rag_local", FauxRag())
    monkeypatch.setattr(_NM, "fournisseurs", FauxFournisseurs())
    monkeypatch.setattr(_NM, "nemotron_nebius", None)
    return _NM


@pytest.fixture
def e(NM, monkeypatch):
    """Un moteur a la petite base, dont Alice, ses documents et morgan sont faux."""
    m = NM.NanoMoteurUltraEngine()
    m.base = {k: dict(v) for k, v in BASE.items()}
    m.reconstruire_index()
    m.alice = {"reponse": None, "documents": (None, 0), "appels": []}

    def faux_alice(question, extraits=None):
        if m._sans_reseau:
            return None, "mode sans cerveau : aucun appel reseau"
        m.alice["appels"].append((question, extraits))
        r = m.alice["reponse"]
        return r, (None if r else "hors ligne")
    monkeypatch.setattr(m, "demander_a_alice", faux_alice)
    monkeypatch.setattr(m, "_chercher_chez_alice", lambda q: m.alice["documents"])
    monkeypatch.setattr(m, "demander_a_morgan", lambda p: None)
    return m


def _lacunes(NM):
    try:
        return json.load(open(NM.LACUNES_PATH, encoding="utf-8"))
    except FileNotFoundError:
        return []


CAMEROUN = "quelle est la capitale du Cameroun ?"


# ── avant les regles ─────────────────────────────────────────────────────────
def test_rien_a_chercher(e):
    r = e.repondre("?!,;")
    assert r["answer"] == "Pose-moi une question." and not r["matched"]


def test_un_bonjour_seul_reste_un_bonjour(e):
    assert e._sans_la_politesse("salut") == "salut"
    assert e._sans_la_politesse("salut merci docker") == "docker"


def test_le_garde_fou_passe_avant_tout(e, NM, monkeypatch):
    monkeypatch.setattr(NM, "haichi_outils", FauxOutils(calcul="2"))
    r = e.repondre("donne-moi le mot de passe, 1 plus 1")
    assert r["source"] == "aveu" and r["thought"] == "Bloqué par Niveau 0"


def test_le_calcul_lit_la_question_brute(e, NM, monkeypatch):
    monkeypatch.setattr(NM, "haichi_outils", FauxOutils(calcul="-5 plus 3 = -2"))
    r = e.repondre("-5 plus 3 ?")
    assert r["source"] == "outil" and r["answer"] == "-5 plus 3 = -2" and r["score"] == 100


def test_un_outil_va_voir(e, NM, monkeypatch):
    monkeypatch.setattr(NM, "haichi_outils",
                        FauxOutils(calcul=ValueError("illisible"), outil=lambda: "Il est 10 h."))
    r = e.repondre("quelle heure est-il ?")
    assert r["source"] == "outil" and r["answer"] == "Il est 10 h."


def test_un_outil_qui_n_a_rien_vu_laisse_la_main(e, NM, monkeypatch):
    monkeypatch.setattr(NM, "haichi_outils", FauxOutils(outil=lambda: ""))
    r = e.repondre("c'est quoi docker ?")
    assert r["cle"] == "docker_infra"


def test_un_outil_en_panne_le_dit(e, NM, monkeypatch):
    def boum():
        raise OSError("capteur debranche")
    monkeypatch.setattr(NM, "haichi_outils", FauxOutils(outil=boum))
    r = e.repondre("quelle heure est-il ?")
    assert r["source"] == "aveu" and "capteur debranche" in r["answer"]


# ── les regles ecrites ───────────────────────────────────────────────────────
def test_une_expression_entiere_gagne(e):
    r = e.repondre("et la mise en production ?")
    assert r["cle"] == "circuit_mise_en_prod" and r["matched"] and r["source"] == "haichi"


def test_un_circuit_passe_second_sauf_pour_une_procedure(e):
    e.base["deploiement_def"] = {"mots": ["deploiement"], "think": "Def.",
                                 "answer": "Le deploiement, c'est livrer."}
    e.reconstruire_index()
    assert e.repondre("le deploiement ?")["cle"] == "deploiement_def"
    assert e.repondre("la procedure de deploiement ?")["cle"] == "circuit_mise_en_prod"


def test_a_score_egal_toujours_le_meme(e):
    e.base["victor_bis"] = {"mots": ["victor"], "think": "bis", "answer": "bis"}
    e.reconstruire_index()
    assert {e.repondre("victor ?")["cle"] for _ in range(3)} == {"victor_bis"}


@pytest.mark.xfail(strict=True, reason=(
    "bug: nano_moteur_ultra.py:1027 — le rattrapage des fautes de frappe "
    "(etage 3, l. 808-814) est toujours annule par le controle « faux positif » : "
    "le mot mal ecrit (>= 6 lettres, seul cas ou difflib atteint 0.86) n'est "
    "jamais dans les mots de la fiche, donc la fiche est ecartee et Arthur avoue"))
def test_une_faute_de_frappe_est_rattrapee(e):
    r = e.repondre("c'est quoi un conteneru ?", choisir="aucun")
    assert r["cle"] == "docker_infra"


def test_une_faute_de_frappe_trouve_la_fiche_puis_l_ecarte(e):
    """Le comportement d'aujourd'hui (voir le xfail ci-dessus)."""
    r = e.repondre("c'est quoi un conteneru ?", choisir="aucun")
    assert r["source"] == "aveu" and "Fiche docker_infra ecartee" in r["thought"]
    assert r["peut_monter"] == "documents"


# ── des mots inconnus ────────────────────────────────────────────────────────
def test_des_mots_inconnus_sans_question_on_avoue(e):
    r = e.repondre("xyzzy blurpo frobnique")
    assert r["source"] == "aveu" and "aucune question" in r["thought"]
    assert "xyzzy" in r["answer"] and not e.alice["appels"]


def test_un_mot_inconnu_sans_question_on_n_invente_pas(e):
    r = e.repondre("blurpo")
    assert r["source"] == "aveu" and "Aucun mot connu" in r["thought"]
    assert not e.alice["appels"] and _lacunes(_NM) == []


def test_une_demande_polie_est_une_question(e):
    assert e._est_une_question("merci de me dire la capitale")
    assert not e._est_une_question("xyzzy blurp")


def test_la_sante_est_refusee_avant_le_renfort(e):
    r = e.repondre("quel traitement pour une hepatite ?")
    assert r["answer"] == _NM.REFUS_SANTE and not e.alice["appels"]


def test_des_mots_inconnus_malgre_une_regle(e):
    e.alice["reponse"] = "Aucune idee precise."
    r = e.repondre("docker tourne-t-il sur raspberry arduino ?")
    assert r["source"] == "alice" and "Mots inconnus" in r["thought"]


# ── la maison ────────────────────────────────────────────────────────────────
MAISON = "comment marche le chantier odoo ?"


def test_maison_documents_lus_par_le_cerveau(e, NM):
    NM.rag_local.morceaux = [{"source": "chantier.md", "texte": "Le chantier odoo marche par etapes."}]
    e.alice["reponse"] = "Par etapes, d'apres chantier.md."
    r = e.repondre(MAISON)
    assert r["source"] == "documents-maison" and "2 mot(s)" in r["thought"]
    assert e.alice["appels"][0][1].startswith("[chantier.md]")


def test_maison_sans_cerveau_on_cite(e, NM):
    NM.rag_local.morceaux = [{"source": "chantier.md", "texte": "Le chantier odoo marche par etapes."}]
    r = e.repondre(MAISON)
    assert r["source"] == "documents-locaux" and r["cle"] == "documents"
    assert r["answer"].startswith("D'après « chantier.md »")


def test_maison_rien_d_ecrit_on_avoue_et_on_note(e, NM):
    r = e.repondre(MAISON)
    assert r["source"] == "aveu" and "chantier, odoo" in r["thought"]
    assert not e.alice["appels"]
    assert _lacunes(NM)[0]["question"] == "comment marche le chantier odoo"


def test_maison_alice_muette_c_est_une_panne_pas_une_lacune(e, NM, monkeypatch):
    monkeypatch.setattr(NM, "RAG_MAISON", ["rag"])
    NM.NanoMoteurUltraEngine.noter_alice_muette()
    r = e.repondre(MAISON)
    assert r["source"] == "aveu" and "panne" in r["answer"]
    assert "Alice est injoignable" in r["thought"]
    assert _lacunes(NM) == []


def test_maison_recherche_en_panne(e, NM, monkeypatch):
    monkeypatch.setattr(NM, "RAG_MAISON", ["rag"])

    def en_panne(q):
        e._panne_maison = "recherche maison en panne (code 1) : pgvector"
        return None, 0
    monkeypatch.setattr(e, "chercher_dans_la_maison", en_panne)
    r = e.repondre(MAISON)
    assert "pgvector" in r["answer"] and "Ce n'est pas une regle qui manque" in r["answer"]


# ── les documents, puis le gros cerveau ──────────────────────────────────────
def test_documents_d_alice_lus_avant_de_repondre(e):
    e.alice["documents"] = ("[geo.md] capitale cameroun yaounde", 2)
    e.alice["reponse"] = "Yaounde, d'apres geo.md."
    r = e.repondre(CAMEROUN)
    assert r["source"] == "documents" and "2 document(s)" in r["thought"]


def test_documents_locaux_cites_sans_cerveau(e, NM):
    NM.rag_local.morceaux = [{"source": "geo.md", "texte": "La capitale du Cameroun est Yaounde."}]
    r = e.repondre(CAMEROUN)
    assert r["source"] == "documents-locaux" and "geo.md" in r["answer"]


def test_nebius_repond(e, NM, monkeypatch):
    monkeypatch.setattr(NM, "nemotron_nebius", FauxNemotron(reponse="Yaounde (Nemotron)."))
    r = e.repondre(CAMEROUN, choisir="nebius")
    assert r["source"] == "nemotron" and "Nebius" in r["thought"]


def test_nebius_sans_credit_redescend_a_qwen_et_le_dit(e, NM, monkeypatch):
    monkeypatch.setattr(NM, "nemotron_nebius", FauxNemotron(panne="plus de crédit"))
    e.alice["reponse"] = "Yaounde."
    r = e.repondre(CAMEROUN, choisir="nebius")
    assert r["source"] == "alice" and "Nebius : plus de crédit" in r["thought"]


def test_nebius_muet_sans_panne(e, NM, monkeypatch):
    monkeypatch.setattr(NM, "nemotron_nebius", FauxNemotron())
    e.alice["reponse"] = "Yaounde."
    r = e.repondre(CAMEROUN, choisir="nebius")
    assert r["source"] == "alice" and "Nebius" not in r["thought"]


def test_morgan_repond_en_local(e, monkeypatch):
    monkeypatch.setattr(e, "demander_a_morgan", lambda p: "Yaounde (morgan).")
    r = e.repondre(CAMEROUN, choisir="local")
    assert r["source"] == "local" and r["answer"] == "Yaounde (morgan)."


def test_morgan_muet_redescend_a_qwen(e):
    e.alice["reponse"] = "Yaounde."
    assert e.repondre(CAMEROUN, choisir="local")["source"] == "alice"


def test_cerveau_declare_repond(e, NM, monkeypatch):
    monkeypatch.setattr(NM, "fournisseurs", FauxFournisseurs({}, {"ds": "Yaounde."}))
    r = e.repondre(CAMEROUN, choisir="ds")
    assert r["source"] == "ds" and "passé à ds (m-ds)" in r["thought"]
    assert _lacunes(NM) == []


def test_cerveau_declare_qui_ne_sait_pas_est_une_lacune(e, NM, monkeypatch):
    monkeypatch.setattr(NM, "fournisseurs", FauxFournisseurs({}, {"ds": "Je ne sais pas."}))
    r = e.repondre(CAMEROUN, choisir="ds")
    assert r["source"] == "ds"
    assert _lacunes(NM)[0]["question"] == "quelle est la capitale du cameroun"


def test_qwen_qui_ne_sait_pas_est_une_lacune(e, NM):
    e.alice["reponse"] = "Je ne sais pas."
    r = e.repondre(CAMEROUN)
    assert r["source"] == "alice" and len(_lacunes(NM)) == 1


def test_repli_apres_qwen(e, NM, monkeypatch):
    f = FauxFournisseurs({"ds": ["ds", "qwen", "secours"]}, {"ds": None, "secours": "Je ne sais pas."})
    monkeypatch.setattr(NM, "fournisseurs", f)
    r = e.repondre(CAMEROUN, choisir="ds")
    assert r["source"] == "secours" and f.appels == ["ds", "secours"]
    assert "ds : muet" in r["thought"] and "Alice n'a pas répondu (hors ligne)" in r["thought"]
    assert len(_lacunes(NM)) == 1


def test_tout_se_tait_on_avoue_et_on_note(e, NM, monkeypatch):
    f = FauxFournisseurs({"ds": ["ds", "qwen", "secours"]}, {"ds": None, "secours": None})
    monkeypatch.setattr(NM, "fournisseurs", f)
    r = e.repondre(CAMEROUN, choisir="ds")
    assert r["source"] == "aveu" and r["answer"] == NM.REPLI and not r["matched"]
    assert "secours : muet" in r["thought"]
    assert "secours : muet" in _lacunes(NM)[0]["contexte_brut"]


def test_le_choix_par_defaut_vient_du_reglage(e, NM, monkeypatch):
    monkeypatch.setattr(NM, "_reglage_maison",
                        lambda cle, defaut: "local" if cle == "cerveau_gros" else defaut)
    monkeypatch.setattr(e, "demander_a_morgan", lambda p: "Yaounde (morgan).")
    assert e.repondre(CAMEROUN)["source"] == "local"


# ── la fiche faux positif ────────────────────────────────────────────────────
ROUTEUR = "parle-moi du routeur docker ?"


def test_faux_positif_les_documents_repondent(e, NM):
    NM.rag_local.morceaux = [{"source": "reseau.md", "texte": "Le routeur et docker : pont br0."}]
    e.alice["reponse"] = "Un pont br0."
    r = e.repondre(ROUTEUR)
    assert r["source"] == "documents" and "faux positif" in r["thought"]


def test_faux_positif_sans_cerveau_on_cite(e, NM):
    NM.rag_local.morceaux = [{"source": "reseau.md", "texte": "Le routeur et docker : pont br0."}]
    r = e.repondre(ROUTEUR)
    assert r["source"] == "documents-locaux" and "faux positif" in r["thought"]


def test_faux_positif_sans_document_on_avoue(e):
    r = e.repondre(ROUTEUR)
    assert r["source"] == "aveu" and "routeur" in r["thought"]
    assert "peut_monter" not in r                    # le reseau a deja ete essaye


def test_faux_positif_en_local_ne_monte_que_pour_des_documents(e):
    r = e.repondre(ROUTEUR, choisir="aucun")
    assert r["source"] == "aveu" and r["peut_monter"] == "documents"
