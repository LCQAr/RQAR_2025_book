# -*- coding: utf-8 -*-
"""
popUnderStationREP.py
Funções para:
1) Consolidar setores censitários + população (Censo 2022)
2) Gerar buffers oficiais a partir da coluna REP_ESPACIAL (classificação)
3) Calcular população atendida por estação (REP_ESPACIAL → ID_MMA_COMPLETO)
"""

import geopandas as gpd
import pandas as pd
from pathlib import Path
import os
import logging

# ========================
# Configurações globais
# ========================
rootPath    = Path(os.path.dirname(os.getcwd()))
SET_DIR     = rootPath / "data/setores_censitarios"
OUTPUT_DIR  = rootPath / "data/outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CSV_ATTR    = SET_DIR / "BR_setores_CD2022.csv"
GPKG_POP    = SET_DIR / "BR_setores_pop2022.gpkg"

BUFFER_PATH = OUTPUT_DIR / "buffers_var.gpkg"
REP_CSV     = rootPath / "data" / "Monitoramento_QAr_BR.csv"

POP_COL     = "v0001"


# ========================
# Consolida setores + população
# ========================
def consolidar_setores(csv_path=CSV_ATTR, shp_dir=SET_DIR, out_path=GPKG_POP):
    """Une shapefiles de setores com o CSV de população (Censo 2022)."""
    print("🔄 Consolidando setores com população...")

    atrib = pd.read_csv(csv_path, sep=",", dtype={"CD_SETOR": str})
    atrib.columns = [c.lower() for c in atrib.columns]

    if POP_COL not in atrib.columns:
        raise ValueError(f"❌ Coluna {POP_COL} não encontrada no CSV.")

    all_setores = []
    for uf_dir in shp_dir.glob("*_setores_CD2022"):
        shp_files = list(uf_dir.glob("*.shp"))
        if not shp_files:
            continue
        shp = shp_files[0]
        setores = gpd.read_file(shp)
        setores["CD_SETOR"] = setores["CD_SETOR"].astype(str)

        setores = setores.merge(
            atrib[["cd_setor", POP_COL]],
            left_on="CD_SETOR", right_on="cd_setor", how="left"
        ).rename(columns={POP_COL: "POP2022"})

        setores.drop(columns=[c for c in ["cd_setor"] if c in setores.columns], inplace=True)
        all_setores.append(setores)

    setores_full = gpd.GeoDataFrame(pd.concat(all_setores, ignore_index=True), crs=setores.crs)
    setores_full = setores_full.loc[:, ~setores_full.columns.duplicated()]
    setores_full.to_file(out_path, driver="GPKG")

    print(f"✅ Consolidado: {len(setores_full)} setores → {out_path}")
    return out_path


# ========================
# Gera buffers oficiais (REP_ESPACIAL)
# ========================
def ensure_buffers_from_rep(rep_csv=REP_CSV, out_buffer_path=BUFFER_PATH):
    """Gera buffers circulares a partir da coluna REP_ESPACIAL (classificação categórica)."""
    print("📍 Gerando buffers a partir de REP_ESPACIAL...")

    rep = pd.read_csv(rep_csv)

    # ======================================================
    # 🔥 NORMALIZAÇÃO DE POLUENTES — AQUI!
    # ======================================================
    pollutant_map = {
        "PM10": "MP10",
        "PM25": "MP25",
        "PM2.5": "MP25",
        "PM2_5": "MP25",
        "PM1": None,
        "VOC": None,
        "VolatileOrganicCompounds": None,
    }

    if "POLUENTE" in rep.columns:
        rep["POLUENTE"] = rep["POLUENTE"].astype(str).str.strip().replace(pollutant_map)
        rep = rep[rep["POLUENTE"].notna()].copy()
    # ======================================================

    needed = {"LATITUDE", "LONGITUDE", "REP_ESPACIAL", "ID_OEMA"}
    missing = needed - set(rep.columns)
    if missing:
        raise ValueError(f"❌ Faltam colunas no CSV: {missing}")

    # Conversão categórica → numérica (raio em metros)
    cat_to_radius = {
        "microescala": 100,
        "mesoescala": 500,
        "bairro": 4000,
        "urbana": 50000,
    }

    rep["REP_ESPACIAL_NUM"] = (
        rep["REP_ESPACIAL"]
        .astype(str)
        .str.lower()
        .map(cat_to_radius)
    )

    rep["ID_OEMA"] = rep["ID_OEMA"].astype(str)

    gdf_pts = gpd.GeoDataFrame(
        rep.copy(),
        geometry=gpd.points_from_xy(rep["LONGITUDE"], rep["LATITUDE"]),
        crs="EPSG:4326"
    ).to_crs(5880)

    # Cria os buffers com base no raio convertido
    gdf_pts["geometry"] = [
        geom.buffer(float(dist)) if pd.notna(dist) and float(dist) > 0 else None
        for geom, dist in zip(gdf_pts.geometry, gdf_pts["REP_ESPACIAL_NUM"])
    ]

    gdf_out = gdf_pts.dropna(subset=["geometry"]).copy()
    gdf_out.to_crs(4326).to_file(out_buffer_path, driver="GPKG")

    print(f"✅ Buffers gerados: {len(gdf_out)} → {out_buffer_path}")
    return out_buffer_path


# ========================
# Calcula população atendida
# ========================
def popUnderStationREP(
    setor_path=GPKG_POP,
    buffer_path=BUFFER_PATH,
    pop_col="POP2022",
    method="A",
    output_csv=OUTPUT_DIR / "populacao_varbuf.csv"
):
    """
    Calcula a população atendida pelos buffers:
    - method="A": população por estação (ID_MMA_COMPLETO)
    - method="C": população total pela união da rede
    """
    logging.getLogger("pyogrio._io").setLevel(logging.ERROR)

    if not Path(setor_path).exists():
        print("⚠️ Setores não encontrados → gerando...")
        consolidar_setores()

    setores = gpd.read_file(setor_path).to_crs(5880)
    
    if not Path(buffer_path).exists():
        buffer_path = ensure_buffers_from_rep()
    
    buffers = gpd.read_file(buffer_path).to_crs(5880)

    if method.upper() == "A":
        print("👩‍👩‍👧‍👦 Calculando população por buffer (método A, incluindo ID_MMA_COMPLETO)...")
        inter = gpd.overlay(setores, buffers, how="intersection")

        inter["AREA_INTER"] = inter.geometry.area
        area_setor = setores.set_index("CD_SETOR").geometry.area
        inter = inter.merge(area_setor.rename("AREA_SETOR"), on="CD_SETOR", how="left")
        inter["frac_area"] = inter["AREA_INTER"] / inter["AREA_SETOR"]
        inter["pop_frac"] = inter[pop_col] * inter["frac_area"]

        # 🧩 Garante colunas necessárias
        for col in ["ID_OEMA", "ID_MMA_COMPLETO"]:
            if col not in inter.columns:
                raise ValueError(f"❌ Coluna {col} não encontrada no CSV de entrada!")

        # 🔹 Agrupa por ID_OEMA e ID_MMA_COMPLETO
        pop_por_buffer = (
            inter.groupby(["ID_OEMA", "ID_MMA_COMPLETO"])["pop_frac"]
            .sum()
            .reset_index()
            .rename(columns={"pop_frac": "POP_BUFFER"})
        )

        pop_por_buffer.to_csv(output_csv, index=False, encoding="utf-8")
        print(f"✅ População por estação salva em {output_csv}")
        return pop_por_buffer

    elif method.upper() == "C":
        print("🌐 Calculando população total (método C)...")
        buffer_union = buffers.unary_union
        inter = gpd.overlay(setores, gpd.GeoDataFrame(geometry=[buffer_union], crs=buffers.crs), how="intersection")

        inter["AREA_INTER"] = inter.geometry.area
        area_setor = setores.set_index("CD_SETOR").geometry.area
        inter = inter.merge(area_setor.rename("AREA_SETOR"), on="CD_SETOR", how="left")
        inter["frac_area"] = inter["AREA_INTER"] / inter["AREA_SETOR"]
        inter["pop_frac"] = inter[pop_col] * inter["frac_area"]

        total_pop = inter["pop_frac"].sum().round(0).astype(int)
        print(f"✅ População total atendida pela rede: {total_pop:,} habitantes")
        return total_pop

    else:
        raise ValueError("method deve ser 'A' (por buffer) ou 'C' (total)")



# ========================
# Execução direta
# ========================
if __name__ == "__main__":
    consolidar_setores()
    ensure_buffers_from_rep()
    popUnderStationREP(method="C")
    popUnderStationREP(method="A")
