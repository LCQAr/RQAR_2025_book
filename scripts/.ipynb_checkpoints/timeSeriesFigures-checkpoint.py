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

# Folder with CSV files
data_folder = "data"

# List CSV files
csv_files = [f for f in os.listdir(data_folder) if f.endswith('.csv')]

# Dropdown widget to select file
file_dropdown = widgets.Dropdown(
    options=csv_files,
    description='CSV:',
    disabled=False,
)

# Dropdown widget to select column (will be updated later)
column_dropdown = widgets.Dropdown(
    options=[],
    description='Column:',
    disabled=False
)

# Date column input
date_column_input = widgets.Text(
    value='date',
    description='Date col:',
    placeholder='Enter date column name'
)

# Output area
output = widgets.Output()

def update_column_dropdown(change):
    try:
        file_path = os.path.join(data_folder, file_dropdown.value)
        df = pd.read_csv(file_path, encoding='utf-8')
        column_dropdown.options = [col for col in df.columns if col != date_column_input.value]
    except Exception as e:
        column_dropdown.options = []
        with output:
            clear_output()
            print(f"Error reading file: {e}")

# Function to plot
def plot_csv(file, column, date_col):
    with output:
        clear_output()
        try:
            file_path = os.path.join(data_folder, file)
            df = pd.read_csv(file_path, encoding='utf-8')
            df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
            df = df.dropna(subset=[date_col, column])
            df = df.sort_values(date_col)

            plt.figure(figsize=(10, 4))
            plt.plot(df[date_col], df[column], marker='o', linestyle='-')
            plt.xlabel(date_col)
            plt.ylabel(column)
            plt.title(f"{column} over time")
            plt.grid(True)
            plt.tight_layout()
            plt.show()
        except Exception as e:
            print(f"Error plotting: {e}")

# Trigger update when file changes
file_dropdown.observe(update_column_dropdown, names='value')

# Button to plot
plot_button = widgets.Button(description="Plot")

def on_plot_clicked(b):
    plot_csv(file_dropdown.value, column_dropdown.value, date_column_input.value)

plot_button.on_click(on_plot_clicked)

# Layout
ui = widgets.VBox([file_dropdown, date_column_input, column_dropdown, plot_button, output])
display(ui)
