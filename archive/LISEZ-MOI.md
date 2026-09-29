# Archive — ce qui ne tourne plus, gardé pour mémoire

Rangé ici le 29/09/2026, pendant la revue de code. Rien de ce dossier n'est
importé, lancé ni testé par Arthur. On garde les fichiers pour pouvoir relire
ce qui a été fait, pas pour s'en servir.

| Fichier | Pourquoi il est ici |
|---|---|
| `serveur_action_arthur.py` | L'ancien serveur d'action (port 8796), sans jeton, ouvert à toute page web. Retiré le 24/09 : le cockpit (8790) sert lui-même `/api/arthur-action`, derrière son jeton. Il occupait aussi le port de la page de la clef Nebius. |
| `arthur_opencode_companion.py`, `daemon_arthur_autonome.py` | Envoyaient leurs messages à ce serveur 8796 retiré : ils tombaient sur la page de la clef Nebius et étaient perdus sans bruit. |
| `arthur_opencode_mcp_bridge.py` | Dépend d'outils personnels (`tdb`, `~/livrables`) absents du dépôt ; jamais appelé. |
| `page_jeton_github.py`, `pages-a-secret/` | Cinq pages qui rangeaient des secrets dans des fichiers que **rien ne lisait**. Deux étaient cassées (`{{ }}`), une ne démarrait pas, deux partageaient un port. La seule page utile, `page_cle_nebius.py`, reste à la racine (port 8796). |
| `gamma_avatar.py`, `gamma/`, `gamma.png`, `fabriquer_gamma_png.py` | Copie presque identique de `haichi_avatar.py` ; rien ne la lançait. |

Pour ressortir un fichier : `git mv archive/<fichier> .`
