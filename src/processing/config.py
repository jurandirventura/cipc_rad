# config.py

def create_sat_config(sat_index):

    return {

        "O3": {
            "index": sat_index["O3"],
            "scale": 1000.0,
            "color": "cyan",
            "marker": "*",
            "label": "O3_SAT*1000"
        },

        "CO": {
            "index": sat_index["CO"],
            "scale": 100.0,
            "color": "magenta",
            "marker": "*",
            "label": "CO_SAT*100"
        },

        "NO2": {
            "index": sat_index["NO2"],
            "scale": 1e6,
            "color": "gold",
            "marker": "^",
            "label": "NO2_SAT*1e6"
        },

        "SO2": {
            "index": sat_index["SO2"],
            "scale": 1e6,
            "color": "limegreen",
            "marker": "D",
            "label": "SO2_SAT*1e6"
        },

        "AI": {
            "index": sat_index["AI"],
            "scale": 100.0,
            "color": "darkviolet",
            "marker": "s",
            "label": "AI_SAT*100"
        },

        "CH4": {
            "index": sat_index["CH4"],
            "scale": 1.0,
            "color": "olive",
            "marker": "P",
            "label": "CH4_SAT"
        }
    }