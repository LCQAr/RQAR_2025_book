# -*- coding: utf-8 -*-
"""
Created on Fri Oct 31 15:49:24 2025
@author: cb_am
"""

import os
import base64
import pandas as pd
from pathlib import Path

def stations_trend_table_interactive(
    csv_name: str = "stations_trend.csv",
    save_html: bool = True,
    html_name: str = "tabela_tendencias.html",
    open_in_notebook: bool = True,
):

    # ===== Caminhos =====
    rootPath = Path(__file__).resolve().parent.parent
    csv_path = rootPath / "data" / "outputs" / csv_name
    static_html_dir = rootPath / "_static" / "tendencias"
    flags_dir = rootPath / "_static" / "bandeiras"

    static_html_dir.mkdir(parents=True, exist_ok=True)
    html_path = static_html_dir / html_name

    # ===== Lê CSV =====
    if not csv_path.exists():
        raise FileNotFoundError(f"❌ Arquivo não encontrado: {csv_path}")
    df = pd.read_csv(csv_path)

    # ===== Colunas obrigatórias =====
    colunas_base = ["UF", "ID_OEMA"]
    if not all(col in df.columns for col in colunas_base):
        raise ValueError("❌ O CSV deve conter as colunas 'UF' e 'ID_OEMA'.")

    # ===== Bandeiras em base64 =====
    def embed_flag(uf):
        img_path = flags_dir / f"{uf}.png"
        if img_path.exists():
            with open(img_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
                return f'<img src="data:image/png;base64,{b64}" width="25">'
        else:
            return ""

    df["Bandeira"] = df["UF"].apply(embed_flag)
    df.insert(0, "Bandeira", df.pop("Bandeira"))

    # ===== Ordena por UF =====
    df = df.sort_values(by="UF").reset_index(drop=True)

    # ===== Gera HTML =====
    html_code = ""
    if save_html:
        html_table = df.to_html(
            index=False,
            escape=False,
            table_id="trendTable",
            classes="display compact stripe"
        )

        html_code = f"""
<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Tabela de Tendências das Estações</title>
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
<h3>Tendências por Estado e Estação</h3>
{html_table}
<script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>
<script src="https://cdn.datatables.net/1.13.8/js/jquery.dataTables.min.js"></script>
<script src="https://cdn.datatables.net/buttons/2.4.2/js/dataTables.buttons.min.js"></script>
<script src="https://cdn.datatables.net/buttons/2.4.2/js/buttons.html5.min.js"></script>
<script src="https://cdn.datatables.net/searchpanes/2.2.0/js/dataTables.searchPanes.min.js"></script>
<script src="https://cdn.datatables.net/select/1.7.0/js/dataTables.select.min.js"></script>
<script>
$(document).ready(function() {{
  $('#trendTable').DataTable({{
    pageLength: 25,
    dom: 'PlBfrtip',
    buttons: ['copyHtml5', 'csvHtml5', 'excelHtml5'],
    searchPanes: {{
        layout: 'columns-2',
        cascadePanes: true
    }},
    columnDefs: [
        {{ searchPanes: {{ show: true }}, targets: [1,2] }},
        {{ searchPanes: {{ show: false }}, targets: '_all' }}
    ]
  }});
}});
</script>
</body>
</html>
"""
        html_path.write_text(html_code, encoding="utf-8")

    # ===== Retorna resultado =====
    if open_in_notebook:
        from IPython.display import HTML
        return df, HTML(html_code)
    else:
        return df, html_path