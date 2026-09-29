#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests unitaires pour structured_outputs, prompt_caching, state_checkpoint et init_graphrag.

jimmy : écrits AVANT vérification. On les voit rouge, puis on corrige.
"""
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest


# ══════════════════════════════════════════════════════════════════════════
# STRUCTURED OUTPUTS
# ══════════════════════════════════════════════════════════════════════════

class TestStructuredOutputs:

    def test_get_schema_known(self):
        from skills.structured_outputs import get_schema
        schema = get_schema("veilleur_fiche")
        assert schema["type"] == "object"
        assert "mots" in schema["properties"]

    def test_get_schema_unknown_raises(self):
        from skills.structured_outputs import get_schema
        with pytest.raises(KeyError):
            get_schema("schema_inexistant_xyz")

    def test_list_schemas(self):
        from skills.structured_outputs import list_schemas
        schemas = list_schemas()
        assert "veilleur_fiche" in schemas
        assert "graphrag_triplet" in schemas

    def test_validate_valid_fiche(self):
        from skills.structured_outputs import validate
        data = {
            "mots": ["docker", "conteneur"],
            "think": "Question sur Docker",
            "answer": "Docker est un outil de conteneurisation",
            "source": "https://docker.com",
            "date_capture": "2026-09-21",
            "confiance": 0.9,
        }
        valid, error = validate(data, "veilleur_fiche")
        assert valid is True
        assert error is None

    def test_validate_missing_field(self):
        from skills.structured_outputs import validate
        data = {"mots": ["test"], "think": "ok"}
        # manque answer, source, date_capture
        valid, error = validate(data, "veilleur_fiche")
        assert valid is False
        assert "manquant" in error

    def test_validate_bad_date_pattern(self):
        from skills.structured_outputs import validate
        data = {
            "mots": ["test"],
            "think": "ok",
            "answer": "test",
            "source": "test",
            "date_capture": "pas-une-date",
        }
        valid, error = validate(data, "veilleur_fiche")
        assert valid is False
        assert "pattern" in error

    def test_validate_bad_type(self):
        from skills.structured_outputs import validate
        data = {
            "mots": "pas-un-array",  # devrait être une liste
            "think": "ok",
            "answer": "test",
            "source": "test",
            "date_capture": "2026-09-21",
        }
        valid, error = validate(data, "veilleur_fiche")
        assert valid is False
        assert "array" in error

    def test_validate_enum(self):
        from skills.structured_outputs import validate
        data = {
            "verdict": "bleu",  # pas dans l'enum
            "total": 10,
            "passed": 10,
            "failed": 0,
            "resume": "ok",
        }
        valid, error = validate(data, "analyse_test")
        assert valid is False
        assert "enum" in error

    def test_format_for_openai(self):
        from skills.structured_outputs import format_for_openai
        fmt = format_for_openai("veilleur_fiche")
        assert fmt["type"] == "json_schema"
        assert fmt["json_schema"]["strict"] is True

    def test_format_for_anthropic(self):
        from skills.structured_outputs import format_for_anthropic
        fmt = format_for_anthropic("veilleur_fiche")
        assert "tools" in fmt
        assert fmt["tools"][0]["name"] == "veilleur_fiche"

    def test_format_for_google(self):
        from skills.structured_outputs import format_for_google
        fmt = format_for_google("veilleur_fiche")
        assert fmt["response_mime_type"] == "application/json"


# ══════════════════════════════════════════════════════════════════════════
# PROMPT CACHING
# ══════════════════════════════════════════════════════════════════════════

class TestPromptCaching:

    def test_set_static_blocks(self):
        from skills.prompt_caching import CacheManager
        cm = CacheManager(backend="local")
        h = cm.set_static_blocks("Tu es un agent de la tour.")
        assert isinstance(h, str)
        assert len(h) == 64  # SHA256

    def test_cache_hit_same_content(self):
        from skills.prompt_caching import CacheManager
        cm = CacheManager(backend="local")
        h1 = cm.set_static_blocks("prompt", {"skills": "a"})
        h2 = cm.set_static_blocks("prompt", {"skills": "a"})
        assert h1 == h2
        assert cm.get_stats()["cache_hits"] == 1

    def test_cache_miss_different_content(self):
        from skills.prompt_caching import CacheManager
        cm = CacheManager(backend="local")
        cm.set_static_blocks("prompt v1")
        cm.set_static_blocks("prompt v2")
        assert cm.get_stats()["cache_misses"] == 2

    def test_anthropic_format(self):
        from skills.prompt_caching import CacheManager
        cm = CacheManager(backend="anthropic")
        cm.set_static_blocks("system prompt", {"skill": "beelzebuth"}, "rules")
        system, messages = cm.format_anthropic_messages("question?")
        assert len(system) == 3
        assert system[0]["cache_control"]["type"] == "ephemeral"
        assert messages[0]["content"] == "question?"

    def test_google_format(self):
        from skills.prompt_caching import CacheManager
        cm = CacheManager(backend="google")
        cm.set_static_blocks("system prompt")
        config = cm.format_google_config("question?")
        assert "cached_content" in config
        assert config["user_message"] == "question?"

    def test_save_and_load_local(self):
        from skills.prompt_caching import CacheManager
        tmpdir = tempfile.mkdtemp(prefix="cache_test_")
        try:
            cm1 = CacheManager(backend="local", cache_dir=tmpdir)
            cm1.set_static_blocks("prompt stable", {"s": 1})
            path = cm1.save_local_cache()
            assert path is not None
            assert os.path.exists(path)

            cm2 = CacheManager(backend="local", cache_dir=tmpdir)
            loaded = cm2.load_local_cache(cm1.get_static_hash())
            assert loaded is True
            assert cm2.get_static_hash() == cm1.get_static_hash()
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_estimate_savings(self):
        from skills.prompt_caching import CacheManager
        cm = CacheManager(backend="anthropic")
        cm.set_static_blocks("prompt")
        cm.set_static_blocks("prompt")  # hit
        saved = cm.estimate_savings(1000)
        assert saved > 0


# ══════════════════════════════════════════════════════════════════════════
# STATE CHECKPOINT
# ══════════════════════════════════════════════════════════════════════════

class TestStateCheckpoint:

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp(prefix="checkpoint_test_")

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_create_empty(self):
        from skills.state_checkpoint import Checkpoint
        cp = Checkpoint(state_dir=self.tmpdir)
        cp.load()
        assert cp.current_step == 0
        assert cp.current_step_name == ""

    def test_advance_and_save(self):
        from skills.state_checkpoint import Checkpoint
        cp = Checkpoint(state_dir=self.tmpdir)
        cp.load()
        cp.advance("eveil", data={"git_clean": True})
        assert cp.current_step == 1
        assert cp.current_step_name == "eveil"
        # Vérifier que le fichier existe
        assert os.path.exists(cp.state_file)

    def test_reload_after_crash(self):
        """Simule un crash : on avance, on sauvegarde, on recharge."""
        from skills.state_checkpoint import Checkpoint
        cp1 = Checkpoint(state_dir=self.tmpdir)
        cp1.load()
        cp1.advance("eveil")
        cp1.mark_done()
        cp1.advance("analyse_sage")
        # Crash ici — l'étape 2 est "running"

        cp2 = Checkpoint(state_dir=self.tmpdir)
        loaded = cp2.load()
        assert loaded is True
        assert cp2.current_step == 2
        assert cp2.current_step_name == "analyse_sage"
        assert cp2.is_step_done("eveil")
        assert not cp2.is_step_done("analyse_sage")

    def test_mark_error(self):
        from skills.state_checkpoint import Checkpoint
        cp = Checkpoint(state_dir=self.tmpdir)
        cp.load()
        cp.advance("eveil")
        cp.mark_error("Alice offline")
        history = cp.state["history"]
        assert history[-1]["status"] == "error"
        assert "Alice" in history[-1]["error"]

    def test_reset(self):
        from skills.state_checkpoint import Checkpoint
        cp = Checkpoint(state_dir=self.tmpdir)
        cp.load()
        cp.advance("eveil")
        cp.advance("analyse_sage")
        cp.reset()
        assert cp.current_step == 0
        assert len(cp.state["history"]) == 0

    def test_summary(self):
        from skills.state_checkpoint import Checkpoint
        cp = Checkpoint(state_dir=self.tmpdir)
        cp.load()
        cp.advance("eveil")
        cp.mark_done()
        s = cp.summary()
        assert "eveil" in s
        assert "✅" in s

    def test_should_resume_from(self):
        from skills.state_checkpoint import Checkpoint
        cp = Checkpoint(state_dir=self.tmpdir)
        cp.load()
        cp.advance("eveil")
        # L'étape est "running", on devrait reprendre
        assert cp.should_resume_from("eveil") is True
        cp.mark_done()
        # Maintenant c'est "done", plus besoin de reprendre
        assert cp.should_resume_from("eveil") is False


# ══════════════════════════════════════════════════════════════════════════
# GRAPHRAG
# ══════════════════════════════════════════════════════════════════════════

class TestGraphRAG:

    def test_normalize(self):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
        from init_graphrag import normalize
        assert normalize("Éléphant") == "elephant"
        assert normalize("Ça va ?") == "ca va ?"

    def test_extract_entities(self):
        from init_graphrag import extract_entities
        found = extract_entities("Docker tourne sur la tour de contrôle")
        assert "docker" in found
        assert "tour" in found

    def test_extract_no_false_positive(self):
        """'tour' dans 'détournement' ne doit PAS matcher."""
        from init_graphrag import extract_entities
        found = extract_entities("détournement de fonds")
        assert "tour" not in found

    def test_extract_triplets(self):
        from init_graphrag import extract_triplets_from_fiche
        fiche = {
            "mots": ["docker", "tour"],
            "answer": "Docker tourne sur la tour de contrôle",
        }
        triplets = extract_triplets_from_fiche(fiche)
        assert len(triplets) >= 1
        assert triplets[0]["entity_a"] == "docker"
        assert triplets[0]["entity_b"] == "tour"

    def test_knowledge_graph_seed(self):
        from init_graphrag import KnowledgeGraph
        g = KnowledgeGraph()
        g.seed_known_entities()
        assert len(g.nodes) > 10
        assert "docker" in g.nodes
        assert "arthur" in g.nodes

    def test_knowledge_graph_ingest(self):
        from init_graphrag import KnowledgeGraph
        g = KnowledgeGraph()
        g.seed_known_entities()
        fiche = {
            "mots": ["arthur", "qwen"],
            "answer": "Arthur utilise Qwen sur Alice",
        }
        n = g.ingest_fiche(fiche)
        assert n >= 1
        assert len(g.edges) >= 1

    def test_knowledge_graph_no_duplicate_edges(self):
        from init_graphrag import KnowledgeGraph
        g = KnowledgeGraph()
        g.seed_known_entities()
        fiche = {"mots": ["docker", "tour"], "answer": "Docker sur tour"}
        g.ingest_fiche(fiche)
        g.ingest_fiche(fiche)  # doublon
        # Pas de doublon dans les edges
        count = sum(1 for e in g.edges
                    if e["from"] == "docker" and e["to"] == "tour")
        assert count == 1

    def test_knowledge_graph_save_load(self):
        from init_graphrag import KnowledgeGraph
        tmpfile = tempfile.mktemp(suffix=".json")
        try:
            g1 = KnowledgeGraph()
            g1.seed_known_entities()
            g1.save(tmpfile)
            assert os.path.exists(tmpfile)

            g2 = KnowledgeGraph()
            g2.load(tmpfile)
            assert len(g2.nodes) == len(g1.nodes)
        finally:
            try:
                os.unlink(tmpfile)
            except OSError:
                pass

    def test_query_neighbors(self):
        from init_graphrag import KnowledgeGraph
        g = KnowledgeGraph()
        g.seed_known_entities()
        g.ingest_fiche({"mots": ["docker", "tour"],
                        "answer": "Docker tourne sur la tour"})
        neighbors = g.query_neighbors("docker")
        assert len(neighbors) >= 1
        assert any(n["entity"] == "tour" for n in neighbors)

    def test_ingest_registre(self):
        from init_graphrag import KnowledgeGraph
        registre = {
            "docker_infra": {
                "mots": ["docker", "conteneur"],
                "answer": "Docker isole les applications sur la tour",
            },
            "arthur_agent": {
                "mots": ["arthur", "braignak"],
                "answer": "Arthur et Braignak communiquent",
            },
        }
        g = KnowledgeGraph()
        g.seed_known_entities()
        total = g.ingest_registre(registre)
        assert total >= 2


# EPREUVE NEE DU CHANGEMENT DU 01/09/2026.
# Forcer le modele a se servir d'un outil precis — tool_choice en « any » ou en
# « tool » — rend maintenant une erreur 400 : la demande est refusee. Seuls
# « auto » (il choisit) et « none » (aucun outil) restent acceptes. Un programme
# qui garde l'ancienne forme tombera des qu'on l'appellera.
# La doc dit comment garantir la forme sans forcer : marquer l'outil strict.

def test_anthropic_ne_force_plus_un_outil():
    from skills.structured_outputs import format_for_anthropic
    fmt = format_for_anthropic("veilleur_fiche")
    tc = fmt.get("tool_choice")
    demande = tc.get("type") if isinstance(tc, dict) else tc
    assert demande not in ("any", "tool"), (
        "tool_choice='%s' est refuse depuis le 01/09/2026 (erreur 400) ; "
        "seuls 'auto' et 'none' passent" % demande)


def test_le_schema_reste_garanti_autrement():
    from skills.structured_outputs import format_for_anthropic
    fmt = format_for_anthropic("veilleur_fiche")
    outil = fmt["tools"][0]
    assert outil.get("strict") is True, (
        "sans le forcage, le seul moyen de garantir la forme de la reponse "
        "est de marquer l'outil « strict »")
