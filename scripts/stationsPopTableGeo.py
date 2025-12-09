# -*- coding: utf-8 -*-
"""
stationsPopTableGeo.py
Módulo responsável por gerenciar os dados populacionais.
Separa o cálculo pesado (gerar CSV) da leitura rápida (exibir tabela).
"""

import os
import base64
import geopandas as gpd
import pandas as pd
from pathlib import Path

# =============================
# Configurações
# =============================
ROOT_PATH = Path(os.path.dirname(os.getcwd()))
BUFFER_PATH = ROOT_PATH / "data/outputs/buffers_var.gpkg"
SETOR_PATH  = ROOT_PATH / "data/setores_censitarios/BR_setores_pop2022.gpkg"
FLAGS_DIR   = ROOT_PATH / "_static" / "bandeiras"
# Arquivo intermediário (CACHE)
CSV_CACHE   = ROOT_PATH / "_static" / "representatividade" / "populacao_consolidada.csv"

POL_VALIDOS = ["MP25", "MP10", "CO", "NO2", "PTS", "SO2", "O3"]

codigo_para_uf = {
    12: 'AC', 27: 'AL', 13: 'AM', 16: 'AP', 29: 'BA', 23: 'CE', 53: 'DF',
    32: 'ES', 52: 'GO', 21: 'MA', 31: 'MG', 50: 'MS', 51: 'MT', 15: 'PA',
    25: 'PB', 26: 'PE', 22: 'PI', 41: 'PR', 33: 'RJ', 24: 'RN', 11: 'RO',
    14: 'RR', 43: 'RS', 42: 'SC', 28: 'SE', 35: 'SP', 17: 'TO'
}

# =============================
# Função 1: PESADA (Gera o CSV)
# =============================
def gerar_cache_populacao():
    """
    Roda o processamento geoespacial pesado e SALVA um CSV.
    Não retorna nada visual, apenas processa dados.
    """
    
    if not BUFFER_PATH.exists() or not SETOR_PATH.exists():
        raise FileNotFoundError("Arquivos de entrada (GPKG) não encontrados.")

    # 1. Preparar Setores
    setores = gpd.read_file(SETOR_PATH).to_crs(5880)
    setores["AREA_ORIGINAL"] = setores.geometry.area
    
    # Extrair CD_UF
    candidatos = [c for c in setores.columns if any(k in c.lower() for k in ["mun", "geoc", "setor"])]
    if candidatos:
        col = candidatos[0]
        setores["CD_UF"] = setores[col].astype(str).str[:2].astype(int)
        setores["UF"] = setores["CD_UF"].map(codigo_para_uf)

    # 2. Preparar Buffers
    buffers = gpd.read_file(BUFFER_PATH).to_crs(5880)
    if "CATEGORIA" not in buffers.columns: buffers["CATEGORIA"] = "Nao declarado"
    buffers["CATEGORIA"] = buffers["CATEGORIA"].fillna("Nao declarado")
    buffers = buffers[buffers["POLUENTE"].isin(POL_VALIDOS)].copy()

    resultados = []
    categorias = ["Referencia", "Indicativa", "Nao declarado"]

    # 3. Loop de Processamento
    for pol in POL_VALIDOS:
        buf_pol = buffers[buffers["POLUENTE"] == pol]
        if buf_pol.empty: continue

        for cat in categorias:
            buf_cat = buf_pol[buf_pol["CATEGORIA"] == cat]
            if buf_cat.empty: continue
            


            # Otimização: Filtro Espacial (.cx)
            minx, miny, maxx, maxy = buf_cat.total_bounds
            setores_focados = setores.cx[minx:maxx, miny:maxy].copy()

            if setores_focados.empty: continue

            # Dissolve e Overlay
            buf_union = buf_cat.dissolve().reset_index(drop=True)
            inter = gpd.overlay(setores_focados, buf_union, how="intersection")

            if not inter.empty:
                inter["AREA_PROP"] = inter.geometry.area / inter["AREA_ORIGINAL"].replace(0, 1e-9)
                inter["POP_PROP"] = inter["POP2022"] * inter["AREA_PROP"]
                pop_uf = inter.groupby("CD_UF")["POP_PROP"].sum().round(0).reset_index()
                pop_uf["UF"] = pop_uf["CD_UF"].map(codigo_para_uf)
            else:
                pop_uf = pd.DataFrame(columns=["UF", "POP_PROP"])

            # Contagem de Estações
            est = gpd.sjoin(buf_cat.to_crs(5880), setores_focados[["CD_UF", "geometry"]], how="left", predicate="intersects")
            est["UF"] = est["CD_UF"].map(codigo_para_uf)
            est_count = est.groupby("UF")["ID_OEMA"].nunique().reset_index(name="N_ESTACOES")

            df_out = pop_uf.merge(est_count, on="UF", how="outer").fillna(0)
            df_out["Poluente"] = pol
            df_out["Categoria"] = cat
            resultados.append(df_out)

    # 4. Salvar CSV
    if resultados:
        resumo = pd.concat(resultados, ignore_index=True)
        resumo["População atendida"] = resumo["POP_PROP"].astype(int)
        resumo["Número de estações"] = resumo["N_ESTACOES"].astype(int)
        resumo = resumo[resumo["População atendida"] >= 1000].copy()
        
        df_final = resumo[["UF", "Poluente", "Categoria", "População atendida", "Número de estações"]]
        
        CSV_CACHE.parent.mkdir(parents=True, exist_ok=True)
        df_final.to_csv(CSV_CACHE, index=False)

    else:
        print("")

# =============================
# Função 2: LEVE (Lê o CSV para o Notebook)
# =============================
def carregar_tabela_pronta():
    """
    Lê o CSV gerado, adiciona as bandeiras e retorna o DataFrame.
    Execução instantânea.
    """
    if not CSV_CACHE.exists():
        raise FileNotFoundError(f"Arquivo de cache não encontrado: {CSV_CACHE}.\nRode 'gerar_cache_populacao()' primeiro.")

    df = pd.read_csv(CSV_CACHE)
    
    # Adicionar imagens das bandeiras (apenas na hora de exibir)
    def embed_flag(uf):
        p = FLAGS_DIR / f"{uf}.png"
        if p.exists():
            with open(p, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
            return f'<img src="data:image/png;base64,{b64}" width="26">'
        return ""

    df.insert(0, "Bandeira", df["UF"].apply(embed_flag))
    df = df.sort_values(by=["UF", "Poluente"]).reset_index(drop=True)
    
    return df