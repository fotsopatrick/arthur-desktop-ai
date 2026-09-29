#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test unitaire TDD : l'outil de gouvernance du cockpit pour Arthur.

Arthur doit être capable de lire l'état réel de gouvernance du Cockpit d'Agents
(agents actifs, décisions en attente, garde-fous mécaniques) sans inventer.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import haichi_outils as H

class TestCockpitGouvernance(unittest.TestCase):

    def test_outil_cockpit_gouvernance_repond_avec_donnees_reelles(self):
        txt = H.outil_cockpit_gouvernance()
        self.assertIsInstance(txt, str)
        self.assertGreater(len(txt), 30)
        # Vérifie qu'il mentionne le cockpit / gouvernance
        txt_min = txt.lower()
        self.assertTrue(
            "cockpit" in txt_min or "gouvernance" in txt_min or "injoignable" in txt_min,
            f"Réponse inattendue: {txt}"
        )

    def test_declenchement_par_mots_cles(self):
        mots_cles = [
            "etat des agents",
            "cockpit agents",
            "qui surveille",
            "gouvernance des agents",
            "refus du garde",
        ]
        for m in mots_cles:
            fn = H.chercher_un_outil(m)
            self.assertIsNotNone(fn, f"Aucun outil trouvé pour: '{m}'")
            self.assertEqual(fn, H.outil_cockpit_gouvernance)

if __name__ == "__main__":
    unittest.main()
