# SCRIPT FUNCIONANDO PARA O3 e CO do satélite
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import glob
import argparse

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import rasterio

import xarray as xr


"""
Plota séries temporais CETESB
(Médias Diárias)

+ Dados de satélite GeoTIFF
(O3 inicialmente)

=========================================================
EXEMPLO
=========================================================

*** Uso dos arquivos Projeção satélite
python src/processing/plot_sentinel_cetesb_proj_satelite.py \
--input ./csvs \
--stations-file ../cipc_data/cetesb/lista_estacoes.json \
--station 288 \
--pollutant all \
--start 15/08/2024 \
--end 25/08/2024 \
--sat-dir-o3 /home/jurandir/cipc_data/L2/O3/2024 \
--sat-dir-co /home/jurandir/cipc_data/L2/CO/2024 \
--sat-dir-ai /home/jurandir/cipc_data/L2/AER_AI/2024 \
--sat-delta-ai 0.20 \
--ai-scale 100 \
--output /home/jurandir/cipc_output/figures/cetesb/compara_sentinel5p_cetesb_ProjSatelite/

"""

# =========================================================
# ARGUMENTOS
# =========================================================

parser = argparse.ArgumentParser()

parser.add_argument(
    "--input",
    required=True,
    help="Diretório dos CSVs"
)

parser.add_argument(
    "--stations-file",
    required=True,
    help="Arquivo JSON lista_estacoes.json"
)

parser.add_argument(
    "--station",
    required=True,
    help="Código estação ou all"
)

parser.add_argument(
    "--pollutant",
    required=True,
    help="Poluente ou all"
)

parser.add_argument(
    "--start",
    required=True,
    help="Data inicial dd/mm/yyyy"
)

parser.add_argument(
    "--end",
    required=True,
    help="Data final dd/mm/yyyy"
)

parser.add_argument(
    "--sat-dir-o3",
    default="/home/jurandir/cipc_output/geotiff/ozone_total_vertical_column/2024",
    help="Diretório GeoTIFF O3 satélite"
)

parser.add_argument(
    "--sat-dir-co",
    default="/home/jurandir/cipc_output/geotiff/carbonmonoxide_total_column/2024",
    help="Diretório GeoTIFF CO satélite"
)

parser.add_argument(
    "--sat-dir-ai",
    default="/home/jurandir/cipc_output/geotiff/aerosol_index_354_388/2024",
    help="Diretório GeoTIFF Aerosol Index satélite"
)

parser.add_argument(
    "--sat-delta",
    type=float,
    default=0.5,
    help="Janela espacial em graus"
)

parser.add_argument(
    "--sat-delta-ai",
    type=float,
    default=0.20,
    help="Janela espacial Aerosol Index"
)

parser.add_argument(
    "--ai-scale",
    type=float,
    default=100.0,
    help="Fator de escala Aerosol Index"
)

parser.add_argument(
    "--o3-scale",
    type=float,
    default=1000.0
)

parser.add_argument(
    "--co-scale",
    type=float,
    default=100.0
)

parser.add_argument(
    "--output",
    default="../cipc_output/figures/cetesb",
    help="Diretório saída"
)


args = parser.parse_args()

INPUT_DIR = args.input
OUTPUT_DIR = args.output

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)

# =========================================================
# POLUENTES
# =========================================================

POLUENTES_VALIDOS = [
    "O3",
    "MP25",
    "MP10",
    "NO2",
    "SO2",
    "CO",
    "NO",
    "NOx"
]

if args.pollutant.lower() == "all":

    poluentes = POLUENTES_VALIDOS

else:

    poluentes = [args.pollutant]

# =========================================================
# DATAS
# =========================================================

DATA_INICIO = pd.to_datetime(
    args.start,
    dayfirst=True
)

DATA_FIM = (
    pd.to_datetime(
        args.end,
        dayfirst=True
    )
    + pd.Timedelta(days=1)
)

# =========================================================
# ESTAÇÕES
# =========================================================

df_st = pd.read_json(
    args.stations_file
)

if args.station.lower() == "all":

    estacoes = (
        df_st["codigo"]
        .astype(str)
        .tolist()
    )

else:

    estacoes = [str(args.station)]

# =========================================================
# FUNÇÃO SATÉLITE
# =========================================================

# Projeção satélite - Arquivos NetCDF
def get_satellite_mean_nc(
    nc_file,
    variable,
    lat_station,
    lon_station,
    delta=0.20,
    qa_min=None,
    method="mean"
):

    try:

        ds = xr.open_dataset(
            nc_file,
            group="PRODUCT"
        )

        lat = ds["latitude"].values
        lon = ds["longitude"].values

        var = ds[variable].values

        if qa_min is not None and "qa_value" in ds:

            qa = ds["qa_value"].values

            mask_qa = qa >= qa_min

        else:

            mask_qa = np.ones_like(
                var,
                dtype=bool
            )

        mask_geo = (
            (lat >= lat_station - delta)
            &
            (lat <= lat_station + delta)
            &
            (lon >= lon_station - delta)
            &
            (lon <= lon_station + delta)
        )

        values = var[
            mask_geo & mask_qa
        ]

        values = values[
            np.isfinite(values)
        ]

        if values.size == 0:

            return np.nan

        if method == "median":

            return float(
                np.nanmedian(values)
            )

        return float(
            np.nanmean(values)
        )

    except Exception as e:

        print(
            f"Erro NetCDF: {nc_file}"
        )
        print(e)

        return np.nan



def get_satellite_mean(
    tif_file,
    lat_station,
    lon_station,
    delta=0.5,
    method="mean"
):

    try:

        with rasterio.open(tif_file) as src:

            band = src.read(1)

            lon_min = lon_station - delta
            lon_max = lon_station + delta

            lat_min = lat_station - delta
            lat_max = lat_station + delta

            row_min, col_min = src.index(
                lon_min,
                lat_max
            )

            row_max, col_max = src.index(
                lon_max,
                lat_min
            )

            r0 = min(row_min, row_max)
            r1 = max(row_min, row_max)

            c0 = min(col_min, col_max)
            c1 = max(col_min, col_max)

            subset = band[
                r0:r1+1,
                c0:c1+1
            ]

            nodata = src.nodata

            if nodata is not None:

                subset = subset[
                    subset != nodata
                ]

            subset = subset[
                np.isfinite(subset)
            ]

            if subset.size == 0:

                return np.nan

            if method == "median":

                return float(
                    np.nanmedian(subset)
                )

            return float(
                np.nanmean(subset)
            )

    except Exception as e:

        print("Erro GeoTIFF:", e)
        return np.nan

# =========================================================
# LEITURA CSVs
# =========================================================

todos = []

for estacao in estacoes:

    for poluente in poluentes:

        pattern = os.path.join(
            INPUT_DIR,
            f"{estacao}_{poluente}_*.csv"
        )

        arquivos = glob.glob(pattern)

        if len(arquivos) == 0:

            print(f"Nenhum arquivo encontrado: {pattern}")
            continue

        for arquivo in arquivos:

            print(f"Lendo: {arquivo}")

            try:

                df = pd.read_csv(
                    arquivo,
                    sep=";"
                )

            except Exception as e:

                print("Erro leitura:", e)
                continue

            df.columns = [
                str(c).strip()
                for c in df.columns
            ]

            if "Data" not in df.columns:
                continue

            df = df[
                df["Data"].notna()
            ]

            if df.empty:
                continue

            if "Hora" not in df.columns:
                df["Hora"] = "00:00"

            df["Hora"] = (
                df["Hora"]
                .astype(str)
                .str.strip()
            )

            df.loc[
                (df["Hora"] == "")
                |
                (df["Hora"].str.lower() == "nan"),
                "Hora"
            ] = "00:00"

            df["Hora"] = df["Hora"].str[:5]

            mask_24 = (
                df["Hora"] == "24:00"
            )

            df.loc[
                mask_24,
                "Hora"
            ] = "00:00"

            df["datetime"] = pd.to_datetime(
                df["Data"].astype(str)
                + " "
                + df["Hora"].astype(str),
                format="%d/%m/%Y %H:%M",
                errors="coerce"
            )

            df.loc[
                mask_24,
                "datetime"
            ] = (
                df.loc[
                    mask_24,
                    "datetime"
                ]
                + pd.Timedelta(days=1)
            )

            df = df[
                df["datetime"].notna()
            ]

            if df.empty:
                continue

            df = df[
                (df["datetime"] >= DATA_INICIO)
                &
                (df["datetime"] <= DATA_FIM)
            ]

            if df.empty:
                continue

            if "Valor Diário" not in df.columns:
                continue

            df["Valor Diário"] = (
                df["Valor Diário"]
                .astype(str)
                .str.replace(",", ".", regex=False)
            )

            df["Valor Diário"] = pd.to_numeric(
                df["Valor Diário"],
                errors="coerce"
            )

            df = df[
                df["Valor Diário"].notna()
            ]

            if df.empty:
                continue

            if "estacao_nome" in df.columns:

                nomes_validos = (
                    df["estacao_nome"]
                    .dropna()
                )

                if len(nomes_validos) > 0:

                    nome_est = nomes_validos.iloc[0]

                else:

                    nome_est = str(estacao)

            else:

                nome_est = str(estacao)

            df["station_name"] = nome_est

            if "poluente" in df.columns:

                df["pollutant"] = (
                    df["poluente"]
                    .astype(str)
                    .str.strip()
                    .str.upper()
                )

                df["pollutant"] = (
                    df["pollutant"]
                    .replace({
                        "MP2.5": "MP25",
                        "MP2,5": "MP25",
                        "PM25": "MP25",
                        "PM10": "MP10",
                        "NOX": "NOx"
                    })
                )

            else:

                df["pollutant"] = poluente

            todos.append(df)

# =========================================================
# CONCATENA
# =========================================================

if len(todos) == 0:

    raise Exception(
        "Nenhum dado encontrado."
    )

final = pd.concat(
    todos,
    ignore_index=True
)

# =========================================================
# CORES
# =========================================================

CORES = {
    "O3": "blue",
    "NO2": "orange",
    "SO2": "green",
    "CO": "red",
    "MP10": "purple",
    "MP25": "brown",
    "NO": "gray",
    "NOx": "black"
}

UNIDADES = {
    "O3": "µg/m³",
    "NO2": "µg/m³",
    "SO2": "µg/m³",
    "CO": "ppm",
    "MP10": "µg/m³",
    "MP25": "µg/m³",
    "NO": "µg/m³",
    "NOx": "µg/m³"
}


UNIDADES_SAT = {
    "O3_SAT": "escalado",
    "CO_SAT": "escalado",
    "AI_SAT": "AER_AI"
}

print("\nPOLUENTES ENCONTRADOS:")
print(final["pollutant"].unique())

# =========================================================
# LOOP ESTAÇÕES
# =========================================================

for estacao in estacoes:

    print("\n===================================")
    print("PLOTANDO ESTAÇÃO:", estacao)
    print("===================================")

    sub_est = final[
        final["estacao_codigo"].astype(str)
        == str(estacao)
    ]

    if sub_est.empty:

        print("Sem dados para estação.")
        continue

    nome_estacao = (
        sub_est["station_name"]
        .iloc[0]
    )

    # =====================================================
    # LAT/LON
    # =====================================================

    st_info = df_st[
        df_st["codigo"].astype(str)
        == str(estacao)
    ]

    if st_info.empty:

        print("Sem lat/lon.")
        continue

    lat_station = float(
        st_info.iloc[0]["latitude"]
    )

    lon_station = float(
        st_info.iloc[0]["longitude"]
    )

    print("LAT:", lat_station)
    print("LON:", lon_station)

    # =====================================================
    # FIGURA
    # =====================================================

    fig, ax = plt.subplots(
        figsize=(20, 8)
    )

    axes = [ax]

    # =====================================================
    # PRIMEIRO POLUENTE
    # =====================================================

    pol0 = poluentes[0]

    sub0 = sub_est[
        sub_est["pollutant"] == pol0
    ]

    if not sub0.empty:

        ax.plot(
            sub0["datetime"],
            sub0["Valor Diário"],
            color=CORES.get(pol0, "blue"),
            label=pol0,
            linewidth=1.5,
            marker="o"
        )

        # =====================================================
        # CONVERSÃO SATÉLITE - Não utilizado
        # =====================================================
        # ALTURA_CAMADA = 35000.0  # metros
        # MASSA_MOLAR = {
        #     "O3": 48.0,
        #     "CO": 28.01
        # }


        # =================================================
        # SATÉLITE O3
        # =================================================


        CORES_SAT = {
        "O3_SAT": "cyan",
        "CO_SAT": "magenta",
        "AI_SAT": "darkgreen"
    }

        if pol0 == "O3":

            sat_dates = []
            sat_values = []

            datas_unicas = (
                sub0["datetime"]
                .dt.normalize()
                .unique()
            )

            for data_ref in datas_unicas:

                yyyymmdd = pd.Timestamp(
                    data_ref
                ).strftime("%Y%m%d")

                pattern_nc = os.path.join(
                    args.sat_dir_o3,
                    "**",
                    f"*{yyyymmdd}*.nc"
                )

                arquivos_nc = glob.glob(
                    pattern_nc,
                    recursive=True
                )
               
                if len(arquivos_nc) == 0:

                    print(
                        "O3 NetCDF não encontrado:",
                        yyyymmdd
                    )

                    continue

                nc_file = arquivos_nc[0]

                sat_mean = get_satellite_mean_nc(
                    arquivos_nc[0],
                    variable="ozone_total_vertical_column",
                    lat_station=lat_station,
                    lon_station=lon_station,
                    delta=args.sat_delta,
                    qa_min=0.75,
                    method="mean"
                )

                # =========================================
                # NORMALIZA O DADO SATÉLITE O3
                # =========================================
 
                if np.isfinite(sat_mean):

                    #sat_mean = sat_mean * 1000.0
                    #sat_mean = sat_mean * 1800.0
                    sat_mean *= args.o3_scale

                    # sat_mean = (
                    #     sat_mean
                    #     * MASSA_MOLAR["O3"]
                    #     * 1e6
                    #     / ALTURA_CAMADA
                    # )

                print(
                    "O3 SAT:",
                    yyyymmdd,
                    sat_mean
                )

                sat_dates.append(
                    pd.Timestamp(data_ref)
                )

                sat_values.append(
                    sat_mean
                )

            if len(sat_dates) > 0:

                ax.plot(
                    sat_dates,
                    sat_values,
                    color="cyan",
                    linestyle="--",
                    linewidth=1.5,
                    marker="*",
                    markersize=12,
                    label="O3_SAT"
                )

        # =================================================
        # SATÉLITE CO
        # =================================================

        ax.set_ylabel(
            f"{pol0} ({UNIDADES.get(pol0,'')})",
            color=CORES.get(pol0, "blue"),
            fontsize=12,
            fontweight="bold"
        )

        ax.tick_params(
            axis="y",
            colors=CORES.get(pol0, "blue")
        )

    # =====================================================
    # DEMAIS POLUENTES
    # =====================================================

    offset = 0

    for pol in poluentes[1:]:

        sat_dates_ai = []
        sat_values_ai = []


        sub = sub_est[
            sub_est["pollutant"] == pol
        ]

        if sub.empty:
            continue

        # =================================================
        # SATÉLITE CO
        # =================================================

        sat_dates_co = []
        sat_values_co = []

        if pol == "CO":

            datas_unicas = (
                sub["datetime"]
                .dt.normalize()
                .unique()
            )

            for data_ref in datas_unicas:

                yyyymmdd = pd.Timestamp(
                    data_ref
                ).strftime("%Y%m%d")

                pattern_nc = os.path.join(
                    args.sat_dir_co,
                    "**",
                    f"*{yyyymmdd}*.nc"
                )                

                arquivos_nc = glob.glob(
                    pattern_nc,
                    recursive=True
                )

                if len(arquivos_nc) == 0:

                    print(
                        "O3 NetCDF não encontrado:",
                        yyyymmdd
                    )

                    continue     

                nc_file = arquivos_nc[0]

                sat_mean = get_satellite_mean_nc(
                    arquivos_nc[0],
                    variable="carbonmonoxide_total_column",
                    lat_station=lat_station,
                    lon_station=lon_station,
                    delta=args.sat_delta,
                    qa_min=0.5,
                    method="mean"
                )                

                # =========================================
                # NORMALIZA CO SATÉLITE
                # =========================================

                if np.isfinite(sat_mean):

                    #sat_mean = sat_mean * 100000.0
                    #sat_mean = sat_mean * 100.0
                    sat_mean *= args.co_scale

                    # sat_mean = (
                    #     sat_mean
                    #     * MASSA_MOLAR["CO"]
                    #     * 1e6
                    #     / ALTURA_CAMADA
                    # )

                print(
                    "CO SAT:",
                    yyyymmdd,
                    sat_mean
                )

                sat_dates_co.append(
                    pd.Timestamp(data_ref)
                )

                sat_values_co.append(
                    sat_mean
                )

        offset += 0.07

        ax_new = ax.twinx()

        ax_new.spines["right"].set_position(
            ("axes", 1 + offset)
        )

        # =================================================
        # SATÉLITE AEROSOL INDEX
        # =================================================

        if pol in ["MP10", "MP25"]:

            datas_unicas = (
                sub["datetime"]
                .dt.normalize()
                .unique()
            )

            for data_ref in datas_unicas:

                yyyymmdd = pd.Timestamp(
                    data_ref
                ).strftime("%Y%m%d")

                pattern_nc = os.path.join(
                    args.sat_dir_ai,
                    "**",
                    f"*{yyyymmdd}*.nc"
                )     

                arquivos_nc = glob.glob(
                    pattern_nc,
                    recursive=True
                )                           

                if len(arquivos_nc) == 0:

                    print(
                        "O3 NetCDF não encontrado:",
                        yyyymmdd
                    )

                    continue

                nc_file = arquivos_nc[0]

                sat_mean = get_satellite_mean_nc(
                    arquivos_nc[0],
                    variable="aerosol_index_354_388",
                    lat_station=lat_station,
                    lon_station=lon_station,
                    delta=args.sat_delta_ai,
                    qa_min=0.8,
                    method="median"
                )                

                # =========================================
                # NORMALIZA AEROSOL INDEX
                # =========================================

                # if np.isfinite(sat_mean):

                #     #sat_mean = sat_mean
                #     sat_mean = sat_mean * 100
                sat_mean *= args.ai_scale

                if np.isfinite(sat_mean):

                    sat_mean = (
                        np.abs(sat_mean)
                        * args.ai_scale
                    )                    

                print(
                    "AI SAT:",
                    yyyymmdd,
                    sat_mean
                )

                sat_dates_ai.append(
                    pd.Timestamp(data_ref)
                )

                sat_values_ai.append(
                    sat_mean
                )



        # =================================================
        # ESTAÇÃO
        # =================================================

        ax_new.plot(
            sub["datetime"],
            sub["Valor Diário"],
            color=CORES.get(pol, "black"),
            label=pol,
            linewidth=1.5,
            marker="o"
        )

        # =================================================
        # CO SATÉLITE
        # =================================================

        if pol == "CO" and len(sat_dates_co) > 0:

            ax_new.plot(
                sat_dates_co,
                sat_values_co,
                color="magenta",
                linestyle="--",
                linewidth=1.5,
                marker="*",
                markersize=12,
                label="CO_SAT"
            )

        ax_new.set_ylabel(
            f"{pol} ({UNIDADES.get(pol,'')})",
            color=CORES.get(pol, "black"),
            fontsize=12,
            fontweight="bold"
        )

        ax_new.tick_params(
            axis="y",
            colors=CORES.get(pol, "black")
        )

        axes.append(ax_new)


        # =================================================
        # AEROSOL INDEX SATÉLITE
        # =================================================

        if pol in ["MP10", "MP25"] and len(sat_dates_ai) > 0:

            ax_new.plot(
                sat_dates_ai,
                sat_values_ai,
                color="darkgreen",
                linestyle="--",
                linewidth=1.5,
                marker="s",
                markersize=8,
                label="AI_SAT"
            )


    # =====================================================
    # TÍTULO
    # =====================================================

    plt.title(
        "Qualidade do Ar - Médias Diárias\n"
        f"Estação: {estacao} - {nome_estacao}\n"
        f"Período: {args.start} a {args.end}",
        fontsize=16,
        fontweight="bold"
    )

    # =====================================================
    # GRID
    # =====================================================

    ax.grid(
        True,
        linestyle="--",
        alpha=0.4
    )

    # =====================================================
    # LEGENDA
    # =====================================================

    lines = []
    labels = []

    for a in axes:

        for ln in a.get_lines():

            lines.append(ln)
            labels.append(ln.get_label())

    ax.legend(
        lines,
        labels,
        loc="upper left"
    )

    plt.xlabel("Data")

    # =====================================================
    # SAVE
    # =====================================================

    output_png = os.path.join(
        OUTPUT_DIR,
        f"{estacao}_{args.pollutant}_timeseries_MediaDiaria_compara.png"
    )

    plt.savefig(
        output_png,
        dpi=150,
        bbox_inches="tight"
    )

    print("\n===================================")
    print("FIGURA GERADA")
    print(output_png)
    print("===================================")

    plt.close()

