# -*- coding: utf-8 -*-
"""
popUnderStationREP.py
Funções para:
1) Consolidar setores censitários + população
2) Gerar buffers oficiais a partir do rep_espacial.csv
3) Calcular população atendida por estação/poluente (REP_ESPACIAL)
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
REP_CSV     = rootPath / "data/rep_espacial/outputs/rep_espacial.csv"

POP_COL     = "v0001"


# ========================
# Consolida setores + população
# ========================
def consolidar_setores(csv_path=CSV_ATTR, shp_dir=SET_DIR, out_path=GPKG_POP):
    print("🔄 Consolidando setores com população...")

    atrib = pd.read_csv(csv_path, sep=",", dtype={"CD_SETOR": str})
    atrib.columns = [c.lower() for c in atrib.columns]

    if POP_COL not in atrib.columns:
        raise ValueError(f"Coluna {POP_COL} não encontrada no CSV. Colunas: {atrib.columns.tolist()[:20]}")

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

        if "cd_setor" in setores.columns:
            setores = setores.drop(columns=["cd_setor"])

        all_setores.append(setores)

    setores_full = gpd.GeoDataFrame(pd.concat(all_setores, ignore_index=True), crs=setores.crs)
    setores_full = setores_full.loc[:, ~setores_full.columns.duplicated()]

    setores_full.to_file(out_path, driver="GPKG")
    print(f"✅ Arquivo consolidado salvo em {out_path} com {len(setores_full)} setores")
    return out_path


# ========================
# Gera buffers SEMPRE do rep_espacial.csv
# ========================
def ensure_buffers_from_rep(rep_csv=REP_CSV, out_buffer_path=BUFFER_PATH):
    print("🔄 Gerando buffers oficiais a partir do rep_espacial.csv...")

    rep = pd.read_csv(rep_csv)
    needed = {"LATITUDE", "LONGITUDE", "REP_ESPACIAL", "ID_OEMA"}
    missing = needed - set(rep.columns)
    if missing:
        raise ValueError(f"Faltam colunas no rep_espacial.csv: {missing}")

    rep["ID_OEMA"] = rep["ID_OEMA"].astype(str)

    gdf_pts = gpd.GeoDataFrame(
        rep.copy(),
        geometry=gpd.points_from_xy(rep["LONGITUDE"], rep["LATITUDE"]),
        crs="EPSG:4326"
    ).to_crs(5880)

    gdf_pts["geometry"] = [
        geom.buffer(float(dist)) if pd.notna(dist) and float(dist) > 0 else None
        for geom, dist in zip(gdf_pts.geometry, gdf_pts["REP_ESPACIAL"])
    ]

    gdf_buf = gdf_pts.to_crs(4326)
    gdf_buf = gdf_buf.reset_index(drop=False).rename(columns={"index": "ID"})

    keep_cols = ["ID", "ID_OEMA", "POLUENTE", "UF", "REP_ESPACIAL", "LATITUDE", "LONGITUDE", "geometry"]
    existing = [c for c in keep_cols if c in gdf_buf.columns]
    gdf_out = gdf_buf[existing].copy()

    gdf_out.to_file(out_buffer_path, driver="GPKG")
    print(f"✅ Buffers oficiais salvos em {out_buffer_path} ({len(gdf_out)} registros)")
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
    Calcula a população atendida usando REP_ESPACIAL como raio de buffer.
    - method="A": população por buffer
    - method="C": população total pela união da rede
    """
    logging.getLogger("pyogrio._io").setLevel(logging.ERROR)

    # --- Garante setores ---
    if not Path(setor_path).exists():
        print("⚠️ Arquivo de setores não encontrado. Rodando consolidação...")
        consolidar_setores()

    setores = gpd.read_file(setor_path).to_crs(5880)

    # --- Sempre recria buffers oficiais ---
    buffer_path = ensure_buffers_from_rep()
    buffers = gpd.read_file(buffer_path).to_crs(5880)

    if "ID" not in buffers.columns:
        buffers = buffers.reset_index(drop=False).rename(columns={"index": "ID"})

    # --- Método A: população por buffer ---
    if method.upper() == "A":
        inter = gpd.overlay(setores, buffers, how="intersection")
        setores["AREA_SETOR"] = setores.geometry.area
        area_total_setor = setores.groupby("CD_SETOR")["AREA_SETOR"].sum()

        inter["frac_area"] = inter.geometry.area / inter["CD_SETOR"].map(area_total_setor)
        inter["pop_frac"] = inter[pop_col] * inter["frac_area"]

        pop_por_buffer = (inter.groupby("ID")["pop_frac"]
                                 .sum()
                                 .reset_index()
                                 .rename(columns={"pop_frac": "POP_BUFFER"}))

        pop_por_buffer.to_csv(output_csv, index=False, encoding="utf-8")
        print(f"✅ População atendida salva em {output_csv}")
        return pop_por_buffer

    # --- Método C: população total por união ---
    elif method.upper() == "C":
        buffer_union = buffers.unary_union
        buffer_union_gdf = gpd.GeoDataFrame(geometry=[buffer_union], crs=buffers.crs)

        inter = gpd.overlay(setores, buffer_union_gdf, how="intersection")
        setores["AREA_SETOR"] = setores.geometry.area
        area_total_setor = setores.groupby("CD_SETOR")["AREA_SETOR"].sum()

        inter["frac_area"] = inter.geometry.area / inter["CD_SETOR"].map(area_total_setor)
        inter["pop_frac"] = inter[pop_col] * inter["frac_area"]

        total_pop = inter["pop_frac"].sum().round(0).astype(int)
        print(f"✅ População total (rede única): {total_pop}")
        return total_pop

    else:
        raise ValueError("method deve ser 'A' ou 'C'")


# ========================
# Execução direta
# ========================
if __name__ == "__main__":
    consolidar_setores()
    popUnderStationREP(method="A")
