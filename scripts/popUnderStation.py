# -*- coding: utf-8 -*-
"""
Calcula população atendida por estação usando REP_ESPACIAL como raio de buffer.
Entrada:
  - setores censitários consolidados com POP2022
  - pontos das estações contendo coluna REP_ESPACIAL (em metros)
Saída:
  - CSV com ID, POP_BUFFER, REP_ESPACIAL
"""

import geopandas as gpd
import pandas as pd
from pathlib import Path
import os

# ========================
# Configurações
# ========================
rootPath   = Path(os.path.dirname(os.getcwd()))
SET_DIR    = rootPath / "data/setores_censitarios"
OUTPUT_DIR = rootPath / "data/outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SETOR_PATH    = SET_DIR / "BR_setores_pop2022.gpkg"
STATIONS_PATH = OUTPUT_DIR / "stations_with_rep.gpkg"  # pontos de estação com coluna REP_ESPACIAL
OUT_CSV       = OUTPUT_DIR / "populacao_rep.csv"

# ========================
# Função principal
# ========================
def popUnderStation_rep(
    setor_path=SETOR_PATH,
    stations_path=STATIONS_PATH,
    pop_col="POP2022",
    output_csv=OUT_CSV
):
    setores = gpd.read_file(setor_path).to_crs(5880)
    stations = gpd.read_file(stations_path).to_crs(5880)

    if "REP_ESPACIAL" not in stations.columns:
        raise ValueError("O arquivo de estações não contém a coluna REP_ESPACIAL")

    # Gera buffers com base no REP_ESPACIAL
    stations["geometry"] = stations.buffer(stations["REP_ESPACIAL"])
    buffers = stations[["ID", "REP_ESPACIAL", "geometry"]]

    # Interseção setores × buffers
    inter = gpd.overlay(setores, buffers, how="intersection")

    # Área dos setores (para ponderar)
    setores["AREA_SETOR"] = setores.geometry.area
    area_total_setor = setores.set_index("CD_SETOR")["AREA_SETOR"]

    # Fração de cada setor dentro do buffer
    inter["frac_area"] = inter.geometry.area / inter["CD_SETOR"].map(area_total_setor)
    inter["pop_frac"]  = inter[pop_col] * inter["frac_area"]

    # Soma população por estação
    pop_por_buffer = (inter.groupby("ID")["pop_frac"]
                             .sum()
                             .reset_index()
                             .rename(columns={"pop_frac": "POP_BUFFER"}))

    # Junta o REP_ESPACIAL de volta
    pop_por_buffer = pop_por_buffer.merge(stations[["ID", "REP_ESPACIAL"]], on="ID", how="left")

    # Salva
    pop_por_buffer.to_csv(output_csv, index=False, encoding="utf-8")
    print(f"✅ População atendida calculada com REP_ESPACIAL salva em {output_csv}")

    return pop_por_buffer

# ========================
# Execução direta
# ========================
if __name__ == "__main__":
    popUnderStation_rep()
