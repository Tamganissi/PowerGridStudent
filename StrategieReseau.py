
import heapq

from Terrain import Terrain, Case

# Caractère affiché pour chaque type de case (mode manuel)
SYMBOLES = {
    Case.OBSTACLE: "X",
    Case.CLIENT: "C",
    Case.VIDE: "~",
    Case.ENTREE: "E",
}

# Coûts définis dans le cahier des charges (en M€)
COUT_ARC = 1.5
COUT_NOEUD = 1
COUT_NOEUD_OBSTACLE = 2

DIRECTIONS = [(-1, 0), (1, 0), (0, -1), (0, 1)]


# Dimensions calculées à partir des cases : justes même si les cases du
# terrain ont été remplies directement, sans passer par charger()
def hauteur(t: Terrain) -> int:
    return len(t.cases)


def largeur(t: Terrain) -> int:
    return max((len(l) for l in t.cases), default=0)


def cout_case(t: Terrain, l: int, c: int) -> float:
    """Coût pour étendre le réseau sur la case (l, c) : un arc et un noeud."""
    if t[l][c] == Case.OBSTACLE:
        return COUT_ARC + COUT_NOEUD_OBSTACLE
    return COUT_ARC + COUT_NOEUD


def voisins(t: Terrain, l: int, c: int):
    for dl, dc in DIRECTIONS:
        nl, nc = l + dl, c + dc
        if 0 <= nl < hauteur(t) and 0 <= nc < len(t[nl]):
            yield nl, nc


class StrategieReseau:
    def configurer(self, t: Terrain) -> tuple[int, dict[int, tuple[int, int]], list[tuple[int, int]]]:
        return -1, {}, []

class StrategieReseauManuelle(StrategieReseau):
    """Construit le réseau en demandant à l'utilisateur où placer chaque noeud.

    Le réseau démarre avec un noeud sur l'entrée du terrain. À chaque tour,
    l'utilisateur donne les coordonnées d'un nouveau noeud, puis choisit les
    noeuds voisins existants auxquels le relier. 'fin' termine la saisie.
    Les fonctions de saisie et d'affichage sont injectables pour les tests.
    """

    def __init__(self, saisie=input, sortie=print):
        self.saisie = saisie
        self.sortie = sortie

    def _afficher(self, t: Terrain, noeuds: dict[int, tuple[int, int]]) -> None:
        coords = {v: k for k, v in noeuds.items()}
        self.sortie("    " + "".join(str(c % 10) for c in range(largeur(t))))
        for l, ligne in enumerate(t.cases):
            texte = "".join("+" if (l, c) in coords else SYMBOLES[case]
                            for c, case in enumerate(ligne))
            self.sortie("{:>3} {}".format(l, texte))

    def configurer(self, t: Terrain) -> tuple[int, dict[int, tuple[int, int]], list[tuple[int, int]]]:
        entree = t.get_entree()
        if entree == (-1, -1):
            self.sortie("Le terrain n'a pas d'entrée électrique.")
            return -1, {}, []

        noeuds = {0: entree}
        arcs = []
        prochain = 1
        while True:
            self._afficher(t, noeuds)
            try:
                reponse = self.saisie("Nouveau noeud 'ligne colonne' (ou 'fin') : ").strip()
            except EOFError:
                break
            if reponse.lower() in ("fin", "f", "q", ""):
                break
            try:
                l, c = (int(v) for v in reponse.replace(",", " ").split())
            except ValueError:
                self.sortie("Saisie invalide, exemple : 3 5")
                continue
            if not (0 <= l < hauteur(t) and 0 <= c < len(t[l])):
                self.sortie("Case hors du terrain.")
                continue
            if (l, c) in noeuds.values():
                self.sortie("Un noeud existe déjà sur cette case.")
                continue

            voisins_existants = [(k, v) for k, v in noeuds.items() if v in set(voisins(t, l, c))]
            if not voisins_existants:
                self.sortie("Aucun noeud voisin : la case doit toucher le réseau existant.")
                continue

            noeuds[prochain] = (l, c)
            for k, v in voisins_existants:
                try:
                    choix = self.saisie("Relier au noeud {} {} ? [o/n] : ".format(k, v)).strip().lower()
                except EOFError:
                    choix = "n"
                if choix in ("o", "oui", "y", ""):
                    arcs.append((min(k, prochain), max(k, prochain)))
            prochain += 1
        return 0, noeuds, arcs

class StrategieReseauAuto(StrategieReseau):
    """Configuration automatique qui cherche à minimiser le coût du réseau.

    Heuristique de l'arbre de Steiner (Takahashi-Matsuyama) : on part de
    l'entrée, puis on relie à chaque étape le client le moins cher à atteindre
    depuis le réseau déjà construit, par un plus court chemin (Dijkstra) où
    chaque case coûte un arc + un noeud (plus cher sur un obstacle).
    """

    def configurer(self, t: Terrain) -> tuple[int, dict[int, tuple[int, int]], list[tuple[int, int]]]:
        entree = t.get_entree()
        if entree == (-1, -1):
            return -1, {}, []

        ids = {entree: 0}  # coordonnées -> identifiant du noeud
        arcs = []
        restants = set(t.get_clients()) - {entree}

        while restants:
            # Dijkstra multi-sources depuis toutes les cases déjà dans le réseau
            dist = {coord: 0.0 for coord in ids}
            precedent = {}
            tas = [(0.0, coord) for coord in ids]
            heapq.heapify(tas)
            cible = None
            while tas:
                d, (l, c) = heapq.heappop(tas)
                if d > dist[(l, c)]:
                    continue
                if (l, c) in restants:
                    cible = (l, c)
                    break
                for v in voisins(t, l, c):
                    if v in ids:
                        continue
                    nd = d + cout_case(t, *v)
                    if nd < dist.get(v, float("inf")):
                        dist[v] = nd
                        precedent[v] = (l, c)
                        heapq.heappush(tas, (nd, v))
            if cible is None:
                break  # client inatteignable (ne peut pas arriver sur une grille)

            # Ajout du chemin trouvé, en remontant de la cible vers le réseau
            chemin = [cible]
            while chemin[-1] not in ids:
                chemin.append(precedent[chemin[-1]])
            for case in reversed(chemin[:-1]):
                ids[case] = len(ids)
            for a, b in zip(chemin, chemin[1:]):
                n1, n2 = ids[a], ids[b]
                arcs.append((min(n1, n2), max(n1, n2)))
            # Un chemin peut passer par d'autres clients : ils sont alors servis
            restants -= set(ids)

        noeuds = {n: coord for coord, n in ids.items()}
        return 0, noeuds, arcs
