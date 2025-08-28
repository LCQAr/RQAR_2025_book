#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Webscraping de dados de qualidade do ar do INEA-RJ.

Este script realiza:
- Definição de parâmetros e estações de monitoramento.
- Download de séries temporais horárias via requisições HTTP.
- Salvamento dos dados em arquivos CSV.

Created on Wed Sep 11 10:45:33 2024
@author: leohoinaski
"""

# ---------------------------------- Importação de pacotes ----------------------------------
import pandas as pd
import requests
from bs4 import BeautifulSoup
import numpy as np
import time
import os
from pathlib import Path
# ---------------------------------- Dicionários de parâmetros ----------------------------------

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
    #'DV - Direção do Vento [°]': '100001',
    #'DVDP - Desvio Padrão Dir. Vento [°]': '20051',
    #'PA - Pressão Atmosférica [hPa]': '100007',
    #'PP - Precipitação [mm]': '100004',
    #'RS - Radiação Solar [W/m²]': '100006',
    #'TA - Temperatura do Ar [°C]': '100002',
    #'UR - Umidade Relativa [%]': '100005',
    #'VV - Velocidade do Vento [m/s]': '100000'
}

# Transformando em dataframe
df_parametros = pd.DataFrame(station_parameters_dict.items(), columns=["parameter_name", "parameter_id"])

# ---------------------------------- Estações ----------------------------------
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

stations_manual = {
    # Região da Costa Verde
    201: "S - AR - Ilha Grande - UERJ",
    727: "S - Mt - Ilha Guaíba",
    728: "S - Mt - Itacuruçá",
    729: "S - Mt - Muriqui",

    # Região das Baixadas Litorâneas
    692: "S - Ara - Morro Grande",
    722: "S - Ara - SIGIL",
    233: "S - SPA - Campo Redondo 1",
    710: "S - SPA - Campo Redondo 2",

    # Região do Médio Paraíba
    212: "S - BM - Ano Bom",
    709: "S - Itt - Rua Oito",
    708: "S - Itt - Rua Quarenta e Quatro",
    258: "S - Manual - Resende - Morada da Colina",
    257: "S - Manual - Volta Redonda - Belmonte",
    256: "S - Manual - Volta Redonda - C.Pesquisa",
    255: "S - Manual - Volta Redonda Banerj",
    254: "S - Manual - Volta Redonda J. Europa",
    802: "S - Pir - Caiçara",
    243: "S - Ponte Coberta",
    245: "S - Ribeirão das Lajes",
    154: "S - Rs - Pólo Industrial",
    116: "S - VR - Aeroclube",
    244: "S - VR - Água Limpa",
    650: "S - VR - Brasilândia",
    117: "S - VR - Centro",
    119: "S - VR - Conforto",
    238: "S - VR - Igreja de Santa Edwiges",
    148: "S - VR - Jardim Paraíba",
    120: "S - VR - Ponte Alta",
    651: "S - VR - São Luís",
    118: "S - VR - Vila Mury",
    146: "S - VR - Volta Grande",

    # Região Metropolitana
    667: "S - BR - Bom Pastor",
    211: "S - BR - Cedae",
    664: "S - BR - Malhapão",
    668: "S - BR - Nova Piam",
    669: "S - BR - Parque Martinho",
    276: "S - BR - Piam",
    666: "S - BR - Santa Maria",
    210: "S - BR - Secretaria de Transporte",
    734: "S - DC - Bacia de Resfriamento",
    204: "S - DC - Campos Elíseos",
    691: "S - DC - Comunidade",
    202: "S - DC - Jardim Primavera",
    203: "S - DC - Jardim Vinte e Cinco de Agosto",
    803: "S - DC - Parada Angélica",
    736: "S - DC - Pier das Chatas",
    738: "S - DC - Reservatório de Segurança",
    739: "S - DC - SETRE",
    741: "S - DC - Taquara",
    603: "S - Inoã - Lavador Da Pedreira",
    127: "S - Itb - Alto do Jacu",
    690: "S - Itb - Badureco",
    131: "S - Itb - Itambi",
    638: "S - Itb - Itambi (DNIT)",
    785: "S - Itb - Pachecos",
    132: "S - Itb - Porto das Caixas",
    133: "S - Itb - Sambaetiba",
    129: "S - Itb - Sambaetiba (Fazenda Macacu)",
    130: "S - Itb - Vale das Pedrinhas",
    816: "S - Itg - Amendoeira",
    687: "S - Itg - Brisa Mar",
    689: "S - Itg - Centro",
    686: "S - Itg - Parque Paraíso",
    598: "S - Itg - Vila Ibirapitanga",
    815: "S - Itg - Vila Ibirapitanga",
    688: "S - Itg - Vila Margarida",
    234: "S - Jp - Vila Japeri",
    239: "S - Ma - Inoã",
    753: "S - Manual - Belford Roxo - Farrula",
    273: "S - Manual - Cascadura",
    272: "S - Manual - Centro Antiga",
    271: "S - Manual - Coelho Neto",
    270: "S - Manual - Copacabana - Light",
    269: "S - Manual - Duque de Caxias - Fórum",
    268: "S - Manual - Engenho da Rainha",
    267: "S - Manual - Ilha do Governador",
    266: "S - Manual - Ilha do Governador Antiga",
    265: "S - Manual - Inhaúma",
    264: "S - Manual - Maracanã  Antiga",
    263: "S - Manual - Méier Antiga 1",
    262: "S - Manual - Mesquita",
    261: "S - Manual - Nilópolis Antiga",
    260: "S - Manual - Nova Iguaçu Horto",
    259: "S - Manual - Queimados",
    232: "S - Mg - Bombeiros",
    685: "S - Mg - Convem Mineração",
    121: "S - Mg - Fazenda Caju",
    241: "S - Mg - Magé (DNIT)",
    717: "S - Mg - Suruí",
    235: "S - Mg - Vila Inca",
    194: "S - NI - Centro",
    606: "S - NI - Cerâmica",
    805: "S - NI - Marapicu",
    599: "S - NI - Parque Rodilar",
    673: "S - Nit - AABB/Piratininga",
    675: "S - Nit - Águas de Niterói/Itaipu",
    191: "S - Nit - Centro",
    187: "S - Nit - Centro",
    676: "S - Nit - Corpo de Bombeiros/Itaipu",
    674: "S - Nit - DPO/Cafubá",
    677: "S - Nit - E M Francisco Portugal Neves/Piratininga",
    189: "S - Nit - Fonseca",
    678: "S - Nit - Hospital Psiquiatrico/Jurujuba",
    242: "S - Nit - Jurujuba",
    185: "S - Np - Rodoviária",
    719: "S - Pedreira Vigne Ltda.",
    801: "S - Prb - Dutra 103",
    236: "S - Qmd - Jardim Excelsior",
    724: "S - RJ - Alvorada",
    682: "S - RJ - Bandeirantes",
    173: "S - RJ - Bangu",
    615: "S - RJ - Bangu",
    705: "S - RJ - Barra da Tijuca",
    701: "S - RJ - Batalhão",
    184: "S - RJ - Benfica",
    679: "S - RJ - Bosque da Boiúna",
    181: "S - RJ - Botafogo",
    155: "S - RJ - Botafogo (Urca)",
    179: "S - RJ - Cajú",
    209: "S - RJ - Campo Grande",
    230: "S - RJ - Campos dos Afonsos",
    704: "S - RJ - Cantagalo",
    177: "S - RJ - Centro",
    176: "S - RJ - Cidade de Deus",
    175: "S - RJ - Copacabana",
    670: "S - RJ - Copacabana 2",
    681: "S - RJ - Curicica",
    172: "S - RJ - Engenho de Dentro",
    693: "S - RJ - Frente da Mineração",
    170: "S - RJ - Gamboa",
    702: "S - RJ - Gastão Baiana",
    707: "S - RJ - Gávea",
    144: "S - RJ - Ilha De Paquetá",
    139: "S - RJ - Inhaúma",
    712: "S - RJ - Inhaúma",
    781: "S - RJ - Inhaúma (Concretan)",
    780: "S - RJ - Inhaúma (Polimix)",
    699: "S - RJ - Ipanema",
    683: "S - RJ - João Cribbin",
    725: "S - RJ - João XXIII A",
    726: "S - RJ - João XXIII B",
    167: "S - RJ - Lagoa",
    698: "S - RJ - Leblon",
    166: "S - RJ - Leblon",
    703: "S - RJ - Leopoldina",
    156: "S - RJ - Maracanã",
    165: "S - RJ - Maracanã",
    697: "S - RJ - Melo Duarte",
    731: "S - RJ - Palmares",
    700: "S - RJ - Pça. Jardim de Alah",
    182: "S - RJ - Ramos",
    164: "S - RJ - Ramos (Piscinão)",
    163: "S - RJ - Realengo",
    168: "S - RJ - Recreio dos Bandeirantes",
    160: "S - RJ - Rio Comprido",
    680: "S - RJ - Rio Grande",
    152: "S - RJ - Santa Cruz",
    153: "S - RJ - Santa Cruz (Conjunto Alvorada)",
    162: "S - RJ - Santa Tereza",
    706: "S - RJ - São Conrado",
    161: "S - RJ - São Cristovão",
    723: "S - RJ - Serra da Misericórdia - Inhaúma",
    247: "S - RJ - Taquara",
    158: "S - RJ - Tijuca",
    732: "S - RJ - Urucania",
    600: "S - RJ - Vargem Pequena",
    684: "S - RJ - Ventura",
    169: "S - RJ - Vila Militar",
    718: "S - SG - Área de Lavras",
    250: "S - SG - Colubandê",
    604: "S - SG - Engenho do Roçado",
    713: "S - SG - Estrada da Carioca",
    151: "S - SG - Prefeitura",
    716: "S - SG - Rua Major Januário",
    715: "S - SG - Rua Rio Juruá",
    614: "S - SG - Santa Isabel",
    150: "S - SJM - Vilar dos Teles",
    149: "S - Sp - Embrapa",
    602: "S - Sp - Fazenda Caxias 1",
    607: "S - Sp - Fazenda Caxias 2",
    248: "S - Sp - Nazaré",
    720: "S - Sp - Portaria Norte",
    721: "S - Sp - Portaria Sudeste",
    237: "S - Sp - Zona Rural",
    711: "S - Tan - Mineração Sartor",
    249: "S - Tan - Vila Cortes",

    # Região Noroeste Fluminense
    617: "S - Itp - Cubatão",

    # Região Norte Fluminense
    208: "S - Cp - Águas do Paraíba",
    207: "S - Cp - Centro",
    206: "S - Cp - Goytacazes",
    205: "S - Cp - Rodoviária",
    663: "S - Mc - Boa Fé",
    671: "S - Mc - Cabiúnas",
    662: "S - Mc - Horto",
    696: "S - Mc - Imboassica",
    800: "S - Mc - Vila Iriri",
    672: "S - São Joaquim",
    656: "S - SJB - Barra do Açu",
    694: "S - Sjb - Barra Do Açu 2",
    654: "S - SJB - Mato Escuro",
    655: "S - SJB - Mato Escuro (Centro)",
    652: "S - SJB - Pipeiras 1",
    695: "S - SJB - Pipeiras 2",
    657: "S - SJB - Porto do Açu",

    # Região Serrana
    137: "S - Cg - Ruínas",
    135: "S - Cg - Vila",
    752: "S - Manual - Cantagalo (Ruínas)",
    751: "S - Manual - Cantagalo (Vila)",
    246: "S - Ter - Vale Alpino",
}

df_stations = pd.DataFrame(list(stations_dict.items()), columns=["station_id", "station_name"])


def webscraper_RJ(out_folder: str, station_id: str, parameter_id: str, start_date: str, end_date: str, year: int) -> pd.DataFrame:
    """
    Realiza webscraping de dados horários de qualidade do ar no estado do RJ.

    Parameters
    ----------
    station_id : str
        Código da estação de monitoramento (ID numérico).
    parameter_id : str
        Código do parâmetro/poluente monitorado (ID numérico).
    start_date : str
        Data inicial no formato 'YYYY-MM-DD'.
    end_date : str
        Data final no formato 'YYYY-MM-DD'.
    year : int
        Ano da coleta, utilizado também para nomear o arquivo de saída.

    Returns
    -------
    pd.DataFrame
        DataFrame contendo as colunas:
        - datetime : str
            Data/hora da medição.
        - value : float
            Valor da concentração ou medida meteorológica.
        - qaqc : str
            Indicador de qualidade (QA/QC) da medição.

    Notas
    -----
    - Os dados são salvos automaticamente em arquivos CSV na pasta:
      `/home/nobre/Notebooks/RQAR_2025_book/data/RJ/`
    - Caso não haja dados disponíveis, retorna um DataFrame vazio.
    """
    hourly_range = pd.date_range(start=start_date, end=end_date, freq='h')

    url = "https://ei.weblakes.com/INEAPublico/AMSTabularData/GridData"
    params = {
        "aStationType": "1",
        "aSites": station_id,
        "aParameters": parameter_id,
        "aStartDate": start_date,
        "aEndDate": end_date,
        "aShowRawData": "True",
        "anAvgPeriod": "1",
        "aDataSouce": "1",
        "aAvgType": "1",
        "gridId": "TabularTimeGrid",
        "Context_Bootstrap_Flag": "true",
        "_search": "false",
        "nd": "1755542020437",
        "rows": np.shape(hourly_range)[0],
        "page": "1",
        "sidx": "Time",
        "sord": "asc",
        "ssSearchField": "__ANY_COLUMN",
        "ssSearchOper": "cn",
        "ssSearchString": "",
        "_": "1755541897561"
    }

    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url, params=params, headers=headers)
    data = resp.json()

    records = []
    for row in data["rows"]:
        cells = row["cell"]

        # Extrair datetime e valor
        timestamp = BeautifulSoup(cells[2], "html.parser").text.strip()
        value = BeautifulSoup(cells[3], "html.parser").text.strip()

        try:
            value = float(value) if value != '' else np.nan
        except ValueError:
            value = np.nan

        qaqc = cells[4]
        records.append({"datetime": timestamp, "value": value, "qaqc": qaqc})

    df = pd.DataFrame(records)

    if not df.empty:
        out_path = f"{out_folder}/{year}_{station_id}_{parameter_id}.csv"
        df.to_csv(out_path, index=False)
        print('PARÂMETRO MEDIDO E COLETADO')
    else:
        print('Parâmetro não medido')
        out_path = f"{out_folder}/{year}_{station_id}_{parameter_id}.csv"
        df.to_csv(out_path, index=False)

    return df


# ---------------------------------- Execução principal ----------------------------------
if __name__ == "__main__":

    print('--------------------- webScraperRJ ---------------------')
    print('')
    print('Universidade Federal de Santa Catarina - UFSC')
    print('Laboratório de Controle da Qualidade do Ar - LCQAr')
    print('@author: leohoinaski')

    # Definindo anos de coleta e caminho para os arquivos de saída
    years = np.arange(2000, 2018)  
    out_folder = '/home/nobre/Notebooks/RQAR_2025_book/data/RJ'
    
    # Loop por ano, estação e parâmetro    
    for _, row in df_stations.iterrows():
        print('')
        print('--------------------- '+row.station_name+' ---------------------')
        print('')
        
        for _, rowParam in df_parametros.iterrows():
            print('##### ' + rowParam.parameter_name+' #####' )
        
            for year in years:
                print(f"Ano: {year}")
     
                if os.path.exists(f"{out_folder}/{year}_{row.station_id}_{rowParam.parameter_id}.csv"):
                    print('Arquivo já está no banco de dados')
                    
                else:

                    while True:
                        try:
                            # Code that might cause an error
                            webscraper_RJ(out_folder, str(row.station_id), rowParam.parameter_id,
                                      f"{year}-01-01", f"{year+1}-01-01", year)
                            time.sleep(10)  # Pausa de 2 segundos entre requisições
                            break  # Exit the loop if successful
                        except:
                            print(f"An error occurred: Retrying...")
                            # Optionally add a delay here to prevent rapid retries
                            # import time
                            time.sleep(10)
                            #print('Baixando...')
                            try: 
                                time.sleep(20)
                                webscraper_RJ(out_folder, str(row.station_id), rowParam.parameter_id,
                                          f"{year}-01-01", f"{year+1}-01-01", year)
                                time.sleep(10)  # Pausa de 10 segundos entre requisições
                            except:
                                print('!!!!!!!!!!Não baixou o dado!!!!!!!!!!!!')

                    