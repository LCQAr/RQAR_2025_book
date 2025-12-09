#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Sep 11 10:45:33 2024

@author: leohoinaski
"""

#-----------------------------Importação de pacotes ------------------------------------

import os
import pandas as pd
from IPython.display import display, HTML
from typing import List
import pandas as pd
import warnings
import numpy as np
warnings.filterwarnings('ignore')
from itables import init_notebook_mode, show
import itables.options as opt

#-------------------------------- Dicionários-------------------------------------------- 
# Códigos IBGE por UF
codigo_para_uf = {
    12: 'AC', 27: 'AL', 13: 'AM', 16: 'AP', 29: 'BA', 23: 'CE', 53: 'DF',
    32: 'ES', 52: 'GO', 21: 'MA', 31: 'MG', 50: 'MS', 51: 'MT', 15: 'PA',
    25: 'PB', 26: 'PE', 22: 'PI', 41: 'PR', 33: 'RJ', 24: 'RN', 11: 'RO',
    14: 'RR', 43: 'RS', 42: 'SC', 28: 'SE', 35: 'SP', 17: 'TO'
}

# UF em cada região
regioes = {
    'Norte':             ['AC', 'AP', 'AM', 'PA', 'RO', 'RR', 'TO'],
    'Nordeste':          ['AL', 'BA', 'CE', 'MA', 'PB', 'PE', 'PI', 'RN', 'SE'],
    'Centro-Oeste':      ['DF', 'GO', 'MT', 'MS'],
    'Sudeste':           ['ES', 'MG', 'RJ', 'SP'],
    'Sul':               ['PR', 'RS', 'SC'],
    '':                  ['BR']
}

columns_names = {
    'UF':           'UF',
    'CIDADE':       'Cidade',
    'COD_IBGE':     'Cod. IBGE',
    'ID_OEMA':      'ID_OEMA',
    'ID_MMA':       'ID_MMA',
    'PROPRIETARIO': 'Proprietário',
    'PROP_ENTIDADE':'Natureza da entidade responsável',
    'OPERADOR':     'Respons. operação',
    'OP_ENTIDADE':  'Natureza da entidade operadora',
    'FUNCIONAMENTO':'Funcionamento',
    'CATEGORIA':    'Categoria',
    'METODO':       'Método',
    'CALIBRACAO':   'Calibração',
    'MARCA':        'Marca',
    'POLUENTE':     'Poluente',
    'MOBILIDADE':   'Mobilidade',
    'REP_ESPACIAL': 'Representatividade espacial',
    'FINALIDADE':   'Finalidade do monitoramento',
    'STATUS':       'Status',
    'INICIO':       'Início de operação',
    'FIM':          'Final de operação',
    'LATITUDE':     'Latitude',
    'LONGITUDE':    'Longitude',
    'MONITORAR':    'Integrado no MONITORAR?',
    'FONTE':        'Fonte',
    'REGIAO':       'Região',
    'FLAG':         '',
    'FINALIDADE':   'Finalidade',
    'ELEVACAO':     'Elevação', 
    'Indicativa':   'Indicativa',
    'INDICATIVA':   'Indicativa',
    'Referencia':   'Referência',
    'REFERENCIA':   'Referência',
    'REFERÊNCIA':   'Referência',
    'BASE_DADOS':   'Base de dados',
    'MODELO':       'Modelo',
    'Nao declarado': 'Não declarado',
    'Nao declarado': 'Não declarado',
    'Nao declarada': 'Não declarado',
    'Não declarada': 'Não declarado',
    'Coleta 2025': 'Consulta 2025',
    'Consulta 2024': 'Consulta 2025',
    'Coleta interna ': 'Coleta interna',
    ' Coleta interna': 'Coleta interna',
    'Coleta  interna': 'Coleta interna',
    'Coleta interna': 'Coleta interna'
    
    
}
# ---------------------------------Funções-----------------------------------------------

# DataReader.minha_acao()

# my_style1 = stilyzer(arg1, arg2)
# my_style1 = stilyzer(arg3, arg4)

# class DataReader:
#     @classmethod
#     def minha_acao(cls):
#         pass
    
# class Stilyzer:
#     def __init__(self, df, html):
#         self.df = df
#         self.html = html

#     def stilize(self, arg1):
#         return self.df.apply_style(self.html)
        

# # Criando tabela 1
# # obtendo
# dados1 = DataReader.leia_dados_do_tipo_tal()
# # preprocessando
# pass
# # estilizando
# my_style_table_1 = stilyzer(arg1, arg2)
# my_table = my_style_table_1.stilize(dados1)

#class DataReader:
#    @classmethod
#    def csv_reader(cls):
#         # Caminho para a pasta de dados
#        rootPath = os.path.dirname(os.getcwd())
#        aqmData = pd.read_csv(rootPath+'/data/Monitoramento_QAr_BR.csv',encoding = 'unicode_escape')

def columns_renamer(aqmDisplay):
    aqmDisplay = aqmDisplay.rename(columns={k: v for k, v in columns_names.items() if k in aqmDisplay.columns})
    return aqmDisplay

def columns_renamer_csv(aqmDisplay):
    """
    Rename columns of a dataframe based on a CSV mapping file.

    Parameters
    ----------
    aqmDisplay : pd.DataFrame
        Input dataframe with original column names.
    csv_mapping_path : str
        Path to the CSV file with two columns: "old" and "new".
        Example:
            old,new
            avg_co,CO
            avg_no2,NO2

    Returns
    -------
    pd.DataFrame
        Dataframe with renamed columns.
    """
    # Caminho para a pasta de dados
    rootPath = os.path.dirname(os.getcwd())
    
    # Read mapping file
    mapping_df = pd.read_csv(rootPath+'/data/dicionarios/CODIGO_POLUENTES_HTML.csv')
    # Convert to dict
    columns_names = dict(zip(mapping_df["NOME_PASTA"], mapping_df["NOME_TEXTO_HTML"]))
    # Rename columns
    aqmDisplay = aqmDisplay.rename(columns={k: v for k, v in columns_names.items() if k in aqmDisplay.columns})
    return aqmDisplay

def style_all_white(row: pd.Series) -> List:
    """
    Define o estilo das linhas da tabela:
    - Linhas de separador ficam com fundo branco, texto centralizado e negrito.
    - Linhas normais ficam em cinza claro, texto preto e centralizado.

    Parameters
    ----------
        row (pd.Series): Linha do DataFrame.

    Returns
    -------
        Lista de strings com estilos CSS aplicados a cada coluna da linha.
    """
    if row[''] == '':
        # Linha separadora
        return ['background-color: white; color: black; text-align: center; font-weight: bold; font-size:11px'] * len(row)
    else:
        # Linhas normais
        return ['background-color: #F5F5F5; color: black; text-align: center; font-size:11px'] * len(row)


def tableReorder(regioes):
    """
    Gera informações de ordenação e associação de estados (UF) a regiões.

    A função percorre um dicionário que associa nomes de regiões às listas de UFs,
    atribui uma ordem sequencial a cada UF e cria um DataFrame com as UFs e suas ordens.
    Além disso, retorna também um dicionário que associa cada UF à sua região correspondente
    e um dicionário com a ordem numérica de cada UF.

    Parameters
    ----------
    regioes : dict
        Dicionário onde as chaves são nomes de regiões (str) e os valores são listas de UFs (list of str).

    Returns
    -------
    df_index : pandas.DataFrame
        DataFrame contendo duas colunas:
        - 'UF' (str): Sigla da unidade federativa.
        - 'ORDEM' (int): Ordem sequencial atribuída a cada UF conforme a ordem nas listas.
    uf_to_region : dict
        Dicionário que associa cada UF (str) ao nome da região (str) correspondente.
    uf_order : dict
        Dicionário que associa cada UF (str) ao seu número de ordem (int).

    Examples
    --------
    >>> regioes = {
    ...     'Norte': ['AC', 'AM'],
    ...     'Nordeste': ['BA', 'PE']
    ... }
    >>> df, uf_to_region, uf_order = tableReorder(regioes)
    >>> print(df)
        UF  ORDEM
    0   AC      0
    1   AM      1
    2   BA      2
    3   PE      3
    >>> print(uf_to_region)
    {'AC': 'Norte', 'AM': 'Norte', 'BA': 'Nordeste', 'PE': 'Nordeste'}
    >>> print(uf_order)
    {'AC': 0, 'AM': 1, 'BA': 2, 'PE': 3}
    """
    
    # Ordenando por região
    # Region name per UF
    uf_to_region = {uf: Regiao for Regiao, ufs in regioes.items() for uf in ufs}

    # Order number per UF
    uf_order = {}
    order = 0
    for region, ufs in regioes.items():
        for uf in ufs:
            uf_order[uf] = order
            order += 1

    # DataFrame com todos os estados e ordens
    df_index = pd.DataFrame(uf_order.items(), columns=['UF', 'ORDEM'])
    return df_index, uf_to_region, uf_order

def table_constructor(columns_selector = ['FLAG','UF', 'Realiza monitoramento?','FONTE','REGIAO'],
                      drop_duplicates_by=['UF','FONTE'],
                     groupby_method = 'join', groupby_column=['FONTE']):
    
    # Caminho para a pasta de dados
    rootPath = os.path.dirname(os.getcwd())
    
    # Lendo o csv
    aqmData = pd.read_csv(rootPath+'/data/Monitoramento_QAr_BR.csv')

    # Criando coluna 'Realiza monitoramento?'
    aqmData['Realiza monitoramento?'] = 'Sim'
    
    df_index,uf_to_region,uf_order = tableReorder(regioes)
    
    # DataFrame com todos os estados e ordens
    df_index = pd.DataFrame(uf_order.items(), columns=['UF', 'ORDEM'])

    # Atualizando o df com todos os estados
    aqmData = df_index.merge(aqmData, left_on='UF', right_on='UF',how='left')
    
    # Remove NaN
    aqmData['Realiza monitoramento?'][aqmData['Realiza monitoramento?'].isna()] = 'Não'
    aqmData['FONTE'][aqmData['FONTE'].isna()] = '-'
    
    # Add columns to the DataFrame
    aqmData['REGIAO'] = aqmData['UF'].map(uf_to_region)
    aqmData['ORDEM'] = aqmData['UF'].map(uf_order)

    #Create a new column with HTML img tag
    aqmData['FLAG'] = aqmData['UF'].apply(
        lambda uf: f'<img src= "../_static/bandeiras/{uf}.png" width="30">'
    ).astype(str)

    # Sort by region order and then by UF order
    aqmData = aqmData.sort_values('ORDEM').drop(columns='ORDEM').reset_index(drop=True)

    aqmDisplay = aqmData[columns_selector]

    # Selecionando apenas Estado e Fonte e removendo redundâncias
    aqmDisplay = aqmDisplay.drop_duplicates(subset=drop_duplicates_by)

    if groupby_method=='join':

        # Agrupamento por estado quando tivermos mais de uma fonte de informação
        for group_col in groupby_column:
            aqmDataGroup = aqmData.groupby('UF').agg({
                group_col: lambda x: ', '.join(x),
            }).reset_index()
            aqmData[group_col] = aqmDataGroup[group_col]

    aqmDisplay = aqmDisplay.rename(columns={k: v for k, v in columns_names.items() if k in aqmDisplay.columns})


    return aqmData,aqmDisplay


def table_stylizer(style_sortBy='REGIAO'):
    aqmData,aqmDisplay = table_constructor()
    # Selecionando apenas Estado e Fonte e removendo redundâncias
    #aqmData = aqmData.drop_duplicates(subset=['UF', 'FONTE']).reset_index()


    # Agrupamento por estado quando tivermos mais de uma fonte de informação
    #aqmDataGroup = aqmData.groupby('UF').agg({
    #    'FONTE': lambda x: ', '.join(x),
    #}).reset_index()
    #aqmData['FONTE'] = aqmDataGroup['FONTE']

    
    #print(aqmData)
    #aqmDisplay = aqmData[['FLAG','UF', 'Realiza monitoramento?','FONTE','REGIAO']]
    #aqmDisplay = aqmDisplay.rename(columns={"FLAG": "", "UF": "UF",'Realiza monitoramento?':'Realiza monitoramento?',"FONTE": "Fonte","REGIAO": "Região"})
    
    rows = []

    for group, data in aqmDisplay.groupby(columns_names[style_sortBy], sort=False):
        empty_dict_UF = {col: group if col == 'UF' else '' for col in aqmDisplay.columns}
        rows.append(empty_dict_UF)  
        rows.extend(data.to_dict('records'))
        # Add separator row: None or '' to create empty row
        empty_dict = {col: '' for col in aqmDisplay.columns}
        rows.append(empty_dict)  
    
    # Add a blank row at the beginning
    rows.insert(0, empty_dict)
        
    df_with_separators = pd.DataFrame(rows)
    df_with_separators = df_with_separators.drop(columns=['Região'])
    #df_with_separators = df_with_separators.style.apply(style_all_white, axis=1)

    styled = (
        df_with_separators
        .style
        .apply(style_all_white, axis=1)
        .hide(axis="index")  # hide the index column
        .set_table_styles([
        {'selector': 'th', 'props': [('text-align', 'center')]},  # center header text
        {'selector': 'td > img', 'props': [('max-width', 'unset')]}
    ])
    )
    return styled
 

def table01():
    
    # Caminho para a pasta de dados
    rootPath = os.path.dirname(os.getcwd())
    
    # Lendo o csv
    aqmData = pd.read_csv(rootPath+'/data/Monitoramento_QAr_BR.csv')
    # Selecionando apenas Estado e Fonte e removendo redundâncias
    aqmData['FONTE'] = aqmData['FONTE'].replace(np.nan, 'Coleta interna')
    aqmData = aqmData.replace(columns_names)
    aqmData = aqmData.drop_duplicates(subset=['UF', 'FONTE'])
    #aqmData[np.isnan(aqmData['FONTE'])] = 'Coleta interna'
    
    # Agrupamento por estado quando tivermos mais de uma fonte de informação
    aqmData = aqmData.groupby('UF').agg({
        'FONTE': lambda x: ', '.join(x),
    }).reset_index()

    # Criando coluna 'Realiza monitoramento?'
    aqmData['Realiza monitoramento?'] = 'Sim'
    
    df_index,uf_to_region,uf_order = tableReorder(regioes)
    
    # DataFrame com todos os estados e ordens
    df_index = pd.DataFrame(uf_order.items(), columns=['UF', 'ORDEM'])

    # Atualizando o df com todos os estados
    aqmData = df_index.merge(aqmData, left_on='UF', right_on='UF',how='left')
    aqmData = aqmData[aqmData["UF"] != "BR"]
    # Remove NaN
    aqmData['Realiza monitoramento?'][aqmData['Realiza monitoramento?'].isna()] = 'Não'
    aqmData['FONTE'][aqmData['FONTE'].isna()] = '-'
    
    # Add columns to the DataFrame
    aqmData['REGIAO'] = aqmData['UF'].map(uf_to_region)
    aqmData['ORDEM'] = aqmData['UF'].map(uf_order)

    #Create a new column with HTML img tag
    aqmData['FLAG'] = aqmData['UF'].apply(
        lambda uf: f'<img src= "../_static/bandeiras/{uf}.png" width="30">'
    ).astype(str)

    # Sort by region order and then by UF order
    aqmData = aqmData.sort_values('ORDEM').drop(columns='ORDEM').reset_index(drop=True)

    aqmDisplay = aqmData[['FLAG','UF', 'Realiza monitoramento?','FONTE','REGIAO']]
    aqmDisplay = aqmDisplay.rename(columns={"FLAG": "", "UF": "UF",'Realiza monitoramento?':'UF possui algum tipo de monitoramento?',"FONTE": "Fonte","REGIAO": "Região"})
    
    rows = []
    

    for group, data in aqmDisplay.groupby('Região', sort=False):
        rows.append({'': '', 'UF': group, 'UF possui algum tipo de monitoramento?': '', 'Fonte': '','Região': ''})  
        rows.extend(data.to_dict('records'))
        # Add separator row: None or '' to create empty row
        rows.append({'': '', 'UF': '', 'UF possui algum tipo de monitoramento?': '', 'Fonte': '','Região': ''})  
    
    # Add a blank row at the beginning
    blank_row = {'': '', 'UF': '', 'UF possui algum tipo de monitoramento?': '', 'Fonte': '','Região': ''}
    rows.insert(0, blank_row)
        
    df_with_separators = pd.DataFrame(rows)
    df_with_separators = df_with_separators.drop(columns=['Região'])
    df_with_separators= df_with_separators.replace(0, '-')
    #df_with_separators = df_with_separators.style.apply(style_all_white, axis=1)

    styled = (
        df_with_separators
        .style
        .apply(style_all_white, axis=1)
        .hide(axis="index")  # ✅ hide the index column
        .set_table_styles([
        {'selector': 'th', 'props': [('text-align', 'center')]},  # center header text
        {'selector': 'td > img', 'props': [('max-width', 'unset')]}
    ])
    )

    return display(HTML(styled.to_html(index=False, border=0,escape=False)))


def table05():

    # Caminho para a pasta de dados
    rootPath = os.path.dirname(os.getcwd())
    
    # Lendo o csv
    aqmData = pd.read_csv(rootPath+'/data/Monitoramento_QAr_BR.csv')
    #print(aqmData.columns)
    # Selecionando apenas estações ativas
    #aqmData = aqmData[aqmData['STATUS']=='Ativa']
    
    aqmData['ID_OEMA'] = aqmData['ID_OEMA'].str.replace(' ', '') 
    #aqmData['CATEGORIA'] = aqmData['CATEGORIA'].str.replace(' ', '') 
    #aqmData['CATEGORIA'] = aqmData['CATEGORIA'].str.replace(' ', '') 
    
    # Selecionando apenas Estado e Fonte e removendo redundâncias
    aqmData = aqmData.drop_duplicates(subset=['ID_OEMA'])
    #print(aqmData.head())
    
    
    # Selecionando apenas Estado e Fonte e removendo redundâncias
    aqmData = aqmData.groupby('UF')['CATEGORIA'].value_counts().unstack(fill_value=0)
    aqmData.loc['BR']= aqmData.sum()
    
   
    df_index,uf_to_region,uf_order = tableReorder(regioes)

    # Atualizando o df com todos os estados
    aqmData = df_index.merge(aqmData, left_on='UF', right_on='UF',how='left')
    
    
    # Add columns to the DataFrame
    aqmData['REGIAO'] = aqmData['UF'].map(uf_to_region)
    aqmData['ORDEM'] = aqmData['UF'].map(uf_order)

    #Create a new column with HTML img tag
    aqmData['FLAG'] = aqmData['UF'].apply(
        lambda uf: f'<img src= "../_static/bandeiras/{uf}.png" width="30">'
    ).astype(str)


    # Sort by region order and then by UF order
    aqmData = aqmData.sort_values('ORDEM').drop(columns='ORDEM').reset_index(drop=True)
    #print(aqmData)


    aqmDisplay = aqmData[['FLAG','UF', 'Indicativa', 'Referencia','Nao declarado','REGIAO']]
    aqmDisplay = columns_renamer(aqmDisplay)

    aqmDisplay = aqmDisplay.fillna(0)
    aqmDisplay['Indicativa'] = aqmDisplay['Indicativa'].astype(int)
    aqmDisplay['Referência'] = aqmDisplay['Referência'].astype(int)
    aqmDisplay['Não declarado'] = aqmDisplay['Não declarado'].astype(int)
    rows = []

    #print(aqmDisplay.groupby('Região'))
    
    for group, data in aqmDisplay.groupby('Região', sort=False):
        rows.append({'': '', 'UF': group, 'Indicativa': '', 'Referência': '','Não declarado':'','Região':''})  
        rows.extend(data.to_dict('records'))
        # Add separator row: None or '' to create empty row
        rows.append({'': '', 'UF': '','Indicativa': '', 'Referência':'','Não declarado':'', 'Região':''})  
    
    # Add a blank row at the beginning
    blank_row = {'': '', 'UF': '', 'Indicativa': '', 'Referência':'','Não declarado':'', 'Região':''}
    rows.insert(0, blank_row)
  
        
    df_with_separators = pd.DataFrame(rows)
    df_with_separators = df_with_separators.drop(columns=['Região'])
    df_with_separators= df_with_separators.replace(0, '-')
    #df_with_separators = df_with_separators.style.apply(style_all_white, axis=1)
    
    styled = (
        df_with_separators
        .style
        .apply(style_all_white, axis=1)
        .hide(axis="index")  # ✅ hide the index column
        .set_table_styles([
        {'selector': 'th', 'props': [('text-align', 'center')]},  # center header text
        {'selector': 'td > img', 'props': [('max-width', 'unset')]}
    ])
    )

    return display(HTML(styled.to_html(index=False, border=0,escape=False)))

def table05MMA2():

    # Caminho para a pasta de dados
    rootPath = os.path.dirname(os.getcwd())
    
    # Lendo o csv
    aqmData = pd.read_csv(rootPath+'/data/Monitoramento_QAr_BR.csv')

    # Remove espaços do ID
    aqmData['ID_OEMA'] = aqmData['ID_OEMA'].astype(str).str.replace(' ', '')
    
    # ===============================
    # 1) CONVERTE ANOS_MONITORADOS
    # ===============================
    def parse_anos(x):
        try:
            return [int(z) for z in str(x)
                    .replace('[','')
                    .replace(']','')
                    .replace("'",'')
                    .split(',')
                    if z.strip().isdigit()]
        except:
            return []

    aqmData['ANOS_MONITORADOS'] = aqmData['ANOS_MONITORADOS'].apply(parse_anos)

    # ===============================
    # 2) FILTRA APENAS ESTAÇÕES QUE MONITORARAM EM 2024
    # ===============================
    aqmData = aqmData[aqmData['ANOS_MONITORADOS'].apply(lambda lst: 2024 in lst)]

    # ===============================
    # 3) PADRONIZAÇÃO DAS CATEGORIAS
    # ===============================
    if 'CATEGORIA' not in aqmData.columns:
        aqmData['CATEGORIA'] = 'Não declarado'

    aqmData['CATEGORIA'] = aqmData['CATEGORIA'].fillna('Não declarado')

    correction_map = {
        'Referencia': 'Referência',
        'Referência': 'Referência',
        'Indicativa': 'Indicativa',
        'Nao declarado': 'Não declarado',
        'Nao declarada': 'Não declarado',
        'Não declarada': 'Não declarado',
        'Não declarado': 'Não declarado'
    }

    aqmData['CATEGORIA'] = (
        aqmData['CATEGORIA']
        .astype(str)
        .str.strip()
        .str.capitalize()
        .replace(correction_map)
    )
    
    # ===============================
    # 4) REMOVE DUPLICIDADES
    # ===============================
    aqmData = aqmData.drop_duplicates(subset=['ID_OEMA'])

    # ===============================
    # 5) AGRUPAMENTO POR UF × CATEGORIA
    # ===============================
    aqmData = aqmData.groupby('UF')['CATEGORIA'].value_counts().unstack(fill_value=0)

    # Brasil
    aqmData.loc['BR'] = aqmData.sum()
    
    # ===============================
    # 6) ORDENA POR REGIÕES + BANDEIRAS
    # ===============================
    df_index, uf_to_region, uf_order = tableReorder(regioes)

    # Garante que todos os estados apareçam na tabela
    aqmData = df_index.merge(aqmData, left_on='UF', right_on='UF', how='left')
    
    aqmData['REGIAO'] = aqmData['UF'].map(uf_to_region)
    aqmData['ORDEM'] = aqmData['UF'].map(uf_order)

    aqmData['FLAG'] = aqmData['UF'].apply(
        lambda uf: f'<img src="../_static/bandeiras/{uf}.png" width="30">'
    )

    aqmData = aqmData.sort_values('ORDEM').drop(columns='ORDEM').reset_index(drop=True)

    # ===============================
    # 7) FORMATAÇÃO FINAL
    # ===============================
    aqmDisplay = aqmData[['FLAG','UF','Indicativa','Referência','Não declarado','REGIAO']]
    aqmDisplay = columns_renamer(aqmDisplay)

    aqmDisplay = aqmDisplay.fillna(0)
    aqmDisplay['Indicativa'] = aqmDisplay['Indicativa'].astype(int)
    aqmDisplay['Referência'] = aqmDisplay['Referência'].astype(int)
    aqmDisplay['Não declarado'] = aqmDisplay['Não declarado'].astype(int)

    rows = []

    for group, data in aqmDisplay.groupby('Região', sort=False):
        rows.append({'': '', 'UF': group, 'Indicativa': '', 'Referência': '','Não declarado':'','Região':''})  
        rows.extend(data.to_dict('records'))
        rows.append({'': '', 'UF': '','Indicativa': '', 'Referência':'','Não declarado':'', 'Região':''})  
    
    rows.insert(0, {'': '', 'UF': '', 'Indicativa': '', 'Referência':'','Não declarado':'', 'Região':''})
  
    df_with_separators = pd.DataFrame(rows)
    df_with_separators = df_with_separators.drop(columns=['Região'])
    df_with_separators = df_with_separators.replace(0, '-')
    
    styled = (
        df_with_separators
        .style
        .apply(style_all_white, axis=1)
        .hide(axis="index")
        .set_table_styles([
            {'selector': 'th', 'props': [('text-align', 'center')]},
            {'selector': 'td > img', 'props': [('max-width', 'unset')]}
        ])
    )

    return display(HTML(styled.to_html(index=False, border=0, escape=False)))


def table06():

    # Caminho para a pasta de dados
    rootPath = os.path.dirname(os.getcwd())
    
    # Lendo o csv
    aqmData = pd.read_csv(rootPath+'/data/Monitoramento_QAr_BR.csv')

    aqmData['ID_OEMA'] = aqmData['ID_OEMA'].str.replace(' ', '') 
    
    # Selecionando apenas Estado e Fonte e removendo redundâncias
    aqmData = aqmData.drop_duplicates(subset=['ID_OEMA'])
    #print(aqmData.head())
    
    # Selecionando apenas Estado e Fonte e removendo redundâncias
    aqmData = aqmData.groupby('UF')['STATUS'].value_counts().unstack(fill_value=0)
    aqmData.loc['BR']= aqmData.sum()
   
    # Ordenando por região
    # Create two mappings:
    # Region name per UF
    uf_to_region = {uf: Regiao for Regiao, ufs in regioes.items() for uf in ufs}
    
    df_index, uf_to_region, uf_order = tableReorder(regioes)

    # Atualizando o df com todos os estados
    aqmData = df_index.merge(aqmData, left_on='UF', right_on='UF', how='left')
    
    # Add columns to the DataFrame
    aqmData['REGIAO'] = aqmData['UF'].map(uf_to_region)
    aqmData['ORDEM'] = aqmData['UF'].map(uf_order)

    #Create a new column with HTML img tag
    aqmData['FLAG'] = aqmData['UF'].apply(
        lambda uf: f'<img src= "../_static/bandeiras/{uf}.png" width="30">'
    ).astype(str)


    # Sort by region order and then by UF order
    aqmData = aqmData.sort_values('ORDEM').drop(columns='ORDEM').reset_index(drop=True)
    
    aqmDisplay = aqmData[['FLAG','UF', 'Inativa', 'Ativa','Nao declarado','REGIAO']]
    aqmDisplay = aqmDisplay.rename(columns={"FLAG": "", "UF": "UF",'Inativa':'Inativa',"Ativa": "Ativa",'Nao declarado':'Não declarado',"REGIAO": "Região"})
    aqmDisplay = aqmDisplay.fillna(0)
    aqmDisplay['Inativa'] = aqmDisplay['Inativa'].astype(int)
    aqmDisplay['Ativa'] = aqmDisplay['Ativa'].astype(int)
    aqmDisplay['Não declarado'] = aqmDisplay['Não declarado'].astype(int)
    rows = []

    for group, data in aqmDisplay.groupby('Região', sort=False):
        rows.append({'': '', 'UF': group, 'Inativa': '', 'Ativa': '','Não declarado':'','Região':''})  
        rows.extend(data.to_dict('records'))
        # Add separator row: None or '' to create empty row
        rows.append({'': '', 'UF': '','Inativa': '', 'Ativa':'','Não declarado':'', 'Região':''})  
    
    # Add a blank row at the beginning
    blank_row = {'': '', 'UF': '', 'Inativa': '', 'Ativa':'','Não declarado':'', 'Região':''}
    rows.insert(0, blank_row)
        
    df_with_separators = pd.DataFrame(rows)
    df_with_separators = df_with_separators.drop(columns=['Região'])
    df_with_separators= df_with_separators.replace(0, '-')
    #df_with_separators = df_with_separators.style.apply(style_all_white, axis=1)
    
    styled = (
        df_with_separators
        .style
        .apply(style_all_white, axis=1)
        .hide(axis="index")  # ✅ hide the index column
        .set_table_styles([
        {'selector': 'th', 'props': [('text-align', 'center')]},  # center header text
        {'selector': 'td > img', 'props': [('max-width', 'unset')]}
    ])
    )

    return display(HTML(styled.to_html(index=False, border=0,escape=False)))

def table06MMA():
    # 1. PREPARAÇÃO DOS DADOS
    rootPath = os.path.dirname(os.getcwd())
    aqmData = pd.read_csv(rootPath+'/data/Monitoramento_QAr_BR.csv')
    aqmData['ID_OEMA'] = aqmData['ID_OEMA'].str.replace(' ', '')
    
    aqmData = aqmData.drop_duplicates(subset=['ID_OEMA'])
    
    # --- AJUSTE DA COLUNA CATEGORIA ---
    col_target = 'CATEGORIA'
    if col_target not in aqmData.columns:
        aqmData[col_target] = 'Não declarado'
        
    # Preenche nulos
    aqmData[col_target] = aqmData[col_target].fillna('Não declarado')
    aqmData['STATUS'] = aqmData['STATUS'].fillna('Não declarado')

    # --- LIMPEZA E PADRONIZAÇÃO DOS NOMES ---
    
    # 1. Padroniza Categoria
    aqmData[col_target] = aqmData[col_target].astype(str).str.strip().str.capitalize()
    
    # 2. Padroniza Status
    aqmData['STATUS'] = aqmData['STATUS'].astype(str).str.strip().str.capitalize()
    
    # Dicionário para corrigir grafias comuns (ex: sem acento)
    correction_map = {
        'Referencia': 'Referência',
        'Referência': 'Referência',
        'Indicativa': 'Indicativa',
        'Nao declarado': 'Não declarado',
        'Não declarado': 'Não declarado',
        # Adicione variações se necessário
        'Ativa': 'Ativa',
        'Inativa': 'Inativa'
    }
    
    # --- A CORREÇÃO PRINCIPAL É AQUI: ---
    # Aplica o replace nas DUAS colunas. Antes você só aplicava em col_target.
    aqmData[col_target] = aqmData[col_target].replace(correction_map)
    aqmData['STATUS'] = aqmData['STATUS'].replace(correction_map)

    # 2. PIVOTAGEM
    # Agora tanto Categoria quanto Status terão "Não declarado" com acento,
    # batendo com a lista 'super_cols' e 'sub_cols' definida abaixo.
    pivot = aqmData.groupby(['UF', col_target, 'STATUS'])['ID_OEMA'].count().unstack([col_target, 'STATUS'], fill_value=0)
    
    # 3. DEFINIÇÃO DA ESTRUTURA FIXA
    # Definimos exatamente quais colunas queremos exibir
    super_cols = ['Indicativa', 'Referência', 'Não declarado']
    sub_cols = ['Ativa', 'Inativa', 'Não declarado']
    
    # Produto cartesiano (Gabarito de todas as colunas possíveis)
    target_combinations = [(sup, sub) for sup in super_cols for sub in sub_cols]

    # Reindexa para garantir que a tabela tenha exatamente essas colunas na ordem certa
    # (Se a coluna Categoria tiver valores diferentes desses, eles serão descartados aqui. 
    #  Se tiver faltando, serão preenchidos com 0)
    pivot = pivot.reindex(columns=pd.MultiIndex.from_tuples(target_combinations), fill_value=0)
    
    # Calcula linha BR (Soma)
    pivot.loc['BR'] = pivot.sum()

    # 4. CONSTRUÇÃO MANUAL DAS LINHAS
    df_index, uf_to_region, uf_order = tableReorder(regioes)
    
    flat_columns = ['FLAG', 'UF', 'REGIAO'] + [f'col_{i}' for i in range(len(target_combinations))]

    def get_flag(uf):
        return f'<img src= "../_static/bandeiras/{uf}.png" width="30">'

    df_index['REGIAO'] = df_index['UF'].map(uf_to_region)
    df_index['ORDEM'] = df_index['UF'].map(uf_order)
    df_index = df_index.sort_values('ORDEM')

    rows = []
    
    for region_name, region_data in df_index.groupby('REGIAO', sort=False):
        # --- Cabeçalho da Região ---
        header_row = {col: '' for col in flat_columns}
        header_row['UF'] = f"<b>{region_name}</b>" 
        rows.append(header_row)

        # --- Linhas dos Estados ---
        for uf in region_data['UF']:
            row_data = {
                'FLAG': get_flag(uf),
                'UF': uf,
                'REGIAO': region_name
            }
            
            if uf in pivot.index:
                vals = pivot.loc[uf].values
            else:
                vals = [0] * len(target_combinations)
            
            for i, val in enumerate(vals):
                row_data[f'col_{i}'] = str(int(val)) if val > 0 else '-'
            
            rows.append(row_data)

        # --- Separador ---
        rows.append({col: '' for col in flat_columns})

    rows.insert(0, {col: '' for col in flat_columns})

    # 5. CRIAÇÃO DO DATAFRAME FINAL
    df_final = pd.DataFrame(rows, columns=flat_columns)
    df_final = df_final.drop(columns=['REGIAO'])

    # Define o Cabeçalho Duplo (MultiIndex)
    header_tuples = [('', ''), ('', 'UF')] 
    for sup, sub in target_combinations:
        header_tuples.append((sup, sub))

    df_final.columns = pd.MultiIndex.from_tuples(header_tuples)

    # 6. ESTILIZAÇÃO (Função customizada corrigida)
    def custom_styler(row):
        uf_val = row[('', 'UF')]
        flag_val = row[('', '')] 

        base_style = 'background-color: white; color: black; font-size: 11px;'
        center = 'text-align: center;'
        left = 'text-align: left;'
        
        styles = []
        
        # Identifica se é linha de Região (Tem texto na UF mas não tem Bandeira)
        if uf_val != '' and flag_val == '':
            for col_tuple in row.index:
                if col_tuple == ('', 'UF'):
                    # Alinha o nome da região à esquerda e em negrito
                    styles.append(base_style + left + 'font-weight: bold; font-size: 12px;')
                else:
                    styles.append(base_style)
            return styles
        
        return [base_style + center] * len(row)

    styled = (
        df_final.style
        .apply(custom_styler, axis=1)
        .hide(axis="index")
        .set_table_styles([
            {'selector': 'th', 'props': [
                ('text-align', 'center'), 
                ('vertical-align', 'middle'),
                ('font-size', '8pt'), # Fonte do cabeçalho levemente menor
                ('background-color', 'white'),
                ('color', 'black')
            ]},
            {'selector': 'td > img', 'props': [('max-width', 'unset')]},
            {'selector': 'th[colspan]', 'props': [
                ('border-bottom', '1px solid #ccc'),
                ('font-weight', 'bold'),
                ('text-transform', 'uppercase')
            ]} 
        ])
    )

    return display(HTML(styled.to_html(index=False, border=0, escape=False)))

def table06MMA2():
    # ===========================================
    # 1. LEITURA E PREPARAÇÃO DOS DADOS
    # ===========================================
    rootPath = os.path.dirname(os.getcwd())
    aqmData = pd.read_csv(rootPath+'/data/Monitoramento_QAr_BR.csv')
    
    # Remove espaços em IDs
    aqmData['ID_OEMA'] = aqmData['ID_OEMA'].astype(str).str.replace(' ', '')

    # -------------------------------------------
    # GARANTE QUE A COLUNA CATEGORIA EXISTE
    # -------------------------------------------
    col_target = 'CATEGORIA'
    if col_target not in aqmData.columns:
        aqmData[col_target] = 'Não declarado'

    # Converte ANOS_MONITORADOS para lista de inteiros
    def parse_anos(x):
        try:
            parts = [int(z) for z in str(x)
                     .replace('[', '')
                     .replace(']', '')
                     .replace("'", '')
                     .split(',')
                     if z.strip().isdigit()]
            return parts
        except:
            return []
    
    aqmData['ANOS_MONITORADOS'] = aqmData['ANOS_MONITORADOS'].apply(parse_anos)

    # -------------------------------------------
    # FILTRA APENAS ESTAÇÕES QUE MONITORARAM EM 2024
    # (para coincidir com o gráfico)
    # -------------------------------------------
    # FILTRA APENAS ESTAÇÕES ATIVAS
    aqmData = aqmData[aqmData['STATUS'].astype(str).str.strip().str.capitalize() == 'Ativa']


    # Se a estação aparecer repetida no CSV, mantém só uma
    aqmData = aqmData.drop_duplicates(subset=['ID_OEMA'])

    # ===========================================
    # 2. PADRONIZAÇÃO DAS VARIÁVEIS
    # ===========================================
    # Preenche NAs
    aqmData[col_target] = aqmData[col_target].fillna('Não declarado')
    aqmData['STATUS'] = aqmData['STATUS'].fillna('Não declarado')

    # Padroniza CATEGORIA
    correction_map = {
        'Referencia': 'Referência',
        'Referência': 'Referência',
        'Indicativa': 'Indicativa',
        'Nao declarado': 'Não declarado',
        'Nao declarada': 'Não declarado',
        'Não declarada': 'Não declarado',
        'Não declarado': 'Não declarado'
    }

    aqmData[col_target] = (
        aqmData[col_target]
        .astype(str)
        .str.strip()
        .str.capitalize()
        .replace(correction_map)
    )

    # Padroniza STATUS
    aqmData['STATUS'] = (
        aqmData['STATUS']
        .astype(str)
        .str.strip()
        .str.capitalize()
    )

    # ===========================================
    # 3. PIVOT (UF × CATEGORIA × STATUS)
    # ===========================================
    pivot = (
        aqmData
        .groupby(['UF', col_target, 'STATUS'])['ID_OEMA']
        .count()
        .unstack([col_target, 'STATUS'], fill_value=0)
    )

    # -------------------------------------------
    # COLUNAS FIXAS (GABARITO)
    # -------------------------------------------
    super_cols = ['Indicativa', 'Referência', 'Não declarado']
    sub_cols = ['Ativa', 'Inativa', 'Não declarado']
    target_combinations = [(sup, sub) for sup in super_cols for sub in sub_cols]

    pivot = pivot.reindex(columns=pd.MultiIndex.from_tuples(target_combinations), fill_value=0)

    # ===========================================
    # 4. LINHA BR (total Brasil)
    # ===========================================
    pivot.loc['BR'] = pivot.sum()

    # ===========================================
    # 5. MONTAGEM DO DATAFRAME FINAL COM BANDEIRAS
    # ===========================================
    df_index, uf_to_region, uf_order = tableReorder(regioes)

    flat_columns = ['FLAG', 'UF', 'REGIAO'] + [f'col_{i}' for i in range(len(target_combinations))]

    def get_flag(uf):
        return f'<img src="../_static/bandeiras/{uf}.png" width="30">'

    df_index['REGIAO'] = df_index['UF'].map(uf_to_region)
    df_index['ORDEM'] = df_index['UF'].map(uf_order)
    df_index = df_index.sort_values('ORDEM')

    rows = []

    # Inserimos um separador no topo
    rows.append({col: '' for col in flat_columns})

    # -------------------------------------------
    # Adiciona UF por Região
    # -------------------------------------------
    for region_name, region_data in df_index.groupby('REGIAO', sort=False):

        # Cabeçalho de região
        header_row = {col: '' for col in flat_columns}
        header_row['UF'] = f"<b>{region_name}</b>"
        rows.append(header_row)

        # Linhas dos estados
        for uf in region_data['UF']:
            row = {
                'FLAG': get_flag(uf),
                'UF': uf,
                'REGIAO': region_name
            }

            if uf in pivot.index:
                vals = pivot.loc[uf].values
            else:
                vals = [0] * len(target_combinations)

            for i, val in enumerate(vals):
                row[f'col_{i}'] = str(int(val)) if val > 0 else '-'

            rows.append(row)

        # Separador entre regiões
        rows.append({col: '' for col in flat_columns})

    # ===========================================
    # 6. MONTAGEM FINAL DO DATAFRAME
    # ===========================================
    df_final = pd.DataFrame(rows, columns=flat_columns)
    df_final = df_final.drop(columns=['REGIAO'])

    header_tuples = [('', ''), ('', 'UF')] + list(target_combinations)
    df_final.columns = pd.MultiIndex.from_tuples(header_tuples)

    # ===========================================
    # 7. ESTILIZAÇÃO
    # ===========================================
    def custom_styler(row):
        uf_val = row[('', 'UF')]
        flag_val = row[('', '')]

        base = 'background-color: white; color: black; font-size: 11px;'
        center = 'text-align: center;'
        left = 'text-align: left;'

        styles = []

        if uf_val != '' and flag_val == '':
            # Linha de Região
            for col in row.index:
                if col == ('', 'UF'):
                    styles.append(base + left + 'font-weight: bold; font-size: 12px;')
                else:
                    styles.append(base)
            return styles

        return [base + center] * len(row)

    styled = (
        df_final.style
        .apply(custom_styler, axis=1)
        .hide(axis="index")
        .set_table_styles([
            {'selector': 'th', 'props': [
                ('text-align', 'center'),
                ('vertical-align', 'middle'),
                ('font-size', '8pt'),
                ('background-color', 'white'),
                ('color', 'black')
            ]},
            {'selector': 'td > img', 'props': [('max-width', 'unset')]},
            {'selector': 'th[colspan]', 'props': [
                ('border-bottom', '1px solid #ccc'),
                ('font-weight', 'bold')
            ]}
        ])
    )

    return display(HTML(styled.to_html(index=False, border=0, escape=False)))


def table07():

    # Caminho para a pasta de dados
    rootPath = os.path.dirname(os.getcwd())
    
    # Lendo o csv
    aqmData = pd.read_csv(rootPath+'/data/Monitoramento_QAr_BR.csv')

    aqmData['ID_OEMA'] = aqmData['ID_OEMA'].str.replace(' ', '') 
    
    # Selecionando apenas Estado e Fonte e removendo redundâncias
    #aqmData = aqmData.drop_duplicates(subset=['ID_OEMA'])
    #print(aqmData.head())
    
    # Selecionando apenas Estado e Fonte e removendo redundâncias
    aqmData['POLUENTE'] = aqmData['POLUENTE'].str.upper() 
    aqmData = aqmData.groupby('UF')['POLUENTE'].value_counts().unstack(fill_value=0)
    numeric_cols = aqmData.select_dtypes(include=['number']).columns
    aqmData[numeric_cols] = aqmData[numeric_cols].astype('Int64')
    aqmData.loc['BR']= aqmData.sum()
    # Ordenando por região
    # Create two mappings:
    # Region name per UF
    uf_to_region = {uf: Regiao for Regiao, ufs in regioes.items() for uf in ufs}
    
    df_index,uf_to_region,uf_order = tableReorder(regioes)

    # Atualizando o df com todos os estados
    aqmData = df_index.merge(aqmData, left_on='UF', right_on='UF',how='left')
    
    
    # Add columns to the DataFrame
    aqmData['REGIAO'] = aqmData['UF'].map(uf_to_region)
    aqmData['ORDEM'] = aqmData['UF'].map(uf_order)

    #Create a new column with HTML img tag
    aqmData['FLAG'] = aqmData['UF'].apply(
        lambda uf: f'<img src= "../_static/bandeiras/{uf}.png" width="20">'
    ).astype(str)

        
    # Sort by region order and then by UF order
    aqmData = aqmData.sort_values('ORDEM').drop(columns='ORDEM').reset_index(drop=True)
    #print(numeric_cols)
    aqmDisplay = aqmData.copy()
    aqmDisplay = aqmDisplay.fillna(0)
    aqmDisplay.rename(columns={'FLAG': ''}, inplace=True)

    rows = []
    for group, data in aqmDisplay.groupby('REGIAO', sort=False):
        rows.append({'': '', 'UF': group})  
        rows.extend(data.to_dict('records'))
        # Add separator row: None or '' to create empty row
        rows.append({'': '', 'UF': ''})  
    
    # Add a blank row at the beginningí
    blank_row = {'': '', 'UF': ''}
    rows.insert(0, blank_row)
        
    df_with_separators = pd.DataFrame(rows)
    df_with_separators = df_with_separators.drop(columns=['REGIAO'])
    
    #df_with_separators = df_with_separators.style.apply(style_all_white, axis=1)
    df_with_separators[numeric_cols]  = df_with_separators[numeric_cols].apply(pd.to_numeric, errors='coerce')
    df_with_separators[numeric_cols] = df_with_separators[numeric_cols].fillna(999999).astype(int)
    df_with_separators= df_with_separators.replace(999999, '')
    df_with_separators= df_with_separators.replace(0, '-')
    df_with_separators = columns_renamer(df_with_separators)
    df_with_separators = columns_renamer_csv(df_with_separators)
    # --- Correção antes de aplicar o estilo ---
    df_with_separators = (
        df_with_separators
        .reset_index(drop=True)  # Garante índice único
        .loc[:, ~df_with_separators.columns.duplicated()]  # Remove colunas duplicadas
    )

    styled = (
        df_with_separators
        .style
        .apply(style_all_white, axis=1)
        .hide(axis="index")  # ✅ hide the index column
        .set_table_styles([
        {'selector': 'th', 'props': [
            ('text-align', 'center'),
            ('font-size', '7pt')  # change font size here
        ]},  # center header text
            {'selector': 'td > img', 'props': [('max-width', 'unset')]}
    ])
    )

    return display(HTML(styled.to_html(index=False, border=0,escape=False)))


def table07MMA():
    # Caminho para a pasta de dados
    rootPath = os.path.dirname(os.getcwd())
    
    # Lendo o csv
    aqmData = pd.read_csv(rootPath+'/data/Monitoramento_QAr_BR.csv')

    # --- NOVA LÓGICA DE FILTRO ---
    # Garante que não haja espaços em branco extras e filtra apenas 'Ativa'
    # Se os dados estiverem sujos (ex: 'ativa', 'ATIVA'), adicione .str.capitalize() antes da comparação
    if 'STATUS' in aqmData.columns:
        aqmData = aqmData[aqmData['STATUS'].str.strip() == 'Ativa']
    # -----------------------------

    aqmData['ID_OEMA'] = aqmData['ID_OEMA'].str.replace(' ', '') 
    
    # Selecionando apenas Estado e Fonte e removendo redundâncias
    aqmData['POLUENTE'] = aqmData['POLUENTE'].str.upper() 
    
    # O filtro de STATUS deve ter ocorrido antes desta linha:
    aqmData = aqmData.groupby('UF')['POLUENTE'].value_counts().unstack(fill_value=0)
    
    numeric_cols = aqmData.select_dtypes(include=['number']).columns
    aqmData[numeric_cols] = aqmData[numeric_cols].astype('Int64')
    aqmData.loc['BR']= aqmData.sum()

    # Ordenando por região
    # Create two mappings:
    # Region name per UF
    # Certifique-se que 'regioes' e 'tableReorder' estão definidos no escopo global ou importados
    uf_to_region = {uf: Regiao for Regiao, ufs in regioes.items() for uf in ufs}
    
    df_index, uf_to_region, uf_order = tableReorder(regioes)

    # Atualizando o df com todos os estados
    aqmData = df_index.merge(aqmData, left_on='UF', right_on='UF', how='left')
    
    # Add columns to the DataFrame
    aqmData['REGIAO'] = aqmData['UF'].map(uf_to_region)
    aqmData['ORDEM'] = aqmData['UF'].map(uf_order)

    # Create a new column with HTML img tag
    aqmData['FLAG'] = aqmData['UF'].apply(
        lambda uf: f'<img src= "../_static/bandeiras/{uf}.png" width="20">'
    ).astype(str)

        
    # Sort by region order and then by UF order
    aqmData = aqmData.sort_values('ORDEM').drop(columns='ORDEM').reset_index(drop=True)
    
    aqmDisplay = aqmData.copy()
    # Preenche com 0 porque estados sem estações ativas ficaram como NaN após o merge
    aqmDisplay = aqmDisplay.fillna(0) 
    aqmDisplay.rename(columns={'FLAG': ''}, inplace=True)

    rows = []
    for group, data in aqmDisplay.groupby('REGIAO', sort=False):
        rows.append({'': '', 'UF': group})  
        rows.extend(data.to_dict('records'))
        # Add separator row: None or '' to create empty row
        rows.append({'': '', 'UF': ''})  
    
    # Add a blank row at the beginning
    blank_row = {'': '', 'UF': ''}
    rows.insert(0, blank_row)
        
    df_with_separators = pd.DataFrame(rows)
    df_with_separators = df_with_separators.drop(columns=['REGIAO'])
    
    df_with_separators[numeric_cols] = df_with_separators[numeric_cols].apply(pd.to_numeric, errors='coerce')
    df_with_separators[numeric_cols] = df_with_separators[numeric_cols].fillna(999999).astype(int)
    df_with_separators = df_with_separators.replace(999999, '')
    df_with_separators = df_with_separators.replace(0, '-')
    
    # Funções auxiliares (assumindo que existem no seu código original)
    df_with_separators = columns_renamer(df_with_separators)
    df_with_separators = columns_renamer_csv(df_with_separators)
    
    # --- Correção antes de aplicar o estilo ---
    df_with_separators = (
        df_with_separators
        .reset_index(drop=True)  # Garante índice único
        .loc[:, ~df_with_separators.columns.duplicated()]  # Remove colunas duplicadas
    )

    styled = (
        df_with_separators
        .style
        .apply(style_all_white, axis=1)
        .hide(axis="index") 
        .set_table_styles([
        {'selector': 'th', 'props': [
            ('text-align', 'center'),
            ('font-size', '7pt') 
        ]}, 
            {'selector': 'td > img', 'props': [('max-width', 'unset')]}
    ])
    )

    return display(HTML(styled.to_html(index=False, border=0, escape=False)))

def table07MMA2():
    import os
    import pandas as pd

    # Caminho para a pasta de dados
    rootPath = os.path.dirname(os.getcwd())
    aqmData = pd.read_csv(rootPath+'/data/Monitoramento_QAr_BR.csv')

    # ============================================================
    # 1) LIMPEZA DO ID
    # ============================================================
    aqmData['ID_OEMA'] = aqmData['ID_OEMA'].astype(str).str.replace(' ', '')

    # ============================================================
    # 2) PARSE DE ANOS_MONITORADOS (VERSÃO CORRETA)
    # ============================================================
    def parse_anos(x):
        try:
            return [
                int(z) for z in str(x)
                .replace('[','').replace(']','').replace("'",'')
                .split(',') if z.strip().isdigit()
            ]
        except:
            return []

    aqmData['ANOS_MONITORADOS'] = aqmData['ANOS_MONITORADOS'].apply(parse_anos)

    # ============================================================
    # 3) FILTRAR APENAS ESTAÇÕES QUE MONITORARAM EM **2024**
    # ============================================================
    aqmData = aqmData[aqmData['ANOS_MONITORADOS'].apply(lambda anos: 2024 in anos)]

    # ============================================================
    # 4) REMOVER DUPLICIDADES
    # ============================================================
    aqmData = aqmData.drop_duplicates(subset=['ID_OEMA'])

    # ============================================================
    # 5) STATUS = ATIVA  (depois do filtro 2024!)
    # ============================================================
    if 'STATUS' in aqmData.columns:
        aqmData['STATUS'] = aqmData['STATUS'].astype(str).str.strip().str.capitalize()
        aqmData = aqmData[aqmData['STATUS'] == 'Ativa']

    # ============================================================
    # 6) NORMALIZA POLUENTE
    # ============================================================
    aqmData['POLUENTE'] = aqmData['POLUENTE'].astype(str).str.upper()

    # ============================================================
    # 7) AGRUPAMENTO UF × POLUENTE
    # ============================================================
    aqmData = aqmData.groupby('UF')['POLUENTE'].value_counts().unstack(fill_value=0)

    numeric_cols = aqmData.select_dtypes(include=['number']).columns
    aqmData[numeric_cols] = aqmData[numeric_cols].astype('Int64')

    # Total Brasil
    aqmData.loc['BR'] = aqmData.sum()

    # ============================================================
    # 8) REORDENAÇÃO POR REGIÕES E BANDEIRAS
    # ============================================================
    df_index, uf_to_region, uf_order = tableReorder(regioes)
    aqmData = df_index.merge(aqmData, left_on='UF', right_on='UF', how='left')

    aqmData['REGIAO'] = aqmData['UF'].map(uf_to_region)
    aqmData['ORDEM'] = aqmData['UF'].map(uf_order)

    aqmData['FLAG'] = aqmData['UF'].apply(
        lambda uf: f'<img src="../_static/bandeiras/{uf}.png" width="20">'
    )

    aqmData = aqmData.sort_values('ORDEM').drop(columns='ORDEM').reset_index(drop=True)

    # ============================================================
    # 9) FORMATAÇÃO FINAL
    # ============================================================
    aqmDisplay = aqmData.fillna(0).copy()
    aqmDisplay.rename(columns={'FLAG': ''}, inplace=True)

    rows = []
    for group, data in aqmDisplay.groupby('REGIAO', sort=False):
        rows.append({'': '', 'UF': group})
        rows.extend(data.to_dict('records'))
        rows.append({'': '', 'UF': ''})

    rows.insert(0, {'': '', 'UF': ''})

    df_with_separators = pd.DataFrame(rows).drop(columns=['REGIAO'])

    df_with_separators[numeric_cols] = (
        df_with_separators[numeric_cols]
        .apply(pd.to_numeric, errors='coerce')
        .fillna(999999)
        .astype(int)
    )

    df_with_separators = df_with_separators.replace(999999, '').replace(0, '-')

    df_with_separators = columns_renamer(df_with_separators)
    df_with_separators = columns_renamer_csv(df_with_separators)

    df_with_separators = (
        df_with_separators
        .reset_index(drop=True)
        .loc[:, ~df_with_separators.columns.duplicated()]
    )

    styled = (
        df_with_separators
        .style
        .apply(style_all_white, axis=1)
        .hide(axis="index")
        .set_table_styles([
            {'selector': 'th', 'props': [
                ('text-align', 'center'),
                ('font-size', '7pt')
            ]},
            {'selector': 'td > img', 'props': [('max-width', 'unset')]}
        ])
    )

    return display(HTML(styled.to_html(index=False, border=0, escape=False)))
def tabela_iterativa(aqmData, searchPaneColumns):
    """
    Create an interactive HTML table for air quality monitoring data with search panes and export options.

    This function formats a pandas DataFrame into an interactive table using the `itables` package.
    It configures visual aspects such as column alignment, font size, export buttons, and dynamic search panes
    to enhance user experience within Jupyter notebooks.

    Parameters
    ----------
    aqmData : pandas.DataFrame
        The input DataFrame containing monitoring station data to be displayed.

    searchPaneColumns : list of int
        A list of column indices to include in the search panes. These allow filtering based on distinct values
        in selected columns.

    Returns
    -------
    itables.javascript.Javascript
        An interactive table rendered in a Jupyter notebook environment. Includes features like column toggling,
        CSV/Excel export, and live filtering.

    Notes
    -----
    - Requires the `itables` library with Jupyter notebook support.
    - The function disables HTML escaping to allow for rendering of HTML content (e.g., embedded flags).
    - The `searchPanes` feature allows users to filter data using dropdown panes for selected columns.
    - Global visual configurations are set using `itables.options` (e.g., font size, width, alignment).
    - Export buttons available: Copy, CSV, Excel, and Column Visibility toggle.
    - Column indices in `searchPaneColumns` should match the visible columns in `aqmData`.

    Examples
    --------
    >>> tabela_iterativa(df, searchPaneColumns=[1, 2, 3])
    """
    
    init_notebook_mode(all_interactive=True)
    opt.maxBytes = 0
    # Configure global options
    opt.classes = "display compact stripe"
    # Larguras automáticas conforme número de colunas
    n_cols = aqmData.shape[1]
    
    if n_cols == 7:
        opt.columnDefs = [
            {"targets": "_all", "className": "dt-right"},
            {"targets": [0], "width": "60px"},   # Bandeira ou ícone
            {"targets": [1], "width": "60px"},   # UF
            {"targets": [2], "width": "100px"},   # ID_OEMA
            {"targets": [3], "width": "120px"},  # Poluente
            {"targets": [4,5,6], "width": "80px"} # Categoria, Funcionamento
        ]
    
    elif n_cols == 8:
        opt.columnDefs = [
            {"targets": "_all", "className": "dt-right"},
            {"targets": [0], "width": "60px"},
            {"targets": [1], "width": "60px"},
            {"targets": [2], "width": "100px"},
            {"targets": [3], "width": "120px"},
            {"targets": [4, 5, 6, 7], "width": "80px"}  # Categoria, Funcionamento, Finalidade
        ]
    else:
        # fallback genérico
        opt.columnDefs = [{"targets": "_all", "className": "dt-right"}]

    opt.style = "font-size: 11px; white-space: normal;div.dt-buttons button {font-size: 10px !important; padding: 4px 6px;"  # Apply font size and enable wrapping
    opt.lengthMenu = [5, 10, 25]

    custom_style = """
    /* Removendo os estilos anteriores do campo de busca */
    div.dt-search > input {
      all: unset !important
    }
    
    /* Reestilizando campo de busca */
    div.dt-search > input {
          /* background-color: #FFFFFF !important; */
          border: 1px solid rgba(27, 31, 35, 0.15) !important;
          border-radius: 6px !important;
          padding: .5em .4em !important;
          margin-left: 0.6em !important;
          
    }

    /* Reestilizando itens de navegação entre páginas */
    nav > .dt-paging-button {
      background-color: transparent;
      border: 1px solid rgba(27, 31, 35, 0.15) !important;
      border-radius: 6px !important;
        
    }
    nav > .current {
      background-color: #F3F4F6 !important;
      text-decoration: none !important;
      transition-duration: 0.1s !important;
    }

    /* Removendo os estilos anteriores dos botões */
    div.dt-buttons > .dt-button,
    div.dt-buttons > .dt-button:hover,
    div.dt-buttons > .dt-button:disabled,
    div.dt-buttons > .dt-button:active,
    div.dt-buttons > .dt-button:focus,
    div.dt-buttons > .dt-button:before,
    div.dt-buttons > .dt-button:hover:not(.disabled),
    div.dt-buttons > .dt-button:focus:not(.disabled),
    div.dt-buttons > .dt-button:active:not(.disabled),
    div.dt-buttons > .dt-button:-webkit-details-marker {
      all: unset !important;
    } 

    /* Reestilizando botões */
    div.dt-buttons > .dt-button {
      appearance: none !important;
      background-color: #FAFBFC !important;
      border: 1px solid rgba(27, 31, 35, 0.15) !important;
      border-radius: 6px !important;
      box-shadow: rgba(27, 31, 35, 0.04) 0 1px 0, rgba(255, 255, 255, 0.25) 0 1px 0 inset !important;
      box-sizing: border-box !important;
      color: #24292E !important;
      cursor: pointer !important;
      display: inline-block !important;
      font-family: -apple-system, system-ui, "Segoe UI", Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji" !important;
      font-size: 14px !important;
      font-weight: 500 !important;
      line-height: 20px !important;
      list-style: none !important;
      padding: 6px 16px !important;
      position: relative !important;
      transition: background-color 0.2s cubic-bezier(0.3, 0, 0.5, 1) !important;
      user-select: none !important;
      -webkit-user-select: none !important;
      touch-action: manipulation !important;
      vertical-align: middle !important;
      white-space: nowrap !important;
      word-wrap: break-word !important;
      background: unset !important;
    }
    
    div.dt-buttons > .dt-button:hover {
      background-color: #F3F4F6 !important;
      text-decoration: none !important;
      transition-duration: 0.1s !important;
    }
    
    div.dt-buttons > .dt-button:disabled {
      background-color: #FAFBFC !important;
      border-color: rgba(27, 31, 35, 0.15) !important;
      color: #959DA5 !important;
      cursor: default !important;
    }
    
    div.dt-buttons > .dt-button:active {
      background-color: #EDEFF2 !important;
      box-shadow: rgba(225, 228, 232, 0.2) 0 1px 0 inset !important;
      transition: none 0s !important;
    }
    
    div.dt-buttons > .dt-button:focus {
      outline: 1px transparent !important;
    }
    
    div.dt-buttons > .dt-button:before {
      display: none !important;
    }
    
    div.dt-buttons > .dt-button:-webkit-details-marker {
      display: none !important;
    } 
    """

    display(HTML(f"<style>{custom_style}</style>" ""))

    
    return show(aqmData, 
             #buttons=["copyHtml5", "csvHtml5", "excelHtml5","columnsToggle"],
             buttons=["copyHtml5", "csvHtml5"],
             layout={"top2": "searchPanes"},
             searchPanes={"layout": "columns-3", "cascadePanes": True, "columns": searchPaneColumns},
             allow_html=True,
             keys=True,
             escape=False,
             index=False,)
             #style="table-layout:auto;width:auto;margin:auto;caption-side:bottom")


def flagTable(columnsSelector):

    """
    Generate a formatted DataFrame of air quality monitoring stations with flags and pollutant counts.

    This function reads air quality monitoring data from a CSV file, cleans and processes it, aggregates
    pollutants by station, and returns a customized DataFrame with selected columns. It also generates
    an HTML image tag for each Brazilian state's flag and counts the number of pollutants measured at
    each station.

    Parameters
    ----------
    columnsSelector : list of str
        A list of column names to include in the final output table. This should be a subset of the
        columns in the processed DataFrame after renaming (e.g., ["FLAG", "UF", "ID_OEMA", ...]).

    Returns
    -------
    pandas.DataFrame
        A formatted DataFrame including selected columns, with added columns for flags and number of
        pollutants measured. The DataFrame is ready for display in HTML or static reports.

    Notes
    -----
    - The data is read from a file located at: `../data/Monitoramento_QAr_BR.csv`, relative to the current working directory.
    - The column `POLUENTE` is aggregated by grouping over all other columns and combining the pollutant names.
    - A flag image is generated per `UF` (federative unit) using the path `"../_static/bandeiras/{UF}.png"`.
    - The number of pollutants per station is computed and stored in the column `"N° Poluentes Medidos"`.
    - The function uses a global helper `columns_renamer()` to rename columns based on a predefined dictionary.
    - Columns with all `NaN` values are removed before processing.
    """
    
    # Caminho para a pasta de dados
    rootPath = os.path.dirname(os.getcwd())
    
    # Lendo o csv
    aqmData = pd.read_csv(rootPath+'/data/Monitoramento_QAr_BR.csv')
    aqmData['ID_OEMA'] = aqmData['ID_OEMA'].str.replace(' ', '') 
    aqmData['POLUENTE'] = aqmData['POLUENTE'].str.upper()
    #aqmData['CATEGORIA'] = aqmData['CATEGORIA'].str.replace(' ', '') 
    aqmData.loc[aqmData['CATEGORIA']=='N','CATEGORIA'] = 'Não identificada' 

    # Remove colunas com todos valores iguais a NaN
    #aqmData = aqmData.dropna(axis=1, how='all')
    aqmData = aqmData.fillna('-')
    
    remaining_columns = aqmData.columns[(aqmData.columns != 'POLUENTE') & (aqmData.columns != 'ID_MMA_COMPLETO') & (aqmData.columns != 'COD_POLUENTE') & 
        (aqmData.columns != 'CALIBRACAO') & (aqmData.columns != 'ANOS_MONITORADOS')
        & (aqmData.columns != 'INICIO') & (aqmData.columns != 'FIM') & (aqmData.columns != 'BASE_DADOS')].tolist()
    #print(remaining_columns)
    
    # Agrupamento por estado quando tivermos mais de uma fonte de informação
    aqmDataGrouped = aqmData.groupby(remaining_columns).agg({
        'POLUENTE': lambda x: ', '.join(x),
    }).reset_index()
    #print(aqmDataGrouped)
    
    #Create a new column with HTML img tag
    aqmDataGrouped['FLAG'] = aqmDataGrouped['UF'].apply(
        lambda uf: f'<img src= "../_static/bandeiras/{uf}.png" width="30">'
    ).astype(str)

     # Cria uma coluna com número de poluentes medidos
    aqmDataGrouped['N° Poluentes Medidos'] = aqmDataGrouped['POLUENTE'].apply(lambda x: len(x.split(',')))
    
    #aqmDataGrouped = aqmDataGrouped[['FLAG','UF','ID_OEMA','LATITUDE','LONGITUDE','CATEGORIA','FUNCIONAMENTO','N° Poluentes Medidos', 'POLUENTE' ]]
    aqmDataGrouped = columns_renamer(aqmDataGrouped)

    # Seleciona as colunas para uso    
    aqmDataGrouped = aqmDataGrouped[columnsSelector]
    aqmDataGrouped = aqmDataGrouped.replace('Nao declarado','Não declarado')
    aqmDataGrouped = aqmDataGrouped.replace('-','Não declarado')
    aqmDataGrouped = aqmDataGrouped.replace('Referencia','Referência')
    return aqmDataGrouped

def flagTable2(columnsSelector):

    """
    Generate a formatted DataFrame of air quality monitoring stations with flags and pollutant counts.

    This function reads air quality monitoring data from a CSV file, cleans and processes it, aggregates
    pollutants by station, and returns a customized DataFrame with selected columns. It also generates
    an HTML image tag for each Brazilian state's flag and counts the number of pollutants measured at
    each station.

    Parameters
    ----------
    columnsSelector : list of str
        A list of column names to include in the final output table. This should be a subset of the
        columns in the processed DataFrame after renaming (e.g., ["FLAG", "UF", "ID_OEMA", ...]).

    Returns
    -------
    pandas.DataFrame
        A formatted DataFrame including selected columns, with added columns for flags and number of
        pollutants measured. The DataFrame is ready for display in HTML or static reports.

    Notes
    -----
    - The data is read from a file located at: `../data/Monitoramento_QAr_BR.csv`, relative to the current working directory.
    - The column `POLUENTE` is aggregated by grouping over all other columns and combining the pollutant names.
    - A flag image is generated per `UF` (federative unit) using the path `"../_static/bandeiras/{UF}.png"`.
    - The number of pollutants per station is computed and stored in the column `"N° Poluentes Medidos"`.
    - The function uses a global helper `columns_renamer()` to rename columns based on a predefined dictionary.
    - Columns with all `NaN` values are removed before processing.
    """
    
    # Caminho para a pasta de dados
    rootPath = os.path.dirname(os.getcwd())
    
    # Lendo o csv
    aqmData = pd.read_csv(rootPath+'/data/Monitoramento_QAr_BR.csv')
    aqmData['ID_OEMA'] = aqmData['ID_OEMA'].str.replace(' ', '') 
    aqmData['POLUENTE'] = aqmData['POLUENTE'].str.upper()
    #aqmData['CATEGORIA'] = aqmData['CATEGORIA'].str.replace(' ', '') 
    aqmData.loc[aqmData['CATEGORIA']=='N','CATEGORIA'] = 'Não identificada' 

    # Remove colunas com todos valores iguais a NaN
    #aqmData = aqmData.dropna(axis=1, how='all')
    aqmData = aqmData.fillna('-')
    remaining_columns = aqmData.columns[(aqmData.columns != 'POLUENTE') & (aqmData.columns != 'ID_MMA_COMPLETO') & (aqmData.columns != 'COD_POLUENTE') & 
        (aqmData.columns != 'ANOS_MONITORADOS')
        & (aqmData.columns != 'INICIO') & (aqmData.columns != 'FIM')].tolist()
    #print(remaining_columns)
    
    # Agrupamento por estado quando tivermos mais de uma fonte de informação
    aqmDataGrouped = aqmData.groupby(remaining_columns).agg({
        'POLUENTE': lambda x: ', '.join(x),
    }).reset_index()
    #print(aqmDataGrouped)
    
    #Create a new column with HTML img tag
    aqmDataGrouped['FLAG'] = aqmDataGrouped['UF'].apply(
        lambda uf: f'<img src= "../_static/bandeiras/{uf}.png" width="30">'
    ).astype(str)

     # Cria uma coluna com número de poluentes medidos
    aqmDataGrouped['N° Poluentes Medidos'] = aqmDataGrouped['POLUENTE'].apply(lambda x: len(x.split(',')))
    
    #aqmDataGrouped = aqmDataGrouped[['FLAG','UF','ID_OEMA','LATITUDE','LONGITUDE','CATEGORIA','FUNCIONAMENTO','N° Poluentes Medidos', 'POLUENTE' ]]
    aqmDataGrouped = columns_renamer(aqmDataGrouped)

    # Seleciona as colunas para uso    
    aqmDataGrouped = aqmDataGrouped[columnsSelector]
    aqmDataGrouped = aqmDataGrouped.replace('Nao declarado','Não declarado')
    aqmDataGrouped = aqmDataGrouped.replace('-','Não declarado')
    aqmDataGrouped = aqmDataGrouped.replace('Referencia','Referência')
    return aqmDataGrouped


def flagTable3(columnsSelector):
    """
    Generate a formatted DataFrame of air quality monitoring stations with flags and pollutant counts.
    """

    import os
    import pandas as pd

    # Caminho para a pasta de dados
    rootPath = os.path.dirname(os.getcwd())

    # Lendo o CSV
    aqmData = pd.read_csv(rootPath + '/data/Monitoramento_QAr_BR.csv')
    aqmData['ID_OEMA'] = aqmData['ID_OEMA'].astype(str).str.replace(' ', '')
    aqmData['POLUENTE'] = aqmData['POLUENTE'].astype(str).str.upper()
    aqmData.loc[aqmData['CATEGORIA'] == 'N', 'CATEGORIA'] = 'Não identificada'

    # Substitui NaN por hífen
    aqmData = aqmData.fillna('-')

    # === 🔧 Converte booleanos em texto Sim/Não ===
    if 'BASE_DADOS' in aqmData.columns:
        aqmData['BASE_DADOS'] = aqmData['BASE_DADOS'].replace({True: 'Sim', False: 'Não'})

    # === Mantém a coluna BASE_DADOS no agrupamento ===
    remaining_columns = aqmData.columns[
        (aqmData.columns != 'POLUENTE') &
        (aqmData.columns != 'ID_MMA_COMPLETO') &
        (aqmData.columns != 'COD_POLUENTE') &
        (aqmData.columns != 'CALIBRACAO') &
        (aqmData.columns != 'ANOS_MONITORADOS') &
        (aqmData.columns != 'INICIO') &
        (aqmData.columns != 'FIM')
    ].tolist()

    # Agrupamento mantendo BASE_DADOS
    aqmDataGrouped = aqmData.groupby(remaining_columns).agg({
        'POLUENTE': lambda x: ', '.join(x),
    }).reset_index()

    # Cria coluna de bandeira
    aqmDataGrouped['FLAG'] = aqmDataGrouped['UF'].apply(
        lambda uf: f'<img src="../_static/bandeiras/{uf}.png" width="30">'
    )

    # Cria coluna com número de poluentes medidos
    aqmDataGrouped['N° Poluentes Medidos'] = aqmDataGrouped['POLUENTE'].apply(lambda x: len(x.split(',')))

    # Renomeia colunas conforme dicionário global
    aqmDataGrouped = columns_renamer(aqmDataGrouped)

    # === 🔧 Padroniza nome da coluna de base de dados ===
    for col in aqmDataGrouped.columns:
        if col.strip().lower() in ['base_dados', 'base de dados']:
            aqmDataGrouped = aqmDataGrouped.rename(columns={col: 'Base de dados'})
            break
    if 'BASE_DADOS' in aqmDataGrouped.columns:
        aqmDataGrouped = aqmDataGrouped.rename(columns={'BASE_DADOS': 'Base de dados'})

    # === Ajuste de colunas existentes ===
    missing_cols = [c for c in columnsSelector if c not in aqmDataGrouped.columns]
    if missing_cols:
        print(f"⚠️ Colunas ausentes ignoradas: {missing_cols}")
        columnsSelector = [c for c in columnsSelector if c in aqmDataGrouped.columns]

    # Seleciona colunas
    aqmDataGrouped = aqmDataGrouped[columnsSelector]

    # Correções de texto
    aqmDataGrouped = aqmDataGrouped.replace({
        'Nao declarado': 'Não declarado',
        '-': 'Não declarado',
        'Referencia': 'Referência'
    })

    return aqmDataGrouped
