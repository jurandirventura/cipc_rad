# Organiza a leitura dos produtos de satélite

import pandas as pd
import numpy as np

from satellite.raster_reader import get_satellite_mean


# =========================================================
# Função para leitura dos produtos de satélite
# =========================================================

def get_satellite_series(
    sat_index,
    datas_unicas,
    lat_station,
    lon_station,
    delta,
    scale=1.0
):

    print("\n===== GET SATELLITE SERIES =====")
    print("Lat:", lat_station)
    print("Lon:", lon_station)
    print("Delta:", delta)
    print("Scale:", scale)
    print("Datas:", datas_unicas)
    print("Índice possui:", len(sat_index), "dias")


    sat_dates = []
    sat_values = []

    for data_ref in datas_unicas:

        yyyymmdd = pd.Timestamp(
            data_ref
        ).strftime("%Y%m%d")

        arquivos = sat_index.get(
            yyyymmdd
        )

        print(
            "DATA:",
            yyyymmdd,
            "ARQUIVOS:",
            len(arquivos) if isinstance(arquivos, list) else arquivos
        )        

        if arquivos is None:
            continue

        # ==================================================
        # Produto diário
        # ==================================================

        if isinstance(arquivos, str):

            arquivos = [arquivos]

        # ==================================================
        # GOES
        # ==================================================

        valores = []

        for tif_file in arquivos:

            valor = get_satellite_mean(
                tif_file,
                lat_station,
                lon_station,
                delta
            )

            print(
                "GOES:",
                tif_file,
                "=>",
                valor
            )


            if np.isfinite(valor):

                valores.append(
                    valor
                )

        # --------------------------------------------------
        # Nenhum valor válido
        # --------------------------------------------------

        if not valores:
            continue

        # --------------------------------------------------
        # Média diária
        # --------------------------------------------------

        valor_medio = np.mean(
            valores
        )

        sat_dates.append(
            pd.Timestamp(data_ref)
        )

        sat_values.append(
            valor_medio * scale
        )

    print(
        "RESULTADO GOES:",
        sat_dates,
        sat_values
    )

    return sat_dates, sat_values





# import pandas as pd
# import numpy as np

# from satellite.raster_reader import get_satellite_mean


# # =========================================================
# # Função para leitura dos produtos de satélite
# # =========================================================

# def get_satellite_series(
#     sat_index,
#     datas_unicas,
#     lat_station,
#     lon_station,
#     delta,
#     scale=1.0
# ):

#     sat_dates = []
#     sat_values = []

#     for data_ref in datas_unicas:

#         yyyymmdd = pd.Timestamp(
#             data_ref
#         ).strftime("%Y%m%d")

#         arquivos = sat_index.get(yyyymmdd)

#         if arquivos is None:
#             continue

#         # =====================================================
#         # Produto diário: um único TIFF
#         # =====================================================

#         if isinstance(arquivos, str):

#             valor = get_satellite_mean(
#                 arquivos,
#                 lat_station,
#                 lon_station,
#                 delta
#             )

#             if np.isfinite(valor):

#                 sat_dates.append(
#                     pd.Timestamp(data_ref)
#                 )

#                 sat_values.append(
#                     valor * scale
#                 )

#         # =====================================================
#         # GOES: vários TIFFs no mesmo dia
#         # =====================================================

#         else:

#             valores = []

#             for arquivo in arquivos:

#                 valor = get_satellite_mean(
#                     arquivo,
#                     lat_station,
#                     lon_station,
#                     delta
#                 )

#                 if np.isfinite(valor):

#                     valores.append(valor)

#             if valores:

#                 valor_medio = np.mean(valores)

#                 sat_dates.append(
#                     pd.Timestamp(data_ref)
#                 )

#                 sat_values.append(
#                     valor_medio * scale
#                 )

#     return sat_dates, sat_values
















###**************************** gráfico funciona para sat e estação, goes-aod nao.
# def get_satellite_series(
#     sat_index,
#     datas_unicas,
#     lat_station,
#     lon_station,
#     delta,
#     scale=1.0
# ):

#     sat_dates = []
#     sat_values = []

#     for data_ref in datas_unicas:

#         yyyymmdd = pd.Timestamp(
#             data_ref
#         ).strftime("%Y%m%d")

#         arquivos = sat_index.get(yyyymmdd)

#         if not arquivos:
#             continue

#         # -------------------------------------------------
#         # Compatibilidade com índice antigo:
#         # se vier apenas uma string, transforma em lista
#         # -------------------------------------------------
#         if isinstance(arquivos, str):

#             arquivos = [arquivos]

#         valores_dia = []

#         # -------------------------------------------------
#         # Processa todos os horários daquele dia
#         # -------------------------------------------------
#         for tif_file in arquivos:

#             try:

#                 valor = get_satellite_mean(
#                     tif_file,
#                     lat_station,
#                     lon_station,
#                     delta
#                 )

#                 if np.isfinite(valor):

#                     valores_dia.append(
#                         valor
#                     )

#             except Exception as e:

#                 print(
#                     f"Erro lendo {tif_file}: {e}"
#                 )

#         # -------------------------------------------------
#         # Nenhum valor válido naquele dia
#         # -------------------------------------------------
#         if not valores_dia:
#             continue

#         # -------------------------------------------------
#         # Média dos horários válidos
#         # -------------------------------------------------
#         valor_medio = np.mean(
#             valores_dia
#         )

#         sat_dates.append(
#             pd.Timestamp(data_ref)
#         )

#         sat_values.append(
#             valor_medio * scale
#         )

#     return sat_dates, sat_values




# # Organiza a leitura dos produtos de satélite
# # get_satellite_series()

# import pandas as pd
# import numpy as np

# from satellite.raster_reader import get_satellite_mean

# # =========================================================
# # Função para leitura dos produtos de satélite
# # =========================================================
# def get_satellite_series(
#     sat_index,
#     datas_unicas,
#     lat_station,
#     lon_station,
#     delta,
#     scale=1.0
# ):

#     sat_dates = []
#     sat_values = []

#     for data_ref in datas_unicas:

#         yyyymmdd = pd.Timestamp(
#             data_ref
#         ).strftime("%Y%m%d")

#         arquivos = sat_index.get(yyyymmdd)

#         if not arquivos:
#             continue

#         # =====================================================
#         # Garantir que seja sempre uma lista
#         # =====================================================

#         if isinstance(arquivos, str):

#             arquivos = [arquivos]

#         valores_dia = []

#         # =====================================================
#         # Ler todos os arquivos daquela data
#         # =====================================================

#         for tif_file in arquivos:

#             try:

#                 valor = get_satellite_mean(
#                     tif_file,
#                     lat_station,
#                     lon_station,
#                     delta
#                 )

#                 if np.isfinite(valor):

#                     valores_dia.append(
#                         valor
#                     )

#             except Exception as e:

#                 print(
#                     f"Erro lendo {tif_file}: {e}"
#                 )

#         # =====================================================
#         # Se nenhum arquivo possui valor válido
#         # =====================================================

#         if not valores_dia:
#             continue

#         # =====================================================
#         # Média diária dos horários disponíveis
#         # =====================================================

#         valor_medio = np.mean(
#             valores_dia
#         )

#         sat_dates.append(
#             pd.Timestamp(data_ref)
#         )

#         sat_values.append(
#             valor_medio * scale
#         )

#     return sat_dates, sat_values














# def get_satellite_series(
#     sat_index,
#     datas_unicas,
#     lat_station,
#     lon_station,
#     delta,
#     scale=1.0
# ):

#     sat_dates = []
#     sat_values = []

#     for data_ref in datas_unicas:

#         yyyymmdd = pd.Timestamp(
#             data_ref
#         ).strftime("%Y%m%d")

#         tif_file = sat_index.get(yyyymmdd)

#         if tif_file is None:
#             continue

#         valor = get_satellite_mean(
#             tif_file,
#             lat_station,
#             lon_station,
#             delta
#         )

#         if np.isfinite(valor):

#             sat_dates.append(
#                 pd.Timestamp(data_ref)
#             )

#             sat_values.append(
#                 valor * scale
#             )

#     return sat_dates, sat_values


# =========================================================
# Função para leitura dos produtos GOES com data + hora
# =========================================================
def get_goes_series(
    goes_index,
    datas_unicas,
    lat_station,
    lon_station,
    delta,
    scale=1.0
):
    """
    Extrai série temporal dos produtos GOES.

    O índice GOES utiliza chaves no formato:

        YYYYMMDD_HHMMSS

    Exemplo:

        20240816_143020
        20240816_152020
        20240816_181020

    Retorna um ponto para cada arquivo GOES disponível.
    """

    goes_dates = []
    goes_values = []

    for data_ref in datas_unicas:

        data_ref = pd.Timestamp(data_ref)

        prefix = data_ref.strftime(
            "%Y%m%d"
        )

        # -------------------------------------------------
        # Todos os arquivos GOES daquele dia
        # -------------------------------------------------

        arquivos_dia = sorted(
            (
                key,
                tif_file
            )
            for key, tif_file in goes_index.items()
            if key.startswith(prefix + "_")
        )

        # -------------------------------------------------
        # Processa cada horário
        # -------------------------------------------------

        for key, tif_file in arquivos_dia:

            valor = get_satellite_mean(
                tif_file,
                lat_station,
                lon_station,
                delta
            )

            if not np.isfinite(valor):
                continue

            # ---------------------------------------------
            # YYYYMMDD_HHMMSS
            # →
            # Timestamp
            # ---------------------------------------------

            data_hora = pd.to_datetime(
                key,
                format="%Y%m%d_%H%M%S"
            )

            goes_dates.append(
                data_hora
            )

            goes_values.append(
                valor * scale
            )

    return goes_dates, goes_values

