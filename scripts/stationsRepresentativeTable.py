# -*- coding: utf-8 -*-
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import os
import matplotlib.image as mpimg
from matplotlib.offsetbox import OffsetImage, AnnotationBbox


def plot_figura8(rootPath=None, save=False, force_rebuild=False):
    """
    Figura 8: Percentual de cobertura das redes de monitoramento da qualidade do ar (ativas)
    nas UFs brasileiras considerando área urbana e rural, com bandeiras no eixo Y.

    Parâmetros
    ----------
    rootPath : str | Path
        Caminho raiz do projeto.
    save : bool
        Se True, salva a figura em _static/figura8.png.
    force_rebuild : bool
        Se True, recalcula o gráfico mesmo que a imagem já exista.
    """

    rootPath = Path(rootPath or os.path.dirname(os.getcwd()))
    static_dir = rootPath / "_static"
    static_dir.mkdir(exist_ok=True)
    img_path = static_dir / "representatividade/figura8.png"

    # --- Se a imagem já existe e o usuário não pediu para recalcular ---
    if img_path.exists() and not force_rebuild:
        #print(f"✅ Carregando imagem existente: {img_path.name}")
        img = plt.imread(img_path)
        fig, ax = plt.subplots(figsize=(6, 8))
        ax.imshow(img)
        ax.axis("off")
        plt.tight_layout()
        return ax

    #print("⚙️ Gerando nova figura...")

    stations_file = rootPath / "data/rep_espacial/outputs/estacoes_completa.gpkg"
    setores_file  = rootPath / "data/setores_censitarios/BR_setores_pop2022.gpkg"
    flags_dir     = static_dir / "bandeiras"
    uf_to_sigla = {
        "Acre": "AC", "Alagoas": "AL", "Amapá": "AP", "Amazonas": "AM",
        "Bahia": "BA", "Ceará": "CE", "Distrito Federal": "DF", "Espírito Santo": "ES",
        "Goiás": "GO", "Maranhão": "MA", "Mato Grosso": "MT", "Mato Grosso do Sul": "MS",
        "Minas Gerais": "MG", "Pará": "PA", "Paraíba": "PB", "Paraná": "PR",
        "Pernambuco": "PE", "Piauí": "PI", "Rio de Janeiro": "RJ", "Rio Grande do Norte": "RN",
        "Rio Grande do Sul": "RS", "Rondônia": "RO", "Roraima": "RR", "Santa Catarina": "SC",
        "São Paulo": "SP", "Sergipe": "SE", "Tocantins": "TO"
    }

    # === Estações ===
    st = gpd.read_file(stations_file).to_crs(4326)
    if "STATUS" in st.columns:
        st = st[st["STATUS"].str.lower().str.contains("ativa")]

    # Buffers de representatividade
    st_proj = st.to_crs(3857)
    st_proj["geometry"] = st_proj.buffer(st_proj["REP_ESPACIAL"])
    st_buff = st_proj.to_crs(4326)

    # === Setores censitários (com SITUACAO) ===
    setores = gpd.read_file(setores_file).to_crs(4326)[["CD_UF", "NM_UF", "SITUACAO", "geometry"]]

    # === Área total por UF ===
    setores_proj = setores.to_crs(3857)
    setores_proj["area_km2"] = setores_proj.geometry.area / 1e6
    
    area_total = (
        setores_proj.groupby(["CD_UF", "NM_UF"])["area_km2"]
        .sum()
        .reset_index()
        .rename(columns={"area_km2": "area_tot_km2"})
    )

    # Interseção buffers × setores
    inter = gpd.overlay(setores, st_buff, how="intersection")
    inter = inter.to_crs(3857)
    inter["area_km2"] = inter.geometry.area / 1e6
    inter = inter.to_crs(4326)

    # Cobertura por UF e situação
    df_area = inter.groupby(["CD_UF", "NM_UF", "SITUACAO"])["area_km2"].sum().reset_index()
    df_area = df_area.merge(area_total, on=["CD_UF", "NM_UF"], how="left")
    df_area["Percentual"] = (df_area["area_km2"] / df_area["area_tot_km2"]) * 100

    # Tabela UF × Situação
    df_pivot = df_area.pivot(index="NM_UF", columns="SITUACAO", values="Percentual").fillna(0)
    df_pivot = df_pivot.sort_index()

    # === Gráfico ===
    cores = {"Urbana": "#64B5F6", "Rural": "#A8E6CF"}
    ax = df_pivot.plot(
        kind="barh", stacked=True, figsize=(9, 12), color=cores
    )

    plt.xlabel("Percentual da área do estado coberta por estações (%)")
    plt.legend(title="Área")
    plt.tight_layout()

    # === Bandeiras no eixo Y (siglas) ===
    yticks = ax.get_yticks()
    labels = df_pivot.index.tolist()
    
    for y, uf in zip(yticks, labels):
        sigla = uf_to_sigla.get(uf, None)
        if sigla:
            flag_path = flags_dir / f"{sigla}.png"
            if flag_path.exists():
                img = mpimg.imread(flag_path)
                imagebox = OffsetImage(img, zoom=0.08)
                ab = AnnotationBbox(
                    imagebox,
                    (-0.02, y),
                    xycoords=(ax.get_yaxis_transform()), 
                    frameon=False,
                    box_alignment=(1, 0.5)
                )
                ax.add_artist(ab)

    # remover labels de texto (só bandeiras ficam)
    ax.set_yticklabels([""] * len(labels))
    
    # 🔹 remove o título do eixo Y e o próprio eixo
    ax.set_ylabel("")
    ax.yaxis.set_ticks_position('none')  # remove os traços do eixo
    
    # 🔹 opcional: remove o contorno do eixo
    for spine in ["left", "right", "top"]:
        ax.spines[spine].set_visible(False)


    # --- Salvar se solicitado ---
    if save:
        plt.savefig(img_path, dpi=300, bbox_inches="tight")
        #print(f"💾 Figura salva em: {img_path}")

    return ax
