#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Sep 11 10:45:33 2024

@author: leohoinaski
"""

#-----------------------------Importação de pacotes ------------------------------------


import os
import pandas as pd
import matplotlib.pyplot as plt
import ipywidgets as widgets
from IPython.display import display, clear_output
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings
warnings.filterwarnings('ignore')


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
    

    # Substitui , por . 
    df['VALOR'] = df['VALOR'].replace(',', '.', regex=True).copy()
    # Converte para float, forçando erro para NaN
    df['VALOR'] = pd.to_numeric(df['VALOR'], errors='coerce').copy()
    # Transforma valores negativos em NaN
    df.loc[df['VALOR'] < 0, 'VALOR'] = np.nan
    df['DATETIME'] = pd.to_datetime(df['DATETIME'], errors='coerce', infer_datetime_format=True)
    time_range = pd.date_range(df['DATETIME'].min(), df['DATETIME'].max(), freq='h').to_series(name='DATETIME')
    df = pd.merge(time_range, df,how='left')
    #df = df.set_index('datetime', drop=False)
    df['DATETIME'] = pd.to_datetime(df['DATETIME']).copy()
    return df

def split_nan_segments(x, y):
    """Splits x and y into segments where y is not NaN"""
    segments = []
    x = np.array(x)
    y = np.array(y)
    
    isnan = np.isnan(y)
    start = 0
    for i in range(1, len(y)):
        if isnan[i] and not isnan[i-1]:
            segments.append((x[start:i], y[start:i]))
            start = i + 1
        elif not isnan[i] and isnan[i-1]:
            start = i
    if not isnan[-1]:
        segments.append((x[start:], y[start:]))
    return segments

    
def iterative_timeseries(df,row):
    df = tratar_dados(df)
    daily_avg_df = df[['DATETIME','VALOR']].groupby(pd.Grouper(key='DATETIME', freq='D')).quantile(0.50)
    daily_min_df = df[['DATETIME','VALOR']].groupby(pd.Grouper(key='DATETIME', freq='D')).quantile(0.05)
    daily_max_df = df[['DATETIME','VALOR']].groupby(pd.Grouper(key='DATETIME', freq='D')).quantile(0.95)
        
    month_avg_df = df.groupby("MES")["VALOR"].quantile(0.50).reset_index()
    month_min_df = df.groupby("MES")["VALOR"].quantile(0.05).reset_index()
    month_max_df = df.groupby("MES")["VALOR"].quantile(0.95).reset_index()
    
    hourly_min = df.groupby('HORA')[['VALOR']].quantile(0.05)
    hourly_max = df.groupby('HORA')[['VALOR']].quantile(0.95)
    hourly_average = df.groupby('HORA')[['VALOR']].quantile(0.50)

    df['day_of_week_name'] = df['DATETIME'].dt.day_name()
    min_by_day_name = df.groupby('day_of_week_name')[['VALOR']].quantile(0.05)
    max_by_day_name = df.groupby('day_of_week_name')[['VALOR']].quantile(0.95)
    average_by_day_name = df.groupby('day_of_week_name')[['VALOR']].quantile(0.50)
    
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    min_by_day_name = min_by_day_name.reindex(day_order)
    max_by_day_name = max_by_day_name.reindex(day_order)
    average_by_day_name = average_by_day_name.reindex(day_order)
    
    dates = daily_min_df.index

    # Create the figure
    #fig = go.Figure()
    fig = make_subplots(rows=5, cols=1)
    
    # raw
    fig.add_trace(go.Scatter(
        x=df.DATETIME,
        y=df.VALOR,
        mode='lines',
        line=dict(color='rgba(100, 100, 100, 0.5)', width=1),
        name='Séries bruta'
    ), row=5, col=1)
    
    
    # daily 
    segments = split_nan_segments(dates, daily_max_df.VALOR)
    for seg_x, seg_y in segments:
        fig.add_trace(go.Scatter(
            x=seg_x,
            y=seg_y,
            fill='tozeroy',
            line=dict(color='rgba(255, 204, 204,.4)', width=1),
            #fillcolor='rgba(255,255,255,1)',
            fillcolor='rgba(255, 204, 204,.4)',
            #name='Máximo',
            showlegend=False,
            connectgaps=False
        ), row=4, col=1)
    
    fig.add_trace(go.Scatter(
        x=dates,
        y=daily_avg_df.VALOR,
        mode='lines',
        line=dict(color='rgba(255, 0, 0, 1)', width=1), # Red line with 50% opacity
        #name='Média'
        showlegend=False,
    ), row=4, col=1)

    segments = split_nan_segments(dates, daily_min_df.VALOR)
    for seg_x, seg_y in segments:
        fig.add_trace(go.Scatter(
            x=seg_x,
            y=seg_y,
            fill='tozeroy',
            line=dict(color='rgba(255, 204, 204,0.4)', width=2),
            fillcolor='rgba(255,255,255,1)',
            #name='Mínimo',
            showlegend=False,
            connectgaps=False
        ), row=4, col=1)
    

    # montly 
    segments = split_nan_segments(month_max_df.index, month_max_df.VALOR)
    for seg_x, seg_y in segments:
        fig.add_trace(go.Scatter(
            x=seg_x,
            y=seg_y,
            fill='tozeroy',
            line=dict(color='rgba(255, 204, 153, 0.2)', width=1),
            #fillcolor='rgba(255,255,255,1)',
            fillcolor='rgba(255, 204, 153, 0.2)',
            #name='Máximo',
            mode='lines',
            showlegend=False,
            connectgaps=False
        ), row=3, col=1)

    fig.add_trace(go.Scatter(
        x=month_avg_df.index,
        y=month_avg_df.VALOR,
        mode='lines',
        showlegend=False,
        line=dict(color='rgba(255, 165, 0, 1)', width=2), # Red line with 50% opacity
        #name='Média'
    ), row=3, col=1)
    
    segments = split_nan_segments(month_min_df.index, month_min_df.VALOR)
    for seg_x, seg_y in segments:
        fig.add_trace(go.Scatter(
            x=seg_x,
            y=seg_y,
            fill='tozeroy',
            line=dict(color='rgba(255, 204, 153, 0.2)', width=1),
            #fillcolor='rgba(255,255,255,1)',
            fillcolor='rgba(255,255,255,1)',
            #name='Mínimo',
            mode='lines',
            showlegend=False,
            connectgaps=False
        ), row=3, col=1)
    
    
    # week 
    segments = split_nan_segments(max_by_day_name.index, max_by_day_name.VALOR)
    for seg_x, seg_y in segments:
        fig.add_trace(go.Scatter(
            x=seg_x,
            y=seg_y,
            fill='tozeroy',
            line=dict(color='rgba(153, 204, 255, 0.1)', width=1),
            #fillcolor='rgba(255,255,255,1)',
            fillcolor='rgba(153, 204, 255, 0.1)',
            #name='Máximo',
            mode='lines',
            showlegend=False,
            connectgaps=False
        ), row=2, col=1)
    
    fig.add_trace(go.Scatter(
        x=average_by_day_name.index,
        y=average_by_day_name.VALOR,
        mode='lines',
        showlegend=False,
        line=dict(color='rgba(153, 204, 255, 1)', width=2), # Red line with 50% opacity
        #name='Média'
    ), row=2, col=1)

    segments = split_nan_segments(min_by_day_name.index, min_by_day_name.VALOR)
    for seg_x, seg_y in segments:
        fig.add_trace(go.Scatter(
            x=seg_x,
            y=seg_y,
            fill='tozeroy',
            line=dict(color='rgba(153, 204, 255, 0.1)', width=1),
            #fillcolor='rgba(255,255,255,1)',
            fillcolor='rgba(255,255,255,1)',
            showlegend=False,
            #name='Mínimo',
            mode='lines',
            connectgaps=False
        ), row=2, col=1)

    
    # hourly 
        
    segments = split_nan_segments(hourly_max.index, hourly_max.VALOR)
    for seg_x, seg_y in segments:
        fig.add_trace(go.Scatter(
            x=seg_x,
            y=seg_y,
            fill='tozeroy',
            line=dict(color='rgba(153, 153, 255, 0.1)', width=1),
            #fillcolor='rgba(255,255,255,1)',
            fillcolor='rgba(153, 153, 255,0.1)',
            showlegend=False,
            #name='Máximo',
            mode='lines',
            connectgaps=False
        ), row=1, col=1)
    

    
    fig.add_trace(go.Scatter(
        x=hourly_average.index,
        y=hourly_average.VALOR,
        mode='lines',
        showlegend=False,
        line=dict(color='rgba(153, 153, 255, 1)', width=2), # Red line with 50% opacity
        #name='Média'
    ), row=1, col=1)


    segments = split_nan_segments(hourly_min.index, hourly_min.VALOR)
    for seg_x, seg_y in segments:
        fig.add_trace(go.Scatter(
            x=seg_x,
            y=seg_y,
            fill='tozeroy',
            line=dict(color='rgba(153, 153, 255, 0.1)', width=1),
            #fillcolor='rgba(255,255,255,1)',
            fillcolor='rgba(255,255,255,1)',
            showlegend=False,
            #name='Mínimo',
            mode='lines',
            connectgaps=False
        ), row=1, col=1)


    # Update layout for better presentation
    fig.update_layout(
        title=dict(text='ID_MMA: '+row.ID_MMA_COMPLETO+ ' - ID_OEMA: '+row.ID_OEMA+' - Cidade: '+row.CIDADE+
                   '<br> Poluente:'+row.POLUENTE +
                   '<br> Início: '+str(row.INICIO) + '   Fim: '+str(row.FIM)+
                   '<br> Faixa =  5°-95° percentil - Linha = 50° percentil'),
            font=dict(
                size=8,  # Set the desired font size here
                family="Arial",
                color="black"),
        hovermode='x unified', # Shows hover info for all traces at a given x-coordinate
        height=1200, width=800,
        plot_bgcolor='rgba(0.9,0.9,0.9,0.2)',
        showlegend=False)

    #unidade = df.loc[0,"UNIDADE"]
    unidade = '(ug/m³)'
    fig.update_yaxes(title_text="Concentração<br>Médias nas horas<br>"+unidade, row=1, col=1)
    fig.update_xaxes(title_text="Hora", row=1, col=1)

    fig.update_yaxes(title_text="Concentração<br>Médias nos dias da semana<br>"+unidade, row=2, col=1)
    fig.update_xaxes(title_text="Dia da semana", row=2, col=1)

    fig.update_yaxes(title_text="Concentração<br>Médias mensais<br>"+unidade, row=3, col=1)
    fig.update_xaxes(title_text="Mês/Ano", row=3, col=1)

    fig.update_yaxes(title_text="Concentração<br>Médias diárias<br>"+unidade, row=4, col=1)
    fig.update_xaxes(title_text="Dia/Ano", row=4, col=1)

    fig.update_yaxes(title_text="Concentração<br>Série completa"+unidade, row=5, col=1)
    fig.update_xaxes(title_text="Dia/Mês/Ano Hora", row=5, col=1)

    rootPath = os.path.dirname(os.getcwd())
    
    fig.write_html(rootPath+"/_static/plotly_figures/timeSeriesFigures/"+row.ID_MMA_COMPLETO+".html")

    
    return fig


def iterative_raw_timeseries(df):
    df = tratar_dados(df)
    dates = df['DATETIME']

    # Create the figure
    #fig = go.Figure()
    fig = make_subplots(rows=1, cols=1)
    
    # raw

    segments = split_nan_segments(df['DATETIME'], df.VALOR)
    for seg_x, seg_y in segments:
        fig.add_trace(go.Scatter(
            x=seg_x,
            y=seg_y,
            #fill='tozeroy',
            line=dict(color='rgba(153, 153, 255, 1)', width=1),
            #fillcolor='rgba(255,255,255,1)',
            #fillcolor='rgba(153, 153, 255,0.1)',
            showlegend=False,
            name='Série temporal',
            mode='lines',
            connectgaps=False
        ))
    

    # Update layout for better presentation
    fig.update_layout(
        title='Série temporal',
        hovermode='x unified', # Shows hover info for all traces at a given x-coordinate
        height=600, width=800,
        plot_bgcolor='rgba(0.9,0.9,0.9,0.2)')

    unidade = '(ug/m³)'

    fig.update_yaxes(title_text="Concentração<br>Série completa"+unidade, row=5, col=1)
    fig.update_xaxes(title_text="Dia/Mês/Ano Hora")

    #rootPath = os.path.dirname(os.getcwd())
    
    #fig.write_html(rootPath+"/data/MQAr/plotly_figures/stationA_PM25.html")

    
    return fig