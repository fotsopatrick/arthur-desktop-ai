#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LES GARDE-FOUS (gardes/*.py) — des murs qui disent non.

Ce qu'on prouve, SANS toucher au vrai HOME (chaque garde tourne dans un
sous-processus, HOME = un dossier jetable) :
  - chaque garde laisse passer un geste legitime (code 0, rien a dire) ;
  - chaque garde REFUSE la faute qui l'a fait naitre (code 2, ou un
    {"decision": "block"} sur la sortie standard pour les crochets Stop) ;
  - une entree illisible ne fait jamais planter un garde : il se tait.
"""
import hashlib
import json
import os
import subprocess
import sys
import time

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GARDES = os.path.join(REPO, "gardes")


def lancer(nom, entree, maison, cwd=None, env=None):
    """Lance un garde comme le ferait Claude Code : JSON sur l'entree."""
    e = dict(os.environ)
    e["HOME"] = str(maison)
    e.pop("GARDE_PLAN_ETAT", None)
    if env:
        e.update(env)
    if not isinstance(entree, str):
        entree = json.dumps(entree, ensure_ascii=False)
    return subprocess.run(
        [sys.executable, os.path.join(GARDES, nom)],
        input=entree, capture_output=True, text=True, encoding="utf-8",
        env=e, cwd=str(cwd or maison), timeout=30)


def transcript(chemin, *messages):
    """Ecrit un faux journal de session (une ligne JSON par evenement)."""
    with open(chemin, "w", encoding="utf-8") as f:
        f.write("pas du json\n")
        f.write(json.dumps({"type": "user", "message": {"content": "salut"}}) + "\n")
        for m in messages:
            f.write(json.dumps({"type": "assistant", "message": {"content": m}},
                               ensure_ascii=False) + "\n")
    return str(chemin)


def bloque(res):
    """Le crochet Stop a-t-il imprime un refus ?"""
    if not res.stdout.strip():
        return None
    d = json.loads(res.stdout)
    assert d["decision"] == "block"
    return d["reason"]


# ─────────────────────────── garde-plan-action.py ──────────────────────────

PLAN = "garde-plan-action.py"

PLAN_COMPLET = (
    "Le harnais refuse la commande. La cause : le classificateur voit un mot interdit. "
    "La suite : je reformule la commande. Tes possibilités : (A) je reformule — "
    "ça passe sans rien casser ; (B) tu autorises — plus rapide. "
    "Aucune compétence à part.")


@pytest.fixture()
def plan_env(tmp_path):
    """Un HOME jetable et un fichier d'etat du garde dans ce HOME."""
    etat = tmp_path / "etat" / ".dernier-juge-plan"
    return tmp_path, {"GARDE_PLAN_ETAT": str(etat)}, etat


def test_plan_entree_illisible_se_tait(plan_env):
    """Pas du JSON : le garde laisse passer sans rien dire."""
    maison, env, _ = plan_env
    r = lancer(PLAN, "{{{ pas du json", maison, env=env)
    assert r.returncode == 0 and r.stdout == ""


def test_plan_succes_net_passe(plan_env):
    """Aucun probleme signale : rien a exiger, mais l'empreinte est notee."""
    maison, env, etat = plan_env
    r = lancer(PLAN, {"last_assistant_message": "Tout est fait, les tests passent."},
               maison, env=env)
    assert r.returncode == 0 and r.stdout == ""
    attendu = hashlib.sha1("Tout est fait, les tests passent.".encode()).hexdigest()
    assert etat.read_text() == attendu


def test_plan_probleme_nu_refuse_les_quatre_manques(plan_env):
    """« C'est bloque » tout seul : analyse, suite, choix, competences manquent."""
    maison, env, _ = plan_env
    r = lancer(PLAN, {"assistant_message": "Je suis bloqué, le harnais refuse."},
               maison, env=env)
    raison = bloque(r)
    assert r.returncode == 0
    assert "L'ANALYSE MANQUE" in raison
    assert "LA SUITE MANQUE" in raison
    assert "TES POSSIBILITÉS MANQUENT" in raison
    assert "LES COMPÉTENCES" in raison


def test_plan_complet_passe(plan_env):
    """Probleme + cause + suite + choix expliques + competences : il passe."""
    maison, env, _ = plan_env
    r = lancer(PLAN, {"message": PLAN_COMPLET}, maison, env=env)
    assert r.returncode == 0 and r.stdout == ""


def test_plan_choix_non_expliques_refuse(plan_env):
    """« (A) bloquer (B) laisser » sans dire ce que ca change : refuse."""
    maison, env, _ = plan_env
    texte = ("Échec du lancement. La cause : le port est pris. La suite : je libère "
             "le port. (A) bloquer (B) laisser. Aucune compétence à part.")
    raison = bloque(lancer(PLAN, {"message": texte}, maison, env=env))
    assert "NE SONT PAS EXPLIQUÉES" in raison
    assert "L'ANALYSE MANQUE" not in raison


def test_plan_probleme_resolu_passe(plan_env):
    """Un probleme deja regle n'a pas besoin de plan."""
    maison, env, _ = plan_env
    r = lancer(PLAN, {"message": "Il y avait une erreur, c'est réglé."}, maison, env=env)
    assert r.stdout == ""


def test_plan_deja_juge_une_seule_fois(plan_env):
    """Le meme texte n'est pas juge deux fois (empreinte)."""
    maison, env, _ = plan_env
    msg = {"message": "Je suis bloqué."}
    assert bloque(lancer(PLAN, msg, maison, env=env))
    r = lancer(PLAN, msg, maison, env=env)
    assert r.returncode == 0 and r.stdout == ""


def test_plan_lit_le_journal_de_session(plan_env):
    """Sans message fourni, il juge le dernier message texte du journal."""
    maison, env, _ = plan_env
    tp = transcript(maison / "t.jsonl",
                    "Tout va bien.",
                    [{"type": "tool_use", "name": "Bash"}],
                    [{"type": "text", "text": "La commande a planté."},
                     {"type": "text", "text": "Voilà."}])
    raison = bloque(lancer(PLAN, {"transcript_path": tp}, maison, env=env))
    assert "LA SUITE MANQUE" in raison


def test_plan_attend_un_nouveau_message_puis_abandonne(plan_env):
    """Journal deja juge : il attend un peu un message neuf, puis se tait."""
    maison, env, etat = plan_env
    tp = transcript(maison / "t.jsonl", "Je suis bloqué.")
    etat.parent.mkdir(parents=True)
    etat.write_text(hashlib.sha1("Je suis bloqué.".encode()).hexdigest())
    debut = time.time()
    r = lancer(PLAN, {"transcript_path": tp}, maison, env=env)
    assert r.stdout == ""
    assert time.time() - debut >= 1.5


def test_plan_journal_absent_ou_illisible(plan_env):
    """Journal inexistant ou dossier a la place : message vide, il se tait."""
    maison, env, _ = plan_env
    r = lancer(PLAN, {"transcript_path": str(maison / "absent.jsonl")}, maison, env=env)
    assert r.stdout == ""
    (maison / "dossier.jsonl").mkdir()
    r = lancer(PLAN, {"transcript_path": str(maison / "dossier.jsonl")}, maison, env=env)
    assert r.returncode == 0 and r.stdout == ""


def test_plan_etat_non_inscriptible_juge_quand_meme(plan_env):
    """Si l'empreinte ne peut pas s'ecrire, le garde juge tout de meme."""
    maison, _, _ = plan_env
    (maison / "bouchon").write_text("un fichier, pas un dossier")
    env = {"GARDE_PLAN_ETAT": str(maison / "bouchon" / "etat")}
    assert bloque(lancer(PLAN, {"message": "Je suis bloqué."}, maison, env=env))


def test_plan_etat_par_defaut_dans_le_home(tmp_path):
    """Sans GARDE_PLAN_ETAT, l'empreinte va dans ~/.claude/portes du HOME jetable."""
    lancer(PLAN, {"message": "Rien de spécial."}, tmp_path)
    assert (tmp_path / ".claude" / "portes" / ".dernier-juge-plan").exists()


# ─────────────────────────── garde-donner-des-boutons.py ───────────────────
# MAISON = expanduser("~orel") : sans utilisateur orel, le chemin reste
# litteral ("~orel/...") et se resout depuis le dossier courant — on lance
# donc le garde avec cwd = le dossier jetable.

BOUTONS = "garde-donner-des-boutons.py"


def _boutons(tmp_path, *messages):
    tp = transcript(tmp_path / "t.jsonl", *messages)
    return lancer(BOUTONS, {"transcript_path": tp}, tmp_path)


def _poser_bouton(tmp_path, carnet="cockpit-generique/taches.json"):
    maison = os.path.expanduser("~orel")
    base = maison if os.path.isabs(maison) else str(tmp_path / maison)
    if os.path.isabs(maison):  # pragma: no cover — machine avec un vrai orel
        pytest.skip("un utilisateur orel existe : on ne touche pas a son HOME")
    chemin = os.path.join(base, carnet)
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    with open(chemin, "w") as f:
        f.write("[]")


def test_boutons_entree_illisible_ou_sans_journal(tmp_path):
    """JSON casse, pas de journal, journal absent : il laisse passer."""
    for entree in ("pas du json", "", {"transcript_path": str(tmp_path / "x")}):
        r = lancer(BOUTONS, entree, tmp_path)
        assert r.returncode == 0 and r.stdout == ""


def test_boutons_commande_a_taper_refusee(tmp_path):
    """« Tape cette commande dans ton terminal » : refuse, il faut un bouton."""
    r = _boutons(tmp_path, [{"type": "text", "text": "Tape cette commande : ls"}])
    raison = bloque(r)
    assert "commande a taper" in raison


def test_boutons_bloc_bang_refuse(tmp_path):
    """Un bloc de code avec « ! » a lancer soi-meme : refuse."""
    r = _boutons(tmp_path, "Fais ceci :\n```bash\n! ls -la\n```")
    assert "poser-action.py" in bloque(r)


def test_boutons_page_sans_adresse_refusee(tmp_path):
    """« J'ai fabriqué la page » sans adresse ni bouton : refuse."""
    r = _boutons(tmp_path, "J'ai fabriqué une page pour toi, bascule avec Alt+Tab.")
    raison = bloque(r)
    assert "GARDE DES BOUTONS" in raison and "http://" in raison


def test_boutons_page_avec_adresse_passe(tmp_path):
    """La page donnee avec son adresse complete : il passe."""
    r = _boutons(tmp_path, "J'ai fabriqué la page : http://127.0.0.1:8835/")
    assert r.returncode == 0 and r.stdout == ""


def test_boutons_bouton_recent_laisse_passer(tmp_path):
    """Un bouton pose dans les 3 dernieres minutes excuse la page et la commande."""
    _poser_bouton(tmp_path)
    r = _boutons(tmp_path, "J'ai fabriqué la page. Tape cette commande : ls")
    assert r.returncode == 0 and r.stdout == ""


def test_boutons_message_banal_passe(tmp_path):
    """Un message sans page ni commande : rien a dire."""
    r = _boutons(tmp_path, "Voici le résumé demandé.", None)
    assert r.stdout == ""


def test_boutons_journal_illisible_se_tait(tmp_path):
    """Le journal est un dossier : lecture impossible, message vide, il passe."""
    (tmp_path / "d").mkdir()
    r = lancer(BOUTONS, {"transcript_path": str(tmp_path / "d")}, tmp_path)
    assert r.returncode == 0 and r.stdout == ""


# ─────────────────────────── garde-ne-pas-reposer.py ───────────────────────

REPOSER = "garde-ne-pas-reposer.py"

CARNET = '''
REPONSES = {"on publie le site": "oui, publie"}
def deja_repondu(q):
    return REPONSES.get(q.lower())
'''


def _carnet(tmp_path):
    (tmp_path / "outils").mkdir()
    (tmp_path / "outils" / "carnet-des-reponses.py").write_text(CARNET)


def _demande(*quoi):
    corps = "\n".join("quoi : %s" % q for q in quoi)
    return {"last_message": "Question :\n```demandes\n%s\n```" % corps}


def test_reposer_question_deja_tranchee_refusee(tmp_path):
    """Une question que Patrick a deja tranchee : code 2, et sa reponse rappelee."""
    _carnet(tmp_path)
    r = lancer(REPOSER, _demande("On publie le site", "Autre chose ?"), tmp_path)
    assert r.returncode == 2
    assert "Il a repondu : oui, publie" in r.stderr


def test_reposer_question_neuve_passe(tmp_path):
    """Une question jamais posee : elle passe."""
    _carnet(tmp_path)
    assert lancer(REPOSER, _demande("On repeint la tour ?"), tmp_path).returncode == 0


def test_reposer_sans_carnet_passe(tmp_path):
    """Pas de carnet des reponses : le garde ne peut rien savoir, il passe."""
    assert lancer(REPOSER, _demande("On publie le site"), tmp_path).returncode == 0


@pytest.mark.parametrize("entree", [
    "pas du json",
    {},
    {"message": "pas de bloc demandes ici"},
    {"assistant_message": "```demandes\nrien a demander\n```"},
])
def test_reposer_rien_a_juger(tmp_path, entree):
    """Entree illisible, vide, sans bloc ou sans « quoi : » : il passe."""
    _carnet(tmp_path)
    r = lancer(REPOSER, entree, tmp_path)
    assert r.returncode == 0 and r.stderr == ""


# ─────────────────────────── garde-video-montree.py ────────────────────────

VIDEO = "garde-video-montree.py"


def _video(tmp_path, nom, taille=300 * 1024, age=0):
    d = tmp_path / "livrables" / "videos"
    chemin = d / nom
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_bytes(b"\0" * taille)
    if age:
        t = time.time() - age
        os.utime(chemin, (t, t))
    return chemin


def test_video_sans_dossier_passe(tmp_path):
    """Pas de dossier de videos : rien a montrer."""
    r = lancer(VIDEO, "{}", tmp_path)
    assert r.returncode == 0 and r.stderr == ""


def test_video_neuve_non_montree_refusee(tmp_path):
    """Une video neuve, jamais montree : code 2 et la commande pour la montrer."""
    _video(tmp_path, "concours.mp4")
    _video(tmp_path, "rangee/autre.webm")
    r = lancer(VIDEO, "{}", tmp_path)
    assert r.returncode == 2
    assert "2 video(s)" in r.stderr
    assert "montrer-la-video.py" in r.stderr


def test_video_ignore_essais_vieilles_et_cachees(tmp_path):
    """Essai minuscule, video d'hier, dossier cache, autre format : ignores."""
    _video(tmp_path, "essai.mp4", taille=1024)
    _video(tmp_path, "hier.mp4", age=7 * 3600)
    _video(tmp_path, ".cache/brouillon.mp4")
    _video(tmp_path, "notes.txt")
    r = lancer(VIDEO, "{}", tmp_path)
    assert r.returncode == 0, r.stderr


def test_video_deja_montree_passe(tmp_path):
    """La marque dit que la video a ete montree apres sa fabrication : il passe."""
    _video(tmp_path, "concours.mp4")
    marque = tmp_path / ".claude" / "portes" / ".videos-montrees"
    marque.parent.mkdir(parents=True)
    marque.write_text(json.dumps({"concours.mp4": time.time() + 60}))
    assert lancer(VIDEO, "{}", tmp_path).returncode == 0


def test_video_marque_abimee_refuse_quand_meme(tmp_path):
    """Une marque illisible ne vaut pas « deja montree »."""
    _video(tmp_path, "concours.mp4")
    marque = tmp_path / ".claude" / "portes" / ".videos-montrees"
    marque.parent.mkdir(parents=True)
    marque.write_text("{casse")
    assert lancer(VIDEO, "", tmp_path).returncode == 2


# ─────────────────────────── garde-jamais-bannir-patrick.py ────────────────

BANNIR = "garde-jamais-bannir-patrick.py"


def _cmd(c):
    return {"tool_name": "Bash", "tool_input": {"command": c}}


@pytest.mark.parametrize("cmd", [
    "sudo ipset add robots 1.2.3.4",
    "fail2ban-client set sshd banip 1.2.3.4",
    "ufw deny from 1.2.3.4",
    "iptables -A INPUT -s 1.2.3.4 -j DROP",
])
def test_bannir_sans_verification_refuse(tmp_path, cmd):
    """Tout geste qui bannit, sans temoin de l'adresse de Patrick : code 2."""
    r = lancer(BANNIR, _cmd(cmd), tmp_path)
    assert r.returncode == 2
    assert "quelle-est-mon-adresse.py" in r.stderr
    assert cmd[:20] in r.stderr


def test_bannir_apres_verification_fraiche_passe(tmp_path):
    """Temoin de moins de quinze minutes : le bannissement passe."""
    t = tmp_path / ".claude" / "portes" / ".ip-patrick-verifiee"
    t.parent.mkdir(parents=True)
    t.write_text("1.1.1.1")
    assert lancer(BANNIR, _cmd("ipset add robots 1.2.3.4"), tmp_path).returncode == 0


def test_bannir_temoin_perime_refuse(tmp_path):
    """Temoin vieux d'une heure : il ne vaut plus rien."""
    t = tmp_path / ".claude" / "portes" / ".ip-patrick-verifiee"
    t.parent.mkdir(parents=True)
    t.write_text("1.1.1.1")
    vieux = time.time() - 3600
    os.utime(t, (vieux, vieux))
    assert lancer(BANNIR, _cmd("ufw insert from 9.9.9.9"), tmp_path).returncode == 2


@pytest.mark.parametrize("entree", [
    "pas du json", {}, {"tool_input": None}, _cmd("iptables -L -n"), _cmd("ls"),
])
def test_bannir_gestes_inoffensifs_passent(tmp_path, entree):
    """Lister les regles, une autre commande, une entree vide : il passe."""
    r = lancer(BANNIR, entree, tmp_path)
    assert r.returncode == 0 and r.stderr == ""


def test_bannir_temoin_inverifiable_refuse(tmp_path):
    """Si le temoin ne peut meme pas etre regarde (chemin trop long), on refuse."""
    maison = tmp_path / ("m" * 300)
    r = lancer(BANNIR, _cmd("ipset add robots 1.2.3.4"), maison, cwd=tmp_path)
    assert r.returncode == 2
    assert "GARDE DU BANNISSEMENT" in r.stderr


def test_video_entree_illisible_ne_desarme_pas(tmp_path):
    """Une entree qui ne se decode pas n'empeche pas le garde de regarder."""
    _video(tmp_path, "concours.mp4")
    e = dict(os.environ, HOME=str(tmp_path), PYTHONIOENCODING="utf-8:strict")
    r = subprocess.run([sys.executable, os.path.join(GARDES, VIDEO)],
                       input=b"\xff\xfe\xfa", capture_output=True, env=e,
                       cwd=str(tmp_path), timeout=30)
    assert r.returncode == 2
    assert b"concours.mp4" in r.stderr
