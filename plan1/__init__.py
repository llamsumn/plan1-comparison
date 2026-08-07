"""plan1 — the penguin ↔ DeformSplat comparison assembler.

Assembles the comparison from archived run records under the rules pre-registered
in ``evidence/record/plan1_prereg.md``, which is vendored into this repository and
is the whole of what governs the assembly. The rules are the comparability gate,
the precision policy and the saturation rule; each is asserted in the suite.

Three pieces, one seam:

* :mod:`plan1.assemble` — **the seam**. A pure function from a declared manifest
  plus the run records to a validated comparison table. Comparability gating and
  gap arithmetic both sit behind it, so every failure mode is drivable from a
  fixture without a GPU, an asset file, or a network.
* :mod:`plan1.saturation` — the pre-registered rule that selects the reported
  rigidity, as a pure function over a sweep.
* :mod:`plan1.records` / :mod:`plan1.manifest` — file reading, below the seam.

Everything above the seam (:mod:`plan1.render`) is presentation.
"""

from plan1.assemble import ComparisonTable, assemble
from plan1.manifest import Manifest, ManifestRow, load_manifest, load_records
from plan1.records import Measurement, RunRecord
from plan1.saturation import SweepPoint, select_saturated_row

__all__ = [
    "ComparisonTable",
    "Manifest",
    "ManifestRow",
    "Measurement",
    "RunRecord",
    "SweepPoint",
    "assemble",
    "load_manifest",
    "load_records",
    "select_saturated_row",
]
