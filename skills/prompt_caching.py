#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PROMPT CACHING — cache les prompts système pour diviser la consommation.

Le prompt système, le dictionnaire de skills et les règles garde-savoir
ne changent JAMAIS au cours d'une session. On les cache une fois, et
chaque appel suivant ne paie que les tokens du message utilisateur.

Trois backends supportés :
  - Anthropic : cache_control {"type": "ephemeral"} sur les blocs statiques
  - Google    : context caching via CachedContent
  - Local     : hash SHA256 → fichier disque (pour les modèles locaux)

Usage :
  from skills.prompt_caching import CacheManager
  cache = CacheManager(backend="anthropic")
  cache.set_static_blocks(system_prompt, skills_dict, rules)
  # Chaque appel réutilise le cache :
  response = cache.call(user_message)
"""
import hashlib
import json
import os
import time


class CacheManager:
    """Gestionnaire de cache de prompt multi-backend."""

    def __init__(self, backend="local", cache_dir=None):
        """
        backend : "anthropic", "google", "local"
        cache_dir : dossier pour le cache local (défaut: .prompt_cache/)
        """
        self.backend = backend
        self.cache_dir = cache_dir or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", ".prompt_cache")
        self._static_hash = None
        self._static_blocks = None
        self._cache_id = None  # ID du cache côté API
        self._stats = {"cache_hits": 0, "cache_misses": 0, "tokens_saved": 0}

    def set_static_blocks(self, system_prompt, skills_dict=None, rules=None):
        """Définit les blocs statiques à cacher.

        Ces blocs sont hashés. Si le hash ne change pas, le cache est réutilisé.
        """
        payload = json.dumps({
            "system": system_prompt,
            "skills": skills_dict or {},
            "rules": rules or "",
        }, ensure_ascii=False, sort_keys=True)

        new_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

        if new_hash != self._static_hash:
            self._static_hash = new_hash
            self._static_blocks = {
                "system": system_prompt,
                "skills": skills_dict or {},
                "rules": rules or "",
            }
            self._cache_id = None  # Invalider le cache API
            self._stats["cache_misses"] += 1
        else:
            self._stats["cache_hits"] += 1

        return new_hash

    def get_static_hash(self):
        """Rend le hash des blocs statiques actuels."""
        return self._static_hash

    def format_anthropic_messages(self, user_message):
        """Prépare les messages Anthropic avec cache_control.

        Les blocs statiques portent cache_control: {"type": "ephemeral"},
        ce qui active le Context Caching côté Anthropic.

        Rend (system, messages) prêts pour l'appel API.
        """
        if not self._static_blocks:
            raise ValueError("Appeler set_static_blocks() d'abord")

        system_blocks = [
            {
                "type": "text",
                "text": self._static_blocks["system"],
                "cache_control": {"type": "ephemeral"},
            },
        ]

        if self._static_blocks["skills"]:
            system_blocks.append({
                "type": "text",
                "text": json.dumps(self._static_blocks["skills"],
                                   ensure_ascii=False),
                "cache_control": {"type": "ephemeral"},
            })

        if self._static_blocks["rules"]:
            system_blocks.append({
                "type": "text",
                "text": self._static_blocks["rules"],
                "cache_control": {"type": "ephemeral"},
            })

        messages = [{"role": "user", "content": user_message}]

        return system_blocks, messages

    def format_google_config(self, user_message):
        """Prépare la config Google Gemini avec context caching.

        Rend un dict avec les clés nécessaires pour CachedContent.
        """
        if not self._static_blocks:
            raise ValueError("Appeler set_static_blocks() d'abord")

        return {
            "cached_content": {
                "model": "gemini-2.5-flash",
                "display_name": f"haichi-cache-{self._static_hash[:8]}",
                "contents": [
                    {"role": "user", "parts": [
                        {"text": self._static_blocks["system"]},
                    ]},
                    {"role": "model", "parts": [
                        {"text": "Compris. Je suis prêt."},
                    ]},
                ],
                "system_instruction": {
                    "parts": [
                        {"text": self._static_blocks["system"]},
                        {"text": json.dumps(self._static_blocks["skills"],
                                            ensure_ascii=False)},
                        {"text": self._static_blocks["rules"] or ""},
                    ]
                },
                "ttl": "3600s",  # 1h
            },
            "user_message": user_message,
            "cache_hash": self._static_hash,
        }

    def save_local_cache(self):
        """Sauvegarde le cache sur disque (pour modèles locaux)."""
        if not self._static_blocks or not self._static_hash:
            return None

        os.makedirs(self.cache_dir, exist_ok=True)
        cache_file = os.path.join(self.cache_dir,
                                  f"cache_{self._static_hash[:16]}.json")

        data = {
            "hash": self._static_hash,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "blocks": self._static_blocks,
            "stats": self._stats,
        }

        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)

        return cache_file

    def load_local_cache(self, expected_hash=None):
        """Charge le cache depuis le disque si le hash correspond."""
        if not os.path.isdir(self.cache_dir):
            return False

        for fname in os.listdir(self.cache_dir):
            if not fname.endswith(".json"):
                continue
            try:
                with open(os.path.join(self.cache_dir, fname),
                          encoding="utf-8") as f:
                    data = json.load(f)
                if expected_hash and data.get("hash") != expected_hash:
                    continue
                self._static_hash = data["hash"]
                self._static_blocks = data["blocks"]
                self._stats["cache_hits"] += 1
                return True
            except Exception:
                continue
        return False

    def get_stats(self):
        """Rend les stats de cache."""
        return dict(self._stats)

    def estimate_savings(self, prompt_tokens):
        """Estime les tokens économisés grâce au cache.

        Anthropic facture les cache hits à 10% du prix normal.
        Google facture les cache hits à 25% du prix normal.
        """
        if self.backend == "anthropic":
            savings_ratio = 0.9  # 90% d'économie
        elif self.backend == "google":
            savings_ratio = 0.75  # 75% d'économie
        else:
            savings_ratio = 1.0  # local = gratuit

        saved = int(prompt_tokens * savings_ratio * self._stats["cache_hits"])
        self._stats["tokens_saved"] = saved
        return saved
