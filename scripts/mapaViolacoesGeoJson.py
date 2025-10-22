# -*- coding: utf-8 -*-
"""
Exporta violações da CONAMA 506/2024 em GeoJSONs individuais por (padrão, poluente, ano)
Compatível com o formato mais recente (coluna ID_MMA_COMPLETO no Monitoramento_QAr_BR.csv)
"""

import os
import pandas as pd
import geopandas as gpd
import numpy as np
from pathlib import Path

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

    # Remove entradas inválidas
    fases = fases[
        (~fases["phase"].isin(["", "NAN", "NONE", "NULL", "E"])) &
        (~fases["pollutant"].isin(["", "NAN", "NONE", "NULL"]))
    ]

    # Mantém apenas poluentes e padrões válidos
    poluentes_validos = ["CO", "SO2", "NO2", "O3", "MP10", "MP25", "PTS"]
    fases = fases[fases["pollutant"].isin(poluentes_validos)]

    padroes_validos = ["PI-1", "PI-2", "PI-3", "PI-4", "PF"]
    fases = fases[fases["phase"].isin(padroes_validos)]

    ordem_padroes = padroes_validos
    padroes = sorted(fases["phase"].unique(), key=lambda x: ordem_padroes.index(x))
    poluentes = [p for p in poluentes_validos if p in fases["pollutant"].unique()]

    meta = meta[meta["POLUENTE"].isin(poluentes)]

    # =======================
    # Funções auxiliares
    # =======================
    def media_geometrica(x):
        x = pd.to_numeric(x, errors="coerce").dropna()
        x = x[x > 0]
        if len(x) == 0:
            return np.nan
        return float(np.exp(np.mean(np.log(x))))

    def calcular_metricas(df, ave_time: str, pol: str):
        if "DATA" not in df.columns:
            poss = [c for c in df.columns if "DATA" in c.upper() or "DATE" in c.upper()]
            if poss:
                df = df.rename(columns={poss[0]: "DATA"})
            else:
                return None

        df["DATA"] = pd.to_datetime(df["DATA"], errors="coerce")
        df = df.dropna(subset=["DATA", "VALOR"]).sort_values("DATA")
        if df.empty:
            return None

        at = str(ave_time).strip().lower()
        if at == "24":
            df["DATA_DIA"] = df["DATA"].dt.floor("D")
            df24 = df.groupby("DATA_DIA", as_index=False)["VALOR"].mean()
            df24 = df24.rename(columns={"VALOR": "VALOR_METRICA"})
            return df24
        if at == "1":
            df["DATA_DIA"] = df["DATA"].dt.floor("D")
            df1 = df.groupby("DATA_DIA", as_index=False)["VALOR"].max()
            df1 = df1.rename(columns={"VALOR": "VALOR_METRICA"})
            return df1
        if at == "8":
            df = df.set_index("DATA").sort_index()
            df["mm8h"] = df["VALOR"].rolling(window=8, min_periods=6).mean()
            df = df.reset_index()
            df["DATA_DIA"] = df["DATA"].dt.floor("D")
            df8 = df.groupby("DATA_DIA", as_index=False)["mm8h"].max()
            df8 = df8.rename(columns={"mm8h": "VALOR_METRICA"})
            return df8
        if at == "anual":
            df["ANO"] = df["DATA"].dt.year
            if pol == "PTS":
                dfy = df.groupby("ANO", as_index=False).agg(VALOR_METRICA=("VALOR", media_geometrica))
            else:
                dfy = df.groupby("ANO", as_index=False)["VALOR"].mean().rename(columns={"VALOR": "VALOR_METRICA"})
            return dfy
        return None

    # =======================
    # Cálculo de violações
    # =======================
    registros = []

    for pol in poluentes:
        ave_times_pol = fases.loc[fases["pollutant"] == pol, "ave_time"].astype(str).str.lower().unique()
        for ave_folder in ave_times_pol:
            pasta = averages_dir / ave_folder / pol
            if not pasta.exists():
                continue
            fases_filt = fases[
                (fases["pollutant"] == pol) &
                (fases["ave_time"].astype(str).str.lower() == ave_folder)
            ]
            if fases_filt.empty:
                continue

            for arq in pasta.glob("*.csv"):
                try:
                    df = pd.read_csv(arq)
                except Exception:
                    continue
                if "VALOR" not in df.columns:
                    continue

                df_calc = calcular_metricas(df, ave_folder, pol)
                if df_calc is None or df_calc.empty:
                    continue

                est_id = arq.stem
                if "DATA_DIA" in df_calc.columns:
                    df_calc["ANO"] = pd.to_datetime(df_calc["DATA_DIA"]).dt.year

                for _, fase in fases_filt.iterrows():
                    lim = None
                    for col in ["y1", "y0", "y1_val"]:
                        if col in fase and pd.notna(fase[col]):
                            try:
                                lim = float(str(fase[col]).replace(",", "."))
                                break
                            except Exception:
                                continue
                    if lim is None:
                        continue

                    for ano, grp in df_calc.groupby("ANO"):
                        total = len(grp)
                        viol = int((grp["VALOR_METRICA"] > lim).sum())
                        pct = round((viol / total) * 100, 2) if total else 0.0

                        registros.append({
                            "ID_MMA_COMPLETO": est_id,
                            "POLUENTE": pol,
                            "ANO": int(ano),
                            "PADRAO": fase["phase"],
                            "LIMITE": lim,
                            "VIOLACOES": viol,
                            "PCT_EXC": pct,
                            "TIPO_MEDIA": ave_folder
                        })

    df_viol = pd.DataFrame(registros)
    df_viol = df_viol[df_viol["ANO"] != 2025]
    df_viol.to_csv(csv_violacoes, index=False)
    print(f"📈 Registros de violações: {len(df_viol)}")

    if df_viol.empty:
        raise RuntimeError("❌ Nenhum dado de violação foi calculado.")

    # =======================
    # GeoJoin e exportação (ID_MMA_COMPLETO direto)
    # =======================
    print("🔍 Fazendo correspondência direta via ID_MMA_COMPLETO...")

    meta_coords = meta.drop_duplicates("ID_MMA_COMPLETO")[["ID_MMA_COMPLETO", "LATITUDE", "LONGITUDE", "POLUENTE", "ID_OEMA"]].copy()
    meta_coords["LATITUDE"] = meta_coords["LATITUDE"].astype(str).str.replace(",", ".", regex=False)
    meta_coords["LONGITUDE"] = meta_coords["LONGITUDE"].astype(str).str.replace(",", ".", regex=False)
    meta_coords["LATITUDE"] = pd.to_numeric(meta_coords["LATITUDE"], errors="coerce")
    meta_coords["LONGITUDE"] = pd.to_numeric(meta_coords["LONGITUDE"], errors="coerce")
    meta_coords = meta_coords.dropna(subset=["LATITUDE", "LONGITUDE"]).reset_index(drop=True)

    # Merge direto por ID_MMA_COMPLETO e POLUENTE
    gdf_merge = df_viol.merge(meta_coords, on=["ID_MMA_COMPLETO", "POLUENTE"], how="left")

    # Remove sem coordenadas
    gdf_merge = gdf_merge.dropna(subset=["LATITUDE", "LONGITUDE"])
    gdf_merged = gpd.GeoDataFrame(
        gdf_merge,
        geometry=gpd.points_from_xy(gdf_merge["LONGITUDE"], gdf_merge["LATITUDE"]),
        crs="EPSG:4326"
    )

    print(f"🌎 {len(gdf_merged)} registros georreferenciados prontos para exportação.")
    print(f"⚠️ {df_viol.shape[0] - len(gdf_merged)} registros sem correspondência.")

    # =======================
    # Exportação final
    # =======================
    for padrao in padroes:
        dir_p = static_dir / padrao
        dir_p.mkdir(exist_ok=True)
        subset_p = gdf_merged[gdf_merged["PADRAO"] == padrao]
        if subset_p.empty:
            continue
        for pol in subset_p["POLUENTE"].unique():
            for ano in subset_p["ANO"].unique():
                sub = subset_p[(subset_p["POLUENTE"] == pol) & (subset_p["ANO"] == ano)]
                if sub.empty:
                    continue
                out_path = dir_p / f"{pol}_{ano}.geojson"
                sub.to_file(out_path, driver="GeoJSON")
                print(f"✅ {out_path}")

    print("🏁 Exportação concluída com sucesso.")


if __name__ == "__main__":
    mapa_violacoes_geojson()
