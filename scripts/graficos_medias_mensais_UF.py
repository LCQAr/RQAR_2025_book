# -*- coding: utf-8 -*-
"""
Created on Tue Jul 22 09:56:06 2025

@author: marzados
    
"""
#%% Bibliotecas utilizadas

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from pathlib import Path

#%%
def tratar_dados(df):
    """
    Recebe DataFrame cru, cria coluna datetime, converte e limpa valores.
    Retorna DataFrame com índice datetime e coluna 'Valor' em float, valores < 0 viram NaN.

    Parameters
    ----------
    df : TYPE
        DF contendo dados brutos com colunas, sem coluna de datetime .

    Returns
    -------
    df : TYPE
        DataFrame tratado com indice de datetime e valores numéricos prontos para análise.

    """
    # Criar datetime conforme colunas disponíveis
    if {'Hora', 'Minuto'}.issubset(df.columns):
        df['datetime'] = df[['Ano', 'Mes', 'Dia', 'Hora', 'Minuto']].apply(
            lambda x: datetime(x['Ano'], x['Mes'], x['Dia'], x['Hora'], x['Minuto']), axis=1)
    elif {'Hora'}.issubset(df.columns):
        df['datetime'] = df[['Ano', 'Mes', 'Dia', 'Hora']].apply(
            lambda x: datetime(x['Ano'], x['Mes'], x['Dia'], x['Hora']), axis=1)
    else:
        df['datetime'] = df[['Ano', 'Mes', 'Dia']].apply(
            lambda x: datetime(x['Ano'], x['Mes'], x['Dia']), axis=1)

    df = df.set_index('datetime')
    # Substitui , por . 
    df['Valor'] = df['Valor'].replace(',', '.', regex=True)
    # Converte para float, forçando erro para NaN
    df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce')
    # Transforma valores negativos em NaN
    df.loc[df['Valor'] < 0, 'Valor'] = np.nan
    return df


#%%
def gerar_graficos_mensais(pasta_dados: str, ano):
    """
    Gera gráficos com a variação mensal da concentração média dos poluentes para cada UF.

    Para cada arquivo de estado presente na pasta, esta função:
        - Lê os dados e os trata com a função tratar_dados().
        - Agrupa as médias mensais por poluente e por ano.
        - Plota um gráfico (subplot) para cada poluente no ano especificado.
        - Salva as figuras na pasta figures/medias_mensais_UF.

    Parameters
    ----------
    pasta_dados : str
        caminho para a pasta que contem os arquivos .xlsx com dados por Estado.
    ano : TYPE
        Ano de interesse para geração dos gráficos.

    Returns
    -------
    None.

    """
  
    pasta = Path(pasta_dados)

    cores_poluentes = {
        'CO': 'b',
        'NO2': 'g',
        'SO2': 'r',
        'O3': 'c',
        'MP10': 'm',
        'NOX': 'y',
        'NO': 'k'
    }

    for arquivo in pasta.glob("*.xlsx"):
        uf = arquivo.stem
        print(f"\n📊 Processando estado: {uf}")
        
        try:
            df = pd.read_excel(arquivo)

            # Pré-processamento
            df = tratar_dados(df)
            df['Ano'] = df.index.year
            df['Mes'] = df.index.month

            poluentes = df['Poluente'].dropna().unique()
            if len(poluentes) == 0:
                print(f"⚠️ Nenhum poluente encontrado para {uf}")
                continue

            # Criar subplots com 1 linha por poluente
            fig, axs = plt.subplots(nrows=len(poluentes), figsize=(9, 4 * len(poluentes)), sharex=True)

            # Se só houver 1 poluente, axs não será uma lista, forçamos isso:
            if len(poluentes) == 1:
                axs = [axs]

            for i, polu in enumerate(poluentes):
                df_poluente = df[df['Poluente'] == polu]
                media_mensal = df_poluente.groupby(['Ano', 'Mes'])['Valor'].mean().unstack(fill_value=0)

                if ano not in media_mensal.index:
                    axs[i].set_title(f"{polu} - Sem dados para {ano}")
                    continue

                axs[i].plot(
                    media_mensal.columns,
                    media_mensal.loc[ano],
                    label=polu,
                    color=cores_poluentes.get(polu, 'gray'),
                    marker='o'
                )
                axs[i].set_title(f'{uf} - {polu} - {ano}')
                axs[i].set_ylabel('Concentração média')
                axs[i].grid(True)
                axs[i].legend(loc='upper right')

            # Eixo X apenas no último subplot
            axs[-1].set_xlabel('Mês')
            axs[-1].set_xticks(range(1, 13))

            plt.tight_layout()
            # Criar pasta de saída se não existir
            saida_dir = Path("figures/medias_mensais_UF")
            saida_dir.mkdir(exist_ok=True)

            # Nome do arquivo a ser salvo
            nome_arquivo = f"{uf}_{ano}_variacao_mensal.png"
            plt.savefig(saida_dir / nome_arquivo, dpi=300, bbox_inches='tight')
        #    plt.show()

        except Exception as e:
            print(f"⚠️ Erro ao processar {uf}: {e}")

#%% MAIN  

# Caminho da pasta onde estão os arquivos .xlsx
dados = r"C:\PYTHON\ENS5132\ENS5132\MMA\inputs\dados_Formatados"

# Ano que você quer analisar
ano_analise = 2023

# Chama a função que gera os gráficos (ela já usa tratar_dados internamente)
gerar_graficos_mensais(dados, ano_analise)



