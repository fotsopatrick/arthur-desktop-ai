# HACHI / Arthur (Nom de code : `nominomi`) — le compagnon posé sur le bureau

**Nom de code :** `nominomi`

Un chien assis sur un ballon de football américain, posé par-dessus toutes les
fenêtres. On lui parle dans sa barre, il répond dans sa bulle. Il tourne sur la
machine : rien ne part dehors.

## Ce qu'il sait faire, et dans quel ordre

| Étage | Ce qu'il fait | Temps mesuré |
|---|---|---|
| **1 — ses outils** | il va VOIR : l'heure, les modules allumés, la veille du matin, le réseau | 1 à 10 ms |
| **2 — ses règles** | 230 sujets appris par cœur sur la maison | 0,14 ms |
| **3 — les documents** | ce qu'Alice a avalé : 100 documents, 1 197 morceaux de texte | ~3 s |
| **4 — le gros cerveau** | Qwen, sur l'autre machine, quand personne d'autre ne sait | ~2 s |
| **l'aveu** | quand aucun des quatre ne sait, il le DIT | 1 ms |

Il ne parle **jamais** de santé : il n'est pas fait pour les médecins.

## Le lancer

    python3 ~/haichi/haichi_avatar.py

Et pour lui poser une question tout de suite :

    python3 ~/haichi/haichi_avatar.py "qui est Victor"

## Les contrôles

Chacun se lance tout seul. Un contrôle vert est une preuve.

| Fichier | Ce qu'il vérifie |
|---|---|
| `test_haichi_repond_juste.py` | il répond juste, et jamais de santé |
| `test_haichi_outils.py` | ses outils vont vraiment voir |
| `test_haichi_trois_etages.py` | qui répond quoi |
| `test_haichi_hors_ligne.py` | il tient sans réseau |
| `test_haichi_avatar.sh` | sa fenêtre est sans bordure, au-dessus, transparente |

## Ce qui a été payé cher

- **Il répondait le cycle du virus du sida** à la question « qu'est-ce que la
  tour ». Le mot *tour* est écrit dans dé-**tour**-nement.
- **Il inventait** au lieu d'avouer. Maintenant il dit « je ne sais pas ».
- **Qwen invente aussi** : question sur une faille récente de Debian, il a
  répondu une référence de 2023, fabriquée. Avec les documents, il répond juste.
- **La bibliothèque de dessin n'est pas installée** sur cette machine. Le dessin
  de Hachi échouait en silence. Son image est donc fabriquée à part.
- **Chrome ne sait pas rendre un fond transparent** ici : il le peint en blanc.
  D'où ce vrai programme de bureau, sans navigateur.
- **Il s'écrit HACHI** sur la vitrine, sans le i du milieu.

## Où vivent ses fichiers

Ils sont ici. Le cockpit (dossier `~/cockpit-generique`) ne garde que des
flèches qui pointent vers eux : il y a une seule vérité, pas deux copies.

## MERCI — ce qu'Arthur doit à d'autres

Arthur ne part pas de rien. Voilà ce qu'il emprunte, et à qui.

### NVIDIA

**Le cerveau du dernier étage.** Quand ses quatre premiers étages n'ont rien
de vrai à dire, Arthur appelle **NVIDIA Nemotron-3-Ultra**. Mesuré sur trois
questions dont un piège : **3 justes sur 3**, en 891 millisecondes. Le modèle
rapide, lui, se trompait sur une. Arthur a gardé le plus lent qui ne devine pas.

**Deux outils, sous licence Apache 2.0** — une licence qui laisse tout faire,
y compris vendre :

| L'outil | À quoi il sert |
|---|---|
| [garak](https://github.com/NVIDIA/garak) | il **attaque** un modèle pour le faire craquer : hallucination, fuite de données, injection, jailbreak. C'est le juge extérieur d'Arthur |
| [NeMo Agent Toolkit](https://github.com/NVIDIA/NeMo-Agent-Toolkit) | il mesure des agents : profilage, traçage, évaluation |

**Et une façon de penser.** NVIDIA bâtit en quatre temps : construire,
observer, **évaluer**, optimiser. Le troisième nous manquait. Il est repris ici.

### Nebius

**Token Factory** fait tourner Nemotron. Leur maison a aussi appris quelque
chose à Arthur, sans le vouloir : leurs modèles à raisonnement peuvent rendre
une réponse **vide**, en silence, quand ils passent tout leur temps à
réfléchir. Arthur le dit maintenant à voix haute au lieu de planter.

### Google

Les voix des vidéos d'Arthur sont fabriquées avec **Google Cloud
Text-to-Speech**.

---

*Les licences ont été relevées avant toute reprise. Rien ici n'est repris sans
que sa licence l'autorise.*
