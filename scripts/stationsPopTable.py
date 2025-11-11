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
opt.dom = "Bfrtip"  # mantém botões, remove SearchPanes
opt.buttons = ["copy", "csv", "excel"]
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
    Pode ser 'resumido' ou 'detalhado'.
    """

    buffers_all = gpd.read_file(BUFFER_PATH).to_crs(5880)
    setores = gpd.read_file(SETOR_PATH).to_crs(5880)

    # CORREÇÃO: Calcular e armazenar a área original do setor
    setores["AREA_ORIGINAL"] = setores.area 

    if "CD_UF" not in setores.columns:
        setores["CD_UF"] = setores["CD_MUN"].astype(str).str[:2].astype(int)
    else:
        setores["CD_UF"] = setores["CD_UF"].astype(int)

    # ======================
    # Modo RESUMIDO (Lógica revisada e filtro aplicado no resultado final)
    # ======================
    if modo == "resumido":
        buffers_max = (
            buffers_all.sort_values("REP_ESPACIAL")
            .groupby("ID_OEMA")
            .tail(1)
        )
        inter_est = gpd.sjoin(
            buffers_max, setores[["CD_UF", "geometry"]],
            how="left", predicate="intersects"
        )
        inter_est["UF"] = inter_est["CD_UF"].map(codigo_para_uf)

        # Dissolve (união) para obter a área total não redundante por UF
        buffers_union = inter_est.dissolve(by="UF").reset_index()
        inter = gpd.overlay(setores, buffers_union, how="intersection")
        
        # CÁLCULO APL CORRIGIDO
        inter["AREA_PROP"] = inter.area / inter["AREA_ORIGINAL"].replace(0, 1e-9)
        inter["POP_PROP"] = inter["POP2022"] * inter["AREA_PROP"]
        
        # FILTRO DE CORTE REMOVIDO DESTE PONTO (para não descartar setores)

        if inter.empty:
            return pd.DataFrame(columns=["Bandeira", "UF", "POP2022", "N_ESTACOES"])

        # Soma total da população atendida por UF
        resumo = (
            inter.groupby("UF")["POP_PROP"]
            .sum()
            .round(0) 
            .reset_index(name="POP2022")
        )
        
        # FILTRO RESUMIDO CORRIGIDO: Aplicado APÓS a soma total por UF
        resumo = resumo[resumo["POP2022"] >= pop_min_corte_resumido].copy()

        estacoes = inter_est.groupby("UF")["ID_OEMA"].nunique().reset_index(name="N_ESTACOES")
        resumo = resumo.merge(estacoes, on="UF", how="left")

        resumo_total = pd.DataFrame([{
            "UF": "BR",
            "POP2022": resumo["POP2022"].sum().round(0),
            "N_ESTACOES": resumo["N_ESTACOES"].sum()
        }])
        resumo = pd.concat([resumo, resumo_total], ignore_index=True)

    # ======================
    # Modo DETALHADO (Mantém o filtro para ruído de buffer individual)
    # ======================
    else:
        buffers = buffers_all.copy()
        inter = gpd.overlay(setores, buffers, how="intersection")
        
        # CÁLCULO APL CORRIGIDO
        inter["AREA_PROP"] = inter.area / inter["AREA_ORIGINAL"].replace(0, 1e-9)
        inter["POP_PROP"] = inter["POP2022"] * inter["AREA_PROP"]

        # FILTRO DETALHADO: Remove intersecções populacionais < 100
        inter_filtrada = inter[inter["POP_PROP"] >= pop_min_corte_detalhado].copy()
        
        if inter_filtrada.empty:
             return pd.DataFrame(columns=["Bandeira", "UF", "POLUENTE", "POP2022", "N_ESTACOES"])

        resumo = (
            inter_filtrada.groupby(["CD_UF", "POLUENTE"])["POP_PROP"]
            .sum()
            .round(0) 
            .reset_index(name="POP2022")
        )
        resumo["UF"] = resumo["CD_UF"].map(codigo_para_uf)

        # Contagem de Estações (sem o filtro POP)
        inter_est = gpd.sjoin(
            buffers_all, setores[["CD_UF", "geometry"]],
            how="left", predicate="intersects"
        )
        inter_est["UF"] = inter_est["CD_UF"].map(codigo_para_uf)
        estacoes = inter_est.groupby("UF")["ID_OEMA"].nunique().reset_index(name="N_ESTACOES")

        resumo = resumo.merge(estacoes, on="UF", how="left")
        resumo["POP2022"] = resumo["POP2022"].astype(int)

    # Pós-processamento comum
    resumo["Bandeira"] = resumo["UF"].apply(bandeira_base64)
    resumo = resumo.fillna(0)
    resumo["N_ESTACOES"] = resumo["N_ESTACOES"].astype(int)
    resumo["POP2022"] = resumo["POP2022"].astype(int) 

    # RENOMEAR COLUNAS PARA PORTUGUÊS
    col_mapping = {
        "UF": "Estado",
        "POP2022": "População atendida",
        "N_ESTACOES": "Número de estações",
    }
    resumo.rename(columns=col_mapping, inplace=True)
    
    # Organização das colunas
    if "POLUENTE" in resumo.columns:
        resumo = resumo[["Bandeira", "Estado", "POLUENTE", "População atendida", "Número de estações"]]
    else:
        resumo = resumo[["Bandeira", "Estado", "População atendida", "Número de estações"]]

    return resumo


# ========================
# Função interativa com cache + HTML leve
# ========================
from IPython.display import HTML, display
import re

def tabela_populacao_interactive(modo="resumido", save_html=True, open_in_notebook=True, use_cache=True):
    """
    Gera ou carrega a tabela populacional (resumido ou detalhado),
    e exibe com largura total no notebook.
    """
    cache_csv = STATIC_DIR / f"tabela_populacao_{modo}.csv"
    html_path = STATIC_DIR / f"tabela_populacao_{modo}.html"
    html_path_leve = STATIC_DIR / f"tabela_populacao_{modo}_leve.html"

    if use_cache and cache_csv.exists():
        df = pd.read_csv(cache_csv)
    else:
        # Chama a função corrigida
        df = tabela_populacao_flag(modo=modo)
        df.to_csv(cache_csv, index=False)

    searchPaneColumns = [1, 2] if "POLUENTE" in df.columns else [1]

    html_code = to_html_datatable(
        df,
        classes="display compact stripe",
        buttons=["copyHtml5", "csvHtml5", "excelHtml5"],
        layout={"top2": "searchPanes"},
        searchPanes={"layout": "columns-3", "cascadePanes": True, "columns": searchPaneColumns},
        allow_html=True,
        escape=False,
        index=False,
    )

    # CSS Estilizado para 100% de largura e FONTE AUMENTADA (16pt)
    css_fullwidth = """
    <style>
    /* Ajustes para o itables (DataTables) */
    .itables, .jp-RenderedHTMLCommon table, table.dataTable {
        width: 100% !important;
        max-width: 100% !important;
        margin: 0 auto !important;
        font-size: 14pt !important; /* FONTE AUMENTADA */
    }
    .dataTables_wrapper {
        width: 100% !important;
        max-width: 100% !important;
        overflow-x: auto !important;
    }
    body, html {
        width: 100% !important;
        overflow-x: hidden !important;
    }
    /* Reduz o padding na coluna da bandeira (primeira coluna) */
    table.dataTable thead th:first-child,
    table.dataTable tbody td:first-child {
        width: 3% !important; 
        padding-left: 5px !important;
        padding-right: 5px !important;
        text-align: center;
    }
    /* Ajuste para o tamanho da fonte nos títulos/filtros do DataTables */
    .dataTables_wrapper label, .dataTables_wrapper .dataTables_info, 
    .dataTables_wrapper .dataTables_length, .dataTables_wrapper .dt-buttons {
        font-size: 11pt !important; /* Mantém os controles menores */
    }
    </style>
    """
    html_code = css_fullwidth + html_code

    if save_html:
        html_path.write_text(html_code, encoding="utf-8")
        html_leve = re.sub(r"<script[\s\S]*?</script>", "", html_code)
        html_path_leve.write_text(html_leve, encoding="utf-8")

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