#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gera GEOJSONs separados por poluente E por CATEGORIA (Indicativa/Referencia),
utilizando ID_MMA_COMPLETO para união.

*** Corrigido: CATEGORIA lida diretamente do buffers_var.gpkg. ***
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
# METADADOS_PATH não é mais necessário

GJSON_DIR   = rootPath / "_static" / "representatividade" / "populacao_geojson"
GJSON_DIR.mkdir(parents=True, exist_ok=True)

# Poluentes desejados
POL_VALIDOS = ["MP25", "MP10", "CO", "NO2", "PTS", "SO2", "O3"]


# ================================================================
# 2) Função principal
# ================================================================
def build_pop_geojson_by_pollutant():

    # LENDO ARQUIVOS
    print(f"📥 Lendo buffers: {BUFFER_PATH}")
    try:
        # buf agora contém a coluna 'CATEGORIA'
        buf = gpd.read_file(BUFFER_PATH) 
    except Exception as e:
        print(f"❌ Erro lendo buffers_var.gpkg: {e}")
        sys.exit(1)

    print(f"📥 Lendo populacao: {POP_PATH}")
    try:
        # pop agora contém 'ID_MMA_COMPLETO' e 'POP_BUFFER'
        pop = pd.read_csv(POP_PATH) 
    except Exception as e:
        print(f"❌ Erro lendo populacao_varbuf.csv: {e}")
        sys.exit(1)


    # Garantir WGS84 e Filtrar poluentes
    if buf.crs is None:
        print("❌ CRS ausente no arquivo buffers_var.gpkg.")
        sys.exit(1)

    buf = buf.to_crs(4326)
    buf = buf[buf["POLUENTE"].isin(POL_VALIDOS)].copy()

    print("\nPoluentes no dataset:", sorted(buf["POLUENTE"].unique()))

    # ===================================================
    # Padronizar IDs usando ID_MMA_COMPLETO para Merge
    # ===================================================
    chave_merge = "ID_MMA_COMPLETO"

    # 1. Buffers (GeoDataFrame)
    if chave_merge in buf.columns:
        buf["ID_MERGE"] = buf[chave_merge].astype(str).str.strip()
    else:
        # Fallback: se o ID principal não estiver no buffer, é um problema sério, mas usamos ID_OEMA
        print(f"⚠️ {chave_merge} não encontrado nos buffers. Usando ID_OEMA.")
        buf["ID_MERGE"] = buf["ID_OEMA"].astype(str).str.strip()

    # 2. População (DataFrame)
    if chave_merge in pop.columns:
        pop["ID_MERGE"] = pop[chave_merge].astype(str).str.strip()
    else:
        print(f"⚠️ {chave_merge} não encontrado na população. Usando ID_OEMA.")
        pop["ID_MERGE"] = pop["ID_OEMA"].astype(str).str.strip()
        
    # ===================================================

    # 1. MERGE dos dados de população
    # Selecionar colunas de população e garantir unicidade antes do merge
    pop_cols = [col for col in ["ID_MERGE", "POP_BUFFER"] if col in pop.columns]
    pop_unique = pop[pop_cols].drop_duplicates(subset=["ID_MERGE"])
    df = buf.merge(pop_unique, on="ID_MERGE", how="left")
    
    # 2. TRATAMENTO DA CATEGORIA (JÁ ESTÁ NA COLUNA 'CATEGORIA' DO DF FINAL)

    # Padronizar a CATEGORIA e criar CLASSIFICACAO
    df['CATEGORIA_PADRONIZADA'] = df['CATEGORIA'].fillna('Não Declarada').astype(str).str.strip()
    
    # Classificação em 2 grupos: Indicativa e Referencia (onde Referencia inclui não declaradas)
    df['CLASSIFICACAO'] = 'Referencia'
    df.loc[df['CATEGORIA_PADRONIZADA'].str.lower().str.contains('indicativa'), 'CLASSIFICACAO'] = 'Indicativa'
    
    # Propriedades a serem mantidas no GeoJSON
    props_base = ["ID_OEMA", "ID_MMA_COMPLETO", "UF", "POLUENTE", "POP_BUFFER", "REP_ESPACIAL", "CATEGORIA", "CLASSIFICACAO"]

    print("\n🔧 Gerando arquivos por Categoria (Indicativa / Referencia)...")

    outputs = {}

    for pol in POL_VALIDOS:
        gdf_pol = df[df["POLUENTE"] == pol].copy()
        
        if gdf_pol.empty:
            print(f"⚠️ {pol}: sem registros — não criado.")
            continue
            
        # --- FILTRAGEM E GERAÇÃO DOS DOIS ARQUIVOS ---
        
        # 1. ESTAÇÕES INDICATIVAS
        gdf_ind = gdf_pol[gdf_pol["CLASSIFICACAO"] == 'Indicativa'][props_base + ["geometry"]].copy()
        if not gdf_ind.empty:
            out_file_ind = GJSON_DIR / f"{pol}_Indicativa.geojson"
            gdf_ind.to_file(out_file_ind, driver="GeoJSON")
            outputs[f"{pol}_Indicativa"] = out_file_ind
            print(f"✔ Criado: {out_file_ind}")
        else:
             print(f"❌ {pol}_Indicativa: Vazio.")

        # 2. ESTAÇÕES DE REFERÊNCIA (INCLUI 'Não Declarada')
        gdf_ref = gdf_pol[gdf_pol["CLASSIFICACAO"] == 'Referencia'][props_base + ["geometry"]].copy()
        if not gdf_ref.empty:
            out_file_ref = GJSON_DIR / f"{pol}_Referencia.geojson"
            gdf_ref.to_file(out_file_ref, driver="GeoJSON")
            outputs[f"{pol}_Referencia"] = out_file_ref
            print(f"✔ Criado: {out_file_ref}")
        else:
            print(f"❌ {pol}_Referencia: Vazio.")

    print("\n🏁 Concluído!")
    return outputs


# ================================================================
# 3) Execução direta pelo terminal
# ================================================================
if __name__ == "__main__":
    build_pop_geojson_by_pollutant()