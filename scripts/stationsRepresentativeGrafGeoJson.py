# -*- coding: utf-8 -*-
import geopandas as gpd
import pandas as pd
from pathlib import Path
import os
import json

def gerar_geojson_figura8_dados(rootPath=None, outfile="figura8_dados.geojson"):
    """
    Gera um GeoJSON contendo SOMENTE os dados da Figura 8:
    - UF
    - % urbano
    - % rural
    - áreas
    (sem geometria, geometry = null)
    """

    rootPath = Path(rootPath or os.path.dirname(os.getcwd()))
    static_dir = rootPath / "_static" / "representatividade"
    static_dir.mkdir(parents=True, exist_ok=True)
    outfile = static_dir / outfile

    # === arquivos ===
    stations_file = rootPath / "data/rep_espacial/outputs/estacoes_completa.gpkg"
    setores_file  = rootPath / "data/setores_censitarios/BR_setores_pop2022.gpkg"

    # === estações ativas ===
    st = gpd.read_file(stations_file).to_crs(4326)
    if "STATUS" in st.columns:
        st = st[st["STATUS"].str.lower().str.contains("ativa")]

    # buffers
    st_proj = st.to_crs(3857)
    st_proj["geometry"] = st_proj.buffer(st_proj["REP_ESPACIAL"])
    st_buff = st_proj.to_crs(4326)

    # setores censitários
    setores = gpd.read_file(setores_file).to_crs(4326)[["CD_UF","NM_UF","SITUACAO","geometry"]]

    # área total UF
    setores_proj = setores.to_crs(3857)
    setores_proj["area_km2"] = setores_proj.geometry.area / 1e6
    area_total = setores_proj.groupby(["CD_UF","NM_UF"])["area_km2"] \
                             .sum().reset_index() \
                             .rename(columns={"area_km2":"area_tot_km2"})

    # interseção com buffers
    inter = gpd.overlay(setores, st_buff, how="intersection").to_crs(3857)
    inter["area_km2"] = inter.geometry.area / 1e6
    inter = inter.to_crs(4326)

    # soma por UF × situação
    df_area = inter.groupby(["CD_UF","NM_UF","SITUACAO"])["area_km2"] \
                   .sum().reset_index()

    # merge com área total UF
    df_area = df_area.merge(area_total, on=["CD_UF","NM_UF"])

    df_area["Percentual"] = (df_area["area_km2"] /
                             df_area["area_tot_km2"]) * 100

    # pivot -> 1 linha por UF
    df = df_area.pivot(index=["CD_UF","NM_UF"],
                       columns="SITUACAO",
                       values=["area_km2", "Percentual"]).fillna(0)

    df.columns = [f"{a}_{b}" for a,b in df.columns]
    df = df.reset_index()

    # renomeia para ficar limpo
    df = df.rename(columns={
        "area_km2_Urbana": "area_urbana_km2",
        "area_km2_Rural": "area_rural_km2",
        "Percentual_Urbana": "perc_urbana",
        "Percentual_Rural": "perc_rural",
    })

    # monta o GeoJSON manualmente (geometry = null)
    features = []
    for _, row in df.iterrows():
        props = row.to_dict()
        props.pop("geometry", None)
        features.append({
            "type": "Feature",
            "geometry": None,
            "properties": props
        })

    gj = {
        "type": "FeatureCollection",
        "features": features
    }

    with open(outfile, "w", encoding="utf-8") as f:
        json.dump(gj, f, ensure_ascii=False, indent=2)

    print(f"✅ GeoJSON gerado: {outfile}")
    return df
