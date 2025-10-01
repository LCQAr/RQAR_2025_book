"""
CRIANDO O MONITORAMENTO_QAR_BR do zero acumulando e explodindo as planilhas intermediárias
com os dados das estações dos estados prontas
MQar --> utilizar esse código 
ainda precisa modificar alguns preenchimentos das colunas como DADOS_MONITORAMENTO e RECONHECIDA
"""
import pandas as pd
import glob
import os
import re

def gerar_monitoramento_qar(pasta_estados, arquivo_codigos, saida_geral, ufs_escolhidas=None, arquivo_sp=None):
    """
    Cria o arquivo de Monitoramento QAR acumulando e explodindo planilhas de estações.

    Parameters
    ----------
    pasta_estados : str
        Pasta onde estão os arquivos de estações dos estados.
    arquivo_codigos : str
        Arquivo CSV com código de poluentes, contendo também coluna NOME_PASTA.
    saida_geral : str
        Caminho do arquivo CSV final.
    ufs_escolhidas : list, optional
        Lista de UFs a processar. Se None, processa todas encontradas.
    arquivo_sp : str, optional
        Arquivo Excel com informações de METODO para SP.
    """

    if ufs_escolhidas is None:
        ufs_escolhidas = ["BA", "MA", "SC", "ES", "SP"]

    # --- Função interna para explosão de POLUENTE, METODO e MARCA ---
    def explode_pol_mtd_marca(df):
        linhas = []

        for _, row in df.iterrows():
            poluentes = [p.strip() for p in str(row.get("POLUENTE", "")).split(",") if p.strip()]
            poluentes_expandidos = []
            for p in poluentes:
                if p.upper() == "MP":
                    poluentes_expandidos.extend(["MP10", "MP25", "PTS"])
                else:
                    poluentes_expandidos.append(p)

            # Métodos
            metodos_dict = {}
            if pd.notna(row.get("METODO", "")) and row["METODO"].strip():
                for item in row["METODO"].split(","):
                    item = item.strip()
                    match = re.search(r"\((.*?)\)", item)
                    if match:
                        pols = [p.strip() for p in match.group(1).split(",")]
                        for p in pols:
                            if p.upper() == "MP":
                                for mp in ["MP10", "MP25", "PTS"]:
                                    metodos_dict[mp] = item
                            else:
                                metodos_dict[p.strip()] = item

            # Marcas
            marcas_dict = {}
            if pd.notna(row.get("MARCA", "")) and row["MARCA"].strip():
                for item in row["MARCA"].split(","):
                    item = item.strip()
                    match = re.search(r"\((.*?)\)", item)
                    if match:
                        pols = [p.strip() for p in match.group(1).split(",")]
                        for p in pols:
                            if p.upper() == "MP":
                                for mp in ["MP10", "MP25", "PTS"]:
                                    marcas_dict[mp] = item
                            else:
                                marcas_dict[p.strip()] = item

            for pol in poluentes_expandidos:
                nova = row.copy()
                nova["POLUENTE"] = pol
                nova["METODO"] = metodos_dict.get(pol, "")
                nova["MARCA"] = marcas_dict.get(pol, "")
                linhas.append(nova)

        return pd.DataFrame(linhas)

    # --- Carregar dicionário de poluentes ---
    df_cod = pd.read_csv(arquivo_codigos, dtype=str)
    mapa_codigos = dict(zip(df_cod["POLUENTE"].str.strip(), df_cod["COD_POLUENTE"].str.strip()))
    mapa_nome = dict(zip(df_cod["POLUENTE"].str.strip(), df_cod["NOME_PASTA"].str.strip()))

    # --- Listar arquivos ---
    arquivos = glob.glob(os.path.join(pasta_estados, "*_estacoes.*"))
    arquivos = [a for a in arquivos if os.path.basename(a)[:2].upper() in ufs_escolhidas]

    if not arquivos:
        print("⚠ Nenhum arquivo encontrado para as UFs escolhidas!")
        return

    df_final = []

    # --- Processar arquivos ---
    for arq in arquivos:
        if arq.endswith(".csv"):
            df = pd.read_csv(arq, dtype=str)
        else:
            df = pd.read_excel(arq, dtype=str)

        # Limpar espaços
        for col in df.select_dtypes(include="object").columns:
            df[col] = df[col].str.strip()

        # Explodir POLUENTE
        if "POLUENTE" in df.columns:
            df = explode_pol_mtd_marca(df)

        # Preencher COD_POLUENTE
        df["COD_POLUENTE"] = df.get("POLUENTE", "").map(mapa_codigos).fillna("").astype(str)
        df["COD_POLUENTE"] = df["COD_POLUENTE"].apply(lambda x: x.zfill(3) if x.isdigit() else x)

        # Substituir POLUENTE pelo NOME_PASTA do dicionário
        df["POLUENTE"] = df.get("POLUENTE", "").map(mapa_nome).fillna(df.get("POLUENTE", ""))

        # Criar ID_MMA_COMPLETO
        df["ID_MMA_COMPLETO"] = (
            df["ID_MMA"].astype(str)
            + df.get("CATEGORIA", "").astype(str).str[:1].fillna("")
            + df.get("FUNCIONAMENTO", "").astype(str).str[:1].fillna("")
            + df["COD_POLUENTE"]
        )

        df_final.append(df)

    # --- Concatenar todos os dados ---
    df_final = pd.concat(df_final, ignore_index=True)

    # --- Preencher METODO de SP se arquivo_sp for fornecido ---
    if arquivo_sp:
        df_sp = pd.read_csv(arquivo_sp, dtype=str)
        for col in ["POLUENTE", "FUNCIONAMENTO", "METODO"]:
            if col in df_sp.columns:
                df_sp[col] = df_sp[col].astype(str).str.strip()

        def preencher_metodo_sp(row):
            if row.get("UF") != "SP":
                return row.get("METODO", "")
            cond = (df_sp["POLUENTE"] == row.get("POLUENTE", "")) & (df_sp["FUNCIONAMENTO"] == row.get("FUNCIONAMENTO", ""))
            match = df_sp.loc[cond, "METODO"]
            if not match.empty:
                return match.values[0]
            else:
                return row.get("METODO", "")

        df_final["METODO"] = df_final.apply(preencher_metodo_sp, axis=1)

    # --- Reorganizar colunas antes de salvar ---
    colunas_desejadas = [
        "UF","ID_OEMA","CIDADE","ID_MMA","ID_MMA_COMPLETO","POLUENTE","COD_POLUENTE",
        "CD_MUN","COD_UF_IBGE","PROPRIETARIO","PROP_ENTIDADE","OPERADOR","OP_ENTIDADE",
        "LATITUDE","LONGITUDE","MOBILIDADE","CATEGORIA","FUNCIONAMENTO","METODO",
        "MARCA","FINALIDADE","MONITORAR","FONTE","CALIBRACAO","REALOCACAO",
        "OBS_CALIBRACAO","DADOS_MONITORAMENTO","RECONHECIDA","OBS_GERAIS",
        "CERTIFICACAO","REP_ESPACIAL_DECLARADA"
    ]

    # Criar colunas que não existem
    for col in colunas_desejadas:
        if col not in df_final.columns:
            df_final[col] = ""

    # Ordenar: primeiras as desejadas, depois qualquer outra que sobrou
    outras_colunas = [c for c in df_final.columns if c not in colunas_desejadas]
    df_final = df_final[colunas_desejadas + outras_colunas]

    # --- Salvar CSV final ---
    df_final.to_csv(saida_geral, index=False, encoding="utf-8-sig")
    print(f"✅ Planilha geral salva em: {saida_geral}")


# --- Chamando a função ---
gerar_monitoramento_qar(
    pasta_estados=r"C:\Users\marit\OneDrive\GAr_BR\Objetivo_07\2025\dados_estacoes",
    arquivo_codigos=r"C:\PYTHON\ENS5132\ENS5132\MMA\inputs\CODIGO_POLUENTES.csv",
    saida_geral=r"C:\PYTHON\ENS5132\ENS5132\MMA\ouputs\Monitoramento_QAr_BR.csv",
    ufs_escolhidas=["BA", "MA", "SC", "ES", "SP","RS"],
    arquivo_sp=r"C:\PYTHON\ENS5132\ENS5132\MMA_dados_2025\inputs\SP\SP_infos_metodo.csv"
)
