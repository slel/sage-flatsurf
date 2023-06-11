r"""
Polygons embedded in the plane `\mathbb{R}^2`.

The emphasis is mostly on convex polygons but there is some limited support for
non-convex polygons.

EXAMPLES::

    sage: from flatsurf.geometry.polygon import Polygon

    sage: K.<sqrt2> = NumberField(x^2 - 2, embedding=AA(2).sqrt())
    sage: p = Polygon(edges=[(1,0), (-sqrt2,1+sqrt2), (sqrt2-1,-1-sqrt2)])
    sage: p
    Polygon(vertices=[(0, 0), (1, 0), (-sqrt2 + 1, sqrt2 + 1)])

    sage: M = MatrixSpace(K,2)
    sage: m = M([[1,1+sqrt2],[0,1]])
    sage: m * p
    Polygon(vertices=[(0, 0), (1, 0), (sqrt2 + 4, sqrt2 + 1)])
"""
# ****************************************************************************
#  This file is part of sage-flatsurf.
#
#        Copyright (C) 2016-2020 Vincent Delecroix
#                      2020-2023 Julian Rüth
#
#  sage-flatsurf is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 2 of the License, or
#  (at your option) any later version.
#
#  sage-flatsurf is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with sage-flatsurf. If not, see <https://www.gnu.org/licenses/>.
# ****************************************************************************

from sage.all import (
    cached_method,
    cached_function,
    infinity,
    Parent,
    ZZ,
    QQ,
    matrix,
    vector,
    free_module_element,
)

from sage.structure.element import Element
from sage.structure.sequence import Sequence

from flatsurf.geometry.euclidean import angle
from flatsurf.geometry.subfield import (
    number_field_elements_from_algebraics,
)

from flatsurf.geometry.categories import RealProjectivePolygons
from flatsurf.geometry.categories.real_projective_polygons_with_angles import RealProjectivePolygonsWithAngles


class EuclideanPolygonPoint(Element):
    pass


class PolygonPosition:
    r"""
    Describes the position of a point within or outside of a polygon.
    """
    # Position Types:
    OUTSIDE = 0
    INTERIOR = 1
    EDGE_INTERIOR = 2
    VERTEX = 3

    def __init__(self, position_type, edge=None, vertex=None):
        self._position_type = position_type
        if self.is_vertex():
            if vertex is None:
                raise ValueError(
                    "Constructed vertex position with no specified vertex."
                )
            self._vertex = vertex
        if self.is_in_edge_interior():
            if edge is None:
                raise ValueError("Constructed edge position with no specified edge.")
            self._edge = edge

    def __repr__(self):
        if self.is_outside():
            return "point positioned outside polygon"
        if self.is_in_interior():
            return "point positioned in interior of polygon"
        if self.is_in_edge_interior():
            return (
                "point positioned on interior of edge "
                + str(self._edge)
                + " of polygon"
            )
        return "point positioned on vertex " + str(self._vertex) + " of polygon"

    def is_outside(self):
        return self._position_type == PolygonPosition.OUTSIDE

    def is_inside(self):
        r"""
        Return true if the position is not outside the closure of the polygon
        """
        return bool(self._position_type)

    def is_in_interior(self):
        return self._position_type == PolygonPosition.INTERIOR

    def is_in_boundary(self):
        r"""
        Return true if the position is in the boundary of the polygon
        (either the interior of an edge or a vertex).
        """
        return (
            self._position_type == PolygonPosition.EDGE_INTERIOR
            or self._position_type == PolygonPosition.VERTEX
        )

    def is_in_edge_interior(self):
        return self._position_type == PolygonPosition.EDGE_INTERIOR

    def is_vertex(self):
        return self._position_type == PolygonPosition.VERTEX

    def get_position_type(self):
        return self._position_type

    def get_edge(self):
        if not self.is_in_edge_interior():
            raise ValueError("Asked for edge when not in edge interior.")
        return self._edge

    def get_vertex(self):
        if not self.is_vertex():
            raise ValueError("Asked for vertex when not a vertex.")
        return self._vertex


# TODO: Almost all of this should be defined in the category so it can be overridden by subcategories.
class EuclideanPolygon(Parent):
    r"""
    A (possibly non-convex) simple polygon in the plane `\mathbb{R}^2`.
    """
    Element = EuclideanPolygonPoint

    def __init__(self, base_ring, vertices, check=True, category=None):
        V = base_ring**2
        self._v = tuple(map(V, vertices))
        for vv in self._v:
            vv.set_immutable()
        if category is None:
            category = RealProjectivePolygons(base_ring)

        category &= RealProjectivePolygons(base_ring)
        if self.is_convex():
            category = category.Convex()

        # TODO: Refine category to the correct WithAngles subcategory.

        super().__init__(base_ring, category=category)

        if check:
            self._check()

    def parent(self):
        # TODO: Deprecate (warn that this is going to change eventually.)
        return self.category()

    def _check(self):
        r"""
        TESTS::

            sage: from flatsurf import Polygons
            sage: P = Polygons(QQ)
            sage: P(vertices=[(0,0),(2,0),(1,1),(1,-1)])
            Traceback (most recent call last):
            ...
            ValueError: edge 0 (= ((0, 0), (2, 0))) and edge 2 (= ((1, 1), (1, -1))) intersect
        """
        super()._check()

        n = len(self._v)
        for i in range(n - 1):
            ei = (self._v[i], self._v[i + 1])
            for j in range(i + 1, n):
                ej = (self._v[j], self._v[(j + 1) % n])

                from flatsurf.geometry.euclidean import is_segment_intersecting
                res = is_segment_intersecting(ei, ej)
                if j == i + 1 or (i == 0 and j == n - 1):
                    if res > 1:
                        raise ValueError(
                            "edge %d (= %s) and edge %d (= %s) backtrack"
                            % (i, ei, j, ej)
                        )
                elif res > 0:
                    raise ValueError(
                        "edge %d (= %s) and edge %d (= %s) intersect" % (i, ei, j, ej)
                    )

    def _mul_(self, g, switch_sides=None):
        r"""
        Apply the 2x2 matrix `g` to the polygon `x`.

        The matrix must have non-zero determinant. If the determinant is
        negative, then the vertices and edges are relabeled according to the
        involutions `v \mapsto (n-v)%n` and  `e \mapsto n-1-e` respectively.

        EXAMPLES::

            sage: from flatsurf import Polygon
            sage: p = Polygon(vertices = [(1,0),(0,1),(-1,-1)])
            sage: p
            Polygon(vertices=[(1, 0), (0, 1), (-1, -1)])
            sage: r = matrix(ZZ,[[0,1], [1,0]])
            sage: r * p
            Polygon(vertices=[(0, 1), (-1, -1), (1, 0)])
        """
        x = self

        if g in self.base_ring():
            from sage.all import MatrixSpace
            g = MatrixSpace(self.base_ring(), 2)(g)

        det = g.det()
        if det > 0:
            return Polygon(vertices=[g * v for v in x.vertices()], check=False, category=x.category())
        if det < 0:
            # Note that in this case we reverse the order
            vertices = [g * x.vertex(0)]
            for i in range(x.num_edges() - 1, 0, -1):
                vertices.append(g * x.vertex(i))
            return Polygon(vertices=vertices, check=False, category=x.category())
        raise ValueError("Can not act on a polygon with matrix with zero determinant")

    @cached_method
    def __hash__(self):
        return hash(self._v)

    def __eq__(self, other):
        r"""
        TESTS::

            sage: from flatsurf import polygons, Polygon
            sage: p1 = polygons.square()
            sage: p2 = Polygon(edges=[(1,0),(0,1),(-1,0),(0,-1)], base_ring=QQbar)
            sage: p1 == p2
            True

            sage: p3 = Polygon(edges=[(2,0),(-1,1),(-1,-1)])
            sage: p1 == p3
            False
        """
        if not isinstance(other, EuclideanPolygon):
            return False

        return self._v == other._v

    def __ne__(self, other):
        r"""
        TESTS::

            sage: from flatsurf import Polygon, polygons
            sage: p1 = polygons.square()
            sage: p2 = Polygon(edges=[(1,0),(0,1),(-1,0),(0,-1)], base_ring=QQbar)
            sage: p1 != p2
            False

            sage: p3 = Polygon(edges=[(2,0),(-1,1),(-1,-1)])
            sage: p1 != p3
            True
        """
        return not (self == other)

    def cmp(self, other):
        r"""
        Implement a total order on polygons
        """
        if not isinstance(other, EuclideanPolygon):
            raise TypeError("__cmp__ only implemented for ConvexPolygons")
        if not self.parent().base_ring() == other.parent().base_ring():
            raise ValueError(
                "__cmp__ only implemented for ConvexPolygons defined over the same base_ring"
            )
        sign = self.num_edges() - other.num_edges()
        if sign > 0:
            return 1
        if sign < 0:
            return -1
        sign = self.area() - other.area()
        if sign > self.base_ring().zero():
            return 1
        if sign < self.base_ring().zero():
            return -1
        for v in range(1, self.num_edges()):
            p = self.vertex(v)
            q = other.vertex(v)
            sign = p[0] - q[0]
            if sign > self.base_ring().zero():
                return 1
            if sign < self.base_ring().zero():
                return -1
            sign = p[1] - q[1]
            if sign > self.base_ring().zero():
                return 1
            if sign < self.base_ring().zero():
                return -1
        return 0

    def triangulation(self):
        r"""
        Return a list of pairs of indices of vertices that together with the boundary
        form a triangulation.

        EXAMPLES:

        We triangulate a non-convex polygon::

            sage: from flatsurf import Polygon
            sage: P = Polygon(vertices=[(0,0), (1,0), (1,1), (0,1), (0,2), (-1,2), (-1,1), (-2,1),
            ....:                    (-2,0), (-1,0), (-1,-1), (0,-1)])
            sage: P.triangulation()
            [(0, 2), (2, 8), (3, 5), (6, 8), (8, 3), (3, 6), (9, 11), (0, 9), (2, 9)]

        TESTS::

            sage: Polygon(vertices=[(0,0), (1,0), (1,1), (0,1)]).triangulation()
            [(0, 2)]

            sage: quad = [(0,0), (1,-1), (0,1), (-1,-1)]
            sage: for i in range(4):
            ....:     Polygon(vertices=quad[i:] + quad[:i]).triangulation()
            [(0, 2)]
            [(1, 3)]
            [(0, 2)]
            [(1, 3)]

            sage: poly = [(0,0),(1,1),(2,0),(3,1),(4,0),(4,2),
            ....:     (-4,2),(-4,0),(-3,1),(-2,0),(-1,1)]
            sage: Polygon(vertices=poly).triangulation()
            [(1, 3), (3, 5), (5, 8), (6, 8), (8, 10), (10, 1), (1, 5), (5, 10)]
            sage: for i in range(len(poly)):
            ....:     Polygon(vertices=poly[i:] + poly[:i]).triangulation()
            [(1, 3), (3, 5), (5, 8), (6, 8), (8, 10), (10, 1), (1, 5), (5, 10)]
            [(0, 2), (2, 4), (4, 7), (5, 7), (7, 9), (9, 0), (0, 4), (4, 9)]
            [(1, 3), (3, 6), (4, 6), (6, 8), (8, 10), (10, 1), (3, 8), (10, 3)]
            [(0, 2), (2, 5), (3, 5), (5, 7), (7, 9), (9, 0), (2, 7), (9, 2)]
            [(1, 4), (2, 4), (4, 6), (6, 8), (8, 10), (10, 1), (1, 6), (8, 1)]
            [(0, 3), (1, 3), (3, 5), (5, 7), (7, 9), (9, 0), (0, 5), (7, 0)]
            [(0, 2), (2, 4), (4, 6), (6, 8), (8, 10), (10, 2), (4, 10), (6, 10)]
            [(1, 3), (3, 5), (5, 7), (7, 9), (9, 1), (10, 1), (3, 9), (5, 9)]
            [(0, 2), (2, 4), (4, 6), (6, 8), (8, 0), (9, 0), (2, 8), (4, 8)]
            [(1, 3), (3, 5), (5, 7), (7, 10), (8, 10), (10, 1), (1, 7), (3, 7)]
            [(0, 2), (2, 4), (4, 6), (6, 9), (7, 9), (9, 0), (0, 6), (2, 6)]

            sage: poly = [(0,0), (1,0), (2,0), (2,1), (2,2), (1,2), (0,2), (0,1)]
            sage: Polygon(vertices=poly).triangulation()
            [(0, 3), (1, 3), (3, 5), (5, 7), (7, 3)]
            sage: for i in range(len(poly)):
            ....:     Polygon(vertices=poly[i:] + poly[:i]).triangulation()
            [(0, 3), (1, 3), (3, 5), (5, 7), (7, 3)]
            [(0, 2), (2, 4), (4, 6), (6, 0), (0, 4)]
            [(0, 3), (1, 3), (3, 5), (5, 7), (7, 3)]
            [(0, 2), (2, 4), (4, 6), (6, 0), (0, 4)]
            [(0, 3), (1, 3), (3, 5), (5, 7), (7, 3)]
            [(0, 2), (2, 4), (4, 6), (6, 0), (0, 4)]
            [(0, 3), (1, 3), (3, 5), (5, 7), (7, 3)]
            [(0, 2), (2, 4), (4, 6), (6, 0), (0, 4)]

            sage: poly = [(0,0), (1,2), (3,3), (1,4), (0,6), (-1,4), (-3,-3), (-1,2)]
            sage: Polygon(vertices=poly).triangulation()
            [(0, 3), (1, 3), (3, 5), (5, 7), (7, 3)]
            sage: for i in range(len(poly)):
            ....:     Polygon(vertices=poly[i:] + poly[:i]).triangulation()
            [(0, 3), (1, 3), (3, 5), (5, 7), (7, 3)]
            [(0, 2), (2, 4), (4, 6), (6, 0), (0, 4)]
            [(0, 3), (1, 3), (3, 5), (5, 7), (7, 3)]
            [(0, 2), (2, 4), (4, 6), (6, 0), (0, 4)]
            [(0, 2), (3, 5), (5, 7), (7, 3), (0, 3)]
            [(0, 2), (2, 4), (4, 6), (6, 0), (0, 4)]
            [(0, 6), (1, 3), (3, 5), (5, 1), (6, 1)]
            [(0, 2), (2, 4), (4, 6), (6, 0), (0, 4)]

            sage: x = polygen(QQ)
            sage: p = x^4 - 5*x^2 + 5
            sage: r = AA.polynomial_root(p, RIF(1.17,1.18))
            sage: K.<a> = NumberField(p, embedding=r)

            sage: poly = [(1/2*a^2 - 3/2, 1/2*a),
            ....:  (-a^3 + 2*a^2 + 2*a - 4, 0),
            ....:  (1/2*a^2 - 3/2, -1/2*a),
            ....:   (1/2*a^3 - a^2 - 1/2*a + 1, 1/2*a^2 - a),
            ....:   (-1/2*a^2 + 1, 1/2*a^3 - 3/2*a),
            ....:   (-1/2*a + 1, a^3 - 3/2*a^2 - 2*a + 5/2),
            ....:   (1, 0),
            ....:   (-1/2*a + 1, -a^3 + 3/2*a^2 + 2*a - 5/2),
            ....:   (-1/2*a^2 + 1, -1/2*a^3 + 3/2*a),
            ....:   (1/2*a^3 - a^2 - 1/2*a + 1, -1/2*a^2 + a)]
            sage: Polygon(vertices=poly).triangulation()
            [(0, 3), (1, 3), (3, 5), (5, 7), (7, 9), (9, 3), (3, 7)]

            sage: z = QQbar.zeta(24)
            sage: pts = [(1+i%2) * z**i for i in range(24)]
            sage: pts = [vector(AA, (x.real(), x.imag())) for x in pts]
            sage: Polygon(vertices=pts).triangulation()
            [(0, 2), ..., (16, 0)]

        This is https://github.com/flatsurf/sage-flatsurf/issues/87 ::

            sage: x = polygen(QQ)
            sage: K.<c> = NumberField(x^2 - 3, embedding=AA(3).sqrt())

            sage: Polygon(vertices=[(0, 0), (1, 0), (1/2*c + 1, -1/2), (c + 1, 0), (-3/2*c + 1, 5/2), (0, c - 2)]).triangulation()
            [(0, 4), (1, 3), (4, 1)]

        """
        if len(self._v) == 3:
            return []

        vertices = self._v

        n = len(vertices)
        if n < 3:
            raise ValueError
        if n == 3:
            return []

        # NOTE: The algorithm is naive. We look at all possible chords between
        # the i-th and j-th vertices. If the chord does not intersect any edge
        # then we cut the polygon along this edge and call recursively
        # triangulate on the two pieces.
        for i in range(n - 1):
            eiright = vertices[(i + 1) % n] - vertices[i]
            eileft = vertices[(i - 1) % n] - vertices[i]
            for j in range(i + 2, (n if i else n - 1)):
                ejright = vertices[(j + 1) % n] - vertices[j]
                ejleft = vertices[(j - 1) % n] - vertices[j]
                chord = vertices[j] - vertices[i]

                from flatsurf.geometry.euclidean import is_between

                # check angles with neighbouring edges
                if not (
                    is_between(eiright, eileft, chord)
                    and is_between(ejright, ejleft, -chord)
                ):
                    continue

                # check intersection with other edges
                e = (vertices[i], vertices[j])
                good = True
                for k in range(n):
                    f = (vertices[k], vertices[(k + 1) % n])

                    from flatsurf.geometry.euclidean import is_segment_intersecting
                    res = is_segment_intersecting(e, f)
                    if res == 2:
                        good = False
                        break
                    elif res == 1:
                        assert k == (i - 1) % n or k == i or k == (j - 1) % n or k == j

                if good:
                    part0 = [(s + i, t + i) for s, t in Polygon(vertices=vertices[i: j + 1], check=False).triangulation()]
                    part1 = []
                    for s, t in Polygon(vertices=vertices[j:] + vertices[: i + 1], check=False).triangulation():
                        if s < n - j:
                            s += j
                        else:
                            s -= n - j
                        if t < n - j:
                            t += j
                        else:
                            t -= n - j
                        part1.append((s, t))
                    return [(i, j)] + part0 + part1

        raise RuntimeError("input {} must be wrong".format(vertices))

    def translate(self, u):
        r"""
        TESTS::

            sage: from flatsurf import Polygon
            sage: Polygon(vertices=[(0,0), (2,0), (1,1)]).translate((3,-2))
            Polygon(vertices=[(3, -2), (5, -2), (4, -1)])
        """
        u = (self.base_ring()**2)(u)
        return EuclideanPolygon(self.base_ring(), [u + v for v in self._v], check=False, category=self.category())

    def change_ring(self, ring):
        r"""
        Return an equal polygon over the base ring ``ring``.

        EXAMPLES::

            sage: from flatsurf import polygons
            sage: S = polygons.square()
            sage: K.<sqrt2> = NumberField(x^2 - 2, embedding=AA(2)**(1/2))
            sage: S.change_ring(K)
            Polygon(vertices=[(0, 0), (1, 0), (1, 1), (0, 1)])
            sage: S.change_ring(K).base_ring()
            Number Field in sqrt2 with defining polynomial x^2 - 2 with sqrt2 = 1.4142...
        """
        if ring is self.base_ring():
            return self
        return Polygon(base_ring=ring, vertices=self._v)

    def is_convex(self):
        from flatsurf.geometry.euclidean import ccw
        for i in range(self.num_edges()):
            if ccw(self.edge(i), self.edge(i + 1)) < 0:
                return False
        return True

    def is_strictly_convex(self):
        r"""
        Return whether this polygon is strictly convex.

        EXAMPLES::

            sage: from flatsurf import Polygon
            sage: Polygon(vertices=[(0,0), (1,0), (1,1)]).is_strictly_convex()
            True
            sage: Polygon(vertices=[(0,0), (1,0), (2,0), (1,1)]).is_strictly_convex()
            False
        """
        from flatsurf.geometry.euclidean import ccw
        for i in range(self.num_edges()):
            if ccw(self.edge(i), self.edge(i + 1)) == 0:
                return False
        return True

    def base_ring(self):
        return self.base()

    def num_edges(self):
        return len(self._v)

    def _repr_(self):
        return f"Polygon(vertices={repr(list(self.vertices()))})"

    # From https://en.wikipedia.org/wiki/Polygon#Naming
    _ngon_names = {
        1: ("a", "monogon"),
        2: ("a", "digon"),
        3: ("a", "triangle"),
        4: ("a", "quadrilateral"),
        5: ("a", "pentagon"),
        6: ("a", "hexagon"),
        7: ("a", "heptagon"),
        8: ("an", "octagon"),
        9: ("a", "nonagon"),
        10: ("a", "decagon"),
        11: ("a", "hendecagon"),
        12: ("a", "dodecagon"),
        13: ("a", "tridecagon"),
        14: ("a", "tetradecagon"),
        15: ("a", "pentadecagon"),
        16: ("a", "hexadecagon"),
        17: ("a", "heptadecagon"),
        18: ("an", "octadecagon"),
        19: ("an", "enneadecagon"),
        20: ("an", "icosagon"),
        # Most people probably don't know the prefixes after that. We
        # keep a few easy/fun ones.
        100: ("a", "hectogon"),
        1000: ("a", "chiliagon"),
        10000: ("a", "myriagon"),
        1000000: ("a", "megagon"),
        infinity: ("an", "apeirogon"),
    }

    @staticmethod
    def _describe_polygon(num_edges, **kwargs):
        description = EuclideanPolygon._ngon_names.get(num_edges, f"{num_edges}-gon")
        description = description + (description[1] + "s",)

        def augment(article, *attributes):
            nonlocal description
            description = (
                article,
                " ".join(attributes + (description[1],)),
                " ".join(attributes + (description[2],)),
            )

        def augment_if(article, attribute, *properties):
            if all(
                [
                    kwargs.get(property, False)
                    for property in (properties or [attribute])
                ]
            ):
                augment(article, attribute)
                return True
            return False

        def augment_if_not(article, attribute, *properties):
            if all(
                [
                    kwargs.get(property, True) is False
                    for property in (properties or [attribute])
                ]
            ):
                augment(article, attribute)
                return True
            return False

        if augment_if("a", "degenerate"):
            return description

        if num_edges == 3:
            augment_if("an", "equilateral", "equiangular") or augment_if(
                "an", "isosceles"
            ) or augment_if("a", "right")

            return description

        if num_edges == 4:
            if kwargs.get("equilateral", False) and kwargs.get("equiangular", False):
                return "a", "square", "squares"

            if kwargs.get("equiangular", False):
                return "a", "rectangle", "rectangles"

            if kwargs.get("equilateral", False):
                return "a", "rhombus", "rhombi"

        augment_if("a", "regular", "equilateral", "equiangular")

        augment_if_not("a", "non-convex", "convex")

        marked_vertices = kwargs.get("marked_vertices", 0)
        if marked_vertices:
            if marked_vertices == 1:
                suffix = "with a marked vertex"
            else:
                suffix = f"with {kwargs.get('marked_vertices')} marked vertices"
            description = (
                description[0],
                f"{description[1]} {suffix}",
                f"{description[2]} {suffix}",
            )

        return description

    def slopes(self, relative=False):
        if not relative:
            return self.edges()

        edges = [
            (self.edge((e - 1) % self.num_edges()), self.edge(e))
            for e in range(self.num_edges())
        ]

        cos = [u.dot_product(v) for (u, v) in edges]
        sin = [u[0] * v[1] - u[1] * v[0] for (u, v) in edges]

        return [vector((c, s)) for (c, s) in zip(cos, sin)]

    def describe_polygon(self):
        marked_vertices = self.marked_vertices()

        if marked_vertices and self.area() != 0:
            self = self.erase_marked_vertices()

        properties = {
            "degenerate": self.is_degenerate(),
            "equilateral": self.is_equilateral(),
            "equiangular": self.is_equiangular(),
            "convex": self.is_convex(),
            "marked_vertices": len(marked_vertices),
        }

        if self.num_edges() == 3:
            slopes = self.slopes(relative=True)
            properties["right"] = any(slope[0] == 0 for slope in slopes)

            from flatsurf.geometry.euclidean import is_parallel

            properties["isosceles"] = (
                is_parallel(slopes[0], slopes[1])
                or is_parallel(slopes[0], slopes[2])
                or is_parallel(slopes[1], slopes[2])
            )

        return EuclideanPolygon._describe_polygon(self.num_edges(), **properties)

    def marked_vertices(self):
        from flatsurf.geometry.euclidean import is_parallel

        return [
            vertex
            for (i, vertex) in enumerate(self.vertices())
            if is_parallel(self.edge(i), self.edge((i - 1) % self.num_edges()))
        ]

    def is_degenerate(self):
        if self.area() == 0:
            return True

        if self.marked_vertices():
            return True

        return False

    def erase_marked_vertices(self):
        marked_vertices = self.marked_vertices()

        if not marked_vertices:
            return self

        vertices = [v for v in self.vertices() if v not in marked_vertices]
        return Polygon(vertices=vertices)

    def is_equilateral(self):
        return len(set(edge[0] ** 2 + edge[1] ** 2 for edge in self.edges())) == 1

    def is_equiangular(self):
        slopes = self.slopes(relative=True)

        from flatsurf.geometry.euclidean import is_parallel

        return all(is_parallel(slopes[i - 1], slopes[i]) for i in range(len(slopes)))

    def vertices(self, translation=None):
        r"""
        Return the set of vertices as vectors.
        """
        if translation is None:
            return self._v

        translation = (self.parent().base_ring().fraction_field()**2)(translation)
        return [translation + v for v in self.vertices()]

    def vertex(self, i):
        r"""
        Return the ``i``-th vertex as a vector
        """
        return self._v[i % len(self._v)]

    def __iter__(self):
        return iter(self.vertices())

    def edges(self):
        r"""
        Return an iterator overt the edges
        """
        return [self.edge(i) for i in range(self.num_edges())]

    def edge(self, i):
        r"""
        Return a vector representing the ``i``-th edge of the polygon.
        """
        return self.vertex(i + 1) - self.vertex(i)

    def plot(
        self, translation=None, polygon_options={}, edge_options={}, vertex_options={}
    ):
        r"""
        Plot the polygon with the origin at ``translation``.

        EXAMPLES::

            sage: from flatsurf import polygons
            sage: S = polygons.square()
            sage: S.plot()
            ...Graphics object consisting of 3 graphics primitives

        We can specify an explicit ``zorder`` to render edges and vertices on
        top of the axes which are rendered at z-order 3::

            sage: S.plot(edge_options={'zorder': 3}, vertex_options={'zorder': 3})
            ...Graphics object consisting of 3 graphics primitives

        We can control the colors, e.g., we can render transparent polygons,
        with red edges and blue vertices::

            sage: S.plot(polygon_options={'fill': None}, edge_options={'color': 'red'}, vertex_options={'color': 'blue'})
            ...Graphics object consisting of 3 graphics primitives

        """
        from sage.plot.point import point2d
        from sage.plot.line import line2d
        from sage.plot.polygon import polygon2d

        P = self.vertices(translation)

        polygon_options = {"alpha": 0.3, "zorder": 1, **polygon_options}
        edge_options = {"color": "orange", "zorder": 2, **edge_options}
        vertex_options = {"color": "red", "zorder": 2, **vertex_options}

        return (
            polygon2d(P, **polygon_options)
            + line2d(P + (P[0],), **edge_options)
            + point2d(P, **vertex_options)
        )

    # TODO: Move to category to allow override in subcategories.
    @cached_method
    def is_rational(self):
        for e in range(self.num_edges()):
            u = self.edge(e)
            v = -self.edge((e - 1) % self.num_edges())

            cos = u.dot_product(v)
            sin = u[0] * v[1] - u[1] * v[0]

            from flatsurf.geometry.euclidean import is_cosine_sine_of_rational

            if not is_cosine_sine_of_rational(cos, sin, scaled=True):
                return False

        self._refine_category_(self.category().Rational())

        return True

    # TODO: Move to category to allow override in subcategories. Ensure that if the angles are known the result is immediate.
    def angle(self, e, numerical=None, assume_rational=None):
        r"""
        Return the angle at the beginning of the start point of the edge ``e``.

        EXAMPLES::

            sage: from flatsurf.geometry.polygon import polygons
            sage: polygons.square().angle(0)
            1/4
            sage: polygons.regular_ngon(8).angle(0)
            3/8

            sage: from flatsurf import Polygon
            sage: T = Polygon(vertices=[(0,0), (3,1), (1,5)])
            sage: [T.angle(i, numerical=True) for i in range(3)]  # abs tol 1e-13
            [0.16737532973071603, 0.22741638234956674, 0.10520828791971722]
            sage: sum(T.angle(i, numerical=True) for i in range(3))   # abs tol 1e-13
            0.5
        """
        if assume_rational is not None:
            import warnings

            warnings.warn(
                "assume_rational has been deprecated as a keyword to angle() and will be removed from a future version of sage-flatsurf"
            )

        if numerical is None:
            numerical = not self.is_rational()

            if numerical:
                import warnings

                warnings.warn(
                    "the behavior of angle() has been changed in recent versions of sage-flatsurf; for non-rational polygons, numerical=True must be set explicitly to get a numerical approximation of the angle"
                )

        return angle(
            self.edge(e),
            -self.edge((e - 1) % self.num_edges()),
            numerical=numerical,
        )

    # TODO: Move to category to allow override in subcategories.
    def angles(self, numerical=None, assume_rational=None):
        r"""
        Return the list of angles of this polygon (divided by `2 \pi`).

        EXAMPLES::

            sage: from flatsurf import Polygon

            sage: T = Polygon(angles=[1, 2, 3])
            sage: [T.angle(i) for i in range(3)]
            [1/12, 1/6, 1/4]
            sage: T.angles()
            (1/12, 1/6, 1/4)
            sage: sum(T.angle(i) for i in range(3))
            1/2
        """
        if assume_rational is not None:
            import warnings

            warnings.warn(
                "assume_rational has been deprecated as a keyword to angles() and will be removed from a future version of sage-flatsurf"
            )

        angles = tuple(self.angle(i, numerical=numerical) for i in range(self.num_edges()))

        if not numerical:
            self._refine_category_(self.category().WithAngles(angles))

        return angles

    def area(self):
        r"""
        Return the area of this polygon.

        EXAMPLES::

            sage: from flatsurf.geometry.polygon import polygons
            sage: polygons.regular_ngon(8).area()
            2*a + 2
            sage: _ == 2*AA(2).sqrt() + 2
            True

            sage: AA(polygons.regular_ngon(11).area())
            9.36563990694544?

            sage: polygons.square().area()
            1
            sage: (2*polygons.square()).area()
            4
        """
        # Will use an area formula obtainable from Green's theorem. See for instance:
        # http://math.blogoverflow.com/2014/06/04/greens-theorem-and-area-of-polygons/
        total = self.base_ring().zero()
        for i in range(self.num_edges()):
            total += (self.vertex(i)[0] + self.vertex(i + 1)[0]) * self.edge(i)[1]
        return total / ZZ(2)

    def centroid(self):
        r"""
        Return the coordinates of the centroid of this polygon.

        ALGORITHM:

        We use the customary formula of the centroid of polygons, see
        https://en.wikipedia.org/wiki/Centroid#Of_a_polygon

        EXAMPLES::

            sage: from flatsurf.geometry.polygon import polygons
            sage: P = polygons.regular_ngon(4)
            sage: P
            Polygon(vertices=[(0, 0), (1, 0), (1, 1), (0, 1)])
            sage: P.centroid()
            (1/2, 1/2)

            sage: P = polygons.regular_ngon(8); P
            Polygon(vertices=[(0, 0), (1, 0), (1/2*a + 1, 1/2*a), (1/2*a + 1, 1/2*a + 1), (1, a + 1), (0, a + 1), (-1/2*a, 1/2*a + 1), (-1/2*a, 1/2*a)])
            sage: P.centroid()
            (1/2, 1/2*a + 1/2)

            sage: P = polygons.regular_ngon(11)
            sage: C = P.centroid()
            sage: P = P.translate(-C)
            sage: P.centroid()
            (0, 0)

        """
        x, y = list(zip(*self.vertices()))
        nvertices = len(x)
        A = self.area()

        from sage.all import vector

        return vector(
            (
                ~(6 * A)
                * sum(
                    [
                        (x[i - 1] + x[i]) * (x[i - 1] * y[i] - x[i] * y[i - 1])
                        for i in range(nvertices)
                    ]
                ),
                ~(6 * A)
                * sum(
                    [
                        (y[i - 1] + y[i]) * (x[i - 1] * y[i] - x[i] * y[i - 1])
                        for i in range(nvertices)
                    ]
                ),
            )
        )

    def j_invariant(self):
        r"""
        Return the Kenyon-Smille J-invariant of this polygon.

        The base ring of the polygon must be a number field.

        The output is a triple ``(Jxx, Jyy, Jxy)`` that corresponds
        respectively to the Sah-Arnoux-Fathi invariant of the vertical flow,
        the Sah-Arnoux-Fathi invariant of the horizontal flow and the `xy`-matrix.

        EXAMPLES::

            sage: from flatsurf import polygons

            sage: polygons.right_triangle(1/3,1).j_invariant()
            (
                      [0 0]
            (0), (0), [1 0]
            )

        The regular 8-gon::

            sage: polygons.regular_ngon(8).j_invariant()
            (
                      [2 2]
            (0), (0), [2 1]
            )

            (
                           [  0 3/2]
            (1/2), (-1/2), [3/2   0]
            )

        Some extra debugging::

            sage: from flatsurf.geometry.polygon import EuclideanPolygon
            sage: K.<a> = NumberField(x^3 - 2, embedding=AA(2)**(1/3))
            sage: ux = 1 + a + a**2
            sage: uy = -2/3 + a
            sage: vx = 1/5 - a**2
            sage: vy = a + 7/13*a**2

            sage: from flatsurf import Polygon
            sage: p = Polygon(edges=[(ux, uy), (vx,vy), (-ux-vx,-uy-vy)], base_ring=K)
            sage: Jxx, Jyy, Jxy = p.j_invariant()
            sage: EuclideanPolygon._wedge_product(ux.vector(), vx.vector()) == Jxx
            True
            sage: EuclideanPolygon._wedge_product(uy.vector(), vy.vector()) == Jyy
            True

        """
        if self.base_ring() is QQ:
            raise NotImplementedError

        K = self.base_ring()
        try:
            V, from_V, to_V = K.vector_space()
        except (AttributeError, ValueError):
            raise ValueError("the surface needs to be define over a number field")

        dim = K.degree()
        M = K**(dim * (dim - 1) // 2)
        Jxx = Jyy = M.zero()
        Jxy = matrix(K, dim)
        vertices = list(self.vertices())
        vertices.append(vertices[0])

        for i in range(len(vertices) - 1):
            a = to_V(vertices[i][0])
            b = to_V(vertices[i][1])
            c = to_V(vertices[i + 1][0])
            d = to_V(vertices[i + 1][1])
            Jxx += EuclideanPolygon._wedge_product(a, c)
            Jyy += EuclideanPolygon._wedge_product(b, d)
            Jxy += EuclideanPolygon._tensor_product(a, d)
            Jxy -= EuclideanPolygon._tensor_product(c, b)

        return (Jxx, Jyy, Jxy)

    @staticmethod
    def _wedge_product(v, w):
        r"""
        Return the wedge product of ``v`` and ``w``.

        This is a helper method for :meth:`j_invariant`.

        EXAMPLES::

            sage: from flatsurf.geometry.polygon import EuclideanPolygon

            sage: EuclideanPolygon._wedge_product(vector((1, 2)), vector((1, 2)))
            (0)
            sage: EuclideanPolygon._wedge_product(vector((1, 2)), vector((2, 1)))
            (-3)

            sage: EuclideanPolygon._wedge_product(vector((1, 2, 3)), vector((2, 3, 4)))
            (-1, -2, -1)

        """
        d = len(v)

        assert len(w) == d

        R = v.base_ring()

        return free_module_element(
            R,
            d * (d - 1) // 2,
            [(v[i] * w[j] - v[j] * w[i]) for i in range(d - 1) for j in range(i + 1, d)],
        )

    @staticmethod
    def _tensor_product(u, v):
        r"""
        Return the tensor product of ``u`` and ``v``.

        This is a helper method for :meth:`j_invariant`.

        EXAMPLES::

            sage: from flatsurf.geometry.polygon import EuclideanPolygon
            sage: EuclideanPolygon._tensor_product(vector((2, 3, 5)), vector((7, 11, 13)))
            [14 21 35]
            [22 33 55]
            [26 39 65]

        """
        from sage.all import vector

        u = vector(u)
        v = vector(v)

        d = len(u)
        R = u.base_ring()

        assert len(u) == len(v) and v.base_ring() == R
        from sage.all import matrix
        return matrix(R, d, [u[i] * v[j] for j in range(d) for i in range(d)])

    def is_isometric(self, other, certificate=False):
        r"""
        Return whether ``self`` and ``other`` are isometric convex polygons via an orientation
        preserving isometry.

        If ``certificate`` is set to ``True`` return also a pair ``(index, rotation)``
        of an integer ``index`` and a matrix ``rotation`` such that the given rotation
        matrix identifies this polygon with the other and the edges 0 in this polygon
        is mapped to the edge ``index`` in the other.

        .. TODO::

            Implement ``is_linearly_equivalent`` and ``is_similar``.

        EXAMPLES::

            sage: from flatsurf import Polygon, polygons
            sage: S = polygons.square()
            sage: S.is_isometric(S)
            True
            sage: U = matrix(2,[0,-1,1,0]) * S
            sage: U.is_isometric(S)
            True

            sage: x = polygen(QQ)
            sage: K.<sqrt2> = NumberField(x^2 - 2, embedding=AA(2)**(1/2))
            sage: S = S.change_ring(K)
            sage: U = matrix(2, [sqrt2/2, -sqrt2/2, sqrt2/2, sqrt2/2]) * S
            sage: U.is_isometric(S)
            True

            sage: U2 = Polygon(edges=[(1,0), (sqrt2/2, sqrt2/2), (-1,0), (-sqrt2/2, -sqrt2/2)])
            sage: U2.is_isometric(U)
            False
            sage: U2.is_isometric(U, certificate=True)
            (False, None)

            sage: S = Polygon(edges=[(1,0), (sqrt2/2, 3), (-2,3), (-sqrt2/2+1, -6)])
            sage: T = Polygon(edges=[(sqrt2/2,3), (-2,3), (-sqrt2/2+1, -6), (1,0)])
            sage: isometric, cert = S.is_isometric(T, certificate=True)
            sage: assert isometric
            sage: shift, rot = cert
            sage: Polygon(edges=[rot * S.edge((k + shift) % 4) for k in range(4)]).translate(T.vertex(0)) == T
            True


            sage: T = (matrix(2, [sqrt2/2, -sqrt2/2, sqrt2/2, sqrt2/2]) * S).translate((3,2))
            sage: isometric, cert = S.is_isometric(T, certificate=True)
            sage: assert isometric
            sage: shift, rot = cert
            sage: Polygon(edges=[rot * S.edge(k + shift) for k in range(4)]).translate(T.vertex(0)) == T
            True
        """
        if type(self) is not type(other):
            raise TypeError

        n = self.num_edges()
        if other.num_edges() != n:
            return False
        sedges = self.edges()
        oedges = other.edges()

        slengths = [x**2 + y**2 for x, y in sedges]
        olengths = [x**2 + y**2 for x, y in oedges]
        for i in range(n):
            if slengths == olengths:
                # we have a match of lengths after a shift by i
                xs, ys = sedges[0]
                xo, yo = oedges[0]
                ms = matrix(2, [xs, -ys, ys, xs])
                mo = matrix(2, [xo, -yo, yo, xo])
                rot = mo * ~ms
                assert rot.det() == 1 and (rot * rot.transpose()).is_one()
                assert oedges[0] == rot * sedges[0]
                if all(oedges[i] == rot * sedges[i] for i in range(1, n)):
                    return (
                        (True, (0 if i == 0 else n - i, rot)) if certificate else True
                    )
            olengths.append(olengths.pop(0))
            oedges.append(oedges.pop(0))
        return (False, None) if certificate else False

    def is_translate(self, other, certificate=False):
        r"""
        Return whether ``other`` is a translate of ``self``.

        EXAMPLES::

            sage: from flatsurf import Polygon
            sage: S = Polygon(vertices=[(0,0), (3,0), (1,1)])
            sage: T1 = S.translate((2,3))
            sage: S.is_translate(T1)
            True
            sage: T2 = Polygon(vertices=[(-1,1), (1,0), (2,1)])
            sage: S.is_translate(T2)
            False
            sage: T3 = Polygon(vertices=[(0,0), (3,0), (2,1)])
            sage: S.is_translate(T3)
            False

            sage: S.is_translate(T1, certificate=True)
            (True, (0, 1))
            sage: S.is_translate(T2, certificate=True)
            (False, None)
            sage: S.is_translate(T3, certificate=True)
            (False, None)
        """
        if type(self) is not type(other):
            raise TypeError

        n = self.num_edges()
        if other.num_edges() != n:
            return False
        sedges = self.edges()
        oedges = other.edges()
        for i in range(n):
            if sedges == oedges:
                return (True, (i, 1)) if certificate else True
            oedges.append(oedges.pop(0))
        return (False, None) if certificate else False

    def is_half_translate(self, other, certificate=False):
        r"""
        Return whether ``other`` is a translate or half-translate of ``self``.

        If ``certificate`` is set to ``True`` then return also a pair ``(orientation, index)``.

        EXAMPLES::

            sage: from flatsurf import Polygon
            sage: S = Polygon(vertices=[(0,0), (3,0), (1,1)])
            sage: T1 = S.translate((2,3))
            sage: S.is_half_translate(T1)
            True
            sage: T2 = Polygon(vertices=[(-1,1), (1,0), (2,1)])
            sage: S.is_half_translate(T2)
            True
            sage: T3 = Polygon(vertices=[(0,0), (3,0), (2,1)])
            sage: S.is_half_translate(T3)
            False

            sage: S.is_half_translate(T1, certificate=True)
            (True, (0, 1))
            sage: half_translate, cert = S.is_half_translate(T2, certificate=True)
            sage: assert half_translate
            sage: shift, rot = cert
            sage: Polygon(edges=[rot * S.edge(k + shift) for k in range(3)]).translate(T2.vertex(0)) == T2
            True
            sage: S.is_half_translate(T3, certificate=True)
            (False, None)
        """
        if type(self) is not type(other):
            raise TypeError

        n = self.num_edges()
        if other.num_edges() != n:
            return False

        sedges = self.edges()
        oedges = other.edges()
        for i in range(n):
            if sedges == oedges:
                return (True, (i, 1)) if certificate else True
            oedges.append(oedges.pop(0))

        assert oedges == other.edges()
        oedges = [-e for e in oedges]
        for i in range(n):
            if sedges == oedges:
                return (True, (0 if i == 0 else n - i, -1)) if certificate else True
            oedges.append(oedges.pop(0))

        return (False, None) if certificate else False


class PolygonsConstructor:
    def square(self, side=1, **kwds):
        r"""
        EXAMPLES::

            sage: from flatsurf.geometry.polygon import polygons

            sage: polygons.square()
            Polygon(vertices=[(0, 0), (1, 0), (1, 1), (0, 1)])
            sage: polygons.square(base_ring=QQbar).category()
            Category of convex real projective rectangles over Algebraic Field

        """
        return self.rectangle(side, side, **kwds)

    def rectangle(self, width, height, **kwds):
        r"""
        EXAMPLES::

            sage: from flatsurf.geometry.polygon import polygons

            sage: polygons.rectangle(1,2)
            Polygon(vertices=[(0, 0), (1, 0), (1, 2), (0, 2)])

            sage: K.<sqrt2> = QuadraticField(2)
            sage: polygons.rectangle(1,sqrt2)
            Polygon(vertices=[(0, 0), (1, 0), (1, sqrt2), (0, sqrt2)])
            sage: _.category()
            Category of convex real projective rectangles over Number Field in sqrt2 with defining polynomial x^2 - 2 with sqrt2 = 1.414213562373095?

        """
        return Polygon(edges=[(width, 0), (0, height), (-width, 0), (0, -height)], angles=(1, 1, 1, 1), **kwds)

    def triangle(self, a, b, c):
        """
        Return the triangle with angles a*pi/N,b*pi/N,c*pi/N where N=a+b+c.

        INPUT:

        - ``a``, ``b``, ``c`` -- integers

        EXAMPLES::

            sage: from flatsurf.geometry.polygon import polygons
            sage: T = polygons.triangle(3,4,5)
            sage: T
            Polygon(vertices=[(0, 0), (1, 0), (-1/2*c0 + 3/2, -1/2*c0 + 3/2)])
            sage: T.base_ring()
            Number Field in c0 with defining polynomial x^2 - 3 with c0 = 1.732050807568878?

            sage: polygons.triangle(1,2,3).angles()
            (1/12, 1/6, 1/4)

        Some fairly complicated examples::

            sage: polygons.triangle(1, 15, 21)  # long time (2s)
            Polygon(vertices=[(0, 0),
                              (1, 0),
                              (1/2*c^34 - 17*c^32 + 264*c^30 - 2480*c^28 + 15732*c^26 - 142481/2*c^24 + 237372*c^22 - 1182269/2*c^20 +
                               1106380*c^18 - 1552100*c^16 + 3229985/2*c^14 - 2445665/2*c^12 + 654017*c^10 - 472615/2*c^8 + 107809/2*c^6 - 13923/2*c^4 + 416*c^2 - 6,
                               -1/2*c^27 + 27/2*c^25 - 323/2*c^23 + 1127*c^21 - 10165/2*c^19 + 31009/2*c^17 - 65093/2*c^15 + 46911*c^13 - 91091/2*c^11 + 57355/2*c^9 - 10994*c^7 + 4621/2*c^5 - 439/2*c^3 + 6*c)])

            sage: polygons.triangle(2, 13, 26)  # long time (3s)
            Polygon(vertices=[(0, 0),
                              (1, 0),
                              (1/2*c^30 - 15*c^28 + 405/2*c^26 - 1625*c^24 + 8625*c^22 - 31878*c^20 + 168245/2*c^18 - 159885*c^16 + 218025*c^14 - 209950*c^12 + 138567*c^10 - 59670*c^8 + 15470*c^6 - 2100*c^4 + 225/2*c^2 - 1/2,
                               -1/2*c^39 + 19*c^37 - 333*c^35 + 3571*c^33 - 26212*c^31 + 139593*c^29 - 557844*c^27 + 1706678*c^25 - 8085237/2*c^23 + 7449332*c^21 -
                               10671265*c^19 + 11812681*c^17 - 9983946*c^15 + 6317339*c^13 - 5805345/2*c^11 + 1848183/2*c^9 - 378929/2*c^7 + 44543/2*c^5 - 2487/2*c^3 + 43/2*c)])
        """
        return Polygon(angles=[a, b, c], check=False)

    @staticmethod
    def regular_ngon(n, field=None):
        r"""
        Return a regular n-gon with unit length edges, first edge horizontal, and other vertices lying above this edge.

        Assuming field is None (by default) the polygon is defined over a NumberField (the minimal number field determined by n).
        Otherwise you can set field equal to AA to define the polygon over the Algebraic Reals. Other values for the field
        parameter will result in a ValueError.

        EXAMPLES::

            sage: from flatsurf.geometry.polygon import polygons

            sage: p = polygons.regular_ngon(17)
            sage: p
            Polygon(vertices=[(0, 0), (1, 0), ..., (-1/2*a^14 + 15/2*a^12 - 45*a^10 + 275/2*a^8 - 225*a^6 + 189*a^4 - 70*a^2 + 15/2, 1/2*a)])

            sage: polygons.regular_ngon(3,field=AA)
            Polygon(vertices=[(0, 0), (1, 0), (1/2, 0.866025403784439?)])
        """
        # The code below crashes for n=4!
        if n == 4:
            return polygons.square(QQ(1), base_ring=field)

        from sage.rings.qqbar import QQbar

        c = QQbar.zeta(n).real()
        s = QQbar.zeta(n).imag()

        if field is None:
            field, (c, s) = number_field_elements_from_algebraics((c, s))
        cn = field.one()
        sn = field.zero()
        edges = [(cn, sn)]
        for _ in range(n - 1):
            cn, sn = c * cn - s * sn, c * sn + s * cn
            edges.append((cn, sn))

        ngon = Polygon(base_ring=field, edges=edges)
        ngon._refine_category_(ngon.category().WithAngles([1] * n))
        return ngon

    @staticmethod
    def right_triangle(angle, leg0=None, leg1=None, hypotenuse=None):
        r"""
        Return a right triangle in a number field with an angle of pi*angle.

        You can specify the length of the first leg (``leg0``), the second leg (``leg1``),
        or the ``hypotenuse``.

        EXAMPLES::

            sage: from flatsurf import polygons

            sage: P = polygons.right_triangle(1/3, 1)
            sage: P
            Polygon(vertices=[(0, 0), (1, 0), (1, a)])
            sage: P.base_ring()
            Number Field in a with defining polynomial y^2 - 3 with a = 1.732050807568878?

            sage: polygons.right_triangle(1/4,1)
            Polygon(vertices=[(0, 0), (1, 0), (1, 1)])
            sage: polygons.right_triangle(1/4,1).base_ring()
            Rational Field
        """
        from sage.rings.qqbar import QQbar

        angle = QQ(angle)
        if angle <= 0 or angle > QQ((1, 2)):
            raise ValueError("angle must be in ]0,1/2]")

        z = QQbar.zeta(2 * angle.denom()) ** angle.numerator()
        c = z.real()
        s = z.imag()

        nargs = (leg0 is not None) + (leg1 is not None) + (hypotenuse is not None)

        if nargs == 0:
            leg0 = 1
        elif nargs > 1:
            raise ValueError("only one length can be specified")

        if leg0 is not None:
            c, s = leg0 * c / c, leg0 * s / c
        elif leg1 is not None:
            c, s = leg1 * c / s, leg1 * s / s
        elif hypotenuse is not None:
            c, s = hypotenuse * c, hypotenuse * s

        field, (c, s) = number_field_elements_from_algebraics((c, s))

        return Polygon(
            base_ring=field,
            edges=[(c, field.zero()), (field.zero(), s), (-c, -s)])

    def __call__(self, *args, **kwargs):
        r"""
        EXAMPLES::

            sage: from flatsurf import polygons

            sage: polygons((1,0),(0,1),(-1,0),(0,-1))
            doctest:warning
            ...
            UserWarning: calling Polygon() with positional arguments has been deprecated and will not be supported in a future version of sage-flatsurf; use edges= or vertices= explicitly instead
            Polygon(vertices=[(0, 0), (1, 0), (1, 1), (0, 1)])
            sage: polygons((1,0),(0,1),(-1,0),(0,-1), ring=QQbar)
            doctest:warning
            ...
            UserWarning: ring has been deprecated as a keyword argument to Polygon() and will be removed in a future version of sage-flatsurf; use base_ring instead
            Polygon(vertices=[(0, 0), (1, 0), (1, 1), (0, 1)])
            sage: _.category()
            Category of convex real projective polygons over Algebraic Field

            sage: polygons(vertices=[(0,0), (1,0), (0,1)])
            Polygon(vertices=[(0, 0), (1, 0), (0, 1)])

            sage: polygons(edges=[(2,0),(-1,1),(-1,-1)], base_point=(3,3))
            doctest:warning
            ...
            UserWarning: base_point has been deprecated as a keyword argument to Polygon() and will be removed in a future version of sage-flatsurf; use .translate() on the resulting polygon instead
            Polygon(vertices=[(3, 3), (5, 3), (4, 4)])
            sage: polygons(vertices=[(0,0),(2,0),(1,1)], base_point=(3,3))
            Polygon(vertices=[(3, 3), (5, 3), (4, 4)])

            sage: polygons(angles=[1,1,1,2], length=1)
            doctest:warning
            ...
            UserWarning: length has been deprecated as a keyword argument to Polygon() and will be removed in a future version of sage-flatsurf; use lengths instead
            Polygon(vertices=[(0, 0), (1, 0), (-1/2*c^2 + 5/2, 1/2*c), (-1/2*c^2 + 2, 1/2*c^3 - 3/2*c)])
            sage: polygons(angles=[1,1,1,2], length=2)
            Polygon(vertices=[(0, 0), (2, 0), (-c^2 + 5, c), (-c^2 + 4, c^3 - 3*c)])
            sage: polygons(angles=[1,1,1,2], length=AA(2)**(1/2))
            Polygon(vertices=[(0, 0), (1.414213562373095?, 0), (0.9771975379242739?, 1.344997023927915?), (0.270090756737727?, 0.831253875554907?)])

            sage: polygons(angles=[1]*5).angles()
            (3/10, 3/10, 3/10, 3/10, 3/10)
            sage: polygons(angles=[1]*8).angles()
            (3/8, 3/8, 3/8, 3/8, 3/8, 3/8, 3/8, 3/8)

            sage: P = polygons(angles=[1,1,3,3], lengths=[3,1])
            sage: P.angles()
            (1/8, 1/8, 3/8, 3/8)
            sage: e0 = P.edge(0); assert e0[0]**2 + e0[1]**2 == 3**2
            sage: e1 = P.edge(1); assert e1[0]**2 + e1[1]**2 == 1

            sage: polygons(angles=[1, 1, 1, 2])
            Polygon(vertices=[(0, 0), (1/10*c^3 + c^2 - 1/5*c - 3, 0), (1/20*c^3 + 1/2*c^2 - 1/20*c - 3/2, 1/20*c^2 + 1/2*c), (1/2*c^2 - 3/2, 1/2*c)])

            sage: polygons(angles=[1,1,1,8])
            Polygon(vertices=[(0, 0), (c^6 - 6*c^4 + 8*c^2 + 3, 0), (1/2*c^4 - 3*c^2 + 9/2, 1/2*c^9 - 9/2*c^7 + 13*c^5 - 11*c^3 - 3*c), (1/2*c^6 - 7/2*c^4 + 7*c^2 - 3, 1/2*c^9 - 5*c^7 + 35/2*c^5 - 49/2*c^3 + 21/2*c)])
            sage: polygons(angles=[1,1,1,8], lengths=[1, 1])
            Polygon(vertices=[(0, 0), (1, 0), (-1/2*c^4 + 2*c^2, 1/2*c^7 - 7/2*c^5 + 7*c^3 - 7/2*c), (1/2*c^6 - 7/2*c^4 + 13/2*c^2 - 3/2, 1/2*c^9 - 9/2*c^7 + 27/2*c^5 - 29/2*c^3 + 5/2*c)])

        TESTS::

            sage: from itertools import product
            sage: for a,b,c in product(range(1,5), repeat=3):  # long time (3s)
            ....:     if gcd([a,b,c]) != 1:
            ....:         continue
            ....:     T = polygons(angles=[a,b,c])
            ....:     D = 2*(a+b+c)
            ....:     assert T.angles() == [a/D, b/D, c/D]
            ....:     assert T.edge(0) == (T.base_ring()**2)((1,0))
        """
        import warnings
        warnings.warn("calling polygons() has been deprecated and will be removed in a future version of sage-flatsurf; use Polygon() instead")
        return Polygon(*args, **kwargs)


def ConvexPolygons(base_ring):
    # TODO: Deprecate
    return RealProjectivePolygons(base_ring).Convex()


def Polygon(*args, vertices=None, edges=None, angles=None, lengths=None, base_ring=None, category=None, check=True, **kwds):
    if "base_point" in kwds:
        base_point = kwds.pop("base_point")
        import warnings
        warnings.warn("base_point has been deprecated as a keyword argument to Polygon() and will be removed in a future version of sage-flatsurf; use .translate() on the resulting polygon instead")
        return Polygon(*args, vertices=vertices, edges=edges, angles=angles, lengths=lengths, base_ring=base_ring, category=category, **kwds).translate(base_point)

    if "ring" in kwds:
        import warnings
        warnings.warn("ring has been deprecated as a keyword argument to Polygon() and will be removed in a future version of sage-flatsurf; use base_ring instead")
        base_ring = kwds.pop("ring")

    if "field" in kwds:
        import warnings
        warnings.warn("field has been deprecated as a keyword argument to Polygon() and will be removed in a future version of sage-flatsurf; use base_ring instead")
        base_ring = kwds.pop("field")

    convex = None
    if "convex" in kwds:
        convex = kwds.pop("convex")
        import warnings
        if convex:
            warnings.warn("convex has been deprecated as a keyword argument to Polygon() and will be removed in a future version of sage-flatsurf; it has no effect other than checking the input for convexity so you may just drop it")
        else:
            warnings.warn("convex has been deprecated as a keyword argument to Polygon() and will be removed in a future version of sage-flatsurf; it has no effect anymore, polygons are always allowed to be non-convex")

    if args:
        import warnings
        warnings.warn("calling Polygon() with positional arguments has been deprecated and will not be supported in a future version of sage-flatsurf; use edges= or vertices= explicitly instead")

        edges = args

    if angles:
        if "length" in kwds:
            import warnings
            warnings.warn("length has been deprecated as a keyword argument to Polygon() and will be removed in a future version of sage-flatsurf; use lengths instead")

            lengths = [kwds.pop("length")] * (len(angles) - 2)

    if kwds:
        raise ValueError("keyword argument not supported by Polygon()")

    # Determine the number of sides of this polygon.
    if angles:
        n = len(angles)
    elif edges:
        n = len(edges)
    elif vertices:
        n = len(vertices)
    else:
        raise ValueError("one of vertices, edges, or angles must be set")

    # Determine the base ring of the polygon
    if base_ring is None:
        from sage.categories.pushout import pushout
        base_ring = QQ

        if angles:
            from flatsurf import EuclideanPolygonsWithAngles
            base_ring = pushout(base_ring, EuclideanPolygonsWithAngles(angles).base_ring())

        if vertices:
            base_ring = pushout(base_ring, Sequence([v[0] for v in vertices] + [v[1] for v in vertices]).universe())

        if edges:
            base_ring = pushout(base_ring, Sequence([e[0] for e in edges] + [e[1] for e in edges]).universe())

        if lengths:
            base_ring = pushout(base_ring, Sequence(lengths).universe())

            if angles and not edges:
                with_angles = EuclideanPolygonsWithAngles(angles)
                for slope, length in zip(with_angles.slopes(), lengths):
                    scale = base_ring(length**2 / (slope[0]**2 + slope[1]**2))
                    if not scale.is_square():
                        # Note that this ring might not be minimal.
                        base_ring = pushout(base_ring, with_angles._cosines_ring())

    if category is None:
        from flatsurf.geometry.categories import RealProjectivePolygons
        category = RealProjectivePolygons(base_ring)
        if angles:
            category = category.WithAngles(angles)

    # We now rewrite the given data into vertices. Whenever there is
    # redundancy, we check that things are compatible. Note that much of the
    # complication of the below comes from the "angles" keyword. When angles
    # are given, some of the vertex coordinates can be deduced automatically.

    # Track whether we made a choice that possibly is the reason that we fail
    # to find a polygon with the given data.
    choice = False

    # Rewrite angles and lengths as angles and edges.
    if angles and lengths and not edges:
        edges = []
        for slope, length in zip(category.slopes(), lengths):
            scale = base_ring((length**2 / (slope[0]**2 + slope[1]**2)).sqrt())
            edges.append(scale * slope)

        if len(edges) == n:
            angles = 0

        lengths = None

    # Deduce edges if only angles are given
    if angles and not edges and not vertices:
        assert not lengths

        choice = True

        # We pick the edges such that they form a closed polygon with the
        # prescribed angles. However, there might be self-intersection which
        # currently leads to an error.
        edges = [length * slope for (length, slope) in zip(sum(r.vector() for r in category.lengths_polytope().rays()), category.slopes())]

    # Rewrite edges as vertices.
    if edges and not vertices:
        vertices = [vector(base_ring, (0, 0))]
        for edge in edges:
            vertices.append(vertices[-1] + vector(base_ring, edge))

        if len(vertices) == n + 1:
            if vertices[-1]:
                raise ValueError("polygon not closed")
            vertices.pop()

        edges = None

    assert vertices

    vertices = [vector(base_ring, vertex) for vertex in vertices]

    # Deduce missing vertices for prescribed angles
    if angles and len(vertices) != n:
        if len(vertices) == n - 1:
            # We do not use category.slopes() since the matrix formed by such
            # slopes might not be invertible (because exact-reals do not have a
            # fraction field implemented.)
            slopes = EuclideanPolygonsWithAngles(angles).slopes()

            # We do not use solve_left() because the vertices might not live in
            # a ring that has a fraction field implemented (such as an
            # exact-real ring.)
            s, t = (vertices[0] - vertices[n - 2]) * matrix([slopes[-1], slopes[n - 2]]).inverse()
            assert vertices[0] - s * slopes[-1] == vertices[n - 2] + t * slopes[n - 2]

            if s <= 0 or t <= 0:
                raise (NotImplementedError if choice else ValueError)("cannot determine polygon with these angles from the given data")

            vertices.append(vertices[0] - s * slopes[-1])

        if len(vertices) != n:
            raise NotImplementedError(f"cannot construct {n}-gon from {n} angles and {len(vertices)} vertices")

        angles = None

    assert len(vertices) == n, f"expected to build an {n}-gon from {n} vertices but found {vertices}"

    p = EuclideanPolygon(
        base_ring=base_ring, vertices=vertices, category=category
    )

    # Check that any redundant data is compatible
    if check:
        # TODO: Where is the check for self-intersection?
        if edges:
            # Check compatibility of vertices and edges
            if len(edges) != len(vertices):
                raise ValueError("vertices and edges must have the same length")

            for i in range(n):
                if vertices[i - 1] + edge[i - 1] != vertices[i]:
                    raise ValueError("vertices and edges are not compatible")

        # TODO: Do not check angles if we are sure that they are correct already.
        if angles:
            # Check that the polygon has the prescribed angles
            from flatsurf.geometry.categories.real_projective_polygons_with_angles import RealProjectivePolygonsWithAngles
            # Use EuclideanPolygon.angles() so we do not use the precomputed angles set by the category.
            if RealProjectivePolygonsWithAngles._normalize_angles(angles) != EuclideanPolygon.angles(p):
                raise ValueError("polygon does not have the prescribed angles")

        if lengths:
            # TODO
            raise NotImplementedError

        if convex and not p.is_convex():
            raise ValueError("polygon is not convex")

    return p


polygons = PolygonsConstructor()


def EuclideanPolygonsWithAngles(*angles, **kwds):
    r"""
    TODO: Document

    TESTS::

        sage: from flatsurf import EquiangularPolygons

    The polygons with inner angles `\pi/4`, `\pi/2`, `5\pi/4`::

        sage: P = EquiangularPolygons(1, 2, 5)
        sage: P
        Category of real projective triangles with angles (1/16, 1/8, 5/16) over Number Field in c0 with defining polynomial x^2 - 2 with c0 = 1.414213562373095?

    Internally, polygons are given by their vertices' coordinates over some
    number field, in this case a quadratic field::

        sage: P.base_ring()
        Number Field in c0 with defining polynomial x^2 - 2 with c0 = 1.414213562373095?

    Polygons can also be defined over other number field implementations::

        sage: from pyeantic import RealEmbeddedNumberField # optional: eantic  # random output due to matplotlib warnings with some combinations of setuptools and matplotlib
        sage: K = RealEmbeddedNumberField(P.base_ring()) # optional: eantic
        sage: P(K(1)) # optional: eantic
        UserWarning: calling EquiangularPolygons() has been deprecated and will be removed in a future version of sage-flatsurf; use Polygon(angles=[...], lengths=[...]) instead. To make the resulting polygon non-normalized, i.e., the lengths are not actual edge lengths but the multiple of slope vectors, use Polygon(edges=[length * slope for (length, slope) in zip(lengths, EuclideanPolygonsWithAngles(angles).slopes())]).
        polygon(vertices=[(0, 0), (1, 0), (1/2*c0, -1/2*c0 + 1)])
        sage: _.base_ring() # optional: eantic
        Number Field in c0 with defining polynomial x^2 - 2 with c0 = 1.414213562373095?

    However, specific instances of such polygons might be defined over another ring::

        sage: P(1)
        doctest:warning
        ...
        UserWarning: calling EquiangularPolygons() has been deprecated and will be removed in a future version of sage-flatsurf; use Polygon(angles=[...], lengths=[...]) instead. To make the resulting polygon non-normalized, i.e., the lengths are not actual edge lengths but the multiple of slope vectors, use Polygon(edges=[length * slope for (length, slope) in zip(lengths, EuclideanPolygonsWithAngles(angles).slopes())]).
        Polygon(vertices=[(0, 0), (1, 0), (1/2*c0, -1/2*c0 + 1)])
        sage: _.base_ring()
        Number Field in c0 with defining polynomial x^2 - 2 with c0 = 1.414213562373095?

        sage: P(AA(1))
        Polygon(vertices=[(0, 0), (1, 0), (0.7071067811865475?, 0.2928932188134525?)])
        sage: _.base_ring()
        Algebraic Real Field

    Polygons can also be defined over a module containing transcendent parameters::

        sage: from pyexactreal import ExactReals # optional: exactreal  # random output due to deprecation warnings with some versions of pkg_resources
        sage: R = ExactReals(P.base_ring()) # optional: exactreal
        sage: P(R(1)) # optional: exactreal
        Polygon(vertices=[(0, 0), (1, 0), ((1/2*c0 ~ 0.70710678), (-1/2*c0+1 ~ 0.29289322))])
        sage: P(R(R.random_element([0.2, 0.3]))) # random output, optional: exactreal
        Polygon(vertices=[(0, 0),])
                 (ℝ(0.287373=2588422249976937p-53 + ℝ(0.120809…)p-54), 0),
                 (((12*c0+17 ~ 33.970563)*ℝ(0.287373=2588422249976937p-53 + ℝ(0.120809…)p-54))/((17*c0+24 ~ 48.041631)),
                 ((5*c0+7 ~ 14.071068)*ℝ(0.287373=2588422249976937p-53 + ℝ(0.120809…)p-54))/((17*c0+24 ~ 48.041631)))
        sage: _.base_ring() # optional: exactreal
        Real Numbers as (Real Embedded Number Field in c0 with defining polynomial x^2 - 2 with c0 = 1.414213562373095?)-Module

    ::

        sage: L = P.lengths_polytope()    # polytope of admissible lengths for edges
        sage: L
        A 1-dimensional polyhedron in (Number Field in c0 with defining polynomial x^2 - 2 with c0 = 1.414213562373095?)^3 defined as the convex hull of 1 vertex and 1 ray
        sage: lengths = L.rays()[0].vector()
        sage: lengths
        (1, -1/2*c0 + 1, -1/2*c0 + 1)
        sage: p = P(*lengths)    # build one polygon with the given lengths
        sage: p
        Polygon(vertices=[(0, 0), (1, 0), (1/2*c0, -1/2*c0 + 1)])
        sage: p.angles()
        (1/16, 1/8, 5/16)
        sage: P.angles(integral=False)
        (1/16, 1/8, 5/16)
        sage: P.angles(integral=True)
        (1, 2, 5)

        sage: P = EquiangularPolygons(1, 2, 1, 2, 2, 1)
        sage: L = P.lengths_polytope()
        sage: L
        A 4-dimensional polyhedron in (Number Field in c with defining polynomial x^6 - 6*x^4 + 9*x^2 - 3 with c = 1.969615506024417?)^6 defined as the convex hull of 1 vertex and 6 rays
        sage: rays = [r.vector() for r in L.rays()]
        sage: rays
        [(1, 0, 0, 0, -1/6*c^5 + 5/6*c^3 - 2/3*c, -1/6*c^5 + 5/6*c^3 - 2/3*c),
         (0, 1, 0, 0, c^2 - 3, c^2 - 2),
         (1/3*c^4 - 2*c^2 + 3, 0, -1/6*c^5 + 5/6*c^3 - 2/3*c, 0, 0, -1/6*c^5 + 5/6*c^3 - 2/3*c),
         (-c^4 + 4*c^2, 0, 0, -1/6*c^5 + 5/6*c^3 - 2/3*c, 0, -1/6*c^5 + 5/6*c^3 - 2/3*c),
         (0, 1/3*c^4 - 2*c^2 + 3, c^2 - 3, 0, 0, 1/3*c^4 - c^2),
         (0, -c^4 + 4*c^2, 0, c^2 - 3, 0, -c^4 + 5*c^2 - 3)]
        sage: lengths = 3*rays[0] + rays[2] + 2*rays[3] + rays[4]
        sage: p = P(*lengths)
        sage: p
        Polygon(vertices=[(0, 0),
                          (-5/3*c^4 + 6*c^2 + 6, 0),
                          (3*c^5 - 5/3*c^4 - 16*c^3 + 6*c^2 + 18*c + 6, c^4 - 6*c^2 + 9),
                          (2*c^5 - 2*c^4 - 10*c^3 + 15/2*c^2 + 9*c + 5, -1/2*c^5 + c^4 + 5/2*c^3 - 3*c^2 - 2*c),
                          (2*c^5 - 10*c^3 - 3/2*c^2 + 9*c + 9, -3/2*c^5 + c^4 + 15/2*c^3 - 3*c^2 - 6*c),
                          (2*c^5 - 10*c^3 - 3*c^2 + 9*c + 12, -3*c^5 + c^4 + 15*c^3 - 3*c^2 - 12*c)])

        sage: p.angles()
        (2/9, 4/9, 2/9, 4/9, 4/9, 2/9)

        sage: EquiangularPolygons(1, 2, 1, 2, 1, 2, 1, 2, 2, 2, 2, 1, 1, 2, 1)
        Category of real projective pentadecagons with angles (13/46, 13/23, 13/46, 13/23, 13/46, 13/23, 13/46, 13/23, 13/23, 13/23, 13/23, 13/46, 13/46, 13/23, 13/46) over Number Field in c with defining polynomial x^22 - 23*x^20 + 230*x^18 - 1311*x^16 + 4692*x^14 - 10948*x^12 + 16744*x^10 - 16445*x^8 + 9867*x^6 - 3289*x^4 + 506*x^2 - 23 with c = 1.995337538381079?

    A regular pentagon::

        sage: E = EquiangularPolygons(1, 1, 1, 1, 1)
        sage: E(1, 1, 1, 1, 1, normalized=True)
        doctest:warning
        ...
        UserWarning: calling EquiangularPolygons() has been deprecated and will be removed in a future version of sage-flatsurf; use Polygon(angles=[...], lengths=[...]) instead.
        Polygon(vertices=[(0, 0), (1, 0), (1/2*c^2 - 1/2, 1/2*c), (1/2, 1/2*c^3 - c), (-1/2*c^2 + 3/2, 1/2*c)])

    """
    if "number_field" in kwds:
        from warnings import warn

        warn(
            "The number_field parameter has been removed in this release of sage-flatsurf. "
            "To create an equiangular polygon over a number field, do not pass this parameter; to create an equiangular polygon over the algebraic numbers, do not pass this parameter but call the returned object with algebraic lengths."
        )
        kwds.pop("number_field")

    if kwds:
        raise ValueError("invalid keyword {!r}".format(next(iter(kwds))))

    if len(angles) == 1 and isinstance(angles[0], (tuple, list)):
        angles = angles[0]

    angles = RealProjectivePolygonsWithAngles._normalize_angles(angles)
    return _EuclideanPolygonsWithAngles(angles)


@cached_function
def _EuclideanPolygonsWithAngles(angles):
    base_ring = RealProjectivePolygonsWithAngles._base_ring(angles)
    return RealProjectivePolygons(base_ring).WithAngles(angles)


# TODO: Deprecate
EquiangularPolygons = EuclideanPolygonsWithAngles
