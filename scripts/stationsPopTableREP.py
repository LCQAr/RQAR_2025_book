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
BANDEIRAS_PATH = rootPath / "RQAR_2025_book/_static/bandeiras"
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
def tabela_populacao_flag(modo="resumido", debug=False,
                          path_bandeiras=rootPath / "RQAR_2025_book/_static/bandeiras"):

    # ... (mesmo cálculo de POP2022 e N_ESTACOES)

    # Garantir que todos os estados aparecem
    df_index, uf_to_region, uf_order = tableReorder(regioes)
    resumo = df_index.merge(resumo, on="UF", how="left")
    resumo["REGIAO"] = resumo["UF"].map(uf_to_region)
    resumo["ORDEM"] = resumo["UF"].map(uf_order)
    resumo = resumo.sort_values("ORDEM").drop(columns="ORDEM").reset_index(drop=True)

    # Bandeiras
    resumo["FLAG"] = resumo["UF"].apply(
        lambda uf: f'<img src="{path_bandeiras}/{uf}.png" width="30">' if uf != "BR" else ""
    )

    # Selecionar colunas finais
    display_df = resumo[["FLAG", "UF", "POP2022", "N_ESTACOES", "REGIAO"]]
    display_df.rename(columns={"FLAG": ""}, inplace=True)

    # Substituir NaN por "-"
    display_df = display_df.fillna(0)
    display_df[["POP2022","N_ESTACOES"]] = display_df[["POP2022","N_ESTACOES"]].astype(int)
    display_df = display_df.replace(0, "-")

    # Montar tabela com separadores por região
    rows = []
    for group, data in display_df.groupby("REGIAO", sort=False):
        rows.append({"": "", "UF": group, "POP2022":"", "N_ESTACOES":"", "REGIAO":""})
        rows.extend(data.to_dict("records"))
        rows.append({"": "", "UF": "", "POP2022":"", "N_ESTACOES":"", "REGIAO":""})

    rows.insert(0, {"": "", "UF": "", "POP2022":"", "N_ESTACOES":"", "REGIAO":""})
    df_final = pd.DataFrame(rows).drop(columns=["REGIAO"])

    # Estilo igual à table06
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
