# -*- coding: utf-8 -*-
"""
Gera GeoJSONs de representatividade por uso do solo (MapBiomas)
Arquivos separados por poluente.

Saída:
    _static/representatividade/uso_solo_geojson/<POLUENTE>.geojson

Execução:
    python3 gerar_geojson_uso_solo.py
"""

import os
from pathlib import Path
import pandas as pd
import geopandas as gpd
import numpy as np
import scripts.stationsLandUse as stl


# ==========================
# CONFIGURAÇÕES
# ==========================
rootPath = Path("/home/nobre/Notebooks/RQAR_2025_book")

CSV_PATH = (
    rootPath
    / "scripts"
    / "rep_espacial"
    / "09_formatar_e_salvar_outputs"
    / "outputs"
    / "rep_espacial.csv"
)

MAPBIOMAS_FOLDER = rootPath / "data" / "MAPBIOMAS"

OUT_DIR = rootPath / "_static" / "representatividade" / "uso_solo_geojson"
OUT_DIR.mkdir(parents=True, exist_ok=True)

LAND_USE_MAP = {
    "Floresta": ["1","3","4","5","6","49"],
    "Herbácea": ["10","11","12","32","29","50"],
    "Agropecuária": ["14","15","18","19","39","20","40","62","41","36","46","47","35","48","9","21"],
    "Não Vegetada": ["22","23","25","26","33","31","27"],
    "Urbanizada": ["24"],
    "Mineração": ["30"],
}
GROUPS = list(LAND_USE_MAP.keys())

pollutant_map = {
    "PM10": "MP10",
    "PM25": "MP25",
    "PM1": None,
    "VOC": None,
}


# ==========================
# FUNÇÃO PRINCIPAL
# ==========================
def gerar_geojsons():

    print("📥 Lendo CSV:", CSV_PATH)
    df = pd.read_csv(CSV_PATH)

    # Normalização de poluentes
    df["POLUENTE"] = df["POLUENTE"].replace(pollutant_map)
    df = df[df["POLUENTE"].notna()]

    # Criar GeoDataFrame inicial
    coords = gpd.points_from_xy(df["LONGITUDE"], df["LATITUDE"])
    gdf = gpd.GeoDataFrame(df.copy(), geometry=coords, crs="EPSG:4326")

    # Identificar poluentes
    poluentes = sorted(gdf["POLUENTE"].dropna().unique())
    print("🔎 Poluentes encontrados:", poluentes)
    print()

    # -------------------------------------
    # LOOP PRINCIPAL
    # -------------------------------------
    for pol in poluentes:

        print(f"➡ Processando {pol} ...")

        gpol = gdf[gdf["POLUENTE"] == pol].copy()

        # ============ buffers ============
        gpol_m = gpol.to_crs(3857)
        buffers = [
            geom.buffer(float(dist)) if pd.notna(dist) and dist > 0 else None
            for geom, dist in zip(gpol_m.geometry, gpol_m["REP_ESPACIAL"])
        ]
        gvar = gpol_m.copy()
        gvar["geometry"] = buffers
        gvar = gvar.to_crs(4326)
        gvar = gvar[~gvar.geometry.isna()].copy()

        # ============ uso do solo ============
        stats = stl.cutMapbiomas(str(MAPBIOMAS_FOLDER), gvar, 2024, "", 30 * 30)

        dfu = stats.copy()
        for gname, codes in LAND_USE_MAP.items():
            dfu[gname] = dfu.filter(codes).sum(axis=1, min_count=1)

        sums = dfu[GROUPS].sum(axis=1).replace(0, np.nan)
        for g in GROUPS:
            dfu[f"{g}_perc"] = (100 * dfu[g] / sums).round(1)

        # Junta com geometrias originais
        gfinal = gvar.join(
            dfu[GROUPS + [f"{g}_perc" for g in GROUPS]]
        )

        # ============ centróides ============
        gcent = gfinal.to_crs(3857)
        gcent["geometry"] = gcent.geometry.centroid
        gcent = gcent.to_crs(4326)

        # ============ salvar ============
        out_file = OUT_DIR / f"{pol}.geojson"
        gcent.to_file(out_file, driver="GeoJSON")

        print(f"   ✔ GeoJSON gerado: {out_file}")

    print("\n🎉 Finalizado: todos os GeoJSONs foram gerados com sucesso.")


# ==========================
# ENTRYPOINT
# ==========================
if __name__ == "__main__":
    gerar_geojsons()
