import os
import re


# ==========================================================
# Criar índice dos arquivos de satélite
#
# Produtos diários:
#
#   20240816 -> arquivo.tif
#
# GOES-AOD:
#
#   20240816 -> [
#       arquivo_104020.tif,
#       arquivo_105020.tif,
#       arquivo_110020.tif,
#       ...
#   ]
# ==========================================================

def build_satellite_index(
    sat_dir,
    include_time=False
):

    index = {}

    # ------------------------------------------------------
    # Regex
    # ------------------------------------------------------

    if include_time:

        regex = re.compile(
            r"(\d{8})_(\d{6})"
        )

    else:

        regex = re.compile(
            r"(\d{8})"
        )

    # ------------------------------------------------------
    # Percorrer arquivos
    # ------------------------------------------------------

    for root, _, files in os.walk(sat_dir):

        for f in files:

            if not f.lower().endswith(".tif"):
                continue

            m = regex.search(f)

            if not m:
                continue

            yyyymmdd = m.group(1)

            caminho = os.path.join(
                root,
                f
            )

            # ==================================================
            # GOES
            # ==================================================

            if include_time:

                index.setdefault(
                    yyyymmdd,
                    []
                ).append(caminho)

            # ==================================================
            # Produtos diários
            # ==================================================

            else:

                index[yyyymmdd] = caminho

    # ------------------------------------------------------
    # Ordenar arquivos GOES pela hora
    # ------------------------------------------------------

    if include_time:

        for data in index:

            index[data].sort()

    return index



# import os
# import re


# def build_satellite_index(
#     sat_dir,
#     include_time=False
# ):

#     index = {}

#     if include_time:
#         regex = re.compile(
#             r"(\d{8})_(\d{6})"
#         )
#     else:
#         regex = re.compile(
#             r"(\d{8})"
#         )

#     for root, _, files in os.walk(sat_dir):

#         for f in files:

#             if not f.lower().endswith(".tif"):
#                 continue

#             m = regex.search(f)

#             if not m:
#                 continue

#             yyyymmdd = m.group(1)

#             if include_time:

#                 index.setdefault(
#                     yyyymmdd,
#                     []
#                 ).append(
#                     os.path.join(root, f)
#                 )

#             else:

#                 index[yyyymmdd] = os.path.join(
#                     root,
#                     f
#                 )

#     if include_time:

#         for data in index:
#             index[data].sort()

#     return index



# # Create index of satellites files
# # build_satellite_index()

    # import os
    # import re


    # # ==========================================================
    # # Criar índice dos arquivos de satélite
    # #
    # # Para produtos diários:
    # #
    # #   20240816 -> arquivo.tif
    # #
    # # Para GOES-AOD:
    # #
    # #   20240816 -> [
    # #       arquivo_143020.tif,
    # #       arquivo_152020.tif,
    # #       arquivo_181020.tif,
    # #       ...
    # #   ]
    # # ==========================================================

    # # Create index of satellites files
    # # build_satellite_index()

    # import os
    # import re


    # # ==========================================================
    # # Criar índice uma única vez para não fazer muitos globs
    # # ==========================================================
    # def build_satellite_index(
    #     sat_dir,
    #     include_time=False
    # ):

    #     index = {}

    #     # ------------------------------------------------------
    #     # Arquivos com data:
    #     #
    #     # YYYYMMDD
    #     #
    #     # ou com data + hora:
    #     #
    #     # YYYYMMDD_HHMMSS
    #     # ------------------------------------------------------

    #     if include_time:

    #         regex = re.compile(
    #             r"(\d{8})_(\d{6})"
    #         )

    #     else:

    #         regex = re.compile(
    #             r"(\d{8})"
    #         )

    #     # ------------------------------------------------------
    #     # Percorre os arquivos
    #     # ------------------------------------------------------

    #     for root, _, files in os.walk(sat_dir):

    #         for f in files:

    #             if not f.lower().endswith(".tif"):
    #                 continue

    #             m = regex.search(f)

    #             if not m:
    #                 continue

    #             yyyymmdd = m.group(1)

    #             # ------------------------------------------------
    #             # Índice com hora
    #             # ------------------------------------------------

    #             if include_time:

    #                 hhmmss = m.group(2)

    #                 index.setdefault(
    #                     yyyymmdd,
    #                     []
    #                 ).append(
    #                     os.path.join(root, f)
    #                 )

    #             # ------------------------------------------------
    #             # Índice somente por data
    #             # ------------------------------------------------

    #             else:

    #                 index[yyyymmdd] = os.path.join(
    #                     root,
    #                     f
    #                 )

    #     # ------------------------------------------------------
    #     # Ordenar arquivos GOES cronologicamente
    #     # ------------------------------------------------------

    #     if include_time:

    #         for data in index:

    #             index[data].sort()

    #     return index



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

#             path = os.path.join(root, f)

#             # ------------------------------------------------
#             # Se já existe arquivo para essa data,
#             # transforma em lista.
#             # ------------------------------------------------
#             if yyyymmdd not in index:

#                 index[yyyymmdd] = [path]

#             else:

#                 index[yyyymmdd].append(path)

#     # ======================================================
#     # Ordenar arquivos de cada data
#     # ======================================================

#     for data in index:

#         index[data].sort()

#     return index



# ## ****************************************** GRÁFICO FRONTEND FUNCIONA
# # Create index of satellites files
# # build_satellite_index()

# # Create index of satellite files
# # build_satellite_index()

# import os
# import re


# # ==========================================================
# # Criar índice uma única vez para não fazer muitos globs
# # ==========================================================
# def build_satellite_index(
#     sat_dir,
#     include_time=False
# ):

#     index = {}

#     # ------------------------------------------------------
#     # Padrão para data
#     #
#     # Exemplo:
#     # 20240816
#     # ------------------------------------------------------
#     regex_date = re.compile(
#         r"(\d{8})"
#     )

#     # ------------------------------------------------------
#     # Padrão para data + hora
#     #
#     # Exemplo:
#     # 20240816_143020
#     # ------------------------------------------------------
#     regex_datetime = re.compile(
#         r"(\d{8})_(\d{6})"
#     )

#     for root, _, files in os.walk(sat_dir):

#         for f in files:

#             if not f.lower().endswith(".tif"):
#                 continue

#             # ==================================================
#             # DATA + HORA
#             # ==================================================
#             if include_time:

#                 m = regex_datetime.search(f)

#                 if not m:
#                     continue

#                 yyyymmdd = m.group(1)
#                 hhmmss = m.group(2)

#                 key = f"{yyyymmdd}_{hhmmss}"

#             # ==================================================
#             # SOMENTE DATA
#             # ==================================================
#             else:

#                 m = regex_date.search(f)

#                 if not m:
#                     continue

#                 key = m.group(1)

#             # --------------------------------------------------
#             # Guarda o caminho completo
#             # --------------------------------------------------
#             index[key] = os.path.join(
#                 root,
#                 f
#             )

#     return index



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
