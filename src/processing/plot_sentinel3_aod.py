#!/usr/bin/env python3
"""
Leitura e plot do AOD 550 nm do produto Sentinel-3 / EUMETSAT.

O produto NRT_AOD.nc não possui uma variável chamada "aod550".
As variáveis relevantes são, entre outras:
    AOD_550                     -> melhor qualidade, somente oceano
    AOD_550_Land                -> somente terra
    AOD_550_Merged_OceanLand    -> campo combinado oceano + terra
    AOD_550_Ocean_NonFiltered   -> oceano, sem filtro pós-processamento

Para este produto, AOD_550_Merged_OceanLand é a variável recomendada
para um campo único de AOD550.
"""

from pathlib import Path
import argparse
import h5py
import numpy as np
import matplotlib.pyplot as plt


def read_eumetsat_aod(filename, variable="AOD_550_Merged_OceanLand"):
    """
    Lê uma variável AOD do NetCDF/HDF5 da EUMETSAT e aplica:
      - _FillValue
      - scale_factor
      - add_offset

    Retorna latitude, longitude, aod e atributos da variável.
    """
    with h5py.File(filename, "r") as f:
        if variable not in f:
            available = [k for k in f.keys() if "AOD" in k.upper()]
            raise KeyError(
                f"Variável '{variable}' não encontrada. "
                f"Variáveis AOD disponíveis: {available}"
            )

        dset = f[variable]
        raw = dset[:].astype(np.float64)

        fill = dset.attrs.get("_FillValue")
        if fill is not None:
            fill = np.asarray(fill).ravel()[0]
            raw[raw == fill] = np.nan

        scale = np.asarray(
            dset.attrs.get("scale_factor", 1.0)
        ).ravel()[0]
        offset = np.asarray(
            dset.attrs.get("add_offset", 0.0)
        ).ravel()[0]

        aod = raw * float(scale) + float(offset)

        latitude = f["latitude"][:].astype(np.float64)
        longitude = f["longitude"][:].astype(np.float64)

        attrs = {
            k: (
                np.asarray(v).ravel()[0].decode(errors="replace")
                if isinstance(v, (bytes, np.bytes_))
                else np.asarray(v).ravel()[0].item()
                if np.asarray(v).size == 1
                else v
            )
            for k, v in dset.attrs.items()
        }

    # Geolocalização inválida também vira NaN.
    aod[(latitude <= -90) | (latitude >= 90)] = np.nan
    aod[(longitude <= -180) | (longitude >= 180)] = np.nan

    return latitude, longitude, aod, attrs


def plot_aod550(
    filename,
    variable="AOD_550_Merged_OceanLand",
    output=None,
    vmin=0.0,
    vmax=None,
    cmap="viridis",
):
    lat, lon, aod, attrs = read_eumetsat_aod(filename, variable)

    valid = np.isfinite(aod)
    if not np.any(valid):
        raise RuntimeError(
            f"A variável {variable} não possui pixels válidos neste arquivo."
        )

    if vmax is None:
        # Limite robusto para evitar que poucos pixels extremos dominem a escala.
        vmax = float(np.nanpercentile(aod, 99))

    fig, ax = plt.subplots(figsize=(10, 7))

    pcm = ax.pcolormesh(
        lon,
        lat,
        aod,
        shading="auto",
        cmap=cmap,
        vmin=vmin,
        vmax=vmax,
    )

    cb = fig.colorbar(pcm, ax=ax, pad=0.02)
    cb.set_label("AOD 550 nm")

    ax.set_xlabel("Longitude (°)")
    ax.set_ylabel("Latitude (°)")
    ax.set_title(
        "Sentinel-3 / EUMETSAT — Aerosol Optical Depth (AOD) 550 nm\n"
        f"{variable}"
    )
    ax.grid(True, alpha=0.25)

    ax.set_xlim(np.nanmin(lon), np.nanmax(lon))
    ax.set_ylim(np.nanmin(lat), np.nanmax(lat))

    fig.tight_layout()

    if output:
        fig.savefig(output, dpi=180, bbox_inches="tight")
        print(f"Figura salva em: {output}")
    else:
        plt.show()

    print(f"Arquivo: {filename}")
    print(f"Variável: {variable}")
    print(f"Dimensão: {aod.shape}")
    print(f"Pixels válidos: {valid.sum()} / {aod.size}")
    print(f"AOD mínimo: {np.nanmin(aod):.4f}")
    print(f"AOD máximo: {np.nanmax(aod):.4f}")
    print(
        f"Latitude: {np.nanmin(lat):.4f} a {np.nanmax(lat):.4f}°"
    )
    print(
        f"Longitude: {np.nanmin(lon):.4f} a {np.nanmax(lon):.4f}°"
    )

    return lat, lon, aod


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("arquivo", help="Arquivo NRT_AOD.nc")
    parser.add_argument(
        "--variable",
        default="AOD_550_Merged_OceanLand",
        help="Variável AOD a plotar",
    )
    parser.add_argument("--output", default=None)
    parser.add_argument("--vmin", type=float, default=0.0)
    parser.add_argument("--vmax", type=float, default=None)
    args = parser.parse_args()

    plot_aod550(
        args.arquivo,
        variable=args.variable,
        output=args.output,
        vmin=args.vmin,
        vmax=args.vmax,
    )
