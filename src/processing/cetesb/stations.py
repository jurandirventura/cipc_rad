import pandas as pd


def load_stations(json_file):

    df_st = pd.read_json(json_file)

    df_st["codigo"] = pd.to_numeric(
        df_st["codigo"],
        errors="coerce"
    )

    stations_dict = (
        df_st
        .set_index("codigo")
        .to_dict("index")
    )

    return df_st, stations_dict