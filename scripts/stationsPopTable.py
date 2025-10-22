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

# ========================
# Caminhos principais
# ========================
rootPath   = Path(os.path.dirname(os.getcwd()))
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
    if img_path.exists():
        with open(img_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
            return f'<img src="data:image/png;base64,{b64}" width="30">'
    return ""

# ========================
# Função principal: cálculo
# ========================
def tabela_populacao_flag(modo="resumido"):
    """
    Calcula a cobertura populacional das estações por UF e poluente.
    Pode ser 'resumido' ou 'detalhado'.
    """
    print(f"🔍 Calculando modo {modo.upper()}...")
    buffers_all = gpd.read_file(BUFFER_PATH).to_crs(5880)
    setores = gpd.read_file(SETOR_PATH).to_crs(5880)

    if "CD_UF" not in setores.columns:
        setores["CD_UF"] = setores["CD_MUN"].astype(str).str[:2].astype(int)
    else:
        setores["CD_UF"] = setores["CD_UF"].astype(int)

    # ======================
    # Modo RESUMIDO
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

        buffers_union = inter_est.dissolve(by="UF").reset_index()
        inter = gpd.overlay(setores, buffers_union, how="intersection")
        inter["AREA_PROP"] = inter.area / inter["geometry"].area
        inter["POP_PROP"] = inter["POP2022"] * inter["AREA_PROP"]

        resumo = (
            inter.groupby("UF")["POP_PROP"]
            .sum()
            .reset_index(name="POP2022")
        )
        estacoes = inter_est.groupby("UF")["ID_OEMA"].nunique().reset_index(name="N_ESTACOES")
        resumo = resumo.merge(estacoes, on="UF", how="left")

        resumo_total = pd.DataFrame([{
            "UF": "BR",
            "POP2022": resumo["POP2022"].sum(),
            "N_ESTACOES": resumo["N_ESTACOES"].sum()
        }])
        resumo = pd.concat([resumo, resumo_total], ignore_index=True)

    # ======================
    # Modo DETALHADO
    # ======================
    else:
        buffers = buffers_all.copy()
        inter = gpd.overlay(setores, buffers, how="intersection")
        inter["AREA_PROP"] = inter.area / inter["geometry"].area
        inter["POP_PROP"] = inter["POP2022"] * inter["AREA_PROP"]

        resumo = (
            inter.groupby(["CD_UF", "POLUENTE"])["POP_PROP"]
            .sum()
            .reset_index(name="POP2022")
        )
        resumo["UF"] = resumo["CD_UF"].map(codigo_para_uf)

        inter_est = gpd.sjoin(
            buffers_all, setores[["CD_UF", "geometry"]],
            how="left", predicate="intersects"
        )
        inter_est["UF"] = inter_est["CD_UF"].map(codigo_para_uf)
        estacoes = inter_est.groupby("UF")["ID_OEMA"].nunique().reset_index(name="N_ESTACOES")

        resumo = resumo.merge(estacoes, on="UF", how="left")

    # Bandeiras embutidas
    resumo["Bandeira"] = resumo["UF"].apply(bandeira_base64)
    resumo = resumo.fillna(0)

    if "POLUENTE" in resumo.columns:
        resumo = resumo[["Bandeira", "UF", "POLUENTE", "POP2022", "N_ESTACOES"]]
    else:
        resumo = resumo[["Bandeira", "UF", "POP2022", "N_ESTACOES"]]

    return resumo


# ========================
# Função interativa com cache + HTML leve
# ========================
def tabela_populacao_interactive(modo="resumido", save_html=True, open_in_notebook=True, use_cache=True):
    """
    Gera ou carrega a tabela populacional (resumido ou detalhado).
    Cria também versão leve (sem JavaScript) para abertura instantânea.
    """
    cache_csv = STATIC_DIR / f"tabela_populacao_{modo}.csv"
    html_path = STATIC_DIR / f"tabela_populacao_{modo}.html"
    html_path_leve = STATIC_DIR / f"tabela_populacao_{modo}_leve.html"

    if use_cache and cache_csv.exists():
        print(f"⚡ Usando cache existente: {cache_csv}")
        df = pd.read_csv(cache_csv)
    else:
        print("🧭 Recalculando interseções espaciais...")
        df = tabela_populacao_flag(modo=modo)
        df.to_csv(cache_csv, index=False)
        print(f"💾 Cache salvo em: {cache_csv}")

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

    if save_html:
        # HTML interativo
        html_path.write_text(html_code, encoding="utf-8")
        print(f"✅ HTML interativo salvo em: {html_path}")

        # HTML leve (remove scripts JS)
        html_leve = re.sub(r"<script[\s\S]*?</script>", "", html_code)
        html_path_leve.write_text(html_leve, encoding="utf-8")
        print(f"💨 HTML leve salvo em: {html_path_leve}")

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
        print("⚠️ Gere primeiro com tabela_populacao_interactive().")
        return

    print(f"⚡ Abertura rápida: {html_path.name}")
    with open(html_path, "r", encoding="utf-8") as f:
        html_code = f.read()

    display(HTML(html_code))


# ========================
# Abertura padrão (interativa)
# ========================
def abrir_html_salvo(modo="detalhado", width=950, height=600):
    """
    Abre o HTML interativo salvo em _static/representatividade.
    """
    html_path = STATIC_DIR / f"tabela_populacao_{modo}.html"
    if not html_path.exists():
        print("⚠️ Gere primeiro com tabela_populacao_interactive().")
        return

    print(f"📄 Exibindo inline: {html_path}")
    display(IFrame(src=f"file://{html_path}", width=width, height=height))
