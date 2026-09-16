# Règles de sécurité d'Arthur

Arthur tourne **sur votre machine**. Il ne contacte aucun serveur pour ses deux
premiers étages, et il ne vous demande aucun compte.

## Ce qu'il fait, et ce qu'il ne fait pas

| | |
|---|---|
| Il **lit** ses règles écrites | il ne les modifie jamais tout seul |
| Il **répond** | il n'envoie rien nulle part |
| Il **avoue** quand il ne sait pas | il n'invente jamais |
| Il **refuse** les questions de santé | ce n'est pas fait pour les médecins |

## Ce qui ne quitte jamais votre machine

Sans greffon installé, **rien** ne sort. Aucun compte, aucun nom, aucune adresse,
aucune question envoyée ailleurs.

C'est vérifié mécaniquement, pas promis : le contrôle `test-app-mobile.js`
refuse la moindre adresse extérieure dans le code, et `test_haichi_hors_ligne.py`
prouve qu'Arthur répond avec le réseau coupé.

## Quand un étage sort quand même

Les étages 3 et 4 (les documents, et le gros modèle) **sortent de la machine**.
Ils sont **optionnels** et clairement identifiés : chaque réponse dit d'où elle
vient (`regles`, `documents`, `alice`, `aveu`). Si vous ne voulez rien qui sorte,
n'utilisez que les étages 1 et 2 — Arthur reste utile et reste muet sur le reste.

## Les greffons — le seul endroit qui peut fuiter

Un greffon **est du code que vous ajoutez**. Il peut, lui, contacter Internet.
Quatre règles, appliquées par le code et non par la confiance :

1. **Un greffon éteint n'est même pas chargé.** Il ne peut rien faire.
2. **Un greffon qui plante ne casse pas Arthur** — sa chute est attrapée,
   signalée, et Arthur continue.
3. **Les règles d'Arthur passent avant tout greffon.** Un greffon ne peut pas
   détourner une réponse qu'Arthur connaît déjà.
4. **N'installez que des greffons dont vous avez lu le code.** Un greffon fait
   quelques lignes : c'est exprès, pour qu'on puisse les lire.

## Ce qu'Arthur n'a pas le droit de faire

- écrire un fichier sans le montrer d'abord ;
- lancer une commande sans demander ;
- envoyer quoi que ce soit sans qu'un greffon allumé le fasse explicitement.

## Signaler un problème

N'écrivez **jamais** un mot de passe ou une clé dans un signalement public.
Pour une faille, écrivez à contact@matourdecontrole.fr.

Version suivie : la dernière du dépôt.
