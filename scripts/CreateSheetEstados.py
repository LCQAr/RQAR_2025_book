##!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Aug 14 13:48:06 2025

@author: lcqar
"""

#%% Imports

import pandas as pd
import os
from collections import defaultdict
from datetime import datetime, timedelta
import re
import numpy as np
from pathlib import Path

os.chdir('/home/nobre/Notebooks/RQAR_2025_book/')

#%% Função para São Paulo

def pol_to_station(df_ids):

    base_path = Path('/home/nobre/Notebooks/RQAR_2025_book/data/MQAr_teste/')

    id_to_poluentes = {}
    
    for poluente_dir in base_path.iterdir():
        if poluente_dir.is_dir():
            poluente = poluente_dir.name
    
            arquivos = [arq.stem for arq in poluente_dir.glob("*")]
    
            for id_mma in df_ids["ID_MMA"]:
                if any(str(arq).startswith(id_mma) for arq in arquivos):
                    id_to_poluentes.setdefault(id_mma, []).append(poluente)
    
    df_ids["POLUENTE"] = df_ids["ID_MMA"].map(id_to_poluentes).fillna("").apply(lambda x: ",".join(x) if isinstance(x, list) else "")
    
    return(df_ids)

def create_df_estacao(uf,df_ids):

    print(uf)
    
    df_ufs = pd.read_csv('/home/nobre/Notebooks/RQAR_2025_book/data/dicionarios/IBGE_UFS_CODIGOS.csv')
    
    cod_uf =  df_ufs.loc[df_ufs['UF'] == uf, 'CODIGOS'].values[0]

    print(cod_uf)
    
    if os.path.exists('/home/nobre/Notebooks/RQAR_2025_book/data/DADOS_ESTACOES/'+uf+'_estacoes.csv'):

        df_estacao = pd.read_csv('/home/nobre/Notebooks/RQAR_2025_book/data/DADOS_ESTACOES/'+uf+'_estacoes.csv')

        df_estacao['ID_MMA'] = df_estacao['ID_OEMA'].map(df_ids.set_index('ID_OEMA')['ID_MMA'])
    
    else:

        colunas = ['ID_OEMA', 'UF', 'ID_MMA', 'COD_UF_IBGE', 'CIDADE', 'CD_MUN',
                   'PROPRIETARIO', 'PROP_ENTIDADE', 'OPERADOR', 'OP_ENTIDADE', 'LATITUDE',
                   'LONGITUDE', 'MOBILIDADE', 'REALOCACAO', 'MARCA', 'CATEGORIA',
                   'FUNCIONAMENTO', 'METODO', 'FINALIDADE', 'REP_ESPACIAL', 'POLUENTE',
                   'INICIO', 'STATUS', 'FIM', 'CALIBRACAO', 'OBS_CALIBRACAO', 'MONITORAR',
                   'FONTE', 'OBS_GERAIS']
        
        df_estacao = pd.DataFrame(columns=colunas)

    df_ids = pol_to_station(df_ids)

    df_estacao = df_estacao.reindex(df_ids.index)

    df_estacao[["ID_MMA", "ID_OEMA", "POLUENTE"]] = df_ids[["ID_MMA", "ID_OEMA", "POLUENTE"]].values

    df_estacao.loc[:, "COD_UF_IBGE"] = cod_uf
    df_estacao.loc[:, "UF"] = uf
    
    df_estacao.to_csv('/home/nobre/Notebooks/RQAR_2025_book/data/DADOS_ESTACOES/'+uf+'_estacoes_teste.csv', index=False)
    
def ug_to_ppm(df):

    df.loc[df["UNIDADE"] != "ppm", "VALOR"] *= 868.26/10**6

    df['UNIDADE'] = "ppm"

    return df

def ajustar_data_hora(d, h):
    if h == '24:00':
        # converte para meia-noite do dia seguinte
        return datetime.strptime(d, '%d/%m/%Y') + timedelta(days=1)
    else:
        return datetime.strptime(d + ' ' + h, '%d/%m/%Y %H:%M')

def parse_valor(x):
    x = str(x).strip()
    if ',' in x:  # caso brasileiro
        x = x.replace('.', '')      # remove separador de milhar
        x = x.replace(',', '.')     # troca vírgula por ponto decimal
    return float(x)

def rectify_SP(path):
    
    path = path + 'dados_coletados/'
    
    estacoes_SP = pd.read_excel('/home/nobre/Notebooks/RQAR_2025_book/data/DADOS_BRUTOS/SP/lista_estacoes_SP.xlsx')
    
    dict_pols_stat = defaultdict(list)
    
    files = os.listdir(path)
    
    lista=[]
    
    for item in files:
        
        arquivos = os.listdir(path+item)
        
        for arquivo in arquivos:

            partes = arquivo.split('_')
            estacao = partes[0]
            cod_estacao = partes[-2]
            
            cod_estacao = cod_estacao
            
            cod_estacao = 'SP' + cod_estacao.zfill(4)
            
            df = pd.read_csv(path+item+'/'+arquivo)
            
            poluentes = df['pol_name'].unique()
    
            for pol in poluentes:
                
                df_pol = df[df['pol_name'] == pol]
                
                pol = pol.split(' (')[0]
                
                if pol == 'NOx':
                    pol = 'NOX'
                
                if pol in tabela_pols['POLUENTE'].values:
                
                    i_ou_r = 'R'
                    
                    s_ou_a = 'A'
                    
                    cod_poluente = int(tabela_pols.loc[tabela_pols['POLUENTE'] == pol, 'COD_POLUENTE'].values[0])
                   
                    cod_poluente = f"{cod_poluente:03d}"
                    
                    nome_pasta = tabela_pols.loc[tabela_pols['COD_POLUENTE'] == int(cod_poluente), 'NOME_PASTA'].values[0]
                    
                    df_pol["DATETIME"] = df_pol["day"] + " " + df_pol["hour"]
                    
                    mask = df_pol["DATETIME"].str.contains("24:00")
                    df_pol.loc[mask, "DATETIME"] = (
                        pd.to_datetime(df_pol.loc[mask, "day"], format="%d/%m/%Y") + pd.Timedelta(days=1)
                    ).dt.strftime("%d/%m/%Y 00:00")
                    
                    
                    df_pol["DATETIME"] = pd.to_datetime(df_pol["DATETIME"], format="%d/%m/%Y %H:%M")    
                    
                    df_pol=df_pol.set_index('DATETIME')
                    
                    lista_horas = pd.date_range(
                        start=df_pol.index.min(), 
                        end=df_pol.index.max(), 
                        freq='H').strftime('%Y-%m-%d %H:%M:%S').tolist()
                    
                    if len(lista_horas) != len(df_pol):
                        df_pol = df_pol.reindex(pd.DatetimeIndex(lista_horas))
                    
                    df_pol['DATETIME'] = df_pol.index
                    
                    cols = ["DATETIME"] + [c for c in df_pol.columns if c != "DATETIME"]
                    df_pol = df_pol[cols]
                    
                    df_pol.index = df_pol['DATETIME']
                    
                    df_pol.insert(1, 'ANO', df_pol.index.year)
                    df_pol.insert(2, 'MES', df_pol.index.month)
                    df_pol.insert(3, 'DIA', df_pol.index.day)
                    df_pol.insert(4, 'HORA', df_pol.index.hour)
                            
                    df_pol = df_pol.drop(columns=["day", "hour", "name", "pol_name", "param_code", "param_name", "aqs_code", "aqs_name"])
                    
                    df_pol = df_pol.rename(columns={"units": "UNIDADE", 'val': 'VALOR'})
                    
                    df_pol['QAQC_INTERNO'] = None
                    
                    cols = list(df_pol.columns)
    
                    cols = cols[:-2] + cols[-2:][::-1]
                    
                    df_pol = df_pol[cols]
                    
                    df_pol.to_csv('/home/nobre/Notebooks/RQAR_2025_book/data/MQAr_teste/'+nome_pasta+'/'+cod_estacao+i_ou_r+s_ou_a+cod_poluente+'.csv', index=False)
                
                else:
                    
                    lista.append(pol)
                    
                    print(pol)

    df_ids = estacoes_SP
    
    return df_ids
    
    
#%% Função para Rio de Janeiro

def rectify_RJ(path):

    stations_dict_automaticas = {
        12: "RJ - Largo do Bodegão",
        18: "BR - São Bernardo",
        19: "NI - Monteiro Lobato",
        20: "RJ - Campo dos Afonsos",
        21: "RJ - Taquara",
        22: "RJ - Centro",
        23: "RJ - Engenhão",
        24: "RJ - Gericinó",
        25: "RJ - Lagoa",
        26: "RJ - Lourenço Jorge",
        27: "SG - UERJ",
        28: "NI - Meteorológica Cerâmica",
        29: "RJ - Manguinhos",
        30: "DC - Campos Elíseos",
        31: "DC - Jardim Primavera",
        32: "DC - São Bento",
        33: "DC - Vila São Luiz",
        34: "DC - Pilar",
        35: "DC - Meteorológica Jardim Piratininga",
        36: "RJ - Ilha de Paquetá",
        37: "RJ - Ilha do Governador",
        38: "Itb - Porto das Caixas",
        39: "Itb - Sambaetiba",
        40: "Itb - Areal",
        41: "Itb - Apa Guapimirim",
        42: "Itb - Fazenda Macacu",
        43: "Mc - Cabiúnas",
        44: "Mc - Fazenda Severina",
        45: "Mc - Pesagro",
        46: "Mc - Meteorológica Fazenda Severina",
        47: "Mc - Fazenda Airis",
        48: "SJB - Mato Escuro 5º Distrito",
        49: "SJB - Açú 5º Distrito",
        50: "Cg - Val Palmas",
        51: "Cg - Macuco",
        52: "Cg - Meteorológica Euclidelândia 2",
        53: "Cg - Meteorológica Euclidelândia 1",
        54: "Cg - Euclidelândia",
        55: "Jp - Engenheiro Pedreira",
        56: "Sp - Meteorológica Jardim Maracanã",
        57: "NI - Jardim Guandu",
        58: "Sp - Piranema",
        59: "RJ - Meteorológica UTE Santa Cruz",
        60: "Itg - Monte Serrat",
        61: "RJ - Adalgisa Nery",
        62: "RJ - Meteorológica Santa Cruz",
        63: "Itg - Coroa Grande",
        64: "Mt - Itacuruçá",  # 2013
        65: "Itg - Meteorológica Ilha Da Madeira",
        66: "Itg - Ilha Da Madeira",
        67: "Mt - Ibicuí",  # 2013
        68: "Mt - Praia Do Saco",  # 2013
        69: "VR - Belmonte",
        70: "VR - Retiro",
        71: "VR - Santa Cecília",
        72: "VR - Meteorológica Ilha das Águas Cruas",
        73: "BM - Boa Sorte",
        74: "BM - Sesi",
        75: "BM - Bocaininha",
        76: "BM - Roberto Silveira",
        77: "BM - Vista Alegre",
        78: "PR - Porto Real",
        79: "Qt - Bom Retiro",
        80: "Rs - Casa da Lua",
        81: "Rs - Cidade Alegria",
        82: "Itt - Campo Alegre",
        83: "Itt - Meteorológica Itatiaia",
        85: "Mt - Sahy",  # 2013
        86: "SJB - Fazenda Saco Dantas",
        142: "Mc - Imboassica",
        215: "SJM - Coelho da Rocha",
        216: "SC - João XXIII (Caminhao)",
        217: "SC - 27ºBPM (Caminhão)",
        218: "RJ - Van (Sumaré-SBT)",
        219: "RJ - Van (Parque Parnaso - Guapimirim)",
        220: "RJ - Van (Parque do Mendanha)",
        221: "RJ - Van (Parque da Serra da Tiririca)",
        222: "RJ - Urca",
        223: "RJ - São Conrado",
        224: "RJ - Maracanã",
        225: "RJ - Leblon",
        226: "RJ - Lab. INEA",
        227: "RJ - Jacarepaguá",
        228: "RJ - Gamboa",
        229: "Nit - Caio Martins",
        252: "Monitor - CO Plaza Shopping",
        281: "E. Móvel - Linha Amarela LAMSA - RJ",
        282: "E. Móvel - Lagoa - RJ.",
        291: "E. Móvel - Velha-Cidade Meninos",
        292: "E. Móvel - Resende",
        293: "E. Móvel - Parmalat Macae-RJ",
        294: "E. Móvel - Macaé - Norte Fuminense",
        295: "E. Móvel - Jardim Meriti - Vilar dos Teles - RJ OF",
        296: "E. Móvel - Itaguaí EMBRAPA",
        297: "E. Móvel - Engenheiro Pedreira",
        298: "E. Móvel - Belford Roxo",
        299: "E. Móvel - Barra Mansa",
        300: "E. Móvel - Velha - Petrópolis",
        609: "Itaborai - Ciep 130 - Meteorologia",
        610: "Itaborai - Vor Infraero - Meteorologia",
        611: "Radar Vor Da Infraero - Cetrel-Automatica",
        613: "Estação Meteorológica - Ute Campos",
        608: "Itb - Alto do Jacú",
        637: "VR - Nossa Sra. das Graças (Van)",
        730: "E. M. Francisco C. de Alvarenga",
        733: "DC - Bacia de Resfriamento",
        735: "DC - Campos Elíseos (Antiga)",
        737: "DC - Pier das Chatas",
        740: "Mc - Macaé Merchant",
        742: "RJ - Aeroporto de Campo dos Afonsos",
        743: "Mc - Aeroporto de Macaé",
        744: "RJ - Aeroporto do Galeão",
        745: "SC - Base Aérea de Santa Cruz",
        746: "SG - GETEC",
        747: "Itg - Estação Gaia",
        748: "Nit - Charitas",
        749: "Nit - Itaipu",
        750: "Mt - Terminal da Ilha Guaíba",  # 2013
        788: "Qmd - Meteorológica Jardim Riachão",
        789: "Pet - Retiro",
        804: "Itg - Brisamar"
    }
    
    df_ids = pd.DataFrame(list(stations_dict_automaticas.items()), columns=["ID_MMA", "ID_OEMA"])
    
    df_ids["ID_MMA"] = "RJ" + df_ids["ID_MMA"].astype(str).str.zfill(4)
    
    return df_ids
    
#%% Função para Espírito Santo

codigo_estacao_ES = {'Carapina': 'ES0001', 
                     'Cariacica': 'ES0002', 
                     'Vila Capixaba': 'ES0002',
                     'Enseada do Suá': 'ES0003', 
                     'Jardim Camburi': 'ES0004', 
                     'Laranjeiras': 'ES0005', 
                     'Vila Velha Centro': 'ES0006', 
                     'Vila Velha IBES': 'ES0007', 
                     'Vitória Centro': 'ES0008', 
                     'Cidade Continental': 'ES0009', 
                     'Ubu': 'ES0010', 
                     'Mãe Bá': 'ES0011', 
                     'Belo Horizonte': 'ES0012', 
                     'Meaípe': 'ES0013', 
                     'Guanabara': 'ES0014', 
                     'Anchieta Centro': 'ES0015', 
                     'Cariacica Vila Capixaba': 'ES0002', 
                     'Linhares2': 'ES0016', 
                     'Linhares1': 'ES0017', 
                     'Ponta Formosa': 'ES0018'}

def rectify_ES(path):
    
    path = path + 'coletados_organizados/'
    
    print(path)
    
    dict_pols_stat = defaultdict(list)
    
    files = os.listdir(path)
    
    lista=[]
    
    codigos_pols_ES = {
        'Partículas Inaláveis (<10µm)': 'PM10',
        'Partículas Totais em Suspensão': 'PTS',
        'Dióxido de Enxofre':'SO2',
        'Monóxido de Nitrogênio':'NO',
        'Dióxido de Nitrogênio':'NO2',
        'Óxidos de Nitrogênio':'NOX',
        'Monóxido de Carbono': 'CO',
        'Ozônio': 'O3',
        'Partículas Inaláveis (< 2.5µm)': 'PM25',
        'Metano': 'CH4',
        'Hidrocarbonetos Não Metano': 'HCNM',
        'Hidrocarbonetos Totais': 'HCT',
        'Partículas Inaláveis <2.5µm': 'PM25',
        'Partículas Respiráveis (<2,5µm)': 'PM25',
        'Partículas Respiráveis (< 2,5µm)': 'PM25',}
        
    for item in files:
        partes = item.split('_')
        ano = partes[-1]
        
        if ano.endswith('.xls'):
            ano = ano[:-4]
                
        elif ano.endswith('.xlsx'):
            ano = ano[:-5]
        
        df = pd.read_excel(path+item)
        
        df.iloc[0] = df.iloc[0].ffill()
        df.iloc[0, 0] = "DATETIME"
        
        df.columns = df.iloc[0]
        
        estacoes = df.columns.unique()
        
        for est in estacoes[1:]:
            print(est)
                
            df_est = df[["DATETIME", est]]
            
            df_est.iloc[1] = df_est.iloc[1].ffill()
            df_est.iloc[1, 0] = "DATETIME"
            
            df_est.columns = df_est.iloc[1]
            
            df_est = df_est[["DATETIME", "Qualidade do Ar"]]
            
            df_est.iloc[3] = df_est.iloc[3].ffill()
            df_est.iloc[3, 0] = "DATETIME"
            
            df_est.columns = df_est.iloc[3]
            
            poluentes = df_est.columns.unique()
                
            for pol in poluentes[1:]:
            
                df_est_pol = df_est[["DATETIME", pol]]
                
                idx = df_est_pol.apply(lambda row: row.astype(str).str.contains("Flag").any(), axis=1).idxmax()

                df_est_pol = df_est_pol.loc[idx:].reset_index(drop=True)
            
                df_est_pol.columns = df_est_pol.iloc[0]

                df_est_pol = df_est_pol.drop(df_est_pol.index[0]).reset_index(drop=True)
                
                unidade = df_est_pol.columns[1].split('[')[1][:-1]
            
                df_est_pol = df_est_pol.rename(columns={df_est_pol.columns[1]: 'VALOR',
                                                        df_est_pol.columns[0]: 'DATETIME',
                                                        df_est_pol.columns[2]: 'QAQC_INTERNO'})
            
                df_est_pol.insert(2, 'UNIDADE', unidade)
            
                if "(" in est:
                    est = est.split('(')[-1][:-1]
                else:
                    est = est.split('- ')[-1]
                
                if "-" in est:
                    est = est.replace("-", " ")
                
                if "-" in pol:
                    pol = pol.replace("-", " ")
                
                if pol in codigos_pols_ES.keys():
                    pol = codigos_pols_ES[pol]
                
                    lista.append(est)
                
                    chave = f"{est}_{pol}"
                    dict_pols_stat[chave].append(df_est_pol)

    dict_pols_stat = dict(dict_pols_stat)
    
    dict_stations = {}
    
    lista_poluentes = []
    
    poluentes = list(pd.DataFrame({'DATETIME':lista_poluentes})['DATETIME'].unique())
    
    for chave in dict_pols_stat.keys():
        
        station = chave.split('_')[0]
        pol = chave.split('_')[1]
            
        df_pol_stat = pd.DataFrame({
            'DATETIME':[]})  
        
        for df in dict_pols_stat[chave]:
            
            if df.shape[1] > 5:  # verifica se tem 5 colunas
                
                df = df.iloc[:, :-(df.shape[1]-3)] 
            
            df = df.rename(columns={df.columns[0]: 'DATETIME'})
            
            df = df.set_index(df['DATETIME'])
            
            df_pol_stat = pd.concat([df_pol_stat, df])
            
        df_pol_stat = df_pol_stat.sort_index()
        
        lista_horas = pd.date_range(
            start=df_pol_stat.index.min(), 
            end=df_pol_stat.index.max(), 
            freq='H').strftime('%Y-%m-%d %H:%M:%S').tolist()
        
        if len(lista_horas) != len(df_pol_stat):
            df_pol_stat = df_pol_stat.reindex(pd.DatetimeIndex(lista_horas))
        
        df_pol_stat = df_pol_stat.drop(columns=['DATETIME'])
        
        df_pol_stat.insert(0, 'DATETIME', df_pol_stat.index)
        df_pol_stat.insert(1, 'ANO', df_pol_stat.index.year)
        df_pol_stat.insert(2, 'MES', df_pol_stat.index.month)
        df_pol_stat.insert(3, 'DIA', df_pol_stat.index.day)
        df_pol_stat.insert(4, 'HORA', df_pol_stat.index.hour)
        
        df_pol_stat['VALOR'] = df_pol_stat['VALOR'].map(parse_valor)  
        
        dict_stations[chave] = df_pol_stat
            
    primeiros_valores = {}

    for chave, df in dict_stations.items():
        
        if ~df['VALOR'].isna().all() and (df['VALOR'] > 0).any(): 
            
            linha_valida = df[df["VALOR"].notna() & (df["VALOR"] > 0)].iloc[0]
            primeiros_valores[chave] = linha_valida["DATETIME"]
    
    codigo_estacao_ES = {}
    
    for chave in primeiros_valores.keys():
        
        station = chave.split('_')[0]
        data = primeiros_valores[chave]
        
        if station in codigo_estacao_ES:
            if data <= codigo_estacao_ES[station]:
                codigo_estacao_ES[station] = data
        else:
            codigo_estacao_ES[station] = data
    
    sorted_items = sorted(
        codigo_estacao_ES.items(),
        key=lambda x: (x[1], x[0])
    )
    
    codigo_estacao_ES = {}
    for i, (nome, ts) in enumerate(sorted_items, start=1):
        codigo = f"ES{i:04d}"
        codigo_estacao_ES[nome] = codigo
        
    codigo_estacao_ES = {'Carapina': 'ES0001', 
                     'Cariacica': 'ES0002', 
                     'Vila Capixaba': 'ES0002',
                     'Enseada do Suá': 'ES0003', 
                     'Jardim Camburi': 'ES0004', 
                     'Laranjeiras': 'ES0005', 
                     'Vila Velha Centro': 'ES0006', 
                     'Vila Velha IBES': 'ES0007', 
                     'Vitória Centro': 'ES0008', 
                     'Cidade Continental': 'ES0009', 
                     'Ubu': 'ES0010', 
                     'Mãe Bá': 'ES0011', 
                     'Belo Horizonte': 'ES0012', 
                     'Meaípe': 'ES0013', 
                     'Guanabara': 'ES0014', 
                     'Anchieta Centro': 'ES0015', 
                     'Cariacica Vila Capixaba': 'ES0002', 
                     'Linhares2': 'ES0016', 
                     'Linhares1': 'ES0017', 
                     'Ponta Formosa': 'ES0018'}
    
    for chave in dict_stations.keys():
        
        df_pol_stat = dict_stations[chave]
        
        station = chave.split('_')[0]
        pol = chave.split('_')[1]

        if pol == 'CO':
            df_pol_stat = ug_to_ppm(df_pol_stat)
        
        cod_poluente = int(tabela_pols.loc[tabela_pols['POLUENTE'] == pol, 'COD_POLUENTE'].values[0])
       
        cod_poluente = f"{cod_poluente:03d}"
        
        s_ou_a = 'A'
        
        i_ou_r = 'R'
        
        cod_estacao = codigo_estacao_ES[station]
        
        nome_pasta = tabela_pols.loc[tabela_pols['COD_POLUENTE'] == int(cod_poluente), 'NOME_PASTA'].values[0]
        
        df_pol_stat.to_csv('/home/nobre/Notebooks/RQAR_2025_book/data/MQAr_teste/'+nome_pasta+'/'+cod_estacao+i_ou_r+s_ou_a+cod_poluente+'.csv', index=False)

    path = '/home/nobre/Notebooks/RQAR_2025_book/data/DADOS_BRUTOS/ES/coletados_norte/Linhares/'
    
    dict_pols_stat = defaultdict(list)
    
    files = os.listdir(path)
    
    lista=[]
    
    for item in files:
        
        est = item[:-5]
        
        df = pd.read_excel(path+item)
        
        poluentes = df.columns.unique()
            
        for pol in poluentes[1:]:
        
            df_est_pol = df[["Data", pol]]
        
            df_est_pol = df_est_pol.rename(columns={df_est_pol.columns[1]: 'VALOR',
                                                    df_est_pol.columns[0]: 'DATETIME'})
        
            if pol == 'CO':
                unidade = 'ppm'
            else:
                unidade = 'µg/m³'
        
            df_est_pol['UNIDADE'] = unidade
        
            df_est_pol['QAQC_INTERNO'] = None
        
            if "(" in est:
                est = est.split('(')[-1][:-1]
            else:
                est = est.split('- ')[-1]
            
            if "-" in est:
                est = est.replace("-", " ")
            
            if "-" in pol:
                pol = pol.replace("-", " ")
            
            lista.append(est)
        
            chave = f"{est}_{pol}"
            dict_pols_stat[chave].append(df_est_pol)
        
    dict_pols_stat = dict(dict_pols_stat)
     
    dict_stations = {}
    
    lista_poluentes = []
    
    poluentes = list(pd.DataFrame({'Data':lista_poluentes})['Data'].unique())
    
    for chave in dict_pols_stat.keys():
        
        station = chave.split('_')[0]
        pol = chave.split('_')[1]
            
        df_pol_stat = dict_pols_stat[chave][0]
            
        df_pol_stat = df_pol_stat.set_index(df_pol_stat['DATETIME']).drop(columns=['DATETIME'])

        df_pol_stat.index = pd.to_datetime(df_pol_stat.index, errors='coerce')  # converte strings para datetime
        df_pol_stat = df_pol_stat.sort_index()
        
        lista_horas = pd.date_range(
            start=df_pol_stat.index.min(), 
            end=df_pol_stat.index.max(), 
            freq='H').strftime('%Y-%m-%d %H:%M:%S').tolist()
        
        if len(lista_horas) != len(df_pol_stat):
            df_pol_stat = df_pol_stat[~df_pol_stat.index.duplicated(keep='first')]
        
        df_pol_stat.insert(0, 'DATETIME', df_pol_stat.index)
        df_pol_stat.insert(1, 'ANO', df_pol_stat.index.year)
        df_pol_stat.insert(2, 'MES', df_pol_stat.index.month)
        df_pol_stat.insert(3, 'DIA', df_pol_stat.index.day)
        df_pol_stat.insert(4, 'HORA', df_pol_stat.index.hour)
        
        df_pol_stat['VALOR'] = df_pol_stat['VALOR'].map(parse_valor)  
        
        dict_stations[chave] = df_pol_stat
    
    codigo_estacao_ES = {
        'Linhares1':'ES0018',
        'Linhares2':'ES0017'}

    for chave in dict_stations.keys():
        
        df_pol_stat = dict_stations[chave]
        
        station = chave.split('_')[0]
        pol = chave.split('_')[1]

        if pol == 'CO':
            df_pol_stat = ug_to_ppm(df_pol_stat)
        
        cod_poluente = int(tabela_pols.loc[tabela_pols['POLUENTE'] == pol, 'COD_POLUENTE'].values[0])
       
        cod_poluente = f"{cod_poluente:03d}"
        
        s_ou_a = 'A'
        
        i_ou_r = 'R'
        
        cod_estacao = codigo_estacao_ES[station]
        
        nome_pasta = tabela_pols.loc[tabela_pols['COD_POLUENTE'] == int(cod_poluente), 'NOME_PASTA'].values[0]
        
        df_pol_stat.to_csv('/home/nobre/Notebooks/RQAR_2025_book/data/MQAr_teste/'+nome_pasta+'/'+cod_estacao+i_ou_r+s_ou_a+cod_poluente+'.csv', index=False)

    df_ids = pd.DataFrame({
        'ID_OEMA': ['EMQAR - RGV1 - Laranjeiras','EMQAR - RGV2 - Carapina',
                    'EMQAR - RGV3 - Jardim Camburi','EMQAR - RGV4 - Enseada do Suá',
                    'EMQAR - RGV5 - Vitória Centro','EMQAR - RGV6 - Ibes',
                    'EMQAR - RGV7 - Vila Velha Centro','EMQAR - RGV8 - Vila Capixaba',
                    'EMQAR - RGV9 - Cidade Continental','EMQAR - RGV10 - Praia do Canto',
                    'EMQAR SUL 01 - Meaípe','EMQAR SUL 02 - Ubu','EMQAR SUL 03 - Guanabara',
                    'EMQAR SUL 04 - Belo Horizonte ','EMQAR SUL 05 - Mãe-Bá ',
                    'EMQAR SUL 06 - Centro','EMQAR - Norte 01 - Cacimbas',
                    'EMQAR - Norte 02 - Cacimbas','EMAQR - UTE Viana'],
        'ID_MMA' : ['ES0005','ES0001','ES0004','ES0003','ES0008','ES0007',
                    'ES0006','ES0002','ES0009','ES0019','ES0013','ES0010','ES0014',
                    'ES0012','ES0011','ES0015','ES0018','ES0017','ES0019']})
    
    return df_ids
    

#%% Função para Minas Gerais
def rectify_MG(path):
    
    path = path + 'coletados_organizado/'
    
    
    lista_poluentes_index_0 = ['CH4 (ppm)',
                    'Dióxido de enxofre (ppb)',
                    'Tolueno (ppb)',
                    'Óxidos de Nitrogênio (ppb)',
                    'Partículas Inaláveis (<10µm)(µg/m3)',
                    'Dióxido de Nitrogênio (ppb)',
                    'Partículas Respiráveis (<2,5µm) (µg/m3)',
                    'Partículas Inaláveis (<10µm) (µg/m3)',
                    'Para e Meta Xileno (ppb)',
                    'Monóxido de Nitrogênio (ppb)',
                    'Partículas Totais (ug/m3)',
                    'Partículas Inaláveis (<10µm/m3)',
                    'HCNM (ppm)',
                    'Partículas Totais (µg/m3)',
                    'Ozônio (ppb)',
                    'Benzeno (ppb)',
                    'Orto Xileno (ppb)',
                    'Partículas Respiráveis (<2,5µm)(µg/m3)',
                    'Etil Benzeno (ppb)',
                    'HCT (ppm)',
                    'Monóxido de Carbono (ppm)',
                    'Partículas Respiráveis (<2,5um/m3)']
    
    lista_poluentes_index_1 = [
     'PM10',
     'PM 10',
     'PM2,5',
     'PM 2,5',
     'PTS',
     'CO',
     'NO2',
     'O3',
     'SO2'
     ]
    
    dict_poluentes_index_0 = {
        'Dióxido de enxofre':'SO2',
        'Tolueno':'TOLUENO',
        'Óxidos de Nitrogênio':'NOX',
        'CH4':'CH4',
        'Partículas Inaláveis':'MP10',
        'Dióxido de Nitrogênio':'NO2',
        'Partículas Respiráveis':'MP25',
        'Para e Meta Xileno':'MPX',
        'Monóxido de Nitrogênio':'NO',
        'Partículas Totais':'PTS',
        'HCNM':'HCNM',
        'Ozônio':'O3',
        'Benzeno':'BENZENO',
        'Orto Xileno':'OX',
        'Etil Benzeno':'ETILBENZENO',
        'HCT':'HCT',
        'Monóxido de Carbono':'CO'}
    
    dict_poluentes_index_1 = {
     'PM10': 'MP10',
     'PM 10': 'MP10',
     'PM2,5': 'MP25',
     'PM 2,5': 'MP25',
     'PTS': 'PTS',
     'CO': 'CO',
     'NO2': 'NO2',
     'O3': 'O3',
     'SO2': 'SO2'}
    
    print(path)
    
    dict_pols_stat = defaultdict(list)
    
    files = os.listdir(path)
    
    lista=[]
    
    tabela_ids_mg = pd.read_excel('/home/nobre/Notebooks/RQAR_2025_book/data/DADOS_BRUTOS/MG/tabela_MG_codigos.xlsx')
    tabela_ids_mg["estacao"] = tabela_ids_mg["estacao"].str.replace("E.M. Pe Vicente Assunção","E.M. Pe. Vicente Assunção", regex=False)
    tabela_ids_mg["estacao"] = tabela_ids_mg["estacao"].str.replace("Sao Domingos","São Domingos", regex=False)
    tabela_ids_mg["estacao"] = tabela_ids_mg["estacao"].str.replace("Corregos","Córregos", regex=False)
    tabela_ids_mg["estacao"] = tabela_ids_mg["estacao"].str.replace("Uniao","União", regex=False)
    tabela_ids_mg["estacao"] = tabela_ids_mg["estacao"].str.replace("Sergio","Sérgio", regex=False)
    tabela_ids_mg["estacao"] = tabela_ids_mg["estacao"].str.replace("Cecilia","Cecília", regex=False)
    tabela_ids_mg["estacao"] = tabela_ids_mg["estacao"].str.replace("Celvia","Célvia", regex=False)
    tabela_ids_mg["estacao"] = tabela_ids_mg["estacao"].str.replace("Fabrica","Fábrica", regex=False)
    tabela_ids_mg["estacao"] = tabela_ids_mg["estacao"].str.replace("Feijao","Feijão", regex=False)
    tabela_ids_mg["estacao"] = tabela_ids_mg["estacao"].str.replace("Para","Pará", regex=False)
    tabela_ids_mg["estacao"] = tabela_ids_mg["estacao"].str.replace("Parácatu","Paracatu", regex=False)
    tabela_ids_mg["estacao"] = tabela_ids_mg["estacao"].str.replace("Sao Gabriel","São Gabriel", regex=False)
    tabela_ids_mg["estacao"] = tabela_ids_mg["estacao"].str.replace("S.Gabriel","São Gabriel", regex=False)
    tabela_ids_mg["estacao"] = tabela_ids_mg["estacao"].str.replace("Basilica","Basílica", regex=False)
    tabela_ids_mg["estacao"] = tabela_ids_mg["estacao"].str.replace("Silverio","Silvério", regex=False)
    tabela_ids_mg["estacao"] = tabela_ids_mg["estacao"].str.replace("SENAC Vale do Aco","Senac", regex=False)
    tabela_ids_mg["estacao"] = tabela_ids_mg["estacao"].str.replace("Puc Barreiro","PUC Barreiro", regex=False)
	

    
    for item in files:
        
        estacao = item.split(' -')[0][:-5][8:]
        cod_estacao = tabela_ids_mg.loc[tabela_ids_mg['estacao'] == estacao, 'codigo'].values[0]
        
        ano = item.split(' -')[0][-4:]
        
        df = pd.read_excel(path+item)
        
        mask = df.iloc[:, 0].astype(str).str.match(r'^\d')
        
        indice = mask.idxmax() if mask.any() else None
        
        if indice == 0:
        
            df = df.loc[indice:]

            colunas_para_manter = list(df.columns[:2]) + [c for c in lista_poluentes_index_0 if c in df.columns]
            
            poluentes = colunas_para_manter[2:]
            
            df = df[colunas_para_manter]    
            
            for pol in poluentes:
                
                unidade = pol.split('(')[-1][:-1]
                
                poluente = pol.split('(')[0][:-1]
                
                poluente = dict_poluentes_index_0[poluente]
                
                df_pol = df[['Data','Hora',pol]]
                
                df_pol["Hora"] = pd.to_timedelta(df_pol["Hora"].astype(str))
                
                df_pol["DATETIME"] = df_pol["Data"] + df_pol["Hora"]
                
                df_pol.index = df_pol["DATETIME"]
                
                mask = (df_pol.index.hour == 0) & (df_pol["Data"] == df_pol["Data"].shift())

                df_pol.loc[mask, "DATETIME"] += pd.Timedelta(days=1)
                
                df_pol = df_pol.drop(columns=['Data','Hora'])
                
                cols = ["DATETIME"] + [c for c in df_pol.columns if c != "DATETIME"]
                
                df_pol = df_pol[cols]
                
                df_pol.index = df_pol['DATETIME']
                
                df_pol.insert(1, 'ANO', df_pol.index.year)
                df_pol.insert(2, 'MES', df_pol.index.month)
                df_pol.insert(3, 'DIA', df_pol.index.day)
                df_pol.insert(4, 'HORA', df_pol.index.hour)
                
                df_pol['UNIDADE'] = unidade
                        
                df_pol = df_pol.rename(columns={pol: 'VALOR'})
                
                df_pol['QAQC_INTERNO'] = None
                
                cod_poluente = int(tabela_pols.loc[tabela_pols['POLUENTE'] == poluente, 'COD_POLUENTE'].values[0])
               
                cod_poluente = f"{cod_poluente:03d}"
                
                i_ou_r = 'R'
                
                s_ou_a = 'A'
                
                nome_pasta = tabela_pols.loc[tabela_pols['COD_POLUENTE'] == int(cod_poluente), 'NOME_PASTA'].values[0]
                
                #df_pol.to_csv('/home/lcqar/MMA/O07/data/MQAr/'+nome_pasta+'/'+cod_estacao+i_ou_r+s_ou_a+cod_poluente+'.csv', index=False)
            
                dict_pols_stat[cod_estacao+i_ou_r+s_ou_a+cod_poluente].append(df_pol)
        
        else:
            cod_poluente='100'
            if indice >= 2:
                df.columns = df.iloc[indice-2]  
                df = df.drop(df.index[indice-2]) 
                df = df.reset_index(drop=True)
            
                cod_poluente = str(indice*100)
            
            mask = df.iloc[:, 1:].applymap(lambda x: pd.api.types.is_number(x) or pd.isna(x)).all(axis=1)
            
            primeira_valida = mask.idxmax()-1
            
            df = df.loc[primeira_valida:].reset_index(drop=True)
            
            df.rename(columns={df.columns[0]: "DATETIME"}, inplace=True)
            
            colunas_para_manter = list(df.columns[:1]) + [c for c in lista_poluentes_index_1 if c in df.columns]
            
            poluentes = colunas_para_manter[1:]
            
            df = df[colunas_para_manter]    

            for pol in poluentes:
                
                df_pol = df[['DATETIME',pol]]
                
                unidade = df_pol[pol][0]
                    
                df_pol = df_pol.iloc[1:].reset_index(drop=True)
                
                poluente = dict_poluentes_index_1[pol]
                
                df_pol = df_pol[~df_pol["DATETIME"].astype(str).str.contains("1900", na=False)]
                
                df_pol["DATETIME"] = pd.to_datetime(df_pol["DATETIME"], errors="coerce")
                
                df_pol.index = df_pol["DATETIME"]
                
                mask = df_pol.index.minute == 30
                
                df_pol.loc[mask, "DATETIME"] = df_pol.loc[mask, "DATETIME"] + pd.Timedelta(minutes=30)
                
                df_pol.insert(1, 'ANO', df_pol.index.year)
                df_pol.insert(2, 'MES', df_pol.index.month)
                df_pol.insert(3, 'DIA', df_pol.index.day)
                df_pol.insert(4, 'HORA', df_pol.index.hour)
                
                df_pol['UNIDADE'] = unidade
                        
                df_pol = df_pol.rename(columns={pol: 'VALOR'})
                
                df_pol['QAQC_INTERNO'] = None
                
                cod_poluente = int(tabela_pols.loc[tabela_pols['POLUENTE'] == poluente, 'COD_POLUENTE'].values[0])
               
                cod_poluente = f"{cod_poluente:03d}"
                
                i_ou_r = 'R'
                
                s_ou_a = 'A'
                
                nome_pasta = tabela_pols.loc[tabela_pols['COD_POLUENTE'] == int(cod_poluente), 'NOME_PASTA'].values[0]
                
                #df_pol.to_csv('/home/lcqar/MMA/O07/data/MQAr/'+nome_pasta+'/'+cod_estacao+i_ou_r+s_ou_a+cod_poluente+'.csv', index=False)
                
                dict_pols_stat[cod_estacao+i_ou_r+s_ou_a+cod_poluente].append(df_pol)
        
    dict_pols_stat = dict(dict_pols_stat)
    
    for id_mma_completo in dict_pols_stat.keys():

        df_pol_stat = pd.DataFrame()
        
        for df in dict_pols_stat[id_mma_completo]:
            
            df_pol_stat = pd.concat([df_pol_stat, df])
            
        df_pol_stat = df_pol_stat.sort_index()
        
        lista_horas = pd.date_range(
            start=df_pol_stat.index.min(), 
            end=df_pol_stat.index.max(), 
            freq='H').strftime('%Y-%m-%d %H:%M:%S').tolist()
        
        if len(lista_horas) != len(df_pol_stat):
            df_pol_stat = df_pol_stat.reindex(pd.DatetimeIndex(lista_horas))
        
        nome_pasta = tabela_pols.loc[tabela_pols['COD_POLUENTE'] == int(id_mma_completo[-3:]), 'NOME_PASTA'].values[0]
        
        df_pol_stat.to_csv('/home/nobre/Notebooks/RQAR_2025_book/data/MQAr_teste/'+nome_pasta+'/'+id_mma_completo+'.csv', index=False)
        
#%%
 
#%%


#%%
codigos_SC = {
    'Estação Vila Moema':'SC0001',
    'Estação Capivari de Baixo':'SC0002',
    'Estação São Bernardo':'SC0003',
    'Estação UFSC':'SC0004'}

codigos_pols_SC = {
    'Dióxido de Enxofre': 'SO2',
    'Partículas Totais em Suspensão': 'PTS',
    'Dióxido de Nitrogênio':'NO2',
    'Material Particulado <10µm':'MP10',
    'Material Particulado <2.5µm':'MP25',
    'Ozônio':'O3',
    'KLABIN_PM25': 'MP25',	
    'KLABIN_NO': 'NO',		
    'KLABIN_NO2': 'NO2',		
    'KLABIN_NOX': 'NOX',	
    'KLABIN_O3': 'O3',
    'Monóxido de Carbono': 'CO'
}

def rectify_SC(path):
    
    estacoes = pd.read_excel(path+'SC_organizado/SC_monitoramento.xlsx')
    
    new_cols = estacoes.columns.to_series()
    new_cols[new_cols.str.contains("Unnamed")] = None
    estacoes.columns = new_cols.ffill()
    
    estacoes = estacoes.drop([0])
    
    estacoes.columns.values[0] = 'DATETIME'
    
    estacoes.columns = estacoes.columns.str.strip()
    
    nome_estacoes = estacoes.columns[1:].unique()
    
    for nome_estacao in nome_estacoes:
        
        estacao = estacoes.loc[:, estacoes.columns.isin([estacoes.columns[0], nome_estacao])]
        
        novos_nomes = estacao.iloc[0, 1:].tolist()
        novas_colunas = [estacoes.columns[0]] + novos_nomes
        estacao.columns = novas_colunas
        estacao = estacao.iloc[1:].reset_index(drop=True)
        
        estacao = estacao.set_index("DATETIME")
    
        for pol in estacao.columns[:]:
            
            estacao_pol = estacao.copy()

            estacao_pol.insert(0, 'DATETIME', estacao_pol.index)
            
            estacao_pol = estacao_pol.filter(items=[estacoes.columns[0],pol])
            
            unidade = estacao_pol[pol][0].split('[')[-1][:-1]
            
            estacao_pol = estacao_pol.drop(['NaT'])
            
            lista_horas = pd.date_range(
                start=estacao_pol.index.min(), 
                end=estacao_pol.index.max(), 
                freq='H').strftime('%Y-%m-%d %H:%M:%S').tolist()
            
            if len(lista_horas) != len(estacao_pol):
                estacao_pol = estacao_pol.reindex(pd.DatetimeIndex(lista_horas))
            
            estacao_pol = estacao_pol.rename(columns={pol:'VALOR'})
            
            estacao_pol.insert(1, 'ANO', estacao_pol[estacao_pol.columns[0]].dt.year)
            estacao_pol.insert(2, 'MES', estacao_pol[estacao_pol.columns[0]].dt.month)
            estacao_pol.insert(3, 'DIA', estacao_pol[estacao_pol.columns[0]].dt.day)
            estacao_pol.insert(4, 'HORA', estacao_pol[estacao_pol.columns[0]].dt.hour)
            
            estacao_pol['UNIDADE'] = unidade
            
            estacao_pol['QAQC_INTERNO'] = None
            
            cod_pol = tabela_pols.loc[tabela_pols['POLUENTE'] == codigos_pols_SC[pol], 'COD_POLUENTE'].values[0]
            
            nome_pasta = tabela_pols.loc[tabela_pols['COD_POLUENTE'] == int(cod_pol), 'NOME_PASTA'].values[0]
        
            estacao_pol.to_csv('/home/nobre/Notebooks/RQAR_2025_book/data/MQAr_teste/'+nome_pasta+'/'
                               + codigos_SC[nome_estacao] +'RA'+ str(cod_pol).zfill(3) + '.csv',index=False)

    estacao_CO = pd.read_excel('/home/nobre/Notebooks/RQAR_2025_book/data/DADOS_BRUTOS/SC/SC_organizado/CO_EQar_VilaMoema.xlsx')
    
    nome_estacao = estacao_CO.iloc[0, 1]
    
    pol = codigos_pols_SC[estacao_CO.iloc[3, 1]]
    
    cod_pol = tabela_pols.loc[tabela_pols['POLUENTE'] == pol, 'COD_POLUENTE'].values[0]
    
    unidade = estacao_CO.iloc[6, 1].split('[')[-1][:-1]
    
    estacao_CO.columns.values[0] = 'DATETIME'
    estacao_CO.columns.values[1] = 'VALOR'
    estacao_CO.columns.values[2] = 'FLAG'
    
    estacao_CO = estacao_CO.drop([0,1,2,3,4,5,6])
    
    estacao_CO = estacao_CO.set_index('DATETIME')
    
    lista_horas = pd.date_range(
        start=estacao_CO.index.min(), 
        end=estacao_CO.index.max(), 
        freq='H').strftime('%Y-%m-%d %H:%M:%S').tolist()
    
    if len(lista_horas) != len(estacao_CO):
        estacao_CO = estacao_CO.reindex(pd.DatetimeIndex(lista_horas))
    
    estacao_CO.insert(0, 'DATETIME', estacao_CO.index)
    
    estacao_CO.insert(1, 'ANO', estacao_CO[estacao_CO.columns[0]].dt.year)
    estacao_CO.insert(2, 'MES', estacao_CO[estacao_CO.columns[0]].dt.month)
    estacao_CO.insert(3, 'DIA', estacao_CO[estacao_CO.columns[0]].dt.day)
    estacao_CO.insert(4, 'HORA', estacao_CO[estacao_CO.columns[0]].dt.hour)
    
    estacao_CO = estacao_CO.rename(columns={'FLAG': 'QAQC_INTERNO'})
    
    estacao_CO['UNIDADE'] = unidade
    
    nome_pasta = tabela_pols.loc[tabela_pols['COD_POLUENTE'] == int(cod_pol), 'NOME_PASTA'].values[0]
    
    estacao_CO.to_csv('/home/nobre/Notebooks/RQAR_2025_book/data/MQAr_teste/'+nome_pasta+'/'
                       + codigos_SC[nome_estacao] +'RA'+ str(cod_pol).zfill(3) + '.csv',index=False)

    # UFSC

    estacao_ufsc = pd.read_csv('/home/nobre/Notebooks/RQAR_2025_book/data/DADOS_BRUTOS/SC/SC_organizado/SC_monitoramento - Florianópolis (startup em outubro24)(data).csv')
    
    poluentes = estacao_ufsc.iloc[0, 1:].dropna().tolist()
    
    estacao_ufsc.columns = estacao_ufsc.iloc[0].ffill()

    estacao_ufsc = estacao_ufsc[1:]
    
    estacao_ufsc.columns.values[0] = 'DATETIME'
    
    for pol in poluentes:
        if pol in codigos_pols_SC.keys():
            
            estacao_pol = estacao_ufsc.copy()
            
            estacao_pol = estacao_pol[[estacao_ufsc.columns[0]] + [col for col in estacao_pol.columns if col.startswith(pol)]]
            
            estacao_pol = estacao_pol.iloc[:, :-2]
            
            estacao_pol.columns.values[0] = 'DATETIME'
            estacao_pol.columns.values[1] = 'VALOR'
            estacao_pol.columns.values[2] = 'QAQC_INTERNO'
            
            unidade = estacao_pol['VALOR'][1]
            
            estacao_pol = estacao_pol[1:]
            
            estacao_pol["DATETIME"] = pd.to_datetime(estacao_pol["DATETIME"])

            estacao_pol["DATETIME"] = estacao_pol["DATETIME"] - pd.Timedelta(minutes=15)
            
            estacao_pol = estacao_pol.set_index('DATETIME')
            
            estacao_pol.insert(0, 'DATETIME', estacao_pol.index)
            estacao_pol.insert(1, 'ANO', estacao_pol[estacao_pol.columns[0]].dt.year)
            estacao_pol.insert(2, 'MES', estacao_pol[estacao_pol.columns[0]].dt.month)
            estacao_pol.insert(3, 'DIA', estacao_pol[estacao_pol.columns[0]].dt.day)
            estacao_pol.insert(4, 'HORA', estacao_pol[estacao_pol.columns[0]].dt.hour)
            
            estacao_pol["VALOR"] = pd.to_numeric(estacao_pol["VALOR"], errors="coerce")
            
            estacao = estacao_pol.groupby(["ANO", "MES", "DIA", "HORA"])
            
            qtd_A = estacao["QAQC_INTERNO"].apply(lambda x: (x == "A").sum())
            media_A = estacao.apply(lambda x: x.loc[x["QAQC_INTERNO"] == "A", "VALOR"].mean())
            
            estacao = (
                media_A.to_frame("VALOR")
                .reset_index()
                .assign(
                    VALOR=lambda d: d["VALOR"].where(qtd_A.values >= 3, np.nan),
                    QAQC_INTERNO=np.where(qtd_A.values >= 3, "A", "N")
                )
            )
            
            estacao['UNIDADE'] = unidade
            
            estacao['DATETIME'] = pd.to_datetime({
                'year': estacao['ANO'],
                'month': estacao['MES'],
                'day': estacao['DIA'],
                'hour': estacao['HORA']
            })
            
            estacao = estacao.set_index('DATETIME')

            lista_horas = pd.date_range(
                start=estacao.index.min(), 
                end=estacao.index.max(), 
                freq='H').strftime('%Y-%m-%d %H:%M:%S').tolist()
            
            if len(lista_horas) != len(estacao_CO):
                estacao_pol = estacao_pol.reindex(pd.DatetimeIndex(lista_horas))
            
            estacao.insert(0, 'DATETIME', estacao.index)
            
            nome_estacao = 'Estação UFSC'
            
            cod_pol = tabela_pols.loc[tabela_pols['POLUENTE'] == codigos_pols_SC[pol], 'COD_POLUENTE'].values[0]
            
            nome_pasta = tabela_pols.loc[tabela_pols['COD_POLUENTE'] == int(cod_pol), 'NOME_PASTA'].values[0]
        
            estacao.to_csv('/home/nobre/Notebooks/RQAR_2025_book/data/MQAr_teste/'+nome_pasta+'/'
                               + codigos_SC[nome_estacao] +'RA'+ str(cod_pol).zfill(3) + '.csv',index=False)
    
    df_ids = pd.DataFrame({
        'ID_OEMA': ['Vila Moema', 'Capivari', 'São Bernardo', 'UFSC'],
        'ID_MMA' : ['SC0001','SC0002','SC0003','SC0004']})
    
    return df_ids
    
#%% Função para Rio Grande do Sul

estacoes_RS = {
    '2014-Triunfo DEPREC':'RS0009',
    '2014-Esteio VE':'RS0006',
    '2014-Canoas VCOMAR':'RS0004',
    '2013-Charqueadas-AT':'RS0013',
    '012A-Gravataí C Jardim Timbaúva':'RS0012',
    '2014-Charqueadas-AT':'RS0013',
    '015A-Guaiba Parque 35':'RS0015',
    '017A-Esteio Parque de Exposição':'RS0017',
    '019A-Candiota Aeroporto':'RS0019',
    '005A-Canoas P Universitário':'RS0005',
    '0013A-Charqueadas Arranca Toco':'RS0013',
    '012A-Gravatai C Jardim Timpauva':'RS0012',
    '021A-Candiota Tres Lagoas':'RS0021',
    '2013- Esteio VE':'RS0006',
    '2013-Gravatai CJT':'RS0012',
    '006A-Esteio Vila Ezequiel':'RS0006',
    '009A-Triunfo DEPREC':'RS0009',
    '2013-Canoas PU':'RS0005',
    '020A-Candiota Candiota':'RS0020',
    '016A-Triunfo Polo Movel':'RS0016',
    '2013-Sapucaia':'RS0001',
    '2014-Gravatai CJT':'RS0012',
    '015A-Guaíba Parque 35':'RS0015',
    '2014-Guaiba P35':'RS0015',
    '004A-Canoas V COMAR':'RS0004',
    '005A-Canoas P Universitario':'RS0005',
    '022A-POA CETE':'RS0022',
    '2014-Canoas PU':'RS0005',
    '018A-Rio Grande Porto':'RS0018',
    '016A-Triunfo Polo móvel':'RS0016',
    '2013- Triunfo DEPREC':'RS0009'}

codigos_pols_RS={
    'co ': 'CO',
    'pm10': 'MP10',
    'pm2,5': 'MP25',
    'no2': 'NO2',
    'so2': 'SO2',
    'o3': 'O3'}

def rectify_RS(path):

    path = '/home/nobre/Notebooks/RQAR_2025_book/data/DADOS_BRUTOS/RS/'
    
    dict_pols_stat = defaultdict(list)
    
    files = os.listdir(path)
    
    lista=[]
    
    for item in files:

        if item.endswith('Vargas'):
        
            estacoes = os.listdir(path+item)[0]
                
            abas = pd.ExcelFile(path+item+'/'+estacoes).sheet_names
    
            for aba in abas:
                
                df = pd.read_excel(path+item+'/'+estacoes, 
                                   sheet_name=aba)
                
                if df.columns[0] != 'data':
                    idx = df[df.iloc[:,0] == "data"].index[0]
        
                    df.columns = df.iloc[idx]
                    df = df.iloc[idx+1:].reset_index(drop=True)
                
                if df.iloc[0].astype(str).str.contains(r"(ppm|ug/m³)", case=False).any():
                    df = df.iloc[1:].reset_index(drop=True)    
                
                poluentes = df.columns
                
                cod_estacao = estacoes_RS[aba]
                
                for pol in poluentes[1:]:
                    
                    df_pol = df[['data',pol]]
                    
                    if pol == 'co ':
                        df_pol['UNIDADE'] = 'ppm'
                    else:
                        df_pol['UNIDADE'] = 'ug/m3'
                
                    df_pol['QAQC_INTERNO'] = None
                
                    cod_pol = tabela_pols.loc[tabela_pols['POLUENTE'] == codigos_pols_RS[pol], 'COD_POLUENTE'].values[0]
                    
                    cod_pol = f"{cod_pol:03d}"
                
                    id_mma_completo = cod_estacao + 'RA' + cod_pol
                
                    df_pol = df_pol.rename(columns={'data':'DATETIME',
                                            pol:'VALOR'})
                
                    dict_pols_stat[id_mma_completo].append(df_pol)
                    
    dict_pols_stat = dict(dict_pols_stat)
    
    for chave in dict_pols_stat.keys():
        
        df_est_pol = pd.DataFrame()
        
        for df in dict_pols_stat[chave]:
                
            df_est_pol = pd.concat([df_est_pol, df])
        
        df_est_pol = df_est_pol[df_est_pol["DATETIME"].notna()]
        
        df_est_pol.index = df_est_pol['DATETIME']
        
        df_est_pol = df_est_pol.sort_index()
        
        df_est_pol = df_est_pol[~df_est_pol.index.duplicated(keep="first")]
        
        lista_horas = pd.date_range(
            start=df_est_pol.index.min(), 
            end=df_est_pol.index.max(), 
            freq='H').strftime('%Y-%m-%d %H:%M:%S').tolist()
        
        if len(lista_horas) != len(df_est_pol):
            df_est_pol = df_est_pol.reindex(pd.DatetimeIndex(lista_horas))
        
        df_est_pol.insert(1, 'ANO', df_est_pol.index.year)
        df_est_pol.insert(2, 'MES', df_est_pol.index.month)
        df_est_pol.insert(3, 'DIA', df_est_pol.index.day)
        df_est_pol.insert(4, 'HORA', df_est_pol.index.hour)
        
        nome_pasta = tabela_pols.loc[tabela_pols['COD_POLUENTE'] == int(chave[-3:]), 'NOME_PASTA'].values[0]
        
        df_est_pol.to_csv('/home/nobre/Notebooks/RQAR_2025_book/data/MQAr_teste/'+nome_pasta+'/'+chave+'.csv',index=False)

    df_ids = pd.DataFrame({
    'ID_MMA': ['RS0001','RS0004','RS0005','RS0006','RS0009','RS0012','RS0013','RS0015','RS0016','RS0017','RS0018','RS0019','RS0020','RS0021','RS0022'],
    'ID_OEMA':['Sapucaia','Canoas VCOMAR','Canoas P Universitário','Esteio Vila Ezequiel','Triunfo DEPREC','Gravataí C Jardim Timbaúva','Charqueadas-AT','Guaiba Parque 35', 'Triunfo Polo Movel','Esteio Parque de Exposição','Rio Grande Porto','Candiota Aeroporto','Candiota Candiota','Candiota Tres Lagoas','POA CETE']})
    return df_ids

    
#%% Função para PR

def rectify_PR(path):
    print(path)

'''
for estado in lista_estados:
    
    path = os.getcwd()+'/data/DADOS_BRUTOS/' + estado + '/'

    funcoes[estado](path)
'''

'''
    
#%% Função para Bahia

def rectify_BA(path):
    
    path = os.getcwd()+'/data/dados_monitoramento/BA/output_by_station_pollutant/'
    
    dict_pols_stat = defaultdict(list)
    
    files = os.listdir(path)
    
    lista=[]
    
    for item in files:
                    
        if 'csv' in item:
            pol = item.split('_')[-4]
            
            pol = tabela_pols.loc[tabela_pols['COD_POLUENTE'] == int(pol), 'NOME_PASTA'].values[0]
            
            ano = item.split('_')[-3]
            mes = item.split('_')[-2]
            dia = item.split('_')[-1].split('.')[0]
            
            estacao = ''.join(item.split('_')[1:-4])
            
            df = pd.read_csv(path+item)
            
            df['ANO'] = ano
            df['MES'] = mes
            df['DIA'] = dia
            
            df['DATETIME'] = pd.to_datetime(df["DATETIME"])
            
            df.index = df['DATETIME']
            
            df['HORA'] = df.index.hour

            df = df.rename(columns={'CONC':'VALOR','QAQC':'QAQC_INTERNO'})
            
            df = df[['DATETIME','ANO','MES','DIA','HORA','VALOR','QAQC_INTERNO']]
            
            dict_pols_stat[estacao+'_'+pol].append(df)
            
            #df = pd.read_csv(path+item)

    lista = list(set(lista))


#%% Função para Maranhão

def rectify_MA(path):
    
    path = os.getcwd()+'/data/dados_monitoramento/MA/output_by_station_pollutant/'
    
    dict_pols_stat = defaultdict(list)
    
    files = os.listdir(path)
    
    lista=[]
    
    for item in files:
        
        pol = item.split('_')[-2]
        
        lista.append(pol)
        
        # df = pd.read_csv(path+item)

    lista = list(set(lista))
'''

funcoes = {
    'MG': rectify_MG,
    'ES': rectify_ES,
    'SP': rectify_SP,
    'RJ': rectify_RJ,
    
    'SC': rectify_SC,
    'RS': rectify_RS,
    'PR': rectify_PR
}

lista_estados = ['RJ','SP','SC','RS','ES']

tabela_ids = pd.read_csv('/home/nobre/Notebooks/RQAR_2025_book/data/Monitoramento_QAr_BR.csv')
tabela_pols = pd.read_csv('/home/nobre/Notebooks/RQAR_2025_book/data/dicionarios/CODIGO_POLUENTES.csv')

for estado in lista_estados:
    
    path = os.getcwd()+'/data/DADOS_BRUTOS/' + estado + '/'

    df_ids = funcoes[estado](path)
    
    create_df_estacao(estado,df_ids)
