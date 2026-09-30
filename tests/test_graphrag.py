#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""INIT GRAPHRAG — les relations devinees, le graphe, et la ligne de commande.

Ce qu'on prouve, dans un dossier jetable :
  - chaque paire de types d'entites donne la relation annoncee ;
  - une fiche a moins de deux entites ne produit aucun triplet ;
  - une arete en double garde la MEILLEURE confiance ;
  - un graphe non amorce cree lui-meme les noeuds qu'il rencontre ;
  - les voisins sont rendus dans les deux sens ;
  - main() ingere un registre et une fiche, puis sauve le graphe.
"""
import importlib.util
import json
import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location(
    "init_graphrag", os.path.join(REPO, "scripts", "init_graphrag.py"))
G = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(G)


@pytest.mark.parametrize("a, b, relation", [
    ("arthur", "qwen", "UTILISE"),
    ("docker", "tour", "TOURNE_SUR"),
    ("tour", "arthur", "HEBERGE"),
    ("cockpit", "python", "DEPEND_DE"),
    ("patrick", "vps", "POSSEDE"),
    ("arthur", "braignak", "COMMUNIQUE_AVEC"),
    ("jimmy", "haichi", "FAIT_PARTIE_DE"),
    ("caddy", "vitrine", "SERT"),
    ("patrick", "docker", "EST_LIE_A"),
    ("inconnu", "autre", "EST_LIE_A"),
])
def test_relations_devinees(a, b, relation):
    """Chaque paire de types donne sa relation ; le reste est EST_LIE_A."""
    assert G._guess_relation(a, b) == relation


def test_moins_de_deux_entites():
    assert G.extract_triplets_from_fiche({"mots": ["docker"], "answer": "rien d'autre"}) == []


def test_sujet_hors_des_mots():
    """Sans entite dans les mots, le sujet est la premiere entite de la reponse."""
    t = G.extract_triplets_from_fiche({"mots": ["question"], "answer": "Caddy sert la vitrine"})
    assert t == [{"entity_a": "caddy", "relation": "SERT", "entity_b": "vitrine",
                  "confidence": 0.7}]


def test_mot_entier_seulement():
    """« tour » n'est pas dans « detournement »."""
    assert G.extract_entities("un détournement") == []


def test_doublon_garde_la_meilleure_confiance():
    g = G.KnowledgeGraph()
    g.add_edge("a", "b", "UTILISE", 0.5)
    g.add_edge("a", "b", "UTILISE", 0.9)
    g.add_edge("a", "b", "UTILISE", 0.1)
    assert len(g.edges) == 1
    assert g.edges[0]["confidence"] == 0.9


def test_graphe_non_amorce_et_voisins():
    """Les noeuds sont crees a la volee ; les voisins sortants et entrants."""
    g = G.KnowledgeGraph()
    n = g.ingest_fiche({"mots": ["docker"], "answer": "Docker tourne sur la tour"}, source="f1")
    assert n == 1
    assert g.nodes["docker"] == {"type": "technologie", "label": "Docker", "meta": {}}
    assert g.nodes["tour"]["label"] == "Tour de Contrôle"
    assert g.query_neighbors("tour") == [{"entity": "docker", "relation": "TOURNE_SUR",
                                          "direction": "entrant", "confidence": 0.7}]
    assert g.query_neighbors("docker")[0]["direction"] == "sortant"
    assert g.query_neighbors("personne") == []


def test_registre_ignore_les_non_fiches():
    g = G.KnowledgeGraph()
    total = g.ingest_registre({"meta": "x", "sans_mots": {"answer": "Docker tour"},
                               "f": {"mots": ["arthur"], "answer": "Arthur utilise Qwen"}})
    assert total == 1
    assert g.edges[0]["source"] == "f"


def test_sauver_et_recharger(tmp_path):
    g = G.KnowledgeGraph()
    g.seed_known_entities()
    g.add_edge("arthur", "qwen", "UTILISE", 0.8, "essai")
    chemin = str(tmp_path / "g.json")
    g.save(chemin)
    h = G.KnowledgeGraph()
    h.load(chemin)
    assert h.nodes == g.nodes and h.edges == g.edges and h.version == 1
    d = json.load(open(chemin, encoding="utf-8"))
    assert d["stats"] == {"node_count": len(G.KNOWN_ENTITIES), "edge_count": 1}


def test_main_registre_et_fiche(tmp_path, monkeypatch, capsys):
    """La ligne de commande ingere un registre ET une fiche, puis sauve."""
    registre = tmp_path / "registre.json"
    registre.write_text(json.dumps({
        "f1": {"mots": ["docker"], "answer": "Docker tourne sur la tour"},
        "f2": {"mots": ["arthur"], "answer": "Arthur utilise Qwen et Ollama"},
    }), encoding="utf-8")
    sortie = tmp_path / "graphe.json"
    monkeypatch.setattr(sys, "argv", [
        "init_graphrag.py", "--registre", str(registre), "--output", str(sortie),
        "--fiche", json.dumps({"mots": ["caddy"], "answer": "Caddy sert la vitrine"})])
    assert G.main() == 0
    out = capsys.readouterr().out
    assert "Registre ingéré : 3 triplets extraits de 2 fiches" in out
    assert "Fiche ingérée : 1 triplets" in out
    d = json.load(open(str(sortie), encoding="utf-8"))
    assert d["stats"]["edge_count"] == 4
    assert "%d nœuds, 4 arêtes" % len(G.KNOWN_ENTITIES) in out


def test_main_amorce_seule(tmp_path, monkeypatch, capsys):
    sortie = tmp_path / "seul.json"
    monkeypatch.setattr(sys, "argv", ["init_graphrag.py", "--seed-only", "--output", str(sortie)])
    assert G.main() == 0
    d = json.load(open(str(sortie), encoding="utf-8"))
    assert d["stats"] == {"node_count": len(G.KNOWN_ENTITIES), "edge_count": 0}


if __name__ == "__main__":
    sys.exit(pytest.main(["-q", __file__]))
