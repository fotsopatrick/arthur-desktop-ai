# Les garde-fous d'Arthur

Un garde-fou est un petit programme qui **refuse**. Pas un conseil écrit,
pas un paragraphe : un mur qui dit non et explique pourquoi.

**Pourquoi des murs et pas des textes.** Mesuré le 16/09/2026 : 566 lignes
de règles écrites et 173 souvenirs n'ont arrêté **zéro** faute ce jour-là.
Les gardes mécaniques en ont arrêté **sept**. Une leçon écrite ne protège
de rien tant qu'elle reste un texte.

| Le garde | Ce qu'il refuse | Né de |
|---|---|---|
| `garde-video-montree.py` | finir en donnant le **nom** d'une vidéo au lieu de la montrer dans une page | 17/09/2026 — une vidéo de 158 s que Patrick n'a jamais vue |
| `garde-plan-action.py` | signaler un problème sans analyse, sans suite, sans choix expliqués | un problème sans plan ne sert à rien |
| `garde-donner-des-boutons.py` | fabriquer une page sans donner ni son adresse ni son bouton | 16/09/2026 — « le lien stp et pourquoi tu me l'as pas donné ??? » |
| `garde-ne-pas-reposer.py` | reposer une question déjà tranchée | « pourquoi tu me reposes la question mille fois » |
| `garde-jamais-bannir-patrick.py` | bannir l'adresse de Patrick lui-même | « vérifie mon IP actuelle avant tout bannissement » |

## Comment ils marchent

Chacun lit ce qu'on lui donne, puis **sort le nombre 2 pour bloquer**, ou
0 pour laisser passer. Ce qu'il écrit sur la sortie d'erreur revient à
l'agent, qui doit alors se corriger.

Deux règles qui les gardent honnêtes :

1. **Un garde qui n'a jamais refusé ne garde rien.** Chaque garde a son
   épreuve, et l'épreuve le **casse exprès** pour le voir devenir rouge.
2. **Un garde trop large n'empêche aucun vol, il empêche de travailler.**
   Quand un garde refuse un geste manifestement légitime, on l'**affine** —
   on ne le désarme jamais. Exemple vécu : se servir d'une clef n'est pas
   lire une clef.

## Les épreuves

    bash outils/test-video-montree.sh          5 contrôles
    bash outils/test-boite-aux-reponses.sh     5 contrôles
