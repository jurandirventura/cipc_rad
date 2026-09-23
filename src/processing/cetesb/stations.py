import pandas as pd


def load_stations(json_file):

    df_st = pd.read_json(json_file)

    print("\n========== ESTAÇÕES ==========")
    print("Arquivo:", json_file)
    print("Linhas:", len(df_st))
    print("Colunas:", df_st.columns.tolist())

    df_st["codigo"] = pd.to_numeric(
        df_st["codigo"],
        errors="coerce"
    )

    print("Códigos nulos:", df_st["codigo"].isna().sum())
    print("Códigos únicos:", df_st["codigo"].nunique())
    print("Total de códigos:", len(df_st))

    duplicados = df_st[
        df_st["codigo"].duplicated(keep=False)
    ].sort_values("codigo")

    if not duplicados.empty:
        print("\n*** CÓDIGOS DUPLICADOS ***")
        print(duplicados.to_string(index=False))
        print("\n============================\n")

        raise ValueError(
            "Existem códigos de estação duplicados no lista_estacoes.json"
        )

    stations_dict = (
        df_st
        .set_index("codigo")
        .to_dict("index")
    )

    return df_st, stations_dict




# import pandas as pd


# def load_stations(json_file):

#     df_st = pd.read_json(json_file)

#     df_st["codigo"] = pd.to_numeric(
#         df_st["codigo"],
#         errors="coerce"
#     )

#     stations_dict = (
#         df_st
#         .set_index("codigo")
#         .to_dict("index")
#     )

#     return df_st, stations_dict