##!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Aug 14 13:48:06 2025

@author: lcqar
"""

#%% Imports

import pandas as pd
import os
import numpy as np

os.chdir('/home/nobre/Notebooks/RQAR_2025_book/')

df_rep_temporal = pd.DataFrame({
    'POLUENTES': ['MP10','MP25','SO2','NO2','O3','FMC','CO','PTS','Pb'],
    'DIA': ['24','24','24','1','8','24','8','24',''],
    'MES': ['mensal','mensal','mensal','mensal','mensal','mensal','mensal','mensal_geom','mensal'],
    'ANO': ['anual','anual','anual','anual','anual','anual','anual','anual_geom','anual']
}).set_index("POLUENTES")

def rep_temp(df,agrupamento,criterio,periodo_ref):

    resultados = []
    
    for chave, dados in df.groupby(agrupamento):
        qntd_valor = dados['VALOR'].notna().sum()  

        if criterio == 'HORA':
            qntd_tempo = 24
        elif criterio == 'DIA':
            if chave[1] in [4,6,9,11]:
                qntd_tempo = 30
            elif chave[1] in [1,3,5,7,8,10,12]:
                qntd_tempo = 31
            else:
                if (chave[0] % 4 == 0 and chave[0] % 100 != 0) or (chave[0] % 400 == 0):
                    qntd_tempo = 29
                else:
                    qntd_tempo = 28
        
        if qntd_valor >= (2/3) * qntd_tempo:
            if periodo_ref == "8horas":
                media = dados["VALOR"].rolling(window=8, min_periods=1).mean().max()
            else:
                media = periodo_ref(dados["VALOR"])
            rep = True
        else:
            media = np.nan   
            rep = False

        prcnt = 100*qntd_valor/qntd_tempo

        resultados.append((*chave, media, rep, prcnt))

    return resultados

def conta_dias_quadrimestre(ano,quadrimestre):

    if quadrimestre == 1:
        if (ano % 4 == 0 and ano % 100 != 0) or (ano % 400 == 0):
            dias = 121
        else:
            dias = 120
    elif quadrimestre == 2:
        dias = 123
    else:
        dias = 122

    return dias

def rep_temp_ano(df,agrupamento,criterio):

    resultados = []
    
    for chave, dados in df.groupby(agrupamento):
        qntd_valor = dados['VALOR'].notna().sum()
        qntd_tempo = conta_dias_quadrimestre(chave[0],chave[1])         
        
        if qntd_valor >= (1/2) * qntd_tempo:
            rep = True
        else:
            rep = False
    
        resultados.append((*chave, rep))

    return resultados

df_estacoes_rep_temporal = pd.DataFrame({
                    'ID_MMA_COMPLETO':[],
                    'PRCNT_REP_TEMPORAL_DIARIA':[],
                    'PRCNT_REP_TEMPORAL_MENSAL':[],
                    'PRCNT_REP_TEMPORAL_ANUAL':[]
                })		
                
for pol in df_rep_temporal.index:
    
    path = os.getcwd()+'/data/MQAr/' + pol + '/'

    print(pol)
    
    if os.path.isdir(path) and os.listdir(path):
        
        arquivos = os.listdir(path)
    
        for estacao in arquivos:

            if estacao.endswith('.csv'):

                print(estacao)

                df = pd.read_csv(path+estacao)

                df["VALOR"] = pd.to_numeric(df["VALOR"], errors="coerce")

                resultados_24 = rep_temp(df,['ANO','MES','DIA'],'HORA',np.mean)

                df_24 = pd.DataFrame(resultados_24, columns=['ANO', 'MES', 'DIA', 'VALOR', 'REP_DIA','PRCNT_HORAS_DIA_REP_TEMPORAL'])

                df_24['DATETIME'] = pd.to_datetime(
                        dict(year=df_24["ANO"], month=df_24["MES"], day=df_24["DIA"])
                    )
            
                df_24 = df_24[['DATETIME','ANO','MES','DIA','VALOR','REP_DIA','PRCNT_HORAS_DIA_REP_TEMPORAL']]

                if df_rep_temporal['DIA'][pol] == 'dia':
                    df_dia = df_24
                elif df_rep_temporal['DIA'][pol] == '8horas':
                    resultados_dia = rep_temp(df,['ANO','MES','DIA'],'HORA','8horas')

                    df_dia = pd.DataFrame(resultados_dia, columns=['ANO', 'MES', 'DIA', 'VALOR', 'REP_DIA','PRCNT_HORAS_DIA_REP_TEMPORAL'])

                    df_dia['DATETIME'] = pd.to_datetime(dict(year=df_dia["ANO"], month=df_dia["MES"], day=df_dia["DIA"]))

                    df_dia = df_dia[['DATETIME','ANO','MES','DIA','VALOR','REP_DIA','PRCNT_HORAS_DIA_REP_TEMPORAL']]
                        
                else:
                    resultados_dia = rep_temp(df,['ANO','MES','DIA'],'HORA',np.max)

                    df_dia = pd.DataFrame(resultados_dia, columns=['ANO', 'MES', 'DIA', 'VALOR', 'REP_DIA','PRCNT_HORAS_DIA_REP_TEMPORAL'])

                    df_dia['DATETIME'] = pd.to_datetime(dict(year=df_dia["ANO"], month=df_dia["MES"], day=df_dia["DIA"]))

                    df_dia = df_dia[['DATETIME','ANO','MES','DIA','VALOR','REP_DIA','PRCNT_HORAS_DIA_REP_TEMPORAL']]

                df_dia.to_csv(os.getcwd()+'/data/MQAr_averages/'+df_rep_temporal['DIA'][pol]+'/'+pol+'/'+estacao,index=False)

                resultados_mes = rep_temp(df_24,['ANO','MES'],'DIA',np.mean)

                df_mes = pd.DataFrame(resultados_mes, columns=['ANO', 'MES', 'VALOR', 'REP_MES','PRCNT_DIAS_MES_REP_TEMPORAL'])

                df_mes['DATETIME'] = pd.to_datetime(dict(year=df_mes["ANO"], month=df_mes["MES"], day=1))
            
                df_mes = df_mes[['DATETIME','ANO','MES','VALOR','REP_MES','PRCNT_DIAS_MES_REP_TEMPORAL']]

                df_mes.to_csv(os.getcwd()+'/data/MQAr_averages/'+df_rep_temporal['MES'][pol][:6]+'/'+pol+'/'+estacao,index=False)

                df_mes_ano = df_mes.pivot(index='ANO', columns='MES', values='PRCNT_DIAS_MES_REP_TEMPORAL')

                df_mes_ano = df_mes_ano.reindex(sorted(df_mes_ano.columns), axis=1)
                
                df_mes_ano = df_mes_ano.reset_index()
                
                df_mes_ano.to_csv(os.getcwd()+'/data/MQAr_averages/rep_temporal_mes_ano/'+pol+'/'+estacao,index=False)

                condicoes = [
                    (df_dia['MES'] <= 4),
                    (df_dia['MES'] >= 5) & (df_dia['MES'] <= 8),
                    (df_dia['MES'] >= 9)
                ]
                
                quadrimestre = [1, 2, 3]
                
                df_dia['QUADRIMESTRE'] = np.select(condicoes, quadrimestre)

                resultados_quad = rep_temp_ano(df_dia,['ANO','QUADRIMESTRE'],'QUADRIMESTRE')

                df_quad = pd.DataFrame(resultados_quad, columns=['ANO', 'QUADRIMESTRE', 'REP_QUAD'])
                
                df_ano_quad = df_quad.groupby("ANO", as_index=False).agg({"REP_QUAD": lambda x: x.sum() == 3})

                resultados = []
                
                for ano, dados in df_dia.groupby(['ANO']):
                    qntd_valor = dados['VALOR'].notna().sum()
                    if (ano[0] % 4 == 0 and ano[0] % 100 != 0) or (ano[0] % 400 == 0):
                        dias = 366
                    else:
                        dias = 365
                    prcnt_rep_dias = (100*qntd_valor/dias)

                    qntd_meses = df_mes.groupby(['ANO']).get_group(ano[0])['VALOR'].notna().sum()
                    prcnt_rep_meses = (100*qntd_meses/12)
                    
                    if df_ano_quad.loc[df_ano_quad["ANO"] == ano[0], "REP_QUAD"].values[0] == True:
                        media = dados['VALOR'].mean()
                        rep = True
                    else:
                        media = np.nan
                        rep = False
                    resultados.append((*ano, media, rep, prcnt_rep_dias, prcnt_rep_meses))
                
                df_ano = pd.DataFrame(resultados, columns=['ANO', 'VALOR','REP_TEMPORAL_ANUAL','PRCNT_DIAS_ANO_REP_TEMPORAL','PRCNT_MESES_ANO_REP_TEMPORAL'])
                
                df_ano['DATETIME'] = pd.to_datetime(dict(year=df_ano["ANO"], month=1, day=1))
            
                df_ano = df_ano[['DATETIME','ANO','VALOR','REP_TEMPORAL_ANUAL','PRCNT_DIAS_ANO_REP_TEMPORAL','PRCNT_MESES_ANO_REP_TEMPORAL']]

                df_ano.to_csv(os.getcwd()+'/data/MQAr_averages/'+df_rep_temporal['ANO'][pol][:5]+'/'+pol+'/'+estacao, index=False)

                prcnt_dia = 100 * df_dia['VALOR'].notna().sum() / len(df_dia)
                prcnt_mes = 100 * df_mes['VALOR'].notna().sum() / len(df_mes)
                prcnt_ano = 100 * df_ano['VALOR'].notna().sum() / len(df_ano)
                anos = df_ano['ANO'].astype(int).astype(str).str.cat(sep=',')
                df_anos_rep = df_ano.dropna(subset=['VALOR'])
                anos_representativos = df_anos_rep['ANO'].astype(int).astype(str).str.cat(sep=',')

                prcnt_estacao = {'ID_MMA_COMPLETO': estacao[:-4], 
                                 'PRCNT_REP_TEMPORAL_DIARIA': prcnt_dia, 
                                 'PRCNT_REP_TEMPORAL_MENSAL': prcnt_mes, 
                                 'PRCNT_REP_TEMPORAL_ANUAL': prcnt_ano, 
                                 'ANOS_REPRESENTATIVOS':anos_representativos,
                                 'ANOS_MONITORADOS': anos}
                
                df_estacoes_rep_temporal = pd.concat([df_estacoes_rep_temporal, pd.DataFrame([prcnt_estacao])], ignore_index=True)

                df_estacoes_rep_temporal.to_csv(os.getcwd()+'/data/MQAr_averages/REP_TEMPORAL.csv', index=False)