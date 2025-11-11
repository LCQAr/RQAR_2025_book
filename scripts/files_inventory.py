#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Sep 11 10:45:33 2024

@author: leohoinaski
"""

#-----------------------------Importação de pacotes ------------------------------------
import os 
import pandas as pd
import scripts.timeSeriesFigures as tsf
import scripts.get_elevation as getelev
import scripts
import numpy as np

# Caminho para a pasta de dados
rootPath = os.path.dirname(os.getcwd())

# Lendo o csv
aqmData = pd.read_csv(rootPath+'/data/Monitoramento_QAr_BR.csv')

# # Substitui vírgulas por pontos
# aqmData['LATITUDE'] = aqmData['LATITUDE'].str.replace(',', '.', regex=False)

# # Substitui 'x' e '-' por NaN
# aqmData['LATITUDE'] = aqmData['LATITUDE'].replace(['x', '-','Nao declarado'], np.nan)

# # Converte para float, caso ainda esteja como string
# aqmData['LATITUDE'] = aqmData['LATITUDE'].astype(float)


# # Substitui vírgulas por pontos
# aqmData['LONGITUDE'] = aqmData['LONGITUDE'].str.replace(',', '.', regex=False)

# # Substitui 'x' e '-' por NaN
# aqmData['LONGITUDE'] = aqmData['LONGITUDE'].replace(['x', '-','Nao declarado'], np.nan)

# # Converte para float, caso ainda esteja como string
# aqmData['LONGITUDE'] = aqmData['LONGITUDE'].astype(float)


col = 'ANOS_MONITORADOS'
if col not in aqmData.columns:
    aqmData[col] = ""   # string vazia como preenchimento
    

# Verifica se o arquivo com os dados existe
temDados = []
for index, row in aqmData.iterrows():
    if pd.isna(row.ID_MMA_COMPLETO) | pd.isna(row.POLUENTE): 
        temDados.append(False)
    else:
        file_path = rootPath+'/data/MQAr/'+row.POLUENTE+'/'+row.ID_MMA_COMPLETO + '.csv'
        if os.path.exists(file_path):
            print(f"'{file_path}' existe.")
            temDados.append(True)
            df = pd.read_csv(file_path)
            
            # Verifica se a coluna valor existe
            if 'VALOR' in df.columns:
                #print("Coluna VALOR existe")
                df_cleaned = df.dropna(subset=['VALOR'])
                inicio = df_cleaned.DATETIME.min()
                print(inicio)
                final = df_cleaned.DATETIME.max()
                print(final)
                if inicio == np.nan or final == np.nan:
                    temDados.append(False)
                else:
                    aqmData.loc[index,'INICIO'] = inicio
                    aqmData.loc[index,'FIM'] = final
                    fig = tsf.iterative_timeseries(df,row)
                    anos_monitorados = df.loc[df["VALOR"].notna(), "ANO"].unique()
                    anos_monitorados = sorted(anos_monitorados)
                    anos_monitorados = [item for item in anos_monitorados if not np.isnan(item)]
                    anos_monitorados = [int(x) for x in anos_monitorados]
                    aqmData.loc[index,'ANOS_MONITORADOS'] = ",".join(map(str, anos_monitorados)) 
                
            elif 'CONC' in df.columns:
                df = df.rename(columns={'CONC': 'VALOR'})
                print("Coluna VALOR criada")
                df.to_csv(rootPath+'/data/MQAr/'+row.POLUENTE+'/'+row.ID_MMA_COMPLETO + '.csv', index=False)
                df_cleaned = df.dropna(subset=['VALOR'])
                inicio = df_cleaned.DATETIME.min()
                final = df_cleaned.DATETIME.max()
                aqmData.loc[index,'INICIO'] = inicio
                aqmData.loc[index,'FIM'] = final
                fig = tsf.iterative_timeseries(df,row)
                anos_monitorados = df.loc[df["VALOR"].notna(), "ANO"].unique()
                anos_monitorados = sorted(anos_monitorados)
                anos_monitorados = [item for item in anos_monitorados if not np.isnan(item)]
                anos_monitorados = [int(x) for x in anos_monitorados]
                aqmData.loc[index,'ANOS_MONITORADOS'] = ",".join(map(str, anos_monitorados))
                
            elif 'value' in df.columns:
                df = df.rename(columns={'value': 'VALOR'})
                print("Coluna VALOR criada")
                df.to_csv(rootPath+'/data/MQAr/'+row.POLUENTE+'/'+row.ID_MMA_COMPLETO + '.csv', index=False)
                df_cleaned = df.dropna(subset=['VALOR'])
                inicio = df_cleaned.DATETIME.min()
                final = df_cleaned.DATETIME.max()
                aqmData.loc[index,'INICIO'] = inicio
                aqmData.loc[index,'FIM'] = final
                fig = tsf.iterative_timeseries(df,row)
                anos_monitoradcomos = df.loc[df["VALOR"].notna(), "ANO"].unique()
                anos_monitorados = sorted(anos_monitorados)
                anos_monitorados = [item for item in anos_monitorados if not np.isnan(item)]
                anos_monitorados = [int(x) for x in anos_monitorados]
                aqmData.loc[index,'ANOS_MONITORADOS'] = ",".join(map(str, anos_monitorados))
                
            else:
                print("Coluna VALOR NÃO existe")
                temDados.append(False)
        else:
            print(f"'{file_path}' não existe.")
            temDados.append(False)

aqmData['BASE_DADOS'] = temDados

aqmData.to_csv(rootPath+'/data/Monitoramento_QAr_BR.csv',index=False)

# Caminho para a pasta de dados
#rootPath = os.path.dirname(os.getcwd())
# Lendo o csv
#csv = pd.read_csv(rootPath+'/data/Monitoramento_QAr_BR.csv')

DirSRTM = "/home/nobre/SRTM/"
aqmData, estacoes_negativas  = getelev.getElevSRTM(DirSRTM, aqmData)
#csvEleva.to_csv(rootPath + '/data/Monitoramento_QAr_BR.csv', index=False)

aqmData.to_csv(rootPath+'/data/Monitoramento_QAr_BR.csv',index=False)





