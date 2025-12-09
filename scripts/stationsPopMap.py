#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gera GEOJSONs separados por poluente:
- MP25.geojson
- MP10.geojson
- CO.geojson
- NO2.geojson
- PTS.geojson
- SO2.geojson
- O3.geojson

Uso no terminal:
    python3 gerar_geojson_pop.py
"""

import geopandas as gpd
import pandas as pd
from pathlib import Path
import os
import sys


# ================================================================
# 1) Caminhos
# ================================================================
rootPath = Path(os.path.dirname(os.getcwd()))
OUTPUT_DIR = rootPath / "data" / "outputs"

BUFFER_PATH = OUTPUT_DIR / "buffers_var.gpkg"
POP_PATH    = OUTPUT_DIR / "populacao_varbuf.csv"

GJSON_DIR   = rootPath / "_static" / "representatividade" / "populacao_geojson"
GJSON_DIR.mkdir(parents=True, exist_ok=True)

# Poluentes desejados
POL_VALIDOS = ["MP25", "MP10", "CO", "NO2", "PTS", "SO2", "O3"]


# ================================================================
# 2) Função principal
# ================================================================
def build_pop_geojson_by_pollutant():

    print("📥 Lendo buffers:", BUFFER_PATH)
    try:
        buf = gpd.read_file(BUFFER_PATH)
    except Exception as e:
        print("❌ Erro lendo buffers_var.gpkg:", e)
        sys.exit(1)

    print("📥 Lendo populacao:", POP_PATH)
    try:
        pop = pd.read_csv(POP_PATH)
    except Exception as e:
        print("❌ Erro lendo populacao_varbuf.csv:", e)
        sys.exit(1)

    # Garantir WGS84
    if buf.crs is None:
        print("❌ CRS ausente no arquivo buffers_var.gpkg.")
        sys.exit(1)

    buf = buf.to_crs(4326)

    # Filtrar poluentes
    buf = buf[buf["POLUENTE"].isin(POL_VALIDOS)].copy()

    print("\nPoluentes no dataset:", sorted(buf["POLUENTE"].unique()))

    # Padronizar IDs
    buf["ID"] = buf["ID_OEMA"].astype(str).str.strip()
    pop["ID"] = pop["ID_OEMA"].astype(str).str.strip()

    df = buf.merge(pop, on="ID", how="left")

    props = ["ID", "UF", "POLUENTE", "POP_BUFFER", "REP_ESPACIAL"]

    print("\n🔧 Gerando arquivos...")

    outputs = {}

    for pol in POL_VALIDOS:
        gdf_pol = df[df["POLUENTE"] == pol][props + ["geometry"]].copy()

        if gdf_pol.empty:
            print(f"⚠️ {pol}: sem registros — não criado.")
            continue

        out_file = GJSON_DIR / f"{pol}.geojson"
        gdf_pol.to_file(out_file, driver="GeoJSON")

        outputs[pol] = out_file
        print(f"✔ Criado: {out_file}")

    print("\n🏁 Concluído!")
    return outputs


# ================================================================
# 3) Execução direta pelo terminal
# ================================================================
if __name__ == "__main__":
    build_pop_geojson_by_pollutant()
