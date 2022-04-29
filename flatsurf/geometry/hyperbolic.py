r"""
Two dimensional hyperbolic geometry.

EXAMPLES::

    sage: from flatsurf.geometry.hyperbolic import HyperbolicPlane

    sage: H = HyperbolicPlane(QQ)

    TODO: More examples.

"""
######################################################################
#  This file is part of sage-flatsurf.
#
#        Copyright (C) 2022 Julian Rüth
#                      2022 Sam Freedman
#                      2022 Vincent Delecroix
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
######################################################################

from sage.structure.parent import Parent
from sage.structure.element import Element
from sage.structure.unique_representation import UniqueRepresentation
from sage.misc.decorators import options, rename_keyword
from sage.plot.primitive import GraphicPrimitive


class HyperbolicPlane(Parent, UniqueRepresentation):
    r"""
    The hyperbolic plane over a base ring.

    All objects in the plane must be specified over the given base ring. Note
    that, in some representations, objects might appear to live in a larger
    ring. E.g., when specifying a line by giving a center and the square of
    its radius in the half plane model, then the ideal endpoints of this line
    might have coordinates in the ring after adjoining a square root.

    The implemented elements of the plane are convex subsets such as (finite
    and infinite) points, geodesics, closed half planes, and closed convex
    polygons.

    ALGORITHM:

    We do not use a fixed representation of the hyperbolic plane internally but
    switch between the Poincaré half plane and the Klein model freely.

    For the Klein model, we use a unit disc centered at (0, 0). The map from
    the Poincaré half plane sends the imaginary unit `i` to the center at the
    origin, and sends 0 to (0, -1), 1 to (1, 0), -1 to (-1, 0) and infinity to
    (0, 1). The Möbius transformation

    .. MATH::

        z \mapsto \frac{z-i}{1 - iz}

    maps from the half plane model to the Poincaré disc model. We then
    post-compose this with the map that goes from the Poincaré disc model to
    the Klein disc model, which in polar coordinates sends

    .. MATH::

        (\phi, r)\mapsto \left(\phi, \frac{2r}{1 + r^2}\right).

    When we write this map out explicitly in Euclidean coordinates, we get

    .. MATH::

        (x, y) \mapsto \frac{1}{1 + x^2 + y^2}\left(2x, -1 + x^2 + y^2\right)

    and

    .. MATH::

        (x, y) \mapsto \frac{1}{1 - y}\left(x, \sqrt{1 - x^2 - y^2}\right),

    for its inverse.

    A geodesic in the Poincaré half plane is then given by an equation of the form

    .. MATH::

        a(x^2 + y^2) + bx + c = 0

    which converts to an equation in the Klein disc as

    .. MATH::

        (a + c) + bx + (a - c)y = 0.

    Conversely, a geodesic's equation in the Klein disc

    .. MATH::

        a + bx + cy = 0

    corresponds to the equation

    .. MATH::

        (a + c)(x^2 + y^2) + 2bx + (a - c) = 0

    in the Poincaré half plane model.

    Note that the intersection of two geodesics defined by coefficients in a
    field `K` in the Klein model has coordinates in `K` in the Klein model.
    This is not true of the Poincaré half plane model.

    INPUT:

    - ``base_ring`` -- a base ring for the coefficients defining the equations
      of geodesics in the plane; defaults to the rational field if not
      specified.

    - ``category`` -- the category for this object; if not specified, defaults
      to sets with partial maps. Note that we do not use metric spaces here
      since the elements of this space are convex subsets of the hyperbolic
      plane and not just points so the elements do not satisfy the assumptions
      of a metric space.

    EXAMPLES::

        sage: from flatsurf.geometry.hyperbolic import HyperbolicPlane

        sage: HyperbolicPlane()
        Hyperbolic Plane over Rational Field

    """

    @staticmethod
    def __classcall__(cls, base_ring=None, category=None):
        r"""
        Create the hyperbolic plane with normalized arguments to make it a
        unique SageMath parent.

        TESTS::

            sage: from flatsurf.geometry.hyperbolic import HyperbolicPlane

            sage: HyperbolicPlane() is HyperbolicPlane(QQ)
            True

        """
        from sage.all import QQ
        base_ring = base_ring or QQ

        from sage.categories.all import Sets
        category = category or Sets()

        return super(HyperbolicPlane, cls).__classcall__(cls, base_ring=base_ring, category=category)

    def __init__(self, base_ring, category):
        r"""
        Create the hyperbolic plane over ``base_ring``.

        TESTS::

            sage: from flatsurf.geometry.hyperbolic import HyperbolicPlane

            sage: TestSuite(HyperbolicPlane(QQ)).run()
            sage: TestSuite(HyperbolicPlane(AA)).run()

        """
        if not base_ring.is_exact():
            # Much of the implementation might work over ineaxct rings,
            # * we did not really worry about precision issues here so unit
            #   tests should be added to check that everything works.
            # * if +infinity is in the base ring, then there might be problems
            #   in the upper half plane model.
            # * if NaN can be represented in the base ring, then there might be
            #   problems in many places where we do not expect this to show up.
            raise NotImplementedError("hyperbolic plane only implemented over exact rings")

        super().__init__(category=category)
        self._base_ring = base_ring

    def _an_element_(self):
        r"""
        Return an element of the hyperbolic plane (mostly for testing.)

        EXAMPLES::

            sage: from flatsurf.geometry.hyperbolic import HyperbolicPlane

            sage: HyperbolicPlane().an_element()
            0

        """
        return self.real(0)

    def some_elements(self):
        r"""
        Return some representative convex subsets for automated testing.

        EXAMPLES::

            sage: from flatsurf.geometry.hyperbolic import HyperbolicPlane

            sage: HyperbolicPlane().some_elements()
            [{}, ∞, 0, 1, -1, ...]

        """
        # TODO: Return more elements.
        return [self.empty_set(),
                # Points
                self.infinity(),
                self.real(0),
                self.real(1),
                self.real(-1),
                # Geodesics
                self.vertical(1),
                self.half_circle(0, 1),
                self.half_circle(1, 3),
                # Half spaces
                self.vertical(0).left_half_space(),
                self.half_circle(0, 2).left_half_space(),
                ]

    def _element_constructor_(self, x):
        r"""
        Return ``x`` as an element of the hyperbolic plane.

        EXAMPLES::

            sage: from flatsurf.geometry.hyperbolic import HyperbolicPlane

            sage: H = HyperbolicPlane(QQ)
            sage: H(H.an_element()) in H
            True

        Base ring elements can be converted to ideal points::

            sage: H(1)
            1

        The point at infinity in the half plane model can be written directly::

            sage: H(oo)
            ∞

        Complex numbers in the upper half plane can be converted to points in
        the hyperbolic plane::

            sage: H(I)
            I

        Elements can be converted between hyperbolic planes with compatible base rings::

            sage: HyperbolicPlane(AA)(H(1))
            1

        """
        if x.parent() is self:
            return x

        from sage.all import Infinity
        if x is Infinity:
            return self.infinity()

        if x in self.base_ring():
            return self.real(x)

        if isinstance(x, HyperbolicConvexSet):
            return x.change_ring(self.base_ring())

        from sage.categories.all import NumberFields
        if x.parent() in NumberFields():
            K = x.parent()

            from sage.all import I
            if I not in K:
                raise NotImplementedError("cannot create a hyperbolic point from an element in a number field that does not contain the imaginary unit")

            return self.point(x.real(), x.imag(), model="half_plane")

        raise NotImplementedError("cannot create a subset of the hyperbolic plane from this element yet.")

    def base_ring(self):
        r"""
        Return the base ring over which objects in the plane are defined.

        EXAMPLES::

            sage: from flatsurf.geometry.hyperbolic import HyperbolicPlane

            sage: HyperbolicPlane().base_ring()
            Rational Field

        """
        return self._base_ring

    def infinity(self):
        r"""
        Return the point at infinity in the Poincaré half plane model.

        EXAMPLES::

            sage: from flatsurf.geometry.hyperbolic import HyperbolicPlane

            sage: HyperbolicPlane().infinity()
            ∞

        """
        return self.projective(1, 0)

    def real(self, r):
        r"""
        Return the ideal point ``r`` on the real axis in the Poincaré half
        plane model.

        EXAMPLES::

            sage: from flatsurf.geometry.hyperbolic import HyperbolicPlane

            sage: HyperbolicPlane().real(-2)
            -2

        """
        return self.projective(r, 1)

    def projective(self, p, q):
        r"""
        Return the ideal point with projective coordinates ``[p: q]`` in the
        Poincaré half plane model.

        EXMAPLES::

            sage: from flatsurf.geometry.hyperbolic import HyperbolicPlane

            sage: H = HyperbolicPlane()
            sage: H.projective(0, 1)
            0

            sage: H.projective(-1, 0)
            ∞

            sage: H.projective(0, 0)
            Traceback (most recent call last):
            ...
            ValueError: one of p and q must not be zero

        """
        if p == 0 and q == 0:
            raise ValueError("one of p and q must not be zero")

        if q == 0:
            return self.point(0, 1, model="klein")

        p = self.base_ring()(p)
        q = self.base_ring()(q)

        return self.point(p/q, 0, model="half_plane")

    def point(self, x, y, model, check=True):
        r"""
        Return the point with coordinates (x, y) in the given model.

        When ``model`` is ``"half_plane"``, return the point `x + iy` in the upper half plane.

        When ``model`` is ``"klein"``, return the point (x, y) in the Klein disc.

        EXAMPLES::

            sage: from flatsurf.geometry.hyperbolic import HyperbolicPlane
            sage: H = HyperbolicPlane()

            sage: H.point(0, 1, model="half_plane")
            I

            sage: H.point(1, 2, model="half_plane")
            1 + 2*I

            sage: H.point(0, 1, model="klein")
            ∞

        """
        x = self.base_ring()(x)
        y = self.base_ring()(y)

        if model == "klein":
            return self.__make_element_class__(HyperbolicPoint)(self, x, y, check=check)
        if model == "half_plane":
            denominator = 1 + x*x + y*y
            return self.point(
                x=2*x / denominator,
                y=(-1 + x*x + y*y) / denominator,
                model="klein")

        raise NotImplementedError("unsupported model")

    def half_circle(self, center, radius_squared):
        r"""
        Return the geodesic centered around the real ``center`` and with
        ``radius_squared`` in the Poincaré half plane model. The geodesic is
        oriented such that the point at infinity is to its left.

        Use the ``-`` operator to pass to the geodesic with opposite
        orientation.

        EXAMPLES::

            sage: from flatsurf.geometry.hyperbolic import HyperbolicPlane
            sage: H = HyperbolicPlane()

            sage: H.half_circle(0, 1)
            {(x^2 + y^2) - 1 = 0}

            sage: H.half_circle(1, 3)
            {(x^2 + y^2) - 2*x - 2 = 0}

            sage: H.half_circle(1/3, 1/2)
            {18*(x^2 + y^2) - 12*x - 7 = 0}

        TESTS::

            sage: H.half_circle(0, 0)
            Traceback (most recent call last):
            ...
            ValueError: radius must be positive

            sage: H.half_circle(0, -1)
            Traceback (most recent call last):
            ...
            ValueError: radius must be positive

            sage: H.half_circle(oo, 1)
            Traceback (most recent call last):
            ...
            TypeError: unable to convert +Infinity to a rational

        """
        center = self.base_ring()(center)
        radius_squared = self.base_ring()(radius_squared)

        if radius_squared <= 0:
            raise ValueError("radius must be positive")

        # Represent this geodesic as a(x^2 + y^2) + b*x + c = 0
        a = 1
        b = -2*center
        c = center*center - radius_squared

        return self.geodesic(a, b, c, model="half_plane")

    def vertical(self, real):
        r"""
        Return the vertical geodesic at the ``real`` ideal point in the
        Poincaré half plane model. The geodesic is oriented such that it goes
        from ``real`` to the point at infinity.

        Use the ``-`` operator to pass to the geodesic with opposite
        orientation.

        EXAMPLES::

            sage: from flatsurf.geometry.hyperbolic import HyperbolicPlane
            sage: H = HyperbolicPlane()

            sage: H.vertical(0)
            {-x = 0}

            sage: H.vertical(1)
            {-x + 1 = 0}

            sage: H.vertical(-1)
            {-x - 1 = 0}

        """
        real = self.base_ring()(real)

        # Convert the equation -x + real = 0 to the Klein model.
        return self.geodesic(real, -1, -real, model="klein")

    def geodesic(self, a, b, c=None, model=None, check=True):
        r"""
        Return a geodesic in the hyperbolic plane.

        If only ``a`` and ``b`` are given, return the geodesic going through the points
        ``a`` and then ``b``.

        If ``c`` is specified and ``model`` is ``"half_plane"``, return the
        geodesic given by the half circle

        .. MATH::

            a(x^2 + y^2) + bx + c = 0

        oriented such that the half plane

        .. MATH::

            a(x^2 + y^2) + bx + c \ge 0

        is to its left.

        If ``c`` is specified and ``model`` is ``"klein"``, return the
        geodesic given by the chord with the equation

        .. MATH::

            a + bx + cy = 0

        oriented such that the half plane

        .. MATH::

            a + bx + cy \ge 0

        is to its left.

        EXAMPLES::

            sage: from flatsurf.geometry.hyperbolic import HyperbolicPlane
            sage: H = HyperbolicPlane()

            sage: H.geodesic(-1, 1)
            {(x^2 + y^2) - 1 = 0}

            sage: H.geodesic(0, I)
            {-x = 0}

            sage: H.geodesic(-1, I + 1)
            {2*(x^2 + y^2) - x - 3 = 0}

            sage: H.geodesic(2, -1, -3, model="half_plane")
            {2*(x^2 + y^2) - x - 3 = 0}

            sage: H.geodesic(-1, -1, 5, model="klein")
            {2*(x^2 + y^2) - x - 3 = 0}

        TESTS::

            sage: H.geodesic(0, 0)
            Traceback (most recent call last):
            ...
            ValueError: points specifying a geodesic must be distinct

        """
        if c is None:
            a = self(a)
            b = self(b)

            if a == b:
                raise ValueError("points specifying a geodesic must be distinct")

            C = b._x - a._x
            B = a._y - b._y
            A = -(B * a._x + C * a._y)

            return self.geodesic(A, B, C, model="klein", check=check)

        if model is None:
            raise ValueError("a model must be specified when specifying a geodesic with coefficients")

        if model == "half_plane":
            # Convert to the Klein model.
            return self.geodesic(a + c, b, a - c, model="klein")

        if model == "klein":
            a = self.base_ring()(a)
            b = self.base_ring()(b)
            c = self.base_ring()(c)
            return self.__make_element_class__(HyperbolicGeodesic)(self, a, b, c, check=check)

        raise NotImplementedError("cannot create geodesic from coefficients in this model")

    def half_space(self, a, b, c, model, check=True):
        r"""
        Return a closed half space from its equation in ``model``.

        If ``model`` is ``"half_plane"``, return the half space

        .. MATH::

            a(x^2 + y^2) + bx + c \ge 0

        in the upper half plane.

        If ``model`` is ``"klein"``, return the half space

        .. MATH::

            a + bx + cy \ge 0

        in the Klein model.

        ..SEEALSO::

            :meth:`HperbolicGeodesic.left_half_space`
            :meth:`HperbolicGeodesic.right_half_space`

        EXAMPLES::

            sage: from flatsurf.geometry.hyperbolic import HyperbolicPlane
            sage: H = HyperbolicPlane()

            sage: H.half_space(0, -1, 0, model="half_plane")
            {x ≤ 0}

        It is often easier to construct a half space as the space bounded by a geodesic::

            sage: H.vertical(0).left_half_space()
            {x ≤ 0}

        """
        return self.__make_element_class__(HyperbolicHalfSpace)(self, self.geodesic(a, b, c, model=model, check=check))

    def segment(self, geodesic, start=None, end=None, check=True):
        return self.__make_element_class__(HyperbolicEdge)(self, geodesic, start, end, check=check)

    def intersection(self, *subsets):
        r"""
        Return the intersection of convex ``subsets``.

        ALGORITHM:

        We compute the intersection of the
        :meth:`HyperbolicConvexSet._half_spaces` that make up the ``subsets``.
        That intersection can be computed in the Klein model where we can
        essentially reduce this problem to the intersection of half spaces in
        the Euclidean plane.

        The Euclidean intersection problem can be solved in time linear in the
        number of half spaces assuming that the half spaces are already sorted
        in a certain way. In particular, this is the case if there is only a
        constant number of ``subsets``. Otherwise, the algorithm is
        quasi-linear in the number of half spaces due to the added complexity
        of sorting.

        See :meth:`_reduce` for more algorithmic details.

        EXAMPLES::

            sage: from flatsurf.geometry.hyperbolic import HyperbolicPlane
            sage: H = HyperbolicPlane()

            sage: H.intersection(H.vertical(0).left_half_space())
            {x ≤ 0}

            sage: H.intersection(H.vertical(0).left_half_space(), H.vertical(0).right_half_space())
            {x = 0}

        """
        subsets = [self.coerce(subset) for subset in subsets]

        half_spaces = [subset._half_spaces() for subset in subsets]

        half_spaces = HyperbolicPlane._merge_sort(*half_spaces)

        return self._reduce(half_spaces)

    @classmethod
    def _merge_sort(cls, *half_spaces):
        r"""
        Return the merge of lists of ``half_spaces``.

        The lists are assumed to be sorted by
        :meth:`HyperbolicHalfSpace._normal_lt` and are merged into a single
        list with that sorting.

        Naturally, when there are a lot of short lists, such a merge sort takes
        quasi-linear time. However, when there are only a few lists, this runs
        in linear time.

        EXAMPLES::

            sage: from flatsurf.geometry.hyperbolic import HyperbolicPlane
            sage: H = HyperbolicPlane()

            sage: HyperbolicPlane._merge_sort()
            []

            sage: HyperbolicPlane._merge_sort(H.real(0)._half_spaces())
            [{(x^2 + y^2) + x ≤ 0}, {x ≥ 0}]

            sage: HyperbolicPlane._merge_sort(H.real(0)._half_spaces(), H.real(0)._half_spaces())
            [{(x^2 + y^2) + x ≤ 0}, {(x^2 + y^2) + x ≤ 0}, {x ≥ 0}, {x ≥ 0}]

            sage: HyperbolicPlane._merge_sort(*[[half_space] for half_space in H.real(0)._half_spaces() * 2])
            [{(x^2 + y^2) + x ≤ 0}, {(x^2 + y^2) + x ≤ 0}, {x ≥ 0}, {x ≥ 0}]

        """
        count = len(half_spaces)

        if count == 0:
            return []

        if count == 1:
            return half_spaces[0]

        # The non-trivial base case.
        if count == 2:
            A = half_spaces[0]
            B = half_spaces[1]
            merged = []

            while A and B:
                if HyperbolicHalfSpace._normal_lt(A[-1], B[-1]):
                    merged.append(B.pop())
                else:
                    merged.append(A.pop())

            merged.reverse()

            return A + B + merged

        # Divide & Conquer recursively.
        return HyperbolicPlane._merge_sort(*(
            HyperbolicPlane._merge_sort(*half_spaces[: count // 2]),
            HyperbolicPlane._merge_sort(*half_spaces[count // 2:])
            ))

    # TODO: Move everything related to _reduce to HyperbolicConvexPolygon.
    # TODO: Add examples.
    def _reduce(self, half_spaces):
        r"""
        Return a convex set describing the intersection of ``half_spaces``.

        The ``half_spaces`` are assumed to be sorted by :meth:`HyperbolicHalfSpace._normal_lt`.

        ALGORITHM:

        We compute the intersection of the half spaces in the Klein model in several steps:

        * Drop trivially redundant half spaces, e.g., repeated ones.
        * Handle the case that the intersection is empty or a single point, see :meth:`_reduce_euclidean_non_empty`.
        * Compute the intersection of the corresponding half spaces in the Euclidean plane, see :meth:`_reduce_euclidean`.
        * Remove redundant half spaces that make no contribution for the unit disk of the Klein model, see :meth:`_reduce_unit_disk`.
        * Determine of which nature (point, segment, line, polygon) the intersection of half spaces is and return the resulting set.

        """
        half_spaces = self._reduce_trivially_redundant(half_spaces)

        if not half_spaces:
            raise NotImplementedError("cannot model intersection of no half spaces yet")

        # Find a segment on the boundary of the intersection.
        boundary = self._reduce_euclidean_non_empty(half_spaces, assume_sorted=True)

        if not isinstance(boundary, HyperbolicHalfSpace):
            # When there was no such segment, i.e., the intersection is empty
            # or just a point, we are done.
            return boundary

        # Compute a minimal subset of the half spaces that defines the intersection in the Euclidean plane.
        half_spaces = self._reduce_euclidean(half_spaces, boundary, assume_sorted=True)

        # Remove half spaces that make no contribution when restricting to the unit disk of the Klein model.
        half_spaces = self._reduce_unit_disk(half_spaces, assume_sorted=True)

        if isinstance(half_spaces, HyperbolicConvexSet):
            return half_spaces

        # Return the intersection as a proper hyperbolic convex set.
        return self._intersection(half_spaces, assume_non_empty=True, assume_sorted=True, assume_no_point=True, assume_minimal=True)

    # TODO: Move reduce methods to specific subsets.
    def _reduce_trivially_redundant(self, half_spaces):
        r"""
        Return a sublist of ``half_spaces`` without changing their intersection
        by removing some trivially redundant half spaces.

        The ``half_spaces`` are assumed to be sorted consistent with :meth:`_normal_lt`.

        EXAMPLES::

            sage: from flatsurf.geometry.hyperbolic import HyperbolicPlane
            sage: H = HyperbolicPlane()

        Repeated half spaces are removed::

            sage: H._reduce_trivially_redundant([H.vertical(0).left_half_space(), H.vertical(0).left_half_space()])
            [{x ≤ 0}]

        Inclusions of half spaces are simplified::

            sage: H._reduce_trivially_redundant([H.vertical(0).left_half_space(), H.geodesic(1/2, 2).left_half_space()])
            [{x ≤ 0}]

        But only if the inclusion is already present when extending the half
        space from the Klein disk to the entire Euclidean plane::

            sage: H._reduce_trivially_redundant([H.vertical(0).left_half_space(), H.vertical(1).left_half_space()])
            [{x ≤ 0}, {x - 1 ≤ 0}]

        """
        reduced = []

        for half_space in half_spaces:
            if reduced:
                a, b, c = half_space.equation(model="klein")
                A, B, C = reduced[-1].equation(model="klein")

                if c * B == C * b and b.sign() == B.sign() and c.sign() == C.sign():
                    # The half spaces are parallel in the Euclidean plane. Since we
                    # assume spaces to be sorted by inclusion, we can drop this
                    # space.
                    continue

            reduced.append(half_space)

        return reduced

    def _reduce_euclidean_non_empty(self, half_spaces, assume_sorted=False):
        r"""
        Return a half space whose (Euclidean) boundary intersects the boundary
        of the intersection of ``half_spaces`` in more than a point.

        Consider the half spaces in the Klein model. Ignoring the unit disk,
        they also describe half spaces in the Euclidean plane.

        If their intersection contains a segment it must be on the boundary of
        one of the ``half_spaces`` which is returned by this method.

        If this is not the case, and the intersection is empty in the
        hyperbolic plane, return the :meth:`empty_set`. Otherwise, if the
        intersection is a point in the hyperbolic plane, return that point.

        The ``half_spaces`` must be sorted with respect to
        :meth:`HyperbolicHalfSpace._normal_lt`.

        ALGORITHM:

        We initially ignore the hyperbolic structure and just consider the half
        spaces of the Klein model as Euclidean half spaces.

        We use a relatively standard randomized optimization approach to find a
        point in the intersection: we randomly shuffle the half spaces and then
        optimize a segment on some boundary of the half spaces. The
        randomization makes this a linear time algorithm, see e.g.,
        https://www2.cs.arizona.edu/classes/cs437/fall07/Lecture4.prn.pdf

        If the only segment we can construct is a point, then the intersection
        is a single point in the Euclidean plane. The interesction in the
        hyperbolic plane might be a single point or empty.

        If not even a point exists, the intersection is empty in the Euclidean
        plane and therefore empty in the hyperbolic plane.

        Note that the segment returned might not be within the unit disk.

        EXAMPLES::

            sage: from flatsurf.geometry.hyperbolic import HyperbolicPlane
            sage: H = HyperbolicPlane()

        Make the following randomized tests reproducible::

            sage: from random import seed
            sage: seed(0R)

        An intersection that is already empty in the Euclidean plane::

            sage: H._reduce_euclidean_non_empty([
            ....:     H.geodesic(2, 1/2).left_half_space(),
            ....:     H.geodesic(-1/2, -2).left_half_space()
            ....: ])
            {}

        An intersection which in the Euclidean plane is a single point but
        outside the unit disk::

            sage: H._reduce_euclidean_non_empty([
            ....:     H.half_space(0, 1, 0, model="klein"),
            ....:     H.half_space(0, -1, 0, model="klein"),
            ....:     H.half_space(2, 2, -1, model="klein"),
            ....:     H.half_space(-2, -2, 1, model="klein"),
            ....: ])
            {}

        An intersection which is a single point inside the unit disk::

            sage: H._reduce_euclidean_non_empty(H(I)._half_spaces())
            I

        An intersection which is a single point on the boundary of the unit
        disk::

            sage: H._reduce_euclidean_non_empty(H.infinity()._half_spaces())
            {x - 1 ≥ 0}

        An intersection which is a segment outside of the unit disk::

            sage: H._reduce_euclidean_non_empty([
            ....:     H.vertical(0).left_half_space(),
            ....:     H.vertical(0).right_half_space(),
            ....:     H.half_space(-2, -2, 1, model="klein"),
            ....:     H.half_space(17/8, 2, -1, model="klein"),
            ....: ])
            {x ≤ 0}

        An intersection which is a polygon outside of the unit disk::

            sage: H._reduce_euclidean_non_empty([
            ....:     H.half_space(0, 1, 0, model="klein"),
            ....:     H.half_space(1, -2, 0, model="klein"),
            ....:     H.half_space(-2, -2, 1, model="klein"),
            ....:     H.half_space(17/8, 2, -1, model="klein"),
            ....: ])
            {(x^2 + y^2) - 4*x + 1 ≥ 0}

        An intersection which is an (unbounded) polygon touching the unit disk::

            sage: H._reduce_euclidean_non_empty([
            ....:     H.vertical(-1).left_half_space(),
            ....:     H.vertical(1).right_half_space(),
            ....: ])
            {x - 1 ≥ 0}

        An intersection which is a segment touching the unit disk::

            sage: H._reduce_euclidean_non_empty([
            ....:     H.vertical(0).left_half_space(),
            ....:     H.vertical(0).right_half_space(),
            ....:     H.vertical(-1).left_half_space(),
            ....:     H.geodesic(-1, -2).right_half_space(),
            ....: ])
            {x ≥ 0}

        An intersection which is a polygon inside the unit disk::

            sage: H._reduce_euclidean_non_empty([
            ....:     H.vertical(1).left_half_space(),
            ....:     H.vertical(-1).right_half_space(),
            ....:     H.geodesic(0, -1).right_half_space(),
            ....:     H.geodesic(0, 1).left_half_space(),
            ....: ])
            {(x^2 + y^2) + x ≥ 0}

        A polygon which has no vertices inside the unit disk but intersects the unit disk::

            sage: H._reduce_euclidean_non_empty([
            ....:     H.geodesic(2, 3).left_half_space(),
            ....:     H.geodesic(-3, -2).left_half_space(),
            ....:     H.geodesic(-1/2, -1/3).left_half_space(),
            ....:     H.geodesic(1/3, 1/2).left_half_space(),
            ....: ])
            {6*(x^2 + y^2) - 5*x + 1 ≥ 0}

        A single half plane::

            sage: H._reduce_euclidean_non_empty([
            ....:     H.vertical(0).left_half_space()
            ....: ])
            {x ≤ 0}

        A pair of anti-parallel half planes::

            sage: H._reduce_euclidean_non_empty([
            ....:     H.geodesic(1/2, 2).left_half_space(),
            ....:     H.geodesic(-1/2, -2).right_half_space(),
            ....: ])
            {2*(x^2 + y^2) - 5*x + 2 ≥ 0}

        """
        if len(half_spaces) == 0:
            raise ValueError("list of half spaces must not be empty")

        if len(half_spaces) == 1:
            return half_spaces[0]

        # Randomly shuffle the half spaces so the loop below runs in expected linear time.
        from random import shuffle
        random_half_spaces = half_spaces[:]
        shuffle(random_half_spaces)

        # Move from the random starting point to a point that is contained in all half spaces.
        point = random_half_spaces[0].boundary().an_element()

        for half_space in random_half_spaces:
            if point in half_space:
                continue
            else:
                # The point is not in this half space. Find a point on the
                # boundary of half_space that is contained in all the half
                # spaces we have seen so far.
                boundary = half_space.boundary()

                # We parametrize the boundary points of half space, i.e., the
                # points that satisfy a + bx + cy = 0 by picking a base point B
                # and then writing points as (x, y) = B + λ(c, -b).

                # Each half space constrains the possible values of λ, starting
                # from (-∞,∞) to a smaller closed interval.
                from sage.all import RealSet
                interval = RealSet.real_line()

                for constraining in random_half_spaces:
                    if constraining is half_space:
                        break

                    intersection = boundary._intersection(constraining.boundary())

                    if intersection is None:
                        # constraining is anti-parallel to half_space
                        if boundary.parametrize(0, model="euclidean", check=False) not in constraining:
                            return self.empty_set()

                        # The intersection is non-empty, so this adds no further constraints.
                        continue

                    λ = boundary.parametrize(intersection, model="euclidean", check=False)

                    # Determine whether this half space constrains to (-∞, λ] or [λ, ∞).
                    if boundary.parametrize(λ + 1, model="euclidean", check=False) in constraining:
                        constraint = RealSet.unbounded_above_closed(λ)
                    else:
                        constraint = RealSet.unbounded_below_closed(λ)

                    interval = interval.intersection(constraint)

                    if interval.is_empty():
                        # The constraints leave no possibility for λ.
                        return self.empty_set()

                # Construct a point from any of the λ in interval.
                λ = interval.an_element()

                point = boundary.parametrize(λ, model="euclidean", check=False)

        if not assume_sorted:
            half_spaces = HyperbolicPlane._merge_sort(*[[half_space] for half_space in half_spaces])

        # Extend the point to a segment
        for (i, half_space) in enumerate(half_spaces):
            if point not in half_space.boundary():
                continue

            following = half_spaces[(i + 1) % len(half_spaces)]
            if half_space.boundary().parametrize(
                  half_space.boundary().parametrize(point, model="euclidean", check=False) + 1,
                  model="euclidean",
                  check=False) in following:
                return half_space

            intersection = half_space.boundary()._intersection(following.boundary())

            assert intersection is not None, "The boundaries do not intersect so they must be anti-parallel. However, the previous check found that the half spaces do not contain the same points."

            if intersection == point:
                continue

            for constraining in random_half_spaces:
                if intersection not in constraining:
                    break
            else:
                return half_space

        # The point is the only point in the intersection.
        x, y = point.coordinates(model="klein")

        if x*x + y*y > 1:
            # The point is only ultra ideal, there is no actual intersection.
            return self.empty_set()

        return point

    def _reduce_euclidean(self, half_spaces, boundary, assume_sorted=False):
        r"""
        Return a minimal sublist of ``half_spaces`` that describe their
        intersection as half spaces of the Euclidean plane.

        Consider the half spaces in the Klein model. Ignoring the unit disk,
        they also describe half spaces in the Euclidean plane.

        The half space ``boundary`` must be one of the ``half_spaces`` that
        defines a boundary edge of the intersection polygon in the Euclidean
        plane.

        ALGORITHM:

        We use an approach similar to gift-wrapping (but from the inside) to remove
        redundant half spaces from the input list. We start from the
        ``boundary`` which is one of the minimal half spaces and extend to the
        full intersection by walking the sorted half spaces.

        Since we visit each half space once, this reduction runs in linear time
        in the number of half spaces.

        EXAMPLES::

            sage: from flatsurf.geometry.hyperbolic import HyperbolicPlane
            sage: H = HyperbolicPlane()

        An intersection which is a single point on the boundary of the unit
        disk::

            sage: H._reduce_euclidean(
            ....:     half_spaces=H.infinity()._half_spaces(),
            ....:     boundary=H.vertical(1).right_half_space())
            [{x - 1 ≥ 0}, {x ≤ 0}]

        An intersection which is a segment outside of the unit disk::

            sage: H._reduce_euclidean([
            ....:     H.vertical(0).left_half_space(),
            ....:     H.vertical(0).right_half_space(),
            ....:     H.half_space(-2, -2, 1, model="klein"),
            ....:     H.half_space(17/8, 2, -1, model="klein"),
            ....: ], boundary=H.vertical(0).left_half_space())
            [{x ≤ 0},
             {9*(x^2 + y^2) + 32*x + 25 ≥ 0},
             {x ≥ 0},
             {(x^2 + y^2) + 4*x + 3 ≤ 0}]

        An intersection which is a polygon outside of the unit disk::

            sage: H._reduce_euclidean([
            ....:     H.half_space(0, 1, 0, model="klein"),
            ....:     H.half_space(1, -2, 0, model="klein"),
            ....:     H.half_space(-2, -2, 1, model="klein"),
            ....:     H.half_space(17/8, 2, -1, model="klein"),
            ....: ], boundary=H.half_space(17/8, 2, -1, model="klein"))
            [{9*(x^2 + y^2) + 32*x + 25 ≥ 0},
             {x ≥ 0},
             {(x^2 + y^2) + 4*x + 3 ≤ 0},
             {(x^2 + y^2) - 4*x + 1 ≥ 0}]

        An intersection which is an (unbounded) polygon touching the unit disk::

            sage: H._reduce_euclidean([
            ....:     H.vertical(-1).left_half_space(),
            ....:     H.vertical(1).right_half_space(),
            ....: ], boundary=H.vertical(1).right_half_space())
            [{x - 1 ≥ 0}, {x + 1 ≤ 0}]

        An intersection which is a segment touching the unit disk::

            sage: H._reduce_euclidean([
            ....:     H.vertical(0).left_half_space(),
            ....:     H.vertical(0).right_half_space(),
            ....:     H.vertical(-1).left_half_space(),
            ....:     H.geodesic(-1, -2).right_half_space(),
            ....: ], boundary=H.vertical(0).left_half_space())
            [{x ≤ 0}, {(x^2 + y^2) + 3*x + 2 ≥ 0}, {x ≥ 0}, {x + 1 ≤ 0}]

        An intersection which is a polygon inside the unit disk::

            sage: H._reduce_euclidean([
            ....:     H.vertical(1).left_half_space(),
            ....:     H.vertical(-1).right_half_space(),
            ....:     H.geodesic(0, -1).right_half_space(),
            ....:     H.geodesic(0, 1).left_half_space(),
            ....: ], boundary=H.geodesic(0, 1).left_half_space())
            [{(x^2 + y^2) - x ≥ 0}, {x - 1 ≤ 0}, {x + 1 ≥ 0}, {(x^2 + y^2) + x ≥ 0}]

        A polygon which has no vertices inside the unit disk but intersects the unit disk::

            sage: H._reduce_euclidean([
            ....:     H.geodesic(2, 3).left_half_space(),
            ....:     H.geodesic(-3, -2).left_half_space(),
            ....:     H.geodesic(-1/2, -1/3).left_half_space(),
            ....:     H.geodesic(1/3, 1/2).left_half_space(),
            ....: ], boundary=H.geodesic(1/3, 1/2).left_half_space())
            [{6*(x^2 + y^2) - 5*x + 1 ≥ 0},
             {(x^2 + y^2) - 5*x + 6 ≥ 0},
             {(x^2 + y^2) + 5*x + 6 ≥ 0},
             {6*(x^2 + y^2) + 5*x + 1 ≥ 0}]

        A single half plane::

            sage: H._reduce_euclidean([
            ....:     H.vertical(0).left_half_space()
            ....: ], boundary=H.vertical(0).left_half_space())
            [{x ≤ 0}]

        A pair of anti-parallel half planes::

            sage: H._reduce_euclidean([
            ....:     H.geodesic(1/2, 2).left_half_space(),
            ....:     H.geodesic(-1/2, -2).right_half_space(),
            ....: ], boundary=H.geodesic(-1/2, -2).right_half_space())
            [{2*(x^2 + y^2) + 5*x + 2 ≥ 0}, {2*(x^2 + y^2) - 5*x + 2 ≥ 0}]

        A segment in the unit disk with several superfluous half planes at infinity::

            sage: H._reduce_euclidean([
            ....:     H.vertical(0).left_half_space(),
            ....:     H.vertical(0).right_half_space(),
            ....:     H.vertical(1).left_half_space(),
            ....:     H.vertical(1/2).left_half_space(),
            ....:     H.vertical(1/3).left_half_space(),
            ....:     H.vertical(1/4).left_half_space(),
            ....:     H.vertical(-1).right_half_space(),
            ....:     H.vertical(-1/2).right_half_space(),
            ....:     H.vertical(-1/3).right_half_space(),
            ....:     H.vertical(-1/4).right_half_space(),
            ....: ], boundary=H.vertical(0).left_half_space())
            [{x ≤ 0}, {4*x + 1 ≥ 0}, {x ≥ 0}]

        A polygon in the unit disk with several superfluous half planes::

            sage: H._reduce_euclidean([
            ....:     H.vertical(1).left_half_space(),
            ....:     H.vertical(-1).right_half_space(),
            ....:     H.geodesic(0, 1).left_half_space(),
            ....:     H.geodesic(0, -1).right_half_space(),
            ....:     H.vertical(2).left_half_space(),
            ....:     H.vertical(-2).right_half_space(),
            ....:     H.geodesic(0, 1/2).left_half_space(),
            ....:     H.geodesic(0, -1/2).right_half_space(),
            ....:     H.vertical(3).left_half_space(),
            ....:     H.vertical(-3).right_half_space(),
            ....:     H.geodesic(0, 1/3).left_half_space(),
            ....:     H.geodesic(0, -1/3).right_half_space(),
            ....: ], boundary=H.vertical(1).left_half_space())
            [{x - 1 ≤ 0}, {x + 1 ≥ 0}, {(x^2 + y^2) + x ≥ 0}, {(x^2 + y^2) - x ≥ 0}]

        """
        # TODO: Make all other assumptions clear in the interface.

        if not assume_sorted:
            half_spaces = HyperbolicPlane._merge_sort(*[[half_space] for half_space in half_spaces])

        half_spaces = half_spaces[half_spaces.index(boundary):] + half_spaces[:half_spaces.index(boundary)]
        half_spaces.reverse()

        required_half_spaces = [half_spaces.pop()]

        while half_spaces:
            A = required_half_spaces[-1]
            B = half_spaces.pop()
            C = half_spaces[-1] if half_spaces else required_half_spaces[0]

            # Determine whether B is redundant, i.e., whether the intersection
            # A, B, C and A, C are the same.
            # Since we know that A is required and the space non-empty, the
            # question here is whether C blocks the line of sight from A to B.

            # We distinguish cases, depending of the nature of the intersection of A and B.
            AB = A.boundary()._configuration(B.boundary())
            BC = B.boundary()._configuration(C.boundary())
            AC = A.boundary()._configuration(C.boundary())

            if AB == "convex":
                if BC == "concave":
                    assert AC in ["equal", "concave"]
                    required_half_spaces.append(B)

                elif BC == "convex":
                    BC = B.boundary()._intersection(C.boundary())
                    if AC == "negative" or (BC in A and BC not in A.boundary()):
                        required_half_spaces.append(B)

                elif BC == "negative":
                    required_half_spaces.append(B)

                else:
                    raise NotImplementedError(f"B and C are in unsupported configuration: {BC}")

            elif AB == "negative":
                required_half_spaces.append(B)

            elif AB == "anti-parallel":
                required_half_spaces.append(B)

            else:
                raise NotImplementedError(f"A and B are in unsupported configuration: {AB}")

        return required_half_spaces

    def _reduce_unit_disk(self, half_spaces, assume_sorted=False):
        r"""
        Return the intersection of the Euclidean ``half_spaces`` with the unit
        disk.

        The ``half_spaces`` must be minimal to describe their intersection in
        the Euclidean plane. If that intersection does not intersect the unit
        disk, then return the :meth:`empty_set`.

        Otherwise, return a minimal sublist of ``half_spaces`` that describes
        the intersection inside the unit disk.

        ALGORITHM:

        When passing to the Klein disk, i.e., intersecting the polygon with the
        unit disk, some of the edges of the (possibly unbounded) polygon
        described by the ``half_spaces`` are unnecessary because they are not
        intersecting the unit disk.

        If none of the edges intersect the unit disk, then the polygon has
        empty intersection with the unit disk.

        Otherwise, we can drop the half spaces describing the edges that do not
        intersect the unit disk.

        EXAMPLES::

            sage: from flatsurf.geometry.hyperbolic import HyperbolicPlane
            sage: H = HyperbolicPlane()

        An intersection which is a single point on the boundary of the unit
        disk::

            sage: H._reduce_unit_disk(half_spaces=H.infinity()._half_spaces())
            ∞

        An intersection which is a segment outside of the unit disk::

            sage: H._reduce_unit_disk([
            ....:     H.vertical(0).left_half_space(),
            ....:     H.vertical(0).right_half_space(),
            ....:     H.half_space(-2, -2, 1, model="klein"),
            ....:     H.half_space(17/8, 2, -1, model="klein"),
            ....: ])
            {}

        An intersection which is a polygon outside of the unit disk::

            sage: H._reduce_unit_disk([
            ....:     H.half_space(0, 1, 0, model="klein"),
            ....:     H.half_space(1, -2, 0, model="klein"),
            ....:     H.half_space(-2, -2, 1, model="klein"),
            ....:     H.half_space(17/8, 2, -1, model="klein"),
            ....: ])
            {}

        An intersection which is an (unbounded) polygon touching the unit disk::

            sage: H._reduce_unit_disk([
            ....:     H.vertical(-1).left_half_space(),
            ....:     H.vertical(1).right_half_space()])
            ∞

        An intersection which is a segment touching the unit disk::

            sage: H._reduce_unit_disk([
            ....:     H.vertical(0).left_half_space(),
            ....:     H.vertical(0).right_half_space(),
            ....:     H.vertical(-1).left_half_space(),
            ....:     H.geodesic(-1, -2).right_half_space()])
            ∞

        An intersection which is a polygon inside the unit disk::

            sage: H._reduce_unit_disk([
            ....:     H.vertical(1).left_half_space(),
            ....:     H.vertical(-1).right_half_space(),
            ....:     H.geodesic(0, -1).right_half_space(),
            ....:     H.geodesic(0, 1).left_half_space()])
            {(x^2 + y^2) - x ≥ 0} ∩ {x - 1 ≤ 0} ∩ {x + 1 ≥ 0} ∩ {(x^2 + y^2) + x ≥ 0}

        A polygon which has no vertices inside the unit disk but intersects the unit disk::

            sage: H._reduce_unit_disk([
            ....:     H.geodesic(2, 3).left_half_space(),
            ....:     H.geodesic(-3, -2).left_half_space(),
            ....:     H.geodesic(-1/2, -1/3).left_half_space(),
            ....:     H.geodesic(1/3, 1/2).left_half_space()])
            {6*(x^2 + y^2) - 5*x + 1 ≥ 0} ∩ {(x^2 + y^2) - 5*x + 6 ≥ 0} ∩ {(x^2 + y^2) + 5*x + 6 ≥ 0} ∩ {6*(x^2 + y^2) + 5*x + 1 ≥ 0}

        A single half plane::

            sage: H._reduce_unit_disk([H.vertical(0).left_half_space()])
            {x ≤ 0}

        A pair of anti-parallel half planes::

            sage: H._reduce_unit_disk([
            ....:     H.geodesic(1/2, 2).left_half_space(),
            ....:     H.geodesic(-1/2, -2).right_half_space()])
            {2*(x^2 + y^2) - 5*x + 2 ≥ 0} ∩ {2*(x^2 + y^2) + 5*x + 2 ≥ 0}

        A segment in the unit disk with a superfluous half plane at infinity::

            sage: H._reduce_unit_disk([
            ....:     H.vertical(0).left_half_space(),
            ....:     H.vertical(0).right_half_space(),
            ....:     H.vertical(1).left_half_space()])
            {x = 0}

        A polygon in the unit disk with several superfluous half planes::

            sage: H._reduce_unit_disk([
            ....:     H.vertical(1).left_half_space(),
            ....:     H.vertical(-1).right_half_space(),
            ....:     H.geodesic(0, 1).left_half_space(),
            ....:     H.geodesic(0, -1).right_half_space(),
            ....:     H.vertical(2).left_half_space(),
            ....:     H.geodesic(0, 1/2).left_half_space()])
            {(x^2 + y^2) - x ≥ 0} ∩ {x - 1 ≤ 0} ∩ {x + 1 ≥ 0} ∩ {(x^2 + y^2) + x ≥ 0}

        """
        # TODO: Make all assumptions clear in the interface.

        if not assume_sorted:
            half_spaces = HyperbolicPlane._merge_sort(*[[half_space] for half_space in half_spaces])

        required_half_spaces = []

        is_empty = True
        is_point = True
        is_segment = True

        for i in range(len(half_spaces)):
            A = half_spaces[(i + len(half_spaces) - 1) % len(half_spaces)]
            B = half_spaces[i]
            C = half_spaces[(i + 1) % len(half_spaces)]

            AB = A.boundary()._intersection(B.boundary())
            BC = B.boundary()._intersection(C.boundary())

            segment = self.segment(B.boundary(), AB, BC, check=False)._restrict_to_disk()

            if isinstance(segment, HyperbolicEmptySet):
                pass
            elif isinstance(segment, HyperbolicPoint):
                is_empty = False
                if is_point:
                    assert is_point is True or is_point == segment, (is_point, segment)
                    is_point = segment
            else:
                is_empty = False
                is_point = False

                if is_segment is True:
                    is_segment = segment
                elif is_segment == -segment:
                    return segment
                else:
                    is_segment = False

                required_half_spaces.append(B)

        if is_empty:
            return self.empty_set()

        if is_point:
            return is_point

        if len(required_half_spaces) == 0:
            raise NotImplementedError("there is no convex set to represent the full space yet")

        if len(required_half_spaces) == 1:
            return required_half_spaces[0]

        return self.__make_element_class__(HyperbolicConvexPolygon)(self, required_half_spaces, assume_normalized=True, assume_sorted=True, check=False)

    def empty_set(self):
        r"""
        Return an empty subset of this space.

        EXAMPLES::

            sage: from flatsurf.geometry.hyperbolic import HyperbolicPlane

            sage: HyperbolicPlane().empty_set()
            {}

        """
        return self.__make_element_class__(HyperbolicEmptySet)(self)

    def _repr_(self):
        r"""
        Return a printable representation of this hyperbolic plane.

        EXAMPLES::

            sage: from flatsurf.geometry.hyperbolic import HyperbolicPlane
            sage: HyperbolicPlane(AA)
            Hyperbolic Plane over Algebraic Real Field

        """
        return f"Hyperbolic Plane over {repr(self.base_ring())}"


# TODO: Change richcmp to compare according to the subset relation.
class HyperbolicConvexSet(Element):
    r"""
    Base class for convex subsets of :class:`HyperbolicPlane`.
    """

    def _half_spaces(self):
        r"""
        Return a minimal set of half spaces whose intersection is this convex set.

        The half spaces are ordered by :meth:`HyperbolicGeodesic._normal_key`.

        EXAMPLES::

            sage: from flatsurf.geometry.hyperbolic import HyperbolicPlane
            sage: H = HyperbolicPlane(QQ)

            sage: H.vertical(0).left_half_space()._half_spaces()
            [{x ≤ 0}]

            sage: H.vertical(0)._half_spaces()
            [{x ≤ 0}, {x ≥ 0}]

            sage: H(0)._half_spaces()
            [{(x^2 + y^2) + x ≤ 0}, {x ≥ 0}]

        """
        # TODO: Check that all subclasses implement this.
        raise NotImplementedError("Convex sets must implement this method.")

    def intersection(self, other):
        r"""
        Return the intersection with the ``other`` convex set.
        """
        return self.parent().intersection([self, other])

    def __contains__(self, point):
        r"""
        Return whether ``point`` is contained in this set.
        """
        raise NotImplementedError

    def is_finite(self):
        r"""
        Return whether all points in this set are finite.
        """
        raise NotImplementedError

    def change_ring(self, ring):
        r"""
        Return this set as an element of the hyperbolic plane over ``ring``.
        """
        raise NotImplementedError

    def _test_change_ring(self, **options):
        r"""
        Verify that this set implements :meth:`change_ring`.

        TESTS::

            sage: from flatsurf.geometry.hyperbolic import HyperbolicPlane
            sage: H = HyperbolicPlane(QQ)

            sage: H.an_element()._test_change_ring()

        """
        tester = self._tester(**options)
        tester.assertEqual(self, self.change_ring(self.parent().base_ring()))

    def plot(self, model="half_plane", *kwds):
        r"""
        Return a plot of this subset.
        """
        # TODO: Check that all subclasses implement this.
        raise NotImplementedError

    def apply_isometry(self, isometry, model="half_plane"):
        r"""
        Return the image of this set under the isometry.

        INPUT:

        - ``isometry`` -- a matrix in `PGL(2,\mathbb{R})`

        """
        # TODO: Understand how isometries transform geodesics so we can
        # transform inequalities in the Klein model.
        raise NotImplementedError

    def _neg_(self):
        r"""
        Return the convex subset obtained by taking the (closed) complements of
        the half spaces whose intersection define this set.

        EXAMPLES::

            sage: from flatsurf.geometry.hyperbolic import HyperbolicPlane
            sage: H = HyperbolicPlane(QQ)

            sage: -H.vertical(0).left_half_space()
            {x ≥ 0}

        """
        return self.parent().intersection(*[-half_space for half_space in self._half_spaces()])

    # TODO: Test that _richcmp_ can compare all kinds of sets by inclusion.

    def an_element(self):
        # TODO: Test that everything implements an_element().
        raise NotImplementedError


class HyperbolicHalfSpace(HyperbolicConvexSet):
    r"""
    A closed half space of the hyperbolic plane.

    EXAMPLES::

        sage: from flatsurf.geometry.hyperbolic import HyperbolicPlane
        sage: H = HyperbolicPlane(QQ)

        sage: H.half_circle(0, 1).left_half_space()
        {(x^2 + y^2) - 1 ≥ 0}

    """

    def __init__(self, parent, geodesic):
        super().__init__(parent)

        self._geodesic = geodesic

    def equation(self, model):
        r"""
        Return an inequality for this half space as a triple ``a``, ``b``, ``c`` such that:

        - if ``model`` is ``"half_plane"``, a point `x + iy` of the upper half
          plane is in the half space if it satisfies `a(x^2 + y^2) + bx + c \ge 0`.

        - if ``model`` is ``"klein"``, points `(x, y)` in the unit disk satisfy
          `a + bx + cy \ge 0`.

        Note that the output is not unique since the coefficients can be scaled
        by a positive scalar.
        """
        return self._geodesic.equation(model=model)

    def __repr__(self):
        r"""
        Return a printable representation of this surface.

        EXAMPLES::

            sage: from flatsurf.geometry.hyperbolic import HyperbolicPlane
            sage: H = HyperbolicPlane(QQ)

            sage: S = H.half_circle(0, 1).right_half_space()

            sage: S
            {(x^2 + y^2) - 1 ≤ 0}

            sage: -S
            {(x^2 + y^2) - 1 ≥ 0}

        """
        # Convert to the Poincaré half plane model as a(x^2 + y^2) + bx + c ≥ 0.
        a, b, c = self.equation(model="half_plane")

        try:
            from sage.all import gcd
            d = gcd((a, b, c))
            a /= d
            b /= d
            c /= d
        except Exception:
            pass

        # Remove any trailing - signs in the output.
        cmp = "≥"
        if a < 0 or (a == 0 and b < 0):
            a *= -1
            b *= -1
            c *= -1
            cmp = "≤"

        from sage.all import PolynomialRing
        R = PolynomialRing(self.parent().base_ring(), names="x")
        if a != 0:
            return f"{{{repr(R([0, a]))[:-1]}(x^2 + y^2){repr(R([c, b, 1]))[3:]} {cmp} 0}}"
        else:
            return f"{{{repr(R([c, b]))} {cmp} 0}}"

    def _half_spaces(self):
        r"""
        Implements :meth:`HyperbolicConvexSet._half_spaces`.

        EXAMPLES::

            sage: from flatsurf.geometry.hyperbolic import HyperbolicPlane
            sage: H = HyperbolicPlane(QQ)

            sage: S = H.vertical(0).left_half_space()
            sage: [S] == S._half_spaces()
            True

        """
        return [self]

    def _neg_(self):
        r"""
        Return the closure of the complement of this half space.

        EXAMPLES::

            sage: from flatsurf.geometry.hyperbolic import HyperbolicPlane
            sage: H = HyperbolicPlane(QQ)

            sage: S = H.half_circle(0, 1).left_half_space()
            sage: -S
            {(x^2 + y^2) - 1 ≤ 0}

        """
        return self._geodesic.right_half_space()

    def _normal_lt(self, other):
        r"""
        Return whether this half space is smaller than ``other`` in a cyclic
        ordering of normal vectors, i.e., in an ordering that half spaces
        whether their normal points to the left/right, the slope of the
        geodesic, and finally by containment.

        This ordering is such that :meth:`HyperbolicPlane.intersection` can be
        computed in linear time for two hyperbolic convex sets.

        TESTS::

            sage: from flatsurf.geometry.hyperbolic import HyperbolicPlane, HyperbolicHalfSpace
            sage: H = HyperbolicPlane(QQ)

            sage: lt = HyperbolicHalfSpace._normal_lt

        A half space is equal to itself::

            sage: lt(H.vertical(0).left_half_space(), H.vertical(0).left_half_space())
            False

        A half space whose normal in the Klein model points to the left is
        smaller than one whose normal points to the right::

            sage: lt(H.vertical(1).left_half_space(), H.half_circle(0, 1).left_half_space())
            True
            sage: lt(H.vertical(0).left_half_space(), -H.vertical(0).left_half_space())
            True
            sage: lt(-H.half_circle(-1, 1).left_half_space(), -H.vertical(1).left_half_space())
            True
            sage: lt(-H.half_circle(-1, 1).left_half_space(), -H.vertical(1/2).left_half_space())
            True
            sage: lt(H.vertical(1).left_half_space(), H.half_circle(-1, 1).left_half_space())
            True
            sage: lt(H.vertical(1/2).left_half_space(), H.half_circle(-1, 1).left_half_space())
            True

        Half spaces are ordered by the slope of their normal in the Klein model::

            sage: lt(H.vertical(-1).left_half_space(), H.vertical(1).left_half_space())
            True
            sage: lt(-H.half_circle(-1, 1).left_half_space(), H.vertical(1).left_half_space())
            True
            sage: lt(H.half_circle(-1, 1).left_half_space(), -H.vertical(1).left_half_space())
            True
            sage: lt(H.vertical(0).left_half_space(), H.vertical(1).left_half_space())
            True

        Parallel half spaces in the Klein model are ordered by inclusion::

            sage: lt(H.vertical(1/2).left_half_space(), -H.half_circle(-1, 1).left_half_space())
            True
            sage: lt(-H.vertical(1/2).left_half_space(), H.half_circle(-1, 1).left_half_space())
            True

        Verify that comparisons are projective::

            sage: lt(H.geodesic(5, -5, -1, model="half_plane").left_half_space(), H.geodesic(5/13, -5/13, -1/13, model="half_plane").left_half_space())
            False
            sage: lt(H.geodesic(5/13, -5/13, -1/13, model="half_plane").left_half_space(), H.geodesic(5, -5, -1, model="half_plane").left_half_space())
            False

        """
        a, b, c = self._geodesic._a, self._geodesic._b, self._geodesic._c
        A, B, C = other._geodesic._a, other._geodesic._b, other._geodesic._c

        def normal_points_left(b, c):
            return b < 0 or (b == 0 and c < 0)

        if normal_points_left(b, c) != normal_points_left(B, C):
            # The normal vectors of the half spaces in the Klein disk are in
            # different half planes, one is pointing left, one is pointing
            # right.
            return normal_points_left(b, c)

        # The normal vectors of the half spaces in the Klein disk are in the
        # same half plane, so we order them by slope.
        if b * B == 0:
            if b == B:
                # The normals are vertical and in the same half plane, so
                # they must be equal. We will order the half spaces by
                # inclusion later.
                cmp = 0
            else:
                # Exactly one of the normals is vertical; we order half spaces
                # such that that one is bigger.
                return B == 0
        else:
            # Order by the slope of the normal.
            cmp = (b * B).sign() * (c * B - C * b).sign()

        if cmp == 0:
            # The half spaces are parallel in the Klein model. We order them by
            # inclusion, i.e., by the offset in direction of the normal.
            if c * C:
                cmp = (c * C).sign() * (a * C - A * c).sign()
            else:
                assert b * B
                cmp = (b * B).sign() * (a * B - A * b).sign()

        return cmp < 0

    def boundary(self):
        r"""
        Return a geodesic on the boundary of this half space, oriented such that the half space is on its left.

        EXAMPLES::

            sage: from flatsurf.geometry.hyperbolic import HyperbolicPlane
            sage: H = HyperbolicPlane(QQ)

            sage: S = H.vertical(0).left_half_space()
            sage: S.boundary()
            {-x = 0}

        """
        return self._geodesic

    def __contains__(self, point):
        point = self.parent()(point)

        if not isinstance(point, HyperbolicPoint):
            raise TypeError("point must be a point in the hyperbolic plane")

        x, y = point.coordinates(model="klein")
        a, b, c = self.equation(model="klein")

        return a + b * x + c * y >= 0

    def _richcmp_(self, other, op):
        from sage.structure.richcmp import op_EQ, op_NE

        if op == op_NE:
            return not self._richcmp_(other, op_EQ)

        if op == op_EQ:
            if not isinstance(other, HyperbolicHalfSpace):
                return False
            return self._geodesic._richcmp_(other._geodesic, op)


class HyperbolicGeodesic(HyperbolicConvexSet):
    r"""
    An oriented geodesic in the hyperbolic plane.

    Internally, we represent geodesics as the chords satisfying the equation `a
    + bx + cy=0` in the unit disc of the Klein model.

    The geodesic is oriented such that the half space `a + bx + cy ≥ 0` is on
    its left.

    EXAMPLES::

        sage: from flatsurf.geometry.hyperbolic import HyperbolicPlane
        sage: H = HyperbolicPlane(QQ)

        sage: H.vertical(0)
        {-x = 0}

        sage: H.half_circle(0, 1)
        {(x^2 + y^2) - 1 = 0}

        sage: H.geodesic(H(I), 0)
        {x = 0}

    """

    def __init__(self, parent, a, b, c, check=True):
        super().__init__(parent)
        self._a = a
        self._b = b
        self._c = c

        if check and not self._is_valid():
            # The line a + bx + cy = 0 does not intersect S¹ (or is not a line.)
            raise ValueError(f"equation {a} + ({b})*x + ({c})*y = 0 does not define a chord")

    def _is_valid(self):
        return self._b*self._b + self._c*self._c > self._a*self._a

    def _half_spaces(self):
        r"""
        Implements :meth:`HyperbolicConvexSet._half_spaces`.

        EXAMPLES::

            sage: from flatsurf.geometry.hyperbolic import HyperbolicPlane
            sage: H = HyperbolicPlane(QQ)

            sage: H.vertical(0)._half_spaces()
            [{x ≤ 0}, {x ≥ 0}]

        """
        return HyperbolicPlane._merge_sort([self.left_half_space()], [self.right_half_space()])

    def start(self):
        r"""
        Return the ideal starting point of this geodesic.

        EXAMPLES::

            sage: from flatsurf.geometry.hyperbolic import HyperbolicPlane
            sage: H = HyperbolicPlane(QQ)

            sage: H.vertical(0).start()
            0

        The coordinates of the end points of the half circle of radius
        `\sqrt{2}` around 0 can not be written down in the rationals::

            sage: H.half_circle(0, 2).start()
            Traceback (most recent call last):
            ...
            ValueError: square root of 32 not a rational number

        Passing to a bigger field, the coordinates can be represented::

            sage: H.half_circle(0, 2).change_ring(AA).start()
            1.414...

        """
        a, b, c = self.equation(model="half_plane")

        if a == 0:
            if b > 0:
                return self.parent().infinity()
            return self.parent().real(-c/b)

        discriminant = b*b - 4*a*c
        root = discriminant.sqrt(extend=False)

        endpoints = ((-b - root) / (2*a), (-b + root) / (2*a))

        if a > 0:
            return max(endpoints)
        else:
            return min(endpoints)

    def end(self):
        r"""
        Return the ideal end point of this geodesic.

        EXAMPLES::

            sage: from flatsurf.geometry.hyperbolic import HyperbolicPlane
            sage: H = HyperbolicPlane(QQ)

            sage: H.vertical(0).end()
            ∞

        The coordinates of the end points of the half circle of radius
        `\sqrt{2}` around 0 can not be written down in the rationals::

            sage: H.half_circle(0, 2).end()
            Traceback (most recent call last):
            ...
            ValueError: square root of 32 not a rational number

        Passing to a bigger field, the coordinates can be represented::

            sage: H.half_circle(0, 2).change_ring(AA).end()
            -1.414...

        """
        return (-self).start()

    def _neg_(self):
        r"""
        Return the reversed geodesic.

        EXAMPLES::

            sage: from flatsurf.geometry.hyperbolic import HyperbolicPlane
            sage: H = HyperbolicPlane(QQ)

            sage: -H.vertical(0)
            {x = 0}

        """
        return self.parent().geodesic(-self._a, -self._b, -self._c, model="klein")

    def equation(self, model):
        r"""
        Return an equation for this geodesic as a triple ``a``, ``b``, ``c`` such that:

        - if ``model`` is ``"half_plane"``, a point `x + iy` of the upper half
          plane is on the geodesic if it satisfies `a(x^2 + y^2) + bx + c = 0`.
          The coefficients are such that the half plane `a(x^2 + y^2) + bx + c
          ≥ 0` is on the left of the geodesic.

        - if ``model`` is ``"klein"``, points `(x, y)` in the unit disk satisfy
          `a + bx + cy = 0`. The sign of the coefficients is such that the half
          plane `a + bx + cy ≥ 0` is on the left of the geodesic.

        Note that the output is not unique since the coefficients can be scaled
        by a positive scalar.
        """
        a, b, c = self._a, self._b, self._c

        if model == "klein":
            return a, b, c

        if model == "half_plane":
            return a + c, 2*b, a - c

        raise NotImplementedError("cannot determine equation for this model yet")

    def _repr_(self):
        # Convert to the Poincaré half plane model as a(x^2 + y^2) + bx + c = 0.
        a, b, c = self.equation(model="half_plane")

        try:
            from sage.all import gcd
            d = gcd((a, b, c))
            a /= d
            b /= d
            c /= d
        except Exception:
            pass

        from sage.all import PolynomialRing
        R = PolynomialRing(self.parent().base_ring(), names="x")
        if a != 0:
            return f"{{{repr(R([0, a]))[:-1]}(x^2 + y^2){repr(R([c, b, 1]))[3:]} = 0}}"
        else:
            return f"{{{repr(R([c, b]))} = 0}}"

    def plot(self, model="half_plane", **kwds):
        r"""
        Create a plot of this geodesic in the hyperbolic ``model``.

        Additional arguments are passed on to the underlying SageMath plotting methods.

        EXAMPLES::
        """
        a, b, c = self.equation(model=model)

        if model == "half_plane":
            if a == 0:
                # This is a vertical in the half plane model.
                x = -c/b

                return vertical(x, **kwds)

            else:
                # This is a half-circle in the half plane model.
                center = -(b/a)/2
                radius_squared = center*center - (c/a)

                from sage.plot.all import arc
                from sage.all import RR, pi
                return arc((RR(center), 0), RR(radius_squared).sqrt(), sector=(0, pi), **kwds)

        if model == "klein":
            raise NotImplementedError

        raise NotImplementedError("plotting not supported in this hyperbolic model")

    def change_ring(self, ring):
        r"""
        Return this geodesic in the Hyperbolic plane over ``ring``.

        EXAMPLES::

            sage: from flatsurf.geometry.hyperbolic import HyperbolicPlane
            sage: H = HyperbolicPlane(AA)

            sage: H.vertical(1).change_ring(QQ)
            {-x + 1 = 0}

            sage: H.vertical(AA(2).sqrt()).change_ring(QQ)
            Traceback (most recent call last):
            ...
            ValueError: Cannot coerce irrational Algebraic Real ... to Rational

        """
        return HyperbolicPlane(ring).geodesic(self._a, self._b, self._c, model="klein")

    def left_half_space(self):
        r"""
        Return the closed half space to the left of this (oriented) geodesic.

        EXAMPLES::

            sage: from flatsurf.geometry.hyperbolic import HyperbolicPlane
            sage: H = HyperbolicPlane(AA)

            sage: H.vertical(0).left_half_space()
            {x ≤ 0}

        """
        return self.parent().half_space(self._a, self._b, self._c, model="klein")

    def right_half_space(self):
        r"""
        Return the closed half space to the right of this (oriented) geodesic.

        EXAMPLES::

            sage: from flatsurf.geometry.hyperbolic import HyperbolicPlane
            sage: H = HyperbolicPlane(AA)

            sage: H.vertical(0).right_half_space()
            {x ≥ 0}

        """
        return (-self).left_half_space()

    def an_element(self):
        a, b, c = self.equation(model="klein")

        return self.parent().geodesic(0, -c, b, model="klein", check=False)._intersection(self)

    def _configuration(self, other):
        r"""
        Return a classification of the angle between this
        geodesic and ``other`` in the Klein model.

        """
        intersection = self._intersection(other)

        if intersection is None:
            orientation = (self._b * other._b + self._c * other._c).sign()

            assert orientation != 0

            if self == other:
                assert orientation > 0
                return "equal"

            if self == -other:
                assert orientation < 0
                return "negative"

            if orientation > 0:
                return "parallel"

            return "anti-parallel"

        tangent = (self._c, -self._b)
        orientation = (-tangent[0] * other._b  - tangent[1] * other._c).sign()

        assert orientation != 0

        # TODO: Is convex/concave the right term?
        if orientation > 0:
            return "convex"

        return "concave"

    def _intersection(self, other):
        r"""
        Return the intersection of this geodesic and ``other`` in the Klein
        model or in the Euclidean plane if the intersection point is ultra
        ideal, i.e., not in the unit disk.

        Returns ``None`` if the lines do not intersect in a point.

        EXAMPLES::

            sage: from flatsurf.geometry.hyperbolic import HyperbolicPlane
            sage: H = HyperbolicPlane(AA)

        ::

            sage: A = -H.vertical(0)
            sage: B = H.vertical(-1)
            sage: C = H.vertical(0)
            sage: A._intersection(B)
            ∞
            sage: A._intersection(C)
            sage: B._intersection(A)
            ∞
            sage: B._intersection(C)
            ∞
            sage: C._intersection(A)
            sage: C._intersection(B)
            ∞

        """
        if not isinstance(other, HyperbolicGeodesic):
            raise TypeError("can only intersect with another geodesic")

        from sage.all import matrix, vector

        A = matrix([[self._b, self._c], [other._b, other._c]])

        if A.rank() < 2:
            return None

        v = vector([-self._a, -other._a])
        x, y = A.solve_right(v)

        return self.parent().point(x, y, model="klein", check=False)

    def __contains__(self, point):
        point = self.parent()(point)

        if not isinstance(point, HyperbolicPoint):
            raise TypeError("point must be a point in the hyperbolic plane")

        x, y = point.coordinates(model="klein")
        a, b, c = self.equation(model="klein")

        return a + b * x + c * y == 0

    def parametrize(self, point, model, check=True):
        if isinstance(point, HyperbolicPoint):
            if check and point not in self:
                raise ValueError("point must be on geodesic to be parametrized")

        if model == "euclidean":
            base = self.an_element().coordinates(model="klein")
            tangent = (self._c, -self._b)

            if isinstance(point, HyperbolicPoint):
                coordinate = 0 if tangent[0] else 1
                return (point.coordinates(model="klein")[coordinate] - base[coordinate]) / tangent[coordinate]

            λ = self.parent().base_ring()(point)

            return self.parent().point(
                x=base[0] + λ * tangent[0],
                y=base[1] + λ * tangent[1],
                model="klein",
                check=check)

        raise NotImplementedError("cannot parametrize a geodesic over this model yet")

    def _richcmp_(self, other, op):
        from sage.structure.richcmp import op_EQ, op_NE

        if op == op_NE:
            return not self._richcmp_(other, op_EQ)

        if op == op_EQ:
            if not isinstance(other, HyperbolicGeodesic):
                return False
            if self._b:
                return self._b.sign() == other._b.sign() and self._a * other._b == other._a * self._b and self._c * other._b == other._c * self._b
            else:
                return self._c.sign() == other._c.sign() and self._a * other._c == other._a * self._c and self._b * other._c == other._b * self._c

        super()._richcmp_(other, op)


class HyperbolicPoint(HyperbolicConvexSet):
    r"""
    A (possibly infinite) point in the :class:`HyperbolicPlane`.

    Internally, we represent a point as the Euclidean coordinates in the unit
    disc of the Klein model.
    """

    def __init__(self, parent, x, y, check=True):
        super().__init__(parent)
        self._x = x
        self._y = y

        if check and not self._is_valid():
            raise ValueError("point is not in the unit disk in the Klein model")

    def _is_valid(self):
        return self._x*self._x + self._y*self._y <= 1

    def _half_spaces(self):
        r"""
        Implements :meth:`HyperbolicConvexSet._half_spaces`.

        EXAMPLES::

            sage: from flatsurf.geometry.hyperbolic import HyperbolicPlane
            sage: H = HyperbolicPlane(QQ)

            sage: H(I)._half_spaces()
            [{(x^2 + y^2) + 2*x - 1 ≤ 0}, {x ≥ 0}, {(x^2 + y^2) - 1 ≥ 0}]

            sage: H(I + 1)._half_spaces()
            [{x - 1 ≤ 0}, {(x^2 + y^2) - 3*x + 1 ≤ 0}, {(x^2 + y^2) - 2 ≥ 0}]

            sage: H.infinity()._half_spaces()
            [{x ≤ 0}, {x - 1 ≥ 0}]

            sage: H(0)._half_spaces()
            [{(x^2 + y^2) + x ≤ 0}, {x ≥ 0}]

            sage: H(-1)._half_spaces()
            [{x + 1 ≤ 0}, {(x^2 + y^2) - 1 ≤ 0}]

            sage: H(1)._half_spaces()
            [{(x^2 + y^2) - x ≤ 0}, {(x^2 + y^2) - 1 ≥ 0}]

            sage: H(2)._half_spaces()
            [{2*(x^2 + y^2) - 3*x - 2 ≥ 0}, {3*(x^2 + y^2) - 7*x + 2 ≤ 0}]

            sage: H(-2)._half_spaces()
            [{(x^2 + y^2) - x - 6 ≥ 0}, {2*(x^2 + y^2) + 3*x - 2 ≤ 0}]

            sage: H(1/2)._half_spaces()
            [{6*(x^2 + y^2) - x - 1 ≤ 0}, {2*(x^2 + y^2) + 3*x - 2 ≥ 0}]

            sage: H(-1/2)._half_spaces()
            [{2*(x^2 + y^2) + 7*x + 3 ≤ 0}, {2*(x^2 + y^2) - 3*x - 2 ≤ 0}]

        """
        x0 = self._x
        y0 = self._y

        if self.is_finite():
            return HyperbolicPlane._merge_sort(
                # x ≥ x0
                [self.parent().half_space(-x0, 1, 0, model="klein")],
                # y ≥ y0
                [self.parent().half_space(-y0, 0, 1, model="klein")],
                # x + y ≤ x0 + y0
                [self.parent().half_space(x0 + y0, -1, -1, model="klein")])
        else:
            return HyperbolicPlane._merge_sort(
                # left of the line from (0, 0) to this point
                [self.parent().half_space(0, -y0, x0, model="klein")],
                # right of a line to this point with a starting point right of (0, 0)
                [self.parent().half_space(-x0*x0 - y0*y0, y0 + x0, y0 - x0, model="klein")])

    def is_finite(self):
        return self._x * self._x + self._y * self._y < 1

    def coordinates(self, model="half_plane", ring=None):
        r"""
        Return coordinates of this point in ``ring``.

        If ``model`` is ``"half_plane"``, return projective coordinates in the
        Poincaré half plane model.

        If ``model`` is ``"klein"``, return Euclidean coordinates in the Klein model.

        If no ``ring`` has been specified, an appropriate extension of the base
        ring of the :class:`HyperbolicPlane` is chosen where these coordinates
        live.
        """
        x, y = self._x, self._y

        # TODO: Implement ring

        if model == "half_plane":
            denominator = 1 - y
            return (x / denominator, (1 - x*x - y*y).sqrt()/denominator)

        if model == "klein":
            return (x, y)

        raise NotImplementedError

    def _richcmp_(self, other, op):
        r"""
        Return how this point compares to ``other``, see
        :meth:`HyperbolicConvexSet._richcmp_`.

        EXAMPLES::

            sage: from flatsurf.geometry.hyperbolic import HyperbolicPlane

            sage: H = HyperbolicPlane()

            sage: H.infinity() == H.projective(1, 0)
            True

        """
        from sage.structure.richcmp import op_EQ, op_NE

        if op == op_NE:
            return not self._richcmp_(other, op_EQ)

        if op == op_EQ:
            if not isinstance(other, HyperbolicPoint):
                return False
            return self._x == other._x and self._y == other._y

        super()._richcmp_(other, op)

    def _repr_(self):
        if self._x == 0 and self._y == 1:
            return "∞"

        x, y = self.coordinates()

        # We represent x + y*I in R[[I]] so we do not have to reimplement printing ourselves.
        if x not in self.parent().base_ring() or y not in self.parent().base_ring():
            x, y = self.coordinates(model="klein")
            return f"({repr(x)}, {repr(y)})"

        # TODO: This does not work when the coordinates are not in the base_ring.
        from sage.all import PowerSeriesRing
        return repr(PowerSeriesRing(self.parent().base_ring(), names="I")([x, y]))

    def change_ring(self, ring):
        return HyperbolicPlane(ring).point(self._x, self._y, model="klein")

    def apply_isometry(self, isometry, model="half_plane"):
        r"""
        Return the image of this point under the isometry.

        INPUT:

        - ``isometry`` -- a matrix in `PGL(2,\mathbb{R})` or `SO(1, 2)`

        - ``model`` -- either ``"half_plane"`` or ``"klein"``

        TESTS::

            sage: from flatsurf.geometry.hyperbolic import HyperbolicPlane
            sage: H = HyperbolicPlane(QQ)

            sage: for (a, b, c, d) in [(2, 1, 1, 1), (1, 1, 0, 1), (1, 0, 1, 1), (2, 0, 0 , 1)]:
            ....:     m = matrix(2, [a, b, c, d])
            ....:     assert H(0).apply_isometry(m) == H(b / d if d else oo)
            ....:     assert H(1).apply_isometry(m) == H((a + b) / (c + d) if c+d else oo)
            ....:     assert H(oo).apply_isometry(m) == H(a / c if c else oo)
        """
        R = self.parent().base_ring()

        if model == "half_plane":
            isometry = sl2_to_so12(isometry)
            model = "klein"

        if model == "klein":
            from sage.matrix.special import diagonal_matrix
            from sage.modules.free_module_element import vector

            # TODO: check that isometry is actually a matrix?
            if isometry.nrows() != 3 or isometry.ncols() != 3 or not R.has_coerce_map_from(isometry.base_ring()):
                raise ValueError('invalid isometry')
            D = isometry.transpose() * diagonal_matrix([1, 1, -1]) * isometry
            if D[0, 1] or D[0, 2] or D[1, 0] or D[1, 2] or D[2, 0] or D[2, 1]:
                raise ValueError('invalid isometry')
            if D[0, 0].is_zero() or D[1, 1].is_zero() or D[2, 2].is_zero():
                raise ValueError('invalid isometry')
            if D[0, 0] != D[1, 1] or D[0, 0] != - D[2, 2]:
                raise ValueError('invalid isometry')
            x, y, z = isometry * vector(R, [self._x, self._y, 1])
            return self.parent().point(x / z, y / z, model="klein")

        raise NotImplementedError("applying isometry not supported in this hyperbolic model")


class HyperbolicConvexPolygon(HyperbolicConvexSet):
    r"""
    A (possibly unbounded) closed polygon in the :class:`HyperbolicPlane`,
    i.e., the intersection of a finite number of :class:`HyperbolicHalfSpace`s.
    """

    def __init__(self, parent, half_spaces, assume_normalized=False, assume_sorted=False, check=True):
        if check:
            # TODO
            raise NotImplementedError

        if not assume_normalized:
            # TODO
            raise NotImplementedError

        if not assume_sorted:
            # TODO
            raise NotImplementedError

        self._half_spaces = half_spaces

    def _normalize(self):
        r"""
        Normalize the internal list of half planes so that they describe the
        :meth:`boundary`.
        """
        raise NotImplementedError

    def equations(self):
        r"""
        Return the equations describing the boundary of this polygon.

        The output is minimal and sorted by slope in the Klein model.
        """
        raise NotImplementedError

    def edges(self):
        r"""
        Return the :class:`HyperbolicEdge`s defining this polygon.
        """
        raise NotImplementedError

    def vertices(self):
        r"""
        Return the vertices of this polygon, i.e., the end points of the
        :meth:`edges`.
        """
        raise NotImplementedError

    def _half_spaces(self):
        return self._half_spaces

    def _repr_(self):
        return " ∩ ".join([repr(half_space) for half_space in self._half_spaces])


class HyperbolicEdge(HyperbolicConvexSet):
    r"""
    An oriented (possibly infinite) segment in the hyperbolic plane such as a
    boundary edge of a :class:`HyperbolicConvexPolygon`.
    """

    def __init__(self, parent, geodesic, start=None, end=None, check=True):
        super().__init__(parent)

        # TODO: Add such type checks everywhere.
        if not isinstance(geodesic, HyperbolicGeodesic):
            raise TypeError("geodesic must be a hyperbolic geodesic")

        if start is not None and not isinstance(start, HyperbolicPoint):
            raise TypeError("start must be a hyperbolic point")

        if end is not None and not isinstance(end, HyperbolicPoint):
            raise TypeError("start must be a hyperbolic point")

        self._geodesic = geodesic
        self._start = start
        self._end = end

        # TODO: Properly report errors.
        if check and not self._is_valid():
            raise ValueError

    def _is_valid(self):
        if not self._geodesic._is_valid():
            return False

        if self._start is not None:
            if not self._start._is_valid():
                return False

            if self._start not in self._geodesic:
                return False

        if self._end is not None:
            if not self._end._is_valid():
                return False

            if self._end not in self._geodesic:
                return False

        if self._start is not None and self._end is not None:
            if self._start == self._end:
                return False

        # TODO: Check that the endpoints are ordered correctly.

        return True

    def _restrict_to_disk(self):
        r"""
        EXAMPLES::

            sage: from flatsurf.geometry.hyperbolic import HyperbolicPlane
            sage: H = HyperbolicPlane(QQ)

        ::

            sage: H.segment(H.vertical(-1), start=H.infinity(), end=H.infinity(), check=False)._restrict_to_disk()
            ∞

        ::

            sage: H.segment(H.vertical(0), start=H.infinity(), end=None, check=False)._restrict_to_disk()
            ∞

        ::

            sage: H.segment(-H.vertical(0), start=H.infinity(), end=None, check=False)._restrict_to_disk()
            {x = 0}

        ::

            sage: H.segment(-H.vertical(0), start=None, end=H.infinity(), check=False)._restrict_to_disk()
            ∞

        """
        if not self._geodesic._is_valid():
            return self.parent().empty_set()

        start = self._start
        end = self._end

        if start is not None:
            λ_start = self._geodesic.parametrize(start, model="euclidean")

        if end is not None:
            λ_end = self._geodesic.parametrize(end, model="euclidean")

        if start is not None and end is not None:
            if λ_end < λ_start:
                end = None
            elif λ_start == λ_end:
                return start if start._is_valid() else self.parent().empty_set()

        if start is not None:
            if not start._is_valid():
                if λ_start > 0:
                    return self.parent().empty_set()
                start = None
            elif not start.is_finite():
                if λ_start > 0:
                    return start
                start = None

        if end is not None:
            if not end._is_valid():
                if λ_end < 0:
                    return self.parent().empty_set()
                end = None
            elif not end.is_finite():
                if λ_end < 0:
                    return end
                end = None

        if start is None and end is None:
            return self._geodesic

        assert (start is None or start._is_valid()) and (end is None or end._is_valid())

        return self.parent().segment(self._geodesic, start=start, end=end)

    def _half_spaces(self):
        half_spaces = self._geodesic._half_spaces()

        if self._start is not None:
            x, y = self._start.coordinates(model="klein")
            b, c = (self._geodesic._c, -self._geodesic._b)
            half_spaces.append(self.parent().half_space(-b * x -c * y, b, c, model="klein"))

        if self._end is not None:
            x, y = self._end.coordinates(model="klein")
            b, c = (-self._geodesic._c, self._geodesic._b)
            half_spaces.append(self.parent().half_space(-b * x -c * y, b, c, model="klein"))

        return half_spaces

    def _repr_(self):
        half_spaces = self._half_spaces()

        geodesic = repr(self._geodesic)
        start = ""
        end = ""

        if self._start is not None:
            start = f" from {repr(half_spaces[2])}"

        if self._end is not None:
            end = f" to {repr(half_spaces[-1])}"

        return f"{geodesic}{start}{end}"


class HyperbolicEmptySet(HyperbolicConvexSet):
    r"""
    The empty subset of the hyperbolic plane.
    """

    def __init__(self, parent):
        super().__init__(parent)

    def _richcmp_(self, other, op):
        r"""
        Return how this set compares to ``other``.

        See :meth:`HyperbolicConvexSet._richcmp_`.

        EXAMPLES::

            sage: from flatsurf.geometry.hyperbolic import HyperbolicPlane

            sage: H = HyperbolicPlane()

            sage: H.empty_set() == H.empty_set()
            True

        """
        from sage.structure.richcmp import rich_to_bool

        if isinstance(other, HyperbolicEmptySet):
            return rich_to_bool(op, 0)

        return rich_to_bool(op, -1)

    def _repr_(self):
        return "{}"

def sl2_to_so12(m):
    r"""
    Return the lift of the 2x2 matrix ``m`` inside ``SO(1,2)``.
    """
    from sage.matrix.constructor import matrix

    if m.nrows() != 2 or m.ncols() != 2:
        raise ValueError('invalid matrix')
    a, b, c, d = m.list()
    return matrix(3, [a*d + b*c, a*c - b*d, a*c + b*d,
                      a*b - c*d, (a**2 - b**2 - c**2 + d**2) / 2, (a**2 + b**2 - c**2 - d**2) / 2,
                      a*b + c*d, (a**2 - b**2 + c**2 - d**2) / 2, (a**2 + b**2 + c**2 + d**2) / 2])


class Vertical(GraphicPrimitive):
    r"""
    A graphical ray going vertically up from (x, y).

    Used internally to, e.g., plot a vertical geodesic in the upper half plane
    model.

    This object should not be created directly (even inside this module) but by
    calling :meth:`vertical` below.

    EXAMPLES::

        sage: from flatsurf.geometry.hyperbolic import Vertical
        sage: Vertical(0, 0)
        Vertical at (0, 0)


    """

    def __init__(self, x, y=0, options={}):
        valid_options = self._allowed_options()
        for option in options:
            if option not in valid_options:
                raise RuntimeError("Error in line(): option '%s' not valid." % option)

        self._x = x
        self._y = y
        super().__init__(options)

    def _allowed_options(self):
        r"""
        Return the options that are supported by a vertical.

        We support all the options that are understood by a SageMath line.

        EXAMPLES::

            sage: from flatsurf.geometry.hyperbolic import Vertical
            sage: Vertical(0, 0)._allowed_options()
            {'alpha': 'How transparent the line is.',
             'hue': 'The color given as a hue.',
             'legend_color': 'The color of the legend text.',
             'legend_label': 'The label for this item in the legend.',
             'linestyle': "The style of the line, which is one of '--' (dashed), '-.' (dash dot), '-' (solid), 'steps', ':' (dotted).",
             'marker': 'the marker symbol (see documentation for line2d for details)',
             'markeredgecolor': 'the color of the marker edge',
             'markeredgewidth': 'the size of the marker edge in points',
             'markerfacecolor': 'the color of the marker face',
             'markersize': 'the size of the marker in points',
             'rgbcolor': 'The color as an RGB tuple.',
             'thickness': 'How thick the line is.',
             'zorder': 'The layer level in which to draw'}

        """
        from sage.plot.line import Line
        return Line([], [], {})._allowed_options()

    def __repr__(self):
        r"""
        Return a printable representation of this graphical primitive.

        EXAMPLES::

            sage: from flatsurf.geometry.hyperbolic import Vertical
            sage: Vertical(0, 0)
            Vertical at (0, 0)

        """
        return f"Vertical at ({self._x}, {self._y})"

    def _render_on_subplot(self, subplot):
        r"""
        Render this vertical on the subplot.

        Matplotlib was not really made to draw things that extend to infinity.
        The trick here is to register a callback that redraws the vertical
        whenever the viewbox of the plot changes, e.g., as more objects are
        added to the plot.
        """
        # Rewrite options to only contain matplotlib compatible entries
        matplotlib_options = {
            key: value for (key, value) in self.options().items()
            if key not in {'alpha', 'legend_color', 'legend_label', 'linestyle', 'rgbcolor', 'thickness'}
        }

        from matplotlib.lines import Line2D
        line = Line2D([self._x, self._x], [self._y, self._y], **matplotlib_options)
        subplot.add_line(line)

        # Translate SageMath options to matplotlib style.
        options = self.options()
        line.set_alpha(float(options['alpha']))
        line.set_linewidth(float(options['thickness']))
        from sage.plot.colors import to_mpl_color
        line.set_color(to_mpl_color(options['rgbcolor']))
        line.set_label(options['legend_label'])

        def redraw(_=None):
            r"""
            Redraw the vertical after the viewport has been rescaled to
            make sure it reaches the top of the viewport.
            """
            ylim = max(self._y, subplot.axes.get_ylim()[1])
            line.set_ydata((self._y, ylim))

        subplot.axes.callbacks.connect('ylim_changed', redraw)
        redraw()

    def get_minmax_data(self):
        r"""
        Return the bounding box of this vertical.

        This box is used to make sure that the viewbox of the plot is zoomed
        such that the vertical is visible.

        EXAMPLES::

            sage: from flatsurf.geometry.hyperbolic import Vertical
            sage: Vertical(1, 2).get_minmax_data()
            {'xmax': 1, 'xmin': 1, 'ymax': 2, 'ymin': 2}

        """
        from sage.plot.plot import minmax_data
        return minmax_data([self._x, self._x], [self._y, self._y], dict=True)


@rename_keyword(color='rgbcolor')
@options(alpha=1, rgbcolor=(0, 0, 1), thickness=1, legend_label=None, legend_color=None, aspect_ratio='automatic')
def vertical(x, y=0, **options):
    r"""
    Create a SageMath graphics object that describe a vertical ray going up
    from the coordinates ``x``, ``y``.

    EXAMPLES::

        sage: from flatsurf.geometry.hyperbolic import vertical
        sage: vertical(1, 2)
        Graphics object consisting of 1 graphics primitive


    """
    from sage.plot.all import Graphics
    g = Graphics()
    g._set_extra_kwds(Graphics._extract_kwds_for_show(options))
    g.add_primitive(Vertical(x, y, options))
    if options['legend_label']:
        g.legend(True)
        g._legend_colors = [options['legend_color']]
    return g
