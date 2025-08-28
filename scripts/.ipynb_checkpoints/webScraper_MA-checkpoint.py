#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Webscraping de dados de qualidade do ar da Baía - CETREL.

Criado por Leonardo Hoinaski
"""


# ---------------------------------- Importação de pacotes ----------------------------------
import requests
import pandas as pd
from datetime import datetime, timedelta
import calendar
import os

# -------------------------
# Configurações
# -------------------------
API_URL = "https://pydjapi.azurewebsites.net/api/envni/chart/small"

DEVICES = {
    "estacao_5": {"cod":"40532F", "nome":"Anjo da Guarda"},
    "estacao_7": {"cod":"41C87F", "nome": "Vila Maranhão 240823"},
    "estacao_17": {"cod": "41C892", "nome": "BR135 Pedrinhas OUT 19_01_24 - IN30_01_24"},
    "estacao_1": {"cod": "825150", "nome": "Coqueiro IN 27_03_25"},
    "estacao_25": {"cod": "41C8AB", "nome": "Vila Sarney 06_23"},
    "estacao_35": {"cod": "41C86B", "nome": "Santa Bárbara"}
}


OUTPUT_DIR = "/home/nobre/Notebooks/RQAR_2025_book/data/MA/output_by_station_pollutant"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# -------------------------
# Função para buscar dados de uma estação por dia
# -------------------------
def fetch_data_day(device_code, date):
    """
    Faz uma requisição para a estação device_code para todo o dia 'date'.
    Retorna dicionário JSON.
    """
    dt_start = f"{date} 00:00"
    dt_end   = f"{date} 23:59"
    payload = {
        "dt_start": dt_start,
        "dt_end": dt_end,
        "device": device_code
    }
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(API_URL, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Error fetching {device_code} for {date}: {e}")
        return None

# -------------------------
# Loop por datas (ex: mês de agosto 2025)
# -------------------------
for YEAR in range(2020,2025):
    if YEAR == 2020:
        MONTHrange = range(8,13)
    else:
        MONTHrange = range(1,13)
    
    
    for MONTH in MONTHrange:      
        
        days = calendar.monthrange(YEAR, MONTH)[1]
        print(days)
        for day in range(1, days + 1):
            date_str = f"{YEAR}-{MONTH:02d}-{day:02d}"
            print(f"\n📅 Processando {date_str}")
            
            for device_key, device_info in DEVICES.items():
                print(f"📥 Baixando dados da estação {device_info['nome']} ({device_info['cod']})")
                data = fetch_data_day(device_info["cod"], date_str)
                if not data:
                    continue
                
                results = []
                for pollutant, values in data.items():
                    if not values:
                        continue  # ignora None ou lista vazia
                
                    # Garantir que values é iterável e adequado
                    if isinstance(values, list) and len(values) > 0 and isinstance(values[0], dict):
                        temp_df = pd.DataFrame(values)
                    else:
                        print(f"⚠️ Pulando poluente {pollutant}, formato inesperado: {type(values)}")
                        continue
                    
                
                    temp_df["POLUENTE"] = pollutant
                    temp_df["ESTACAO"] = device_info["nome"]
                    temp_df["COD"] = device_info["cod"]
                    results.append(temp_df)
                
                if not results:
                    continue
                
                df_all = pd.concat(results, ignore_index=True)
                df_all["DATETIME"] = pd.to_datetime(date_str + " " + df_all["hour"])
                
                # Salvar CSV por estação e poluente
                # Exemplo de dicionário para padronizar nomes de poluentes e índices
                pollutant_name_map = {
                    "avg_co": "CO",
                    "avg_no2": "NO2",
                    "avg_so2": "SO2",
                    "avg_pm100": "PTS",
                    "avg_pm10": "MP10",
                    "avg_pm25": "MP25",
                    "avg_o3": "O3",
                    "avg_uv": "UV",
                    "avg_co_iqar": "COIQAR",
                    "avg_no2_iqar": "NO2IQAR",
                    "avg_o3_iqar": "O3IQAR",
                    "avg_uv_iqar": "UVIQAR",
                    "avg_pm25_iqar": "MP25IQAR",
                    "avg_pm10_iqar": "MP10IQAR",
                    "avg_o3_index": "O3INDEX",
                    "avg_uv_index": "UVINDEX",
                    "avg_pm25_index": "MP25INDEX",
                    "avg_pm10_index": "MP10INDEX"
                }

                # Lista das colunas de poluentes (as médias)
                pollutant_cols = [
                    "avg_co", "avg_no2", "avg_so2", "avg_pm100", "avg_o3",
                    "avg_uv", "avg_pm25", "avg_pm10",
                    "avg_co_iqar", "avg_no2_iqar", "avg_o3_iqar", "avg_uv_iqar",
                    "avg_pm25_iqar", "avg_pm10_iqar"
                ]
                
                # Transformar para formato longo
                df_long = df_all.melt(
                    id_vars=["DATETIME", "ESTACAO", "COD"],  # colunas que permanecem
                    value_vars=pollutant_cols,               # colunas que viram 'POLUENTE'
                    var_name="POLUENTE",
                    value_name="CONC"
                )
                
                # Substituir nomes pelo padrão, se existir no dicionário
                df_long["POLUENTE"] = df_long["POLUENTE"].map(lambda x: pollutant_name_map.get(x, x))
        
        
                for (station, pollutant), group in df_long.groupby(["ESTACAO", "POLUENTE"]):
                    filename = f"MA_{station}_{pollutant}_{date_str}.csv".replace(" ", "_")
                    filepath = os.path.join(OUTPUT_DIR, filename)
                    group = group.drop(["POLUENTE","ESTACAO"], axis=1)
                    group.to_csv(filepath, index=False, encoding="utf-8")
                    print(f"✅ Saved: {filepath}")
