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
import glob
import csv


os.chdir('/home/nobre/Notebooks/RQAR_2025_book/')

def create_QAQCMMA_VALOR(df,pol):

    if 'VALOR_ORIGINAL' in df.columns:
        df = df.drop(columns='VALOR_ORIGINAL')

    df = df.rename(columns={'VALOR':'VALOR_ORIGINAL'})

    flags_invalidos = ['?E','!', 'IF', 'IO', 'IC', 'I%', 'IL', 'IE', 'IS', 'IU', 'IM', 'IP', 'ID', 'IT', 'IR', 
                       'Fora da Faixa de Medição', 'Disabilitada Temporariamente', 'Inválido', 
                       'Insuficientes', 'Inexistente']

    df['QAQC_INTERNO'] = ~df['QAQC_INTERNO'].isin(flags_invalidos)
    
    DEFAULT_RANGE_LIMITS = {
        "O3": (0, 500),
        "CO": (0, 50),
        "NO2": (0, 1000),
        "NOX": (0, 2000),
        "SO2": (0, 1000),
        "MP25": (0, 1000),
        "MP10": (0, 2000),
    }

    df['QAQC_MMA'] = df['QAQC_INTERNO']

    if pol in list(DEFAULT_RANGE_LIMITS.keys()):
        lim_min = DEFAULT_RANGE_LIMITS[pol][0]
        lim_max = DEFAULT_RANGE_LIMITS[pol][1]
    else:
        lim_min = 0
        lim_max = np.inf
    
    df['VALOR'] = df['VALOR_ORIGINAL']

    df['VALOR'] = pd.to_numeric(df['VALOR'], errors='coerce')
    
    df.loc[df['QAQC_MMA'] & (df['VALOR'].isna() | (df['VALOR'] <= lim_min) | (df['VALOR'] >= lim_max)), 'QAQC_MMA'] = False
    
    df.loc[df['VALOR'] == 985, 'VALOR'] = np.nan
    
    df.loc[~df['QAQC_MMA'], 'VALOR'] = np.nan
    
    df = df[['DATETIME', 'ANO', 'MES', 'DIA', 'HORA', 'VALOR', 'VALOR_ORIGINAL', 'UNIDADE', 'QAQC_INTERNO', 'QAQC_MMA']]

    return df

def pol_to_station(df_ids):

    base_path = Path('/home/nobre/Notebooks/RQAR_2025_book/data/MQAr/')

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

        colunas = ['ID_OEMA', 'UF', 'ID_MMA', 'ID_MMA_COMPLETO', 'COD_UF_IBGE', 'CIDADE', 'CD_MUN',
                   'PROPRIETARIO', 'PROP_ENTIDADE', 'OPERADOR', 'OP_ENTIDADE', 'LATITUDE',
                   'LONGITUDE', 'MOBILIDADE', 'REALOCACAO', 'MARCA', 'CATEGORIA',
                   'FUNCIONAMENTO', 'METODO', 'FINALIDADE', 'POLUENTE',
                   'INICIO', 'STATUS', 'FIM', 'CALIBRACAO', 'OBS_CALIBRACAO', 'MONITORAR',
                   'FONTE', 'OBS_GERAIS','DADOS_MONITORAMENTO','RECONHECIDA','REP_ESPACIAL_DECLARADA']
        
        df_estacao = pd.DataFrame(columns=colunas)

    df_ids = pol_to_station(df_ids)

    mapa = dict(zip(df_ids['ID_MMA'], df_ids['POLUENTE']))
    
    df_estacao['POLUENTE'] = df_estacao['ID_MMA'].map(mapa).fillna(df_estacao['POLUENTE'])

    df_estacao.loc[:, "COD_UF_IBGE"] = cod_uf
    df_estacao.loc[:, "UF"] = uf
    
    df_estacao.to_csv('/home/nobre/Notebooks/RQAR_2025_book/data/DADOS_ESTACOES/'+uf+'_estacoes.csv', index=False)

def ug_to_ppm(df):

    df.loc[df["UNIDADE"] == "ug/m3", "VALOR"] = 868.26/10*6
    df.loc[df["UNIDADE"] == "Âµg/mÂ", "VALOR"] = 868.26/10*6
    df.loc[df["UNIDADE"] == "µg/m³", "VALOR"] = 868.26/10*6
    df.loc[df["UNIDADE"] == "µg/m3", "VALOR"] = 868.26/10*6
    df.loc[df["UNIDADE"] == "µg/m³", "VALOR"] = 868.26/10*6
    df.loc[df["UNIDADE"] == "ppb", "VALOR"] *= 1/1000
    

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
    
def normalize_text(x: str) -> str:
    """Remove acentos e padroniza texto (útil para nomes de poluentes e flags)."""
    import unicodedata
    if pd.isna(x):
        return ""
    x = str(x).strip()
    x = unicodedata.normalize("NFKD", x).encode("ascii", "ignore").decode("ascii")
    return x
    
def create_QAQCMMA_VALOR_RR(df, pol):
    import unicodedata

    # === Preserva valor original ===
    if 'VALOR_ORIGINAL' not in df.columns:
        df = df.rename(columns={'VALOR': 'VALOR_ORIGINAL'})

    # === Normaliza flag textual ===
    flags_invalidos = {
        '?E','!','IF','IO','IC','I%','IL','IE','IS','IU','IM','IP','ID','IT','IR',
        'FORA DA FAIXA DE MEDICAO','DISABILITADA TEMPORARIAMENTE','INVALIDO',
        'INSUFICIENTES','INEXISTENTE'
    }
    if 'QAQC_INTERNO' not in df.columns:
        df['QAQC_INTERNO'] = np.nan

    flags_norm = df['QAQC_INTERNO'].astype(str).str.strip().str.upper()
    flags_norm = flags_norm.apply(lambda s: unicodedata.normalize("NFKD", s).encode("ascii","ignore").decode("ascii") if isinstance(s,str) else s)
    flags_norm = flags_norm.replace({"NAN":"INVALIDO", "": "INVALIDO"})
    df['QAQC_INTERNO'] = ~flags_norm.isin(flags_invalidos)

    # === Limpeza textual do valor ===
    df['VALOR_LIMPO'] = (
        df['VALOR_ORIGINAL']
        .astype(str)
        .str.replace(r'[^\d\.\-]', '', regex=True)  # remove letras, unidades, etc.
        .replace({'': np.nan})
    )

    df['VALOR'] = pd.to_numeric(df['VALOR_LIMPO'], errors='coerce')

    # === Faixas e sentinelas ===
    DEFAULT_RANGE_LIMITS = {
        "O3": (0, 500),
        "CO": (0, 50),
        "NO2": (0, 1000),
        "NOX": (0, 2000),
        "SO2": (0, 1000),
        "MP25": (0, 1000),
        "MP10": (0, 2000),
        "NO": (0, 2000)
    }

    sentinelas_invalidas = {985, 998, 999, 9999, -999, -9999, 8888, 7777}
    lim_min, lim_max = DEFAULT_RANGE_LIMITS.get(pol, (0, np.inf))

    # arredonda floats antes da comparação (evita erro 985.0 ≠ 985)
    df['VALOR_INT'] = df['VALOR'].round().astype('Int64')

    mask_invalida = (
        df['VALOR'].isna() |
        (df['VALOR'] <= lim_min) |
        (df['VALOR'] >= lim_max) |
        (df['VALOR_INT'].isin(sentinelas_invalidas))
    )

    df['QAQC_MMA'] = df['QAQC_INTERNO']
    df.loc[df['QAQC_MMA'] & mask_invalida, 'QAQC_MMA'] = False
    df.loc[~df['QAQC_MMA'], 'VALOR'] = np.nan

    cols = ['DATETIME','ANO','MES','DIA','HORA','VALOR','VALOR_ORIGINAL','UNIDADE','QAQC_INTERNO','QAQC_MMA']
    for c in cols:
        if c not in df.columns:
            df[c] = np.nan

    return df[cols]

   
#%% Função para São Paulo
def rectify_SP(path):
    
    path = path + 'dados_coletados/'
    
    estacoes_SP = pd.read_excel('/home/nobre/Notebooks/RQAR_2025_book/data/DADOS_BRUTOS/SP/lista_estacoes_SP.xlsx')
    
    dict_pols_stat = defaultdict(list)
    
    files = os.listdir(path)
    
    lista=[]
    
    for item in files:

        if item != '.ipynb_checkpoints':
                
            arquivos = os.listdir(path+item)
            
            for arquivo in arquivos:

                if arquivo != '.ipynb_checkpoints':
    
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
        
                            df_pol = create_QAQCMMA_VALOR(df_pol,nome_pasta)
                            
                            df_pol.to_csv('/home/nobre/Notebooks/RQAR_2025_book/data/MQAr/'+nome_pasta+'/'+cod_estacao+i_ou_r+s_ou_a+cod_poluente+'.csv', index=False)
                        
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
    
    for pol in tabela_pols['NOME_PASTA'].unique():

        print(pol)
        
        caminho = os.getcwd()+'/data/MQAr/' + str(pol) + '/'

        print(caminho)
        
        if os.path.isdir(caminho) and os.listdir(caminho):
            
            arquivos = os.listdir(caminho)
        
            for estacao in arquivos:
    
                if estacao.startswith('RJ'):

                    print(caminho+estacao)
    
                    df = pd.read_csv(caminho+estacao)

                    df = create_QAQCMMA_VALOR(df,pol)

                    df.to_csv('/home/nobre/Notebooks/RQAR_2025_book/data/MQAr/'+pol+'/'+estacao, index=False)
    
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
        
        if item != '.ipynb_checkpoints':
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
                     'Linhares1':'ES0018',
                     'Linhares2':'ES0017',
                     'Ponta Formosa': 'ES0016'}
    
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

        df_pol_stat = create_QAQCMMA_VALOR(df_pol_stat,nome_pasta)
        
        df_pol_stat.to_csv('/home/nobre/Notebooks/RQAR_2025_book/data/MQAr/'+nome_pasta+'/'+cod_estacao+i_ou_r+s_ou_a+cod_poluente+'.csv', index=False)

    path = '/home/nobre/Notebooks/RQAR_2025_book/data/DADOS_BRUTOS/ES/coletados_norte/Linhares/'
    
    dict_pols_stat = defaultdict(list)
    
    files = os.listdir(path)
    
    lista=[]
    
    for item in files:

        if item != '.ipynb_checkpoints':
        
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

        df_pol_stat = create_QAQCMMA_VALOR(df_pol_stat,nome_pasta)
        
        df_pol_stat.to_csv('/home/nobre/Notebooks/RQAR_2025_book/data/MQAr/'+nome_pasta+'/'+cod_estacao+i_ou_r+s_ou_a+cod_poluente+'.csv', index=False)

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
                    'ES0006','ES0002','ES0009','ES0016','ES0013','ES0010','ES0014',
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

        if item != '.ipynb_checkpoints':
        
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
        
        df_pol_stat = create_QAQCMMA_VALOR(df_pol_stat,nome_pasta)
        
        df_pol_stat.to_csv('/home/nobre/Notebooks/RQAR_2025_book/data/MQAr/'+nome_pasta+'/'+id_mma_completo+'.csv', index=False)

    df_ids = pd.read_csv('/home/nobre/Notebooks/RQAR_2025_book/data/DADOS_BRUTOS/MG/tabela_MG_codigos.csv')

    return df_ids
        
#%%
 
#%% SC


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

            estacao_pol = create_QAQCMMA_VALOR(estacao_pol,nome_pasta)
        
            estacao_pol.to_csv(
                f"/home/nobre/Notebooks/RQAR_2025_book/data/MQAr/{nome_pasta}/"
                f"{codigos_SC[nome_estacao]}RA{int(cod_pol):03d}.csv",
                index=False
            )
            
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

    estacao_CO = create_QAQCMMA_VALOR(estacao_CO,nome_pasta)
    
    estacao_CO.to_csv(
        f"/home/nobre/Notebooks/RQAR_2025_book/data/MQAr/{nome_pasta}/"
        f"{codigos_SC[nome_estacao]}RA{int(cod_pol):03d}.csv",
        index=False
    )

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

            estacao = create_QAQCMMA_VALOR(estacao,nome_pasta)
        
            estacao.to_csv(
                f"/home/nobre/Notebooks/RQAR_2025_book/data/MQAr/{nome_pasta}/"
                f"{codigos_SC[nome_estacao]}RA{int(cod_pol):03d}.csv",
                index=False
            )

    
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

        if item != '.ipynb_checkpoints':

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
                    
                        cod_pol = str(int(tabela_pols.loc[tabela_pols['POLUENTE'] == codigos_pols_RS[pol], 'COD_POLUENTE'].values[0])).zfill(3)
                    
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

        df_est_pol = create_QAQCMMA_VALOR(df_est_pol,nome_pasta)
        
        df_est_pol.to_csv('/home/nobre/Notebooks/RQAR_2025_book/data/MQAr/'+nome_pasta+'/'+chave+'.csv',index=False)

    df_ids = pd.DataFrame({
    'ID_MMA': ['RS0001','RS0004','RS0005','RS0006','RS0009','RS0012','RS0013','RS0015','RS0016','RS0017','RS0018','RS0019','RS0020','RS0021','RS0022'],
    'ID_OEMA':['Sapucaia','Canoas VCOMAR','Canoas P Universitário','Esteio Vila Ezequiel','Triunfo DEPREC','Gravataí C Jardim Timbaúva','Charqueadas-AT','Guaiba Parque 35', 'Triunfo Polo Movel','Esteio Parque de Exposição','Rio Grande Porto','Candiota Aeroporto','Candiota Candiota','Candiota Tres Lagoas','POA CETE']})
    return df_ids

    
#%% Função para PR

#%% Função para PR

def ler_dados_parana_2024(dicionario,ano):
    
    #caminho =  os.getcwd()+'/data/DADOS_BRUTOS/PR/2024/'

    caminho = os.getcwd()+'/data/DADOS_BRUTOS/PR/'+ano+'/'
    
    arquivos = os.listdir(caminho)
    
    for arquivo in arquivos:

        if arquivo != '.ipynb_checkpoints':
    
            if arquivo.endswith(('.xls', '.xlsx')):
                caminho_arquivo = os.path.join(caminho, arquivo)
                try:
                    df = pd.read_excel(caminho_arquivo, header=3)
                except Exception as e:
                    print(f"Tentando ler como texto: {arquivo}")
                    df = pd.read_csv(caminho_arquivo, sep='\t', engine='python', encoding='latin1', header=2, on_bad_lines='skip')
                    print(len(df))
                    
                col_data = next(c for c in df.columns if c.startswith('Data'))
            
                df = (
                df.replace('-', np.nan)
                  .assign(**{
                      c: pd.to_numeric(
                          df[c].astype(str).str.replace(',', '.', regex=False),
                          errors='coerce'
                      )
                      for c in df.columns if c != col_data
                  })
                  .groupby(col_data, as_index=False)
                  .agg(lambda x: x.dropna().iloc[0] if len(x.dropna()) else np.nan)
                )
                
                if '5MIN' in arquivo:
                    estacao = arquivo.split('_')[0]
                else:
                    estacao = arquivo.split('2')[0]
                
                if df.columns[0] == 'Data/Hora':
            
                    print(estacao)
        
                    dicionario[ano][estacao] = df
    
                print(len(df))

    return dicionario

def adicionar_colunas_unidade(df):
    unidades = df.iloc[0]
    
    df = df.iloc[1:].reset_index(drop=True)
    
    for col, unidade in unidades.items():
        if pd.notna(unidade):
            df[f"{col}_UNIDADE"] = unidade
    
    return df

def num_para_hora(valor):
    try:
        h = int(valor)
        m = "30" if valor % 1 == 0.5 else "00"
        return f"{h}:{m}"
    except:
        return None
        
    return df

def ler_dados_parana_1998_2002(dicionario,ano):
    
    caminho = os.getcwd()+'/data/DADOS_BRUTOS/PR/'+ano+'/'
        
    arquivos = os.listdir(caminho)
    
    for arquivo in arquivos:

        print(arquivo)
    
        if any(Path(caminho+arquivo).iterdir()):
            pasta = os.listdir(caminho+arquivo)[0]
    
            df = pd.read_excel(caminho+arquivo+'/'+pasta,header=1)

            df = adicionar_colunas_unidade(df)

            for hora in ['H', 'HORA', 'Hora']:
                if hora in df.columns:
                    df[hora] = df[hora].astype(float).apply(num_para_hora)
                    break

            estacao = arquivo[:-4]
    
            dicionario[ano][estacao] = df 

            print(len(df))
    
        else:
            print('Não há nada em '+ caminho+arquivo)

    return dicionario

def ler_dados_mes_a_mes(caminho):

    tipos_arquivos_ignorar = ['.zip','.rar','.xls','.xlsx','.7z','testes','2016','.ipynb_checkpoints']

    df = pd.DataFrame()

    #print(caminho)
    #print(sorted(os.listdir(caminho)))

    estacao = caminho.split('/')[-2].split('2')[0]
    
    for arquivo in sorted(os.listdir(caminho)):
        df_mes = pd.DataFrame()
    
        if not any(p in arquivo for p in tipos_arquivos_ignorar) or any(p in arquivo for p in ['txt']):

            if '.txt' in arquivo:
                df_mes = pd.read_csv(caminho+arquivo, sep='\t', engine='python', encoding='latin1')
                #print(df_mes.head())
                #print(arquivo)
                df = pd.concat([df, df_mes], ignore_index=True)
            
            else:
                mes = arquivo[:2]
                base_path = os.path.join(caminho, arquivo)
                
                nomes_possiveis = [
                    [f"{estacao}1H_{mes}_{ano}.txt",0],
                    [f"{estacao}1H.txt",0],
                    [f"{estacao}1H_{mes}_{ano}.xls",3],
                    [f"{estacao}_1H.xls",2]
                ]

                for nome in nomes_possiveis:
                    full_path = os.path.join(base_path, nome[0])
                    
                    try:
                        df_mes = pd.read_csv(full_path, sep='\t', engine='python', encoding='latin1',header=nome[1])
                        break
                    except Exception:
                        try:
                            df_mes = pd.read_excel(full_path, engine='xlrd',header=nome[1])
                            break
                        except Exception:
                            continue

            if len(df_mes) == 0:

                print(caminho)
                #print(sorted(os.listdir(caminho)))
                #print(arquivo)
                print(df_mes.head())
                print('')
                
            df = pd.concat([df, df_mes], ignore_index=True)

            #df = pd.concat([df, df_mes], ignore_index=True)
           
    
    print('')
            
    
    return df

def verifica_numero(num):
    try:
        if num != np.nan:
            float(num)
            return True
    except (ValueError, TypeError):
        return False

def verifica_data(data):
    try:
        pd.to_datetime(data)
        return True
    except (ValueError, TypeError):
        return False

def ler_dados_parana_2003_2019(dicionario,ano):

    pastas_ignorar = ['IQA diário','IQA_IAP','2016','ARAUCARIA2018','ARAUCARIA2019','Thumbs.db','~$Validação_Maio_2014.xlsm','SIX1H_2017.zip','.ipynb_checkpoints']

    caminho = os.getcwd()+'/data/DADOS_BRUTOS/PR/'+ano+'/'
        
    arquivos = os.listdir(caminho)

    print('')
    print(ano)
    
    for arquivo in arquivos:

        if arquivo not in pastas_ignorar:

            print(arquivo)
            
            if any(nome.endswith(('.xls', '.xlsx')) for nome in os.listdir(caminho+arquivo)) and len(os.listdir(caminho+arquivo)) <= 3:
                print(os.listdir(caminho+arquivo))

                xlsx = [f for f in os.listdir(caminho+arquivo) if f.endswith('.xlsx')]
                xls = [f for f in os.listdir(caminho+arquivo) if f.endswith('.xls')]
                
                if xlsx:
                    estacao = xlsx[0] 
                elif xls:
                    estacao = xls[0]

                try:
                    if ano == '2003':
                        df = pd.read_excel(caminho+arquivo+'/'+estacao,header=1)
                    elif estacao == 'CIC2019.xlsx':
                        df = pd.read_excel(caminho+arquivo+'/'+estacao,header=2)
                    else:
                        df = pd.read_excel(caminho+arquivo+'/'+estacao)
                except Exception as e:
                    print(f"Tentando ler como texto: {arquivo}")
                    df = pd.read_csv(caminho+arquivo+'/'+estacao, sep='\t', engine='python', encoding='latin1', header=2)
                
                if not (verifica_numero(df[df.columns[0]].iloc[0]) or verifica_data(df[df.columns[0]].iloc[0])) or arquivo == 'SIX2017':

                    df = adicionar_colunas_unidade(df)

                print(len(df))
                    
                dicionario[ano][arquivo[:-4]] = df 

            elif 'IAP' not in arquivo:

                try:
                        
                    df = ler_dados_mes_a_mes(caminho+arquivo+'/')
                    
                    if not (verifica_numero(df[df.columns[0]].iloc[0]) or verifica_data(df[df.columns[0]].iloc[0])):
    
                        df = adicionar_colunas_unidade(df)
                
                    dicionario[ano][arquivo[:-4]] = df 

                    print(len(df))

                except Exception as e:
                    print(f"A seguinte pasta não existe: {caminho}{arquivo}")
                    
    return(dicionario)

def parse_datetime(x):
    for fmt in ('%Y-%m-%d %H:%M:%S', '%d/%m/%Y %H:%M', '%m/%d/%Y %I:%M:%S %p'):
        try:
            return pd.to_datetime(x, format=fmt)
        except:
            continue
    return pd.to_datetime(x, errors='coerce')
                
def criar_datetime(df,tipo):

    if tipo == 'D':

        df['A'] = pd.to_numeric(df['A'], errors='coerce')

        if df['A'].iloc[0] < 2000:

            df['A'] = df['A'] + 2000
                
        df['H'] = df['H'].astype(str).str.split(':').str[0]
        
        df[['A', 'M', 'D', 'H']] = df[['A', 'M', 'D', 'H']].apply(pd.to_numeric, errors='coerce')
        
        df['datetime'] = pd.to_datetime(
            dict(year=df['A'], month=df['M'], day=df['D'], hour=df['H'].clip(upper=23)),
            errors='coerce'
        )
        
        df.loc[df['H'] == 24, 'datetime'] = df.loc[df['H'] == 24, 'datetime'] + pd.Timedelta(hours=1)
    
    elif tipo == 'DATA':

        df['datetime'] = pd.to_datetime(df['DATA']) + pd.to_timedelta(df['HORA'] + ':00')

        df = df.drop(columns=[c for c in ['ANO', 'MES', 'DIA', 'HORA'] if c in df.columns])
    
    elif tipo == 'Data':

        try:
            df['Data'] = pd.to_datetime(df['Data']).dt.date
        except:
            print(1)

        print(df.loc[df['Data'].astype(str).str.contains('--', na=False)])

        df['datetime'] = pd.to_datetime(df['Data']) + pd.to_timedelta(df['Hora'] + ':00')

    elif tipo == 'Data/Hora':
        
        df['Data/Hora'] = df['Data/Hora'].apply(parse_datetime)
        
        df['Data/Hora'] = df['Data/Hora'].dt.strftime('%Y-%m-%d %H:%M:%S')

        df['datetime'] = pd.to_datetime(df['Data/Hora'])

    elif tipo == 'Date/Time':
        
        df['Date/Time'] = df['Date/Time'].apply(parse_datetime)
        
        df['Date/Time'] = df['Date/Time'].dt.strftime('%Y-%m-%d %H:%M:%S')

        df['datetime'] = pd.to_datetime(df['Date/Time'])
        
    df = df.set_index("datetime")

    df = df.sort_index()
    
    df.insert(0, 'DATETIME', df.index)
    df.insert(1, 'ANO', df.index.year)
    df.insert(2, 'MES', df.index.month)
    df.insert(3, 'DIA', df.index.day)
    df.insert(4, 'HORA', df.index.hour)

    return df

def rectify_PR(path):

    estacoes_por_ano = {
        '1998': {},
        '1999': {},
        '2000': {},
        '2001': {},
        '2002': {},
        '2003': {},
        '2004': {},
        '2005': {},
        '2006': {},
        '2007': {},
        '2008': {},
        '2009': {},
        '2010': {},
        '2011': {},
        '2012': {},
        '2013': {},
        '2014': {},
        '2015': {},
        '2016': {},
        '2017': {},
        '2018': {},
        '2019': {},
        '2020': {},
        '2021': {},
        '2022': {},
        '2023': {},
        '2024': {}
    }
    
    for ano in ['1998','1999','2000',
                '2001','2002','2003','2004','2005','2006','2007','2008','2009','2010',
                '2011','2012','2013','2014','2015','2016','2017','2018','2019','2024']:
    
        if ano in ['1998','1999','2000','2001','2002']:
            estacoes_por_ano = ler_dados_parana_1998_2002(estacoes_por_ano,ano)
        elif ano in ['2003','2004','2005','2006','2007','2008','2009','2010','2011','2012','2013','2014','2015','2016','2017','2018','2019']:
            estacoes_por_ano = ler_dados_parana_2003_2019(estacoes_por_ano,ano)
        elif ano in ['2024']:
            estacoes_por_ano = ler_dados_parana_2024(estacoes_por_ano,ano)

    lista_colunas = []

    lista = []

    for ano in estacoes_por_ano.keys():
        
        print(ano)
    
        for estacao in estacoes_por_ano[ano].keys():
    
            #print(estacao)
            
            lista.append(estacao)
    
            lista_colunas = lista_colunas + list(estacoes_por_ano[ano][estacao].columns)
            
            if any(item in ['D','DATA','Data','Date/Time','Data/Hora'] for item in estacoes_por_ano[ano][estacao].columns):
    
                if 'D' in estacoes_por_ano[ano][estacao].columns:
                    print('D')
                    estacoes_por_ano[ano][estacao] = criar_datetime(estacoes_por_ano[ano][estacao], 'D')
                    #print(estacoes_por_ano[ano][estacao])
                elif 'DATA' in estacoes_por_ano[ano][estacao].columns:
                    print('DATA')
                    estacoes_por_ano[ano][estacao] = criar_datetime(estacoes_por_ano[ano][estacao], 'DATA')
                    #print(estacoes_por_ano[ano][estacao])
                elif 'Data' in estacoes_por_ano[ano][estacao].columns:
                    print('Data')
                    estacoes_por_ano[ano][estacao] = criar_datetime(estacoes_por_ano[ano][estacao], 'Data')
                    #print(estacoes_por_ano[ano][estacao])
                elif 'Date/Time' in estacoes_por_ano[ano][estacao].columns:
                    print('Date/Time')
                    estacoes_por_ano[ano][estacao] = criar_datetime(estacoes_por_ano[ano][estacao], 'Date/Time')
                    #print(estacoes_por_ano[ano][estacao])
                elif 'Data/Hora' in estacoes_por_ano[ano][estacao].columns:
                    print('Data/Hora')
                    estacoes_por_ano[ano][estacao] = criar_datetime(estacoes_por_ano[ano][estacao], 'Data/Hora')
                    #print(estacoes_por_ano[ano][estacao])
                else:
                    print('ERRO')
        print('')

    df_col_pols = pd.read_csv('/home/nobre/Notebooks/RQAR_2025_book/data/DADOS_BRUTOS/PR/colunas_pol_PR.csv',encoding='UTF-8')

    pol_estacao_ano = {}
    
    print(df_col_pols)
    
    for ano in estacoes_por_ano.keys():
    
        pol_estacao_ano[ano] = {}
    
        for estacao in estacoes_por_ano[ano]:
        
            pol_estacao_ano[ano][estacao] = {}
            
            for pol in df_col_pols['col_pr']:
    
                if pol in estacoes_por_ano[ano][estacao].columns and 'UNIDADE' not in pol:
    
                    poluente_mma = df_col_pols.loc[df_col_pols['col_pr'] == pol, 'col_mma'].iloc[0]
    
                    qaqc_interno = np.nan
                    
                    if '(' in pol:
                        unidade = pol.split('(')[-1][:-1]
                        print(pol)            
                        #print(unidade)
    
                        df = estacoes_por_ano[ano][estacao][['DATETIME','ANO','MES','DIA','HORA',pol]]
    
                        df['UNIDADE'] = unidade
                        df['QAQC_INTERNO'] = qaqc_interno
    
                        df.rename(columns={pol: 'VALOR'}, inplace=True)
                        
                    elif (pol+'_UNIDADE') in estacoes_por_ano[ano][estacao].columns:
                        #print('')
                        #print(pol)
                        #print('')
    
                        df = estacoes_por_ano[ano][estacao][['DATETIME','ANO','MES','DIA','HORA',pol,pol+'_UNIDADE']]
    
                        df['QAQC_INTERNO'] = qaqc_interno
    
                        df.rename(columns={pol: 'VALOR',pol+'_UNIDADE':'UNIDADE'}, inplace=True)
                        
                    else:
    
                        df = estacoes_por_ano[ano][estacao][['DATETIME','ANO','MES','DIA','HORA',pol]]
                        
                        df['UNIDADE'] = np.nan
                        df['QAQC_INTERNO'] = qaqc_interno
    
                        df.rename(columns={pol: 'VALOR'}, inplace=True)
    
                    pol_estacao_ano[ano][estacao][poluente_mma] = df

    pol_estacao = {}

    for ano, estacoes in pol_estacao_ano.items():
        for estacao, poluentes in estacoes.items():
            for poluente, df in poluentes.items():
                pol_estacao.setdefault(estacao, {}).setdefault(poluente, [])
                pol_estacao[estacao][poluente].append(df)
    
    estacoes_finais = {}
    
    for estacao, poluentes in pol_estacao.items():
        for poluente, lista_dfs in poluentes.items():
            df_concat = pd.concat(lista_dfs, ignore_index=True)
    
            df_concat = df_concat[df_concat['DATETIME'].notna()]
    
            df_concat['VALOR'] = (
                df_concat['VALOR']
                .astype(str)           
                .str.replace(',', '.', regex=False)  
            )
    
            df_concat['VALOR'] = pd.to_numeric(df_concat['VALOR'], errors='coerce')
    
            df_media = (
                df_concat.groupby(['ANO', 'MES', 'DIA', 'HORA', 'UNIDADE'], as_index=False)['VALOR']
                  .mean()
            )
            
            df_media["DATETIME"] = pd.to_datetime(
                df_media.apply(
                    lambda r: f"{int(r.ANO):04d}-{int(r.MES):02d}-{int(r.DIA):02d} {int(r.HORA):02d}:00:00",
                    axis=1
                )
            )
    
            df_media = df_media.drop(columns=['ANO', 'MES', 'DIA', 'HORA'])
    
            df_media = df_media.set_index("DATETIME")
        
            df_media = df_media.sort_index()
            
            lista_horas = pd.date_range(
                start=df_media.index.min(), 
                end=df_media.index.max(), 
                freq='H').strftime('%Y-%m-%d %H:%M:%S').tolist()
            
            if len(lista_horas) != len(df):
                df_media = df_media.reindex(pd.DatetimeIndex(lista_horas))
    
            df_media.insert(1, 'ANO', df_media.index.year)
            df_media.insert(2, 'MES', df_media.index.month)
            df_media.insert(3, 'DIA', df_media.index.day)
            df_media.insert(4, 'HORA', df_media.index.hour)
            
            df_media['DATETIME'] = df_media.index
    
            df_media['QAQC_INTERNO'] = None
            
            df_media = df_media[['DATETIME', 'ANO', 'MES', 'DIA', 'HORA', 'VALOR', 'UNIDADE', 'QAQC_INTERNO']]
    
            estacoes_finais[estacao+'_'+poluente] = df_media

    primeiros_valores = {}

    for chave, df in estacoes_finais.items():  
        
        if ~df['VALOR'].isna().all() and (df['VALOR'] > 0).any(): 
            
            linha_valida = df[df["VALOR"].notna() & (df["VALOR"] > 0)].iloc[0]
            primeiros_valores[chave] = linha_valida["DATETIME"]
    
    codigo_estacao_PR = {}
    
    for chave in primeiros_valores.keys():
        
        station = chave.split('_')[0]
        data = primeiros_valores[chave]
        
        if station in codigo_estacao_PR:
            if data <= codigo_estacao_PR[station]:
                codigo_estacao_PR[station] = data
        else:
            codigo_estacao_PR[station] = data
    
    sorted_items = sorted(
        codigo_estacao_PR.items(),
        key=lambda x: (x[1], x[0])
    )
    
    codigo_estacao_PR = {}
    for i, (nome, ts) in enumerate(sorted_items, start=1):
        codigo = f"PR{i:04d}"
        codigo_estacao_PR[nome] = codigo
        
    for chave, df in estacoes_finais.items():
        
        estacao = codigo_estacao_PR[chave.split('_')[0]]
    
        if chave.split('_')[-1] != 'CS':
            
            cod_pol = tabela_pols.loc[tabela_pols['NOME_PASTA'] == chave.split('_')[-1], 'COD_POLUENTE'].values[0]
            
            nome_pasta = tabela_pols.loc[tabela_pols['COD_POLUENTE'] == int(cod_pol), 'NOME_PASTA'].values[0]
        
            df = create_QAQCMMA_VALOR(df,nome_pasta)
    
            df.to_csv('/home/nobre/Notebooks/RQAR_2025_book/data/MQAr/'+nome_pasta+'/'+estacao+'RA'+str(int(cod_pol)).zfill(3)+'.csv',index=False)
    
    df_ids = pd.DataFrame({
        'ID_OEMA': codigo_estacao_PR.keys(),
        'ID_MMA':list(codigo_estacao_PR.values())})

    
    
    return df_ids


#%% Função para Bahia

def rectify_BA(path):
    
    path = path+'/output_by_station_pollutant/'
    
    dict_pols_stat = defaultdict(list)
    
    files = os.listdir(path)
    
    lista=[]
    
    i = 0
    
    for item in files:
        print(i)
        i = i + 1
                   
        if 'csv' in item:
            
            if os.path.getsize(path+item) > 0:  # só tenta ler se não for vazio
                try:
                    df = pd.read_csv(path+item)
                    
                    pol = item.split('_')[-4]
                    
                    pol = tabela_pols.loc[tabela_pols['COD_POLUENTE'] == int(pol), 'NOME_PASTA'].values[0]
                    
                    estacao = ''.join(item.split('_')[1:-4])
                    
                    df['DATETIME'] = pd.to_datetime(df["DATETIME"])
                    
                    df.index = df['DATETIME']

                    df = df.rename(columns={'CONC':'VALOR','QAQC':'QAQC_INTERNO'})
                    
                    dict_pols_stat[estacao+'_'+pol].append(df)
                    
                except pd.errors.EmptyDataError:
                    print(f"Arquivo vazio ou inválido: {path+item}")
                    df = pd.DataFrame()  # cria DF vazio
            else:
                print(f"Arquivo vazio: {path+item}")
                df = pd.DataFrame()
    
    dict_formatado = {}
    
    for chave in dict_pols_stat.keys():
        
        lista_dfs = dict_pols_stat[chave]
        
        df = pd.concat(lista_dfs, ignore_index=True)

        df["DATETIME"] = pd.to_datetime(df["DATETIME"])

        df = df.set_index("DATETIME")

        df = df.sort_index()
        
        lista_horas = pd.date_range(
            start=df.index.min(), 
            end=df.index.max(), 
            freq='H').strftime('%Y-%m-%d %H:%M:%S').tolist()
        
        if len(lista_horas) != len(df):
            df = df.reindex(pd.DatetimeIndex(lista_horas))
        
        df.insert(0, 'DATETIME', df.index)
        df.insert(1, 'ANO', df.index.year)
        df.insert(2, 'MES', df.index.month)
        df.insert(3, 'DIA', df.index.day)
        df.insert(4, 'HORA', df.index.hour)
        
        if chave.split('_')[-1] == 'CO':
            df['UNIDADE'] = 'ppm'
        else:
            df['UNIDADE'] = 'ug/m³'
        
        dict_formatado[chave] = df
        
    primeiros_valores = {}

    for chave, df in dict_formatado.items():
        
        if ~df['VALOR'].isna().all() and (df['VALOR'] > 0).any(): 
            
            linha_valida = df[df["VALOR"].notna() & (df["VALOR"] > 0)].iloc[0]
            primeiros_valores[chave] = linha_valida["DATETIME"]
    
    codigo_estacao_BA = {}
    
    for chave in primeiros_valores.keys():
        
        station = chave.split('_')[0]
        data = primeiros_valores[chave]
        
        if station in codigo_estacao_BA:
            if data <= codigo_estacao_BA[station]:
                codigo_estacao_BA[station] = data
        else:
            codigo_estacao_BA[station] = data
    
    sorted_items = sorted(
        codigo_estacao_BA.items(),
        key=lambda x: (x[1], x[0])
    )
    
    codigo_estacao_BA = {}
    for i, (nome, ts) in enumerate(sorted_items, start=1):
        codigo = f"BA{i:04d}"
        codigo_estacao_BA[nome] = codigo
        
    for chave, df in dict_formatado.items():
        
        estacao = codigo_estacao_BA[chave.split('_')[0]]
        
        cod_pol = tabela_pols.loc[tabela_pols['POLUENTE'] == chave.split('_')[-1], 'COD_POLUENTE'].values[0]
        
        nome_pasta = tabela_pols.loc[tabela_pols['COD_POLUENTE'] == int(cod_pol), 'NOME_PASTA'].values[0]

        df = create_QAQCMMA_VALOR(df,nome_pasta)
        
        df.to_csv('/home/nobre/Notebooks/RQAR_2025_book/data/MQAr/'+nome_pasta+'/'+estacao+'ND'+str(int(cod_pol)).zfill(3)+'.csv',index=False)

    df_ids = pd.DataFrame({
    'ID_OEMA': codigo_estacao_BA.keys(),
    'ID_MMA':list(codigo_estacao_BA.values())})

    return df_ids

#%% Função para Maranhão

def rectify_MA(path):
    
    path = path+'/output_by_station_pollutant/'
    
    dict_pols_stat = defaultdict(list)
    
    files = os.listdir(path)
    
    lista=[]
    
    lista_pols = ['MP25','MP10','CO','O3','NO2','SO2','PTS']
    
    lista_regex = ['OUT','CO','NO2','O3IQAR','UVIQAR','MP25',
                   'COIQAR','IQAR','MP10IQAR','MP25IQAR','O3',
                   'MP10','SO2','NO2IQAR','PTS','UV','IN']
    
    lista_negada = "|".join(lista_regex)
    
    padrao = rf"^[A-Z]{{2}}_(.*?)(?=_(?:\d|{lista_negada}))"
    
    for item in files:
        
        if 'csv' in item:
            
            pol = item.split('_')[-2]
            
            if pol in lista_pols:
                
                estacao = re.search(padrao, item)
                
                lista.append(estacao.group(1).replace("_", " "))
                
                df = pd.read_csv(path+item)
                
                pol = tabela_pols.loc[tabela_pols['POLUENTE'] == pol, 'NOME_PASTA'].values[0]
                
                estacao = estacao.group(1).replace("_", " ")
                
                df['DATETIME'] = pd.to_datetime(df["DATETIME"])
                
                df.index = df['DATETIME']
                
                df = df.rename(columns={'CONC':'VALOR'})
                
                df = df.drop(columns=["COD"])
                
                dict_pols_stat[estacao+'_'+pol].append(df)
    
    dict_formatado = {}
    
    for chave in dict_pols_stat.keys():
        
        lista_dfs = dict_pols_stat[chave]
        
        df = pd.concat(lista_dfs, ignore_index=True)

        df["DATETIME"] = pd.to_datetime(df["DATETIME"])

        df = df.set_index("DATETIME")

        df = df.sort_index()
        
        lista_horas = pd.date_range(
            start=df.index.min(), 
            end=df.index.max(), 
            freq='H').strftime('%Y-%m-%d %H:%M:%S').tolist()
        
        if len(lista_horas) != len(df):
            df = df.reindex(pd.DatetimeIndex(lista_horas))
        
        df.insert(0, 'DATETIME', df.index)
        df.insert(1, 'ANO', df.index.year)
        df.insert(2, 'MES', df.index.month)
        df.insert(3, 'DIA', df.index.day)
        df.insert(4, 'HORA', df.index.hour)
        
        if chave.split('_')[-1] == 'CO':
            df['UNIDADE'] = 'ppm'
        else:
            df['UNIDADE'] = 'ug/m³'
        
        df['QAQC_INTERNO'] = None
        
        dict_formatado[chave] = df
        
    primeiros_valores = {}

    for chave, df in dict_formatado.items():
        
        if ~df['VALOR'].isna().all() and (df['VALOR'] > 0).any(): 
            
            linha_valida = df[df["VALOR"].notna() & (df["VALOR"] > 0)].iloc[0]
            primeiros_valores[chave] = linha_valida["DATETIME"]
    
    codigo_estacao_MA = {}
    
    for chave in primeiros_valores.keys():
        
        station = chave.split('_')[0]
        data = primeiros_valores[chave]
        
        if station in codigo_estacao_MA:
            if data <= codigo_estacao_MA[station]:
                codigo_estacao_MA[station] = data
        else:
            codigo_estacao_MA[station] = data
    
    sorted_items = sorted(
        codigo_estacao_MA.items(),
        key=lambda x: (x[1], x[0])
    )
    
    codigo_estacao_MA = {}
    for i, (nome, ts) in enumerate(sorted_items, start=1):
        codigo = f"MA{i:04d}"
        codigo_estacao_MA[nome] = codigo
        
    for chave, df in dict_formatado.items():
        
        estacao = codigo_estacao_MA[chave.split('_')[0]]
        
        cod_pol = tabela_pols.loc[tabela_pols['POLUENTE'] == chave.split('_')[-1], 'COD_POLUENTE'].values[0]
        
        nome_pasta = tabela_pols.loc[tabela_pols['COD_POLUENTE'] == int(cod_pol), 'NOME_PASTA'].values[0]

        df = create_QAQCMMA_VALOR(df,nome_pasta)
        
        df.to_csv('/home/nobre/Notebooks/RQAR_2025_book/data/MQAr/'+nome_pasta+'/'+estacao+'RA'+str(int(cod_pol)).zfill(3)+'.csv',index=False)

    df_ids = pd.DataFrame({
    'ID_OEMA': codigo_estacao_MA.keys(),
    'ID_MMA':list(codigo_estacao_MA.values())})
    
    return df_ids

#%% Função para Mato Grosso

def ppb_to_ug(df,pol):

    if pol == 'so2':

        df.loc[df["Unidade"] != "ug/m3", "Valor"] *= 2661260.49/10**6        

    elif pol == 'no2':

        df.loc[df["Unidade"] != "ug/m3", "Valor"] *= 1911038.92/10**6        

    elif pol == 'o3':

        df.loc[df["Unidade"] != "ug/m3", "Valor"] *= 1993889.17/10**6        
    
    df.loc[:, "Unidade"] = "ug/m3"

    return df

def rectify_MT(path):

    dict_pols_stat = defaultdict(list)

    files = os.listdir(path)
    
    print(files)
    
    for item in files:

        if item != '.ipynb_checkpoints':
        
            estacao = " ".join(item.split('-')[1].split('.')[0].split('_')[0:2])
        
            print(estacao)
        
            df = pd.read_excel(path+item)
        
            df = df.drop(columns=['Nome da estação'])
        
            lista_pols = set(df['Poluente'])
        
            for pol in lista_pols:
        
                df_pol = df[df["Poluente"] == pol]
                
                if pol in ['no2','so2','o3']:
        
                    df_pol = ppb_to_ug(df_pol,pol)
        
                df_pol_hora = df_pol.groupby(["Ano", "Mes", "Dia", "Hora", "Unidade"])
                
                df_pol_hora = df_pol_hora.filter(lambda g: len(g) >= 9)
                
                df_pol = (
                    df_pol_hora.groupby(["Ano", "Mes", "Dia", "Hora", "Unidade"], as_index=False)
                          .agg({"Valor": "mean"})
                )
        
                df_pol['QAQC_INTERNO'] = None
        
                df_pol = df_pol.rename(columns={'Ano':'ANO',
                                                'Mes':'MES',
                                                'Dia':'DIA',
                                                'Hora':'HORA',
                                                'Unidade':'UNIDADE',
                                                'Valor':'VALOR'})
        
                for col in ["ANO", "MES", "DIA", "HORA"]:
                    df_pol[col] = pd.to_numeric(df_pol[col], errors="coerce").astype("Int64")
                
                dict_pols_stat[estacao+'_'+pol].append(df_pol)

    dict_pols_MT = {
        'co':'CO',
        'no2': 'NO2',
        'so2': 'SO2',
        'o3': 'O3',
        'pm2p5':'MP25',
        'pm10': 'MP10'
    }

    dict_formatado = {}
    
    for chave in dict_pols_stat.keys():
        
        lista_dfs = dict_pols_stat[chave]
        
        df = pd.concat(lista_dfs, ignore_index=True)
    
        df["DATETIME"] = pd.to_datetime(
            df.apply(lambda r: f"{r.ANO}-{r.MES}-{r.DIA} {r.HORA}:00:00", axis=1)
        )
        df = df.set_index("DATETIME")
    
        df = df.sort_index()
        
        lista_horas = pd.date_range(
            start=df.index.min(), 
            end=df.index.max(), 
            freq='H').strftime('%Y-%m-%d %H:%M:%S').tolist()
        
        if len(lista_horas) != len(df):
            df = df.reindex(pd.DatetimeIndex(lista_horas))
    
        df['DATETIME'] = df.index
    
        df = df[['DATETIME','ANO','MES','DIA','HORA','VALOR','UNIDADE','QAQC_INTERNO']]
        
        dict_formatado[chave] = df
        
        primeiros_valores = {}
    
    for chave, df in dict_formatado.items():
        
        if ~df['VALOR'].isna().all() and (df['VALOR'] > 0).any(): 
            
            linha_valida = df[df["VALOR"].notna() & (df["VALOR"] > 0)].iloc[0]
            primeiros_valores[chave] = linha_valida["DATETIME"]
    
    codigo_estacao_MT = {}
    
    for chave in primeiros_valores.keys():
        
        station = chave.split('_')[0]
        data = primeiros_valores[chave]
        
        if station in codigo_estacao_MT:
            if data <= codigo_estacao_MT[station]:
                codigo_estacao_MT[station] = data
        else:
            codigo_estacao_MT[station] = data
    
    sorted_items = sorted(
        codigo_estacao_MT.items(),
        key=lambda x: (x[1], x[0])
    )
    
    codigo_estacao_MT = {}
    for i, (nome, ts) in enumerate(sorted_items, start=1):
        codigo = f"MT{i:04d}"
        codigo_estacao_MT[nome] = codigo
        
    for chave, df in dict_formatado.items():
        
        estacao = codigo_estacao_MT[chave.split('_')[0]]
        
        cod_pol = tabela_pols.loc[tabela_pols['POLUENTE'] == dict_pols_MT[chave.split('_')[-1]], 'COD_POLUENTE'].values[0]
        
        nome_pasta = tabela_pols.loc[tabela_pols['COD_POLUENTE'] == int(cod_pol), 'NOME_PASTA'].values[0]

        df = create_QAQCMMA_VALOR(df,nome_pasta)
        
        df.to_csv('/home/nobre/Notebooks/RQAR_2025_book/data/MQAr/'+nome_pasta+'/'+estacao+'IA'+str(int(cod_pol)).zfill(3)+'.csv',index=False)

    dict_stations_MT = {
        'Sema':'CPA - SEMA - CBA',
        'BEA CBA': 'Dom Aquino - BEA - CBA',
        'CBM VG': 'Água Limpa - CBM - VG',
        'Mae Bonifacia': 'Duque de Caxias - Pq Mãe Bonifácia - CBA',
        'UFMT':'Boa Esperança - UFMT - CBA'
    }
    
    df_ids = pd.DataFrame({
        'ID_OEMA': codigo_estacao_MT.keys(),
        'ID_MMA':list(codigo_estacao_MT.values())})
    
    df_ids["ID_OEMA"] = df_ids["ID_OEMA"].replace(dict_stations_MT)

    print(df_ids)
    
    return df_ids

#%% Função para DF

def fix_24h(row):
    if isinstance(row, str) and row.startswith("24:"):
        # substitui 24: por 00:
        new_str = row.replace("24:", "00:", 1)
        # converte para datetime
        dt = pd.to_datetime(new_str, errors="coerce")
        # adiciona 1 dia
        if pd.notna(dt):
            dt += timedelta(days=1)
        return dt
    else:
        return pd.to_datetime(row, errors="coerce")

def rectify_DF(path):

    path = path + 'Monitor Report 2024_FINAL.xlsx'
    
    df = pd.read_excel(path)
    
    df.iloc[1] = df.iloc[1].ffill()
    
    poluentes = ['CO_ppm','NO2_ug/m3','NO_ug/m3','NOx_ug/m3','O3_ug/m3','PM10','PM25','PTS','SO2_ug/m3']
    
    dict_pols = {'CO_ppm':'CO',
                 'NO2_ug/m3':'NO2',
                 'NO_ug/m3':'NO',
                 'NOx_ug/m3':'NOX',
                 'O3_ug/m3':'O3',
                 'PM10':'MP10',
                 'PM25':'MP25',
                 'PTS':'PTS',
                 'SO2_ug/m3':'SO2'}
    
    df.columns = df.iloc[1]
    
    df = df.drop(index=[0, 1]).reset_index(drop=True)
    
    df = df.rename(columns={'Date Time':'DATETIME'})
    
    estacoes = set(df.columns[1:])
    
    dict_pols_stat = defaultdict(list)
    
    for estacao in estacoes:
    
        df_estacao = df[["DATETIME",estacao]]
    
        df_estacao.columns = [df_estacao.columns.tolist()[0]] + df_estacao.iloc[0, 1:].tolist()
    
        df_estacao = df_estacao.drop(index=[0]).reset_index(drop=True)
    
        for pol in poluentes:
    
            if pol in df_estacao.columns:
                
                df_pol = df_estacao[["DATETIME",pol]]
    
                df_pol['UNIDADE'] = df_pol[pol][0]
    
                df_pol = df_pol.drop(index=[0]).reset_index(drop=True)
    
                df_pol = df_pol[df_pol["DATETIME"].astype(str).str.contains(r"\d", na=False)].reset_index(drop=True)
    
                df_pol['DATETIME'] = df_pol['DATETIME'].apply(fix_24h)
    
                df_pol = df_pol.rename(columns={pol:'VALOR'})
    
                df_pol.index = df_pol['DATETIME']
    
                lista_horas = pd.date_range(
                    start=df_pol.index.min(), 
                    end=df_pol.index.max(), 
                    freq='H').strftime('%Y-%m-%d %H:%M:%S').tolist()
                
                if len(lista_horas) != len(df_pol):
                    df_pol = df_pol.reindex(pd.DatetimeIndex(lista_horas))
                
                df_pol['QAQC_INTERNO'] = None
                
                df_pol.insert(1, 'ANO', df_pol.index.year)
                df_pol.insert(2, 'MES', df_pol.index.month)
                df_pol.insert(3, 'DIA', df_pol.index.day)
                df_pol.insert(4, 'HORA', df_pol.index.hour)
    
                pol = dict_pols[pol]
    
                df_pol['VALOR'] = pd.to_numeric(df_pol['VALOR'], errors='coerce')
    
                df_pol = df_pol[['DATETIME','ANO','MES','DIA','HORA','VALOR','UNIDADE','QAQC_INTERNO']] 
    
                dict_pols_stat[estacao+'_'+pol] = df_pol

    primeiros_valores = {}

    for chave, df in dict_pols_stat.items():  
        
        if ~df['VALOR'].isna().all() and (df['VALOR'] > 0).any(): 
            
            linha_valida = df[df["VALOR"].notna() & (df["VALOR"] > 0)].iloc[0]
            primeiros_valores[chave] = linha_valida["DATETIME"]
    
    codigo_estacao_DF = {}
    
    for chave in primeiros_valores.keys():
        
        station = chave.split('_')[0]
        data = primeiros_valores[chave]
        
        if station in codigo_estacao_DF:
            if data <= codigo_estacao_DF[station]:
                codigo_estacao_DF[station] = data
        else:
            codigo_estacao_DF[station] = data
    
    sorted_items = sorted(
        codigo_estacao_DF.items(),
        key=lambda x: (x[1], x[0])
    )
    
    codigo_estacao_DF = {}
    for i, (nome, ts) in enumerate(sorted_items, start=1):
        codigo = f"DF{i:04d}"
        codigo_estacao_DF[nome] = codigo
        
    for chave, df in dict_pols_stat.items():
        
        estacao = codigo_estacao_DF[chave.split('_')[0]]
        
        cod_pol = tabela_pols.loc[tabela_pols['POLUENTE'] == chave.split('_')[-1], 'COD_POLUENTE'].values[0]
        
        nome_pasta = tabela_pols.loc[tabela_pols['COD_POLUENTE'] == int(cod_pol), 'NOME_PASTA'].values[0]

        df = create_QAQCMMA_VALOR(df,nome_pasta)
        
        df.to_csv('/home/nobre/Notebooks/RQAR_2025_book/data/MQAr/'+nome_pasta+'/'+estacao+'RS'+str(int(cod_pol)).zfill(3)+'.csv',index=False)
    
    dict_oema = {
        'Estação CRAS FERCAL': 'Fercal CRAS',
        'Estação Escola':	   'Fercal Escola'}
    
    df_ids = pd.DataFrame({
        'ID_OEMA': codigo_estacao_DF.keys(),
        'ID_MMA':list(codigo_estacao_DF.values())})
    
    df_ids['ID_OEMA'] = df_ids['ID_OEMA'].replace(dict_oema)
    
    return df_ids
#%% Função Pernambuco
    
def rectify_PE(path):
    import glob
    import os
    import re
    import numpy as np
    import pandas as pd
    from collections import defaultdict

    # Localiza todos os arquivos Excel dentro da pasta PE
    arquivos = sorted(glob.glob(os.path.join(path, '*.xls*')))
    if not arquivos:
        raise FileNotFoundError(f"Nenhum arquivo Excel encontrado em {path}")

    print(f"📂 Encontrados {len(arquivos)} arquivos em {path}")

    dict_pols_stat_global = defaultdict(lambda: pd.DataFrame())

    for arq in arquivos:

        if arq != '.ipynb_checkpoints':
            
            ano = re.search(r'\d{4}', os.path.basename(arq))
            ano_txt = ano.group(0) if ano else "?"
            print(f"🔹 Processando: {os.path.basename(arq)} (ano {ano_txt})")
    
            try:
                df = pd.read_excel(arq)
            except Exception as e:
                print(f"⚠️ Erro ao ler {arq}: {e}")
                continue
    
            # ======== Cabeçalhos e estrutura básica ========
            df.iloc[1] = df.iloc[1].ffill()
            df.columns = df.iloc[1]
            df = df.drop(index=[0, 1]).reset_index(drop=True)
            df = df.rename(columns={'Date Time': 'DATETIME'})
    
            poluentes = ['CO_ppm', 'NO2_ug/m3', 'NO_ug/m3', 'NOx_ug/m3',
                         'O3_ug/m3', 'PM10', 'PM25', 'PTS', 'SO2_ug/m3']
            dict_pols = {'CO_ppm': 'CO', 'NO2_ug/m3': 'NO2', 'NO_ug/m3': 'NO',
                         'NOx_ug/m3': 'NOX', 'O3_ug/m3': 'O3', 'PM10': 'MP10',
                         'PM25': 'MP25', 'PTS': 'PTS', 'SO2_ug/m3': 'SO2'}
    
            estacoes = set(df.columns[1:])
            dict_pols_stat = defaultdict(pd.DataFrame)
    
            for estacao in estacoes:
                df_estacao = df[['DATETIME', estacao]].copy()
    
                # Extrai colunas de poluentes
                df_estacao.columns = [df_estacao.columns.tolist()[0]] + df_estacao.iloc[0, 1:].tolist()
                df_estacao = df_estacao.drop(index=[0]).reset_index(drop=True)
    
                for pol in poluentes:
                    if pol in df_estacao.columns:
                        df_pol = df_estacao[['DATETIME', pol]].copy()
                        df_pol['UNIDADE'] = df_pol[pol].iloc[0]
                        df_pol = df_pol.drop(index=[0]).reset_index(drop=True)
                        df_pol = df_pol[df_pol['DATETIME'].astype(str).str.contains(r"\d", na=False)].reset_index(drop=True)
    
                        # Conserta "24:" → "00:" e converte para datetime
                        df_pol['DATETIME'] = df_pol['DATETIME'].apply(fix_24h)
                        df_pol['DATETIME'] = pd.to_datetime(df_pol['DATETIME'], errors='coerce')
                        df_pol = df_pol.dropna(subset=['DATETIME'])
    
                        df_pol = df_pol.rename(columns={pol: 'VALOR'})
                        df_pol['VALOR'] = pd.to_numeric(df_pol['VALOR'], errors='coerce')
    
                        # ========= Garantia de sequência horária completa =========
                        df_pol = df_pol.set_index('DATETIME').sort_index()
                        horas_completas = pd.date_range(df_pol.index.min(), df_pol.index.max(), freq='H')
                        df_pol = df_pol.reindex(horas_completas)
    
                        # Preenche unidade e cria QAQC
                        for col in ['UNIDADE']:
                            if col in df_pol.columns:
                                df_pol[col] = df_pol[col].ffill().bfill()
    
                        df_pol['QAQC_INTERNO'] = np.where(df_pol['VALOR'].isna(), 'Inválido', 'OK')
    
                        # Colunas auxiliares
                        df_pol['ANO'] = df_pol.index.year
                        df_pol['MES'] = df_pol.index.month
                        df_pol['DIA'] = df_pol.index.day
                        df_pol['HORA'] = df_pol.index.hour
    
                        df_pol = df_pol.reset_index().rename(columns={'index': 'DATETIME'})
                        df_pol = df_pol[['DATETIME', 'ANO', 'MES', 'DIA', 'HORA', 'VALOR', 'UNIDADE', 'QAQC_INTERNO']]
    
                        pol_sigla = dict_pols[pol]
                        chave = f"{estacao}_{pol_sigla}"
                        dict_pols_stat[chave] = df_pol
    
            # ======== Acumula todos os anos (concatena) ========
            for chave, df_parcial in dict_pols_stat.items():
                dict_pols_stat_global[chave] = pd.concat(
                    [dict_pols_stat_global[chave], df_parcial],
                    ignore_index=True
                )

    # ======== Criação de IDs e exportação ========
    primeiros_valores = {}
    for chave, df in dict_pols_stat_global.items():
        if not df['VALOR'].isna().all() and (df['VALOR'] > 0).any():
            linha_valida = df[df['VALOR'].notna() & (df['VALOR'] > 0)].iloc[0]
            primeiros_valores[chave] = linha_valida['DATETIME']

    codigo_estacao_PE = {}
    for chave, data in primeiros_valores.items():
        station = chave.split('_')[0]
        if station in codigo_estacao_PE:
            if data <= codigo_estacao_PE[station]:
                codigo_estacao_PE[station] = data
        else:
            codigo_estacao_PE[station] = data

    sorted_items = sorted(codigo_estacao_PE.items(), key=lambda x: (x[1], x[0]))
    codigo_estacao_PE = {nome: f"PE{i:04d}" for i, (nome, _) in enumerate(sorted_items, start=1)}

    # ======== Salva os CSVs por poluente ========
    for chave, df in dict_pols_stat_global.items():
        estacao = codigo_estacao_PE.get(chave.split('_')[0], 'PE9999')
        pol = chave.split('_')[-1]

        cod_pol = tabela_pols.loc[tabela_pols['POLUENTE'] == pol, 'COD_POLUENTE'].values[0]
        nome_pasta = tabela_pols.loc[tabela_pols['COD_POLUENTE'] == int(cod_pol), 'NOME_PASTA'].values[0]

        df = create_QAQCMMA_VALOR(df, nome_pasta)

        df.to_csv(
            f'/home/nobre/Notebooks/RQAR_2025_book/data/MQAr/{nome_pasta}/{estacao}ND{int(cod_pol):03d}.csv',
            index=False
        )

    # ======== Cria e retorna df_ids ========
    df_ids = pd.DataFrame({
        'ID_OEMA': codigo_estacao_PE.keys(),
        'ID_MMA': list(codigo_estacao_PE.values())
    })

    df_ids.to_csv(f'/home/nobre/Notebooks/RQAR_2025_book/data/DADOS_ESTACOES/teste_id_mma_oema_PE.csv')

    print(f"\n✅ {len(df_ids)} estações processadas em Pernambuco")
    print("\n📋 Mapeamento Estação → Código MMA:")
    for k, v in codigo_estacao_PE.items():
        print(f"{v} → {k}")

    return df_ids



#%% Função para Roraima (RR)


def rectify_RR(path):
    
    # 1. Configuração e Busca
    target_file = "Medições (29).xlsx"
    path_dir = Path(path)
    files = [f for f in os.listdir(path_dir) if f.endswith((".xls", ".xlsx"))]

    if not files:
        print(f"⚠️ Aviso: Nenhum arquivo Excel encontrado em {path_dir}")
        return pd.DataFrame(columns=['ID_OEMA', 'POLUENTE', 'ID_MMA', 'ID_MMA_COMPLETO'])

    pasta_saida_raiz = '/home/nobre/Notebooks/RQAR_2025_book/data/MQAr/'

    codigos_pols_RR = {
        'Partículas Respiráveis (<2,5µm)': 'MP25',
        'Monóxido de Carbono': 'CO',
        'Dióxido de Nitrogênio': 'NO2',
        'Óxidos de Nitrogênio': 'NOX',
        'Ozônio': 'O3',
        'Hidrocarbonetos Totais': 'HCT',
        'Hidrocarbonetos Não Metano': 'HCNM',
        'Metano': 'CH4',
        'Dióxido de Enxofre': 'SO2',
        'Partículas Inaláveis (<10µm)': 'MP10',
        'Monóxido de Nitrogênio': 'NO'
    }

    stations_map = {
        'Estação Fazenda Carolina': 'RR0001',
        'Estação FEMARH': 'RR0002'
    }

    df_ids_list = []
    
    # 2. Loop sobre os arquivos Excel
    for item in files:
        print(f"🔹 Processando: {item}")
        fpath = path_dir / item
        
        try:
            # Lê o Excel com headers [1, 4]
            df_multi = pd.read_excel(fpath, header=[1, 4])
            df_multi = df_multi.dropna(axis=1, how="all")
        except Exception as e:
            print(f"⚠️ Erro ao ler o arquivo {item}: {e}")
            continue

        # 3. Tratamento da Coluna DATETIME
        
        # 3a. Encontra a chave completa da coluna de data e hora
        col_tempo_key = None
        for c in df_multi.columns:
            if isinstance(c, tuple) and 'Data e Hora' in c[0]:
                col_tempo_key = c
                break
        
        if col_tempo_key is None:
             col_tempo_key = df_multi.columns[0] # Recorre à primeira coluna MultiIndex ou simples
        
        # 3b. Extrai a coluna de DATETIME (série de dados)
        # Usamos df_multi[col_tempo_key] para extrair os dados de forma segura,
        # pois 'col_tempo_key' é a chave MultiIndex correta.
        datetime_data = pd.to_datetime(df_multi[col_tempo_key], errors='coerce')
        
        # 3c. Renomeia o nível 0 do cabeçalho da coluna de tempo para 'DATETIME'
        df_multi.rename(columns={col_tempo_key[0]: "DATETIME"}, level=0, inplace=True)
        
        # 4. Loop sobre as Estações
        for est_nome, id_mma in stations_map.items():
            
            try:
                # 4a. Isola o bloco de dados da estação (mantém o MultiIndex)
                bloco_estacao = df_multi.xs(est_nome, axis=1, level=0, drop_level=False)
                
                # 4b. Cria um DataFrame com a nova coluna DATETIME e os dados da Estação.
                # Achata o cabeçalho do bloco de estações para o nome do poluente (nível 1).
                # Reinicia a construção do DataFrame com a série de dados DATETIME.
                bloco = pd.DataFrame({'DATETIME': datetime_data}).reset_index(drop=True)
                bloco_estacao.columns = bloco_estacao.columns.droplevel(0)
                
                # Junta o DATETIME com o bloco de estações (usando index resetado)
                bloco = pd.concat([bloco, bloco_estacao.reset_index(drop=True)], axis=1)

            except KeyError:
                continue

            bloco = bloco.dropna(subset=['DATETIME'])
            
            # 5. Loop sobre os Poluentes
            for pol_texto, pol_sigla in codigos_pols_RR.items():
                
                col_match = [c for c in bloco.columns if pol_texto in c]
                if not col_match: continue

                value_col_name = [c for c in col_match if 'Flag' not in c and 'Unidade' not in c and c != 'DATETIME']
                if not value_col_name: continue
                value_col_name = value_col_name[0]
                
                col_flag = [
                    c for c in bloco.columns 
                    if ('Flag' in c or 'FLAG' in c) and pol_texto.split('(')[0].strip() in c[0]
                ]

                df_pol = bloco[["DATETIME", value_col_name]].copy()
                df_pol.rename(columns={value_col_name: 'VALOR'}, inplace=True)
                
                df_pol['QAQC_INTERNO'] = bloco[col_flag[0]] if col_flag else np.nan
                if not col_flag:
                    print(f"⚠️ Nenhuma coluna de flag encontrada para {pol_texto} em {est_nome}")

                
                match_unit = re.search(r'\((.*?)\)', pol_texto)
                unit = match_unit.group(1).replace('µ', 'u') if match_unit else 'Nao declarado'
                df_pol['UNIDADE'] = unit.replace('[', '').replace(']', '')

                df_pol['VALOR'] = pd.to_numeric(df_pol['VALOR'], errors='coerce')
                
                df_pol = df_pol.dropna(subset=['DATETIME']).set_index('DATETIME').sort_index()
                
                # Reindexa para série horária completa e adiciona colunas de tempo
                full_range = pd.date_range(df_pol.index.min(), df_pol.index.max(), freq='h')
                df_pol = df_pol.reindex(full_range).reset_index().rename(columns={'index': 'DATETIME'})
                
                df_pol['ANO'] = df_pol['DATETIME'].dt.year
                df_pol['MES'] = df_pol['DATETIME'].dt.month
                df_pol['DIA'] = df_pol['DATETIME'].dt.day
                df_pol['HORA'] = df_pol['DATETIME'].dt.hour
                

                # Aplica QAQC (depende de tabela_pols global)
                nome_pasta = tabela_pols.loc[tabela_pols['POLUENTE'] == pol_sigla, 'NOME_PASTA'].iloc[0]
                df_pol_filtrado = create_QAQCMMA_VALOR(df_pol.copy(), pol_sigla)
                
                # ======= PRINTS DE VERIFICAÇÃO =======
                total = len(df_pol)
                validos = df_pol_filtrado['QAQC_MMA'].sum()
                invalidos = total - validos
                pct = (validos / total * 100) if total > 0 else 0
                print(f"   🔎 {pol_sigla}: {validos}/{total} válidos ({pct:.1f}%) — {invalidos} removidos")
                
                # Substitui o df original pelo filtrado
                df_pol = df_pol_filtrado


                # Determina ID_MMA_COMPLETO (depende de tabela_ids global)
                cod_pol_val = tabela_pols.loc[tabela_pols['POLUENTE'] == pol_sigla, 'COD_POLUENTE'].iloc[0]
                meta_match = tabela_ids.loc[(tabela_ids["ID_MMA"] == id_mma) & (tabela_ids["POLUENTE"] == pol_sigla), "ID_MMA_COMPLETO"]
                
                if not meta_match.empty:
                     id_mma_completo = meta_match.iloc[0]
                else:
                     id_mma_completo = f"{id_mma}RA{int(cod_pol_val):03d}"
                
                # 6. Salva o arquivo CSV no caminho padrão
                pasta_destino = Path(pasta_saida_raiz) / nome_pasta
                pasta_destino.mkdir(parents=True, exist_ok=True)
                
                df_final_save = df_pol[['DATETIME', 'ANO', 'MES', 'DIA', 'HORA', 'VALOR', 'VALOR_ORIGINAL', 'UNIDADE', 'QAQC_INTERNO', 'QAQC_MMA']]
                
                output_filepath = pasta_destino / f'{id_mma_completo}.csv'
                df_final_save.to_csv(output_filepath, index=False)
                
                df_ids_list.append({
                    "ID_OEMA": est_nome,
                    "POLUENTE": pol_sigla,
                    "ID_MMA": id_mma,
                    "ID_MMA_COMPLETO": id_mma_completo
                })
        
    # 7. Retorna o DataFrame de IDs
    df_ids = pd.DataFrame(df_ids_list)
    df_ids = df_ids.drop_duplicates(subset=["ID_MMA", "ID_OEMA"]).reset_index(drop=True)
    return df_ids
  
    
#%% Função Ceará
def padronizar_horas(df, nome_df="df"):
    """
    Padroniza coluna DATETIME e cria intervalo horário completo (hora a hora)
    """
    df = df.rename(columns={df.columns[0]: 'DATETIME'})
    df['DATETIME'] = pd.to_datetime(df['DATETIME'], errors='coerce')
    df = df.dropna(subset=['DATETIME'])

    if df.empty:
        print(f"⚠️ {nome_df} está vazio após remover datas inválidas!")
        return df
    
    full_range = pd.date_range(start=df['DATETIME'].min(), end=df['DATETIME'].max(), freq='h')
    df = df.set_index('DATETIME').reindex(full_range).reset_index()
    df = df.rename(columns={'index': 'DATETIME'})
    print(f"✅ {nome_df} atualizado: {len(df)} linhas com horas consecutivas")
    return df

def adicionar_colunas_data(df):
    """
    Adiciona colunas ANO, MES, DIA, HORA após DATETIME
    """
    df['DATETIME'] = pd.to_datetime(df['DATETIME'], errors='coerce')
    df['ANO'] = df['DATETIME'].dt.year
    df['MES'] = df['DATETIME'].dt.month
    df['DIA'] = df['DATETIME'].dt.day
    df['HORA'] = df['DATETIME'].dt.hour

    cols = df.columns.tolist()
    novas_colunas = ['DATETIME', 'ANO', 'MES', 'DIA', 'HORA']
    outras_colunas = [col for col in cols if col not in novas_colunas]
    return df[novas_colunas + outras_colunas]

def gerar_arquivos_estacoes_poluentes(dfs_alvo, UF_estacoes, df_cod_pol, pasta_saida):
    """
    Gera arquivos CSV por estação e poluente com QAQC
    """
    for nome_var in dfs_alvo:
        if nome_var not in globals():
            continue

        df_estacao = globals()[nome_var].copy()
        id_oema = nome_var.replace("df_", "").replace("_", " ").strip()

        # Buscar o ID_MMA correspondente
        id_mma = UF_estacoes.loc[UF_estacoes['ID_OEMA'].str.lower() == id_oema.lower(), 'ID_MMA']
        if id_mma.empty:
            print(f"⚠️ ID_MMA não encontrado para {id_oema}")
            continue
        id_mma = id_mma.iloc[0]

        colunas_poluentes = df_estacao.columns[5:]

        for col in colunas_poluentes:
            if df_estacao[col].dropna().eq('').all():
                print(f"⏭️ Pulando {col} em {id_oema} (sem dados válidos)")
                continue

            nome_poluente_col = re.sub(r"\(.*\)", "", col).strip()
            unidade = ""
            match_unidade = re.search(r"\((.*?)\)", col)
            if match_unidade:
                unidade = match_unidade.group(1)

            linha_pol = df_cod_pol[df_cod_pol['POLUENTE'].str.upper().str.strip() == nome_poluente_col.upper()]
            if linha_pol.empty:
                print(f"⚠️ Poluente {nome_poluente_col} não encontrado em CODIGO_POLUENTES.csv")
                continue

            cod_pol = linha_pol['COD_POLUENTE'].iloc[0].zfill(3)
            nome_pasta = linha_pol['NOME_PASTA'].iloc[0]

            pasta_destino = os.path.join(pasta_saida, nome_pasta)
            os.makedirs(pasta_destino, exist_ok=True)

            df_saida = pd.DataFrame({
                'DATETIME': df_estacao['DATETIME'],
                'ANO': df_estacao['ANO'],
                'MES': df_estacao['MES'],
                'DIA': df_estacao['DIA'],
                'HORA': df_estacao['HORA'],
                'VALOR_ORIGINAL': df_estacao[col],
                'UNIDADE': unidade,
                'QAQC_INTERNO': df_estacao[col],
                'QAQC_MMA': df_estacao[col]
            })

            df_saida = create_QAQCMMA_VALOR(df_saida, nome_poluente_col)

            nome_arquivo = f"{id_mma}ND{cod_pol}".replace("_", "") + ".csv"
            caminho_saida = os.path.join(pasta_destino, nome_arquivo)
            df_saida.to_csv(caminho_saida, index=False, sep=',', encoding='utf-8-sig')
            print(f"💾 Arquivo criado: {caminho_saida}")
            
def rectify_CE(path):
    import pandas as pd
    import os, glob, re, csv

    # Caminhos fixos
    arquivo_estacoes = "/home/nobre/Notebooks/RQAR_2025_book/data/DADOS_ESTACOES/CE_estacoes.csv"
    UF_estacoes = pd.read_csv(arquivo_estacoes, sep=',', dtype=str)

    codigos = r"/home/nobre/Notebooks/RQAR_2025_book/data/dicionarios/CODIGO_POLUENTES.csv"
    df_cod_pol = pd.read_csv(codigos, sep=',', dtype=str).drop(columns=['NOME_TEXTO'], errors='ignore')

    pasta = r"/home/nobre/Notebooks/RQAR_2025_book/data/DADOS_BRUTOS/CE"
    dados_brutos_CE = glob.glob(os.path.join(pasta, "*.csv"))

    dfs_alvo = []

    # Ler CSVs e criar DataFrames globais
    for caminho in dados_brutos_CE:
        nome_arquivo = os.path.splitext(os.path.basename(caminho))[0]
        nome_variavel = re.sub(r'\W+', '_', nome_arquivo)

        # Detectar delimitador automaticamente
        with open(caminho, 'r', encoding='utf-8', errors='ignore') as f:
            amostra = f.read(2048)
            f.seek(0)
            try:
                delimitador = csv.Sniffer().sniff(amostra).delimiter
            except:
                delimitador = ','

        # Ler CSV
        df_temp = pd.read_csv(caminho, sep=delimitador, dtype=str)
        globals()[f"df_{nome_variavel}"] = df_temp
        dfs_alvo.append(f"df_{nome_variavel}")
        print(f"✅ Criado DataFrame: df_{nome_variavel} (sep='{delimitador}', {len(df_temp)} linhas, {len(df_temp.columns)} colunas)")

    # Padronizar horas, adicionar colunas e converter unidades
    for nome_var in dfs_alvo:
        df = globals()[nome_var]

        # Padronizar horas
        df = padronizar_horas(df, nome_var)
        if df.empty:
            print(f"⚠️ {nome_var} ficou vazio após padronizar horas. Pulando...")
            continue

        df = adicionar_colunas_data(df)

        # Colunas de poluentes (a partir da 6ª coluna)
        colunas_poluentes = df.columns[5:]

        print(colunas_poluentes)

        for col in colunas_poluentes:
            print(col)
            if col == 'CO(µg/m³)':
                print(col)
            
                df_temp = pd.DataFrame({
                    "VALOR": pd.to_numeric(df[col], errors="coerce"),
                    "UNIDADE": "µg/m³"
                })

                df_temp = ug_to_ppm(df_temp)

                df[col] = df_temp["VALOR"]
                df[f"{col}_UNIDADE"] = df_temp["UNIDADE"]

                # Debug opcional
                print(f"🔁 Conversão concluída para {col} (amostra):")
                print(df_temp.head(3))

        # Atualiza o DataFrame global
        globals()[nome_var] = df

    # Pasta de saída
    pasta_saida = r"/home/nobre/Notebooks/RQAR_2025_book/data/MQAr"
    gerar_arquivos_estacoes_poluentes(dfs_alvo, UF_estacoes, df_cod_pol, pasta_saida)

    print("✅ Processamento do Ceará concluído com sucesso!")

    # 🔁 Retorno necessário para o CreateSheetEstados.py
    return UF_estacoes


def rectify_PB(path):
    #--------------------------------------------------------
    # Caminhos
    #--------------------------------------------------------
    arquivo_estacoes = "/home/nobre/Notebooks/RQAR_2025_book/data/DADOS_ESTACOES/PB_estacoes.csv"
    arquivo_cod_pol = "/home/nobre/Notebooks/RQAR_2025_book/data/dicionarios/CODIGO_POLUENTES.csv"
    pasta_dados = "/home/nobre/Notebooks/RQAR_2025_book/data/DADOS_BRUTOS/PB"
    pasta_saida = "/home/nobre/Notebooks/RQAR_2025_book/data/MQAr"

    #--------------------------------------------------------
    # Carregar bases auxiliares
    #--------------------------------------------------------
    UF_estacoes = pd.read_csv(arquivo_estacoes, sep=',', dtype=str)
    df_cod_pol = pd.read_csv(arquivo_cod_pol, sep=',', dtype=str)
    df_cod_pol = df_cod_pol.drop(columns=['NOME_TEXTO'], errors='ignore')

    #--------------------------------------------------------
    # Ler dados brutos
    #--------------------------------------------------------
    arquivos_txt = glob.glob(os.path.join(pasta_dados, "*.txt"))
    colunas = [
        "Data", "Serial", "Nome do Órgão",
        "PTS", "PM10", "PM25", "PM1", "Voltagem da Bateria"
    ]

    dfs = {}
    for arquivo in arquivos_txt:
        nome_base = os.path.splitext(os.path.basename(arquivo))[0]
        nome_var = "df_" + re.sub(r'\W+', '_', nome_base)

        try:
            df = pd.read_csv(arquivo, sep=';', header=None, names=colunas, encoding='utf-8')
            dfs[nome_var] = df
            print(f"✅ DataFrame criado: {nome_var} ({len(df)} linhas)")
        except Exception as e:
            print(f"⚠️ Erro ao ler {arquivo}: {e}")

    #--------------------------------------------------------
    # Padronizar DATETIME e criar intervalo horário completo
    #--------------------------------------------------------
    for nome_var, df in dfs.items():
        dfs[nome_var] = padronizar_horas(df, nome_var)

    #--------------------------------------------------------
    # Adicionar colunas de tempo (ANO, MES, DIA, HORA)
    #--------------------------------------------------------
    for nome_var in dfs:
        dfs[nome_var] = adicionar_colunas_data(dfs[nome_var])
        print(f"✅ Colunas de tempo adicionadas: {nome_var}")

    #--------------------------------------------------------
    # Geração dos arquivos QAQC (usa funções já existentes)
    #--------------------------------------------------------
    gerar_arquivos_estacoes_poluentes_PB(dfs, UF_estacoes, df_cod_pol, pasta_saida)

    print("\n✅ Processamento completo para PB finalizado com sucesso!")
# Função MS

def carregar_estacoes(caminho_estacoes):
    """Carrega CSV de estações e retorna dataframe com ID_MMA e ID_OEMA"""
    UF_estacoes = pd.read_csv(caminho_estacoes, sep=',', dtype=str)
    UF_ID_MMA = UF_estacoes[['ID_MMA','ID_OEMA']].copy()
    return UF_ID_MMA

def carregar_codigos_poluentes(caminho_codigos):
    """Carrega CSV de códigos de poluentes e remove coluna NOME_TEXTO se existir"""
    df_cod_pol = pd.read_csv(caminho_codigos, sep=',', dtype=str)
    df_cod_pol = df_cod_pol.drop(columns=['NOME_TEXTO'], errors='ignore')
    return df_cod_pol

def ler_dados_brutos(pasta):
    """Lê todos CSVs de uma pasta e concatena em um único dataframe"""
    arquivos = glob.glob(os.path.join(pasta, "*.csv"))
    lista_dfs = []
    for caminho in arquivos:
        with open(caminho, 'r', encoding='utf-8', errors='ignore') as f:
            amostra = f.read(2048)
            f.seek(0)
            try:
                delimitador = csv.Sniffer().sniff(amostra).delimiter
            except:
                delimitador = ';'
        df_temp = pd.read_csv(caminho, sep=delimitador, dtype=str)
        lista_dfs.append(df_temp)
        print(f"✅ Lido: {os.path.basename(caminho)} ({len(df_temp)} linhas)")
    df = pd.concat(lista_dfs, ignore_index=True)
    print(f"\n✅ Base combinada: {len(df)} linhas\n")
    return df

def padronizar_datetime_por_estacao(df):
    """Cria coluna DATETIME contínua por estação e poluente"""
    dfs_resultado = []
    for estacao, df_est in df.groupby('Estação'):
        for poluente, df_pol in df_est.groupby('Sigla'):
            df_temp = df_pol.copy()
            df_temp['DATETIME'] = pd.to_datetime(df_temp['Data'] + ' ' + df_temp['Hora'], errors='coerce')
            df_temp = df_temp.dropna(subset=['DATETIME'])
            df_temp = df_temp.drop_duplicates(subset='DATETIME')
            df_temp = df_temp.set_index('DATETIME')
            all_hours = pd.date_range(start=df_temp.index.min(), end=df_temp.index.max(), freq='h')
            df_temp = df_temp.reindex(all_hours).reset_index().rename(columns={'index': 'DATETIME'})
            df_temp['ANO'] = df_temp['DATETIME'].dt.year
            df_temp['MES'] = df_temp['DATETIME'].dt.month
            df_temp['DIA'] = df_temp['DATETIME'].dt.day
            df_temp['HORA'] = df_temp['DATETIME'].dt.hour
            df_temp['Estação'] = estacao
            df_temp['Sigla'] = poluente
            dfs_resultado.append(df_temp)
    df_final = pd.concat(dfs_resultado, ignore_index=True)
    return df_final

def rectify_MS(path):
    import os
    import pandas as pd
    import numpy as np

    caminho_estacoes = '/home/nobre/Notebooks/RQAR_2025_book/data/DADOS_ESTACOES/MS_estacoes.csv'
    caminho_codigos = '/home/nobre/Notebooks/RQAR_2025_book/data/dicionarios/CODIGO_POLUENTES.csv'
    pasta_dados = '/home/nobre/Notebooks/RQAR_2025_book/data/DADOS_BRUTOS/MS'
    pasta_saida = '/home/nobre/Notebooks/RQAR_2025_book/data/MQAr'
    os.makedirs(pasta_saida, exist_ok=True)

    # Carregar dados usando funções externas
    UF_estacoes = carregar_estacoes(caminho_estacoes)
    df_cod_pol = carregar_codigos_poluentes(caminho_codigos)
    df_MS = ler_dados_brutos(pasta_dados)
    df_MS = padronizar_datetime_por_estacao(df_MS)

    # ---------------------------------------------------------
    # Conteúdo de gerar_arquivos_por_estacao() incorporado
    # ---------------------------------------------------------
    for estacao in df_MS['Estação'].dropna().unique():
        df_est = df_MS[df_MS['Estação'] == estacao].copy()
        id_mma = UF_estacoes.loc[UF_estacoes['ID_OEMA'].str.lower() == estacao.lower(), 'ID_MMA']
        if id_mma.empty:
            print(f"⚠️ ID_MMA não encontrado para estação: {estacao}")
            continue
        id_mma = id_mma.iloc[0]

        for sigla_pol in df_est['Sigla'].dropna().unique():
            df_pol = df_est[df_est['Sigla'] == sigla_pol].copy()
            linha_pol = df_cod_pol[df_cod_pol['POLUENTE'].str.upper().str.strip() == sigla_pol.upper()]
            if linha_pol.empty:
                print(f"⚠️ Poluente {sigla_pol} não encontrado")
                continue

            cod_pol = str(int(linha_pol['COD_POLUENTE'].iloc[0])).zfill(3)
            nome_pasta = linha_pol['NOME_PASTA'].iloc[0]
            pasta_destino = os.path.join(pasta_saida, nome_pasta)
            os.makedirs(pasta_destino, exist_ok=True)

            # Criar df_saida com QAQC_INTERNO e QAQC_MMA
            df_saida = pd.DataFrame({
                'DATETIME': df_pol['DATETIME'],
                'ANO': df_pol['ANO'],
                'MES': df_pol['MES'],
                'DIA': df_pol['DIA'],
                'HORA': df_pol['HORA'],
                'VALOR_ORIGINAL': df_pol.get('Valor Medido', np.nan),
                'UNIDADE': df_pol.get('Unidade', ''),
                'QAQC_INTERNO': df_pol.get('Valor Medido', np.nan),
                'QAQC_MMA': df_pol.get('Valor Medido', np.nan)
            })

            # Chama função QAQC externa
            df_saida = create_QAQCMMA_VALOR(df_saida, sigla_pol)

            # Salvar CSV
            nome_arquivo = f"{id_mma}ND{cod_pol}.csv"
            caminho_saida = os.path.join(pasta_destino, nome_arquivo)
            df_saida.to_csv(caminho_saida, index=False, sep=',', encoding='utf-8-sig')
            print(f"💾 Criado: {caminho_saida}")

    print("\n✅ Processamento de MS concluído!")



#%% Função Acre (PurpleAir) — versão final com detecção de codificação

def rectify_AC(path):
    """
    Processa arquivos CSV semanais do Acre (PurpleAir), unindo todos os anos
    e gerando um único arquivo por estação com dados horários padronizados.
    """
    import glob, os, re
    import pandas as pd
    import numpy as np
    from collections import defaultdict
    from datetime import timedelta

    # ======== Localiza arquivos CSV (todos os anos) ========
    arquivos = sorted(glob.glob(os.path.join(path, '*.csv')))
    if not arquivos:
        raise FileNotFoundError(f"Nenhum arquivo CSV encontrado em {path}")

    print(f"📂 {len(arquivos)} arquivos encontrados em {path}")

    # ======== Lê todos os arquivos e concatena ========
    df_total = pd.DataFrame()
    for arq in arquivos:
        print(f"🔹 Lendo: {os.path.basename(arq)}")
        try:
            # Tenta UTF-8 primeiro
            df = pd.read_csv(arq, encoding='utf-8')
        except UnicodeDecodeError:
            # Se falhar, tenta Latin-1 (Windows-1252)
            print(f"⚠️ Arquivo {os.path.basename(arq)} não está em UTF-8, tentando Latin-1...")
            df = pd.read_csv(arq, encoding='latin1')
        except Exception as e:
            print(f"❌ Erro ao ler {os.path.basename(arq)}: {e}")
            continue

        # Remove coluna SEMANA se existir
        if 'SEMANA' in df.columns:
            df = df.drop(columns=['SEMANA'])

        # Converte DATA para datetime
        df['DATA'] = pd.to_datetime(df['DATA'], errors='coerce')
        df = df.dropna(subset=['DATA'])

        # Acumula
        df_total = pd.concat([df_total, df], ignore_index=True)

    # ======== Remove duplicados e ordena ========
    df_total = df_total.drop_duplicates(subset=['DATA']).sort_values('DATA')

    # ======== Identifica estações (todas as colunas menos DATA) ========
    estacoes = [c for c in df_total.columns if c != 'DATA']
    print(f"📡 Estações detectadas: {len(estacoes)}")

    # ======== Dicionário de DataFrames finais ========
    dict_estacoes = defaultdict(lambda: pd.DataFrame())

    for estacao in estacoes:
        print(f"⚙️ Processando estação: {estacao}")
        df_est = df_total[['DATA', estacao]].copy()
        df_est = df_est.rename(columns={estacao: 'VALOR'})
        df_est['VALOR'] = pd.to_numeric(df_est['VALOR'], errors='coerce')

        # Expande valores diários em 24 registros horários
        registros = []
        for _, row in df_est.iterrows():
            if pd.isna(row['VALOR']):
                continue
            for hora in range(24):
                registros.append({
                    'DATETIME': row['DATA'] + timedelta(hours=hora),
                    'VALOR': row['VALOR']
                })
        df_horario = pd.DataFrame(registros)
        if df_horario.empty:
            continue

        # Garante frequência horária completa
        df_horario = df_horario.set_index('DATETIME').sort_index()
        horas_completas = pd.date_range(df_horario.index.min(), df_horario.index.max(), freq='H')
        df_horario = df_horario.reindex(horas_completas)
        df_horario['VALOR'] = pd.to_numeric(df_horario['VALOR'], errors='coerce')

        df_horario['UNIDADE'] = 'µg/m³'
        df_horario['QAQC_INTERNO'] = np.where(df_horario['VALOR'].isna(), 'Inválido', 'OK')

        # Colunas auxiliares
        df_horario['ANO'] = df_horario.index.year
        df_horario['MES'] = df_horario.index.month
        df_horario['DIA'] = df_horario.index.day
        df_horario['HORA'] = df_horario.index.hour

        df_horario = df_horario.reset_index().rename(columns={'index': 'DATETIME'})
        df_horario = df_horario[['DATETIME','ANO','MES','DIA','HORA','VALOR','UNIDADE','QAQC_INTERNO']]

        dict_estacoes[estacao] = df_horario

    # ======== Criação de IDs únicos ========
    primeiros_valores = {}
    for estacao, df in dict_estacoes.items():
        if not df['VALOR'].isna().all() and (df['VALOR'] > 0).any():
            linha_valida = df[df['VALOR'].notna() & (df['VALOR'] > 0)].iloc[0]
            primeiros_valores[estacao] = linha_valida['DATETIME']

    sorted_items = sorted(primeiros_valores.items(), key=lambda x: (x[1], x[0]))
    codigo_estacao_AC = {nome: f"AC{i:04d}" for i, (nome, _) in enumerate(sorted_items, start=1)}

    # ======== Exportação dos CSVs (1 arquivo por estação) ========
    for estacao, df in dict_estacoes.items():
        est_id = codigo_estacao_AC.get(estacao, 'AC9999')
        pol = 'MP25'  # PurpleAir → PM2.5

        cod_pol = tabela_pols.loc[tabela_pols['POLUENTE'] == pol, 'COD_POLUENTE'].values[0]
        nome_pasta = tabela_pols.loc[tabela_pols['COD_POLUENTE'] == int(cod_pol), 'NOME_PASTA'].values[0]

        df = create_QAQCMMA_VALOR(df, nome_pasta)
        out_path = f'/home/nobre/Notebooks/RQAR_2025_book/data/MQAr/{nome_pasta}/{est_id}RS{int(cod_pol):03d}.csv'
        df.to_csv(out_path, index=False)
        print(f"💾 {out_path}: {len(df)} linhas salvas")

    # ======== Mapeamento e retorno ========
    df_ids = pd.DataFrame({
        'ID_OEMA': codigo_estacao_AC.keys(),
        'ID_MMA': list(codigo_estacao_AC.values())
    })

    print(f"\n✅ {len(df_ids)} estações processadas no Acre (PurpleAir, 3 anos combinados)")
    print("\n📋 Mapeamento Estação → Código MMA:")
    for k, v in codigo_estacao_AC.items():
        print(f"{v} → {k}")

    return df_ids

#%% MAIN
funcoes = {
    'MG': rectify_MG, 
    'ES': rectify_ES,
    'SP': rectify_SP,
    'RJ': rectify_RJ,
     
    'SC': rectify_SC,
    'RS': rectify_RS,
    'PR': rectify_PR,
    
    'MA': rectify_MA,
    'BA': rectify_BA,
    'PE': rectify_PE,
    'CE': rectify_CE,
    'PB': rectify_PB,
    
    'MT': rectify_MT,
    'DF': rectify_DF,
    'MS': rectify_MS,
    
    'RR': rectify_RR,
    'AC': rectify_AC,

    
}

#lista_estados = ['DF','ES','MA','MG','MS','PE','PR','RS','SC','SP','BA']
#lista_estados = ['SP','BA']
#lista_estados = ['ES','SP','RJ','RS','PR','MA','BA','PE','CE','PB','MT','DF','MS','MG']
lista_estados = ['MA']
tabela_ids = pd.read_csv('/home/nobre/Notebooks/RQAR_2025_book/data/Monitoramento_QAr_BR.csv')
tabela_pols = pd.read_csv('/home/nobre/Notebooks/RQAR_2025_book/data/dicionarios/CODIGO_POLUENTES.csv')

for estado in lista_estados:
    
    path = os.getcwd()+'/data/DADOS_BRUTOS/' + estado + '/'

    df_ids = funcoes[estado](path)
    
    #create_df_estacao(estado,df_ids)##!/usr/bin/env python3



