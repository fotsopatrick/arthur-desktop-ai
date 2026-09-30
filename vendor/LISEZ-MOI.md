# vendor/ — les outils de test, copiés dans le dépôt

Pour que les tests d'Arthur ne dépendent **pas** de ce qui est installé sur la
machine, pytest et ses dépendances (du Python pur) sont copiés ici, avec leurs
licences (`*.dist-info/`) :

| Paquet | Version | Licence |
|---|---|---|
| pytest | 8.3.5 | MIT |
| pluggy | 1.5.0 | MIT |
| iniconfig | 2.0.0 | MIT |
| packaging | 24.2 | Apache-2.0 ou BSD-2-Clause |
| exceptiongroup | 1.2.2 | MIT (seulement pour Python < 3.11) |
| tomli | 2.2.1 | MIT (seulement pour Python < 3.11) |

Seul `qualite/lancer.py` (et `./tester`) s'en sert. On ne modifie jamais ces
fichiers à la main : pour changer de version, on remplace le dossier entier.
