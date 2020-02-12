A tour of sage-flatsurf
***********************

(under construction)

Polygons
--------

The most basic object in sage-flatsurf is a convex polygon. There
are some predefined ones

::

    sage: import flatsurf
    sage: P5 = flatsurf.polygons.regular_ngon(5)
    sage: P5
    Polygon: (0, 0), (1, 0), (1/2*a^2 - 1/2, 1/2*a), (1/2, 1/2*a^3 - a), (-1/2*a^2 + 3/2, 1/2*a)

And you can also build your own polygon

.. link

::

    sage: flatsurf.polygons((1,0), (0,3), (1,-1))   # from a list of edges
    Polygon: (0, 0), (1, 0), (1, 3)
    sage: flatsurf.polygons(vertices = [(0,0), (1,0), (1,3)])   # from a list of vertices
    Polygon: (0, 0), (1, 0), (1, 3)

If you want to construct a polygon whose coordinates are algebraic
numbers you need to build the appropriate embedded number field

.. link

::

    sage: x = polygen(QQ)
    sage: K.<u> = NumberField(x^3 - 2, 'cbrt2', embedding=AA(2)**(1/3))
    sage: flatsurf.polygons((1,u), (0,1), (-u,0), ring=K)
    Polygon: (0, 0), (1, u), (1, u + 1)

.. link

::

    sage: p = x^4 - x - 1
    sage: emb = AA.polynomial_root(p, RIF(1.21, 1.23))
    sage: L.<v> = NumberField(p, 'a', emb)
    sage: flatsurf.polygons((1, 1+v), (0,v), (-1,v), (-v,-1))
    Polygon: (0, 0), (1, v + 1), (1, 2*v + 1), (0, 3*v + 1)

From polygons to surfaces
-------------------------

Given a polygon, you can directly construct the associated billiard as a
similarity surface (made of two copies of the polygon). From there, you can
build its translation cover

::

    sage: import flatsurf
    sage: T = flatsurf.polygons.triangle(1,4,5)
    sage: S = flatsurf.similarity_surfaces.billiard(T)
    sage: S.minimal_cover(cover_type="translation")
    TranslationSurface built from 20 polygons

Some famous translation surfaces are also available

.. link

::

    sage: AY = flatsurf.translation_surfaces.arnoux_yoccoz(3)
    sage: AY
    TranslationSurface built from 12 polygons