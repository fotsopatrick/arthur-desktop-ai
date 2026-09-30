# qualite/ — les tests d'Arthur, leur couverture, un tableau de bord

```bash
./tester              # tous les tests, la couverture, puis le tableau de bord
./tester --vite       # seulement tests/ (pytest), quelques secondes
./tester --serie calcul   # une seule série
python3 qualite/lancer.py --page   # refaire la page sans relancer les tests
```

Le tableau de bord : `qualite/rapport/index.html` — une page qui s'ouvre sans
internet. Quatre vues :

| Vue | Ce qu'elle montre |
|---|---|
| **Carte** | chaque fichier du code d'Arthur en tuile : ✓ couvert, ! incomplet, ✗ sans test |
| **Modules** | le tableau triable : couverture, lignes, fonctions jamais appelées, séries qui le touchent |
| **Tests** | chaque série : ✓ passe, ✗ échoue, ~ sautée (et ce qui manque), avec ses épreuves ; et **⚑ Bugs connus** : les défauts prouvés par un test « échec attendu » (`xfail(strict=True)`), avec leur `fichier:ligne` |
| **Fichier** | le code, ligne par ligne : vert exécuté, rouge jamais exécuté ; ses fonctions ; ses tests |

## Les bugs connus

Un test qui prouve un vrai défaut est marqué `@pytest.mark.xfail(strict=True,
reason="bug: fichier:ligne — …")`. Il reste « échec attendu » tant que le
défaut existe ; le jour où il est corrigé, le test **passe**, et `strict` le
fait alors échouer : on retire la marque, et le bug sort de la liste.

## Rien ne dépend de la machine

- **pytest** vient de `vendor/` (copié dans le dépôt, avec ses licences) ; les
  greffons pytest installés sur la machine ne sont **pas** chargés.
- **La couverture** est mesurée par `traceur.py`, écrit avec la seule
  bibliothèque standard (`sys.settrace`). Elle suit aussi les sous-processus
  lancés par les tests (via `amorce/sitecustomize.py`).
- Chaque série tourne dans son propre processus avec un **HOME jetable** :
  aucun test ne touche aux vrais `~/.secrets`, `~/.config` ou `~/.claude`.

## Les règles de la mesure

- **Lignes exécutables** : lues dans le code compilé, pas devinées dans le texte.
- **Exclu, et affiché** : le bloc `if __name__ == "__main__":` et toute
  instruction marquée `# pragma: no cover`.
- **Verdicts** : couvert ≥ 80 % · incomplet entre 1 ligne et 80 % · sans test = 0.
- **Sautée** : une série qui échoue parce qu'il manque une chose *extérieure*
  (le cockpit 8790, la tour en ssh, GTK, docker, un écran…). La chose manquante
  est nommée. Une série qui échoue pour une autre raison reste **rouge**.

| Fichier | Rôle |
|---|---|
| `lancer.py` | trouve les séries, les lance, lit les résultats, écrit le rapport |
| `traceur.py` | note les lignes d'Arthur qui tournent |
| `analyse.py` | lignes exécutables, fonctions, exclusions, verdicts |
| `tableau.py` | la page HTML (autonome) |
| `amorce/sitecustomize.py` | démarre le traceur dans chaque processus Python |
