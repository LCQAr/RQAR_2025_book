# -*- coding: utf-8 -*-
"""
Tabela populacional das estações de monitoramento:
- Modo resumido e detalhado
- Bandeiras embutidas em base64
- Cache automático (CSV)
- Gera HTML interativo e leve
- Exibição inline (rápida) no Jupyter
"""

import os
import re
import base64
import pandas as pd
import geopandas as gpd
from pathlib import Path
from IPython.display import display, HTML, IFrame
from itables import to_html_datatable
import webbrowser
import itables.options
import itables.options as opt
opt.dom = "tip"  # t = tabela, i = info (rodapé), p = paginação
opt.buttons = []
opt.searchPanes = False

# SILENCIA O AVISO DE SINTAXE DO ITABLES
itables.options.warn_on_undocumented_option = False 

# ========================
# Caminhos principais
# ========================
rootPath    = Path(os.path.dirname(os.getcwd()))
STATIC_DIR = rootPath / "_static" / "representatividade"
FLAGS_DIR  = rootPath / "_static" / "bandeiras"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

BUFFER_PATH = rootPath / "data/outputs/buffers_var.gpkg"
SETOR_PATH  = rootPath / "data/setores_censitarios/BR_setores_pop2022.gpkg"

codigo_para_uf = {
    12: 'AC', 27: 'AL', 13: 'AM', 16: 'AP', 29: 'BA', 23: 'CE', 53: 'DF',
    32: 'ES', 52: 'GO', 21: 'MA', 31: 'MG', 50: 'MS', 51: 'MT', 15: 'PA',
    25: 'PB', 26: 'PE', 22: 'PI', 41: 'PR', 33: 'RJ', 24: 'RN', 11: 'RO',
    14: 'RR', 43: 'RS', 42: 'SC', 28: 'SE', 35: 'SP', 17: 'TO'
}

# ========================
# Bandeira embutida
# ========================
def bandeira_base64(uf: str) -> str:
    img_path = FLAGS_DIR / f"{uf}.png"
    # Tamanho da imagem
    width_size = 20 
    if img_path.exists():
        with open(img_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
            return f'<img src="data:image/png;base64,{b64}" width="{width_size}">'
    return ""

# ========================
# Função principal: cálculo
# ========================
def tabela_populacao_flag(modo="resumido", pop_min_corte_detalhado=100, pop_min_corte_resumido=1000):
    """
    Calcula a cobertura populacional das estações por UF e poluente.
    Pode ser 'resumido' (sem sobreposição total) ou 'detalhado' (sem sobreposição dentro de cada poluente).
    """

    buffers_all = gpd.read_file(BUFFER_PATH).to_crs(5880)
    setores = gpd.read_file(SETOR_PATH).to_crs(5880)

    # Calcula área original dos setores
    setores["AREA_ORIGINAL"] = setores.area 

    if "CD_UF" not in setores.columns:
        setores["CD_UF"] = setores["CD_MUN"].astype(str).str[:2].astype(int)
    else:
        setores["CD_UF"] = setores["CD_UF"].astype(int)

    # =========================================================
    # 🔹 MODO RESUMIDO — descarta sobreposição total
    # =========================================================
    if modo == "resumido":
        buffers_max = (
            buffers_all.sort_values("REP_ESPACIAL_NUM")
            .groupby("ID_OEMA")
            .tail(1)
        )

        inter_est = gpd.sjoin(
            buffers_max, setores[["CD_UF", "geometry"]],
            how="left", predicate="intersects"
        )
        inter_est["UF"] = inter_est["CD_UF"].map(codigo_para_uf)

        # União por UF — remove sobreposições entre buffers
        buffers_union = inter_est.dissolve(by="UF").reset_index()
        inter = gpd.overlay(setores, buffers_union, how="intersection")

        # Cálculo proporcional
        inter["AREA_PROP"] = inter.area / inter["AREA_ORIGINAL"].replace(0, 1e-9)
        inter["POP_PROP"] = inter["POP2022"] * inter["AREA_PROP"]

        if inter.empty:
            return pd.DataFrame(columns=["Bandeira", "Estado", "População atendida", "Número de estações"])

        # Soma por UF
        resumo = (
            inter.groupby("UF")["POP_PROP"]
            .sum()
            .round(0)
            .reset_index(name="POP2022")
        )

        # Corte mínimo após soma
        resumo = resumo[resumo["POP2022"] >= pop_min_corte_resumido].copy()

        # Contagem de estações
        estacoes = inter_est.groupby("UF")["ID_OEMA"].nunique().reset_index(name="N_ESTACOES")
        resumo = resumo.merge(estacoes, on="UF", how="left")

        # Linha total Brasil
        resumo_total = pd.DataFrame([{
            "UF": "BR",
            "POP2022": resumo["POP2022"].sum().round(0),
            "N_ESTACOES": resumo["N_ESTACOES"].sum()
        }])
        resumo = pd.concat([resumo, resumo_total], ignore_index=True)

    # =========================================================
    # 🔹 MODO DETALHADO — descarta sobreposição por POLUENTE
    # =========================================================
    else:
        buffers = buffers_all.copy()

        # União dos buffers por poluente
        buffers_union = buffers.dissolve(by="POLUENTE").reset_index()

        # Overlay com setores
        inter = gpd.overlay(setores, buffers_union, how="intersection")

        # Cálculo proporcional
        inter["AREA_PROP"] = inter.area / inter["AREA_ORIGINAL"].replace(0, 1e-9)
        inter["POP_PROP"] = inter["POP2022"] * inter["AREA_PROP"]

        # Corte mínimo
        inter_filtrada = inter[inter["POP_PROP"] >= pop_min_corte_detalhado].copy()

        if inter_filtrada.empty:
            return pd.DataFrame(columns=["Bandeira", "Estado", "Poluente", "População atendida", "Número de estações"])

        # Soma por UF e poluente
        resumo = (
            inter_filtrada.groupby(["CD_UF", "POLUENTE"])["POP_PROP"]
            .sum()
            .round(0)
            .reset_index(name="POP2022")
        )
        resumo["UF"] = resumo["CD_UF"].map(codigo_para_uf)

        # Contagem de estações
        inter_est = gpd.sjoin(
            buffers_all, setores[["CD_UF", "geometry"]],
            how="left", predicate="intersects"
        )
        inter_est["UF"] = inter_est["CD_UF"].map(codigo_para_uf)
        estacoes = inter_est.groupby("UF")["ID_OEMA"].nunique().reset_index(name="N_ESTACOES")

        resumo = resumo.merge(estacoes, on="UF", how="left")
        resumo["POP2022"] = resumo["POP2022"].astype(int)

    # =========================================================
    # 🔸 PÓS-PROCESSAMENTO COMUM
    # =========================================================
    resumo["Bandeira"] = resumo["UF"].apply(bandeira_base64)
    resumo = resumo.fillna(0)
    resumo["N_ESTACOES"] = resumo["N_ESTACOES"].astype(int)
    resumo["POP2022"] = resumo["POP2022"].astype(int)

    col_mapping = {
        "UF": "Estado",
        "POP2022": "População atendida",
        "N_ESTACOES": "Número de estações",
        "POLUENTE": "Poluente",
    }

    resumo.rename(columns=col_mapping, inplace=True)

    # Reorganização de colunas
    if "Poluente" in resumo.columns:
        resumo = resumo[["Bandeira", "Estado", "Poluente", "População atendida", "Número de estações"]]
    else:
        resumo = resumo[["Bandeira", "Estado", "População atendida", "Número de estações"]]

    # =========================================================
    # 🔹 EXIBIR SOMENTE OS POLUENTES DESEJADOS
    #    (sem afetar cálculos anteriores)
    # =========================================================
    POL_VALIDOS = ['MP25', 'MP10', 'CO', 'NO2', 'PTS', 'SO2', 'O3']

    if "Poluente" in resumo.columns:
        resumo = resumo[resumo["Poluente"].isin(POL_VALIDOS)].copy()

    return resumo




# ========================
# Função interativa com cache + HTML leve
# ========================
from IPython.display import HTML, display
import re

def tabela_populacao_interactive(
    modo="resumido",
    save_html=True,
    open_in_notebook=True,
    use_cache=True
):

    cache_csv = STATIC_DIR / f"tabela_populacao_{modo}.csv"
    html_path = STATIC_DIR / f"tabela_populacao_{modo}.html"
    html_path_leve = STATIC_DIR / f"tabela_populacao_{modo}_leve.html"

    # Cache
    if use_cache and cache_csv.exists():
        df = pd.read_csv(cache_csv)
    else:
        df = tabela_populacao_flag(modo=modo)
        df.to_csv(cache_csv, index=False)

    # 🔹 Ajuste do searchPane
    searchPaneColumns = [1, 2] if "Poluente" in df.columns else [1]

    html_code = to_html_datatable(
        df,
        classes="display compact stripe",
        dom="tip",
        buttons=[],
        allow_html=True,
        escape=False,
        index=False,
    )

    # CSS
    css_fullwidth = """
    <style>
    .itables, table.dataTable {
        width: 100% !important;
        font-size: 14pt !important;
    }
    table.dataTable thead th {
        text-align: left !important;
    }
    table.dataTable thead th.sorting,
    table.dataTable thead th.sorting_asc,
    table.dataTable thead th.sorting_desc {
        background-position: right center !important;
        padding-right: 25px !important;
    }
    </style>
    """

    html_code = css_fullwidth + html_code

    if save_html:
        html_path.write_text(html_code, encoding="utf-8")
        html_path_leve.write_text(
            re.sub(r"<script[\s\S]*?</script>", "", html_code),
            encoding="utf-8"
        )

    if open_in_notebook:
        display(HTML(html_code))

    return df, html_path




# ========================
# Abertura rápida (HTML leve)
# ========================
def abrir_html_rapido(modo="detalhado"):
    """
    Abre o HTML leve (sem scripts JS) inline no notebook.
    """
    html_path = STATIC_DIR / f"tabela_populacao_{modo}_leve.html"
    if not html_path.exists():
        print(f"⚠️ Arquivo HTML leve não encontrado: {html_path}")
        return

    with open(html_path, "r", encoding="utf-8") as f:
        html_code = f.read()

    display(HTML(html_code))


# ========================
# Abertura padrão (interativa)
# ========================
def abrir_html_salvo(modo="detalhado", width="100%", height="800px"):
    """
    Abre o HTML interativo salvo em _static/representatividade com largura total e maior altura.
    """
    html_path = STATIC_DIR / f"tabela_populacao_{modo}.html"
    if not html_path.exists():
        print(f"⚠️ Arquivo não encontrado: {html_path}")
        return

    display(IFrame(src=f"file://{html_path}", width=width, height=height))