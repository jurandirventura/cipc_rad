# Create index of satellites files
# build_satellite_index()

# Create index of satellite files
# build_satellite_index()

import os
import re


# ==========================================================
# Criar índice uma única vez para não fazer muitos globs
# ==========================================================
def build_satellite_index(
    sat_dir,
    include_time=False
):

    index = {}

    # ------------------------------------------------------
    # Padrão para data
    #
    # Exemplo:
    # 20240816
    # ------------------------------------------------------
    regex_date = re.compile(
        r"(\d{8})"
    )

    # ------------------------------------------------------
    # Padrão para data + hora
    #
    # Exemplo:
    # 20240816_143020
    # ------------------------------------------------------
    regex_datetime = re.compile(
        r"(\d{8})_(\d{6})"
    )

    for root, _, files in os.walk(sat_dir):

        for f in files:

            if not f.lower().endswith(".tif"):
                continue

            # ==================================================
            # DATA + HORA
            # ==================================================
            if include_time:

                m = regex_datetime.search(f)

                if not m:
                    continue

                yyyymmdd = m.group(1)
                hhmmss = m.group(2)

                key = f"{yyyymmdd}_{hhmmss}"

            # ==================================================
            # SOMENTE DATA
            # ==================================================
            else:

                m = regex_date.search(f)

                if not m:
                    continue

                key = m.group(1)

            # --------------------------------------------------
            # Guarda o caminho completo
            # --------------------------------------------------
            index[key] = os.path.join(
                root,
                f
            )

    return index



# versão até 07/ago/2026 com data apenas, sem o time
# import os
# import re

# #==========================================================
# # Criar índice uma única vez para não fazer muitos globs
# #==========================================================
# def build_satellite_index(sat_dir):

#     index = {}

#     regex = re.compile(r"(\d{8})")

#     for root, _, files in os.walk(sat_dir):

#         for f in files:

#             if not f.lower().endswith(".tif"):
#                 continue

#             m = regex.search(f)

#             if not m:
#                 continue

#             yyyymmdd = m.group(1)

#             index[yyyymmdd] = os.path.join(
#                 root,
#                 f
#             )

#     return index
