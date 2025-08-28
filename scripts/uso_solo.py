# -*- coding: utf-8 -*-
"""
Created on Wed Sep 11 16:09:53 2024

@author: rafab
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

map_bio = pd.read_csv(r'C:\Users\rafab\OneDrive\GAr_BR\Objetivo_07\2024\Usos_solo\usos_solo_dados\mapbiomasLegend.csv')

statsByUF = pd.read_csv(r'C:\Users\rafab\OneDrive\GAr_BR\Objetivo_07\2024\outputs/statsByUF_semRJ_b5km.csv') 
#st_lu = pd.read_excel(r'C:\Users\rafab\OneDrive\GAr_BR\Objetivo_07\2024\outputs\stationsLandUseNoGeometry.xlsx') 
main_land_use = pd.read_csv(r'C:\Users\rafab\OneDrive\GAr_BR\Objetivo_07\2024\outputs/statsByStations_semRJ.csv') 

#%%
land_use_colors = {
        'Floresta (%)': 'seagreen',  
        'Herbácea (%)': 'darkseagreen',  
        'Agropecuária (%)': 'goldenrod', 
        'Não Vegetada (%)': 'rosybrown',  
        'Urbanizada (%)': 'indianred', 
        'Mineração (%)':  'cornflowerblue' #6495ED # antigo 3d6690
        # Add as many land uses as you need
    }

# montar tabela de informações por estado e regiao do brasil
regions = {
    'Norte': ['TO', 'PA', 'AP', 'AM', 'AC'],
    'Nordeste': ['PE', 'MA', 'CE', 'BA'],
    'Centro-Oeste': ['MT', 'MS', 'GO', 'DF'],
    'Sudeste': ['SP', 'RJ', 'MG', 'ES'],
    'Sul': ['SC', 'RS', 'PR']
}

uf_to_state = {
    'AC': 'Acre', 'AP': 'Amapá', 'AM': 'Amazonas', 'BA': 'Bahia',
    'CE': 'Ceará', 'DF': 'Distrito Federal', 'ES': 'Espírito Santo', 'GO': 'Goiás',
    'MA': 'Maranhão', 'MT': 'Mato Grosso', 'MS': 'Mato Grosso do Sul', 'MG': 'Minas Gerais',
    'PA': 'Pará', 'PR': 'Paraná', 'PE': 'Pernambuco', 
    'RJ': 'Rio de Janeiro', 'RS': 'Rio Grande do Sul',
    'SC': 'Santa Catarina', 'SP': 'São Paulo',
    'TO': 'Tocantins'
}

land_use_map = {
    'Floresta': ['1', '3', '4', '5', '6', '49'],
    'Herbácea': ['10', '11', '12', '32', '29', '50'],
    'Agropecuária': ['14', '15', '18', '19', '39', '20', '40', '62', '41', '36', '46', '47', '35', '48', '9', '21'],
    'Não Vegetada': ['22', '23', '25', '26', '33', '31', '27'],
    'Urbanizada': ['24'],
    'Mineração': ['30']
}

#%%
stations = main_land_use[['LATITUDE','LONGITUDE','ESTADO','CIDADE','ESTAÇÃO','TIPO','Certificação','STATUS','FONTE', 'majorLandUse']] #'land_use_name',

def merge_strings(x):
    unique_strings = x.unique()
    if len(unique_strings) == 1:
        return unique_strings[0]
    else:
        return ', '.join(unique_strings)

# Group by 'ESTADO' and 'ESTAÇÃO' and apply aggregation function
stations_grouped = stations.groupby(['ESTADO', 'ESTAÇÃO']).agg({
    'CIDADE': merge_strings,
    'TIPO': merge_strings,
    'Certificação': merge_strings,
    'STATUS': merge_strings,
    'FONTE': merge_strings,
    #'land_use_name': merge_strings,
    'majorLandUse':merge_strings

}).reset_index()

#stations_grouped = pd.merge(stations_grouped, stations[['ESTAÇÃO', 'LATITUDE', 'LONGITUDE']], on='ESTAÇÃO', how='right')
stations_grouped.set_index('ESTADO', inplace=True)

#stations_grouped.to_csv(r'C:\Users\rafab\OneDrive\GAr_BR\Objetivo_07\2024\outputs/stations_grouped.csv') 

#%%
def main_land_use_by_state(df, state_col, land_use_col):
    # Agrupar os dados pelo estado e uso da terra, e contar a frequência de cada uso
    counts = df.groupby([state_col, land_use_col]).size().reset_index(name='count')
    
    # Para cada estado, selecionar o uso da terra com a maior contagem
    main_use = counts.loc[counts.groupby(state_col)['count'].idxmax()]
    
    # Retornar um DataFrame com o estado e o uso da terra principal
    return main_use[[state_col, land_use_col]], counts

main_useResume, counts = main_land_use_by_state(stations_grouped, 'ESTADO', 'majorLandUse')
counts['majorLandUse'] = counts['majorLandUse'].astype(str)

reverse_land_use_map = {code: category for category, codes in land_use_map.items() for code in codes}

# Step 3: Map the majorLandUse values based on the reverse mapping
counts['majorLandUse'] = counts['majorLandUse'].replace(reverse_land_use_map)

#%%
# Função para mapear os códigos para os nomes de uso da terra
def map_land_use(code):
    for land_use, codes in land_use_map.items():
        if str(code) in codes:
            return land_use
    return 'Desconhecido'  # Caso não se encaixe em nenhum código

# Função atualizada para encontrar o principal uso da terra por estado e contar as ocorrências
def main_land_use_by_state(df, state_col, land_use_col):
    # Mapear os códigos de uso da terra para os nomes
    df['land_use_name'] = df[land_use_col].apply(map_land_use)
    
    # Agrupar os dados pelo estado e nome de uso da terra, e contar a frequência de cada uso
    counts = df.groupby([state_col, 'land_use_name']).size().reset_index(name='count')
    
    # Para cada estado, selecionar o uso da terra com a maior contagem
    main_use = counts.loc[counts.groupby(state_col)['count'].idxmax()]
    
    # Retornar o DataFrame com o estado e o uso da terra principal, e o DataFrame com as contagens
    return main_use[[state_col, 'land_use_name']], counts

# Passo 1: Rodar a função principal para encontrar o uso da terra mais comum e as contagens
main_useResume, counts = main_land_use_by_state(stations_grouped, 'ESTADO', 'majorLandUse')

# Passo 2: Converter as contagens para formato "wide" (matriz de estados x usos da terra)
counts_wide = counts.pivot(index='ESTADO', columns='land_use_name', values='count').fillna(0)
counts_wide['total'] = counts_wide.apply(pd.to_numeric, errors='coerce').sum(axis=1) #soma as linhas com base nas colunas
counts_sorted = counts_wide.sort_values(by='total', ascending=True)
counts_filtered = counts_sorted
#counts_filtered = counts_sorted[(counts_sorted['total'] > 0) & (counts_sorted['total'] < 13)]


def plotStations(df):
    colors = [land_use_colors[f'{col} (%)'] for col in counts_wide.columns if col != 'total']

    # Define the ordered regions
    ordered_regions = ['Norte', 'Nordeste', 'Centro-Oeste', 'Sudeste', 'Sul']
    state_order = []
    region_boundaries = {}
    current_position = 0

    # Create an ordered list of states based on regions and sort states alphabetically within each region
    for region in ordered_regions:
        states = regions[region]
        count = 0
        # Filter and sort the states alphabetically
        states_in_region = [state for state in states if state in df.index]
        states_in_region_sorted = sorted(states_in_region, reverse=False)  # Sort alphabetically

        for state in states_in_region_sorted:
            state_order.append(state)
            count += 1
        region_boundaries[region] = current_position
        current_position += count

    # Reorder the DataFrame based on state_order
    df_sorted = df.reindex(state_order)

    # Create a grid of subplots (2 rows, 3 columns)
    fig, axs = plt.subplots(nrows=2, ncols=3, figsize=(15, 10))
    fig.subplots_adjust(hspace=0.1, wspace=0.3)
    axs = axs.flatten()  # Flatten the array of axes for easy iteration

    # Iterate through each region and create a plot for it
    for i, region in enumerate(ordered_regions):
        ax = axs[i]
        # Filter the sorted DataFrame for the current region's states
        region_states = [state for state in regions[region] if state in df_sorted.index]
        df_region = df_sorted.loc[region_states]

        if not df_region.empty:
            # Plot the stacked bar chart for the current region
            df_region.drop(columns=['total']).plot(kind='bar', stacked=True, ax=ax, color=colors, width=0.3)

            # Customize the plot
            ax.set_title(region, fontsize=17, fontweight='bold')
            ax.set_ylabel(None)
            ax.set_xlabel(None)
            ax.legend().remove()  # Hide legend for individual plots
            ax.tick_params(axis='x', labelsize=17, rotation=0)
            ax.tick_params(axis='y', labelsize=17)

            # Add separator lines between regions
            for boundary in region_boundaries.values():
                ax.axvline(boundary - 0.5, color='gray', linewidth=1, linestyle='--')

    # Hide the last empty subplot (6th position)
    axs[-1].axis('off')
    
    # Add a global legend outside the subplots
    handles, labels = axs[0].get_legend_handles_labels()
    axs[-1].legend(handles, labels, loc='center', fontsize=17, ncol=1,frameon=False)
    
    # Adjust layout to avoid clipping
    plt.tight_layout()
    plt.show()

    # folder_path = r'C:\Users\rafab\OneDrive\GAr_BR\Objetivo_07\2024\Usos_solo\imagens'
    # file_path = os.path.join(folder_path, 'numEstacoes.png')
    # fig.savefig(file_path, dpi=300, bbox_inches='tight')

    return
plotStations(counts_filtered)


#%%

def totalArea (data):
    
    flo = ['1','3','4','5','6','49']
    herb = ['10','11','12','32','29','50']
    agro = ['14','15','18','19','39','20','40','62','41','36','46','47','35','48','9','21']
    nveg = ['22','23','25','26','33','31','27']
    urb = ['24'] 
    mine = ['30'] 
    
    ar_flo = data.loc[:,flo].sum(axis=1)
    ar_herb = data.loc[:,herb].sum(axis=1) 
    ar_agro = data.loc[:,agro].sum(axis=1) 
    ar_nveg = data.loc[:,nveg].sum(axis=1) 
    ar_urb = data.loc[:,urb].sum(axis=1)
    ar_mine = data.loc[:,mine].sum(axis=1)
    
    def sum_by_category(numbers):
        # Filter columns that match the numbers and start with 'AREAUF_'
        columns = [col for col in data.columns if col.startswith('AREAUF_') and col.split('_')[-1] in numbers]  
        print(f"Columns selected for summing: {columns}")
        
        if len(columns) > 0:
            # Ensure the data in these columns is numeric and handle NaNs
            data[columns] = data[columns].apply(pd.to_numeric, errors='coerce').fillna(0)
            return data[columns].sum(axis=1)
        else:
            # Return a Series with zeros if no matching columns are found
            return pd.Series(0, index=data.index)
        
    solo_ar = pd.DataFrame({'Estado': data['ESTAÇÃO'],
                            'Floresta': ar_flo,
                            'Herbácea': ar_herb, 
                            'Agropecuária': ar_agro, 
                            'Não Vegetada': ar_nveg,
                            'Urbanizada': ar_urb, 
                            'Mineração': ar_mine, 
                            'Área Floresta': sum_by_category(flo),
                            'Área Herbácea': sum_by_category(herb),
                            'Área Agropecuária': sum_by_category(agro),
                            'Área Não Vegetada': sum_by_category(nveg),
                            'Área Urbanizada': sum_by_category(urb),
                            'Área Mineração': sum_by_category(mine)})
    
    solo_ar.set_index('Estado', inplace=True) 
    
    return solo_ar

solo_ar = totalArea(statsByUF)

#%%
def calculate_totalArea(data):
    area_cols = [col for col in data.columns if col.startswith('Área')]     
    data['Área Total - Uso do solo'] = data[area_cols].sum(axis=1)
    
    return data

calculate_totalArea(solo_ar)
#%%
def calculate_percentage(data):
    area_cols = [col for col in data.columns if not col.startswith('Área')]     
    # Sum the values across the selected area columns for each row
    data['Estações - Uso do solo'] = data[area_cols].sum(axis=1)  # Sum across the area columns row by row
    
    # Calculate the percentage for each area column
    for col in area_cols:
        
        ''' A pct do uso do solo é calculada em relação ao uso do solo dos buffers das estações, ou em relação a todo o estado; 
            Só uma das opções pode ser calculada por vez, a depender da análise que se deseja fazer'''
            
        data[f'{col} (%)'] = (data[col] / data['Estações - Uso do solo']) * 100 #pct em relação ao uso do solo total por buffer de estações
        #data[f'{col} (%)'] = (data[col] / data['Área Total - Uso do solo']) * 100 #pct em relação ao uso do solo total por estado

    return data

solo_pct = calculate_percentage(solo_ar.copy())

#%% Pct uso do solo dentro do buffer das estações 
# import os
# def plotSolo(df):
#     pct_columns = [col for col in df.columns if '(%)' in col]
    
#     df['Total_sum'] = df[pct_columns].sum(axis=1)  # Add a column for total percentage
#     df.replace([np.inf, -np.inf], np.nan, inplace=True)
    
#     df_filtered = df[df['Total_sum'] > 0]  # Filter out rows with no data
    
#     colors = [land_use_colors[col] for col in pct_columns]
    
#     # Define the order of regions
#     ordered_regions = ['Sul', 'Sudeste', 'Centro-Oeste', 'Nordeste', 'Norte']
#     state_order = []
#     region_boundaries = {}
#     current_position = 0
    
#     # Create an ordered list of states based on regions, and sort states alphabetically within each region
#     for region in ordered_regions:
#         states = regions[region]
#         count = 0
#         # Filter and sort the states alphabetically
#         states_in_region = [state for state in states if state in df_filtered.index]
#         states_in_region_sorted = sorted(states_in_region, reverse=True)  # Sort alphabetically
        
#         for state in states_in_region_sorted:
#             state_order.append(state)
#             count += 1
#         region_boundaries[region] = current_position
#         current_position += count

#     # Reorder the DataFrame based on state_order
#     df_sorted = df_filtered.reindex(state_order)
    
#     if not df_sorted.empty:
#         fig, ax = plt.subplots(figsize=(14, 10))
#         df_sorted[pct_columns].plot(kind='barh', stacked=True, ax=plt.gca(), color=colors)

#         ax.set_xlabel('Porcentagem de cobertura das estações por uso do solo no estado (%)', fontsize=17)  # X-axis label
#         ax.set_ylabel('Estado', fontsize=17, labelpad=25)  # Y-axis label

#         ax.tick_params(axis='x', labelsize=17)
#         ax.tick_params(axis='y', labelsize=17)
        
#         # Add region labels on the left
#         for region, start in region_boundaries.items():
#             end = start + len([state for state in regions[region] if state in df_filtered.index])
#             if end > start:  # Ensure the region has states to label
#                 ax.text(-4, start + (end - start) / 2, region, va='center', ha='right', fontsize=10, fontweight='bold', color='black', rotation=90)

#         # Add separator lines between regions
#         for boundary in region_boundaries.values():
#             ax.axhline(boundary - 0.5, color='gray', linewidth=1, linestyle='--')

#         ax.legend(loc='upper center', bbox_to_anchor=(0.5, 1.1), ncol=6, fontsize=12)

#         plt.tight_layout()
#         plt.show()
#         # folder_path = r'C:\Users\rafab\OneDrive\GAr_BR\Objetivo_07\2024\Usos_solo\imagens'
#         # file_path = os.path.join(folder_path, 'NEW_usoSoloLog.png')
#         # fig.savefig(file_path, dpi=300, bbox_inches='tight')
        
#     return 

# plotSolo(solo_pct)

#%% Pct uso do solo em relação a todo o estado

def plotSolo(df):
    pct_columns = [col for col in df.columns if '(%)' in col]
    
    df['Total_sum'] = df[pct_columns].sum(axis=1)  # Add a column for total percentage
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    
    df_filtered = df #[df['Total_sum'] > 0]  # Filter out rows with no data
    
    colors = [land_use_colors[col] for col in pct_columns]
    
    # Define the order of regions
    #ordered_regions = ['Sul', 'Sudeste', 'Centro-Oeste', 'Nordeste', 'Norte']
    ordered_regions = ['Norte','Nordeste','Centro-Oeste','Sudeste','Sul']
    
    state_order = []
    region_boundaries = {}
    current_position = 0
    
    # Create an ordered list of states based on regions, and sort states alphabetically within each region
    for region in ordered_regions:
        states = regions[region]
        count = 0
        # Filter and sort the states alphabetically
        states_in_region = [state for state in states if state in df_filtered.index]
        states_in_region_sorted = sorted(states_in_region, reverse=False)  # Sort alphabetically
        
        for state in states_in_region_sorted:
            state_order.append(state)
            count += 1
        region_boundaries[region] = current_position
        current_position += count

    # Reorder the DataFrame based on state_order
    df_sorted = df_filtered.reindex(state_order)
    
    if not df_sorted.empty:
        fig, ax = plt.subplots(figsize=(14, 10))
        #fig, ax = plt.subplots(figsize=(5,4))
        
        # Change from barh (horizontal) to bar (vertical)
        df_sorted[pct_columns].plot(kind='bar', ax=ax, color=colors, stacked=True)
        
        #ax.set_ylabel('Cobertura das estações por uso do solo (%)', fontsize=17)  # Y-axis label
        ax.set_xlabel('')
        ax.set_ylabel('Cobertura das estações por uso do solo no estado (%)', fontsize=17)  # Y-axis label
        #ax.set_xlabel('Estado', fontsize=17, labelpad=25)  # X-axis label
        ax.set_xticklabels(state_order, rotation=0)  # Rotate state labels for better visibility

        #ax.set_yscale('log') #aplicar log pra ficar uma escala visível

        ax.tick_params(axis='x', labelsize=17)
        ax.tick_params(axis='y', labelsize=17)
        
        # Add region labels on the right side
        for region, start in region_boundaries.items():
            count = len([state for state in regions[region] if state in df_filtered.index])
            if count > 0:  # Ensure the region has states to label
                end = start + count  # This will give the end position for the current region
                mid_position = (start + end) / 2 # Calculate midpoint
                ax.text(mid_position, -1, region, va='center', ha='center', fontsize=17, fontweight='bold', color='black', rotation=0)
                # Add separator lines between regions
        for boundary in region_boundaries.values():
             ax.axvline(boundary - 0.5, color='gray', linewidth=1, linestyle='--')

        ax.legend(ncol=1, fontsize=17, frameon=False)
        #ax.legend('')

        plt.tight_layout()
        plt.show()
        
        # folder_path = r'C:\Users\rafab\OneDrive\GAr_BR\Objetivo_07\2024\Usos_solo\imagens'
        # file_path = os.path.join(folder_path, 'usoSoloEstados_slog.png')
        # fig.savefig(file_path, dpi=300, bbox_inches='tight')
        
    return

plotSolo(solo_pct)

#%%
regions = {
    'Norte': ['AC', 'AM', 'AP', 'PA', 'TO'],
    'Nordeste': ['BA', 'CE', 'MA', 'PE'],
    'Centro-Oeste': ['DF','GO', 'MS', 'MT'],
    'Sudeste': ['ES', 'MG', 'RJ', 'SP'],
    'Sul': ['PR', 'RS', 'SC']
}

def plotSolo(df):
    pct_columns = [col for col in df.columns if '(%)' in col]
    
    df['Total_sum'] = df[pct_columns].sum(axis=1)  # Add a column for total percentage
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    
    df_filtered = df  # Filter out rows with no data
    
    colors = [land_use_colors[col] for col in pct_columns]
    
    # Define the order of regions
    #ordered_regions = ['Sul', 'Sudeste', 'Centro-Oeste', 'Nordeste', 'Norte']
    ordered_regions = ['Norte','Nordeste','Centro-Oeste','Sudeste','Sul']
    
    state_order = []
    region_boundaries = {}
    current_position = 0
    
    # Create an ordered list of states based on regions, and sort states alphabetically within each region
    for region in ordered_regions:
        states = regions[region]
        count = 0
        # Filter and sort the states alphabetically
        states_in_region = [state for state in states if state in df_filtered.index]
        states_in_region_sorted = sorted(states_in_region, reverse=True)  # Sort alphabetically
        
        for state in states_in_region_sorted:
            state_order.append(state)
            count += 1
        region_boundaries[region] = current_position
        current_position += count

    # Reorder the DataFrame based on state_order
    df_sorted = df_filtered.reindex(state_order)
    
    if not df_sorted.empty:
        # Create a 2x3 grid of subplots (for five regions)
        fig, axs = plt.subplots(nrows=2, ncols=3, figsize=(14,10))
        fig.subplots_adjust(hspace=0.1, wspace=0.3)  # Adjust space between subplots
        
        # Flatten the 2x3 array of axes for easy iteration
        axs = axs.flatten()
        
        # Plot each region in its respective subplot
        for i, region in enumerate(ordered_regions):
            ax = axs[i]
            # Get states for the current region
            states_in_region = [state for state in regions[region] if state in df_filtered.index]
            df_region = df_sorted.loc[states_in_region]
            
            # Plot stacked bar chart
            df_region[pct_columns].plot(kind='bar', ax=ax, color=colors, stacked=True, width=0.3)
            
            # Customize each subplot
            ax.set_title(region, fontsize=17, fontweight='bold')
            ax.set_xlabel(None)  # Remove x-axis label
            ax.set_ylabel(None)
            ax.set_xticklabels(states_in_region, rotation=0)
            ax.tick_params(axis='x', labelsize=17)
            ax.tick_params(axis='y', labelsize=17)
            ax.legend().remove()
        
        # Hide the last empty subplot (6th position)
        axs[-1].axis('off')
        
        # Add a global legend outside the subplots
        handles, labels = axs[0].get_legend_handles_labels()
        axs[-1].legend(handles, labels, loc='center', fontsize=17, ncol=1,frameon=False)
        
        # Adjust layout to avoid clipping
        plt.tight_layout()
        plt.show()
        
        # folder_path = r'C:\Users\rafab\OneDrive\GAr_BR\Objetivo_07\2024\Usos_solo\imagens'
        # file_path = os.path.join(folder_path, 'usoSoloEstados.png')
        # fig.savefig(file_path, dpi=300, bbox_inches='tight')
        
    
    return

plotSolo(solo_pct)

#%% plots individuais
#%%
def plot_buffer_vs_total(df):
    # Define buffer and total area columns based on your naming convention
    buffer_columns = ['Floresta', 'Herbácea', 'Agropecuária', 'Não Vegetada', 'Urbanizada', 'Mineração']
    area_columns = [f'Área {col}' for col in buffer_columns]
    
    # Iterate over each row (state) in the DataFrame
    for state, row in df.iterrows():
        # Extract buffer areas and corresponding total areas
        buffer_areas = [row[col] for col in buffer_columns]
        total_areas = [row[col] for col in area_columns]
        state_total_area = row['Área Total - Uso do solo']
        estacoes_total_area = row['Estações - Uso do solo']
        
        # Create a figure and axis
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Plot the stacked bar chart
        categories = buffer_columns
        buffer_area_values = buffer_areas
        total_area_values = total_areas
        
        # Create a stacked bar chart
        bar_width = 0.35
        index = range(len(categories))
        
        ax.bar(index, buffer_area_values, bar_width, label='Buffer Area', color='blue')
        ax.bar(index, total_area_values, bar_width, bottom=buffer_area_values, label='Total Area', color='orange')
        
        # Add horizontal lines for total state area and buffer area
        ax.axhline(y=state_total_area, color='gray', linestyle='--', label='Área Total do Estado (100%)')
        ax.axhline(y=estacoes_total_area, color='black', linestyle='--', label='Estações - Uso do Solo (100%)')
        
        # Customize plot
        ax.set_xlabel('Categorias', fontsize=10)
        ax.set_ylabel('Área (em unidades)', fontsize=10)
        ax.set_title(f'Comparação do Uso do Solo para {state}', fontsize=12)
        ax.set_xticks(index)
        ax.set_xticklabels(categories, rotation=45, ha='right')
        ax.legend(loc='upper left')
        ax.set_yscale('log')
        
        plt.tight_layout()
        plt.show()

plot_buffer_vs_total(solo_pct)

#%%
def plot_buffer_vs_total(df):
    # Define buffer and total area columns based on your naming convention
    buffer_columns = ['Floresta', 'Herbácea', 'Agropecuária', 'Não Vegetada', 'Urbanizada', 'Mineração']
    area_columns = [f'Área {col}' for col in buffer_columns]
    
    # Split DataFrame into three parts
    split_size = len(df) // 3
    df1 = df.iloc[:split_size]
    df2 = df.iloc[split_size:2 * split_size]
    df3 = df.iloc[2 * split_size:]
    
    def create_plot(df_part, fig_num):
        # Create a figure with subplots, sharing the x-axis
        fig, axes = plt.subplots(len(df_part), 1, figsize=(10, 8 * len(df_part)), sharex=True)
        
        # Iterate over each row (state) in the DataFrame
        for i, (state, row) in enumerate(df_part.iterrows()):
            # Extract buffer areas and corresponding total areas
            buffer_areas = [row[col] for col in buffer_columns]
            total_areas = [row[col] for col in area_columns]
            
            colors = [land_use_colors[f'{col} (%)'] for col in buffer_columns]            
            # Current axis
            ax = axes[i] if len(df_part) > 1 else axes
            
            # Plot the stacked bar chart
            categories = buffer_columns
            buffer_area_values = buffer_areas
            total_area_values = total_areas
            
            # Create a stacked bar chart
            bar_width = 0.35
            index = np.arange(len(categories))
            
            ax.bar(index, buffer_area_values, bar_width, label='Buffer Area', color=colors)
            ax.bar(index, total_area_values, bar_width, bottom=buffer_area_values, label='Total Area', color='lightgray')

            # Customize plot
            ax.text(0.99, 0.9, f'Estado - {state}', transform=ax.transAxes, va='top', ha='right',  bbox=dict(facecolor='white', alpha=0.5, edgecolor='black'), fontsize=8)

            # Show legend only on the first plot of the first figure
            if fig_num == 1 and i == 0:
                ax.legend(loc='upper left')
            
            # Set x-ticks only on the last plot
            if i == len(df_part) - 1:
                ax.set_xticks(index)
                ax.set_xticklabels(categories, fontsize=8)
            else:
                ax.set_xticks([])  # Hide x-ticks for all other plots

            ax.set_yscale('log')
       
        # Adjust layout to ensure y-labels and titles are not cropped
        fig.text(0, 0.5, 'Log de Área (m2)', va='center', rotation='vertical', fontsize=10)
        plt.tight_layout()
        plt.show()
    
    # Create three separate figures
    create_plot(df1, 1)  # First figure
    create_plot(df2, 2)  # Second figure
    create_plot(df3, 3)  # Third figure

# Assuming 'solo_pct' is your DataFrame
plot_buffer_vs_total(solo_pct)

#%%
# criar e unir colunas dos estados e estações

estacoes = main_land_use[['ESTADO','CIDADE','ESTAÇÃO','TIPO','Certificação','STATUS','FONTE', 'land_use_name']]

def merge_strings(x):
    unique_strings = x.unique()
    if len(unique_strings) == 1:
        return unique_strings[0]
    else:
        return ', '.join(unique_strings)

# Group by 'ESTADO' and 'ESTAÇÃO' and apply aggregation function
estacoes_grouped = estacoes.groupby(['ESTADO', 'ESTAÇÃO']).agg({
    'CIDADE': merge_strings,
    'TIPO': merge_strings,
    'Certificação': merge_strings,
    'STATUS': merge_strings,
    'FONTE': merge_strings,
    'land_use_name': merge_strings
}).reset_index()

#desconsiderando estacoes inativas do RJ
#estacoes_grouped = estacoes_grouped[~((estacoes_grouped['ESTADO'] == 'RJ') & (estacoes_grouped['STATUS'] == 'Inativa'))]


#%%
# Drop duplicates while keeping the first occurrence
# estacoes_unique = estacoes.drop_duplicates(subset=['ESTADO', 'ESTAÇÃO'], keep='first') #DESCONSIDERAR AS INATIVAS DO RJ

# # Define a function to merge duplicates from other columns
# def merge_values(group):
#     merged_row = group.iloc[0].copy()  # Start with the first row
#     for col in ['CIDADE', 'TIPO', 'Certificação', 'STATUS', 'FONTE', 'land_use_name']:
#         unique_values = group[col].unique()
#         merged_row[col] = ', '.join(unique_values)
#     return merged_row

# # Apply the function to group rows by 'ESTADO' and 'ESTAÇÃO'
# estacoes_merged = estacoes.groupby(['ESTADO', 'ESTAÇÃO']).apply(merge_values).reset_index(drop=True)


#%%
# Create a function to assign regions based on UF
def assign_region(uf):
    for region, states in regions.items():
        if uf in states:
            return region
    return None

def createRegion (df):    
    # Add the region column
    df['REGIÃO'] = df['ESTADO'].map(lambda x: assign_region(x))   
    df_sorted = df[['REGIÃO','ESTADO', 'CIDADE', 'ESTAÇÃO', 'TIPO', 'Certificação', 'STATUS', 'FONTE', 'land_use_name']]
    df_sorted = df.sort_values(by=['REGIÃO', 'ESTADO', 'CIDADE'])
    return df_sorted

df_sorted = createRegion(estacoes_grouped)



num = df_sorted.groupby('ESTADO').count()



