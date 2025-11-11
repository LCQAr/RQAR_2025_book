#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gera GeoJSONs de representatividade (buffers + estações + indústrias + ruas)
Autor: Robson Will
Atualizado: 2025-11-05
"""

import geopandas as gpd
import pandas as pd
from pathlib import Path

# =======================
# CONFIGURAÇÕES INICIAIS
# =======================
INPUT_DIR = Path("/home/nobre/Notebooks/RQAR_2025_book/scripts/rep_espacial/09_formatar_e_salvar_outputs/inputs")
OUTPUT_DIR = Path("/home/nobre/Notebooks/RQAR_2025_book/_static/mapas/estacoes_industrias")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# arquivos parquet (um por poluente)
arquivos = {
    "PM10": "buffered_subset_pm.parquet",
    "PM25": "buffered_subset_pm.parquet",  # caso o arquivo combine PMs
    "NO2": "buffered_subset_no2.parquet",
    "SO2": "buffered_subset_so2.parquet",
    "O3": "buffered_subset_o3.parquet",
    "CO": "buffered_subset_co.parquet",
}

# =======================
# FUNÇÃO AUXILIAR
# =======================
def preparar_geojson(gdf: gpd.GeoDataFrame, poluente: str, tipo: str):
    """Filtra, formata e exporta GeoJSON único por poluente/tipo."""
    if gdf.empty:
        print(f"⚠️ Nenhum dado para {poluente}/{tipo}")
        return

    # garante CRS 4326
    gdf = gdf.to_crs(4326)

    # converte geometria secundária (industry_geom) para texto, se existir
    if "industry_geom" in gdf.columns:
        try:
            gdf["industry_wkt"] = gdf["industry_geom"].to_wkt()
        except Exception:
            gdf["industry_wkt"] = None
        gdf = gdf.drop(columns=["industry_geom"])

    # seleciona colunas relevantes
    colunas = [
        "UF", "CIDADE", "ID_MMA", "ID_MMA_COMPLETO", "ID_OEMA",
        "REP_ESPACIAL", "REP_ESPACIAL_DECLARADA", "POLUENTE",
        "osm_id_mais_prox_valida", "distance_70k",
        "industry_wkt", "geometry"
    ]
    colunas_existentes = [c for c in colunas if c in gdf.columns]
    gdf = gdf[colunas_existentes].copy()

    # define diretório e exporta
    out_dir = OUTPUT_DIR / tipo
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{poluente}.geojson"

    gdf = gdf.set_geometry("geometry")
    gdf.to_file(out_file, driver="GeoJSON")

    print(f"✅ {tipo.title()}: {poluente}.geojson salvo ({len(gdf)} feições)")



# =======================
# PROCESSAMENTO
# =======================
for pol, arq in arquivos.items():
    path = INPUT_DIR / arq
    if not path.exists():
        print(f"⚠️ Arquivo não encontrado: {path.name}")
        continue

    print(f"🔹 Lendo {path.name}...")
    gdf = gpd.read_parquet(path)
    if gdf.empty:
        print(f"⚠️ {pol}: sem dados.")
        continue

    # Separa por tipo (estimada / declarada)
    gdf_est = gdf[gdf["REP_ESPACIAL"].notna()].copy()
    gdf_dec = gdf[gdf["REP_ESPACIAL_DECLARADA"].notna()].copy()

    preparar_geojson(gdf_est, pol, "estimada")
    preparar_geojson(gdf_dec, pol, "declarada")

print("🏁 Finalizado: GeoJSONs prontos para o mapa interativo.")
