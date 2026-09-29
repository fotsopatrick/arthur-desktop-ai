#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MCP REFACTOR — recherche-et-remplace structuré, sans charger en RAM.

L'agent ne doit plus lancer sed/awk/grep et parser le résultat.
Ce script accepte un pattern de fichier, une cible (texte ou regex)
et un remplacement, applique les modifications LIGNE PAR LIGNE
(streaming, jamais tout le fichier en mémoire), et rend un JSON
strict des modifications effectuées.

Sortie :
  {
    "files_scanned": 12,
    "files_modified": 2,
    "total_replacements": 7,
    "changes": [
      {
        "file": "nano_moteur_ultra.py",
        "replacements": 3,
        "lines": [42, 108, 201]
      }
    ],
    "dry_run": false
  }

Usage :
  python skills/mcp_refactor.py --glob "*.py" --target "ancien_nom" --replace "nouveau_nom"
  python skills/mcp_refactor.py --glob "*.py" --regex "TODO:?\\s+" --replace "" --dry-run
"""
import glob
import json
import os
import re
import sys
import tempfile


def refactor_file(filepath, target, replacement, use_regex=False,
                  dry_run=False):
    """Applique le remplacement sur UN fichier, ligne par ligne (streaming).

    Rend (nb_remplacements, lignes_touchées) ou (0, []) si rien.
    Le fichier n'est JAMAIS chargé entièrement en mémoire.
    """
    if use_regex:
        try:
            pattern = re.compile(target)
        except re.error as e:
            return 0, [], f"regex invalide : {e}"
    else:
        pattern = None

    replacements = 0
    lines_touched = []

    # Phase 1 : lecture/écriture streaming dans un fichier temporaire
    # On écrit à côté pour ne jamais corrompre l'original en cas de crash.
    dir_name = os.path.dirname(filepath)
    try:
        tmp_fd, tmp_path = tempfile.mkstemp(dir=dir_name or ".",
                                            suffix=".mcp_tmp")
    except OSError as e:
        return 0, [], f"impossible de créer le fichier temporaire : {e}"

    try:
        # (29/09) errors="strict" : un fichier qui n'est pas en UTF-8 est
        # refuse, jamais reecrit avec des caracteres de remplacement.
        with open(filepath, "r", encoding="utf-8") as src, \
             os.fdopen(tmp_fd, "w", encoding="utf-8") as dst:
            for line_no, line in enumerate(src, 1):
                if pattern:
                    new_line, count = pattern.subn(replacement, line)
                else:
                    count = line.count(target)
                    new_line = line.replace(target, replacement) if count else line

                if count > 0:
                    replacements += count
                    lines_touched.append(line_no)

                dst.write(new_line)

        # Phase 2 : remplacement atomique (ou suppression si dry-run)
        if replacements > 0 and not dry_run:
            # Préserve les permissions du fichier original
            try:
                st = os.stat(filepath)
                os.chmod(tmp_path, st.st_mode)
            except OSError:
                pass
            os.replace(tmp_path, filepath)
        else:
            os.unlink(tmp_path)

    except Exception as e:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        return 0, [], f"erreur lecture/écriture : {e}"

    return replacements, lines_touched, None


def refactor(glob_pattern, target, replacement, use_regex=False,
             dry_run=False, base_dir="."):
    """Applique le refactoring sur tous les fichiers matchés.

    Rend le dict de résultat structuré.
    """
    # (29/09) Une cible vide « se trouve » entre chaque caractere : le
    # remplacement etait insere partout et le fichier detruit. On refuse.
    if not target:
        return {"files_scanned": 0, "files_modified": 0,
                "total_replacements": 0, "changes": [], "dry_run": dry_run,
                "success": False, "reason": "empty_target"}

    # Résolution du glob
    if os.path.isabs(glob_pattern):
        files = sorted(glob.glob(glob_pattern, recursive=True))
    else:
        files = sorted(glob.glob(os.path.join(base_dir, "**", glob_pattern),
                                 recursive=True))

    # (29/09) On ne touche QUE ce qui vit sous base_dir : un chemin absolu
    # ou un « ../ » dans le glob ne doit pas sortir du depot.
    racine = os.path.realpath(base_dir)

    def _sous_la_racine(chemin):
        vrai = os.path.realpath(chemin)
        return vrai == racine or vrai.startswith(racine + os.sep)

    # Ne touche que les fichiers texte (skip binaires)
    text_files = []
    for f in files:
        if os.path.isfile(f) and _sous_la_racine(f) and not _is_binary(f):
            text_files.append(f)

    changes = []
    total_replacements = 0

    for filepath in text_files:
        count, lines, error = refactor_file(filepath, target, replacement,
                                            use_regex, dry_run)
        if error:
            changes.append({
                "file": os.path.relpath(filepath, base_dir),
                "error": error,
            })
        elif count > 0:
            total_replacements += count
            changes.append({
                "file": os.path.relpath(filepath, base_dir),
                "replacements": count,
                "lines": lines,
            })

    # SUCCESS/REASON : l'agent ne doit pas deviner en comptant les champs.
    # Rien de remplacé nulle part (cible absente, ou tous les fichiers
    # visés étaient protégés) -> succès faux, motif nommé.
    reussi = total_replacements > 0
    return {
        "files_scanned": len(text_files),
        "files_modified": sum(1 for c in changes if "replacements" in c),
        "total_replacements": total_replacements,
        "changes": changes,
        "dry_run": dry_run,
        "success": reussi,
        "reason": None if reussi else "target_not_found",
    }


def _is_binary(filepath, chunk_size=8192):
    """Détecte grossièrement si un fichier est binaire."""
    try:
        with open(filepath, "rb") as f:
            chunk = f.read(chunk_size)
            return b"\x00" in chunk
    except OSError:
        return True


def main():
    import argparse
    parser = argparse.ArgumentParser(description="MCP Refactor — recherche-et-remplace structuré")
    parser.add_argument("--glob", required=True, help="Pattern glob des fichiers (ex: '*.py')")
    parser.add_argument("--target", required=True, help="Chaîne ou regex à chercher")
    parser.add_argument("--replace", required=True, help="Chaîne de remplacement")
    parser.add_argument("--regex", action="store_true", help="Interpréter --target comme regex")
    parser.add_argument("--dry-run", action="store_true", help="Simuler sans modifier")
    parser.add_argument("--base-dir", default=".", help="Répertoire de base")
    parser.add_argument("--json", action="store_true", help="Sortie JSON pure")
    args = parser.parse_args()

    try:
        result = refactor(args.glob, args.target, args.replace,
                          use_regex=args.regex, dry_run=args.dry_run,
                          base_dir=args.base_dir)
    except Exception as e:
        # RÈGLE ABSOLUE : zéro trace Python rendue à l'agent.
        result = {"success": False, "reason": "erreur inattendue : %s" % e}

    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))

    return 0 if result.get("success") else 1


if __name__ == "__main__":
    sys.exit(main())
