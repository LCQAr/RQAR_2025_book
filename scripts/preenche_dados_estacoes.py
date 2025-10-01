import pandas as pd
import os

def preencher_estado(uf, arquivo_geral, arquivo_estado, arquivo_saida):
    """
    Preenche informações de uma planilha geral na planilha específica de um estado
    e reordena as colunas no padrão desejado.

    Esta função lê um arquivo geral com dados de todos os estados, filtra apenas o estado
    desejado, remove duplicatas, atualiza a planilha do estado com as informações selecionadas,
    reordena as colunas e salva o resultado em um arquivo de saída.

    Parameters
    ----------
    uf : str
        Sigla do estado que será processado (ex.: "SP", "RJ").
    arquivo_geral : str
        Caminho completo para o arquivo CSV contendo os dados gerais de todos os estados.
    arquivo_estado : str
        Caminho completo para o arquivo CSV do estado que será preenchido com os dados.
    arquivo_saida : str
        Caminho completo para o arquivo CSV de saída, onde os dados atualizados serão salvos.

    Returns
    -------
    None
        A função não retorna valores. Apenas gera um arquivo CSV preenchido com as informações do estado.
    """

    # --- 1. Ler os dados ---
    df_geral = pd.read_csv(arquivo_geral, encoding="utf-8")
    df_estado = pd.read_csv(arquivo_estado, encoding="utf-8")

    # --- 2. Filtrar apenas a UF desejada ---
    df_geral = df_geral[df_geral["UF"] == uf]

    # --- 3. Colunas a preencher da planilha geral ---
    colunas_preencher = [
        "CIDADE", "CD_MUN", "PROPRIETARIO", "PROP_ENTIDADE",
        "OPERADOR", "OP_ENTIDADE", "FUNCIONAMENTO", "CATEGORIA",
        "STATUS", "REP_ESPACIAL", "FINALIDADE",
        "LATITUDE", "LONGITUDE", "MONITORAR", "FONTE",
    ]

    # --- 4. Garantir apenas uma linha por ID_MMA ---
    df_geral_unico = df_geral.drop_duplicates(subset=["ID_MMA"] + colunas_preencher)

    # --- 5. Juntar os dados pelo ID_MMA ---
    df_estado = df_estado.drop(columns=[c for c in colunas_preencher if c in df_estado.columns], errors="ignore")
    df_estado = df_estado.merge(
        df_geral_unico[["ID_MMA"] + colunas_preencher],
        on="ID_MMA", how="left"
    )

    # --- 6. Reordenar colunas no padrão desejado ---
    ordem = [
        "UF", "COD_UF_IBGE", "ID_OEMA", "ID_MMA", "CIDADE", "CD_MUN",
        "CATEGORIA", "FUNCIONAMENTO", "PROPRIETARIO", "PROP_ENTIDADE",
        "OPERADOR", "OP_ENTIDADE", "LATITUDE", "LONGITUDE",
        "MOBILIDADE", "REALOCACAO", "POLUENTE", "MARCA", "METODO",
        "FINALIDADE", "INICIO", "FIM", "STATUS", 
        "CALIBRACAO", "OBS_CALIBRACAO", "MONITORAR", "FONTE", 
        "OBS_GERAIS", "DADOS_MONITORAMENTO", "RECONHECIDA", 
        "REP_ESPACIAL_DECLARADA"
    ]

    # campos = ["UF","CIDADE","CD_MUN","ID_OEMA","ID_MMA","ID_MMA_COMPLETO","PROPRIETARIO",
    #       "PROP_ENTIDADE","OPERADOR","OP_ENTIDADE","FUNCIONAMENTO","CATEGORIA","METODO",
    #       "CALIBRACAO","MARCA","MODELO","POLUENTE","COD_POLUENTE","MOBILIDADE","REP_ESPACIAL",
    #       "FINALIDADE","STATUS","INICIO","FIM","LATITUDE","LONGITUDE","MONITORAR","FONTE",
    #       "CERTIFICACAO","COD_UF_IBGE","ANOS_MONITORADOS","BASE_DADOS","ELEVACAO"]

    # Criar colunas vazias se não existirem
    for col in ordem:
        if col not in df_estado.columns:
            df_estado[col] = None

    # Reordenar
    df_estado = df_estado[ordem]

    # --- 7. Salvar resultado ---
    df_estado.to_csv(arquivo_saida, index=False, encoding="utf-8")
    print(f"[OK] {uf} salvo em: {arquivo_saida}")


# =============================
# Escolher UFs que você quer rodar
# =============================
lista_ufs = ["SP", "RJ", "MG"]  # <<< altere aqui

# Caminhos
arquivo_geral = r"RQAR_2025_book/data/Monitoramento_QAr_BR.csv"
pasta_estados = r"RQAR_2025_book\data\DADOS_ESTACOES"
pasta_saida   = r"RQAR_2025_book\data\DADOS_ESTACOES"

# =============================
# Loop para rodar para todos os estados da lista
# =============================
for uf in lista_ufs:
    arquivo_estado = os.path.join(pasta_estados, f"{uf}_estacoes_teste.csv")
    arquivo_saida   = os.path.join(pasta_saida, f"{uf}_estacoes.csv")
    
    try:
        preencher_estado(uf, arquivo_geral, arquivo_estado, arquivo_saida)
    except FileNotFoundError:
        print(f"[ERRO] Arquivo do estado {uf} não encontrado.")
