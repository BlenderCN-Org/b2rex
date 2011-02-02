"""
 Hacks on external libraries
"""

import ogrepkg.materialexport
from b2rexpkg.material import RexMaterialExporter

ogrepkg.materialexport.GameEngineMaterial = RexMaterialExporter
