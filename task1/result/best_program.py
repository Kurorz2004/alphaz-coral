"""Max-sum-of-radii packing of 26 circles in the unit square.

The centers below were found by parallel basin-hopping: each step perturbs the
incumbent (global shake / relocate smallest circles / fill the largest empty
pocket) and re-solves a bilevel local problem. For *fixed* centers the optimal
radii are the solution of a linear program

    maximize  sum r_i
    s.t.      r_i + r_j <= dist(c_i, c_j)      for all i < j
              0 <= r_i  <= dist(c_i, wall)     for all i

so `run()` only stores centers and recovers the radii exactly at call time. That
keeps the returned packing feasible by construction rather than by tolerance.

sum of radii = 2.635983085   (best known 2.635977)
"""
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix

N = 26

CENTERS = np.array([
    (np.float64(0.48259558221054133), np.float64(0.1034672333579533)),
    (np.float64(0.3869235534095992), np.float64(0.7052539409510491)),
    (np.float64(0.7629588636539975), np.float64(0.24064759843906713)),
    (np.float64(0.889220987209283), np.float64(0.8892209872092832)),
    (np.float64(0.682080042932588), np.float64(0.09615133404576329)),
    (np.float64(0.9074079050485631), np.float64(0.3140569780132149)),
    (np.float64(0.6832585349730809), np.float64(0.9042676706929788)),
    (np.float64(0.07886037291596634), np.float64(0.5027155537958921)),
    (np.float64(0.08463950069577354), np.float64(0.9153604993042259)),
    (np.float64(0.9060726627225556), np.float64(0.5005716308609597)),
    (np.float64(0.8888438205895559), np.float64(0.11115617941044542)),
    (np.float64(0.1332585727708121), np.float64(0.2976904749108409)),
    (np.float64(0.5960427019081348), np.float64(0.2730942856884041)),
    (np.float64(0.08492626245490054), np.float64(0.08492626245489932)),
    (np.float64(0.38166584445264545), np.float64(0.2973903963009764)),
    (np.float64(0.7420494434605908), np.float64(0.40478026706026726)),
    (np.float64(0.5299634197531916), np.float64(0.5013319244965974)),
    (np.float64(0.2753426167714393), np.float64(0.5044682393256418)),
    (np.float64(0.7636735693833852), np.float64(0.7602894720724628)),
    (np.float64(0.9076084484290381), np.float64(0.6868841900295979)),
    (np.float64(0.7424170495016343), np.float64(0.596641216397318)),
    (np.float64(0.27478328335082075), np.float64(0.8932098553714225)),
    (np.float64(0.5976347963876607), np.float64(0.7283701485139975)),
    (np.float64(0.48460080265191496), np.float64(0.896939479858417)),
    (np.float64(0.130221101065227), np.float64(0.7053905112181725)),
    (np.float64(0.27395283962395284), np.float64(0.1051825602687507)),
])


def optimal_radii(centers):
    """Exact optimal radii for fixed centers (a linear program)."""
    iu, ju = np.triu_indices(N, k=1)
    dist = np.linalg.norm(centers[iu] - centers[ju], axis=1)
    npair = iu.size
    rows_ = np.repeat(np.arange(npair), 2)
    cols = np.column_stack([iu, ju]).ravel()
    A = coo_matrix((np.ones(2 * npair), (rows_, cols)), shape=(npair, N))
    wall = np.minimum.reduce([centers[:, 0], centers[:, 1],
                              1.0 - centers[:, 0], 1.0 - centers[:, 1]])
    res = linprog(-np.ones(N), A_ub=A, b_ub=dist,
                  bounds=list(zip(np.zeros(N), np.maximum(wall, 0.0))),
                  method="highs")
    return np.maximum(res.x, 0.0)


def run():
    centers = CENTERS.copy()
    radii = optimal_radii(centers)
    return centers, radii, float(np.sum(radii))


if __name__ == "__main__":
    _, rr, ss = run()
    print(f"sum={ss:.9f} score={ss / 2.635977:.6f}")
