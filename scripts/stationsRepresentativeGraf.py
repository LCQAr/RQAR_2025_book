# -*- coding: utf-8 -*-
import geopandas as gpd
import pandas as pd
import numpy as np
import os, base64
from pathlib import Path
import plotly.graph_objects as go
from IPython.display import HTML

def plot_figura8_interativo(rootPath=None, save_html=True, force_rebuild=False):
    """
    Figura 8 (interativa, Plotly): Percentual de cobertura das redes de monitoramento por UF,
    com bandeiras embutidas no HTML e visualização direta no Jupyter.
    """

    rootPath = Path(rootPath or os.path.dirname(os.getcwd()))
    static_dir = rootPath / "_static"
    rep_dir = static_dir / "representatividade"
    rep_dir.mkdir(parents=True, exist_ok=True)
    html_path = rep_dir / "figura8_interativo.html"
    flags_dir = static_dir / "bandeiras"

    # === Mapeamento de estados ===
    uf_to_sigla = {
        "Acre": "AC", "Alagoas": "AL", "Amapá": "AP", "Amazonas": "AM",
        "Bahia": "BA", "Ceará": "CE", "Distrito Federal": "DF", "Espírito Santo": "ES",
        "Goiás": "GO", "Maranhão": "MA", "Mato Grosso": "MT", "Mato Grosso do Sul": "MS",
        "Minas Gerais": "MG", "Pará": "PA", "Paraíba": "PB", "Paraná": "PR",
        "Pernambuco": "PE", "Piauí": "PI", "Rio de Janeiro": "RJ", "Rio Grande do Norte": "RN",
        "Rio Grande do Sul": "RS", "Rondônia": "RO", "Roraima": "RR", "Santa Catarina": "SC",
        "São Paulo": "SP", "Sergipe": "SE", "Tocantins": "TO"
    }

    # === Leitura dos dados ===
    stations_file = rootPath / "data/rep_espacial/outputs/estacoes_completa.gpkg"
    setores_file  = rootPath / "data/setores_censitarios/BR_setores_pop2022.gpkg"

    st = gpd.read_file(stations_file).to_crs(4326)
    if "STATUS" in st.columns:
        st = st[st["STATUS"].str.lower().str.contains("ativa")]

    st_proj = st.to_crs(3857)
    st_proj["geometry"] = st_proj.buffer(st_proj["REP_ESPACIAL"])
    st_buff = st_proj.to_crs(4326)

    setores = gpd.read_file(setores_file).to_crs(4326)[["CD_UF", "NM_UF", "SITUACAO", "geometry"]]
    setores_proj = setores.to_crs(3857)
    setores_proj["area_km2"] = setores_proj.geometry.area / 1e6
    area_total = setores_proj.groupby(["CD_UF", "NM_UF"])["area_km2"].sum().reset_index().rename(columns={"area_km2":"area_tot_km2"})

    inter = gpd.overlay(setores, st_buff, how="intersection").to_crs(3857)
    inter["area_km2"] = inter.geometry.area / 1e6
    inter = inter.to_crs(4326)

    df_area = inter.groupby(["CD_UF","NM_UF","SITUACAO"])["area_km2"].sum().reset_index()
    df_area = df_area.merge(area_total,on=["CD_UF","NM_UF"],how="left")
    df_area["Percentual"] = (df_area["area_km2"]/df_area["area_tot_km2"])*100
    df_pivot = df_area.pivot(index="NM_UF",columns="SITUACAO",values="Percentual").fillna(0)
    if "Urbana" in df_pivot.columns:
        df_pivot = df_pivot.sort_values("Urbana",ascending=True)

    # === Criação do gráfico ===
    cores = {"Urbana":"#64B5F6","Rural":"#A8E6CF"}
    fig = go.Figure()

    for situacao in ["Urbana","Rural"]:
        if situacao in df_pivot.columns:
            fig.add_trace(go.Bar(
                y=df_pivot.index,
                x=df_pivot[situacao],
                name=situacao,
                orientation="h",
                marker=dict(color=cores[situacao]),
                hovertemplate="<b>%{y}</b><br>Área "+situacao+": %{x:.2f}%<extra></extra>"
            ))

    # === Bandeiras ===
    max_x = df_pivot.sum(axis=1).max()*1.05
    x_flag = -max_x*0.04
    sizex = max_x*0.035
    images = []
    for uf in df_pivot.index:
        sigla = uf_to_sigla.get(uf)
        if not sigla:
            continue
        img_path = flags_dir / f"{sigla}.png"
        if not img_path.exists():
            continue
        with open(img_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        src = f"data:image/png;base64,{b64}"
        images.append(dict(
            source=src,
            xref="x",
            yref="y",
            x=x_flag,
            y=uf,
            sizex=sizex,
            sizey=0.8,
            xanchor="right",
            yanchor="middle",
            layer="above"
        ))

    fig.update_layout(
        images=images,
        barmode="stack",
        template="plotly_white",
        title=dict(
            text="Cobertura das redes de monitoramento por UF<br><sup>Percentual da área estadual com buffers ativos</sup>",
            x=0.5,font=dict(size=18)
        ),
        xaxis_title="Percentual da área do estado coberta por estações (%)",
        yaxis_title=None,
        yaxis=dict(showgrid=False,categoryorder="total ascending"),
        plot_bgcolor="white",
        paper_bgcolor="white",
        legend_title_text="Área",
        hovermode="y unified",
        height=950,
        margin=dict(l=120,r=40,t=80,b=40)
    )
    fig.update_xaxes(range=[-max_x*0.08,max_x])

    # === Salva e mostra inline ===
    if save_html:
        fig.write_html(html_path, include_plotlyjs="cdn", full_html=True)


    # Mostra direto no Jupyter (sem iframe)
    return HTML(fig.to_html(include_plotlyjs="cdn", full_html=False))
