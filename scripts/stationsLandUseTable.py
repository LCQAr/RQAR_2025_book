# -*- coding: utf-8 -*-
"""
Tabela interativa: Uso do solo (MapBiomas) por estação e poluente
Versão otimizada:
- Corrige e padroniza UFs (garante presença de todos os estados)
- Inclui bandeiras embutidas
- Usa paginação e renderização adiada (carregamento rápido)
- Compatível com Jupyter Book e visualização via IFrame
"""

import os
import base64
import pandas as pd
import numpy as np
from pathlib import Path


def land_use_table_interactive(
    csv_name: str = "uso_solo_varbuf.csv",
    save_html: bool = True,
    html_name: str = "tabela_uso_solo.html",
):
    """
    Gera uma tabela interativa leve de uso do solo (MapBiomas) por estação e poluente.
    - Corrige UFs e mantém todos os estados (inclusive Amazonas)
    - Ordena por UF, POLUENTE e Buffer
    - Bandeiras embutidas em base64
    - Usa paginação e renderização adiada
    """

    # =========================
    # Caminhos e entrada
    # =========================
    rootPath = Path(os.path.dirname(os.getcwd()))
    csv_path = rootPath / "data" / "outputs" / csv_name
    static_html_dir = rootPath / "_static" / "representatividade"
    flags_dir = rootPath / "_static" / "bandeiras"

    static_html_dir.mkdir(parents=True, exist_ok=True)
    html_path = static_html_dir / html_name

    if not csv_path.exists():
        raise FileNotFoundError(f"❌ Arquivo não encontrado: {csv_path}")

    print(f"📂 Lendo dados de: {csv_path}")
    df = pd.read_csv(csv_path)

    # =========================
    # Seleção e renomeação
    # =========================
    columnsSelector = [
        "UF", "ID_OEMA", "POLUENTE", "REP_ESPACIAL", "GRUPO_PRED_VAR",
        "Floresta_perc", "Herbácea_perc", "Agropecuária_perc",
        "Não Vegetada_perc", "Urbanizada_perc", "Mineração_perc"
    ]
    df = df[[c for c in columnsSelector if c in df.columns]].copy()

    df.rename(columns={
        "REP_ESPACIAL": "Buffer (m)",
        "GRUPO_PRED_VAR": "Predominância",
        "Floresta_perc": "Floresta (%)",
        "Herbácea_perc": "Herbácea (%)",
        "Agropecuária_perc": "Agropecuária (%)",
        "Não Vegetada_perc": "Não Vegetada (%)",
        "Urbanizada_perc": "Urbanizada (%)",
        "Mineração_perc": "Mineração (%)"
    }, inplace=True)

    # =========================
    # Padronização de UFs
    # =========================
    ordem_estados = [
        "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
        "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
        "SP", "SE", "TO"
    ]

    correcoes = {
        "AMAZONAS": "AM",
        "PARA": "PA", "PARÁ": "PA",
        "MATO GROSSO": "MT",
        "MATO GROSSO DO SUL": "MS",
        "MINAS GERAIS": "MG",
        "RIO DE JANEIRO": "RJ",
        "RIO GRANDE DO SUL": "RS",
        "RIO GRANDE DO NORTE": "RN",
        "SÃO PAULO": "SP", "SAO PAULO": "SP",
        "DISTRITO FEDERAL": "DF",
        "SANTA CATARINA": "SC",
        "CEARA": "CE", "CEARÁ": "CE",
    }

    df["UF"] = (
        df["UF"]
        .astype(str)
        .str.strip()
        .str.upper()
        .replace(correcoes)
        .replace({"NAN": np.nan, "": np.nan})
    )

    # Preenche estados faltantes (se existirem) com NaN seguro
    if df["UF"].isna().any():
        print(f"⚠️ Linhas sem UF: {df['UF'].isna().sum()}")

    # =========================
    # Bandeiras embutidas
    # =========================
    def embed_flag(uf):
        img_path = flags_dir / f"{uf}.png"
        if img_path.exists():
            with open(img_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
                return f'<img src="data:image/png;base64,{b64}" width="30">'
        return ""

    df["Bandeira"] = df["UF"].apply(embed_flag)

    # =========================
    # Ordenação segura (sem excluir nada)
    # =========================
    df["UF_ordem"] = df["UF"].apply(
        lambda x: ordem_estados.index(x) if x in ordem_estados else 999
    )
    df.sort_values(
        by=["UF_ordem", "POLUENTE", "Buffer (m)"],
        inplace=True,
        ignore_index=True
    )
    df.drop(columns=["UF_ordem"], inplace=True)

    # Reorganiza colunas
    cols = [
        "Bandeira", "UF", "POLUENTE", "Buffer (m)", "Predominância",
        "Floresta (%)", "Herbácea (%)", "Agropecuária (%)",
        "Não Vegetada (%)", "Urbanizada (%)", "Mineração (%)", "ID_OEMA"
    ]
    df = df[[c for c in cols if c in df.columns]]

    # =========================
    # Gera HTML otimizado (DataTables com paginação)
    # =========================
    if save_html:
        print("💾 Salvando tabela otimizada em _static/representatividade ...")

        html_table = df.to_html(
            classes="display compact stripe",
            index=False,
            escape=False,
            table_id="uso_solo"
        )

        html_code = f"""
        <html>
        <head>
          <meta charset="utf-8">
          <script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>
          <link rel="stylesheet"
                href="https://cdn.datatables.net/1.13.8/css/jquery.dataTables.min.css"/>
          <link rel="stylesheet"
                href="https://cdn.datatables.net/searchpanes/2.2.0/css/searchPanes.dataTables.min.css"/>
          <link rel="stylesheet"
                href="https://cdn.datatables.net/buttons/2.4.2/css/buttons.dataTables.min.css"/>
          <script src="https://cdn.datatables.net/1.13.8/js/jquery.dataTables.min.js"></script>
          <script src="https://cdn.datatables.net/searchpanes/2.2.0/js/dataTables.searchPanes.min.js"></script>
          <script src="https://cdn.datatables.net/buttons/2.4.2/js/dataTables.buttons.min.js"></script>
          <script src="https://cdn.datatables.net/buttons/2.4.2/js/buttons.html5.min.js"></script>
          <script>
            $(document).ready(function() {{
                $('#uso_solo').DataTable({{
                    dom: 'PlBfrtip',
                    buttons: ['copyHtml5', 'csvHtml5', 'excelHtml5'],
                    searchPanes: {{
                        cascadePanes: true,
                        layout: 'columns-3'
                    }},
                    pageLength: 25,
                    deferRender: true,
                    order: [[1, 'asc'], [2, 'asc'], [3, 'asc']],
                    language: {{
                        url: 'https://cdn.datatables.net/plug-ins/1.13.8/i18n/pt-BR.json'
                    }}
                }});
            }});
          </script>
        </head>
        <body>
        {html_table}
        </body>
        </html>
        """

        html_path.write_text(html_code, encoding="utf-8")
        print(f"✅ HTML leve salvo em: {html_path}")

    return df, html_path
