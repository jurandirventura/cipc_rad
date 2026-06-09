# plotting/legends.py

LEGEND_ORDER = [

    "O3",
    "O3_SAT*1000",

    "MP25",
    "MP10",
    "AI_SAT*100",

    "NO2",
    "NO2_SAT*1e6",

    "SO2",
    "SO2_SAT*1e6",

    "CO",
    "CO_SAT*100",

    "CH4_SAT"
]


def build_legend(ax, axes):

    legend_dict = {}

    for a in axes:

        for line in a.get_lines():

            label = line.get_label()

            if label.startswith("_"):
                continue

            legend_dict.setdefault(label, line)

    lines = []
    labels = []

    for label in LEGEND_ORDER:

        if label in legend_dict:

            lines.append(
                legend_dict[label]
            )

            labels.append(
                label
            )

    ax.legend(
        lines,
        labels,
        loc="upper left",
        fontsize=9
    )