# -*- coding: utf-8 -*-
"""
Tabela de Uso do Solo — versão estilo FLAGTAB
Gera um DataFrame pronto para usar em flagtab.tabela_iterativa()
"""

import os
import base64
import pandas as pd
from pathlib import Path


def land_use_table_flagtab(csv_name="uso_solo_varbuf.csv"):
    # Caminhos
    rootPath = Path(os.path.dirname(os.getcwd()))
    csv_path = rootPath / "data" / "outputs" / csv_name
    flags_dir = rootPath / "_static" / "bandeiras"

    if not csv_path.exists():
        raise FileNotFoundError(f"❌ Arquivo não encontrado: {csv_path}")

    # -----------------------------------------------------
    # 1) Ler CSV
    # -----------------------------------------------------
    df = pd.read_csv(csv_path)

    # Normalizar poluentes (opcional)
    pollutant_map = {
        "PM10": "MP10",
        "PM25": "MP25",
        "PM1": None,
        "VOC": None
    }
    if "POLUENTE" in df.columns:
        df["POLUENTE"] = df["POLUENTE"].replace(pollutant_map)
        df = df[df["POLUENTE"].notna()]

    # -----------------------------------------------------
    # 2) Selecionar colunas como no flagtab
    # -----------------------------------------------------
    columnsSelector = [
        "UF",
        "ID_OEMA",
        "POLUENTE",
        "REP_ESPACIAL",
        "GRUPO_PRED_VAR",
        "Floresta_perc",
        "Herbácea_perc",
        "Agropecuária_perc",
        "Não Vegetada_perc",
        "Urbanizada_perc",
        "Mineração_perc",
    ]

    df = df[[c for c in columnsSelector if c in df.columns]]

    # -----------------------------------------------------
    # 3) Renomear colunas (nome amigável)
    # -----------------------------------------------------
    df.rename(columns={
        "POLUENTE": "Poluente",
        "REP_ESPACIAL": "Buffer (m)",
        "GRUPO_PRED_VAR": "Predominância",
        "Floresta_perc": "Floresta (%)",
        "Herbácea_perc": "Herbácea (%)",
        "Agropecuária_perc": "Agropecuária (%)",
        "Não Vegetada_perc": "Não Vegetada (%)",
        "Urbanizada_perc": "Urbanizada (%)",
        "Mineração_perc": "Mineração (%)",
    }, inplace=True)

    # -----------------------------------------------------
    # 4) Adicionar coluna de bandeiras (base64)
    # -----------------------------------------------------
    def embed_flag(uf):
        p = flags_dir / f"{uf}.png"
        if p.exists():
            b64 = base64.b64encode(p.read_bytes()).decode("utf-8")
            return f'<img src="data:image/png;base64,{b64}" width="26">'
        return ""

    df["Bandeira"] = df["UF"].apply(embed_flag)
    df = df[["Bandeira"] + [c for c in df.columns if c != "Bandeira"]]

    # -----------------------------------------------------
    # 5) Ordenar por UF (igual flagtab)
    # -----------------------------------------------------
    df = df.sort_values(by="UF", ascending=True).reset_index(drop=True)

    return df
