# -*- coding: utf-8 -*-
import pandas as pd
import os, json
from pathlib import Path

root = Path(os.path.dirname(os.getcwd()))
csv_path = root / "data" / "Monitoramento_QAr_BR.csv"
out_json = root / "_static" / "monitoramento" / "monitoramento_agrupado.json"
out_json.parent.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(csv_path)

df['UF'] = df['UF'].astype(str).str.replace(" ", "")
df.loc[df['POLUENTE']=="PM25","POLUENTE"]="MP25"

# Categorias
df['CATEGORIA'] = (
    df.get('CATEGORIA','Não declarado')
      .fillna('Não declarado')
      .astype(str).str.strip().str.capitalize()
)

fix = {
    "Referencia":"Referência", 
    "Indicativa":"Indicativa",
    "Nao declarado":"Não declarado",
    "Nao declarada":"Não declarado",
    "Não declarada":"Não declarado"
}
df['CATEGORIA'] = df['CATEGORIA'].replace(fix)
valid = ["Referência","Indicativa","Não declarado"]
df.loc[~df['CATEGORIA'].isin(valid),"CATEGORIA"]="Não declarado"

# Anos
df["ANOS_MONITORADOS"] = df["ANOS_MONITORADOS"].astype(str).str.split(",")
df = df.explode("ANOS_MONITORADOS")
df = df[pd.to_numeric(df["ANOS_MONITORADOS"], errors="coerce").notna()]
df["ANOS_MONITORADOS"] = df["ANOS_MONITORADOS"].astype(int)

# Agrupamento
df_ag = (
    df.groupby(["POLUENTE","UF","CATEGORIA","ANOS_MONITORADOS"])
      .size().reset_index(name="NSTATION")
)

# Salvar JSON organizado
rows = df_ag.to_dict(orient="records")

with open(out_json, "w", encoding="utf-8") as f:
    json.dump(rows, f, ensure_ascii=False, indent=2)

print("Arquivo salvo:", out_json)
