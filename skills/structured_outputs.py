#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""STRUCTURED OUTPUTS — schémas JSON stricts pour les appels LLM.

Remplace tout prompt engineering "Réponds uniquement en JSON" par un
schéma JSON strict passé au moteur d'inférence. Le LLM est CONTRAINT
de produire un JSON conforme — zéro parsing fragile, zéro regex.

Chaque schéma est un dict JSON Schema (draft-2020-12) que l'on passe
via response_format (OpenAI-compatible) ou via les Structured Outputs
de Google/Anthropic.

Usage :
  from skills.structured_outputs import get_schema, wrap_openai_call
  schema = get_schema("veilleur_fiche")
  result = wrap_openai_call(messages, schema)  # rend un dict validé
"""
import json
import re

# ══════════════════════════════════════════════════════════════════════════
# CATALOGUE DES SCHÉMAS
# ══════════════════════════════════════════════════════════════════════════

SCHEMAS = {
    # Le veilleur de savoir : structurer une lacune en fiche
    "veilleur_fiche": {
        "type": "object",
        "properties": {
            "mots": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Mots-clés pour indexer cette fiche"
            },
            "think": {
                "type": "string",
                "description": "Raisonnement interne (contexte, source)"
            },
            "answer": {
                "type": "string",
                "description": "Réponse factuelle, sans invention"
            },
            "source": {
                "type": "string",
                "description": "URL ou référence de la source"
            },
            "date_capture": {
                "type": "string",
                "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
                "description": "Date de capture AAAA-MM-JJ"
            },
            "confiance": {
                "type": "number",
                "minimum": 0,
                "maximum": 1,
                "description": "Score de fiabilite deterministe (grade de la source + fraicheur de la date)"
            },
        },
        "required": ["mots", "think", "answer", "source", "date_capture", "confiance"],
        "additionalProperties": False,
    },

    # L'éveil synthétique : état du système
    "eveil_etat": {
        "type": "object",
        "properties": {
            "resume": {
                "type": "string",
                "description": "Résumé en une phrase de l'état"
            },
            "problemes": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Liste des problèmes détectés"
            },
            "actions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Actions recommandées"
            },
        },
        "required": ["resume", "problemes", "actions"],
        "additionalProperties": False,
    },

    # Analyse de test : résultat structuré
    "analyse_test": {
        "type": "object",
        "properties": {
            "verdict": {
                "type": "string",
                "enum": ["vert", "rouge", "orange"],
                "description": "vert=tout passe, rouge=échecs, orange=warnings"
            },
            "total": {"type": "integer"},
            "passed": {"type": "integer"},
            "failed": {"type": "integer"},
            "resume": {
                "type": "string",
                "description": "Résumé des échecs en une phrase"
            },
        },
        "required": ["verdict", "total", "passed", "failed", "resume"],
        "additionalProperties": False,
    },

    # Triplet GraphRAG : extraction d'entités
    "graphrag_triplet": {
        "type": "object",
        "properties": {
            "entity_a": {
                "type": "string",
                "description": "Entité source"
            },
            "relation": {
                "type": "string",
                "description": "Type de relation (EST_UN, UTILISE, DEPEND_DE, etc.)"
            },
            "entity_b": {
                "type": "string",
                "description": "Entité cible"
            },
            "confidence": {
                "type": "number",
                "minimum": 0,
                "maximum": 1,
                "description": "Score de confiance [0, 1]"
            },
        },
        "required": ["entity_a", "relation", "entity_b", "confidence"],
        "additionalProperties": False,
    },
}


def get_schema(name):
    """Rend le schéma JSON par nom. KeyError si inconnu."""
    if name not in SCHEMAS:
        raise KeyError(f"Schéma inconnu : {name}. "
                       f"Connus : {', '.join(SCHEMAS.keys())}")
    return SCHEMAS[name]


def list_schemas():
    """Rend la liste des noms de schémas disponibles."""
    return list(SCHEMAS.keys())


def validate(data, schema_name):
    """Validation STRICTE d'un dict contre un schéma.

    Rend (True, None) si valide, (False, message) sinon.
    N'utilise PAS jsonschema (dépendance externe) : validation manuelle
    des champs required et des types de base.
    """
    schema = get_schema(schema_name)
    errors = []

    if not isinstance(data, dict):
        return False, "données non-dict"

    # Champs requis
    for field in schema.get("required", []):
        if field not in data:
            errors.append(f"champ requis manquant : {field}")

    # Types de base
    props = schema.get("properties", {})
    for field, value in data.items():
        if field not in props:
            if schema.get("additionalProperties") is False:
                errors.append(f"champ inconnu : {field}")
            continue

        expected_type = props[field].get("type")
        if expected_type == "string" and not isinstance(value, str):
            errors.append(f"{field} : attendu string, reçu {type(value).__name__}")
        elif expected_type == "integer" and not isinstance(value, int):
            errors.append(f"{field} : attendu integer, reçu {type(value).__name__}")
        elif expected_type == "number" and not isinstance(value, (int, float)):
            errors.append(f"{field} : attendu number, reçu {type(value).__name__}")
        elif expected_type == "array" and not isinstance(value, list):
            errors.append(f"{field} : attendu array, reçu {type(value).__name__}")
        elif expected_type == "object" and not isinstance(value, dict):
            errors.append(f"{field} : attendu object, reçu {type(value).__name__}")

        # Pattern (pour date_capture)
        if expected_type == "string" and "pattern" in props[field]:
            if isinstance(value, str) and not re.fullmatch(props[field]["pattern"], value):
                errors.append(f"{field} : ne matche pas le pattern {props[field]['pattern']}")

        # Enum
        if "enum" in props[field]:
            if value not in props[field]["enum"]:
                errors.append(f"{field} : valeur '{value}' hors enum {props[field]['enum']}")

    if errors:
        return False, "; ".join(errors)
    return True, None


def format_for_openai(schema_name):
    """Rend le dict response_format compatible OpenAI pour Structured Outputs.

    Usage dans l'appel API :
      response_format=format_for_openai("veilleur_fiche")
    """
    return {
        "type": "json_schema",
        "json_schema": {
            "name": schema_name,
            "strict": True,
            "schema": get_schema(schema_name),
        }
    }


def format_for_anthropic(schema_name):
    """Rend le tool_choice + tools pour forcer un JSON structuré via Anthropic.

    Anthropic utilise le pattern "tool use" pour les Structured Outputs :
    on déclare un outil fictif dont le schéma est notre format de sortie.
    """
    schema = get_schema(schema_name)
    # 22/09/2026 : forcer un outil precis (tool_choice « tool » ou « any ») rend
    # desormais une erreur 400 — la demande est refusee. Seuls « auto » et
    # « none » passent. Pour garder la forme de la reponse garantie, on marque
    # l'outil « strict » : la doc appelle ca le « strict tool use ».
    return {
        "tools": [{
            "name": schema_name,
            "description": f"Structured output: {schema_name}",
            "input_schema": schema,
            "strict": True,
        }],
        "tool_choice": {"type": "auto"},
    }


def format_for_google(schema_name):
    """Rend le generation_config pour Google Gemini Structured Outputs.

    Gemini utilise response_mime_type + response_schema.
    """
    return {
        "response_mime_type": "application/json",
        "response_schema": get_schema(schema_name),
    }
