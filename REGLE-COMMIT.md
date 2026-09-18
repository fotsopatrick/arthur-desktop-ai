# Regle : toute modification doit etre detailee et expliquee

Ne le 18/09/2026, a la demande de Patrick : « toute modification doit etre
détailée et expliquée ».

Un *garde-fou mécanique* refuse les commits trop courts
(`githooks/commit-msg`, branche par `core.hooksPath = githooks`).

Chaque commit doit dire :
1. **CE QUI** a change (les gestes, les fichiers) ;
2. **POURQUOI** (la cause, le besoin, la lecon) ;
3. **QUELS** fichiers sont touches.

Un message d'une ligne est **refuse**.
