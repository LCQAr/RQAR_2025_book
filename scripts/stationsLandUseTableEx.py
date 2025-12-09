# -*- coding: utf-8 -*-
"""
Versão compatível com build (Jupyter Book) da tabela de uso do solo.
Gera HTML autossuficiente (com DataTables carregado via CDN) — sem linhas entre colunas.
"""

import os
import base64
import pandas as pd
from pathlib import Path


def land_use_table_interactive(
    csv_name: str = "uso_solo_varbuf.csv",
    save_html: bool = True,
    html_name: str = "tabela_uso_solo.html",
    open_in_notebook: bool = True,
):
    # Caminhos principais
    rootPath = Path(os.path.dirname(os.getcwd()))
    csv_path = rootPath / "data" / "outputs" / csv_name
    static_html_dir = rootPath / "_static" / "representatividade"
    flags_dir = rootPath / "_static" / "bandeiras"

    static_html_dir.mkdir(parents=True, exist_ok=True)
    html_path = static_html_dir / html_name

    # ======== Lê CSV ========
    if not csv_path.exists():
        raise FileNotFoundError(f"❌ Arquivo não encontrado: {csv_path}")
    df = pd.read_csv(csv_path)

    # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    # === Normalizar e limpar poluentes indesejados ===
    pollutant_map = {
        "PM10": "MP10",
        "PM25": "MP25",
        "PM1": None,   # remover
        "VOC": None    # remover
    }
    if "POLUENTE" in df.columns:
        df["POLUENTE"] = df["POLUENTE"].replace(pollutant_map)
        df = df[df["POLUENTE"].notna()]
    # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

    # ======== Seleciona colunas principais ========
    columnsSelector = [
        "UF", "ID_OEMA", "POLUENTE", "REP_ESPACIAL", "GRUPO_PRED_VAR",
        "Floresta_perc", "Herbácea_perc", "Agropecuária_perc",
        "Não Vegetada_perc", "Urbanizada_perc", "Mineração_perc"
    ]
    df = df[[c for c in columnsSelector if c in df.columns]].copy()

    # Renomeia colunas
    df.rename(columns={
        "POLUENTE": "Poluente", 
        "REP_ESPACIAL": "Buffer (m)",
        "GRUPO_PRED_VAR": "Predominância",
        "Floresta_perc": "Floresta (%)",
        "Herbácea_perc": "Herbácea (%)",
        "Agropecuária_perc": "Agropecuária (%)",
        "Não Vegetada_perc": "Não Vegetada (%)",
        "Urbanizada_perc": "Urbanizada (%)",
        "Mineração_perc": "Mineração (%)"
    }, inplace=True)

    # ======== Bandeiras em base64 ========
    def embed_flag(uf):
        img_path = flags_dir / f"{uf}.png"
        if img_path.exists():
            with open(img_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
                return f'<img src="data:image/png;base64,{b64}" width="25">'
        else:
            return ""
    df["Bandeira"] = df["UF"].apply(embed_flag)
    df = df[["Bandeira"] + [c for c in df.columns if c != "Bandeira"]]

    # ======== Ordena por UF ========
    df = df.sort_values(by="UF", ascending=True).reset_index(drop=True)

    # =========================
    # Salva como HTML leve e reutilizável
    # =========================
    if save_html:
        html_table = df.to_html(
            index=False, escape=False, table_id="usoSoloTable", classes="display compact stripe"
        )

        html_code = f"""
<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Tabela de Uso do Solo</title>
<link rel="stylesheet" href="https://cdn.datatables.net/1.13.8/css/jquery.dataTables.min.css">
<link rel="stylesheet" href="https://cdn.datatables.net/buttons/2.4.2/css/buttons.dataTables.min.css">
<link rel="stylesheet" href="https://cdn.datatables.net/searchpanes/2.2.0/css/searchPanes.dataTables.min.css">
<link rel="stylesheet" href="https://cdn.datatables.net/select/1.7.0/css/select.dataTables.min.css">
<style>
body {{
  font-family: Arial, sans-serif;
  margin: 10px;
}}
h3 {{
  font-family: Arial;
  margin-bottom: 10px;
}}
table.dataTable thead th {{
  background-color: #f5f5f5;
}}
table.dataTable,
table.dataTable th,
table.dataTable td {{
  border: none !important;
  border-collapse: collapse !important;
}}
table.dataTable.stripe tbody tr.odd,
table.dataTable.display tbody tr.odd {{
  background-color: #fafafa;
}}
table.dataTable td {{
  padding: 6px 8px !important;
}}
</style>
</head>
<body>
<h3>Uso do Solo por Estação e Poluente</h3>
{html_table}
<script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>
<script src="https://cdn.datatables.net/1.13.8/js/jquery.dataTables.min.js"></script>
<script src="https://cdn.datatables.net/buttons/2.4.2/js/dataTables.buttons.min.js"></script>
<script src="https://cdn.datatables.net/buttons/2.4.2/js/buttons.html5.min.js"></script>
<script src="https://cdn.datatables.net/searchpanes/2.2.0/js/dataTables.searchPanes.min.js"></script>
<script src="https://cdn.datatables.net/select/1.7.0/js/dataTables.select.min.js"></script>
<script>
$(document).ready(function() {{
  $('#usoSoloTable').DataTable({{
    pageLength: 25,
    dom: 'PlBfrtip',
    buttons: ['copyHtml5', 'csvHtml5', 'excelHtml5'],
    searchPanes: {{
        layout: 'columns-3',
        cascadePanes: true
    }},
    columnDefs: [
        {{ searchPanes: {{ show: true }}, targets: [1,2,3] }},
        {{ searchPanes: {{ show: false }}, targets: '_all' }}
    ]
  }});
}});
</script>
</body>
</html>
"""
        html_path.write_text(html_code, encoding="utf-8")

    if open_in_notebook:
        from IPython.display import HTML
        return df, HTML(html_code)
    else:
        return df, html_path
