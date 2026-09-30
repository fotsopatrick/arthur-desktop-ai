#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LES GREFFONS — le chargeur, WhatsApp et la veille d'Uatu.

Ce qu'on prouve, SANS reseau (faux urlopen) et dans des dossiers jetables
(les vrais greffons/ ne sont jamais reecrits) :
  - le chargeur : fiche cassee, greffon sans programme ou sans « repondre »,
    greffon qui plante, basculer/regler, le cache d'une seconde ;
  - WhatsApp : pas d'ordre -> rien ; mode essai -> rien ne part ; mode vrai
    -> il manque un reglage, il manque le destinataire, l'envoi reussi ou rate ;
  - la veille : exposition, actionnaires, medias, crises, et « aucune trace ».
"""
import importlib.util
import json
import os
import shutil
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import haichi_greffons as HG  # noqa: E402


def _charger(nom):
    chemin = os.path.join(REPO, "greffons", nom, "greffon.py")
    spec = importlib.util.spec_from_file_location("greffon_test_" + nom, chemin)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


WA = _charger("whatsapp")
VEILLE = _charger("veille")


# ══════════════════════════════════════════════════════════════════════════
# LE CHARGEUR
# ══════════════════════════════════════════════════════════════════════════

def _poser(dossier, nom, fiche, programme=None):
    d = dossier / nom
    d.mkdir()
    if isinstance(fiche, str):
        (d / "greffon.json").write_text(fiche, encoding="utf-8")
    else:
        (d / "greffon.json").write_text(json.dumps(fiche), encoding="utf-8")
    if programme is not None:
        (d / "greffon.py").write_text(programme, encoding="utf-8")
    return d


@pytest.fixture
def dossier(tmp_path):
    d = tmp_path / "greffons"
    d.mkdir()
    HG._CACHE.update({"quand": 0.0, "dossier": None, "greffons": []})
    yield d
    HG._CACHE.update({"quand": 0.0, "dossier": None, "greffons": []})


class TestChargeur:
    def test_fiche_cassee_et_intrus(self, dossier):
        """Une fiche illisible est listee eteinte, avec la panne ; un fichier
        ou un dossier sans fiche est ignore."""
        _poser(dossier, "casse", "{pas du json")
        (dossier / "sans_fiche").mkdir()
        (dossier / "fichier.txt").write_text("x", encoding="utf-8")
        _poser(dossier, "minimal", {})
        liste = HG.lister(str(dossier), relire=True)
        assert [g["nom"] for g in liste] == ["casse", "minimal"]
        assert liste[0]["allume"] is False and liste[0]["fiche_cassee"]
        assert liste[1]["titre"] == "minimal" and liste[1]["mots"] == []

    def test_cache_une_seconde(self, dossier):
        """Dans la seconde, la liste vient du cache (le disque n'est pas relu)."""
        _poser(dossier, "a", {"allume": True})
        premiere = HG.lister(str(dossier))
        _poser(dossier, "b", {"allume": True})
        assert HG.lister(str(dossier)) is premiere
        assert len(HG.lister(str(dossier), relire=True)) == 2

    def test_dossier_vide_ou_question_vide(self, dossier):
        assert HG.essayer("bonjour", str(dossier)) is None
        _poser(dossier, "a", {"allume": True, "mots": ["meteo"]})
        HG.lister(str(dossier), relire=True)
        assert HG.essayer("?!", str(dossier)) is None

    def test_eteint_mots_vides_et_sans_programme(self, dossier):
        """Eteint : n'existe pas. Mot vide : ignore. Sans greffon.py : panne dite."""
        _poser(dossier, "a_eteint", {"allume": False, "mots": ["meteo"]}, "def repondre(q, r): return 'non'")
        _poser(dossier, "b_sans_prog", {"allume": True, "mots": ["!!", "meteo"]})
        HG.lister(str(dossier), relire=True)
        r = HG.essayer("la meteo de demain", str(dossier))
        assert r["greffon"] == "b_sans_prog"
        assert r["mot"] == "meteo"
        assert r["reponse"] is None
        assert "repondre" in r["panne"]

    def test_greffon_qui_repond_puis_qui_plante(self, dossier):
        _poser(dossier, "bon", {"allume": True, "mots": ["heure"], "reglages": {"fuseau": "UTC"}},
               "def repondre(q, r):\n    return 'fuseau ' + r['fuseau']\n")
        _poser(dossier, "chute", {"allume": True, "mots": ["pluie"]},
               "def repondre(q, r):\n    raise RuntimeError('greffon tombe')\n")
        HG.lister(str(dossier), relire=True)
        r = HG.essayer("quelle heure est-il", str(dossier))
        assert r == {"greffon": "bon", "titre": "bon", "mot": "heure",
                     "reponse": "fuseau UTC", "panne": None}
        r = HG.essayer("va-t-il y avoir de la pluie", str(dossier))
        assert r["reponse"] is None and r["panne"] == "greffon tombe"
        assert HG.essayer("rien a voir", str(dossier)) is None

    def test_basculer_et_regler(self, dossier):
        """Les deux ecrivent la fiche et oublient le cache ; greffon absent -> False."""
        _poser(dossier, "a", {"allume": False, "mots": ["meteo"]},
               "def repondre(q, r):\n    return r.get('ville', '?')\n")
        HG.lister(str(dossier))
        assert HG.basculer("a", True, str(dossier)) is True
        assert HG.regler("a", {"ville": "Douala"}, str(dossier)) is True
        assert HG.essayer("meteo", str(dossier))["reponse"] == "Douala"
        fiche = json.load(open(str(dossier / "a" / "greffon.json"), encoding="utf-8"))
        assert fiche["allume"] is True and fiche["reglages"] == {"ville": "Douala"}
        assert HG.basculer("absent", True, str(dossier)) is False
        assert HG.regler("absent", {}, str(dossier)) is False

    def test_vrai_greffon_whatsapp_copie(self, dossier):
        """Le vrai greffon WhatsApp, copie et allume dans un dossier jetable."""
        shutil.copytree(os.path.join(REPO, "greffons", "whatsapp"), str(dossier / "whatsapp"),
                        ignore=shutil.ignore_patterns("__pycache__"))
        HG.basculer("whatsapp", True, str(dossier))
        r = HG.essayer("envoie un whatsapp a Patrick pour dire que tout va bien", str(dossier))
        assert r["panne"] is None
        assert "RIEN N'A ÉTÉ ENVOYÉ" in r["reponse"]


# ══════════════════════════════════════════════════════════════════════════
# WHATSAPP
# ══════════════════════════════════════════════════════════════════════════

REGLAGES_VRAIS = {"mode": "vrai", "numero": "+237600000000", "jeton": " secret ",
                  "identifiant_expediteur": " 12345 "}


class _FausseReponse:
    def __init__(self, corps):
        self.corps = corps

    def read(self):
        return self.corps

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


@pytest.fixture
def poste(monkeypatch):
    """Un faux Meta : garde les requetes, rend la reponse choisie."""
    envois = []
    etat = {"corps": json.dumps({"messages": [{"id": "wamid.42"}]}).encode(), "lever": None}

    def faux_urlopen(req, timeout=None):
        envois.append(req)
        if etat["lever"]:
            raise etat["lever"]
        return _FausseReponse(etat["corps"])
    monkeypatch.setattr(WA.urllib.request, "urlopen", faux_urlopen)
    return envois, etat


class TestWhatsapp:
    def test_parler_n_est_pas_un_ordre(self, poste):
        envois, _ = poste
        r = WA.repondre("c'est quoi WhatsApp ?", REGLAGES_VRAIS)
        assert r.startswith("Je ne touche pas à WhatsApp")
        assert envois == []

    def test_mode_essai_par_defaut(self, poste):
        envois, _ = poste
        r = WA.repondre("Envoie un message à Patrick pour dire que le serveur est reparti.", None)
        assert "à       : Patrick" in r
        assert "« le serveur est reparti »" in r
        assert "Mode ESSAI" in r
        assert envois == []

    def test_reglages_manquants(self, poste):
        envois, _ = poste
        r = WA.repondre("previens Awa : on arrive", {"mode": "VRAI", "numero": "1"})
        assert "il me manque le réglage « jeton », « identifiant_expediteur »" in r
        assert "« on arrive »" in r
        assert envois == []

    def test_sans_destinataire(self, poste):
        envois, _ = poste
        r = WA.repondre("envoie bonjour", REGLAGES_VRAIS)
        assert "Je ne sais pas à qui l'envoyer" in r
        assert "(personne indiquée)" in r
        assert envois == []

    def test_envoi_par_numero(self, poste):
        """Le numero est nettoye, le jeton et l'expediteur sont sans espaces."""
        envois, _ = poste
        r = WA.repondre("envoie au 06 12 34 56 78 disant rendez-vous a midi", REGLAGES_VRAIS)
        assert "✅ Envoyé. Numéro du message : wamid.42" in r
        req = envois[0]
        assert req.full_url == "https://graph.facebook.com/v21.0/12345/messages"
        assert req.get_header("Authorization") == "Bearer secret"
        charge = json.loads(req.data)
        assert charge["to"] == "0612345678"
        assert charge["text"] == {"body": "rendez-vous a midi"}

    def test_envoi_par_nom_repli_sur_le_numero(self, poste):
        """Un nom sans chiffres : le numero des reglages sert de destinataire."""
        envois, etat = poste
        etat["corps"] = b"{}"
        r = WA.repondre("ecris a Mireille avec le texte bonne fete", REGLAGES_VRAIS)
        assert "Numéro du message : (sans numéro)" in r
        assert json.loads(envois[0].data)["to"] == "+237600000000"

    def test_envoi_rate(self, poste):
        envois, etat = poste
        etat["lever"] = OSError("reseau coupe")
        r = WA.repondre("transmets a Paul : je suis en retard", REGLAGES_VRAIS)
        assert "❌ L'envoi a échoué : reseau coupe" in r

    def test_texte_sans_marqueur(self):
        assert WA._extraire_le_texte("  envoie bonjour  ") == "envoie bonjour"
        assert WA._extraire_le_destinataire("envoie bonjour") is None

    def test_ordre_nie_ne_part_pas(self, poste):
        envois, _ = poste
        WA.repondre("N'envoie surtout rien à Patrick", REGLAGES_VRAIS)
        assert envois == []


# ══════════════════════════════════════════════════════════════════════════
# LA VEILLE D'UATU
# ══════════════════════════════════════════════════════════════════════════

class TestVeille:
    def test_exposition_d_un_geant(self):
        r = VEILLE.repondre("À quoi Nvidia est-il exposé ?", {})
        assert r.startswith("Nvidia est exposé(e) à 2 crise(s)")
        assert "Protocole Beelzebuth" in r
        assert r.endswith(VEILLE.AVERTI)

    def test_exposition_inconnue(self):
        """Un nom absent des fiches : Arthur le dit, il ne comble pas le trou."""
        r = VEILLE.repondre("À quoi Zorglub Industries est exposé ?", {})
        assert r.startswith("Aucune trace de Zorglub Industries parmi les géants des 10 fiches")

    def test_sujet_libre_par_defaut(self):
        assert VEILLE._sujet_libre("a quoi est expose ce truc ?") == "cette entreprise"

    def test_actionnaires(self):
        r = VEILLE.repondre("Qui détient Apple ?", {})
        assert r.startswith("Les fiches citent 1 grand(s) détenteur(s) de Apple")
        assert "BlackRock, Inc." in r

    def test_actionnaires_nom_sans_fiche(self):
        """Un geant de la matrice qu'aucune fiche d'actionnaires ne cite."""
        r = VEILLE.repondre("Qui sont les actionnaires de Tesla ?", {})
        assert r.startswith("Aucune des 17 fiches d'actionnaires ne cite Tesla")

    def test_actionnaires_inconnu(self):
        r = VEILLE.repondre("Qui possède Zorglub ?", {})
        assert r.startswith("Aucune trace de Zorglub dans les 17 fiches d'actionnaires")

    def test_medias_bourse_tech_et_tous(self):
        """Le secteur choisit la liste ; l'acces libre passe d'abord."""
        bourse = VEILLE.repondre("Où lire les nouvelles de la bourse ?", {})
        assert "- Reuters (Thomson Reuters) (Bourse & Finance, accès open)" in bourse
        assert "Tech & IT" not in bourse
        tech = VEILLE.repondre("Quels médias pour la tech ?", {})
        assert "Tech & IT" in tech and "Bourse & Finance" not in tech
        tous = VEILLE.repondre("Où lire la presse ?", {})
        lignes = [l for l in tous.splitlines() if l.startswith("- ")]
        assert len(lignes) == 5 and all("accès open" in l for l in lignes)

    def test_crises_systemiques(self):
        r = VEILLE.repondre("Montre la matrice des crises systémiques", {})
        assert r.startswith("15 crises suivies, dont ")
        assert "- Goulet d'Étranglement Énergétique & Eau des Datacenters IA" in r


if __name__ == "__main__":
    sys.exit(pytest.main(["-q", __file__]))
