---
name: redaction-histoire
description: Écrire et monter l'histoire d'un jeu (Hunteria et les suivants) — capturer une scène dictée par Patrick, la mettre en données, la jouer comme une cinématique (gros plans puis retour au jeu), avec les agents qui jouent les personnages et le nom choisi par le joueur. À invoquer quand Patrick raconte une scène, un dialogue, une cinématique, ou dit « écris l'histoire », « la scène du bateau », « rédaction d'histoire ».
---

# Rédaction d'histoire — capturer, mettre en données, jouer

Née le 16/09/2026, pendant l'écriture de **Hunteria** (le jeu de Patrick
inspiré de Hunter × Hunter, SANS les vrais noms — voir
[[hunteria-univers-histoire]]).

## La règle en une phrase
**On capture les mots de Patrick À L'IDENTIQUE, on les met en données (un
fichier JSON), et un moteur les joue.** Jamais réécrire ses répliques ;
jamais inventer une réplique qu'il n'a pas dite.

## Les mots de métier, décodés
- **Cinématique** (anglais « cutscene ») : un petit film DANS le jeu — le
  jeu s'arrête, une scène se joue (dialogue, caméra qui bouge), puis **le jeu
  reprend** et le joueur récupère les commandes.
- **Plan rapproché / gros plan** : la caméra s'approche du visage d'un
  personnage pendant qu'il parle.
- **Cinématique temps réel** : le petit film est fait avec les VRAIS décors
  et personnages du jeu (pas une vidéo à part). C'est ce qu'on fait ici.

## Les 3 morceaux (composants réutilisables)
1. **La scène en données** — un fichier `scene-*.json` :
   - `declencheur` : l'événement qui lance la scène (ex. `"monter_bateau"`) ;
   - `casting` : quel **agent** joue quel personnage ;
   - `lignes` : la suite des répliques `{perso, texte}`, DANS L'ORDRE ;
   - le mot `{nom}` dans une réplique = le **nom que le joueur a choisi** au
     début (les agents l'appellent par ce nom).
   - Modèle réel : `~/livrables/hunteria/scene-bateau.json`.
2. **Le moteur** — `~/livrables/hunteria/cutscene.py` : `Scene(chemin)`,
   `assigner(perso, agent)`, `jouer(evenement, nom_joueur)` → rend les
   répliques dans l'ordre, `{nom}` déjà remplacé. Il ne dessine rien.
3. **La caméra de cinématique** (côté 3D, à brancher) : pendant la scène, la
   caméra passe sur des **plans** définis (un gros plan par personnage qui
   parle), puis rend la main à la caméra du jeu. Les plans se rangent aussi
   en données (position + cible + durée), pour rester réutilisables.

## Comment monter une scène (les étapes)
1. **Écouter et capturer** : coller les répliques de Patrick mot pour mot
   dans un `scene-*.json`. Garder ses noms (Kurata, Dame Lioness, Fantômeia,
   nénia…).
2. **Distribuer** : dire quel agent joue quel personnage (`casting`).
3. **Tester la logique** : un test qui vérifie l'ordre des répliques, le
   casting, le remplacement de `{nom}`, et que le mauvais événement ne lance
   rien. Modèle : `~/livrables/hunteria/test_cutscene.py` (5 contrôles).
4. **Brancher la 3D plus tard** : la scène se joue avec les VRAIS décors.

## Le style — ATTENTION
Pour la 3D, on réutilise les **vrais modèles** (le bureau 3D des agents, le
donjon, les avatars Quaternius/VRoid). **JAMAIS** des formes faites à la main
(boîtes, capsules) — Patrick déteste : voir [[style-3d-hunteria-refuse]] et
[[gout-assets-3d-patrick]].

## Le théâtre — pour que les agents jouent juste
Un agent qui joue un rôle, c'est un acteur. On lui donne, avec sa réplique :
- **La didascalie** (mot de théâtre : l'indication de jeu écrite à côté du
  texte) — le **ton** (« sec », « grave ») et le **geste** (« croise les bras »).
  Dans la scène, ce sont les champs `ton` et `geste` de chaque ligne.
- **Le sous-texte** : ce que le personnage pense vraiment sous ses mots
  (Kurata retient sa colère). Ça guide le ton.
- **Le tempo et le silence** : un blanc avant une réplique dit autant que les
  mots. Le mode `touche` (on appuie pour passer) laisse ce temps au joueur.
- Structure : une **scène** (un lieu, un moment), des **entrées/sorties**,
  des **répliques** (courtes) et **tirades** (longues).

## Les gestes en parlant (pour du réalisme)
Chaque émotion a son geste — on l'écrit dans `geste`, la 3D l'animera :
- colère retenue → poings serrés, mâchoire ; mépris → se détourne, menton haut ;
- fierté → buste droit ; secret/confidence → se penche, baisse la voix ;
- doute → détourne le regard ; détermination → regard droit, s'avance.
Règle : **un geste par idée**, jamais gesticuler sans arrêt.

## Ce que font Unity et Unreal (et notre version rapide)
- **Unity** : cinématiques avec **Timeline** (une frise où l'on pose des
  clips : dialogue, animation, caméra) + **Cinemachine** (des **caméras
  virtuelles** qui cadrent les plans et enchaînent les gros plans tout seuls).
- **Unreal Engine** : **Sequencer** (même idée que Timeline, image par image)
  + **MetaHuman** (personnages photo-réalistes) + **Control Rig** (poses et
  gestes). C'est le plus réaliste, mais lourd.
- **A-t-on accès à leurs techniques ?** Pas à leurs logiciels (nous, c'est le
  navigateur, avec Three.js). Mais leurs **idées sont libres** à reprendre :
  une frise de plans, des caméras virtuelles, des gestes par émotion.
- **Notre version, rapide et à notre logique** : la scène est déjà en
  **données** (déclencheur, répliques, casting, ton, geste, `plan`). On ajoute
  une petite **frise de plans** (position caméra + cible + durée, un gros plan
  par réplique) que Three.js joue en temps réel avec nos VRAIS modèles. Léger,
  dans le navigateur, sans gros moteur ni compilation.

## Ce qu'on ne fait jamais
- Réécrire ou « améliorer » les répliques de Patrick.
- Inventer une suite d'histoire qu'il n'a pas donnée.
- Annoncer une scène « prête » sans le test vert (voir la garde des tests).
