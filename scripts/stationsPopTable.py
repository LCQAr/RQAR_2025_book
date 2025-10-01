# -*- coding: utf-8 -*-
"""
Mapa + Tabela: População atendida por estação de monitoramento
- Tabela resumida: usa apenas o maior buffer por estação (população atendida e nº de estações únicas por UF)
- Tabela detalhada: mostra população atendida por cada buffer/poluente em cada estado
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

BUFFER_PATH = OUTPUT_DIR / "buffers_var.gpkg"
SETOR_PATH  = rootPath / "data/setores_censitarios/BR_setores_pop2022.gpkg"

# Dicionário de UFs
codigo_para_uf = {
    12: 'AC', 27: 'AL', 13: 'AM', 16: 'AP', 29: 'BA', 23: 'CE', 53: 'DF',
    32: 'ES', 52: 'GO', 21: 'MA', 31: 'MG', 50: 'MS', 51: 'MT', 15: 'PA',
    25: 'PB', 26: 'PE', 22: 'PI', 41: 'PR', 33: 'RJ', 24: 'RN', 11: 'RO',
    14: 'RR', 43: 'RS', 42: 'SC', 28: 'SE', 35: 'SP', 17: 'TO'
}


# ========================
# Função principal
# ========================
def tabela_populacao_flag(modo="resumido", debug=False):
    """
    modo = "resumido"  -> só o maior buffer por estação (união p/ evitar dupla contagem)
    modo = "detalhado" -> todos os buffers (poluentes separados)
    """
    # Leitura dos dados
    buffers_all = gpd.read_file(BUFFER_PATH).to_crs(5880)
    setores = gpd.read_file(SETOR_PATH).to_crs(5880)

    # Garante que CD_UF é int
    if "CD_UF" not in setores.columns:
        setores["CD_UF"] = setores["CD_MUN"].astype(str).str[:2].astype(int)
    else:
        setores["CD_UF"] = setores["CD_UF"].astype(int)

    # ======================
    # RESUMIDO → maior buffer + união
    # ======================
    if modo == "resumido":
        # pega só o maior buffer por estação
        buffers_max = (
            buffers_all.sort_values("REP_ESPACIAL")
            .groupby("ID_OEMA")
            .tail(1)
        )

        # join espacial p/ descobrir estado de cada estação
        inter_est = gpd.sjoin(
            buffers_max, setores[["CD_UF", "geometry"]],
            how="left", predicate="intersects"
        )
        inter_est["UF"] = inter_est["CD_UF"].map(codigo_para_uf)

        # dissolve buffers por UF (união → evita dupla contagem de população)
        buffers_union = inter_est.dissolve(by="UF").reset_index()

        # intersecta união dos buffers com setores
        inter = gpd.overlay(setores, buffers_union, how="intersection")
        inter["AREA_PROP"] = inter.area / inter["geometry"].area
        inter["POP_PROP"] = inter["POP2022"] * inter["AREA_PROP"]

        # população coberta por UF
        resumo = (
            inter.groupby("UF")["POP_PROP"]
            .sum()
            .reset_index(name="POP2022")
        )

        # número de estações únicas
        estacoes = inter_est.groupby("UF")["ID_OEMA"].nunique().reset_index(name="N_ESTACOES")
        resumo = resumo.merge(estacoes, on="UF", how="left")

        # Brasil total
        resumo_total = pd.DataFrame([{
            "UF": "BR",
            "POP2022": resumo["POP2022"].sum(),
            "N_ESTACOES": resumo["N_ESTACOES"].sum()
        }])
        resumo = pd.concat([resumo, resumo_total], ignore_index=True)

    # ======================
    # DETALHADO → todos buffers/poluentes
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

        # número de estações únicas por UF
        inter_est = gpd.sjoin(
            buffers_all, setores[["CD_UF", "geometry"]],
            how="left", predicate="intersects"
        )
        inter_est["UF"] = inter_est["CD_UF"].map(codigo_para_uf)
        estacoes = inter_est.groupby("UF")["ID_OEMA"].nunique().reset_index(name="N_ESTACOES")

        resumo = resumo.merge(estacoes, on="UF", how="left")

    if debug:
        print("\n=== Resumo final ===")
        print(resumo.head(30))

    return resumo


# ========================
# Função de exibição
# ========================
def mostrar_tabela(modo="resumido", debug=False):
    df = tabela_populacao_flag(modo=modo, debug=debug)

    # troca NaN por 0
    df = df.fillna(0)

    # ordena colunas
    if "POLUENTE" in df.columns:
        cols = ["UF", "POLUENTE", "POP2022", "N_ESTACOES"]
    else:
        cols = ["UF", "POP2022", "N_ESTACOES"]

    df = df[cols]

    # exibe no notebook
    return display(HTML(df.to_html(index=False, border=0)))
