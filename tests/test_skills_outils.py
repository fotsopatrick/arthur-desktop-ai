#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LES PETITS OUTILS MCP — eveil, refactor, cache, checkpoint, schemas.

Ce qu'on prouve, sans reseau et dans des dossiers jetables :
  - eveil : un agent qui ecoute est « up », un /proc illisible donne None,
    une section qui plante n'emporte pas les autres, main() parle JSON ;
  - refactor : fichier non UTF-8 refuse (jamais reecrit), droits non
    copiables, fichier temporaire impossible, main() rend 0 ou 1 ;
  - cache de prompt : les erreurs d'usage, le cache disque, les economies ;
  - checkpoint : etat abime, autre cycle, reprise, resume lisible ;
  - schemas : chaque type mal donne est nomme.
"""
import json
import os
import socket
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from skills import mcp_eveil, mcp_refactor  # noqa: E402
from skills import prompt_caching, state_checkpoint, structured_outputs  # noqa: E402


# ══════════════════════════════════════════════════════════════════════════
# EVEIL
# ══════════════════════════════════════════════════════════════════════════

class TestEveil:
    def test_git_modifie_et_nouveau(self, monkeypatch):
        """Les lignes de git status sont rangees : modifie, non suivi, vide ignoree."""
        sorties = {
            "rev-parse": "main",
            "status": " M a.py\n\n?? b.py\nA  c.py",
            "log": "abc123 premier\nsansmessage",
        }

        def faux_run(cmd, cwd=None, timeout=10):
            return sorties[cmd[1]]
        monkeypatch.setattr(mcp_eveil, "_run", faux_run)
        r = mcp_eveil.git_state("/nulle/part")
        assert r["branch"] == "main"
        assert r["modified"] == ["a.py", "c.py"]
        assert r["untracked"] == ["b.py"]
        assert r["clean"] is False
        assert r["last_commits"] == [{"hash": "abc123", "message": "premier"}]

    def test_run_commande_introuvable(self):
        assert mcp_eveil._run(["commande-qui-n-existe-pas-xyz"]) is None

    def test_agent_qui_ecoute_est_up(self):
        """Un vrai port ouvert sur cette machine : statut « up », latence mesuree."""
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        try:
            port = s.getsockname()[1]
            etat, latence = mcp_eveil.probe_agent("127.0.0.1", port, timeout=2)
            assert etat == "up"
            assert isinstance(latence, float) and latence >= 0
            r = mcp_eveil.agents_state({"moi": port})
            assert r["moi"]["status"] == "up" and r["moi"]["port"] == port
        finally:
            s.close()

    def test_proc_illisible(self, monkeypatch):
        """Sans /proc ni disque lisibles : des None, pas d'exception."""
        def pas_de_proc(*a, **k):
            raise OSError("pas de /proc")
        monkeypatch.setattr(mcp_eveil, "open", pas_de_proc, raising=False)
        monkeypatch.setattr(mcp_eveil.os, "statvfs", pas_de_proc)
        r = mcp_eveil.system_state()
        assert r["load_1m"] is None
        assert r["mem_used_pct"] is None
        assert r["disk_used_pct"] is None
        assert r["hostname"]

    def test_section_qui_plante(self, monkeypatch):
        """Une section en panne est nommee ; les autres repondent quand meme."""
        def boum():
            raise RuntimeError("capteur mort")
        monkeypatch.setattr(mcp_eveil, "system_state", boum)
        r = mcp_eveil.eveil(REPO, agents={"x": 1})
        assert "capteur mort" in r["system"]["error"]
        assert "section system" in r["system"]["error"]
        assert r["agents"]["x"]["status"] == "down"
        assert "timestamp" in r

    def test_main_lisible(self, monkeypatch, capsys):
        monkeypatch.setattr(mcp_eveil, "eveil", lambda repo, host: {"repo": repo, "host": host})
        monkeypatch.setattr(sys, "argv", ["mcp_eveil.py", "--repo", "/x", "--host", "h"])
        assert mcp_eveil.main() == 0
        out = capsys.readouterr().out
        assert json.loads(out) == {"repo": "/x", "host": "h"}
        assert '\n  "repo"' in out

    def test_main_eveil_en_panne(self, monkeypatch, capsys):
        """main() ne laisse jamais sortir une trace Python."""
        def boum(*a, **k):
            raise RuntimeError("tout casse")
        monkeypatch.setattr(mcp_eveil, "eveil", boum)
        monkeypatch.setattr(sys, "argv", ["mcp_eveil.py", "--json"])
        assert mcp_eveil.main() == 0
        r = json.loads(capsys.readouterr().out)
        assert "tout casse" in r["error"]


# ══════════════════════════════════════════════════════════════════════════
# REFACTOR
# ══════════════════════════════════════════════════════════════════════════

class TestRefactor:
    def test_fichier_non_utf8_refuse(self, tmp_path):
        """Un fichier Latin-1 n'est JAMAIS reecrit : erreur nommee, octets intacts."""
        f = tmp_path / "latin.txt"
        octets = "caf\xe9 ancien\n".encode("latin-1")
        f.write_bytes(octets)
        r = mcp_refactor.refactor("*.txt", "ancien", "nouveau", base_dir=str(tmp_path))
        assert r["success"] is False
        assert r["files_modified"] == 0
        assert r["changes"][0]["file"] == "latin.txt"
        assert "erreur lecture" in r["changes"][0]["error"]
        assert f.read_bytes() == octets
        assert not [p for p in os.listdir(tmp_path) if p.endswith(".mcp_tmp")]

    def test_temporaire_non_efface(self, tmp_path, monkeypatch):
        """Meme si le temporaire ne s'efface pas, l'erreur est rendue proprement."""
        f = tmp_path / "latin.txt"
        f.write_bytes(b"\xff\xfe ancien")

        def refuse(chemin):
            raise OSError("verrou")
        monkeypatch.setattr(mcp_refactor.os, "unlink", refuse)
        n, lignes, err = mcp_refactor.refactor_file(str(f), "ancien", "x")
        assert (n, lignes) == (0, [])
        assert "erreur lecture" in err

    def test_temporaire_impossible(self, tmp_path):
        """Dossier inexistant : impossible de creer le temporaire, on le dit."""
        n, lignes, err = mcp_refactor.refactor_file(
            str(tmp_path / "absent" / "f.py"), "a", "b")
        assert (n, lignes) == (0, [])
        assert "temporaire" in err

    def test_droits_non_copiables(self, tmp_path, monkeypatch):
        """chmod refuse : le remplacement se fait quand meme."""
        f = tmp_path / "a.py"
        f.write_text("x = ancien\n", encoding="utf-8")

        def refuse(*a):
            raise OSError("chmod interdit")
        monkeypatch.setattr(mcp_refactor.os, "chmod", refuse)
        n, lignes, err = mcp_refactor.refactor_file(str(f), "ancien", "neuf")
        assert (n, lignes, err) == (1, [1], None)
        assert f.read_text(encoding="utf-8") == "x = neuf\n"

    def test_binaire_illisible(self, tmp_path):
        """Un fichier illisible est traite comme binaire (donc ignore)."""
        assert mcp_refactor._is_binary(str(tmp_path / "absent")) is True

    def test_main_ecrit(self, tmp_path, monkeypatch, capsys):
        f = tmp_path / "a.py"
        f.write_text("ancien\nancien\n", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["mcp_refactor.py", "--glob", "*.py", "--target", "ancien",
                                          "--replace", "neuf", "--base-dir", str(tmp_path)])
        assert mcp_refactor.main() == 0
        r = json.loads(capsys.readouterr().out)
        assert r["total_replacements"] == 2
        assert f.read_text(encoding="utf-8") == "neuf\nneuf\n"

    def test_main_exception(self, monkeypatch, capsys):
        """Une panne imprevue devient un JSON, code 1."""
        def boum(*a, **k):
            raise RuntimeError("imprevu")
        monkeypatch.setattr(mcp_refactor, "refactor", boum)
        monkeypatch.setattr(sys, "argv", ["mcp_refactor.py", "--glob", "*", "--target", "a",
                                          "--replace", "b", "--json"])
        assert mcp_refactor.main() == 1
        r = json.loads(capsys.readouterr().out)
        assert r == {"success": False, "reason": "erreur inattendue : imprevu"}


# ══════════════════════════════════════════════════════════════════════════
# CACHE DE PROMPT
# ══════════════════════════════════════════════════════════════════════════

class TestCache:
    def test_formats_sans_blocs(self, tmp_path):
        c = prompt_caching.CacheManager(cache_dir=str(tmp_path))
        with pytest.raises(ValueError):
            c.format_anthropic_messages("q")
        with pytest.raises(ValueError):
            c.format_google_config("q")
        assert c.save_local_cache() is None

    def test_anthropic_trois_blocs(self, tmp_path):
        c = prompt_caching.CacheManager("anthropic", cache_dir=str(tmp_path))
        c.set_static_blocks("systeme", {"eveil": "x"}, "regles")
        system, messages = c.format_anthropic_messages("bonjour")
        assert [b["text"] for b in system] == ["systeme", '{"eveil": "x"}', "regles"]
        assert all(b["cache_control"] == {"type": "ephemeral"} for b in system)
        assert messages == [{"role": "user", "content": "bonjour"}]

    def test_cache_disque_absent(self, tmp_path):
        c = prompt_caching.CacheManager(cache_dir=str(tmp_path / "absent"))
        assert c.load_local_cache() is False

    def test_cache_disque_tri(self, tmp_path):
        """On saute les non-JSON, les fichiers abimes et les mauvais hash."""
        c = prompt_caching.CacheManager(cache_dir=str(tmp_path))
        c.set_static_blocks("systeme A")
        c.save_local_cache()
        (tmp_path / "note.txt").write_text("rien", encoding="utf-8")
        (tmp_path / "abime.json").write_text("{", encoding="utf-8")
        d = prompt_caching.CacheManager(cache_dir=str(tmp_path))
        assert d.load_local_cache(expected_hash="0" * 64) is False
        assert d.load_local_cache(expected_hash=c.get_static_hash()) is True
        assert d.get_static_hash() == c.get_static_hash()
        assert d.get_stats()["cache_hits"] == 1

    def test_economies_par_backend(self, tmp_path):
        """Anthropic 90 %, Google 75 %, local 100 % par hit."""
        attendus = {"anthropic": 900, "google": 750, "local": 1000}
        for backend, attendu in attendus.items():
            c = prompt_caching.CacheManager(backend, cache_dir=str(tmp_path))
            c.set_static_blocks("s")
            c.set_static_blocks("s")          # meme contenu : un hit
            assert c.estimate_savings(1000) == attendu
            assert c.get_stats()["tokens_saved"] == attendu


# ══════════════════════════════════════════════════════════════════════════
# CHECKPOINT
# ══════════════════════════════════════════════════════════════════════════

class TestCheckpoint:
    def test_autre_cycle_repart_de_zero(self, tmp_path):
        chemin = tmp_path / "etat.json"
        chemin.write_text(json.dumps({"cycle": "autre", "step": 4}), encoding="utf-8")
        c = state_checkpoint.Checkpoint("beelzebuth", state_file=str(chemin))
        assert c.load() is True
        assert c.current_step == 0 and c.state["cycle"] == "beelzebuth"

    def test_etat_abime(self, tmp_path):
        chemin = tmp_path / "etat.json"
        chemin.write_text("{abime", encoding="utf-8")
        c = state_checkpoint.Checkpoint(state_file=str(chemin))
        assert c.load() is False
        assert c.current_step == 0

    def test_save_sans_etat(self, tmp_path):
        c = state_checkpoint.Checkpoint(state_dir=str(tmp_path / "sous"))
        chemin = c.save()
        assert json.load(open(chemin, encoding="utf-8"))["step"] == 0

    def test_advance_charge_puis_termine(self, tmp_path):
        """advance() charge seul l'etat ; mark_done ajoute les donnees."""
        c = state_checkpoint.Checkpoint(state_dir=str(tmp_path))
        assert c.advance("eveil") == 1
        c.mark_done({"verdict": "vert"})
        assert c.is_step_done("eveil")
        assert c.state["data"] == {"verdict": "vert"}
        assert c.should_resume_from("eveil") is False
        assert c.should_resume_from("autre") is False

    def test_resume_vide(self):
        c = state_checkpoint.Checkpoint()
        assert c.summary() == "Pas d'état chargé."
        assert c.should_resume_from("eveil") is True     # rien n'a commence

    @pytest.mark.xfail(strict=True, reason="bug: state_checkpoint.py:153-154 — mark_done(data) "
                       "sur un checkpoint jamais charge fait None['data'] (TypeError)")
    def test_mark_done_sans_chargement(self, tmp_path):
        c = state_checkpoint.Checkpoint(state_dir=str(tmp_path))
        c.mark_done({"x": 1})
        assert c.state["data"] == {"x": 1}


# ══════════════════════════════════════════════════════════════════════════
# SCHEMAS
# ══════════════════════════════════════════════════════════════════════════

class TestSchemas:
    def test_pas_un_dict(self):
        assert structured_outputs.validate([1], "veilleur_fiche") == (False, "données non-dict")

    def test_champ_inconnu_et_types(self):
        ok, err = structured_outputs.validate(
            {"verdict": "vert", "total": "3", "passed": 1.5, "failed": 0,
             "resume": 7, "intrus": 1}, "analyse_test")
        assert ok is False
        assert "champ inconnu : intrus" in err
        assert "total : attendu integer, reçu str" in err
        assert "passed : attendu integer, reçu float" in err
        assert "resume : attendu string, reçu int" in err

    def test_nombre_et_tableau(self):
        ok, err = structured_outputs.validate(
            {"entity_a": "a", "relation": "R", "entity_b": "b", "confidence": "haute"},
            "graphrag_triplet")
        assert ok is False and "confidence : attendu number, reçu str" in err
        ok, err = structured_outputs.validate({"mots": "docker"}, "veilleur_fiche")
        assert "mots : attendu array, reçu str" in err

    def test_objet_et_champs_libres(self, monkeypatch):
        """Un schema qui accepte des champs libres, avec un champ objet."""
        monkeypatch.setitem(structured_outputs.SCHEMAS, "essai_objet", {
            "type": "object", "properties": {"meta": {"type": "object"}}, "required": []})
        assert structured_outputs.validate({"meta": {}, "libre": 1}, "essai_objet") == (True, None)
        ok, err = structured_outputs.validate({"meta": [1]}, "essai_objet")
        assert ok is False and "meta : attendu object, reçu list" in err


if __name__ == "__main__":
    sys.exit(pytest.main(["-q", __file__]))
