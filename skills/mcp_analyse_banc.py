#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MCP ANALYSE BANC — lance pytest et rend un JSON strict des échecs.

Remplace le cycle « lancer pytest en bash → parser le texte → deviner ».
L'agent reçoit un JSON structuré : zéro parsing, zéro hallucination.

Sortie :
  {
    "total": 25,
    "passed": 23,
    "failed": 2,
    "errors": 0,
    "duration_s": 1.42,
    "failures": [
      {
        "file": "test_foo.py",
        "line": 17,
        "test": "test_addition",
        "expected": "4",
        "received": "5",
        "message": "assert 4 == 5"
      }
    ]
  }

Usage :
  python skills/mcp_analyse_banc.py [--path tests/] [--pattern "test_*.py"]
  python skills/mcp_analyse_banc.py --json  # sortie JSON pure (pour l'agent)
"""
import json
import os
import subprocess
import sys
import tempfile


def run_pytest(test_path=".", pattern="test_*.py", extra_args=None):
    """Lance pytest avec json-report et rend le dict résumé structuré.

    Si pytest-json-report est absent, tombe sur le format XML JUnit
    natif de pytest (toujours disponible) et parse le résultat.
    """
    extra = extra_args or []

    # Essai 1 : pytest-json-report (le plus propre)
    result = _try_json_report(test_path, pattern, extra)
    if result is not None:
        return result

    # Essai 2 : JUnit XML natif (toujours disponible)
    return _try_junit_xml(test_path, pattern, extra)


def parse_pytest_json_report(path):
    """Lit et parse le rapport JSON de pytest. Ne lève JAMAIS d'exception :
    rend le dict parsé, ou un JSON fatal structuré si le fichier est
    illisible ou corrompu (texte brut au lieu de JSON, par exemple)."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        return {"fatal": True, "error": "rapport pytest illisible : %s" % e}


def _try_json_report(test_path, pattern, extra):
    """Essaie pytest --json-report. Rend None si le plugin manque."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        json_path = tmp.name

    cmd = [
        sys.executable, "-m", "pytest",
        test_path,
        "-k", pattern.replace("test_", "").replace(".py", "") if pattern != "test_*.py" else "",
        "--json-report",
        "--json-report-file", json_path,
        "-q", "--tb=short", "--no-header",
    ] + extra

    # Retire -k vide
    cmd = [c for c in cmd if c]

    try:
        subprocess.run(cmd, capture_output=True, timeout=120)
    except FileNotFoundError:
        return None
    except subprocess.TimeoutExpired:
        return {"total": 0, "passed": 0, "failed": 0, "errors": 0,
                "duration_s": 120.0, "failures": [],
                "error_message": "pytest timeout (120s)"}

    if not os.path.exists(json_path):
        return None

    # Fichier VIDE (0 octet) = le plugin pytest-json-report n'a jamais rien
    # écrit dedans (absent, ou pytest a planté avant). C'est le cas normal
    # de "plugin manquant" : on rend None pour laisser le repli JUnit faire
    # le travail, comme avant.
    if os.path.getsize(json_path) == 0:
        try:
            os.unlink(json_path)
        except OSError:
            pass
        return None

    data = parse_pytest_json_report(json_path)
    try:
        os.unlink(json_path)
    except OSError:
        pass

    # Un rapport NON VIDE mais illisible/corrompu est une VRAIE anomalie
    # (le plugin a écrit n'importe quoi) : on le remonte tel quel, on ne le
    # cache pas derrière le repli JUnit. Un moteur muet qui avale l'erreur
    # cache la panne.
    if data.get("fatal"):
        return data

    summary = data.get("summary", {})
    failures = []
    for test in data.get("tests", []):
        if test.get("outcome") in ("failed", "error"):
            call = test.get("call", {}) or {}
            crash = call.get("crash", {}) or {}
            failures.append({
                "file": crash.get("path", test.get("nodeid", "?")),
                "line": crash.get("lineno", 0),
                "test": test.get("nodeid", "?").split("::")[-1],
                "expected": "",
                "received": "",
                "message": (crash.get("message") or
                            call.get("longrepr", ""))[:300],
            })

    return {
        "total": summary.get("total", 0),
        "passed": summary.get("passed", 0),
        "failed": summary.get("failed", 0),
        "errors": summary.get("error", 0),
        "duration_s": round(summary.get("duration", 0), 3),
        "failures": failures,
    }


def _try_junit_xml(test_path, pattern, extra):
    """Fallback : pytest --junitxml + parsing XML."""
    with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as tmp:
        xml_path = tmp.name

    cmd = [
        sys.executable, "-m", "pytest",
        test_path,
        "--junitxml", xml_path,
        "-q", "--tb=short", "--no-header",
    ] + extra

    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=120,
                              text=True)
    except FileNotFoundError:
        return {"total": 0, "passed": 0, "failed": 0, "errors": 0,
                "duration_s": 0, "failures": [],
                "error_message": "pytest introuvable"}
    except subprocess.TimeoutExpired:
        return {"total": 0, "passed": 0, "failed": 0, "errors": 0,
                "duration_s": 120.0, "failures": [],
                "error_message": "pytest timeout (120s)"}

    if not os.path.exists(xml_path):
        return {"total": 0, "passed": 0, "failed": 0, "errors": 0,
                "duration_s": 0, "failures": [],
                "error_message": "junitxml non créé",
                "stderr": (proc.stderr or "")[:500]}

    try:
        import xml.etree.ElementTree as ET
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except Exception as e:
        return {"total": 0, "passed": 0, "failed": 0, "errors": 0,
                "duration_s": 0, "failures": [],
                "error_message": f"XML illisible : {e}"}
    finally:
        try:
            os.unlink(xml_path)
        except OSError:
            pass

    suite = root if root.tag == "testsuite" else root.find("testsuite")
    if suite is None:
        suite = root

    total = int(suite.attrib.get("tests", 0))
    fails = int(suite.attrib.get("failures", 0))
    errs = int(suite.attrib.get("errors", 0))
    duration = float(suite.attrib.get("time", 0))

    failures = []
    for tc in suite.iter("testcase"):
        fail_el = tc.find("failure")
        err_el = tc.find("error")
        el = fail_el if fail_el is not None else err_el
        if el is not None:
            failures.append({
                "file": tc.attrib.get("classname", "?").replace(".", "/") + ".py",
                "line": 0,
                "test": tc.attrib.get("name", "?"),
                "expected": "",
                "received": "",
                "message": (el.attrib.get("message") or
                            (el.text or ""))[:300],
            })

    return {
        "total": total,
        "passed": total - fails - errs,
        "failed": fails,
        "errors": errs,
        "duration_s": round(duration, 3),
        "failures": failures,
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="MCP Analyse Banc — JSON structuré des tests")
    parser.add_argument("--path", default=".", help="Répertoire des tests")
    parser.add_argument("--pattern", default="test_*.py", help="Pattern des fichiers de test")
    parser.add_argument("--json", action="store_true", help="Sortie JSON pure")
    args = parser.parse_args()

    try:
        result = run_pytest(args.path, args.pattern)
    except Exception as e:
        # RÈGLE ABSOLUE : zéro trace Python (stacktrace) rendue à l'agent.
        # Toute défaillance imprévue devient un JSON propre.
        result = {"fatal": True, "error": "mcp_analyse_banc a échoué : %s" % e}

    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))

    if result.get("fatal"):
        return 2
    return 0 if result.get("failed", 0) == 0 and result.get("errors", 0) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
