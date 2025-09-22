# -*- coding: utf-8 -*-
"""
Pipeline completo:
1) Consolida shapefiles de setores censitários (Censo 2022) + CSV nacional (população v0001)
2) Gera BR_setores_pop2022.gpkg com geometria + POP2022
3) Calcula população atendida por buffers (A = por buffer; C = união da rede)
4) Produz Tabela 13 (potencial vs. única) por UF e Brasil
"""

import geopandas as gpd
import pandas as pd
from pathlib import Path
import os
import logging

# ========================
# Configurações
# ========================
rootPath   = Path(os.path.dirname(os.getcwd()))
SET_DIR    = rootPath / "data/setores_censitarios"
OUTPUT_DIR = rootPath / "data/outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CSV_ATTR   = SET_DIR / "BR_setores_CD2022.csv"
GPKG_POP   = SET_DIR / "BR_setores_pop2022.gpkg"
BUFFER_PATH = OUTPUT_DIR / "buffers_var.gpkg"
USO_PATH    = OUTPUT_DIR / "uso_solo_varbuf.csv"
TAB13_PATH  = OUTPUT_DIR / "tabela13_pop_uf.csv"

POP_COL = "v0001"

# ========================
# Passo 1 – Consolidar setores + população
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
        print(f" - {shp.name}")
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
# Passo 2 – População por buffer (A) ou por união (C)
# ========================
def popUnderStation(
    setor_path=GPKG_POP,
    buffer_path=BUFFER_PATH,
    pop_col="POP2022",
    method="A",
    output_csv=OUTPUT_DIR / "populacao_varbuf.csv"
):
    logging.getLogger("pyogrio._io").setLevel(logging.ERROR)

    if not Path(setor_path).exists():
        print("⚠️ Arquivo de setores não encontrado. Rodando consolidação primeiro...")
        consolidar_setores()

    setores = gpd.read_file(setor_path).to_crs(5880)
    buffers = gpd.read_file(buffer_path).to_crs(5880)

    if "ID" not in buffers.columns:
        buffers = buffers.reset_index(drop=False).rename(columns={"index": "ID"})

    if method.upper() == "A":
        inter = gpd.overlay(setores, buffers, how="intersection")
        setores["AREA_SETOR"] = setores.geometry.area
        area_total_setor = setores.groupby("CD_SETOR")["AREA_SETOR"].sum()
        inter["frac_area"] = inter.geometry.area / inter["CD_SETOR"].map(area_total_setor)
        inter["pop_frac"]  = inter[pop_col] * inter["frac_area"]

        pop_por_buffer = (inter.groupby("ID")["pop_frac"]
                                 .sum()
                                 .reset_index()
                                 .rename(columns={"pop_frac": "POP_BUFFER"}))

        pop_por_buffer.to_csv(output_csv, index=False, encoding="utf-8")
        return pop_por_buffer

    elif method.upper() == "C":
        buffer_union = buffers.unary_union
        buffer_union_gdf = gpd.GeoDataFrame(geometry=[buffer_union], crs=buffers.crs)

        inter = gpd.overlay(setores, buffer_union_gdf, how="intersection")
        setores["AREA_SETOR"] = setores.geometry.area
        area_total_setor = setores.groupby("CD_SETOR")["AREA_SETOR"].sum()
        inter["frac_area"] = inter.geometry.area / inter["CD_SETOR"].map(area_total_setor)
        inter["pop_frac"]  = inter[pop_col] * inter["frac_area"]

        total_pop = inter["pop_frac"].sum().round(0).astype(int)
        return total_pop

    else:
        raise ValueError("method deve ser 'A' ou 'C'")


# ========================
# Passo 3 – Tabela 13 (com A e C)
# ========================
def tabela13(
    uso_path=USO_PATH,
    pop_path=OUTPUT_DIR / "populacao_varbuf.csv",
    setor_path=GPKG_POP,
    buffer_path=BUFFER_PATH,
    out_path=TAB13_PATH
):
    print("🔄 Gerando Tabela 13...")

    uso = pd.read_csv(uso_path)
    pop = pd.read_csv(pop_path)
    df = uso.merge(pop, on="ID", how="left")

    # --- Potencial (A)
    estacoes_por_uf = df.groupby("UF")["ID"].nunique()
    pop_por_uf_A = df.groupby("UF")["POP_BUFFER"].sum()
    uso_pred_uf = df.groupby("UF")["GRUPO_PRED_VAR"].agg(lambda x: x.mode().iloc[0] if not x.mode().empty else None)

    # --- Única (C), calculada por UF
    setores = gpd.read_file(setor_path).to_crs(5880)
    buffers = gpd.read_file(buffer_path).to_crs(5880)

    pop_unica = {}
    for uf, uf_buffers in buffers.groupby("UF"):
        buffer_union = uf_buffers.unary_union
        buffer_union_gdf = gpd.GeoDataFrame(geometry=[buffer_union], crs=buffers.crs)
        inter = gpd.overlay(setores[setores.CD_UF == uf], buffer_union_gdf, how="intersection")
        setores["AREA_SETOR"] = setores.geometry.area
        area_total_setor = setores.groupby("CD_SETOR")["AREA_SETOR"].sum()
        inter["frac_area"] = inter.geometry.area / inter["CD_SETOR"].map(area_total_setor)
        inter["pop_frac"]  = inter["POP2022"] * inter["frac_area"]
        pop_unica[uf] = inter["pop_frac"].sum().round(0).astype(int)

    tabela = pd.DataFrame({
        "UF": estacoes_por_uf.index,
        "N_ESTACOES": estacoes_por_uf.values,
        "POP_ATENDIDA_POTENCIAL": pop_por_uf_A.round(0).astype("int64"),
        "POP_ATENDIDA_UNICA": [pop_unica.get(uf, 0) for uf in estacoes_por_uf.index],
        "USO_PREDOMINANTE": uso_pred_uf.values
    })

    # Linha Brasil
    brasil = pd.DataFrame({
        "UF": ["BR"],
        "N_ESTACOES": [estacoes_por_uf.sum()],
        "POP_ATENDIDA_POTENCIAL": [int(pop_por_uf_A.sum().round(0))],
        "POP_ATENDIDA_UNICA": [sum(pop_unica.values())],
        "USO_PREDOMINANTE": ["—"]
    })
    tabela = pd.concat([tabela, brasil], ignore_index=True)

    tabela.to_csv(out_path, index=False, encoding="utf-8")
    print(f"✅ Tabela 13 salva em {out_path}")
    return tabela


# ========================
# Execução direta
# ========================
if __name__ == "__main__":
    consolidar_setores()
    popUnderStation(method="A")
    tabela13()
