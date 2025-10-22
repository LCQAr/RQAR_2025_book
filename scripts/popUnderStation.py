# -*- coding: utf-8 -*-
"""
Gera buffers e calcula população atendida por estação (REP_ESPACIAL)
Entrada: rep_espacial.csv
Saídas:
  - buffers_var.gpkg (com ID único)
  - populacao_varbuf.csv (ID + POP_BUFFER)
"""

import geopandas as gpd
import pandas as pd
from pathlib import Path
import os

rootPath    = Path(os.path.dirname(os.getcwd()))
SET_DIR     = rootPath / "data/setores_censitarios"
OUTPUT_DIR  = rootPath / "data/outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Arquivos de entrada
REP_CSV     = rootPath / "data/rep_espacial/outputs/rep_espacial.csv"
SET_GPKG    = SET_DIR / "BR_setores_pop2022.gpkg"

# Arquivos de saída
BUF_GPKG    = OUTPUT_DIR / "buffers_var.gpkg"
POP_CSV     = OUTPUT_DIR / "populacao_varbuf.csv"

# Nome da coluna de população nos setores
POP_COL     = "POP2022"


def generate_buffers(rep_csv=REP_CSV, out_gpkg=BUF_GPKG):
    rep = pd.read_csv(rep_csv, dtype={"ID_OEMA": str})

    gdf_pts = gpd.GeoDataFrame(
        rep.copy(),
        geometry=gpd.points_from_xy(rep["LONGITUDE"], rep["LATITUDE"]),
        crs="EPSG:4326"
    ).to_crs(5880)  # projeção em metros

    # gera buffers circulares
    gdf_pts["geometry"] = [
        geom.buffer(float(dist)) if pd.notna(dist) and float(dist) > 0 else None
        for geom, dist in zip(gdf_pts.geometry, gdf_pts["REP_ESPACIAL"])
    ]

    # adiciona ID único sequencial
    gdf_pts = gdf_pts.reset_index(drop=True).reset_index().rename(columns={"index": "ID"})

    # salva
    gdf_out = gdf_pts.to_crs(4326)  # volta para WGS84
    gdf_out.to_file(out_gpkg, driver="GPKG")
    print(f"✅ Buffers salvos em {out_gpkg} ({len(gdf_out)} registros)")
    return gdf_out


def calc_pop(setor_gpkg=SET_GPKG, buffer_gpkg=BUF_GPKG, pop_col=POP_COL, out_csv=POP_CSV):
    setores = gpd.read_file(setor_gpkg).to_crs(5880)
    buffers = gpd.read_file(buffer_gpkg).to_crs(5880)

    # garante ID
    if "ID" not in buffers.columns:
        buffers = buffers.reset_index(drop=True).reset_index().rename(columns={"index": "ID"})

    # interseção
    inter = gpd.overlay(setores, buffers, how="intersection")

    setores["AREA_SETOR"] = setores.geometry.area
    area_total_setor = setores.set_index("CD_SETOR")["AREA_SETOR"]

    inter["AREA_INTER"] = inter.geometry.area
    inter["FRAC"] = inter["AREA_INTER"] / inter["CD_SETOR"].map(area_total_setor)
    inter["POP_FRAC"] = inter[pop_col] * inter["FRAC"]

    # soma população por buffer
    pop_por_buffer = (inter.groupby("ID")["POP_FRAC"]
                             .sum()
                             .reset_index()
                             .rename(columns={"POP_FRAC": "POP_BUFFER"}))

    pop_por_buffer.to_csv(out_csv, index=False, encoding="utf-8")
    print(f"✅ População atendida salva em {out_csv}")
    return pop_por_buffer


if __name__ == "__main__":
    gdf_buf = generate_buffers()
    df_pop  = calc_pop()
