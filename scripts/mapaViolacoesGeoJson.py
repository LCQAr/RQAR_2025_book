# -*- coding: utf-8 -*-
"""
Exporta violações da CONAMA 506/2024 em GeoJSONs individuais por (padrão, poluente, ano)
Versão final — apenas médias 1h, 8h e 24h, com correção de limites textuais (ex: "25 µg/m³")
Autor: Robson Will
"""

import os
import pandas as pd
import geopandas as gpd
import numpy as np
from pathlib import Path
import re

def mapa_violacoes_geojson(rootPath=None):
    print("🚀 Gerando GeoJSONs de violações...")

    # =======================
    # Caminhos principais
    # =======================
    rootPath = Path(rootPath or os.path.dirname(os.getcwd()))
    data_dir = rootPath / "data"
    averages_dir = data_dir / "MQAr_averages"
    meta_csv = data_dir / "Monitoramento_QAr_BR.csv"
    fases_csv = data_dir / "fases_CONAMA506.csv"
    output_dir = data_dir / "outputs"
    output_dir.mkdir(exist_ok=True)
    csv_violacoes = output_dir / "violacoes_estacoes.csv"

    static_dir = rootPath / "_static" / "mapas" / "violacoes"
    static_dir.mkdir(parents=True, exist_ok=True)

    # =======================
    # Leitura de metadados
    # =======================
    meta = pd.read_csv(meta_csv)
    fases = pd.read_csv(fases_csv)

    fases["pollutant"] = fases["pollutant"].astype(str).str.strip().str.upper()
    fases["phase"] = fases["phase"].astype(str).str.strip().str.upper()
    fases = fases[
        (~fases["phase"].isin(["", "NAN", "NONE", "NULL", "E"])) &
        (~fases["pollutant"].isin(["", "NAN", "NONE", "NULL"]))
    ]

    poluentes_validos = ["CO", "SO2", "NO2", "O3", "MP10", "MP25", "PTS"]
    fases = fases[fases["pollutant"].isin(poluentes_validos)]
    padroes_validos = ["PI-1", "PI-2", "PI-3", "PI-4", "PF"]
    fases = fases[fases["phase"].isin(padroes_validos)]

    ordem_padroes = padroes_validos
    padroes = sorted(fases["phase"].unique(), key=lambda x: ordem_padroes.index(x))
    poluentes = [p for p in poluentes_validos if p in fases["pollutant"].unique()]
    meta = meta[meta["POLUENTE"].isin(poluentes)]

    # =======================
    # Cálculo de violações — apenas médias 1h, 8h e 24h
    # =======================
    registros = []
    medias_validas = ["1", "8", "24"]

    for pol in poluentes:
        fases_pol = fases.loc[fases["pollutant"] == pol]
        ave_times_pol = fases_pol["ave_time"].astype(str).str.lower().unique()

        for ave_folder in ave_times_pol:
            # ignora médias anuais e outras
            if not any(x in ave_folder for x in medias_validas):
                continue  

            pasta = averages_dir / ave_folder.replace("h", "") / pol
            if not pasta.exists():
                continue

            print(f"📊 Processando {pol} ({ave_folder}h)...")

            fases_filt = fases_pol[fases_pol["ave_time"].astype(str).str.lower() == ave_folder]
            if fases_filt.empty:
                continue

            for arq in pasta.glob("*.csv"):
                try:
                    df = pd.read_csv(arq)
                except Exception as e:
                    print(f"⚠️ Erro ao ler {arq.name}: {e}")
                    continue

                # Detecta colunas de valor e data
                col_valor = next((c for c in df.columns if "valor" in c.lower()), None)
                col_data = next((c for c in df.columns if "data" in c.lower() or "date" in c.lower()), None)
                if not col_valor:
                    print(f"⚠️ Coluna de valor não encontrada em {arq.name}")
                    continue

                # Determina o ano
                if "ANO" in df.columns:
                    df["ANO"] = pd.to_numeric(df["ANO"], errors="coerce")
                elif col_data:
                    df["ANO"] = pd.to_datetime(df[col_data], errors="coerce").dt.year
                else:
                    continue

                if df["ANO"].isna().all():
                    continue

                df = df.rename(columns={col_valor: "VALOR"})
                est_id = arq.stem

                # Loop por fase (PI-1, PI-2, … PF)
                for _, fase in fases_filt.iterrows():
                    # Extrai limite numérico com regex, ignorando símbolos
                    lim = None
                    for col in ["y1", "y0", "y1_val"]:
                        if col in fase and pd.notna(fase[col]):
                            val_str = str(fase[col]).replace(",", ".")
                            val_num = re.findall(r"[-+]?\d*\.?\d+", val_str)
                            if val_num:
                                lim = float(val_num[0])
                                break
                    if lim is None:
                        print(f"⚠️ Limite não numérico para {pol} / {fase['phase']}")
                        continue

                    # Loop por ano dentro da estação
                    for ano, grp in df.groupby("ANO"):
                        grp = grp.dropna(subset=["VALOR"])
                        total_validos = len(grp)
                        if total_validos == 0:
                            continue

                        viol = int((grp["VALOR"] > lim).sum())
                        pct = np.nan if total_validos < 20 else round((viol / total_validos) * 100, 2)

                        registros.append({
                            "ID_MMA_COMPLETO": est_id,
                            "POLUENTE": pol,
                            "ANO": int(ano),
                            "PADRAO": fase["phase"],
                            "TIPO_MEDIA": ave_folder,
                            "LIMITE": lim,
                            "N_VALIDOS": total_validos,
                            "VIOLACOES": viol,
                            "PCT_EXC": pct
                        })

    # =======================
    # Finalização e validação
    # =======================
    if not registros:
        print("⚠️ Nenhum registro válido encontrado — verifique se as pastas 1, 8 ou 24 contêm arquivos com colunas de data e valor.")
        return

    df_viol = pd.DataFrame(registros)
    df_viol = df_viol.dropna(subset=["ANO"])
    df_viol = df_viol[df_viol["ANO"] != 2025]
    df_viol.to_csv(csv_violacoes, index=False)
    print(f"📈 Registros de violações salvos: {len(df_viol)}")

    # =======================
    # GeoJoin e exportação
    # =======================
    meta_coords = meta.drop_duplicates("ID_MMA_COMPLETO")[["ID_MMA_COMPLETO", "LATITUDE", "LONGITUDE", "POLUENTE", "ID_OEMA"]].copy()
    meta_coords["LATITUDE"] = pd.to_numeric(meta_coords["LATITUDE"].astype(str).str.replace(",", "."), errors="coerce")
    meta_coords["LONGITUDE"] = pd.to_numeric(meta_coords["LONGITUDE"].astype(str).str.replace(",", "."), errors="coerce")
    meta_coords = meta_coords.dropna(subset=["LATITUDE", "LONGITUDE"])

    gdf_merge = df_viol.merge(meta_coords, on=["ID_MMA_COMPLETO", "POLUENTE"], how="left").dropna(subset=["LATITUDE", "LONGITUDE"])
    gdf_merged = gpd.GeoDataFrame(
        gdf_merge,
        geometry=gpd.points_from_xy(gdf_merge["LONGITUDE"], gdf_merge["LATITUDE"]),
        crs="EPSG:4326"
    )

    print(f"🌎 {len(gdf_merged)} registros georreferenciados prontos para exportação.")

    # Exporta GeoJSONs por padrão/poluente/ano
    for padrao in padroes:
        dir_p = static_dir / padrao
        dir_p.mkdir(exist_ok=True)
        subset_p = gdf_merged[gdf_merged["PADRAO"] == padrao]
        if subset_p.empty:
            continue
        for pol in subset_p["POLUENTE"].unique():
            subset_pol = subset_p[subset_p["POLUENTE"] == pol]
            for ano in subset_pol["ANO"].unique():
                sub = subset_pol[subset_pol["ANO"] == ano]
                if sub.empty:
                    continue
                out_path = dir_p / f"{pol}_{ano}.geojson"
                sub.to_file(out_path, driver="GeoJSON")
                print(f"✅ Exportado: {out_path}")

    print("🏁 Exportação concluída com sucesso.")


if __name__ == "__main__":
    mapa_violacoes_geojson()
