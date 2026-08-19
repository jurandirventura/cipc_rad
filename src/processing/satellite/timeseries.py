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

    import time

    print("\n===== GET SATELLITE SERIES =====")
    print("Lat:", lat_station)
    print("Lon:", lon_station)
    print("Delta:", delta)
    print("Scale:", scale)
    print("Datas:", datas_unicas)
    print("Índice possui:", len(sat_index), "dias")

    sat_dates = []
    sat_values = []

    inicio_total = time.perf_counter()

    for data_ref in datas_unicas:

        inicio_dia = time.perf_counter()

        data_ref = pd.Timestamp(data_ref)

        yyyymmdd = data_ref.strftime("%Y%m%d")

        arquivos = sat_index.get(
            yyyymmdd
        )

        print(
            "\nDATA:",
            yyyymmdd,
            "ARQUIVOS:",
            len(arquivos) if isinstance(arquivos, list) else arquivos
        )

        if arquivos is None:
            continue

        if isinstance(arquivos, str):
            arquivos = [arquivos]

        # =================================================
        # SELECIONA 1 ARQUIVO POR HORA
        # =================================================

        arquivos_horarios = {}

        for tif_file in arquivos:

            # -------------------------------------------------
            # Extrai o horário do nome/caminho do arquivo
            # -------------------------------------------------

            nome = str(tif_file)

            # Procura padrão YYYYMMDD_HHMMSS
            import re

            match = re.search(
                r"(\d{8})_(\d{6})",
                nome
            )

            if not match:
                continue

            data_str = match.group(1)
            hora_str = match.group(2)

            if data_str != yyyymmdd:
                continue

            hora = int(
                hora_str[0:2]
            )

            minuto = int(
                hora_str[2:4]
            )

            segundo = int(
                hora_str[4:6]
            )

            # -------------------------------------------------
            # Distância para a hora cheia
            # -------------------------------------------------

            segundos_desde_hora = (
                minuto * 60 +
                segundo
            )

            # Distância circular dentro da hora
            distancia = min(
                segundos_desde_hora,
                3600 - segundos_desde_hora
            )

            # -------------------------------------------------
            # Guarda o mais próximo da hora cheia
            # -------------------------------------------------

            atual = arquivos_horarios.get(
                hora
            )

            if (
                atual is None
                or distancia < atual["distancia"]
            ):

                arquivos_horarios[hora] = {

                    "arquivo": tif_file,

                    "distancia": distancia
                }

        # =================================================
        # PROCESSA OS ARQUIVOS HORÁRIOS
        # =================================================

        arquivos_selecionados = [

            arquivos_horarios[h]["arquivo"]

            for h in sorted(
                arquivos_horarios
            )
        ]

        print(
            "ARQUIVOS SELECIONADOS:",
            len(arquivos_selecionados)
        )

        valores = []

        for tif_file in arquivos_selecionados:

            inicio_tif = time.perf_counter()

            valor = get_satellite_mean(
                tif_file,
                lat_station,
                lon_station,
                delta
            )

            tempo_tif = (
                time.perf_counter()
                - inicio_tif
            )

            print(
                "GOES:",
                tif_file,
                "=>",
                valor,
                f"tempo={tempo_tif:.3f}s"
            )

            if np.isfinite(valor):

                valores.append(
                    valor
                )

        # =================================================
        # NENHUM VALOR VÁLIDO
        # =================================================

        if not valores:
            continue

        # =================================================
        # MÉDIA DIÁRIA
        # =================================================

        valor_medio = np.mean(
            valores
        )

        sat_dates.append(
            data_ref
        )

        sat_values.append(
            valor_medio * scale
        )

        tempo_dia = (
            time.perf_counter()
            - inicio_dia
        )

        print(
            f"TEMPO DIA {yyyymmdd}: "
            f"{tempo_dia:.3f}s"
        )

    tempo_total = (
        time.perf_counter()
        - inicio_total
    )

    print(
        "\n===== RESULTADO GOES ====="
    )

    print(
        "DATAS:",
        sat_dates
    )

    print(
        "VALORES:",
        sat_values
    )

    print(
        f"TEMPO TOTAL GOES = "
        f"{tempo_total:.3f}s"
    )

    return sat_dates, sat_values



#------------------

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





# # VERSÃO FUNCIONAVA MAS DEPOIS DE MUDAR PARA BUSCAR ARQUIVOS 
# # GOES MAIS PRÓXIMO DA HORA E NÃO DE 10 EM 10 MINUTOS, FOI 
# # ALTERADA PARA A NOVA VERSÃO. 
# def get_satellite_series(
#     sat_index,
#     datas_unicas,
#     lat_station,
#     lon_station,
#     delta,
#     scale=1.0
# ):

#     print("\n===== GET SATELLITE SERIES =====")
#     print("Lat:", lat_station)
#     print("Lon:", lon_station)
#     print("Delta:", delta)
#     print("Scale:", scale)
#     print("Datas:", datas_unicas)
#     print("Índice possui:", len(sat_index), "dias")


#     sat_dates = []
#     sat_values = []

#     for data_ref in datas_unicas:

#         yyyymmdd = pd.Timestamp(
#             data_ref
#         ).strftime("%Y%m%d")

#         arquivos = sat_index.get(
#             yyyymmdd
#         )

#         print(
#             "DATA:",
#             yyyymmdd,
#             "ARQUIVOS:",
#             len(arquivos) if isinstance(arquivos, list) else arquivos
#         )        

#         if arquivos is None:
#             continue

#         # ==================================================
#         # Produto diário
#         # ==================================================

#         if isinstance(arquivos, str):

#             arquivos = [arquivos]

#         # ==================================================
#         # GOES
#         # ==================================================

#         valores = []

#         for tif_file in arquivos:

#             valor = get_satellite_mean(
#                 tif_file,
#                 lat_station,
#                 lon_station,
#                 delta
#             )

#             print(
#                 "GOES:",
#                 tif_file,
#                 "=>",
#                 valor
#             )


#             if np.isfinite(valor):

#                 valores.append(
#                     valor
#                 )

#         # --------------------------------------------------
#         # Nenhum valor válido
#         # --------------------------------------------------

#         if not valores:
#             continue

#         # --------------------------------------------------
#         # Média diária
#         # --------------------------------------------------

#         valor_medio = np.mean(
#             valores
#         )

#         sat_dates.append(
#             pd.Timestamp(data_ref)
#         )

#         sat_values.append(
#             valor_medio * scale
#         )

#     print(
#         "RESULTADO GOES:",
#         sat_dates,
#         sat_values
#     )

#     return sat_dates, sat_values





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


