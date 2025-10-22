# -*- coding: utf-8 -*-
"""
Mapa + Tabelas de População atendida por estação de monitoramento
- Resumida: maior buffer por estação, união por UF (com bandeiras e regiões)
- Detalhada: todos os buffers/poluentes por estado
"""

import os
import pandas as pd
import geopandas as gpd
from IPython.display import display, HTML
from pathlib import Path

# ========================
# Configurações
# ========================
rootPath   = Path(os.path.dirname(os.getcwd()))
OUTPUT_DIR = rootPath / "data/outputs"

BUFFER_PATH   = OUTPUT_DIR / "buffers_var.gpkg"
SETOR_PATH    = rootPath / "data/setores_censitarios/BR_setores_pop2022.gpkg"
BANDEIRAS_DIR = rootPath / "RQAR_2025_book/_static/bandeiras"

codigo_para_uf = {
    12: 'AC', 27: 'AL', 13: 'AM', 16: 'AP', 29: 'BA', 23: 'CE', 53: 'DF',
    32: 'ES', 52: 'GO', 21: 'MA', 31: 'MG', 50: 'MS', 51: 'MT', 15: 'PA',
    25: 'PB', 26: 'PE', 22: 'PI', 41: 'PR', 33: 'RJ', 24: 'RN', 11: 'RO',
    14: 'RR', 43: 'RS', 42: 'SC', 28: 'SE', 35: 'SP', 17: 'TO'
}

regioes = {
    "Norte":    ["AC","AM","AP","PA","RO","RR","TO"],
    "Nordeste": ["AL","BA","CE","MA","PB","PE","PI","RN","SE"],
    "Centro-Oeste": ["DF","GO","MT","MS"],
    "Sudeste":  ["ES","MG","RJ","SP"],
    "Sul":      ["PR","RS","SC"]
}

# ========================
# Helpers
# ========================
def tableReorder(regioes_dict):
    uf_to_region = {uf: reg for reg, ufs in regioes_dict.items() for uf in ufs}
    uf_order = {uf: i for i, (reg, ufs) in enumerate(regioes_dict.items()) for uf in ufs}
    df_index = pd.DataFrame({"UF": [uf for reg in regioes_dict.values() for uf in reg]})
    return df_index, uf_to_region, uf_order

def style_all_white(row):
    return ["background-color: white"] * len(row)

# ========================
# TABELA DETALHADA
# ========================
def tabela_populacao_detalhada(debug=False):
    buffers_all = gpd.read_file(BUFFER_PATH).to_crs(5880)
    setores = gpd.read_file(SETOR_PATH).to_crs(5880)

    if "CD_UF" not in setores.columns:
        setores["CD_UF"] = setores["CD_MUN"].astype(str).str[:2].astype(int)
    else:
        setores["CD_UF"] = setores["CD_UF"].astype(int)

    inter = gpd.overlay(setores, buffers_all, how="intersection")
    inter["AREA_PROP"] = inter.area / inter["geometry"].area
    inter["POP_PROP"] = inter["POP2022"] * inter["AREA_PROP"]

    resumo = (
        inter.groupby(["CD_UF", "POLUENTE"])["POP_PROP"]
        .sum()
        .reset_index(name="POP2022")
    )
    resumo["UF"] = resumo["CD_UF"].map(codigo_para_uf)

    # Número de estações por UF
    inter_est = gpd.sjoin(buffers_all, setores[["CD_UF", "geometry"]],
                          how="left", predicate="intersects")
    inter_est["UF"] = inter_est["CD_UF"].map(codigo_para_uf)
    estacoes = inter_est.groupby("UF")["ID_OEMA"].nunique().reset_index(name="N_ESTACOES")

    resumo = resumo.merge(estacoes, on="UF", how="left")

    if debug:
        print(resumo.head(30))
    return resumo[["UF","POLUENTE","POP2022","N_ESTACOES"]]

# ========================
# TABELA RESUMIDA
# ========================
def tabela_populacao_resumida(debug=False, path_bandeiras=BANDEIRAS_DIR):
    buffers_all = gpd.read_file(BUFFER_PATH).to_crs(5880)
    setores = gpd.read_file(SETOR_PATH).to_crs(5880)

    if "CD_UF" not in setores.columns:
        setores["CD_UF"] = setores["CD_MUN"].astype(str).str[:2].astype(int)
    else:
        setores["CD_UF"] = setores["CD_UF"].astype(int)

    # Maior buffer por estação
    buffers_max = (
        buffers_all.sort_values("REP_ESPACIAL")
        .groupby("ID_OEMA")
        .tail(1)
    )

    inter_est = gpd.sjoin(buffers_max, setores[["CD_UF","geometry"]],
                          how="left", predicate="intersects")
    inter_est["UF"] = inter_est["CD_UF"].map(codigo_para_uf)

    buffers_union = inter_est.dissolve(by="UF").reset_index()
    inter = gpd.overlay(setores, buffers_union, how="intersection")
    inter["AREA_PROP"] = inter.area / inter["geometry"].area
    inter["POP_PROP"] = inter["POP2022"] * inter["AREA_PROP"]

    resumo = inter.groupby("UF")["POP_PROP"].sum().reset_index(name="POP2022")
    estacoes = inter_est.groupby("UF")["ID_OEMA"].nunique().reset_index(name="N_ESTACOES")
    resumo = resumo.merge(estacoes, on="UF", how="left")

    resumo_total = pd.DataFrame([{
        "UF": "BR",
        "POP2022": resumo["POP2022"].sum(),
        "N_ESTACOES": resumo["N_ESTACOES"].sum()
    }])
    resumo = pd.concat([resumo, resumo_total], ignore_index=True)

    # Garantir ordem/região
    df_index, uf_to_region, uf_order = tableReorder(regioes)
    resumo = df_index.merge(resumo, on="UF", how="left")
    resumo["REGIAO"] = resumo["UF"].map(uf_to_region)
    resumo["ORDEM"] = resumo["UF"].map(uf_order)
    resumo = resumo.sort_values("ORDEM").drop(columns="ORDEM").reset_index(drop=True)

    # Bandeiras
    resumo["FLAG"] = resumo["UF"].apply(
        lambda uf: f'<img src="{path_bandeiras}/{uf}.png" width="30">' if uf != "BR" else ""
    )

    display_df = resumo[["FLAG","UF","POP2022","N_ESTACOES","REGIAO"]]
    display_df.rename(columns={"FLAG":""}, inplace=True)

    display_df = display_df.fillna(0)
    display_df[["POP2022","N_ESTACOES"]] = display_df[["POP2022","N_ESTACOES"]].astype(int)
    display_df = display_df.replace(0, "-")

    # Separadores por região
    rows = []
    for group, data in display_df.groupby("REGIAO", sort=False):
        rows.append({"": "", "UF": group, "POP2022":"", "N_ESTACOES":"", "REGIAO":""})
        rows.extend(data.to_dict("records"))
        rows.append({"": "", "UF": "", "POP2022":"", "N_ESTACOES":"", "REGIAO":""})

    rows.insert(0, {"": "", "UF": "", "POP2022":"", "N_ESTACOES":"", "REGIAO":""})
    df_final = pd.DataFrame(rows).drop(columns=["REGIAO"])

    styled = (
        df_final
        .style
        .apply(style_all_white, axis=1)
        .hide(axis="index")
        .set_table_styles([
            {'selector': 'th', 'props': [('text-align', 'center')]},
            {'selector': 'td > img', 'props': [('max-width', 'unset')]}
        ])
    )
    return display(HTML(styled.to_html(index=False, border=0, escape=False)))
