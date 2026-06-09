import os
import glob

import pandas as pd


def load_cetesb_data(
    input_dir,
    estacoes,
    poluentes,
    data_inicio,
    data_fim
):

    todos = []

    for estacao in estacoes:

        for poluente in poluentes:

            pattern = os.path.join(
                input_dir,
                f"{estacao}_{poluente}_*.csv"
            )

            arquivos = glob.glob(pattern)

            if not arquivos:

                print(
                    f"Nenhum arquivo encontrado: {pattern}"
                )
                continue

            for arquivo in arquivos:

                df = _read_single_csv(
                    arquivo,
                    poluente,
                    data_inicio,
                    data_fim,
                    estacao
                )

                if df is not None and not df.empty:

                    todos.append(df)

    if not todos:

        raise Exception(
            "Nenhum dado encontrado."
        )

    final = pd.concat(
        todos,
        ignore_index=True
    )

    final["estacao_codigo"] = (
        final["estacao_codigo"]
        .astype(str)
    )

    return final



# Função privada
def _read_single_csv(
    arquivo,
    poluente,
    data_inicio,
    data_fim,
    estacao
):

    print(f"Lendo: {arquivo}")

    try:

        df = pd.read_csv(
            arquivo,
            sep=";"
        )

    except Exception as e:

        print(
            f"Erro leitura {arquivo}: {e}"
        )

        return None

    df.columns = [
        str(c).strip()
        for c in df.columns
    ]

    if "Data" not in df.columns:

        return None

    df = df[df["Data"].notna()]

    if df.empty:

        return None

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

    # df.loc[
    #     mask_24,
    #     "datetime"
    # ] += pd.Timedelta(days=1)

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

    df = df[
        (df["datetime"] >= data_inicio)
        &
        (df["datetime"] <= data_fim)
    ]

    if df.empty:

        return None

    if "Valor Diário" not in df.columns:

        return None

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

        return None

    if "estacao_nome" in df.columns:

        nomes_validos = (
            df["estacao_nome"]
            .dropna()
        )

        if len(nomes_validos):

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
            .str.upper()
            .str.strip()
        )

        df["pollutant"] = (
            df["pollutant"]
            .replace({
                "MP2.5": "MP25",
                "MP2,5": "MP25",
                "PM25": "MP25",
                "PM10": "MP10"
            })
        )

    else:

        df["pollutant"] = poluente

    return df