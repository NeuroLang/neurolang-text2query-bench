"""Run a brute-force checker (argv[1], its argv after) and count the
rewriting steps the one-step test of ``_surely_dead`` (``_moves``) drops
that the reach test (``_backward``) keeps: whether the checker exercises
the one-step test at all.

    PYTHONPATH=<NeuroLang packages> .venv-dsparity/bin/python \\
        scripts/hang/xrmoves/prune_count.py CHECKER [ARGS...]
"""
import atexit
import runpy
import sys

from nl_core.datalog import ontologies_rewriter as orw

R = orw.OntologyRewriter
count = {"steps": 0, "one_step": 0, "reach": 0}
surely_dead = R._surely_dead


def reach_of(self, functor, position):
    """``_backward`` from the class's ``_moves``, uncached."""
    reach, todo = {(functor, position)}, [(functor, position)]
    while todo:
        for move in R._moves(self, *todo.pop()) - reach:
            reach.add(move)
            todo.append(move)
    return reach


def counted(self, q, S, sigma):
    dead = surely_dead(self, q, S, sigma)
    self._moves = lambda functor, position: reach_of(
        self, functor, position
    )
    try:
        reach = surely_dead(self, q, S, sigma)
    finally:
        del self._moves
    count["steps"] += 1
    count["one_step"] += dead
    count["reach"] += reach
    return dead


R._surely_dead = counted
atexit.register(lambda: print("prune count", count, file=sys.stderr))
sys.argv = sys.argv[1:]
runpy.run_path(sys.argv[0], run_name="__main__")
