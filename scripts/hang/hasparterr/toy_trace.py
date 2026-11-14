"""Trace the deterministic stratum and its ontology rewrite on the query
path of the toy program of toy.py."""
import runpy
import sys

from neurolang.frontend import probabilistic_frontend as pf

sys.argv = ["toy"]
orig = pf.NeurolangPDL._solve_deterministic_stratum


def traced(self, det_idb):
    print("DET", det_idb)
    if "__constraints__" in self.symbol_table:
        print("REWRITTEN", self._rewrite_det_idb(det_idb))
    return orig(self, det_idb)


pf.NeurolangPDL._solve_deterministic_stratum = traced
runpy.run_path(sys.path[0] + "/toy.py")
