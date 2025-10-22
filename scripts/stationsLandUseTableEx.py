# -*- coding: utf-8 -*-
"""
Versão compatível com build (Jupyter Book) da tabela de uso do solo.
Gera HTML autossuficiente (com DataTables carregado via CDN).
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

    # ======== Seleciona colunas principais ========
    columnsSelector = [
        "UF", "ID_OEMA", "POLUENTE", "REP_ESPACIAL", "GRUPO_PRED_VAR",
        "Floresta_perc", "Herbácea_perc", "Agropecuária_perc",
        "Não Vegetada_perc", "Urbanizada_perc", "Mineração_perc"
    ]
    df = df[[c for c in columnsSelector if c in df.columns]].copy()

    # Renomeia colunas
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
        print("💾 Salvando tabela renderizada em _static/html (com bandeiras embutidas)...")

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
body {{ font-family: Arial, sans-serif; margin: 10px; }}
table.dataTable thead th {{ background-color: #f5f5f5; }}
</style>
</head>
<body>
<h3 style="font-family:Arial; margin-bottom:10px;">Uso do Solo por Estação e Poluente</h3>
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
        {{ searchPanes: {{ show: true }}, targets: [1,2,3] }},  // 🔹 Apenas UF, ID_OEMA e POLUENTE
        {{ searchPanes: {{ show: false }}, targets: '_all' }}   // 🔹 Desativa nas demais
    ]
  }});
}});
</script>
</body>
</html>
"""
        html_path.write_text(html_code, encoding="utf-8")
        print(f"✅ HTML salvo em: {html_path}")

        

    if open_in_notebook:
        from IPython.display import HTML
        return df, HTML(html_code)
    else:
        return df, html_path
