# -*- coding: utf-8 -*-
r"""
Eskin-McMullen-Mukamel-Write quadrilaterals from the article
"Billiards, quadrilaterals and moduli spaces"

Note that in some cases, the billiards might give a Veech surface and not
the ambient rank 2 locus.
"""
######################################################################
# This file is part of sage-flatsurf.
#
#       Copyright (C) 2020 Vincent Delecroix
#
# sage-flatsurf is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# sage-flatsurf is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with sage-flatsurf. If not, see <https://www.gnu.org/licenses/>.
######################################################################

import sys
import pytest

import itertools

pytest.importorskip('pyflatsurf')

from sage.all import AA, QQ, sqrt, NumberField
from flatsurf import EquiangularPolygons, similarity_surfaces, GL2ROrbitClosure

# TODO: the test for field of definition with is_isomorphic() does not check
# for embeddings... though for quadratic fields it does not matter much.
@pytest.mark.parametrize("a,b,c,d,l1,l2,veech,discriminant", [
    (1,1,1,7,1,1,True,5),
    (1,1,1,7,AA(2).sqrt(),1,False,5),
    (1,1,1,9,1,1,True,3),
    (1,1,1,9,AA(2).sqrt(),1,False,1),
    (2,2,3,13,1,1,False,5),
    (1,1,2,8,1,1,False,1),
    (1,1,2,12,1,1,False,2),
    (1,2,2,11,1,1,False,2),
    (1,2,2,15,1,1,False,5)
])
def test_rank2_quadrilateral(a, b, c, d, l1, l2, veech, discriminant):
    E = EquiangularPolygons(a, b, c, d)
    P = E([l1, l2], normalized=True)
    B = similarity_surfaces.billiard(P, rational=True)
    S = B.minimal_cover(cover_type="translation")
    S = S.erase_marked_points()
    S, _ = S.normalized_coordinates()
    O = GL2ROrbitClosure(S)
    assert O.ambient_stratum() == E.billiard_unfolding_stratum(cover_type="translation")
    D = itertools.islice(O.decompositions(9, 40), 30)
    if veech:
        assert S.base_ring().degree() <= 2
        for dec in D:
            O.update_tangent_space_from_flow_decomposition(dec)
            assert dec.parabolic()
        assert O.dimension() == O.absolute_dimension() == 2, (O.dimension(), O.absolute_dimension())
    else:
        for dec in D:
            O.update_tangent_space_from_flow_decomposition(dec)
        assert O.absolute_dimension() == O.dimension() == 4, (O.U.dimension(), O.absolute_dimension())

    if discriminant == 1:
        assert O.field_of_definition() == QQ
    else:
        assert O.field_of_definition().degree() == 2
        assert O.field_of_definition().discriminant().squarefree_part() == discriminant