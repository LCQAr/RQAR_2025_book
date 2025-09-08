#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Sep 11 10:45:33 2024

@author: Marcos Perrude com organização de Leonardo
"""

# import os
# import math
# import rasterio
# import numpy as np
# import matplotlib.pyplot as plt

# # ---- Seleção da estação ----
# subset_mask = (csv['ID_OEMA'] == 'Centro') & (csv['UF'] == 'SP')
# subset = csv.loc[subset_mask]

# if subset.empty:
#     raise ValueError("Nenhuma estação encontrada para os filtros dados.")

# lat = subset['LATITUDE'].iloc[0]
# lon = subset['LONGITUDE'].iloc[0]

# lat_prefixo = 's' if lat < 0 else 'n'
# lon_prefixo = 'w' if lon < 0 else 'e'

# if lat < 0:
#     lat_num = math.ceil(abs(lat))
# else:
#     lat_num = math.floor(abs(lat))

# if lon < 0:
#     lon_num = math.ceil(abs(lon))
# else:
#     lon_num = math.floor(abs(lon))

# lat_str = f"{lat_num:02d}"
# lon_str = f"{lon_num:03d}"

# filename = f"{lat_prefixo}{lat_str}_{lon_prefixo}{lon_str}_1arc_v3.tif"
# print("Arquivo SRTM:", filename)

# # ---- Abrir o raster ----
# filepath = os.path.join(DirSRTM, filename)
# with rasterio.open(filepath) as dem_data:
#     dem_array = dem_data.read(1)
#     extent = [
#         dem_data.bounds.left, dem_data.bounds.right,
#         dem_data.bounds.bottom, dem_data.bounds.top
#     ]
#     nodata = dem_data.nodata  # valor de NoData do raster

# # ---- Criar máscara de dados válidos ----
# if nodata is not None:
#     dem_array = np.where(dem_array == nodata, np.nan, dem_array)

# # ---- Plotar ----
# fig, ax = plt.subplots(figsize=(8, 6))
# img = ax.imshow(
#     dem_array, extent=extent, cmap="terrain",
#     origin="upper"
# )
# plt.colorbar(img, ax=ax, label="Elevação (m)")

# # Localização da estação
# ax.scatter(lon, lat, color="red", s=60, marker="x", label="Estação")

# ax.set_title(f"SRTM - {filename}")
# ax.set_xlabel("Longitude")
# ax.set_ylabel("Latitude")
# ax.legend()

# plt.show()

import pandas as pd
import os
import rasterio
import matplotlib.pyplot as plt
import pandas as pd
import math
from shapely.geometry import Point, mapping
from rasterio.mask import mask
import numpy as np

def corrige_elevacoes(csv_neg, estacoes_negativas, DirSRTM):

    csv_neg['ELEVACAO'] = None  # cria/zera a coluna de saída
    # Loop em cada estação única
    for estacao in csv_neg['ID_OEMA'].unique():
        subset_mask = csv_neg['ID_OEMA'] == estacao
        subset = csv_neg.loc[subset_mask]

        filename = estacoes_negativas[estacao]
        dem_data = rasterio.open(DirSRTM + filename[0])
        dem_array = dem_data.read(1)


        elevations = []
        for _, row_data in subset.iterrows():
            # obtém índice do pixel
            row, col = dem_data.index(row_data['LONGITUDE'], row_data['LATITUDE'])
            elev = dem_array[row, col]

            # cria buffer de ~1km em torno do ponto
            ponto = Point(row_data['LONGITUDE'], row_data['LATITUDE'])
            buffer = ponto.buffer(0.1)
            out_image, _ = mask(dem_data, [mapping(buffer)], crop=True)

            # média dos valores positivos dentro do buffer
            elev_corrigido = np.nanmean(out_image[0][out_image[0] > 0])
            elevations.append(int(elev_corrigido))

        # Salva de volta no dataframe
        csv_neg.loc[subset_mask, 'ELEVACAO'] = elevations

    return csv_neg


def getElevSRTM(DirSRTM, csv):
    
    csv['ELEVACAO'] = None
    estacoes_negativas = {}

    # Loop por UF
    for uf in csv['UF'].unique():
        csv_uf = csv[csv['UF'] == uf]

        # Loop por estação dentro da UF
        for estacao in csv_uf['ID_OEMA'].unique():
            mask = (csv['ID_OEMA'] == estacao) & (csv['UF'] == uf)
            subset = csv.loc[mask]

            try:
                # Prefixos de latitude e longitude
                lat_prefixo = 's' if subset['LATITUDE'].iloc[0] < 0 else 'n'
                lon_prefixo = 'w' if subset['LONGITUDE'].iloc[0] < 0 else 'e'

                # Número do arquivo SRTM
                if lat_prefixo == 's':
                    lat_num = math.ceil(abs(subset['LATITUDE'].iloc[0]))
                else:
                    lat_num = math.floor(abs(subset['LATITUDE'].iloc[0]))

                lon_num = math.ceil(abs(subset['LONGITUDE'].iloc[0]))
                filename = f"{lat_prefixo}{str(lat_num).zfill(2)}_{lon_prefixo}{str(lon_num).zfill(3)}_1arc_v3.tif"

                # Carregar arquivo
                path = os.path.join(DirSRTM, filename)
                dem_data = rasterio.open(path)
                dem_array = dem_data.read(1)

                elevations = []

                for _, row_data in subset.iterrows():
                    row, col = dem_data.index(row_data['LONGITUDE'], row_data['LATITUDE'])
                    elev = dem_array[row, col]

                    if elev < 0:
                        estacoes_negativas.setdefault(estacao, []).append(filename)

                    elevations.append(elev)

                # Atualiza a coluna ELEVACAO no CSV original
                csv.loc[mask, 'ELEVACAO'] = elevations

            except Exception as e:
                print(f"Erro na estação {estacao} ({filename}): {e}")
                continue

    # Corrigir as estações com erro (mantendo sua função existente)
    csv_neg = csv[csv['ID_OEMA'].isin(estacoes_negativas.keys())]
    csv_cor = corrige_elevacoes(csv_neg, estacoes_negativas, DirSRTM)
    csv.loc[csv_cor.index, 'ELEVACAO'] = csv_cor['ELEVACAO']

    return csv, estacoes_negativas

