# -*- coding: utf-8 -*-
"""
Pipeline completo:
1) Consolida shapefiles de setores censitários (Censo 2022) + CSV nacional (população V0001)
2) Gera BR_setores_pop2022.gpkg com geometria + POP2022
3) Calcula população atendida por buffers de monitoramento
4) Produz Tabela 13 (população atendida + nº de estações + uso do solo predominante por UF)
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

CSV_ATTR   = SET_DIR / "BR_setores_CD2022.csv"    # atributos nacionais (com V0001)
GPKG_POP   = SET_DIR / "BR_setores_pop2022.gpkg"  # saída consolidada
BUFFER_PATH = OUTPUT_DIR / "buffers_var.gpkg"     # buffers gerados no uso do solo
USO_PATH    = OUTPUT_DIR / "uso_solo_varbuf.csv"  # uso do solo
TAB13_PATH  = OUTPUT_DIR / "tabela13_pop_uf.csv"  # saída Tabela 13

# Nome da coluna de população no CSV do IBGE
POP_COL = "v0001"

# ========================
# Passo 1 – Consolidar setores + população
# ========================
def consolidar_setores(csv_path=CSV_ATTR, shp_dir=SET_DIR, out_path=GPKG_POP):
    print("🔄 Consolidando setores com população...")

    # Lê o CSV de atributos
    atrib = pd.read_csv(csv_path, sep=",", dtype={"CD_SETOR": str})

    # Normaliza colunas para minúsculo
    atrib.columns = [c.lower() for c in atrib.columns]

    # Define a coluna de população
    pop_col = "v0001"
    if pop_col not in atrib.columns:
        raise ValueError(f"Coluna {pop_col} não encontrada no CSV. Colunas disponíveis: {atrib.columns.tolist()[:20]}")

    all_setores = []
    for uf_dir in shp_dir.glob("*_setores_CD2022"):
        shp_files = list(uf_dir.glob("*.shp"))
        if not shp_files:
            continue
        shp = shp_files[0]
        print(f" - {shp.name}")
        setores = gpd.read_file(shp)
        setores["CD_SETOR"] = setores["CD_SETOR"].astype(str)

        # Faz o merge com a população
        setores = setores.merge(
            atrib[["cd_setor", pop_col]],
            left_on="CD_SETOR", right_on="cd_setor", how="left"
        )

        # Renomeia para padrão único
        setores = setores.rename(columns={pop_col: "POP2022"})

        # Remove coluna duplicada cd_setor
        if "cd_setor" in setores.columns:
            setores = setores.drop(columns=["cd_setor"])

        all_setores.append(setores)

    setores_full = gpd.GeoDataFrame(pd.concat(all_setores, ignore_index=True), crs=setores.crs)

    # Garante que não existam colunas duplicadas
    setores_full = setores_full.loc[:, ~setores_full.columns.duplicated()]

    setores_full.to_file(out_path, driver="GPKG")
    print(f"✅ Arquivo consolidado salvo em {out_path} com {len(setores_full)} setores")
    return out_path



# ========================
# Passo 2 – População por buffer
# ========================
def popUnderStation(
    setor_path=GPKG_POP,
    buffer_path=BUFFER_PATH,
    pop_col="POP2022",
    output_csv=OUTPUT_DIR / "populacao_varbuf.csv"
):
    logging.getLogger("pyogrio._io").setLevel(logging.ERROR)

    # Se o GPKG consolidado não existir, cria primeiro
    if not Path(setor_path).exists():
        print("⚠️ Arquivo de setores não encontrado. Rodando consolidação primeiro...")
        consolidar_setores()

    print("🔄 Calculando população por buffer...")
    setores = gpd.read_file(setor_path).to_crs(5880)
    buffers = gpd.read_file(buffer_path).to_crs(5880)

    if "ID" not in buffers.columns:
        buffers = buffers.reset_index(drop=False).rename(columns={"index": "ID"})

    inter = gpd.overlay(setores, buffers, how="intersection")

    # Calcula área de cada polígono
    setores["AREA_SETOR"] = setores.geometry.area
    
    # Garante área total única por setor (soma se houver setores duplicados)
    area_total_setor = setores.groupby("CD_SETOR")["AREA_SETOR"].sum()
    
    # Fração da área de interseção em relação ao setor
    inter["frac_area"] = inter.geometry.area / inter["CD_SETOR"].map(area_total_setor)
    
    # População proporcional
    inter["pop_frac"]  = inter[pop_col] * inter["frac_area"]

    pop_por_buffer = (inter.groupby("ID")["pop_frac"]
                             .sum()
                             .reset_index()
                             .rename(columns={"pop_frac": "POP_BUFFER"}))

    pop_por_buffer.to_csv(output_csv, index=False, encoding="utf-8")
    print(f"✅ População por buffer salva em {output_csv}")
    return pop_por_buffer

# ========================
# Passo 3 – Tabela 13 por UF
# ========================
def tabela13(uso_path=USO_PATH, pop_path=OUTPUT_DIR / "populacao_varbuf.csv", out_path=TAB13_PATH):
    print("🔄 Gerando Tabela 13...")
    uso = pd.read_csv(uso_path)
    pop = pd.read_csv(pop_path)

    df = uso.merge(pop, on="ID", how="left")

    estacoes_por_uf = df.groupby("UF")["ID"].nunique()
    pop_por_uf = df.groupby("UF")["POP_BUFFER"].sum()
    uso_pred_uf = df.groupby("UF")["GRUPO_PRED_VAR"].agg(lambda x: x.mode().iloc[0] if not x.mode().empty else None)

    tabela = pd.DataFrame({
        "UF": estacoes_por_uf.index,
        "N_ESTACOES": estacoes_por_uf.values,
        "POP_ATENDIDA": pop_por_uf.round(0).astype("int64"),
        "USO_PREDOMINANTE": uso_pred_uf.values
    })

    # Linha Brasil
    brasil = pd.DataFrame({
        "UF": ["BR"],
        "N_ESTACOES": [estacoes_por_uf.sum()],
        "POP_ATENDIDA": [int(pop_por_uf.sum().round(0))],
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
    popUnderStation()
    tabela13()
