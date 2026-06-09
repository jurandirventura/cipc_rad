# Create index of satellites files
# build_satellite_index()

import os
import re

#==========================================================
# Criar índice uma única vez para não fazer muitos globs
#==========================================================
def build_satellite_index(sat_dir):

    index = {}

    regex = re.compile(r"(\d{8})")

    for root, _, files in os.walk(sat_dir):

        for f in files:

            if not f.lower().endswith(".tif"):
                continue

            m = regex.search(f)

            if not m:
                continue

            yyyymmdd = m.group(1)

            index[yyyymmdd] = os.path.join(
                root,
                f
            )

    return index
