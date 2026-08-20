# Organiza a leitura dos produtos de satélite

### FUNCIONA PARA GOES-AOD MAS NÃO PARA SENTINEL-5P
import pandas as pd
import numpy as np
from satellite.raster_reader import get_satellite_mean

#--------------------

### CHAT PEDIU PARA MANTER ESSE SCRIPT
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

        yyyymmdd = pd.Timestamp(data_ref).strftime("%Y%m%d")

        arquivos = sat_index.get(yyyymmdd)

        print(
            "DATA:",
            yyyymmdd,
            "ARQUIVOS:",
            len(arquivos) if isinstance(arquivos, list) else arquivos
        )

        if arquivos is None:
            continue

        if isinstance(arquivos, str):
            arquivos = [arquivos]

        valores = []

        for tif_file in arquivos:

            valor = get_satellite_mean(
                tif_file,
                lat_station,
                lon_station,
                delta
            )

            print(
                "SAT:",
                tif_file,
                "=>",
                valor
            )

            if np.isfinite(valor):
                valores.append(valor)

        if not valores:
            continue

        valor_medio = np.mean(valores)

        sat_dates.append(
            pd.Timestamp(data_ref)
        )

        sat_values.append(
            valor_medio * scale
        )

    print(
        "RESULTADO SAT:",
        sat_dates,
        sat_values
    )

    return sat_dates, sat_values


# #------------------

# =========================================================
# GOES-16 AOD
#
# Seleciona 1 arquivo por hora, preferencialmente o mais
# próximo da hora cheia, e calcula a média diária.
#
# Janela desejada:
#
#   06:00 - 18:00 horário local de São Paulo
#
# Como GOES utiliza UTC:
#
#   09:00 - 21:00 UTC
# =========================================================

def get_goes_series_hourly(
    goes_index,
    datas_unicas,
    lat_station,
    lon_station,
    delta,
    scale=1.0
):

    import re
    import time

    print("\n")
    print("==============================================")
    print("===== GET GOES SERIES HOURLY ================")
    print("==============================================")

    print("Lat:", lat_station)
    print("Lon:", lon_station)
    print("Delta:", delta)
    print("Scale:", scale)
    print("Datas:", datas_unicas)
    print("Índice possui:", len(goes_index), "dias")

    goes_dates = []
    goes_values = []

    inicio_total = time.perf_counter()

    # =====================================================
    # HORÁRIO DE INTERESSE
    #
    # São Paulo:
    #   06:00 até 18:00
    #
    # GOES:
    #   09:00 até 21:00 UTC
    #
    # =====================================================

    HORA_UTC_INICIAL = 9
    HORA_UTC_FINAL = 21

    # =====================================================
    # LOOP DOS DIAS
    # =====================================================

    for data_ref in datas_unicas:

        inicio_dia = time.perf_counter()

        data_ref = pd.Timestamp(data_ref)

        yyyymmdd = data_ref.strftime("%Y%m%d")

        print("\n==============================================")
        print("GOES DATA:", yyyymmdd)
        print("==============================================")

        # =================================================
        # PEGA OS ARQUIVOS DIRETAMENTE PELO DIA
        # =================================================

        arquivos = goes_index.get(
            yyyymmdd
        )

        print(
            "ARQUIVOS DO DIA:",
            len(arquivos)
            if isinstance(arquivos, list)
            else arquivos
        )

        if arquivos is None:

            print(
                "GOES: nenhum arquivo encontrado para",
                yyyymmdd
            )

            continue

        # -------------------------------------------------
        # Se vier apenas uma string
        # -------------------------------------------------

        if isinstance(arquivos, str):

            arquivos = [
                arquivos
            ]

        # =================================================
        # SELECIONA 1 ARQUIVO POR HORA
        # =================================================

        arquivos_horarios = {}

        for tif_file in arquivos:

            nome = str(tif_file)

            # -------------------------------------------------
            # Procura YYYYMMDD_HHMMSS
            # -------------------------------------------------

            match = re.search(
                r"(\d{8})_(\d{6})",
                nome
            )

            if not match:

                print(
                    "GOES: timestamp não encontrado:",
                    nome
                )

                continue

            data_str = match.group(1)

            hora_str = match.group(2)

            # -------------------------------------------------
            # Garante que é realmente o dia solicitado
            # -------------------------------------------------

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

            # =================================================
            # FILTRO DE HORÁRIO
            #
            # 06:00 - 18:00 LOCAL
            # =
            # 09:00 - 21:00 UTC
            # =================================================

            if hora < HORA_UTC_INICIAL:
                continue

            if hora > HORA_UTC_FINAL:
                continue

            # -------------------------------------------------
            # Distância até a hora cheia
            # -------------------------------------------------

            segundos_desde_hora = (
                minuto * 60 +
                segundo
            )

            distancia = min(
                segundos_desde_hora,
                3600 - segundos_desde_hora
            )

            # -------------------------------------------------
            # Verifica se já existe arquivo selecionado
            # para esta hora
            # -------------------------------------------------

            atual = arquivos_horarios.get(
                hora
            )

            # -------------------------------------------------
            # Guarda o arquivo mais próximo da hora cheia
            # -------------------------------------------------

            if (
                atual is None
                or distancia < atual["distancia"]
            ):

                arquivos_horarios[hora] = {

                    "arquivo": tif_file,

                    "distancia": distancia,

                    "hora_str": hora_str
                }

        # =================================================
        # ARQUIVOS SELECIONADOS
        # =================================================

        arquivos_selecionados = [

            arquivos_horarios[h]

            for h in sorted(
                arquivos_horarios
            )
        ]

        print(
            "ARQUIVOS ENCONTRADOS:",
            len(arquivos)
        )

        print(
            "ARQUIVOS SELECIONADOS:",
            len(arquivos_selecionados),
            "(1 por hora)"
        )

        # -------------------------------------------------
        # Mostra os arquivos selecionados
        # -------------------------------------------------

        for item in arquivos_selecionados:

            print(
                "  HORA UTC:",
                item["hora_str"],
                "| distância:",
                item["distancia"],
                "s",
                "| arquivo:",
                item["arquivo"]
            )

        # =================================================
        # CALCULA VALORES HORÁRIOS
        # =================================================

        valores = []

        for item in arquivos_selecionados:

            tif_file = item["arquivo"]

            hora_str = item["hora_str"]

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
                yyyymmdd,
                hora_str,
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

            print(
                "GOES:",
                yyyymmdd,
                "=> NENHUM VALOR VÁLIDO"
            )

            continue

        # =================================================
        # MÉDIA DO PERÍODO DIURNO
        # =================================================

        valor_medio = np.mean(
            valores
        )

        valor_final = (
            valor_medio * scale
        )

        goes_dates.append(
            data_ref
        )

        goes_values.append(
            valor_final
        )

        tempo_dia = (
            time.perf_counter()
            - inicio_dia
        )

        print(
            "GOES MÉDIA 06-18 LOCAL:",
            yyyymmdd,
            "=>",
            valor_final
        )

        print(
            "QUANTIDADE DE HORÁRIOS:",
            len(valores)
        )

        print(
            f"TEMPO DIA {yyyymmdd}: "
            f"{tempo_dia:.3f}s"
        )

    # =====================================================
    # RESULTADO FINAL
    # =====================================================

    tempo_total = (
        time.perf_counter()
        - inicio_total
    )

    print("\n")
    print("==============================================")
    print("===== RESULTADO GOES HOURLY ==================")
    print("==============================================")

    print(
        "DATAS:",
        goes_dates
    )

    print(
        "VALORES:",
        goes_values
    )

    print(
        f"TEMPO TOTAL GOES = "
        f"{tempo_total:.3f}s"
    )

    return goes_dates, goes_values



##########################################################
# # ------------------- funcionou para média de 24 horas
##########################################################
# def get_goes_series_hourly(
#     goes_index,
#     datas_unicas,
#     lat_station,
#     lon_station,
#     delta,
#     scale=1.0
# ):

#     import re
#     import time

#     print("\n")
#     print("==============================================")
#     print("===== GET GOES SERIES HOURLY ================")
#     print("==============================================")

#     print("Lat:", lat_station)
#     print("Lon:", lon_station)
#     print("Delta:", delta)
#     print("Scale:", scale)
#     print("Datas:", datas_unicas)
#     print("Índice possui:", len(goes_index), "dias")

#     goes_dates = []
#     goes_values = []

#     inicio_total = time.perf_counter()

#     # =====================================================
#     # LOOP DOS DIAS
#     # =====================================================

#     for data_ref in datas_unicas:

#         inicio_dia = time.perf_counter()

#         data_ref = pd.Timestamp(data_ref)

#         yyyymmdd = data_ref.strftime("%Y%m%d")

#         print("\n==============================================")
#         print("GOES DATA:", yyyymmdd)
#         print("==============================================")

#         # =================================================
#         # PEGA OS ARQUIVOS DIRETAMENTE PELO DIA
#         # =================================================

#         arquivos = goes_index.get(
#             yyyymmdd
#         )

#         print(
#             "ARQUIVOS DO DIA:",
#             len(arquivos)
#             if isinstance(arquivos, list)
#             else arquivos
#         )

#         if arquivos is None:

#             print(
#                 "GOES: nenhum arquivo encontrado para",
#                 yyyymmdd
#             )

#             continue

#         # -------------------------------------------------
#         # Se vier apenas uma string
#         # -------------------------------------------------

#         if isinstance(arquivos, str):

#             arquivos = [
#                 arquivos
#             ]

#         # =================================================
#         # SELECIONA 1 ARQUIVO POR HORA
#         # =================================================

#         arquivos_horarios = {}

#         for tif_file in arquivos:

#             nome = str(tif_file)

#             # -------------------------------------------------
#             # Procura YYYYMMDD_HHMMSS
#             # -------------------------------------------------

#             match = re.search(
#                 r"(\d{8})_(\d{6})",
#                 nome
#             )

#             if not match:

#                 print(
#                     "GOES: timestamp não encontrado:",
#                     nome
#                 )

#                 continue

#             data_str = match.group(1)

#             hora_str = match.group(2)

#             # -------------------------------------------------
#             # Garante que é realmente o dia solicitado
#             # -------------------------------------------------

#             if data_str != yyyymmdd:

#                 continue

#             hora = int(
#                 hora_str[0:2]
#             )

#             minuto = int(
#                 hora_str[2:4]
#             )

#             segundo = int(
#                 hora_str[4:6]
#             )

#             # -------------------------------------------------
#             # Distância até a hora cheia
#             # -------------------------------------------------

#             segundos_desde_hora = (
#                 minuto * 60 +
#                 segundo
#             )

#             distancia = min(
#                 segundos_desde_hora,
#                 3600 - segundos_desde_hora
#             )

#             # -------------------------------------------------
#             # Verifica se já existe arquivo selecionado
#             # para esta hora
#             # -------------------------------------------------

#             atual = arquivos_horarios.get(
#                 hora
#             )

#             # -------------------------------------------------
#             # Guarda o arquivo mais próximo da hora cheia
#             # -------------------------------------------------

#             if (
#                 atual is None
#                 or distancia < atual["distancia"]
#             ):

#                 arquivos_horarios[hora] = {

#                     "arquivo": tif_file,

#                     "distancia": distancia,

#                     "hora_str": hora_str
#                 }

#         # =================================================
#         # ARQUIVOS SELECIONADOS
#         # =================================================

#         arquivos_selecionados = [

#             arquivos_horarios[h]

#             for h in sorted(
#                 arquivos_horarios
#             )
#         ]

#         print(
#             "ARQUIVOS ENCONTRADOS:",
#             len(arquivos)
#         )

#         print(
#             "ARQUIVOS SELECIONADOS:",
#             len(arquivos_selecionados),
#             "(1 por hora)"
#         )

#         # -------------------------------------------------
#         # Mostra os arquivos selecionados
#         # -------------------------------------------------

#         for item in arquivos_selecionados:

#             print(
#                 "  HORA:",
#                 item["hora_str"],
#                 "| distância:",
#                 item["distancia"],
#                 "s",
#                 "| arquivo:",
#                 item["arquivo"]
#             )

#         # =================================================
#         # CALCULA VALORES HORÁRIOS
#         # =================================================

#         valores = []

#         for item in arquivos_selecionados:

#             tif_file = item["arquivo"]

#             hora_str = item["hora_str"]

#             inicio_tif = time.perf_counter()

#             valor = get_satellite_mean(
#                 tif_file,
#                 lat_station,
#                 lon_station,
#                 delta
#             )

#             tempo_tif = (
#                 time.perf_counter()
#                 - inicio_tif
#             )

#             print(
#                 "GOES:",
#                 yyyymmdd,
#                 hora_str,
#                 "=>",
#                 valor,
#                 f"tempo={tempo_tif:.3f}s"
#             )

#             if np.isfinite(valor):

#                 valores.append(
#                     valor
#                 )

#         # =================================================
#         # NENHUM VALOR VÁLIDO
#         # =================================================

#         if not valores:

#             print(
#                 "GOES:",
#                 yyyymmdd,
#                 "=> NENHUM VALOR VÁLIDO"
#             )

#             continue

#         # =================================================
#         # MÉDIA DIÁRIA
#         # =================================================

#         valor_medio = np.mean(
#             valores
#         )

#         valor_final = (
#             valor_medio * scale
#         )

#         goes_dates.append(
#             data_ref
#         )

#         goes_values.append(
#             valor_final
#         )

#         tempo_dia = (
#             time.perf_counter()
#             - inicio_dia
#         )

#         print(
#             "GOES MÉDIA DIÁRIA:",
#             yyyymmdd,
#             "=>",
#             valor_final
#         )

#         print(
#             f"TEMPO DIA {yyyymmdd}: "
#             f"{tempo_dia:.3f}s"
#         )

#     # =====================================================
#     # RESULTADO FINAL
#     # =====================================================

#     tempo_total = (
#         time.perf_counter()
#         - inicio_total
#     )

#     print("\n")
#     print("==============================================")
#     print("===== RESULTADO GOES HOURLY ==================")
#     print("==============================================")

#     print(
#         "DATAS:",
#         goes_dates
#     )

#     print(
#         "VALORES:",
#         goes_values
#     )

#     print(
#         f"TEMPO TOTAL GOES = "
#         f"{tempo_total:.3f}s"
#     )

#     return goes_dates, goes_values

#--------------------

### Essa função não está sendo utilizada....  
### Verificar, se realmente não estiver sendo usada, remover
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

            print("\n>>> TESTANDO ARQUIVO GOES")
            print("KEY =", key)
            print("ARQUIVO =", tif_file)
            print("LAT =", lat_station)
            print("LON =", lon_station)
            print("DELTA =", delta)          
            print(">>> RESULTADO =", valor)

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

