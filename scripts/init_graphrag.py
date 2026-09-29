#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""INIT GRAPHRAG — fondations du graphe de connaissances.

Remplace le modèle plat lacunes.json par une base orientée graphe :
chaque fiche de savoir devient un ensemble de TRIPLETS
  (Entité A) --[RELATION]--> (Entité B)

Ceci élimine les confusions d'entités lors des recherches vectorielles :
au lieu de chercher "Docker + tour" et d'obtenir n'importe quoi,
on traverse le graphe :
  Docker --[TOURNE_SUR]--> Tour
  Tour --[HÉBERGE]--> Caddy
  Caddy --[SERT]--> Vitrine

Le graphe est stocké en JSON (pas de base externe) pour rester autonome.

Structure du graphe :
  {
    "nodes": {
      "docker": {"type": "technologie", "label": "Docker", "meta": {}},
      "tour":   {"type": "infrastructure", "label": "Tour de Contrôle", "meta": {}},
      ...
    },
    "edges": [
      {"from": "docker", "to": "tour", "relation": "TOURNE_SUR", "confidence": 0.95, "source": "..."},
      ...
    ],
    "version": 1,
    "updated": "2026-09-21T21:00:00"
  }

Usage :
  python scripts/init_graphrag.py --registre registre_exemple.json --output graphe.json
  python scripts/init_graphrag.py --fiche '{"mots": [...], "answer": "..."}'
"""
import json
import os
import re
import sys
import time


# ══════════════════════════════════════════════════════════════════════════
# TYPES D'ENTITÉS
# ══════════════════════════════════════════════════════════════════════════

ENTITY_TYPES = {
    "technologie": {"desc": "Outil, framework, langage"},
    "infrastructure": {"desc": "Serveur, réseau, machine"},
    "agent": {"desc": "Agent IA (Arthur, Braignak, etc.)"},
    "concept": {"desc": "Concept, méthode, processus"},
    "personne": {"desc": "Personne humaine"},
    "circuit": {"desc": "Procédure, workflow"},
    "service": {"desc": "Service déployé (web, API)"},
    "competence": {"desc": "Compétence d'agent (beelzebuth, etc.)"},
}

# ══════════════════════════════════════════════════════════════════════════
# TYPES DE RELATIONS
# ══════════════════════════════════════════════════════════════════════════

RELATION_TYPES = {
    "EST_UN": "classification (Docker EST_UN conteneur)",
    "UTILISE": "usage actif (Arthur UTILISE Qwen)",
    "TOURNE_SUR": "hébergement (Caddy TOURNE_SUR Tour)",
    "DEPEND_DE": "dépendance (Vitrine DEPEND_DE Caddy)",
    "HEBERGE": "contient/héberge (Tour HEBERGE Alice)",
    "POSSEDE": "propriété (Patrick POSSEDE Tour)",
    "FAIT_PARTIE_DE": "composition (Alice FAIT_PARTIE_DE Tour)",
    "COMMUNIQUE_AVEC": "échange (Arthur COMMUNIQUE_AVEC Alice)",
    "PROTEGE": "sécurité (Garde PROTEGE Savoir)",
    "SURVEILLE": "monitoring (Cockpit SURVEILLE Tour)",
    "PRODUIT": "création (Veilleur PRODUIT Fiche)",
    "SERT": "exposition (Caddy SERT Vitrine)",
}


# ══════════════════════════════════════════════════════════════════════════
# EXTRACTION DES TRIPLETS D'UNE FICHE
# ══════════════════════════════════════════════════════════════════════════

# Entités connues de la tour (seed initial)
KNOWN_ENTITIES = {
    "docker": ("technologie", "Docker"),
    "caddy": ("technologie", "Caddy"),
    "odoo": ("technologie", "Odoo"),
    "postgresql": ("technologie", "PostgreSQL"),
    "qwen": ("technologie", "Qwen"),
    "nemotron": ("technologie", "Nemotron"),
    "ollama": ("technologie", "Ollama"),
    "python": ("technologie", "Python"),
    "linux": ("technologie", "Linux"),
    "debian": ("technologie", "Debian"),
    "tour": ("infrastructure", "Tour de Contrôle"),
    "vps": ("infrastructure", "VPS"),
    "alice": ("infrastructure", "Alice (machine)"),
    "arthur": ("agent", "Arthur"),
    "braignak": ("agent", "Braignak"),
    "gamma": ("agent", "Gamma"),
    "victor": ("agent", "Victor"),
    "chloe": ("agent", "Chloé"),
    "clark": ("agent", "Clark"),
    "haichi": ("agent", "Haichi"),
    "mirline": ("agent", "Mirline"),
    "patrick": ("personne", "Patrick"),
    "beelzebuth": ("competence", "Beelzebuth"),
    "jimmy": ("competence", "Jimmy"),
    "cockpit": ("service", "Cockpit"),
    "vitrine": ("service", "Vitrine"),
}


def normalize(text):
    """Normalise un texte pour la recherche d'entités."""
    t = (text or "").lower().strip()
    t = re.sub(r"[éèêë]", "e", t)
    t = re.sub(r"[àâä]", "a", t)
    t = re.sub(r"[ùûü]", "u", t)
    t = re.sub(r"[îï]", "i", t)
    t = re.sub(r"[ôö]", "o", t)
    t = re.sub(r"[ç]", "c", t)
    return t


def extract_entities(text):
    """Cherche les entités connues dans un texte. Rend une liste de clés."""
    text_norm = normalize(text)
    found = []
    for key in KNOWN_ENTITIES:
        # Mot entier seulement (pas "tour" dans "detournement")
        if re.search(r"\b" + re.escape(key) + r"\b", text_norm):
            found.append(key)
    return found


def extract_triplets_from_fiche(fiche):
    """Extrait les triplets (entité_a, relation, entité_b) d'une fiche de savoir.

    Stratégie simple mais fiable :
    1. Trouver toutes les entités connues dans les mots + la réponse
    2. Relier la première entité (sujet principal) aux autres

    Rend une liste de dicts {"entity_a", "relation", "entity_b", "confidence"}.
    """
    mots_text = " ".join(fiche.get("mots", []))
    answer_text = fiche.get("answer", "")
    full_text = mots_text + " " + answer_text

    entities = extract_entities(full_text)
    if len(entities) < 2:
        return []

    # Le sujet principal est la première entité trouvée dans les mots-clés
    mots_entities = extract_entities(mots_text)
    subject = mots_entities[0] if mots_entities else entities[0]

    triplets = []
    for other in entities:
        if other == subject:
            continue
        # Deviner la relation par les types d'entités
        relation = _guess_relation(subject, other)
        triplets.append({
            "entity_a": subject,
            "relation": relation,
            "entity_b": other,
            "confidence": 0.7,  # extraction heuristique
        })

    return triplets


def _guess_relation(a, b):
    """Devine la relation entre deux entités par leurs types."""
    type_a = KNOWN_ENTITIES.get(a, ("concept",))[0]
    type_b = KNOWN_ENTITIES.get(b, ("concept",))[0]

    if type_a == "agent" and type_b == "technologie":
        return "UTILISE"
    if type_a == "technologie" and type_b == "infrastructure":
        return "TOURNE_SUR"
    if type_a == "infrastructure" and type_b == "agent":
        return "HEBERGE"
    if type_a == "service" and type_b == "technologie":
        return "DEPEND_DE"
    if type_a == "personne" and type_b == "infrastructure":
        return "POSSEDE"
    if type_a == "agent" and type_b == "agent":
        return "COMMUNIQUE_AVEC"
    if type_a == "competence" and type_b == "agent":
        return "FAIT_PARTIE_DE"
    if type_a == "technologie" and type_b == "service":
        return "SERT"

    return "EST_LIE_A"


# ══════════════════════════════════════════════════════════════════════════
# GRAPHE
# ══════════════════════════════════════════════════════════════════════════

class KnowledgeGraph:
    """Graphe de connaissances JSON pur."""

    def __init__(self):
        self.nodes = {}
        self.edges = []
        self.version = 1

    def add_node(self, key, entity_type, label, meta=None):
        """Ajoute un nœud au graphe."""
        self.nodes[key] = {
            "type": entity_type,
            "label": label,
            "meta": meta or {},
        }

    def add_edge(self, from_key, to_key, relation, confidence=0.7,
                 source=""):
        """Ajoute une arête au graphe."""
        # Éviter les doublons exacts
        for e in self.edges:
            if (e["from"] == from_key and e["to"] == to_key
                    and e["relation"] == relation):
                # Mettre à jour la confiance si supérieure
                if confidence > e.get("confidence", 0):
                    e["confidence"] = confidence
                return

        self.edges.append({
            "from": from_key,
            "to": to_key,
            "relation": relation,
            "confidence": confidence,
            "source": source,
        })

    def seed_known_entities(self):
        """Charge les entités connues de la tour."""
        for key, (etype, label) in KNOWN_ENTITIES.items():
            self.add_node(key, etype, label)

    def ingest_fiche(self, fiche, source=""):
        """Ingère une fiche de savoir dans le graphe."""
        triplets = extract_triplets_from_fiche(fiche)
        for t in triplets:
            # Assurer que les nœuds existent
            for key in (t["entity_a"], t["entity_b"]):
                if key not in self.nodes:
                    etype = KNOWN_ENTITIES.get(key, ("concept",))[0]
                    label = KNOWN_ENTITIES.get(key, ("concept", key))[1]
                    self.add_node(key, etype, label)
            self.add_edge(t["entity_a"], t["entity_b"], t["relation"],
                          t["confidence"], source)
        return len(triplets)

    def ingest_registre(self, registre):
        """Ingère tout un registre de connaissances dans le graphe."""
        total = 0
        for cle, fiche in registre.items():
            if isinstance(fiche, dict) and "mots" in fiche:
                total += self.ingest_fiche(fiche, source=cle)
        return total

    def query_neighbors(self, entity_key):
        """Rend les voisins directs d'une entité."""
        neighbors = []
        for e in self.edges:
            if e["from"] == entity_key:
                neighbors.append({
                    "entity": e["to"],
                    "relation": e["relation"],
                    "direction": "sortant",
                    "confidence": e.get("confidence", 0),
                })
            elif e["to"] == entity_key:
                neighbors.append({
                    "entity": e["from"],
                    "relation": e["relation"],
                    "direction": "entrant",
                    "confidence": e.get("confidence", 0),
                })
        return neighbors

    def to_dict(self):
        """Sérialise le graphe en dict JSON."""
        return {
            "nodes": self.nodes,
            "edges": self.edges,
            "version": self.version,
            "updated": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "stats": {
                "node_count": len(self.nodes),
                "edge_count": len(self.edges),
            },
        }

    def save(self, filepath):
        """Sauvegarde le graphe sur disque."""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    def load(self, filepath):
        """Charge le graphe depuis le disque."""
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
        self.nodes = data.get("nodes", {})
        self.edges = data.get("edges", [])
        self.version = data.get("version", 1)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Init GraphRAG — fondations du graphe de connaissances")
    parser.add_argument("--registre", help="Chemin du registre de connaissances JSON")
    parser.add_argument("--output", default="graphe.json", help="Fichier de sortie")
    parser.add_argument("--fiche", help="Fiche JSON unique à ingérer")
    parser.add_argument("--seed-only", action="store_true", help="Ne créer que les entités connues")
    args = parser.parse_args()

    graph = KnowledgeGraph()
    graph.seed_known_entities()

    total_triplets = 0

    if args.registre:
        with open(args.registre, encoding="utf-8") as f:
            registre = json.load(f)
        total_triplets = graph.ingest_registre(registre)
        print(f"Registre ingéré : {total_triplets} triplets extraits "
              f"de {len(registre)} fiches")

    if args.fiche:
        fiche = json.loads(args.fiche)
        n = graph.ingest_fiche(fiche)
        total_triplets += n
        print(f"Fiche ingérée : {n} triplets")

    graph.save(args.output)
    stats = graph.to_dict()["stats"]
    print(f"Graphe sauvé dans {args.output} : "
          f"{stats['node_count']} nœuds, {stats['edge_count']} arêtes")

    return 0


if __name__ == "__main__":
    sys.exit(main())
