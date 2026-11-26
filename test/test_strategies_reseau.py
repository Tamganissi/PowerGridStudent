
import os
import sys
import unittest

# Permet de lancer ce fichier directement (bouton ▶ de VS Code) :
# les modules du projet se trouvent dans le dossier parent
RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

try:
    import xmlrunner
except ImportError:  # module absent : on garde l'affichage unittest classique
    xmlrunner = None

from Terrain import Terrain, Case
from Reseau import Reseau
from StrategieReseau import StrategieReseauAuto, StrategieReseauManuelle

class TestStrategiesReseau(unittest.TestCase):

    def test_config_auto(self):
        r = Reseau()
        r.set_strategie(StrategieReseauAuto())

        t = Terrain()
        t.charger(os.path.join(RACINE, "terrains", "t1.txt"))
        r.configurer(t)

        self.assertTrue(r.valider_reseau())
        self.assertTrue(r.valider_distribution(t))

        t.charger(os.path.join(RACINE, "terrains", "t2.txt"))
        r.configurer(t)

        self.assertTrue(r.valider_reseau())
        self.assertTrue(r.valider_distribution(t))

    def test_config_auto_ligne_droite(self):
        r = Reseau()
        t = Terrain()
        t.cases = [[Case.ENTREE, Case.VIDE, Case.CLIENT]]
        r.configurer(t)
        self.assertTrue(r.valider_reseau())
        self.assertTrue(r.valider_distribution(t))
        # 3 noeuds + 2 arcs : chemin le plus court possible
        self.assertEqual(r.calculer_cout(t), 3 + 2 * 1.5)

    def test_config_auto_contourne_obstacle(self):
        # Par l'obstacle : 3.5 + 2.5 = 6 ; par le bas : 4 cases x 2.5 = 10.
        # La stratégie doit choisir le chemin le moins cher
        r = Reseau()
        t = Terrain()
        t.cases = [
            [Case.ENTREE, Case.OBSTACLE, Case.CLIENT],
            [Case.VIDE, Case.VIDE, Case.VIDE],
        ]
        r.configurer(t)
        self.assertTrue(r.valider_distribution(t))
        self.assertEqual(r.calculer_cout(t), 7)

    def test_config_auto_moins_chere_que_terrain_complet(self):
        # Le réseau automatique doit coûter moins cher que couvrir tout le terrain
        r = Reseau()
        t = Terrain()
        t.charger(os.path.join(RACINE, "terrains", "t1.txt"))
        r.configurer(t)
        cout_complet = t.largeur * t.hauteur * 1 + (t.largeur * t.hauteur - 1) * 1.5
        self.assertLess(r.calculer_cout(t), cout_complet)

    def test_config_auto_sans_entree(self):
        r = Reseau()
        t = Terrain()
        t.cases = [[Case.VIDE, Case.CLIENT]]
        r.configurer(t)
        self.assertFalse(r.valider_reseau())

    def test_config_manuelle(self):
        t = Terrain()
        t.cases = [
            [Case.ENTREE, Case.VIDE, Case.CLIENT],
            [Case.VIDE, Case.VIDE, Case.VIDE],
        ]
        # Saisies : case hors terrain, case non voisine, puis deux noeuds reliés
        reponses = iter(["9 9", "1 2", "0 1", "o", "0 2", "o", "fin"])
        strat = StrategieReseauManuelle(saisie=lambda _: next(reponses), sortie=lambda *a: None)
        r = Reseau()
        r.set_strategie(strat)
        r.configurer(t)
        self.assertEqual(r.noeuds, {0: (0, 0), 1: (0, 1), 2: (0, 2)})
        self.assertEqual(r.arcs, [(0, 1), (1, 2)])
        self.assertTrue(r.valider_reseau())
        self.assertTrue(r.valider_distribution(t))

    def test_config_manuelle_refus_liaison(self):
        t = Terrain()
        t.cases = [[Case.ENTREE, Case.CLIENT]]
        reponses = iter(["0 1", "n", "fin"])
        strat = StrategieReseauManuelle(saisie=lambda _: next(reponses), sortie=lambda *a: None)
        r = Reseau()
        r.set_strategie(strat)
        r.configurer(t)
        # Le noeud est ajouté mais pas relié : le réseau n'est pas valide
        self.assertEqual(r.arcs, [])
        self.assertFalse(r.valider_reseau())

if __name__ == "__main__":
    if xmlrunner:
        unittest.main(testRunner=xmlrunner.XMLTestRunner(output=os.path.join(RACINE, "test-reports")))
    else:
        unittest.main()
