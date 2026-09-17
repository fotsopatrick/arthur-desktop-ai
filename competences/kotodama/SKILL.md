---
name: kotodama
description: "Relire une conversation et n'en sortir QUE les questions et demandes d'Orel, groupées par thème, avec leur état — PUIS lui envoyer le tout par courrier. À invoquer sur « kotodama », « résume mes demandes », « qu'est-ce que je t'ai demandé », « sors ce que je t'ai posé »."
---

# Kotodama (言霊) — l'esprit des mots

Garder les mots qui portent une intention, jeter le reste.

## Ce que tu fais

1. **Ne relis QUE les tours d'Orel.** Pas les tiens, pas les sorties d'outils.
2. Garde **uniquement** ses questions et ses demandes. Jette l'humeur, le
   contexte, les « ok », « continue », « c'est top », les corrections de forme.
3. Réécris chaque intention en **une ligne**, à l'infinitif ou en question
   directe. Ses mots à lui autant que possible.
4. **Dédoublonne** : une même demande reformulée trois fois = une ligne.
5. **Groupe par thème** (le projet, la méthode, un dossier…). Pas par ordre
   chronologique.
6. Marque l'état de chacune :
   - ✅ faite et vérifiée
   - ⏳ en cours, ou faite mais non vérifiée
   - ⛔ bloquée, ou en attente d'une décision de sa part
7. Termine par **ce qui reste ouvert**, y compris ce que tu as soulevé toi-même
   et qu'il n'a pas tranché. Une ligne chacun.
8. **ENVOIE-LE PAR COURRIER.** Voir la section suivante — ce n'est pas
   optionnel.

## 8 bis. LE COURRIER AUTOMATIQUE (demandé le 10/09/2026)

Ses mots : « quand je te dis kotodama, envoie-moi automatiquement le rapport
par mail ou le kotodama, **en plus** de répondre ici ».

Donc, à chaque kotodama, DEUX choses, jamais une seule :

1. la liste s'affiche **dans la réponse** — il ne va pas la chercher ailleurs ;
2. la même liste part **par courrier** à `fotsoorel95@gmail.com`, avec le
   rapport de session en pièce jointe s'il en existe un
   (`~/rapports-sessions/RAPPORT-<date>-*.md`, le plus récent).

Objet du courrier : `Kotodama + rapport — <jour> <mois> <année>`.
Corps : la liste, en texte simple, sans mise en forme compliquée — un
courrier se lit sur un téléphone.

**Si l'outil de courrier n'existe pas là où tu tournes** (opencode, la tour),
tu le dis en UNE ligne — « pas d'outil de courrier ici, la liste est écrite
dans `~/livrables/kotodama-<date>.md` » — et tu écris le fichier quand même.
Ne jamais faire semblant d'avoir envoyé.

## Ce que tu ne fais pas

- Pas de pavé, pas de récit, pas de justification. Une ligne = une intention.
- Ne réponds pas aux demandes dans le résumé : tu les listes, c'est tout.
- N'invente pas d'intention qu'il n'a pas exprimée.
- Ne marque ✅ que si le contrôle correspondant est réellement passé. Une chose
  faite mais non vérifiée est ⏳.
- **Ne l'envoie pas chercher un fichier.** La liste se LIT dans la réponse ;
  le fichier et le courrier servent à la garder, pas à l'aller chercher.
- N'envoie jamais un kotodama vide. S'il n'y a aucune demande dans la
  conversation, dis-le en une ligne et n'envoie pas de courrier.

## Ce qui rend un kotodama utile plutôt que joli

- **Un état sans preuve n'est pas un état.** Devant chaque ✅, le chiffre du
  contrôle : « 12 verts / 0 rouge », pas « c'est bon ».
- **Un ⛔ dit toujours QUI débloque.** « bloqué » tout seul ne sert à rien :
  « bloqué — il faut son code à six chiffres » sert.
- **Les fautes de la session comptent comme des demandes.** Ce qu'il a dû
  corriger chez toi mérite sa ligne, sinon tu le lui feras redire.

## Pourquoi

Orel déteste répéter et re-répondre à du déjà réglé. Kotodama est le filtre qui
ressort la liste propre de ce qu'il a voulu, pour ne rien rater et ne plus le
lui faire redire. Le courrier existe pour la même raison : il ne relit pas un
terminal fermé, mais il relit sa boîte.

## 8 ter. LA PAGE WEB (demandé le 17/09/2026)

Ses mots : « quand je fais kotodama, que le résultat s'affiche dans une page web ».

Donc, à CHAQUE kotodama, en plus de la réponse et du mail : **une page web,
montrée à l'écran**. Le programme est le même pour Claude Code, opencode et
Antigravity.

1. Écris le texte du kotodama dans un fichier (ex. `/tmp/kotodama.txt`).
2. Fabrique la page :
   `python3 ~/outils/kotodama-page.py /tmp/kotodama.txt`
   → il crée `~/livrables/kotodama-<date>.html` et affiche son chemin.
   (Format : `== Titre ==` ouvre une section ; une ligne `- ...` est une
   demande ; le signe ✅/⏳/⛔ dedans donne sa couleur.)
3. Ouvre-la à SON écran (8891 sert `~/livrables`) :
   `setsid sudo -u orel -H env DISPLAY=:0 XDG_RUNTIME_DIR=/run/user/1000 xdg-open http://127.0.0.1:8891/kotodama-<date>.html`
   puis marque le geste : `python3 ~/.claude/portes/marque-stream.py`.

Contrôle de l'outil : `python3 ~/outils/test-kotodama-page.py` (doit être 7 vert).


## 8 ter. LA PAGE WEB (demandé le 17/09/2026)

Ses mots : « quand je fais kotodama, que le résultat s'affiche dans une page web ».

Donc, à CHAQUE kotodama, en plus de la réponse et du mail : **une page web,
montrée à l'écran**. Le programme est le même pour Claude Code, opencode et
Antigravity.

1. Écris le texte du kotodama dans un fichier (ex. `/tmp/kotodama.txt`).
2. Fabrique la page :
   `python3 ~/outils/kotodama-page.py /tmp/kotodama.txt`
   → il crée `~/livrables/kotodama-<date>.html` et affiche son chemin.
   (Format : `== Titre ==` ouvre une section ; une ligne `- ...` est une
   demande ; le signe ✅/⏳/⛔ dedans donne sa couleur.)
3. Ouvre-la à SON écran (8891 sert `~/livrables`) :
   `setsid sudo -u orel -H env DISPLAY=:0 XDG_RUNTIME_DIR=/run/user/1000 xdg-open http://127.0.0.1:8891/kotodama-<date>.html`
   puis marque le geste : `python3 ~/.claude/portes/marque-stream.py`.

Contrôle de l'outil : `python3 ~/outils/test-kotodama-page.py` (doit être 7 vert).

