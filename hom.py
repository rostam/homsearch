import logging as log

from sage.graphs.graph import Graph
from sage.modules.free_module import VectorSpace
from sage.rings.finite_rings.constructor import GF
from sage.misc.preparser import load
from sage.misc.misc import powerset


try:
  load("hom_c.pyx", locals())
except Exception as e:
  log.fatal("hom_c.pyx failed to load: %s", e)


def CayleyGraph(vspace, gens, directed=False):
  """
  Generate a Cayley Graph over given vector space with edges
  generated by given generators. The graph is optionally directed.
  Try e.g. CayleyGraph(VectorSpace(GF(2), 3), [(1,0,0), (0,1,0), (0,0,1)])
  """
  G = Graph()
  for v in vspace:
    G.add_vertex(tuple(v))
    for g in gens:
      g2 = vspace(g)
      G.add_edge(tuple(v), tuple(v + g2))
  return G


def nonisomorphic_cubes_Z2(n, avoid_complete=False):
  """
  Returns a generator for all n-dimensional Cube-like graphs
  (Cayley graphs over Z_2^n) with their generators.
  With avoid_complete=True avoids the complete graph.
  Iterates over tuples (generatorSet, G).
  """
  vs = VectorSpace(GF(2), n)
  basegens = vs.gens()
  optgens = [v for v in vs if sum(map(int,v)) >= 2]
  total = 2**len(optgens)
  seen_graphs = set()
  c = 0
  for g in powerset(optgens):
    c += 1
    gens = tuple(list(basegens) + g)
    if c % (total / 100 + 1) == 0:
      log.debug("Generating (%d of %d)" % (c, total))
    if avoid_complete:
      if len(g) >= len(optgens):
        continue
    G = CayleyGraph(vs, gens)

    canon = tuple(Graph(G).canonical_label().edges())
    if canon in seen_graphs:
      continue
    log.debug("Unique graph (%d of %d) gens=%s" % (c, total, gens))
    seen_graphs.add(canon)

    yield (gens, G)


def find_hom_image(G, candidates=None):
  """
  Tries to find a smaller hom-image of G. Repeatedly sets H:=G\{v} for v in candidates.
  Returns an induced subgraph on a strictly smaller hom-image, or None if G is a core.
  candidates defaults to V(G). If G is e.g. vertex-transitive, you may wish to use just
  one vertex.
  """
  if candidates is None:
    candidates = G.vertices()
  for v0 in candidates:
    H = G.copy()
    H.delete_vertex(v0)
    maps = extend_hom(G, H, limit=1)
    if len(maps) >= 1:
      VC = maps[0].values()
      C = G.subgraph(VC)
      return C
  return None


def check_subcore(G, candidates=None):
  """
  Tries to find a core, returning a smaller core or None if G is already core.
  Tries to remove every vertex of tryremove (one at a time), defauts to all.
  """
  if candidates is None:
    candidates = G.vertices()
  #log.info(tryremove)
  for v0 in candidates:
    H = G.copy()
    H.delete_vertex(v0)
    maps = extend_hom(G, H, limit=1)
    if len(maps) >= 1:
      VC = maps[0].values()
      C = G.subgraph(VC)
      return C
  return None


def find_core(G, vertex_trans=False):
  """
  Finds a core of a Graph. If G is vertex-transitive, the process is much faster.
  Returns a core (a subgraph of G) or G itself.
  Complete graphs are treated specially.
  """
  if G.size() == (G.order() * (G.order()-1)) / 2:
    return G
  Gold = G
  rem0 = None
  if vertex_trans:
    rem0 = G.vertices()[:1]
  G = check_subcore(G, candidates=rem0)
  while G:
    Gold = G
    G = find_hom_image(G)
  return Gold


def squash_cube(G, c):
  """
  Assuming G is a cube-like _undirected_ graph (Cayley over Z_2^n),
  given a vector c from Z_2^n, finds a homomorphism unifying
  vectors differing by c. One of the vertives (v, v+c) still must
  be chosen as the target for the homomorphism in each such pair.

  Returns a hom map to a subgraph or None if none such exists.
  """
  n = len(c)
  vs = VectorSpace(GF(2), n)
  c = vs(c)

  pairs = {}   # vertex -> pair
  for v in G.vertices():
    w = tuple(vs(v) + c)
    if G.has_edge(v, w):
      return False # contracting an edge!
    if w in pairs or v in pairs: continue
    pairs[v] = (v, w)
    pairs[w] = (v, w)
  chosen = {}  # pair -> 0 or 1 (first or second in the pair)
  undecided = set(pairs.values()) # undecided pairs

  def extend(pair, sel):
    """Extend `chosen[]` by setting pair to sel (0 or 1).
    Recursively chooses for pairs forced by this coloring.
    Returns False on inconsistency, True if all the forcing
    succeeded."""
    if pair in chosen:
      if chosen[pair] != sel:
        return False
      return True
    chosen[pair] = sel
    if pair in undecided:
      undecided.remove(pair)
    v = pair[sel]
    w = pair[1 - sel]

    for n in G.neighbors(v):
      np = pairs[n]
      ni = np.index(n)
      if G.has_edge(n, w):
        continue
      if not extend(np, ni):
        return False
    return True

  while undecided:
    p = undecided.pop()
    if not extend(p, 0):
      return None
  # create the hom-map
  hom = {}
  for p, sel in chosen.items():
    hom[p[0]] = p[sel]
    hom[p[1]] = p[sel]
  return hom


def is_hom(G, H, hom):
  """
  Check whether hom is a homomorphism from G to H.
  Works for both directed and undirected.
  """
  assert set(G.vertices()) == set(hom.keys())
  assert set(H.vertices()).issuperset(set(hom.values()))
  for e in G.edges():
    u, v = e[0], e[1]
    if not H.has_edge(hom[u], hom[v]):
      return False
  return True


def hom_is_by_subspace(G, vs, h, require_isomorphic=True):
  """
  Check whether for a given homomorphism `h`, there is a subspace `span` of `vs` such that
  `h` unifies exactly vertices differing by element of `span` (alternatively: `h` factorizes
  the vertices of `G` by a subspace of `vs`).

  If you specify require_isomorphic=False, each of the unified vertex group is checked to be an
  affine subspace, but these subspaces are not required to be isomorphic.

  Returns True/False.
  """
  span_com = None
  for im in h.values():
    src = [vs(v) for v in G if h[v] == im]
    src0 = [i - src[0] for i in src]
    span = vs.span(src0)
    if len(src0) < 2**span.dimension():
      # log.debug("Dim of span too large %d for %s from %s", span.dimension(), src0, src)
      return False
    if require_isomorphic:
      if span_com is None:
        span_com = span
      if span_com != span:
        # log.debug("Subspaces not isomorphic: %s vs %s", span, span_com)
        return False
  return True


## Module unit testing


def raises(f):
  "Internal helper for testing."
  try:
    f()
  except:
    return True
  return False


def test():
  "Run unit tests for the module."
  log.getLogger().setLevel(log.DEBUG)

  from sage.graphs.graph_generators import graphs
  K2 = graphs.CompleteGraph(2)
  K4 = graphs.CompleteGraph(4)
  C16 = graphs.CycleGraph(16)
  Z2_3 = VectorSpace(GF(2), 3)
  Z2_2 = VectorSpace(GF(2), 2)

  # extend_hom
  assert len(extend_hom(K4, K4, limit=100)) == 24
  assert len(extend_hom(K2, K4, partmap={0:0}, limit=10)) == 3
  assert len(extend_hom(C16, K2, limit=10)) == 2
  assert len(extend_hom(C16, K2, partmap={0:0, 2:1}, limit=10)) == 0

  # nonisomorphic_cubes_Z2
  assert len(list(nonisomorphic_cubes_Z2(1))) == 1
  assert len(list(nonisomorphic_cubes_Z2(2))) == 2
  assert len(list(nonisomorphic_cubes_Z2(3))) == 6

  # CayleyGraph
  K4b = CayleyGraph(Z2_2, [(1,0), (0,1), (1,1)])
  assert K4.is_isomorphic(K4b)

  # find_hom_image
  K4c = find_hom_image(K4.disjoint_union(K4))
  assert K4.is_isomorphic(K4c)

  # find_core
  K4d = find_core(K4.disjoint_union(K4).disjoint_union(K4))
  assert K4.is_isomorphic(K4d)

  # squash_cube
  Ge = CayleyGraph(Z2_2, [(1,0), (0,1)])
  Smap = squash_cube(Ge, (1,1))
  K2e = Ge.subgraph(Smap.values())
  assert K2.is_isomorphic(K2e)
  assert is_hom(Ge, K2e, Smap)

  # is_hom
  for hom in extend_hom(C16, K2, limit=10):
    assert is_hom(C16, K2, hom)
  assert raises(lambda: is_hom(K2, K2, {0:0})) # not all vertices mapped
  assert raises(lambda: is_hom(K2, K2, {0:4})) # some vertices outside K2
  assert not is_hom(K2, K2, {0:0, 1:0}) # creates a loop

  # hom_is_by_subspace
  Gg = CayleyGraph(Z2_3, [(1,0,0), (0,1,0)])
  Hg = CayleyGraph(Z2_2, [(1,0), (0,1), (1,1)])
  homg = {(0,0,0):(0,0), (1,0,0):(1,0), (0,1,0):(0,1), (1,1,0):(1,1),
          (0,0,1):(0,0), (1,0,1):(1,0), (0,1,1):(1,1), (1,1,1):(0,1)}
  assert is_hom(Gg, Hg, homg)
  assert hom_is_by_subspace(Gg, Z2_3, homg, require_isomorphic=False)
  assert not hom_is_by_subspace(Gg, Z2_3, homg, require_isomorphic=True)
  for h in extend_hom(Gg, K2, limit=10):
    assert hom_is_by_subspace(Gg, Z2_3, h, require_isomorphic=True)

  log.info("All tests passed.")

