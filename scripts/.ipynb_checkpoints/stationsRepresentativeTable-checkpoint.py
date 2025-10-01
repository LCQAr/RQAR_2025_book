# -*- coding: utf-8 -*-
"""
Figura 8: Percentual e estatística de cobertura das redes de monitoramento da qualidade do ar (ativas)
nas UFs brasileiras considerando a área rural e urbana.
"""

import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import os


def plot_figura8(rootPath=None):
    """
    Gera a Figura 8 em matplotlib, cruzando estações com setores censitários
    para classificar como urbano/rural.
    """
    rootPath = Path(rootPath or os.path.dirname(os.getcwd()))

    stations_file = rootPath / "data/rep_espacial/outputs/estacoes_completa.gpkg"
    setores_file  = rootPath / "data/setores_censitarios/BR_setores_pop2022.gpkg"

    # === Carregar estações ===
    st = gpd.read_file(stations_file).to_crs(4326)

    # Filtrar apenas ativas
    if "STATUS" in st.columns:
        st = st[st["STATUS"].str.lower().str.contains("ativa")]

    # === Carregar setores censitários com coluna SITUACAO ===
    setores = gpd.read_file(setores_file).to_crs(4326)[["CD_SETOR", "SITUACAO", "geometry"]]

    # === Atribuir situação (urbana/rural) para cada estação via spatial join ===
    st = gpd.sjoin(st, setores, how="left", predicate="intersects")

    # Caso alguma estação não case, marcar como "Desconhecida"
    st["SITUACAO"] = st["SITUACAO"].fillna("Desconhecida")

    # === Contagem por UF e situação ===
    df_counts = st.groupby(["UF", "SITUACAO"]).size().reset_index(name="N")
    df_total = df_counts.groupby("UF")["N"].transform("sum")
    df_counts["Percentual"] = (df_counts["N"] / df_total) * 100

    # Pivot para gráfico
    df_pivot = df_counts.pivot(index="UF", columns="SITUACAO", values="Percentual").fillna(0)
    df_pivot = df_pivot.sort_index()

    # === Gráfico ===
    cores = {"Urbana": "#64B5F6", "Rural": "#A8E6CF", "Desconhecida": "#B0BEC5"}
    ax = df_pivot.plot(
        kind="barh", stacked=True, figsize=(8, 10),
        color=cores
    )

    plt.xlabel("Percentual de estações (%)")
    plt.ylabel("Unidade da Federação (UF)")
    plt.title(
        "Figura 8: Percentual e estatística de cobertura das redes de monitoramento\n"
        "da qualidade do ar (ativas) nas UFs brasileiras considerando a área rural e urbana"
    )
    plt.legend(title="Área")
    plt.tight_layout()

    return ax
