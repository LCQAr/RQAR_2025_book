#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""


Criado por Leonardo Hoinaski
"""

# ---------------------------------- Importação de pacotes ----------------------------------

import os 
import pandas as pd
import numpy as np

station_parameters_dict = {
    'CH4 - Metano [ppm]': '7',
    'CO - Monóxido de Carbono [ppm]': '3',
    'NOX - Óxidos de Nitrogênio [µg/m³]': '9',
    'HCNM - Hidrocarbonetos Não-Metano [ppm]': '11',
    'MP10 - Partículas Inaláveis (<10µm) [µg/m³]': '18',
    'MP2,5 - Partículas Inaláveis (<2,5µm) [µg/m³]': '20',
    'SO2 - Dióxido de Enxofre [µg/m³]': '23',
    'BENZ - Benzeno [µg/m³]': '134',
    'ETBENZ - Etil Benzeno [µg/m³]': '263',
    'OX - O-Xileno [µg/m³]': '413',
    'TOL - Tolueno [µg/m³]': '482',
    'XIL - Xileno [µg/m³]': '504',
    'H2S - Sulfeto de Hidrogênio [µg/m³]': '1305',
    'NO2 - Dióxido de Nitrogênio [µg/m³]': '1465',
    'PTS - Partículas Totais em Suspensão [µg/m³]': '1955',
    'NO - Monóxido de Nitrogênio [µg/m³]': '2128',
    'O3 - Ozônio [µg/m³]': '2130',
    'HCT - Hidrocarbonetos Totais [ppm]': '2143',
    'MPX - M,P-Xileno [µg/m³]': '2168',
    'DV - Direção do Vento [°]': '100001',
    'DVDP - Desvio Padrão Dir. Vento [°]': '20051',
    'PA - Pressão Atmosférica [hPa]': '100007',
    'PP - Precipitação [mm]': '100004',
    'RS - Radiação Solar [W/m²]': '100006',
    'TA - Temperatura do Ar [°C]': '100002',
    'UR - Umidade Relativa [%]': '100005',
    'VV - Velocidade do Vento [m/s]': '100000'
}

stations_dict = {
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

df_stations = pd.DataFrame(list(stations_dict.items()), columns=["station_id", "station_name"])
df_stations= df_stations.drop_duplicates()

# Transformando em dataframe
df_parametros = pd.DataFrame(station_parameters_dict.items(), columns=["parameter_name", "parameter_id"])


directory_path = '/home/nobre/Notebooks/RQAR_2025_book/data/RJ' 


file_sizes = []
filenames = []
for filename in os.listdir(directory_path):
    #print(filename)
    filepath = os.path.join(directory_path, filename)
    if os.path.isfile(filepath): # Check if it's a file, not a directory
        size_in_bytes = os.path.getsize(filepath)
        file_sizes.append(size_in_bytes)
        filenames.append(filename)
#print(file_sizes)

df_files = pd.DataFrame({'filenames':filenames})
df_files[['ANO','ESTACAO', 'PARAMETRO']] =  df_files['filenames'].str.split('_', expand=True)
df_files[['PARAMETRO', 'EXTENSAO']] = df_files['PARAMETRO'].str.split('.', expand=True)
df_files['TAMANHO'] = file_sizes

pn=[]
en=[]
for ii, row in df_files.iterrows():
    #print(row)
    parname = df_parametros['parameter_name'][row.PARAMETRO == df_parametros.parameter_id]
    pn.append(parname.values[0])
    estname = df_stations['station_name'][int(row.ESTACAO) == df_stations.station_id]
    en.append(estname.values[0])
    #print(parname)
    
df_files['PARNAME'] = pn
df_files['ESTNAME'] = en

df_files = df_files[df_files['TAMANHO']>1]

# Sort by 'Age' in ascending order
df_files = df_files.sort_values(by='ANO')

df_files_years = df_files.groupby(['ESTACAO','ESTNAME', 'PARAMETRO','PARNAME']).agg({
    'ANO': lambda x: ', '.join(x),
    #'PARNAME': lambda Y: ', '.join(Y),
    
}).reset_index()

df_files_years['INICIO'] = np.nan
df_files_years['FIM'] = np.nan
df_files_years['NANOS'] = np.nan
df_files_years['NGAPS'] = np.nan

for ii, row in df_files_years.iterrows():
    
    df_files_years.loc[ii, "INICIO"]  = np.array(row['ANO'].split(','),dtype=int).min().item()
    df_files_years.loc[ii, "FIM"]  = np.array(row['ANO'].split(','),dtype=int).max().item()
    df_files_years.loc[ii, "NANOS"]  = np.array(row['ANO'].split(','),dtype=int).shape[0]
    
    if df_files_years.loc[ii, "INICIO"]==df_files_years.loc[ii, "FIM"]:
         df_files_years.loc[ii, "NGAPS"] =  0
    else:
        df_files_years.loc[ii, "NGAPS"] =  np.size(np.arange(df_files_years.loc[ii, "INICIO"],df_files_years.loc[ii, "FIM"]+1, 1)) - df_files_years.loc[ii,'NANOS']
    
df_files_years['INICIO'] = df_files_years['INICIO'].astype(int)
df_files_years['FIM'] = df_files_years['FIM'].astype(int)
df_files_years['NANOS'] = df_files_years['NANOS'].astype(int)
df_files_years['NGAPS'] = df_files_years['NGAPS'].astype(int)

#min_values_per_category = df_files.groupby(['ESTNAME','PARNAME'])['ANO'].min()

#df_files_years['INICIO'] = min_values_per_category.reset_index().ANO.astype(int)

# max_values_per_category = df_files.groupby(['ESTNAME','PARNAME'])['ANO'].max()

# df_files_years['FIM'] = max_values_per_category.reset_index().ANO.astype(int)

# count_years = df_files.groupby(['ESTNAME','PARNAME'])['ANO'].count()

# df_files_years['NANOS'] = count_years.reset_index().ANO

# df_files_years['NGAPS'] =  df_files_years.apply(lambda row: np.size(np.arange(row['INICIO'], row['FIM']+1, 1)), axis=1) - df_files_years['NANOS']


df_files_years.to_csv('/home/nobre/Notebooks/RQAR_2025_book/data/RJ_STATIONS_ANOS.csv', index=False)
#df_files.to_csv('/home/nobre/Notebooks/RQAR_2025_book/data/RJ_STATIONS.csv', index=False)

import pathlib

directory_path = '/home/nobre/Notebooks/RQAR_2025_book/data/RJ/' 
directory_out = '/home/nobre/Notebooks/RQAR_2025_book/data/RJ_compilado/' 

mapping = {
    "7":"011"
    "9": "018",
    "11": "016",
    "18": "001",
    "20": "002",
    "23": "003",
    "134": "010",
    "263": "013",
    "413": "025",
    "482": "022",
    "504": "023",
    "1305": "014",
    "1465": "004",
    "1955": "008",
    "2128": "017",
    "2130": "005",
    "2143": "026",
    "2168": "027"
}


unique_df = df_files_years.drop_duplicates(subset=['ESTACAO', 'PARAMETRO'])
unique_df["nosso_parametro"] = unique_df["PARAMETRO"].map(mapping)
for ii, row in unique_df.iterrows():
    #print(str(row['ESTACAO'])+'_'+str(row['PARAMETRO']))
    df_list=[]
    all_files = glob.glob(directory_path + '*'+str(row['ESTACAO'])+'_'+str(row['PARAMETRO'])+'.csv')
    for lf in all_files:
        filepath = os.path.join(directory_path, lf)
        try:
            df = pd.read_csv(filepath)
        except:
            df = pd.DataFrame()
            
        df_list.append(df)
    
    if len(all_files)>1:
        combined_df = pd.concat(df_list, ignore_index=True)
    else:
        combined_df = df.copy()
        
    combined_df['datetime'] = pd.to_datetime(combined_df['datetime'],format='mixed')
    combined_df['ANO'] = pd.to_datetime(combined_df['datetime']).dt.year
    combined_df['MES'] = pd.to_datetime(combined_df['datetime']).dt.month
    combined_df['DIA'] = pd.to_datetime(combined_df['datetime']).dt.day
    combined_df['HORA'] = pd.to_datetime(combined_df['datetime']).dt.hour
    
    combined_df = combined_df.drop_duplicates()
    combined_df = combined_df.sort_values(by='datetime')
    
    #combined_df
    #combined_df['value'].plot()
    if isinstance(row['nosso_parametro'], str):
        combined_df.to_csv(directory_out+'RJ'+str(row['ESTACAO']).zfill(4)+str(row['nosso_parametro']).zfill(3)+'.csv', index=False)
    else:
        combined_df.to_csv(directory_out+'RJ'+str(row['ESTACAO']).zfill(4)+str(row['PARAMETRO']).zfill(3)+'.csv', index=False)
    