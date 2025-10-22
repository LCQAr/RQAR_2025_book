#!/usr/bin/env python
# coding: utf-8

#-----------------------------Importação de pacotes ------------------------------------

import os, time, math, requests, pandas as pd
from datetime import datetime, timedelta, timezone
import pandas as pd
from collections import defaultdict
import re
import numpy as np
from pathlib import Path
import difflib
import unicodedata
from typing import Callable, Any, Optional
from functools import partial
from pandas.api.types import is_object_dtype, is_string_dtype
from collections import Counter
import unicodedata as ud


#----------------------------- Dicionários e listas ------------------------------------

mqar_campos = [
        "UF","ID_OEMA","CIDADE","ID_MMA","ID_MMA_COMPLETO","POLUENTE","COD_POLUENTE",
        "CD_MUN","COD_UF_IBGE","PROPRIETARIO","PROP_ENTIDADE","OPERADOR","OP_ENTIDADE",
        "LATITUDE","LONGITUDE","MOBILIDADE","CATEGORIA","FUNCIONAMENTO","METODO",
        "MARCA",'INICIO', 'FIM',"FINALIDADE","MONITORAR","FONTE","CALIBRACAO","REALOCACAO",
        "OBS_CALIBRACAO","DADOS_MONITORAMENTO","RECONHECIDA","OBS_GERAIS",
        "STATUS","CERTIFICACAO","REP_ESPACIAL_DECLARADA"
    ]

name_to_uf = {
    "acre":"AC","alagoas":"AL","amapa":"AP","amazonas":"AM","bahia":"BA","ceara":"CE",
    "distrito federal":"DF","espirito santo":"ES","goias":"GO","maranhao":"MA",
    "mato grosso":"MT","mato grosso do sul":"MS","minas gerais":"MG","para":"PA",
    "paraiba":"PB","parana":"PR","pernambuco":"PE","piaui":"PI","rio de janeiro":"RJ",
    "rio grande do norte":"RN","rio grande do sul":"RS","rondonia":"RO","roraima":"RR",
    "santa catarina":"SC","sao paulo":"SP","sergipe":"SE","tocantins":"TO"
}


UF_TO_IBGE = {
    "AC":12,"AL":27,"AP":16,"AM":13,"BA":29,"CE":23,"DF":53,"ES":32,"GO":52,"MA":21,
    "MT":51,"MS":50,"MG":31,"PA":15,"PB":25,"PR":41,"PE":26,"PI":22,"RJ":33,"RN":24,
    "RS":43,"RO":11,"RR":14,"SC":42,"SP":35,"SE":28,"TO":17
}

def sigla_to_ibge(uf): return UF_TO_IBGE[uf.upper()]


# Importar planilha com os códigos de poluentes
base = Path.cwd().parent  
out_dir = base / "data" / "dicionarios" 
out_dir.mkdir(parents=True, exist_ok=True)

df_cod = pd.read_csv(out_dir / 'CODIGO_POLUENTES.csv')


# Importar planilha com as respostas do formulário das UFs
base = Path.cwd().parent  
fr_dir = base / "data" 
fr_dir.mkdir(parents=True, exist_ok=True)

forms = pd.read_csv(fr_dir / '2025_Formulário_Coleta_Respostas_UFs.csv')

#Indice das colunas com respostas sobre rede de monitoramento
# for i, c in enumerate(forms.columns):
#    print(f"[{i}] {c}")

idxs = [6,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22] 


#----------------------------- Ler e abrir arquivos CSV ------------------------------------


def _read_csv(path, sep=None, decimal=None, encoding=None, **kw):
    head = path.read_bytes()[:4096]
    txt  = head.decode(encoding or "utf-8", errors="ignore")
    sep_guess = sep or (";" if txt.count(";") > txt.count(",") else ",")
    dec_guess = decimal or ("," if re.search(r"\d+,\d+", txt) and txt.count(",") > txt.count(".") else ".")
    enc_guess = encoding or ("utf-8-sig" if txt.startswith("\ufeff")
                             else ("latin-1" if ("Ã" in txt or "�" in txt) else "utf-8"))
    try:
        return pd.read_csv(path, sep=sep_guess, decimal=dec_guess, encoding=enc_guess, engine="c", **kw)
    except Exception:
        return pd.read_csv(path, sep=None, engine="python", decimal=dec_guess, encoding=enc_guess, **kw)

def load_csvs(dir_path, prefix=None, recursive=False, limit=None, **read_csv_kwargs):
    pattern = "**/*.csv" if recursive else "*.csv"
    files = sorted(dir_path.glob(pattern))
    if prefix:
        p = prefix.upper()
        files = [f for f in files if f.name.upper().startswith(p)]
    if limit:
        files = files[:int(limit)]
    dfs = {}
    for f in files:
        df = _read_csv(f, **read_csv_kwargs)
        key = f.stem
        # avoid key clashes
        if key in dfs:
            key = f"{f.stem}__{len(dfs)}"
        dfs[key] = df
        print(f"Loaded {f.name}: {df.shape}")
    return dfs

#----------------------------- Ler e abrir arquivos TXT ------------------------------------

def _read_txt(path, sep=None, decimal=None, encoding=None, header=None, **kw):
    head = path.read_bytes()[:4096]
    txt  = head.decode(encoding or "utf-8", errors="ignore")

    enc_guess = encoding or ("utf-8-sig" if txt.startswith("\ufeff")
                             else ("latin-1" if ("Ã" in txt or "�" in txt) else "utf-8"))
    dec_guess = decimal or ("," if re.search(r"\d+,\d+", txt) and txt.count(",") > txt.count(".") else ".")

    if sep is not None:
        sep_guess = sep
    else:
        candidates = ["\t", ";", "|", ","]
        counts = {d: txt.count(d) for d in candidates}
        sep_guess = max(counts, key=counts.get) if max(counts.values()) >= 2 else None

    try:
        if sep_guess is None:
            return pd.read_csv(path, sep=None, engine="python",
                               decimal=dec_guess, encoding=enc_guess,
                               header=header, **kw)
        else:
            return pd.read_csv(path, sep=sep_guess, engine="c",
                               decimal=dec_guess, encoding=enc_guess,
                               header=header, **kw)
    except Exception:
        full = path.read_text(encoding=enc_guess, errors="ignore")
        return pd.DataFrame({"text": full.splitlines()})

def load_txts(dir_path, prefix=None, recursive=False, limit=None, **read_txt_kwargs):
    pattern = "**/*.txt" if recursive else "*.txt"
    files = sorted(dir_path.glob(pattern))
    if prefix:
        p = prefix.upper()
        files = [f for f in files if f.name.upper().startswith(p)]
    if limit:
        files = files[:int(limit)]
    dfs = {}
    for f in files:
        df = _read_txt(f, **read_txt_kwargs)
        key = f.stem
        if key in dfs:
            key = f"{f.stem}__{len(dfs)}"
        dfs[key] = df
        print(f"Loaded {f.name}: {df.shape}")
    return dfs

#----------------------------- Ler e abrir arquivos XLSX ------------------------------------

EXCEL_EXTS = {".xlsx", ".xls", ".xlsm", ".xltx", ".xltm"}

def _excel_engine(ext: str) -> str | None:
    """
    Retorna o engine recomendado para cada extensão.
    .xlsx, .xlsm, .xltx, .xltm -> openpyxl
    .xls -> xlrd (necessita instalar xlrd)
    """
    ext = ext.lower()
    if ext in {".xlsx", ".xlsm", ".xltx", ".xltm"}:
        return "openpyxl"
    if ext == ".xls":
        return "xlrd"  
    return None


def load_excels(dir_path, sheets=0, prefix=None, recursive=False, limit=None, **read_excel_kwargs):
    """
    Lê arquivos Excel de uma pasta e retorna um dicionário {chave: DataFrame}.

    Parâmetros:
      - dir_path: str | Path
        Caminho da pasta onde estão os arquivos.
      - sheets: int | str | list | "all"
        Qual planilha carregar.
        0 carrega a primeira planilha. Pode ser índice (int) ou nome (str).
        Lista para múltiplas planilhas. "all" para todas as planilhas.
      - prefix: str | None
        Se definido, carrega apenas arquivos cujo nome começa com este prefixo.
      - recursive: bool
        Se True, busca nas subpastas.
      - limit: int | None
        Limita a quantidade de arquivos lidos.
      - **read_excel_kwargs:
        Parâmetros extras repassados na função

    Retorno:
      - Dicionário com chave nome base do arquivo
    """
    dir_path = Path(dir_path)
    files = []
    if recursive:
        for ext in EXCEL_EXTS:
            files += list(dir_path.rglob(f"*{ext}"))
    else:
        for ext in EXCEL_EXTS:
            files += list(dir_path.glob(f"*{ext}"))
    files = sorted(files)

    if prefix:
        p = prefix.upper()
        files = [f for f in files if f.name.upper().startswith(p)]
    if limit:
        files = files[:int(limit)]

    dfs = {}
    for f in files:
        eng = _excel_engine(f.suffix)
        try:
            with pd.ExcelFile(f, engine=eng) as xls:
                if sheets == "all":
                    wanted = xls.sheet_names
                elif isinstance(sheets, (list, tuple)):
                    wanted = sheets
                else:
                    wanted = [sheets]

                for s in wanted:
                    df = pd.read_excel(xls, sheet_name=s, **read_excel_kwargs)
                    if sheets == "all" or isinstance(sheets, (list, tuple)):
                        sheet_label = s if isinstance(s, str) else xls.sheet_names[s]
                        key = f"{f.stem}__{sheet_label}"
                    else:
                        key = f.stem
                    if key in dfs:
                        i = 1
                        new_key = f"{key}__{i}"
                        while new_key in dfs:
                            i += 1
                            new_key = f"{key}__{i}"
                        key = new_key

                    dfs[key] = df
                    print(f"Loaded {f.name} [sheet {s}]: {df.shape}")
        except Exception as e:
            print(f"Skip {f.name} due to read error: {e}")
            continue
    return dfs


#----------------------------- Remover e substituir caracteres ------------------------------------

CLEAN_TABLE = {
    ord("ç"): "c",
    ord("Ç"): "C",
    ord("´"): None,
    ord("~"): None,
    ord("ˆ"): None,
    ord("°"): None,
    ord("`"): None,
    0x0302: None,  # combining ^
}

def clean_text_full(s: object) -> object:
    if pd.isna(s):
        return s
    t = str(s)
    # sua tabela primeiro
    t = t.translate(CLEAN_TABLE)
    # remover acentos de letras precompostas (ex.: ã, á, í)
    t = unicodedata.normalize("NFKD", t)
    t = "".join(ch for ch in t if unicodedata.category(ch) != "Mn")
    return t

def clean_df_all_text(df: pd.DataFrame, cols=None, in_place=False) -> pd.DataFrame:
    out = df if in_place else df.copy()
    if cols is None:
        cols = [c for c in out.columns
                if is_object_dtype(out[c].dtype) or is_string_dtype(out[c].dtype)
                   or isinstance(out[c].dtype, pd.CategoricalDtype)]
    for c in cols:
        s = out[c]
        was_cat = isinstance(s.dtype, pd.CategoricalDtype)
        s2 = s.astype("string").map(lambda v: clean_text_full(v) if pd.notna(v) else v)
        out[c] = s2.astype("category") if was_cat else s2
    return out


#----------------------------- Transformar coluna Datetime ------------------------------------

def convert_column_to_datetime(df, column_name, format=None):
    out = df.copy()

    if (out.index.name or "").upper() == column_name.upper():
        if column_name in out.columns:
            out.reset_index(drop=True, inplace=True)
        else:
            out.reset_index(inplace=True)

    if column_name not in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out.index):
            out[column_name] = out.index
            if not keep_index:
                out.reset_index(drop=True, inplace=True)
        else:
            raise ValueError(f"Column or datetime index '{column_name}' not found.")

    out[column_name] = pd.to_datetime(out[column_name], format=format,  errors="coerce")

    return out


#----------------------------- Inspecionar colunas repetidas no mesmo dicionário ------------------------------------

def _flatten_columns(df):
    """
    Achata colunas MultiIndex em strings simples.
    Exemplo: ("A","B") vira "A | B".
    """
    cols = df.columns
    if isinstance(cols, pd.MultiIndex):
        return [" | ".join([str(x) for x in tup if pd.notna(x)]) for tup in cols]
    return [str(c) for c in cols]


def _normalize(names, lower=True, strip=True):
    """
    Normaliza nomes de colunas para comparação justa.
    - lower: converte para minúsculas
    - strip: remove espaços extras
    """
    out = []
    for n in names:
        s = str(n)
        if strip:
            s = s.strip()
        if lower:
            s = s.lower()
        out.append(s)
    return out


def summarize_columns(dfs: dict, normalize=True):
    """
    Resume colunas presentes em um dicionário {nome_df: DataFrame}.

    Parâmetros
    - dfs: dict[str, pd.DataFrame]
      Dicionário onde a chave é o nome e o valor é um DataFrame.
    - normalize: bool
      Se True, compara usando nomes normalizados (minúsculas e trim).

    Retorno
    - summary_df: pd.DataFrame
      Tabela com uma linha por coluna distinta:
        col            nome da coluna considerada na comparação
        n_present      em quantos DataFrames ela aparece
        n_missing      em quantos não aparece
        is_common      True se aparece em todos
        is_unique      True se aparece em apenas um
        present_in     lista de DataFrames onde aparece
        missing_in     lista de DataFrames onde não aparece
        examples       exemplos de rótulos originais vistos para esta coluna
    - per_df_stats: pd.DataFrame
      Uma linha por DataFrame com:
        n_cols                 quantidade de colunas
        n_common_present       quantas colunas comuns ele possui
        n_common_missing       quantas colunas comuns faltam nele
        extras_count           colunas que só existem em alguns e estão nele
        extras                 lista dessas colunas extras
    """
    # 1) coletar nomes por df
    name_to_cols = {}
    name_to_rawmap = {}
    for name, df in dfs.items():
        cols_raw = _flatten_columns(df)
        cols_cmp = _normalize(cols_raw) if normalize else cols_raw
        name_to_cols[name] = set(cols_cmp)
        # mapeia versão normalizada para exemplos originais
        rawmap = {}
        for raw, cmp in zip(cols_raw, cols_cmp):
            rawmap.setdefault(cmp, set()).add(raw)
        name_to_rawmap[name] = rawmap

    all_cols = set().union(*name_to_cols.values()) if name_to_cols else set()
    df_names = list(name_to_cols.keys())
    n_dfs = len(df_names)

    # 2) frequências por coluna
    records = []
    for col in sorted(all_cols):
        present_in = [n for n in df_names if col in name_to_cols[n]]
        missing_in = [n for n in df_names if col not in name_to_cols[n]]
        # exemplos de rótulos originais
        examples = sorted(set().union(*[name_to_rawmap[n].get(col, set()) for n in df_names]))
        records.append({
            "col": col,
            "n_present": len(present_in),
            "n_missing": n_dfs - len(present_in),
            "is_common": len(present_in) == n_dfs,
            "is_unique": len(present_in) == 1,
            "present_in": present_in,
            "missing_in": missing_in,
            "examples": examples[:5],  # mostra até 5 exemplos
        })
    summary_df = pd.DataFrame(records).sort_values(
        ["is_common", "n_present", "col"], ascending=[False, False, True]
    ).reset_index(drop=True)

    # 3) colunas comuns e extras
    common_set = set(summary_df.loc[summary_df["is_common"], "col"])
    per_df_rows = []
    for name in df_names:
        cols_set = name_to_cols[name]
        n_cols = len(cols_set)
        n_common_present = len(cols_set & common_set)
        n_common_missing = len(common_set - cols_set)
        extras = sorted(c for c in cols_set if c not in common_set)
        per_df_rows.append({
            "df": name,
            "n_cols": n_cols,
            "n_common_present": n_common_present,
            "n_common_missing": n_common_missing,
            "extras_count": len(extras),
            "extras": extras
        })
    per_df_stats = pd.DataFrame(per_df_rows).sort_values("df").reset_index(drop=True)

    return summary_df, per_df_stats


#----------------------------- Renomear colunas ------------------------------------

# manual_map = {"fecha":  "DATETIME",
#              "Date":  "DATETIME",
#              "Fecha":  "DATETIME",
#}

#----------------------------- Selecionar estações unicas no mesmo df ------------------------------------

# Nota: Quando há junção de mais de uma base de dados de fontes diferentes, utilizar função para manter estações não repetidas e garantir que a maioria das colunas com dados seja mantida.

def merge_by_id_multi(
    dfs_dict: dict,
    id_cols,              # pode ser "ID_OEMA" ou ["ID_OEMA","UF"]
    source_col="__source",
    source_priority: list[str] | None = None,
    drop_empty_strings: bool = True,
):
    """
    Une vários DataFrames (em um dict) e mantém 1 linha por chave composta.

    Parâmetros:
      - dfs_dict: dict[str, pd.DataFrame]  dicionário nome->DataFrame.
      - id_cols: str | list/tuple          coluna(s) que formam a chave. Ex.: "ID_OEMA" ou ["ID_OEMA","UF"].
      - source_col: str                    coluna auxiliar com o nome da fonte.
      - source_priority: list[str] | None  prioridade entre fontes para resolver conflitos.
      - drop_empty_strings: bool           converte strings vazias em NaN antes de mesclar.

    Retorna:
      - df_merged: DataFrame final com 1 linha por chave.
      - df_conflicts: DataFrame listando conflitos por coluna e chave.
    """
    if isinstance(id_cols, str):
        id_cols = (id_cols,)
    id_set = set(id_cols)

    # 1) concatena e marca fonte
    frames = []
    for name, df in dfs_dict.items():
        if isinstance(df, pd.DataFrame):
            tmp = df.copy()
            tmp[source_col] = name
            frames.append(tmp)
    if not frames:
        return pd.DataFrame(), pd.DataFrame()
    big = pd.concat(frames, ignore_index=True, sort=False)

    # garante que todas as colunas de chave existam
    for c in id_cols:
        if c not in big.columns:
            big[c] = pd.NA

    # 2) normalização leve
    if drop_empty_strings:
        for c in big.columns:
            if big[c].dtype.kind in "OUS":
                big[c] = big[c].astype("string").str.strip().replace({"": pd.NA})

    def pick_value(series, sources):
        mask = series.notna()
        vals = series[mask].astype(object).tolist()
        srcs = sources[mask].astype(str).tolist()
        if not vals:
            return pd.NA, None, []
        if len(set(map(str, vals))) == 1:
            return vals[0], srcs[0], list(dict.fromkeys(srcs))
        if source_priority:
            pri = {s: i for i, s in enumerate(source_priority)}
            best = min(range(len(srcs)), key=lambda i: pri.get(srcs[i], 10**9))
            return vals[best], srcs[best], list(dict.fromkeys(srcs))
        return vals[0], srcs[0], list(dict.fromkeys(srcs))

    # 3) reduz por chave composta
    data_cols = [c for c in big.columns if c not in id_set | {source_col}]
    rows, conflicts = [], []
    for key_vals, g in big.groupby(list(id_cols), dropna=True, sort=False):
        if len(id_cols) == 1:
            key_vals = (key_vals,)
        out = {c: v for c, v in zip(id_cols, key_vals)}

        for c in data_cols:
            s = g[c] if c in g.columns else pd.Series([pd.NA] * len(g))
            winner, winner_src, all_srcs = pick_value(s, g[source_col])
            out[c] = winner

            non_null = [str(v) for v in s.dropna().tolist()]
            if len(set(non_null)) > 1:
                confl = {col: val for col, val in zip(id_cols, key_vals)}
                confl.update({
                    "col": c,
                    "values": sorted(set(non_null)),
                    "sources": all_srcs,
                    "chosen": str(winner),
                    "chosen_source": winner_src,
                })
                conflicts.append(confl)

        rows.append(out)

    df_merged = pd.DataFrame(rows)
    ordered = list(id_cols) + [c for c in df_merged.columns if c not in id_set]
    df_merged = df_merged[ordered]

    df_conflicts = pd.DataFrame(conflicts)
    return df_merged, df_conflicts


#----------------------------- Unir estações que estão dentro do mesmo dicionário ------------------------------------

# Nota: Maneira mais simplificada de unir diferentes dfs dentro de um dict, quando sabemos que não existem linhas duplicadas ou informações repetidas. Quando há dúvida, rodar a função anterior.

def merge_station_dfs(dfs_dict, uf):
    frames = []
    for station_name, d in dfs_dict.items():
        df = d.copy()

        # station
        df["ESTACAO"] = station_name # LEMBRAR DE DAR UM DROP
        frames.append(df)

    if not frames:
        raise ValueError("No data frames to merge.")
    return pd.concat(frames, ignore_index=True, sort=False)


#----------------------------- Corrigir e identificar problemas com Datetime ------------------------------------

TARGET_FMT = "%d/%m/%Y %H:%M"

def fix_datetime_df(df, col, keep_dt_col=True):
    out = df.copy()
    out.rename(columns=lambda c: str(c).strip().lstrip("\ufeff"), inplace=True)

    s = (out[col].astype(str)
                  .str.strip()
                  .str.replace("\xa0", " ", regex=False)   # nbsp
                  .str.replace("T", " ", regex=False)
                  .str.replace("Z", "", regex=False))

    dt = pd.Series(pd.NaT, index=out.index, dtype="datetime64[ns]")

    # put your actual input formats first
    tries = [
        ("%H:%M %m/%d/%Y", False),       # 02:00 1/1/2019
        ("%H:%M:%S %m/%d/%Y", False),    # 02:00:00 1/1/2019
        ("%d/%m/%Y %H:%M", True),
        ("%d/%m/%Y %H:%M:%S", True),
        ("%Y-%m-%d %H:%M", False),
        ("%Y-%m-%d %H:%M:%S", False),
        ("%d-%b-%Y %H:%M", True),
        ("%d-%b-%Y %H:%M:%S", True),
    ]

    for fmt, dayfirst in tries:
        m = dt.isna()
        if not m.any():
            break
        dt.loc[m] = pd.to_datetime(s[m], format=fmt, errors="coerce", dayfirst=dayfirst)

    # final fallback
    m = dt.isna()
    if m.any():
        try:
            dt.loc[m] = pd.to_datetime(s[m], format="mixed", dayfirst=True, errors="coerce")
        except TypeError:
            dt.loc[m] = pd.to_datetime(s[m], dayfirst=True, errors="coerce")

    if keep_dt_col:
        out[f"{col}_DT"] = dt

    out[col] = np.where(dt.notna(), dt.dt.strftime(TARGET_FMT), np.nan)
    return out


# Diagnóstico das colunas ou linhas com problema
def diag_bad_stations(df_all, col="DATETIME", top=5):
    out = []
    for st, g in df_all.groupby("ESTACAO"):
        rate = g[col].notna().mean()
        if rate < 0.99:
            bad = g.loc[g[col].isna(), col].astype(str).head(top).tolist()
            out.append((st, rate, bad))
    for st, rate, examples in out:
        print(f"{st}: parsed {rate:.1%}  examples not parsed -> {examples}")


#----------------------------- Criar colunas de INICIO e FIM das medições ------------------------------------

def station_year_bounds(g: pd.DataFrame, datetime_col: Optional[str]):
    if not datetime_col or datetime_col not in g.columns:
        return pd.NA, pd.NA
    s = pd.to_datetime(g[datetime_col], dayfirst=True)
    if s.notna().any():
        return int(s.min().year), int(s.max().year)
    return pd.NA, pd.NA

#----------------------------- Criar coluna padronizada de poluentes ------------------------------------

# Função para mapear e converter apenas os nomes dos poluentes quando no CABEÇALHO DAS COLUNAS
def id_pol(df, df_cod, column_name, drop_after_underscore=True):
    nomes = []
    for col in df.columns:
        if col == column_name:
            continue  

        # limpa parênteses -> "CO(µg/m³)" -> "CO"
        new_col = re.sub(r"\(.*?\)", "", col).strip()
        # keep only left side before first underscore if you want
        if drop_after_underscore and "_" in new_col:
            new_col = new_col.split("_", 1)[0]

        # verifica no dicionário
        linha = df_cod[df_cod["POLUENTE"].str.strip() == new_col]
        if not linha.empty:
            nomes.append(linha["NOME_PASTA"].values[0])

    return ",".join(sorted(set(nomes)))  # retorna só os nomes únicos


# Função para mapear e converter apenas os nomes dos poluentes quando NAS LINHAS DOS DFS
def id_pol_from_rows(
    df,
    df_cod,
    cols_cand=("POLUENTE","POLUENTES","Poluente","pollutant","nome_poluente","NomePoluente"),
    find_all=True,
    col_sinonimos=None,
    sep=r"[;,/|]+",
):
    """
    Identifica poluentes quando os nomes estão nas LINHAS e retorna nomes únicos
    padronizados conforme df_cod['NOME_PASTA'], separados por vírgula.

    Parâmetros:
      - df: DataFrame de entrada com as respostas.
      - df_cod: DataFrame de dicionário com colunas obrigatórias:
          'POLUENTE'  nome canônico
          'NOME_PASTA' nome padronizado desejado
        Opcional:
          col_sinonimos  nome de coluna em df_cod com sinônimos separados por '|'
      - cols_cand: possíveis nomes de coluna em df que contêm o texto dos poluentes.
      - find_all: se True, quando não encontrar cols_cand, varre todas as colunas de texto.
      - sep: regex para dividir listas no texto, ex "CO, NO2; PM10".

    Retorno:
      - str com nomes únicos padronizados, separados por vírgula.
    """

    # Normalização simples de rótulos para comparação
    def _erase(s: str) -> str:
        return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))

    def _norm(s: str) -> str:
        s = str(s)
        s = re.sub(r"\(.*?\)|\[.*?\]", "", s)  # remove unidades entre () ou []
        s = s.replace("µ", "u")
        s = _erase(s)
        s = re.sub(r"\s+", " ", s).strip().lower()
        return s

    # Mapa normalizado -> NOME_PASTA, incluindo sinônimos se houver
    cod_map = {}
    for _, row in df_cod.iterrows():
        cod_map[_norm(row["POLUENTE"])] = row["NOME_PASTA"]
        if col_sinonimos and col_sinonimos in df_cod.columns and pd.notna(row[col_sinonimos]):
            for alt in str(row[col_sinonimos]).split("|"):
                alt = alt.strip()
                if alt:
                    cod_map[_norm(alt)] = row["NOME_PASTA"]

    # Coleta de text candidatos
    text = []
    col_pol = next((c for c in df.columns if str(c).strip() in cols_cand), None)
    if col_pol is not None:
        text = df[col_pol].dropna().astype(str).tolist()
    elif find_all:
        for c in df.columns:
            if df[c].dtype.kind in "OUS":
                text += df[c].dropna().astype(str).tolist()

    if not text:
        return ""

    # Quebra por sep e mapeia para nomes padronizados
    seen = set()
    out = []
    sep_re = re.compile(sep)
    for t in text:
        partes = [p.strip() for p in sep_re.split(t)] if sep_re.search(t) else [t.strip()]
        for p in partes:
            if not p:
                continue
            k = _norm(p)
            nome = cod_map.get(k)
            if nome and nome not in seen:
                seen.add(nome)
                out.append(nome)

    return ",".join(sorted(out))

#----------------------------- Criar planilha final com dados da estações já processados (quando informações estão nas LINHAS) ------------------------------------

def build_inventory_rows(df_all,
                         df_cod,
                         uf,
                         datetime_col: str | None=None,
                         drop_after_underscore=True,
                         mode: str = "rows"):
    """
    Monta linhas do inventário por estação.

    Parâmetros:
      - df_all: DataFrame já unido, com colunas 'ESTACAO' e opcionalmente a coluna de data-hora.
      - df_cod: dicionário de poluentes com colunas 'POLUENTE' e 'NOME_PASTA' (e opcional 'SINONIMOS').
      - uf: sigla UF, ex. 'RJ'.
      - datetime_col: nome da coluna de data-hora ou None (quando não há).
      - mode:
          'columns' -> detectar poluentes no CABEÇALHO (usa sua função id_pol(...))
          'rows'    -> detectar poluentes nas LINHAS (usa id_pol_from_rows(...))

    Retorno:
      - DataFrame com uma linha por estação, incluindo POLUENTE, INICIO e FIM.
    """ 
    rows = []
    for station, g in df_all.groupby("ESTACAO", sort=True):
        inicio, fim = station_year_bounds(g, datetime_col)

        if mode == "columns":
            # usa função que lê do cabeçalho; passar um nome para ignorar
            col_to_ignore = datetime_col 
            pols = id_pol(g, df_cod, column_name=col_to_ignore, drop_after_underscore=True)
        else:
            # lê poluentes a partir das LINHAS; NÃO passe datetime_col aqui
            pols = id_pol_from_rows(g, df_cod)

        rows.append({
            "UF": uf,
            "ID_OEMA": station,
            "CIDADE": "",
            "ID_MMA": "",  # será preenchido depois
            "ID_MMA_COMPLETO": "",
            "POLUENTE": pols,
            "COD_POLUENTE": "",  # deixamos vazio
            "CD_MUN": "",
            "COD_UF_IBGE": sigla_to_ibge(uf),
            "PROPRIETARIO": "",
            "PROP_ENTIDADE": "",
            "OPERADOR": "",
            "OP_ENTIDADE": "",
            "LATITUDE": "",
            "LONGITUDE": "",
            "MOBILIDADE": "",
            "CATEGORIA": "",
            "FUNCIONAMENTO": "",
            "METODO": "",
            "MARCA": "",
            "FINALIDADE": "",
            "MONITORAR": "",
            "FONTE": "",
            "CALIBRACAO": "",
            "REALOCACAO": "",
            "OBS_CALIBRACAO": "",
            "INICIO": inicio,
            "FIM": fim,
            "DADOS_MONITORAMENTO": "",
            "RECONHECIDA": "",
            "OBS_GERAIS": "",
            "CERTIFICACAO": "",
            "STATUS": "",
            "REP_ESPACIAL_DECLARADA": ""
        })

    return pd.DataFrame(rows)


#----------------------------- Criar planilha final com dados da estações já processados (quando informações estão nas COLUNAS) ------------------------------------

def pick_group_value(s: pd.Series, strategy="first_non_null", sep=" | "):
    """
    Escolhe um valor representativo dentro de um grupo.
    - s: Série com valores do grupo
    - strategy: "first_non_null" | "mode" | "concat_unique"
    - sep: separador para concatenação
    """
    ss = s.dropna()
    if ss.empty:
        return None
    if strategy == "mode":
        m = ss.mode()
        return m.iloc[0] if not m.empty else ss.iloc[0]
    if strategy == "concat_unique":
        vals = pd.unique(ss.astype(str).str.strip())
        return sep.join([v for v in vals if v])
    return ss.iloc[0]  # padrão


def build_inventory_flexible(
    df_all: pd.DataFrame,
    uf: str,
    df_cod,                         # usado pelas funções de poluentes
    group_col: str = "ID_OEMA",
    datetime_col: Optional[str] = None,
    mode: str = "rows",
    field_map: Optional[dict[str, Any]] = None,
    drop_after_underscore=True
) -> pd.DataFrame:
    """
    PT-BR:
      - df_all: DataFrame com ao menos group_col.
      - uf: sigla da UF.
      - df_cod: dicionário de poluentes.
      - group_col: chave do agrupamento.
      - datetime_col: coluna de data-hora para INICIO/FIM (opcional).
      - mode: "rows" usa id_pol_from_rows, "columns" usa id_pol.
      - field_map: regras extras, ex. {"CIDADE": ("col","CIDADE",{"strategy":"mode"})}
    """
    if group_col not in df_all.columns:
        raise ValueError(f"Coluna de agrupamento '{group_col}' não existe.")

    # funções de poluentes por modo
    if mode == "columns":
        pol_func = lambda g: id_pol(g, df_cod, column_name=datetime_col, drop_after_underscore=True)
    else:
        pol_func = lambda g: id_pol_from_rows(g, df_cod)

    # regras base: valores por grupo usando ("func", ...)
    base_rules = {
        "UF": uf,
        "ID_OEMA": ("group_key",),
        "POLUENTE": ("func", pol_func),
        "COD_UF_IBGE": sigla_to_ibge(uf),
        "INICIO": ("func", lambda g: station_year_bounds(g, datetime_col)[0]) if datetime_col else "",
        "FIM":    ("func", lambda g: station_year_bounds(g, datetime_col)[1]) if datetime_col else "",
        "CIDADE": "",
        "ID_MMA": "",
        "ID_MMA_COMPLETO": "",
        "COD_POLUENTE": "",
        "CD_MUN": "",
        "PROPRIETARIO": "",
        "PROP_ENTIDADE": "",
        "OPERADOR": "",
        "OP_ENTIDADE": "",
        "LATITUDE": "",
        "LONGITUDE": "",
        "MOBILIDADE": "",
        "CATEGORIA": "",
        "FUNCIONAMENTO": "",
        "METODO": "",
        "MARCA": "",
        "FINALIDADE": "",
        "MONITORAR": "",
        "FONTE": "",
        "CALIBRACAO": "",
        "REALOCACAO": "",
        "OBS_CALIBRACAO": "",
        "DADOS_MONITORAMENTO": "",
        "RECONHECIDA": "",
        "OBS_GERAIS": "",
        "CERTIFICACAO": "",
        "STATUS": "",
        "REP_ESPACIAL_DECLARADA": "",
    }

    rules = {**base_rules, **(field_map or {})}

    rows = []
    for group_key, g in df_all.groupby(group_col, sort=True):
        out = {}
        for field, rule in rules.items():
            # literal
            if not isinstance(rule, tuple):
                out[field] = rule
                continue

            kind = rule[0]
            if kind == "group_key":
                out[field] = group_key
            elif kind == "col":
                colname = rule[1]
                opts = rule[2] if len(rule) > 2 and isinstance(rule[2], dict) else {}
                out[field] = pick_group_value(g[colname], **opts) if colname in g.columns else None
            elif kind == "func":
                func = rule[1] if len(rule) > 1 else None
                out[field] = func(g) if callable(func) else None
            else:
                out[field] = None

        rows.append(out)

    return pd.DataFrame(rows)


#----------------------------- Criar ID_MMA ------------------------------------

# NOTA: Sempre antes de criar ID_MMA COMPLETO na planilha final dos DADOS ESTAÇÕES, precisa garantir que as estações estejam com os campos início e fim preenchidos, para criar a sequência dos códigos - que depende do período de funcionamento

def _ascii_lower(s: str) -> str:
    s = str(s)
    s = ud.normalize("NFKD", s)
    s = "".join(ch for ch in s if not ud.combining(ch))
    return s.lower()

def assign_id_mma(df, uf_col="UF", date_col="INICIO"):
    out = df.copy()
    name_key = out["ID_OEMA"].astype(str).map(_ascii_lower)

    out = (
        out.assign(_name_key=name_key)
           .sort_values([uf_col, date_col, "_name_key"], kind="mergesort", na_position="last")
           .drop(columns="_name_key")
           .reset_index(drop=True)
    )

    seq = out.groupby(uf_col).cumcount().add(1).astype(str).str.zfill(4)
    out["ID_MMA"] = out[uf_col] + seq
    out["ID_MMA_COMPLETO"] = out["ID_MMA"]
    return out


#----------------------------- Conferir linhas duplicadas na planilha final ------------------------------------

# Linhas duplicadas por chave (ex: "ID_OEMA")
def get_duplicate_rows(df: pd.DataFrame, key: str = "ID_OEMA") -> pd.DataFrame:
    '''  - df: DataFrame final
         - key: nome da coluna que quer usar como filtro'''

    s = df[key].astype("string").str.strip()
    mask = s.duplicated(keep=False)
    return df.loc[mask].sort_values(key)

# Relatório por chave com número de linhas e colunas diferentes
def get_duplicates_report(df: pd.DataFrame, key: str = "ID_OEMA") -> pd.DataFrame:
    s = df[key].astype("string").str.strip()
    dups = df.loc[s.duplicated(keep=False)]
    rows = []
    for k, g in dups.groupby(key):
        nun = g.nunique(dropna=False)
        diff_cols = nun[nun > 1].index.tolist()
        rows.append({"ID": k, "n_rows": len(g), "diff_cols": diff_cols})
    rep = pd.DataFrame(rows).sort_values(["n_rows","ID"], ascending=[False, True])
    return rep

# Linhas duplicadas por chave dupla (ex: ["ID_OEMA","UF"])
def get_duplicate_rows_multi(df: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    # normaliza espaços nas chaves
    norm = df.copy()
    for k in keys:
        norm[k] = norm[k].astype("string").str.strip()
    mask = norm.duplicated(subset=keys, keep=False)
    return df.loc[mask].sort_values(keys)

# Todas as linhas de uma chave composta específica
def get_rows_for_keys(df: pd.DataFrame, keys: list[str], values: list) -> pd.DataFrame:
    m = pd.Series(True, index=df.index)
    for c, v in zip(keys, values):
        m &= df[c].astype("string").str.strip().eq(str(v).strip())
    return df.loc[m]


#----------------------------- Salvar como 'UF'_estacoes ------------------------------------

def save_UF_estacoes_csv(df_final, uf):
    base = Path.cwd().parent  
    out_dir = base / "data" / "DADOS_ESTACOES"
    out_dir.mkdir(parents=True, exist_ok=True)

    out_file = out_dir / f"{uf}_estacoes.csv"
    df_final.to_csv(out_file, index=False, encoding="utf-8")
    print("Saved to:", out_file.resolve())
    return

#----------------------------- Aplicação das funções nas UFs ------------------------------------

# ##### a) Ceará

# uf = "CE" 

# # Conferir respostas do formulário 
# ce_forms = forms[forms["Unidade da Federação: "].str.contains(uf, case=False, na=False)]
# ce_forms.iloc[:, idxs].head()

# # Importar arquivos do estado
# base = Path.cwd().parent 
# df_dir = base / "data" / "DADOS_BRUTOS" 
# df_dir.mkdir(parents=True, exist_ok=True)
# ce_dir = df_dir / uf

# ce_dfs = load_csvs(ce_dir)

# # Renomear todas as colunas com data e hora para datetime
# manual_map = {"fecha":  "DATETIME",
#               "Date":  "DATETIME",
#               "Fecha":  "DATETIME",
# }

# ce_dfs = {name: df.rename(columns=manual_map) for name, df in ce_dfs.items()}

# # Transformar coluna datetime para formato desejado
# ce_dfs = {
#     name: convert_column_to_datetime(d, column_name="DATETIME", format="%d/%m/%Y %H:%M")
#     for name, d in ce_dfs.copy().items()
# }

# # Unir dataframes em único > Precisa ser feito antes de rodar a rotina de criação da planilha de estações
# ce_frame = merge_station_dfs(ce_dfs.copy(), uf)

# # Corrigir problemas com datetime
# ce_frame = fix_datetime_df(ce_frame, "DATETIME")
# diag_bad_stations(ce_frame, "DATETIME")

# # Criar planilha final
# ce_dfs = build_inventory_rows(ce_frame.copy(), df_cod, uf, datetime_col='DATETIME', mode="columns")
# ce_dfs = assign_id_mma(ce_dfs)

# save_UF_estacoes_csv(ce_dfs, uf)


# # ##### b) Rio de Janeiro

# uf = "RJ" 

# # Conferir respostas do formulário 
# rj_forms = forms[forms["Unidade da Federação: "].str.contains(uf, case=False, na=False)]
# rj_forms.iloc[:, idxs].head()

# # Importar arquivos do estado
# base = Path.cwd().parent 
# df_dir = base / "data" / "DADOS_ESTACOES" 
# df_dir.mkdir(parents=True, exist_ok=True)
# rj_dir = df_dir / uf 
# os.listdir(rj_dir)

# ''' Neste caso, a inspeção das pastas indiciou que existiam arquivos .XLSX e .CSV, 
#     necessitando aplicar duas operações diferentes para leitura dos arquivos'''

# rj_exls = load_excels(rj_dir) # Está organizado para ler sempre a primeira planilha
# rj_csvs = load_csvs(rj_dir)


# ''' Neste caso, como são dois dicionários diferentes - uma para arquivos .XLSX e uma para arquivos .CSV,
#     foi necessário fazer um merge entre eles. Esse passo vai existir nessas condições'''

# rj_dfs = rj_csvs | rj_exls 


# # Encontrar colunas diferentes e iguais dentro dos dicts 
# summary, stats = summarize_columns(rj_dfs, normalize=True)

# # Colunas iguais em todos
# cols_comuns = summary.loc[summary.is_common, "col"].tolist()

# # Colunas diferentes em todos
# cols_diff = summary.loc[~ summary.is_common, "col"].tolist()

# # Estatísticas por DataFrame
# stats[["df","n_cols","n_common_present","n_common_missing","extras_count"]].head()

# # Limpar caracteres indesejados
# for name, d in rj_dfs.items(): clean_df_all_text(d, in_place=True)

# # Depois de rodar pela primeira vez e identificar os conflitos, posso escolher a base de dados prioritária para sobrepor informações
# priority = ["RJ_estacoes_enviada", "RJ_estacoes_nao_preenchidas", "RJ_estacoes"]

# rj_frame, conflicts = merge_by_id_multi(
#     rj_dfs.copy(),
#     id_cols=['ID_OEMA','POLUENTE'],
#     source_priority=priority,
#     drop_empty_strings=True,
# )

# # Lista de colunas alvo que já existem no df (na ordem desejada)
# cols = [
#     "ID_OEMA","ID_MMA","CIDADE","CD_MUN","CATEGORIA",
#     "FUNCIONAMENTO","PROPRIETARIO","PROP_ENTIDADE","OPERADOR","OP_ENTIDADE",
#     "LATITUDE","LONGITUDE","MOBILIDADE","REALOCACAO","MARCA","METODO","FINALIDADE",
#     "STATUS","CALIBRACAO","OBS_CALIBRACAO","MONITORAR","FONTE",
#     "OBS_GERAIS","DADOS_MONITORAMENTO","RECONHECIDA","REP_ESPACIAL_DECLARADA",
#     "REP_ESPACIAL"
# ]

# def make_field_map(cols,
#                    prefer_mode=("CIDADE",),     # PT-BR: colunas que preferem moda
#                    use_group_key=("ID_OEMA",)): # PT-BR: colunas que vêm da chave do grupo
#     fm = {}
#     for c in cols:
#         if c in use_group_key:
#             fm[c] = ("group_key",)
#         elif c in prefer_mode:
#             fm[c] = ("col", c, {"strategy": "mode"})
#         else:
#             fm[c] = ("col", c, {"strategy": "first_non_null"})
#     return fm

# field_map = make_field_map(cols)
# teste = build_inventory_flexible(
#     rj_frame.copy(),
#     uf,
#     df_cod,
#     group_col="ID_OEMA",
#     datetime_col=None,  # ou "DATETIME" se desejar calcular INICIO/FIM
#     mode= "rows",
#     field_map=field_map
# )

# save_UF_estacoes_csv(teste, uf)


# # ##### c) Paraíba

# uf = "PB" 

# # Conferir respostas do formulário 
# pb_forms = forms[forms["Unidade da Federação: "].str.contains(uf, case=False, na=False)]
# pb_forms.iloc[:, idxs].head()


# # Importar arquivos do estado
# base = Path.cwd().parent 
# df_dir = base / "data" / "DADOS_BRUTOS" 
# df_dir.mkdir(parents=True, exist_ok=True)

# pb_dir = df_dir / uf

# pb_dfs = load_txts(pb_dir)


# # NOTA: Informações fornecidas pela UF
# # 
# # Localização:
# # 
# # Estação 1: 7°2'4.75"S 34°50'34.73"W
# # 
# # Estação 2: 7°5'11.20"S 34°50'56.19"W
# # 
# # Estação 3: 7°2'50.65"S 34°57'23.56"W
# # 
# # Formato do arquivo de dados:[Data]T[Hora];[Serial];[NOME DO ÓRGÃO];[PTS];[PM10];[PM2.5];[PM1];[VOLTAGEM DA BATERIA];

# # Adicionar informações de cabeçalho 
# # Manual_map foi montado com base nas informações fornecidas pelo estado sobre os arquivos .txt
# manual_map = [
#     "DATETIME", "serial", "PROPRIETARIO", "PTS",
#     "MP10", "MP25", "MP1", "voltagem_bateria"
# ]

# pb_dfs = {name: df.set_axis(manual_map, axis=1) for name, df in pb_dfs.items()}

# # Unir dfs
# pb_frame = merge_station_dfs(pb_dfs.copy(), uf)

# # Limpar linhas de datetime para aceitar o formato
# pb_frame["DATETIME"] = (pb_frame["DATETIME"].astype(str).str.replace("T", " "))

# # Criar planilha final 
# pb_dfs = build_inventory_rows(pb_frame.copy(), df_cod, uf, datetime_col='DATETIME', mode="columns")
# pb_dfs["PROPRIETARIO"] = pb_frame["PROPRIETARIO"]

# # Adicionar colunas de latitude e longitude
# lat_map = {
#     "Estação 1": -7.034652778,
#     "Estação 2": -7.086444444,
#     "Estação 3": -7.047402778,
# }
# lon_map = {
#     "Estação 1": -34.842980556,
#     "Estação 2": -34.848941667,
#     "Estação 3": -34.956544444,
# }

# pb_dfs["LATITUDE"]  = pb_dfs["ID_OEMA"].map(lat_map)
# pb_dfs["LONGITUDE"] = pb_dfs["ID_OEMA"].map(lon_map)

# # Adicionar ID_MMA
# pb_dfs = assign_id_mma(pb_dfs)

# save_UF_estacoes_csv(pb_dfs, uf)


# # ##### d) Pernambuco

# uf = "PE" 

# # Conferir respostas do formulário 
# pe_forms = forms[forms["Unidade da Federação: "].str.contains(uf, case=False, na=False)]
# pe_forms.iloc[:, idxs].head()

# # Importar arquivos do estado
# base = Path.cwd().parent 
# df_dir = base / "data" / "DADOS_BRUTOS" 
# df_dir.mkdir(parents=True, exist_ok=True)

# pe_dir = df_dir / uf
# pe_dfs = load_excels(pe_dir,sheets=0)


# # Limpar dataframes pois contém informações extras nas linhas que não são utilizadas

# bad_rows = {
#     "Data Precent","Avg","STD","Num",
#     "Maximum","Max Date","Max Time",
#     "Minimum","Min Date","Min Time",
# }

# for name, df in pe_dfs.items():
#     first_col = df.columns[0]
#     mask = df[first_col].astype(str).str.strip().isin(bad_rows)
#     pe_dfs[name] = df.loc[~mask].copy()


# # Criar um dataframe por df dentro do dict
# pe_out = {} 

# for name, df in pe_dfs.copy().items():

#     # 1) find the header start row
#     idx = df.index[df.iloc[:, 0].astype(str).str.strip().eq("Date Time")]
#     start = int(idx[0]) if len(idx) else 0
#     sub = df.iloc[start:].reset_index(drop=True)

#     # df is your raw frame
#     station = df.iloc[1].ffill()          # row 1, forward-fill across columns
#     pollutant = df.iloc[2].astype(str)                # row 2

#     new_cols = ["DATETIME"] + [f"{st}|{po}" for st, po in zip(station[1:], pollutant[1:])]

#     out = sub.iloc[4:].copy()                       # data rows
#     out.columns = new_cols

#     pe_out[name] = out  


# # Reparar coluna datetime
# pe_frame = {
#     name: fix_datetime_df(d, col="DATETIME", keep_dt_col=False)
#     for name, d in pe_out.copy().items()
# }


# # Nota: Nesse caso, as planilhas de estações seguem ordem cronológica de datetime, então o merge precisa conferir se a estação já existia ou se foi criada em um novo ano.

# def coalesce_duplicate_columns(df: pd.DataFrame) -> pd.DataFrame:
#     """If the same column name appears multiple times, keep one and fill with first non-null."""
#     counts = Counter(df.columns)
#     dups = [c for c, n in counts.items() if n > 1]
#     for c in dups:
#         cols = [k for k in df.columns if k == c]
#         df[c] = df[cols].bfill(axis=1).iloc[:, 0]  # take first non-null left-to-right
#         df.drop(columns=cols[1:], inplace=True)
#     return df

# def merge_by_datetime_union(dfs_dict: dict, keep_source=True):
#     frames = []
#     for name, df in dfs_dict.items():
#         t = df.copy()
#         if keep_source:
#             t["__source"] = name  # year or filename

#         frames.append(t)

#     if not frames:
#         return pd.DataFrame()

#     out = pd.concat(frames, axis=0, ignore_index=True, sort=True)  # union of columns
#     out = coalesce_duplicate_columns(out)

#     # keep DATETIME first if present
#     if "DATETIME" in out.columns:
#         cols = ["DATETIME"] + [c for c in out.columns if c != "DATETIME"]
#         out = out[cols]

#     return out

# pe_all = merge_by_datetime_union(pe_frame.copy(), keep_source=True)

# # Criar planilha com formato adequado usando MELT

# def make_station_layout(df_or_dict, keep_source=True):
#   # accept dicts of DataFrames too
#     df = (pd.concat(df_or_dict.values(), ignore_index=True, sort=False)
#           if isinstance(df_or_dict, dict) else df_or_dict)

#     id_vars = ["DATETIME"]
#     if keep_source and "__source" in df.columns:
#         id_vars.append("__source")

#     long = df.melt(id_vars=id_vars, var_name="pair", value_name="VALUE")
#     long = long[long["pair"].astype(str).str.contains(r"\|", na=False)].copy()

#     # critical line: force string and split on literal "|"
#     long["pair"] = long["pair"].astype("string")
#     long[["ESTACAO", "POLLUTANT"]] = long["pair"].str.split(
#         pat="|", n=1, expand=True, regex=False
#     )
#     long.drop(columns=["pair"], inplace=True)
#     long["ESTACAO"] = long["ESTACAO"].str.strip()
#     long["POLLUTANT"] = long["POLLUTANT"].str.strip()

#     index_cols = ["DATETIME", "ESTACAO"] + (["__source"] if "__source" in id_vars else [])
#     wide = (
#         long.pivot_table(index=index_cols, columns="POLLUTANT", values="VALUE", aggfunc="first")
#             .reset_index()
#             .sort_values(["DATETIME", "ESTACAO"], kind="stable")
#     )
#     wide.columns.name = None
#     return wide


# pe_all = make_station_layout(pe_all, keep_source=True)  # keeps "NoData"

# # Nota: Nota-se que existem anos que não há medição por poluente, discriminado como NoData. Neste caso, não podemos contabilizar o poluente na estação, por isso deve-se aplicar um filtro.

# pe_station = build_inventory_rows(pe_all.copy(), df_cod, uf, datetime_col='DATETIME', mode="columns", drop_after_underscore=True)
# pe_station = assign_id_mma(pe_station)

# save_UF_estacoes_csv(pe_station, uf)


# # ##### e) Roraima

# uf = "RR" 

# # Conferir respostas do formulário 
# rr_forms = forms[forms["Unidade da Federação: "].str.contains("RR" , case=False, na=False)]
# rr_forms.iloc[:, idxs].head()

# # Importar arquivos do estado
# base = Path.cwd().parent 
# df_dir = base / "data" / "DADOS_BRUTOS" 
# df_dir.mkdir(parents=True, exist_ok=True)

# rr_dir = df_dir / uf
# os.listdir(rr_dir)

# rr_dfs = load_excels(rr_dir)


# # Nota: Como os 3 dataframes possuem formatos diferentes, é necessário tratá-los conforme suas particularidades


# # 1) Fazer alterações somente no df Medições (29) dentro de rr_dfs dict
# data = rr_dfs.copy()
# key = "Medições (29)"              # exact key in rr_dfs
# df = data[key].copy()

# # 1) find the header start row
# idx = df.index[df.iloc[:, 0].astype(str).str.strip().eq("Data e Hora")]
# start = int(idx[0]) if len(idx) else 0
# sub = df.iloc[start:].reset_index(drop=True)

# # df is your raw frame
# station = df.iloc[0].ffill()          # row 1, forward-fill across columns
# pollutant = df.iloc[3].astype(str)                # row 2

# new_cols = ["DATETIME"] + [f"{st}|{po}" for st, po in zip(station[1:], pollutant[1:])]

# out = sub.iloc[7:].copy()                       # data rows
# out.columns = new_cols
# out["__source"] = key

# data[key]=out


# # 2) Fazer alterações nos dfs "FAZENDA-ENEVA" e "FEMARH-ENEVA" dentro de rr_dfs dict
# manual_map = {"Data": "DATETIME"}

# for key in ["FAZENDA-ENEVA", "FEMARH-ENEVA"]:
#     val = data.get(key)
#     if val is None:
#         continue

#     if isinstance(val, dict):
#         # rename inside nested dict
#         new = {}
#         for name, obj in val.items():
#             if isinstance(obj, pd.DataFrame):
#                 new[name] = obj.rename(columns=manual_map)
#         data[key] = new

#     elif isinstance(val, pd.DataFrame):
#         data[key] = val.rename(columns=manual_map)

#     elif isinstance(val, pd.Series):
#         data[key] = val.rename("DATETIME") if val.name == "Data" else val

# # Reparar coluna datetime
# rr_frame = {
#     name: fix_datetime_df(d, col="DATETIME", keep_dt_col=False)
#     for name, d in data.copy().items()
# }


# # 1) Fazer alterações somente no df Medições (29) dentro de rr_dfs dict
# key = "Medições (29)"              
# df = rr_frame[key].copy()

# medicoes = make_station_layout(df, keep_source=True)

# #Criar planilha final 

# rr_station = build_inventory_rows(medicoes.copy(), df_cod, uf, datetime_col='DATETIME', mode="columns", drop_after_underscore=True)
# rr_station = assign_id_mma(rr_station)

# save_UF_estacoes_csv(rr_station, uf)


# # ##### f) Acre

# uf = "AC" 

# # Conferir respostas do formulário 
# ac_forms = forms[forms["Unidade da Federação: "].str.contains(uf , case=False, na=False)]
# ac_forms.iloc[:, idxs].head()

# # Importar arquivos do estado
# base = Path.cwd().parent 
# df_dir = base / "data" / "DADOS_BRUTOS" 
# df_dir.mkdir(parents=True, exist_ok=True)

# ac_dir = df_dir / uf
# os.listdir(ac_dir)

# # Como foram apresentadas particularidades nesse arquivo csv, foi necessário fazer uma alteração na função read,
# # para transformar manualmente o tipo de encoding

# def _read_csv(path, sep=None, decimal=None, encoding="cp1252", **kw):
#     head = path.read_bytes()[:4096]
#     txt  = head.decode(encoding or "utf-8", errors="ignore")
#     sep_guess = sep or (";" if txt.count(";") > txt.count(",") else ",")
#     dec_guess = decimal or ("," if re.search(r"\d+,\d+", txt) and txt.count(",") > txt.count(".") else ".")
#     enc_guess = encoding or ("utf-8-sig" if txt.startswith("\ufeff")
#                              else ("latin-1" if ("Ã" in txt or "�" in txt) else "utf-8"))
#     try:
#         return pd.read_csv(path, sep=sep_guess, decimal=dec_guess, encoding=enc_guess, engine="c", **kw)
#     except Exception:
#         return pd.read_csv(path, sep=None, engine="python", decimal=dec_guess, encoding=enc_guess, **kw)


# ac_csv = load_csvs(ac_dir)

# # Nota: Como há apenas 1 df - fazer a conversão direta para dataframe
# ac_long = pd.DataFrame(list(ac_csv.values())[0])


# # Como a planilha de dados possui diversas particularidades, precisa passar por uma limpeza

# df = ac_long.copy()

# # 1) find the header start row
# idx = df.index[(df.iloc[:, 0].isna()) & (df.notna().sum(axis=1) >= 3)]
# start = int(idx[0]) if len(idx) else 0
# sub = df.iloc[start:].reset_index(drop=True)

# # 2) build column names: row 1 has stations from col 1 onward
# stations = (
#     sub.iloc[1, 1:]           # row with station names, skip first col
#        .astype(str).str.strip()
#        .tolist()
# )

# new_cols = ["DATETIME"] + stations 

# ac_dfc = sub.iloc[2:].copy() 
# ac_dfc.columns = new_cols 
# ac_dfc.head()


# # Criar coluna de ESTACOES com os nomes dos headers
# station_cols = ['Ministério Público do Estado do Acre (SEDE) A',
#        'Ministério Público do Estado do Acre (SEDE) B', 'UFAC A', 'UFAC B',
#        'RB-BACKUP (Estação particular FB) A',
#        'RB-BACKUP (Estação particular FB) B', 'AcreBioClima - UFAC A',
#        'AcreBioClima - UFAC B', 'MPAC_BJR_01_promotoria A',
#        'MPAC_BJR_01_promotoria B', 'MPAC_SNG_01_promotoria A',
#        'MPAC_SNG_01_promotoria B', 'MPAC_PTA_01_Sec.infraestrutura A',
#        'MPAC_PTA_01_Sec.infraestrutura B', 'MPAC_ACL_01_promotoria A',
#        'MPAC_ACL_01_promotoria B', 'MPAC_CPX_01_qpm A', 'MPAC_CPX_01_qpm B',
#        'MPAC_XAP_02_promotoria A', 'MPAC_XAP_02_promotoria B',
#        'MPAC_ABR_01_promotoria A', 'MPAC_ABR_01_promotoria B',
#        'MPAC_ABR_02_SEMSA A', 'MPAC_ABR_02_SEMSA B',
#        'MPAC_PLC_01_promotoria A', 'MPAC_PLC_01_promotoria B',
#        'MPAC_SNM_01_ifac A', 'MPAC_SNM_01_ifac B', 'MPAC_SNM_02_promotoria A',
#        'MPAC_SNM_02_promotoria B', 'MPAC_MNU_01_promotoria A',
#        'MPAC_MNU_01_promotoria B', 'MPAC_FIJ_01_promotoria A',
#        'MPAC_FIJ_01_promotoria B', 'MPAC_TRC_02_ifac A', 'MPAC_TRC_02_ifac B',
#        'MPAC_JRD_01_prefeitura A', 'MPAC_JRD_01_prefeitura B',
#        'MPAC_RDA_01_prefeitura A', 'MPAC_RDA_01_prefeitura B',
#        'MPAC_CZS_02_ciosp A', 'MPAC_CZS_02_ciosp B', 'UFACFloresta A',
#        'UFACFloresta B', 'MPAC_MTH_01_semec A', 'MPAC_MTH_01_semec B',
#        'MPAC_EPL_02_escola.joao.pedro A', 'MPAC_EPL_02_escola.joao.pedro B',
#        'MPAC_BRL_02_radio fm 90.3 A', 'MPAC_BRL_02_radio fm 90.3 B',
#        'MPAC_BRL_01_promotoria A', 'MPAC_BRL_01_promotoria B',
#        'MPAC_SRP_01_prefeitura A', 'MPAC_SRP_01_prefeitura B',
#        'MPAC_PTW_01_prefeitura A', 'MPAC_PTW_01_prefeitura B']

# ac_full = ac_dfc.melt(
#     id_vars=['DATETIME'],   # keep these as is
#     value_vars=station_cols,                      # columns to unpivot
#     var_name='ESTACAO',                           # new col with station names
#     value_name='VALOR'                            # new col with numeric values
# )
# ac_full

# # Criar planilha final 
# ac_station = build_inventory_rows(ac_full.copy(), df_cod, uf, datetime_col='DATETIME', mode="rows", drop_after_underscore=True)

# # Adicionar coluna de CIDADE
# df = ac_long.copy()

# # 1) find the header start row
# idx = df.index[(df.iloc[:, 0].isna()) & (df.notna().sum(axis=1) >= 3)]
# start = int(idx[0]) if len(idx) else 0
# sub = df.iloc[start:].reset_index(drop=True)

# # From your cleaned 'sub' with two header rows:
# cities   = sub.iloc[0, 1:].astype(str).tolist()      
# stations = sub.iloc[1, 1:].astype(str).tolist()     

# # 1) station -> city
# station_to_city = dict(zip(stations, cities))        

# # 2) map onto your dataframe
# ac_station["CIDADE"] = ac_station["ID_OEMA"].map(station_to_city)

# # Adicionar colunas conhecidas
# cols = {
#     "POLUENTE": "MP25",
#     "CATEGORIA": "Indicativa",
#     "MARCA": "PurpleAir",
# }

# targets = list(cols)

# # normalize empty strings and whitespace to NA
# ac_station[targets] = ac_station[targets].replace(r"^\s*$", pd.NA, regex=True)

# # fill only where missing
# for c, v in cols.items():
#     ac_station.loc[ac_station[c].isna(), c] = v

# # Adicionar ID_MMA
# ac_station = assign_id_mma(ac_station)

# save_UF_estacoes_csv(ac_station, uf)


# # ##### g) Mato Grosso do Sul

# uf = "MS" 

# # Conferir respostas do formulário 
# ms_forms = forms[forms["Unidade da Federação: "].str.contains(uf, case=False, na=False)]
# ms_forms.iloc[:, idxs].head()

# # Importar arquivos do estado
# base = Path.cwd().parent 
# df_dir = base / "data" / "DADOS_BRUTOS" 
# df_dir.mkdir(parents=True, exist_ok=True)

# ms_dir = df_dir / uf
# oad_excels(ms_dir)


# # Criar coluna DATETIME com merge de colunas Data e HOra (que estão separadas)

# for name, df in ms_dfs.items():
#     df["DATETIME"] = pd.to_datetime(df["Data"] + " " + df["Hora"], format="%d/%m/%Y %H:%M")

# # Unir dfs dentro do dict pela coluna Datetime para seguir ordem cronológica
# ms_full = merge_by_datetime_union(ms_dfs, keep_source=True)

# # Renomear colunas
# manual_map = {"Estação":  "ESTACAO",
#               "Sigla":  "POLUENTE"
# }

# ms_full = ms_full.rename(columns=manual_map) 

# # Converter formado datetime
# ms_full = convert_column_to_datetime(ms_full, column_name="DATETIME", format="%d/%m/%Y %H:%M")

# # Criar planilha final
# ms_station = build_inventory_rows(ms_full.copy(), df_cod, uf, datetime_col='DATETIME', mode="rows")
# ms_station = assign_id_mma(ms_station)

# # Adicionar valores em colunas conhecidas 
# cols = {
#     "CATEGORIA": "Referencia",
# }

# targets = list(cols)
# # normalize empty strings and whitespace to NA
# ms_station[targets] = ms_station[targets].replace(r"^\s*$", pd.NA, regex=True)
# # fill only where missing
# for c, v in cols.items():
#     ms_station.loc[ms_station[c].isna(), c] = v


# save_UF_estacoes_csv(ms_station, uf)

#!/usr/bin/env python
# coding: utf-8

#-----------------------------Importação de pacotes ------------------------------------

import os, time, math, requests, pandas as pd
from datetime import datetime, timedelta, timezone
import pandas as pd
from collections import defaultdict
import re
import numpy as np
from pathlib import Path
import difflib
import unicodedata
from typing import Callable, Any, Optional
from functools import partial
from pandas.api.types import is_object_dtype, is_string_dtype
from collections import Counter
import unicodedata as ud


#----------------------------- Dicionários e listas ------------------------------------

mqar_campos = [
        "UF","ID_OEMA","CIDADE","ID_MMA","ID_MMA_COMPLETO","POLUENTE","COD_POLUENTE",
        "CD_MUN","COD_UF_IBGE","PROPRIETARIO","PROP_ENTIDADE","OPERADOR","OP_ENTIDADE",
        "LATITUDE","LONGITUDE","MOBILIDADE","CATEGORIA","FUNCIONAMENTO","METODO",
        "MARCA",'INICIO', 'FIM',"FINALIDADE","MONITORAR","FONTE","CALIBRACAO","REALOCACAO",
        "OBS_CALIBRACAO","DADOS_MONITORAMENTO","RECONHECIDA","OBS_GERAIS",
        "STATUS","CERTIFICACAO","REP_ESPACIAL_DECLARADA"
    ]

name_to_uf = {
    "acre":"AC","alagoas":"AL","amapa":"AP","amazonas":"AM","bahia":"BA","ceara":"CE",
    "distrito federal":"DF","espirito santo":"ES","goias":"GO","maranhao":"MA",
    "mato grosso":"MT","mato grosso do sul":"MS","minas gerais":"MG","para":"PA",
    "paraiba":"PB","parana":"PR","pernambuco":"PE","piaui":"PI","rio de janeiro":"RJ",
    "rio grande do norte":"RN","rio grande do sul":"RS","rondonia":"RO","roraima":"RR",
    "santa catarina":"SC","sao paulo":"SP","sergipe":"SE","tocantins":"TO"
}


UF_TO_IBGE = {
    "AC":12,"AL":27,"AP":16,"AM":13,"BA":29,"CE":23,"DF":53,"ES":32,"GO":52,"MA":21,
    "MT":51,"MS":50,"MG":31,"PA":15,"PB":25,"PR":41,"PE":26,"PI":22,"RJ":33,"RN":24,
    "RS":43,"RO":11,"RR":14,"SC":42,"SP":35,"SE":28,"TO":17
}

def sigla_to_ibge(uf): return UF_TO_IBGE[uf.upper()]


# Importar planilha com os códigos de poluentes
base = Path.cwd().parent  
out_dir = base / "data" / "dicionarios" 
out_dir.mkdir(parents=True, exist_ok=True)

df_cod = pd.read_csv(out_dir / 'CODIGO_POLUENTES.csv')


# Importar planilha com as respostas do formulário das UFs
base = Path.cwd().parent  
fr_dir = base / "data" 
fr_dir.mkdir(parents=True, exist_ok=True)

forms = pd.read_csv(fr_dir / '2025_Formulário_Coleta_Respostas_UFs.csv')

#Indice das colunas com respostas sobre rede de monitoramento
# for i, c in enumerate(forms.columns):
#    print(f"[{i}] {c}")

idxs = [6,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22] 


#----------------------------- Ler e abrir arquivos CSV ------------------------------------


def _read_csv(path, sep=None, decimal=None, encoding=None, **kw):
    head = path.read_bytes()[:4096]
    txt  = head.decode(encoding or "utf-8", errors="ignore")
    sep_guess = sep or (";" if txt.count(";") > txt.count(",") else ",")
    dec_guess = decimal or ("," if re.search(r"\d+,\d+", txt) and txt.count(",") > txt.count(".") else ".")
    enc_guess = encoding or ("utf-8-sig" if txt.startswith("\ufeff")
                             else ("latin-1" if ("Ã" in txt or "�" in txt) else "utf-8"))
    try:
        return pd.read_csv(path, sep=sep_guess, decimal=dec_guess, encoding=enc_guess, engine="c", **kw)
    except Exception:
        return pd.read_csv(path, sep=None, engine="python", decimal=dec_guess, encoding=enc_guess, **kw)

def load_csvs(dir_path, prefix=None, recursive=False, limit=None, **read_csv_kwargs):
    pattern = "**/*.csv" if recursive else "*.csv"
    files = sorted(dir_path.glob(pattern))
    if prefix:
        p = prefix.upper()
        files = [f for f in files if f.name.upper().startswith(p)]
    if limit:
        files = files[:int(limit)]
    dfs = {}
    for f in files:
        df = _read_csv(f, **read_csv_kwargs)
        key = f.stem
        # avoid key clashes
        if key in dfs:
            key = f"{f.stem}__{len(dfs)}"
        dfs[key] = df
        print(f"Loaded {f.name}: {df.shape}")
    return dfs

#----------------------------- Ler e abrir arquivos TXT ------------------------------------

def _read_txt(path, sep=None, decimal=None, encoding=None, header=None, **kw):
    head = path.read_bytes()[:4096]
    txt  = head.decode(encoding or "utf-8", errors="ignore")

    enc_guess = encoding or ("utf-8-sig" if txt.startswith("\ufeff")
                             else ("latin-1" if ("Ã" in txt or "�" in txt) else "utf-8"))
    dec_guess = decimal or ("," if re.search(r"\d+,\d+", txt) and txt.count(",") > txt.count(".") else ".")

    if sep is not None:
        sep_guess = sep
    else:
        candidates = ["\t", ";", "|", ","]
        counts = {d: txt.count(d) for d in candidates}
        sep_guess = max(counts, key=counts.get) if max(counts.values()) >= 2 else None

    try:
        if sep_guess is None:
            return pd.read_csv(path, sep=None, engine="python",
                               decimal=dec_guess, encoding=enc_guess,
                               header=header, **kw)
        else:
            return pd.read_csv(path, sep=sep_guess, engine="c",
                               decimal=dec_guess, encoding=enc_guess,
                               header=header, **kw)
    except Exception:
        full = path.read_text(encoding=enc_guess, errors="ignore")
        return pd.DataFrame({"text": full.splitlines()})

def load_txts(dir_path, prefix=None, recursive=False, limit=None, **read_txt_kwargs):
    pattern = "**/*.txt" if recursive else "*.txt"
    files = sorted(dir_path.glob(pattern))
    if prefix:
        p = prefix.upper()
        files = [f for f in files if f.name.upper().startswith(p)]
    if limit:
        files = files[:int(limit)]
    dfs = {}
    for f in files:
        df = _read_txt(f, **read_txt_kwargs)
        key = f.stem
        if key in dfs:
            key = f"{f.stem}__{len(dfs)}"
        dfs[key] = df
        print(f"Loaded {f.name}: {df.shape}")
    return dfs

#----------------------------- Ler e abrir arquivos XLSX ------------------------------------

EXCEL_EXTS = {".xlsx", ".xls", ".xlsm", ".xltx", ".xltm"}

def _excel_engine(ext: str) -> str | None:
    """
    Retorna o engine recomendado para cada extensão.
    .xlsx, .xlsm, .xltx, .xltm -> openpyxl
    .xls -> xlrd (necessita instalar xlrd)
    """
    ext = ext.lower()
    if ext in {".xlsx", ".xlsm", ".xltx", ".xltm"}:
        return "openpyxl"
    if ext == ".xls":
        return "xlrd"  
    return None


def load_excels(dir_path, sheets=0, prefix=None, recursive=False, limit=None, **read_excel_kwargs):
    """
    Lê arquivos Excel de uma pasta e retorna um dicionário {chave: DataFrame}.

    Parâmetros:
      - dir_path: str | Path
        Caminho da pasta onde estão os arquivos.
      - sheets: int | str | list | "all"
        Qual planilha carregar.
        0 carrega a primeira planilha. Pode ser índice (int) ou nome (str).
        Lista para múltiplas planilhas. "all" para todas as planilhas.
      - prefix: str | None
        Se definido, carrega apenas arquivos cujo nome começa com este prefixo.
      - recursive: bool
        Se True, busca nas subpastas.
      - limit: int | None
        Limita a quantidade de arquivos lidos.
      - **read_excel_kwargs:
        Parâmetros extras repassados na função

    Retorno:
      - Dicionário com chave nome base do arquivo
    """
    dir_path = Path(dir_path)
    files = []
    if recursive:
        for ext in EXCEL_EXTS:
            files += list(dir_path.rglob(f"*{ext}"))
    else:
        for ext in EXCEL_EXTS:
            files += list(dir_path.glob(f"*{ext}"))
    files = sorted(files)

    if prefix:
        p = prefix.upper()
        files = [f for f in files if f.name.upper().startswith(p)]
    if limit:
        files = files[:int(limit)]

    dfs = {}
    for f in files:
        eng = _excel_engine(f.suffix)
        try:
            with pd.ExcelFile(f, engine=eng) as xls:
                if sheets == "all":
                    wanted = xls.sheet_names
                elif isinstance(sheets, (list, tuple)):
                    wanted = sheets
                else:
                    wanted = [sheets]

                for s in wanted:
                    df = pd.read_excel(xls, sheet_name=s, **read_excel_kwargs)
                    if sheets == "all" or isinstance(sheets, (list, tuple)):
                        sheet_label = s if isinstance(s, str) else xls.sheet_names[s]
                        key = f"{f.stem}__{sheet_label}"
                    else:
                        key = f.stem
                    if key in dfs:
                        i = 1
                        new_key = f"{key}__{i}"
                        while new_key in dfs:
                            i += 1
                            new_key = f"{key}__{i}"
                        key = new_key

                    dfs[key] = df
                    print(f"Loaded {f.name} [sheet {s}]: {df.shape}")
        except Exception as e:
            print(f"Skip {f.name} due to read error: {e}")
            continue
    return dfs


#----------------------------- Remover e substituir caracteres ------------------------------------

CLEAN_TABLE = {
    ord("ç"): "c",
    ord("Ç"): "C",
    ord("´"): None,
    ord("~"): None,
    ord("ˆ"): None,
    ord("°"): None,
    ord("`"): None,
    0x0302: None,  # combining ^
}

def clean_text_full(s: object) -> object:
    if pd.isna(s):
        return s
    t = str(s)
    # sua tabela primeiro
    t = t.translate(CLEAN_TABLE)
    # remover acentos de letras precompostas (ex.: ã, á, í)
    t = unicodedata.normalize("NFKD", t)
    t = "".join(ch for ch in t if unicodedata.category(ch) != "Mn")
    return t

def clean_df_all_text(df: pd.DataFrame, cols=None, in_place=False) -> pd.DataFrame:
    out = df if in_place else df.copy()
    if cols is None:
        cols = [c for c in out.columns
                if is_object_dtype(out[c].dtype) or is_string_dtype(out[c].dtype)
                   or isinstance(out[c].dtype, pd.CategoricalDtype)]
    for c in cols:
        s = out[c]
        was_cat = isinstance(s.dtype, pd.CategoricalDtype)
        s2 = s.astype("string").map(lambda v: clean_text_full(v) if pd.notna(v) else v)
        out[c] = s2.astype("category") if was_cat else s2
    return out


#----------------------------- Transformar coluna Datetime ------------------------------------

def convert_column_to_datetime(df, column_name, format=None):
    out = df.copy()

    if (out.index.name or "").upper() == column_name.upper():
        if column_name in out.columns:
            out.reset_index(drop=True, inplace=True)
        else:
            out.reset_index(inplace=True)

    if column_name not in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out.index):
            out[column_name] = out.index
            if not keep_index:
                out.reset_index(drop=True, inplace=True)
        else:
            raise ValueError(f"Column or datetime index '{column_name}' not found.")

    out[column_name] = pd.to_datetime(out[column_name], format=format,  errors="coerce")

    return out


#----------------------------- Inspecionar colunas repetidas no mesmo dicionário ------------------------------------

def _flatten_columns(df):
    """
    Achata colunas MultiIndex em strings simples.
    Exemplo: ("A","B") vira "A | B".
    """
    cols = df.columns
    if isinstance(cols, pd.MultiIndex):
        return [" | ".join([str(x) for x in tup if pd.notna(x)]) for tup in cols]
    return [str(c) for c in cols]


def _normalize(names, lower=True, strip=True):
    """
    Normaliza nomes de colunas para comparação justa.
    - lower: converte para minúsculas
    - strip: remove espaços extras
    """
    out = []
    for n in names:
        s = str(n)
        if strip:
            s = s.strip()
        if lower:
            s = s.lower()
        out.append(s)
    return out


def summarize_columns(dfs: dict, normalize=True):
    """
    Resume colunas presentes em um dicionário {nome_df: DataFrame}.

    Parâmetros
    - dfs: dict[str, pd.DataFrame]
      Dicionário onde a chave é o nome e o valor é um DataFrame.
    - normalize: bool
      Se True, compara usando nomes normalizados (minúsculas e trim).

    Retorno
    - summary_df: pd.DataFrame
      Tabela com uma linha por coluna distinta:
        col            nome da coluna considerada na comparação
        n_present      em quantos DataFrames ela aparece
        n_missing      em quantos não aparece
        is_common      True se aparece em todos
        is_unique      True se aparece em apenas um
        present_in     lista de DataFrames onde aparece
        missing_in     lista de DataFrames onde não aparece
        examples       exemplos de rótulos originais vistos para esta coluna
    - per_df_stats: pd.DataFrame
      Uma linha por DataFrame com:
        n_cols                 quantidade de colunas
        n_common_present       quantas colunas comuns ele possui
        n_common_missing       quantas colunas comuns faltam nele
        extras_count           colunas que só existem em alguns e estão nele
        extras                 lista dessas colunas extras
    """
    # 1) coletar nomes por df
    name_to_cols = {}
    name_to_rawmap = {}
    for name, df in dfs.items():
        cols_raw = _flatten_columns(df)
        cols_cmp = _normalize(cols_raw) if normalize else cols_raw
        name_to_cols[name] = set(cols_cmp)
        # mapeia versão normalizada para exemplos originais
        rawmap = {}
        for raw, cmp in zip(cols_raw, cols_cmp):
            rawmap.setdefault(cmp, set()).add(raw)
        name_to_rawmap[name] = rawmap

    all_cols = set().union(*name_to_cols.values()) if name_to_cols else set()
    df_names = list(name_to_cols.keys())
    n_dfs = len(df_names)

    # 2) frequências por coluna
    records = []
    for col in sorted(all_cols):
        present_in = [n for n in df_names if col in name_to_cols[n]]
        missing_in = [n for n in df_names if col not in name_to_cols[n]]
        # exemplos de rótulos originais
        examples = sorted(set().union(*[name_to_rawmap[n].get(col, set()) for n in df_names]))
        records.append({
            "col": col,
            "n_present": len(present_in),
            "n_missing": n_dfs - len(present_in),
            "is_common": len(present_in) == n_dfs,
            "is_unique": len(present_in) == 1,
            "present_in": present_in,
            "missing_in": missing_in,
            "examples": examples[:5],  # mostra até 5 exemplos
        })
    summary_df = pd.DataFrame(records).sort_values(
        ["is_common", "n_present", "col"], ascending=[False, False, True]
    ).reset_index(drop=True)

    # 3) colunas comuns e extras
    common_set = set(summary_df.loc[summary_df["is_common"], "col"])
    per_df_rows = []
    for name in df_names:
        cols_set = name_to_cols[name]
        n_cols = len(cols_set)
        n_common_present = len(cols_set & common_set)
        n_common_missing = len(common_set - cols_set)
        extras = sorted(c for c in cols_set if c not in common_set)
        per_df_rows.append({
            "df": name,
            "n_cols": n_cols,
            "n_common_present": n_common_present,
            "n_common_missing": n_common_missing,
            "extras_count": len(extras),
            "extras": extras
        })
    per_df_stats = pd.DataFrame(per_df_rows).sort_values("df").reset_index(drop=True)

    return summary_df, per_df_stats


#----------------------------- Renomear colunas ------------------------------------

# manual_map = {"fecha":  "DATETIME",
#              "Date":  "DATETIME",
#              "Fecha":  "DATETIME",
#}

#----------------------------- Selecionar estações unicas no mesmo df ------------------------------------

# Nota: Quando há junção de mais de uma base de dados de fontes diferentes, utilizar função para manter estações não repetidas e garantir que a maioria das colunas com dados seja mantida.

def merge_by_id_multi(
    dfs_dict: dict,
    id_cols,              # pode ser "ID_OEMA" ou ["ID_OEMA","UF"]
    source_col="__source",
    source_priority: list[str] | None = None,
    drop_empty_strings: bool = True,
):
    """
    Une vários DataFrames (em um dict) e mantém 1 linha por chave composta.

    Parâmetros:
      - dfs_dict: dict[str, pd.DataFrame]  dicionário nome->DataFrame.
      - id_cols: str | list/tuple          coluna(s) que formam a chave. Ex.: "ID_OEMA" ou ["ID_OEMA","UF"].
      - source_col: str                    coluna auxiliar com o nome da fonte.
      - source_priority: list[str] | None  prioridade entre fontes para resolver conflitos.
      - drop_empty_strings: bool           converte strings vazias em NaN antes de mesclar.

    Retorna:
      - df_merged: DataFrame final com 1 linha por chave.
      - df_conflicts: DataFrame listando conflitos por coluna e chave.
    """
    if isinstance(id_cols, str):
        id_cols = (id_cols,)
    id_set = set(id_cols)

    # 1) concatena e marca fonte
    frames = []
    for name, df in dfs_dict.items():
        if isinstance(df, pd.DataFrame):
            tmp = df.copy()
            tmp[source_col] = name
            frames.append(tmp)
    if not frames:
        return pd.DataFrame(), pd.DataFrame()
    big = pd.concat(frames, ignore_index=True, sort=False)

    # garante que todas as colunas de chave existam
    for c in id_cols:
        if c not in big.columns:
            big[c] = pd.NA

    # 2) normalização leve
    if drop_empty_strings:
        for c in big.columns:
            if big[c].dtype.kind in "OUS":
                big[c] = big[c].astype("string").str.strip().replace({"": pd.NA})

    def pick_value(series, sources):
        mask = series.notna()
        vals = series[mask].astype(object).tolist()
        srcs = sources[mask].astype(str).tolist()
        if not vals:
            return pd.NA, None, []
        if len(set(map(str, vals))) == 1:
            return vals[0], srcs[0], list(dict.fromkeys(srcs))
        if source_priority:
            pri = {s: i for i, s in enumerate(source_priority)}
            best = min(range(len(srcs)), key=lambda i: pri.get(srcs[i], 10**9))
            return vals[best], srcs[best], list(dict.fromkeys(srcs))
        return vals[0], srcs[0], list(dict.fromkeys(srcs))

    # 3) reduz por chave composta
    data_cols = [c for c in big.columns if c not in id_set | {source_col}]
    rows, conflicts = [], []
    for key_vals, g in big.groupby(list(id_cols), dropna=True, sort=False):
        if len(id_cols) == 1:
            key_vals = (key_vals,)
        out = {c: v for c, v in zip(id_cols, key_vals)}

        for c in data_cols:
            s = g[c] if c in g.columns else pd.Series([pd.NA] * len(g))
            winner, winner_src, all_srcs = pick_value(s, g[source_col])
            out[c] = winner

            non_null = [str(v) for v in s.dropna().tolist()]
            if len(set(non_null)) > 1:
                confl = {col: val for col, val in zip(id_cols, key_vals)}
                confl.update({
                    "col": c,
                    "values": sorted(set(non_null)),
                    "sources": all_srcs,
                    "chosen": str(winner),
                    "chosen_source": winner_src,
                })
                conflicts.append(confl)

        rows.append(out)

    df_merged = pd.DataFrame(rows)
    ordered = list(id_cols) + [c for c in df_merged.columns if c not in id_set]
    df_merged = df_merged[ordered]

    df_conflicts = pd.DataFrame(conflicts)
    return df_merged, df_conflicts


#----------------------------- Unir estações que estão dentro do mesmo dicionário ------------------------------------

# Nota: Maneira mais simplificada de unir diferentes dfs dentro de um dict, quando sabemos que não existem linhas duplicadas ou informações repetidas. Quando há dúvida, rodar a função anterior.

def merge_station_dfs(dfs_dict, uf):
    frames = []
    for station_name, d in dfs_dict.items():
        df = d.copy()

        # station
        df["ESTACAO"] = station_name # LEMBRAR DE DAR UM DROP
        frames.append(df)

    if not frames:
        raise ValueError("No data frames to merge.")
    return pd.concat(frames, ignore_index=True, sort=False)


#----------------------------- Corrigir e identificar problemas com Datetime ------------------------------------

TARGET_FMT = "%d/%m/%Y %H:%M"

def fix_datetime_df(df, col, keep_dt_col=True):
    out = df.copy()
    out.rename(columns=lambda c: str(c).strip().lstrip("\ufeff"), inplace=True)

    s = (out[col].astype(str)
                  .str.strip()
                  .str.replace("\xa0", " ", regex=False)   # nbsp
                  .str.replace("T", " ", regex=False)
                  .str.replace("Z", "", regex=False))

    dt = pd.Series(pd.NaT, index=out.index, dtype="datetime64[ns]")

    # put your actual input formats first
    tries = [
        ("%H:%M %m/%d/%Y", False),       # 02:00 1/1/2019
        ("%H:%M:%S %m/%d/%Y", False),    # 02:00:00 1/1/2019
        ("%d/%m/%Y %H:%M", True),
        ("%d/%m/%Y %H:%M:%S", True),
        ("%Y-%m-%d %H:%M", False),
        ("%Y-%m-%d %H:%M:%S", False),
        ("%d-%b-%Y %H:%M", True),
        ("%d-%b-%Y %H:%M:%S", True),
    ]

    for fmt, dayfirst in tries:
        m = dt.isna()
        if not m.any():
            break
        dt.loc[m] = pd.to_datetime(s[m], format=fmt, errors="coerce", dayfirst=dayfirst)

    # final fallback
    m = dt.isna()
    if m.any():
        try:
            dt.loc[m] = pd.to_datetime(s[m], format="mixed", dayfirst=True, errors="coerce")
        except TypeError:
            dt.loc[m] = pd.to_datetime(s[m], dayfirst=True, errors="coerce")

    if keep_dt_col:
        out[f"{col}_DT"] = dt

    out[col] = np.where(dt.notna(), dt.dt.strftime(TARGET_FMT), np.nan)
    return out


# Diagnóstico das colunas ou linhas com problema
def diag_bad_stations(df_all, col="DATETIME", top=5):
    out = []
    for st, g in df_all.groupby("ESTACAO"):
        rate = g[col].notna().mean()
        if rate < 0.99:
            bad = g.loc[g[col].isna(), col].astype(str).head(top).tolist()
            out.append((st, rate, bad))
    for st, rate, examples in out:
        print(f"{st}: parsed {rate:.1%}  examples not parsed -> {examples}")


#----------------------------- Criar colunas de INICIO e FIM das medições ------------------------------------

def station_year_bounds(g: pd.DataFrame, datetime_col: Optional[str]):
    if not datetime_col or datetime_col not in g.columns:
        return pd.NA, pd.NA
    s = pd.to_datetime(g[datetime_col], dayfirst=True)
    if s.notna().any():
        return int(s.min().year), int(s.max().year)
    return pd.NA, pd.NA

#----------------------------- Criar coluna padronizada de poluentes ------------------------------------

# Função para mapear e converter apenas os nomes dos poluentes quando no CABEÇALHO DAS COLUNAS
def id_pol(df, df_cod, column_name, drop_after_underscore=True):
    nomes = []
    for col in df.columns:
        if col == column_name:
            continue  

        # limpa parênteses -> "CO(µg/m³)" -> "CO"
        new_col = re.sub(r"\(.*?\)", "", col).strip()
        # keep only left side before first underscore if you want
        if drop_after_underscore and "_" in new_col:
            new_col = new_col.split("_", 1)[0]

        # verifica no dicionário
        linha = df_cod[df_cod["POLUENTE"].str.strip() == new_col]
        if not linha.empty:
            nomes.append(linha["NOME_PASTA"].values[0])

    return ",".join(sorted(set(nomes)))  # retorna só os nomes únicos


# Função para mapear e converter apenas os nomes dos poluentes quando NAS LINHAS DOS DFS
def id_pol_from_rows(
    df,
    df_cod,
    cols_cand=("POLUENTE","POLUENTES","Poluente","pollutant","nome_poluente","NomePoluente"),
    find_all=True,
    col_sinonimos=None,
    sep=r"[;,/|]+",
):
    """
    Identifica poluentes quando os nomes estão nas LINHAS e retorna nomes únicos
    padronizados conforme df_cod['NOME_PASTA'], separados por vírgula.

    Parâmetros:
      - df: DataFrame de entrada com as respostas.
      - df_cod: DataFrame de dicionário com colunas obrigatórias:
          'POLUENTE'  nome canônico
          'NOME_PASTA' nome padronizado desejado
        Opcional:
          col_sinonimos  nome de coluna em df_cod com sinônimos separados por '|'
      - cols_cand: possíveis nomes de coluna em df que contêm o texto dos poluentes.
      - find_all: se True, quando não encontrar cols_cand, varre todas as colunas de texto.
      - sep: regex para dividir listas no texto, ex "CO, NO2; PM10".

    Retorno:
      - str com nomes únicos padronizados, separados por vírgula.
    """

    # Normalização simples de rótulos para comparação
    def _erase(s: str) -> str:
        return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))

    def _norm(s: str) -> str:
        s = str(s)
        s = re.sub(r"\(.*?\)|\[.*?\]", "", s)  # remove unidades entre () ou []
        s = s.replace("µ", "u")
        s = _erase(s)
        s = re.sub(r"\s+", " ", s).strip().lower()
        return s

    # Mapa normalizado -> NOME_PASTA, incluindo sinônimos se houver
    cod_map = {}
    for _, row in df_cod.iterrows():
        cod_map[_norm(row["POLUENTE"])] = row["NOME_PASTA"]
        if col_sinonimos and col_sinonimos in df_cod.columns and pd.notna(row[col_sinonimos]):
            for alt in str(row[col_sinonimos]).split("|"):
                alt = alt.strip()
                if alt:
                    cod_map[_norm(alt)] = row["NOME_PASTA"]

    # Coleta de text candidatos
    text = []
    col_pol = next((c for c in df.columns if str(c).strip() in cols_cand), None)
    if col_pol is not None:
        text = df[col_pol].dropna().astype(str).tolist()
    elif find_all:
        for c in df.columns:
            if df[c].dtype.kind in "OUS":
                text += df[c].dropna().astype(str).tolist()

    if not text:
        return ""

    # Quebra por sep e mapeia para nomes padronizados
    seen = set()
    out = []
    sep_re = re.compile(sep)
    for t in text:
        partes = [p.strip() for p in sep_re.split(t)] if sep_re.search(t) else [t.strip()]
        for p in partes:
            if not p:
                continue
            k = _norm(p)
            nome = cod_map.get(k)
            if nome and nome not in seen:
                seen.add(nome)
                out.append(nome)

    return ",".join(sorted(out))

#----------------------------- Criar planilha final com dados da estações já processados (quando informações estão nas LINHAS) ------------------------------------

def build_inventory_rows(df_all,
                         df_cod,
                         uf,
                         datetime_col: str | None=None,
                         drop_after_underscore=True,
                         mode: str = "rows"):
    """
    Monta linhas do inventário por estação.

    Parâmetros:
      - df_all: DataFrame já unido, com colunas 'ESTACAO' e opcionalmente a coluna de data-hora.
      - df_cod: dicionário de poluentes com colunas 'POLUENTE' e 'NOME_PASTA' (e opcional 'SINONIMOS').
      - uf: sigla UF, ex. 'RJ'.
      - datetime_col: nome da coluna de data-hora ou None (quando não há).
      - mode:
          'columns' -> detectar poluentes no CABEÇALHO (usa sua função id_pol(...))
          'rows'    -> detectar poluentes nas LINHAS (usa id_pol_from_rows(...))

    Retorno:
      - DataFrame com uma linha por estação, incluindo POLUENTE, INICIO e FIM.
    """ 
    rows = []
    for station, g in df_all.groupby("ESTACAO", sort=True):
        inicio, fim = station_year_bounds(g, datetime_col)

        if mode == "columns":
            # usa função que lê do cabeçalho; passar um nome para ignorar
            col_to_ignore = datetime_col 
            pols = id_pol(g, df_cod, column_name=col_to_ignore, drop_after_underscore=True)
        else:
            # lê poluentes a partir das LINHAS; NÃO passe datetime_col aqui
            pols = id_pol_from_rows(g, df_cod)

        rows.append({
            "UF": uf,
            "ID_OEMA": station,
            "CIDADE": "",
            "ID_MMA": "",  # será preenchido depois
            "ID_MMA_COMPLETO": "",
            "POLUENTE": pols,
            "COD_POLUENTE": "",  # deixamos vazio
            "CD_MUN": "",
            "COD_UF_IBGE": sigla_to_ibge(uf),
            "PROPRIETARIO": "",
            "PROP_ENTIDADE": "",
            "OPERADOR": "",
            "OP_ENTIDADE": "",
            "LATITUDE": "",
            "LONGITUDE": "",
            "MOBILIDADE": "",
            "CATEGORIA": "",
            "FUNCIONAMENTO": "",
            "METODO": "",
            "MARCA": "",
            "FINALIDADE": "",
            "MONITORAR": "",
            "FONTE": "",
            "CALIBRACAO": "",
            "REALOCACAO": "",
            "OBS_CALIBRACAO": "",
            "INICIO": inicio,
            "FIM": fim,
            "DADOS_MONITORAMENTO": "",
            "RECONHECIDA": "",
            "OBS_GERAIS": "",
            "CERTIFICACAO": "",
            "STATUS": "",
            "REP_ESPACIAL_DECLARADA": ""
        })

    return pd.DataFrame(rows)


#----------------------------- Criar planilha final com dados da estações já processados (quando informações estão nas COLUNAS) ------------------------------------

def pick_group_value(s: pd.Series, strategy="first_non_null", sep=" | "):
    """
    Escolhe um valor representativo dentro de um grupo.
    - s: Série com valores do grupo
    - strategy: "first_non_null" | "mode" | "concat_unique"
    - sep: separador para concatenação
    """
    ss = s.dropna()
    if ss.empty:
        return None
    if strategy == "mode":
        m = ss.mode()
        return m.iloc[0] if not m.empty else ss.iloc[0]
    if strategy == "concat_unique":
        vals = pd.unique(ss.astype(str).str.strip())
        return sep.join([v for v in vals if v])
    return ss.iloc[0]  # padrão


def build_inventory_flexible(
    df_all: pd.DataFrame,
    uf: str,
    df_cod,                         # usado pelas funções de poluentes
    group_col: str = "ID_OEMA",
    datetime_col: Optional[str] = None,
    mode: str = "rows",
    field_map: Optional[dict[str, Any]] = None,
    drop_after_underscore=True
) -> pd.DataFrame:
    """
    PT-BR:
      - df_all: DataFrame com ao menos group_col.
      - uf: sigla da UF.
      - df_cod: dicionário de poluentes.
      - group_col: chave do agrupamento.
      - datetime_col: coluna de data-hora para INICIO/FIM (opcional).
      - mode: "rows" usa id_pol_from_rows, "columns" usa id_pol.
      - field_map: regras extras, ex. {"CIDADE": ("col","CIDADE",{"strategy":"mode"})}
    """
    if group_col not in df_all.columns:
        raise ValueError(f"Coluna de agrupamento '{group_col}' não existe.")

    # funções de poluentes por modo
    if mode == "columns":
        pol_func = lambda g: id_pol(g, df_cod, column_name=datetime_col, drop_after_underscore=True)
    else:
        pol_func = lambda g: id_pol_from_rows(g, df_cod)

    # regras base: valores por grupo usando ("func", ...)
    base_rules = {
        "UF": uf,
        "ID_OEMA": ("group_key",),
        "POLUENTE": ("func", pol_func),
        "COD_UF_IBGE": sigla_to_ibge(uf),
        "INICIO": ("func", lambda g: station_year_bounds(g, datetime_col)[0]) if datetime_col else "",
        "FIM":    ("func", lambda g: station_year_bounds(g, datetime_col)[1]) if datetime_col else "",
        "CIDADE": "",
        "ID_MMA": "",
        "ID_MMA_COMPLETO": "",
        "COD_POLUENTE": "",
        "CD_MUN": "",
        "PROPRIETARIO": "",
        "PROP_ENTIDADE": "",
        "OPERADOR": "",
        "OP_ENTIDADE": "",
        "LATITUDE": "",
        "LONGITUDE": "",
        "MOBILIDADE": "",
        "CATEGORIA": "",
        "FUNCIONAMENTO": "",
        "METODO": "",
        "MARCA": "",
        "FINALIDADE": "",
        "MONITORAR": "",
        "FONTE": "",
        "CALIBRACAO": "",
        "REALOCACAO": "",
        "OBS_CALIBRACAO": "",
        "DADOS_MONITORAMENTO": "",
        "RECONHECIDA": "",
        "OBS_GERAIS": "",
        "CERTIFICACAO": "",
        "STATUS": "",
        "REP_ESPACIAL_DECLARADA": "",
    }

    rules = {**base_rules, **(field_map or {})}

    rows = []
    for group_key, g in df_all.groupby(group_col, sort=True):
        out = {}
        for field, rule in rules.items():
            # literal
            if not isinstance(rule, tuple):
                out[field] = rule
                continue

            kind = rule[0]
            if kind == "group_key":
                out[field] = group_key
            elif kind == "col":
                colname = rule[1]
                opts = rule[2] if len(rule) > 2 and isinstance(rule[2], dict) else {}
                out[field] = pick_group_value(g[colname], **opts) if colname in g.columns else None
            elif kind == "func":
                func = rule[1] if len(rule) > 1 else None
                out[field] = func(g) if callable(func) else None
            else:
                out[field] = None

        rows.append(out)

    return pd.DataFrame(rows)


#----------------------------- Criar ID_MMA ------------------------------------

# NOTA: Sempre antes de criar ID_MMA COMPLETO na planilha final dos DADOS ESTAÇÕES, precisa garantir que as estações estejam com os campos início e fim preenchidos, para criar a sequência dos códigos - que depende do período de funcionamento

def _ascii_lower(s: str) -> str:
    s = str(s)
    s = ud.normalize("NFKD", s)
    s = "".join(ch for ch in s if not ud.combining(ch))
    return s.lower()

def assign_id_mma(df, uf_col="UF", date_col="INICIO"):
    out = df.copy()
    name_key = out["ID_OEMA"].astype(str).map(_ascii_lower)

    out = (
        out.assign(_name_key=name_key)
           .sort_values([uf_col, date_col, "_name_key"], kind="mergesort", na_position="last")
           .drop(columns="_name_key")
           .reset_index(drop=True)
    )

    seq = out.groupby(uf_col).cumcount().add(1).astype(str).str.zfill(4)
    out["ID_MMA"] = out[uf_col] + seq
    out["ID_MMA_COMPLETO"] = out["ID_MMA"]
    return out


#----------------------------- Conferir linhas duplicadas na planilha final ------------------------------------

# Linhas duplicadas por chave (ex: "ID_OEMA")
def get_duplicate_rows(df: pd.DataFrame, key: str = "ID_OEMA") -> pd.DataFrame:
    '''  - df: DataFrame final
         - key: nome da coluna que quer usar como filtro'''

    s = df[key].astype("string").str.strip()
    mask = s.duplicated(keep=False)
    return df.loc[mask].sort_values(key)

# Relatório por chave com número de linhas e colunas diferentes
def get_duplicates_report(df: pd.DataFrame, key: str = "ID_OEMA") -> pd.DataFrame:
    s = df[key].astype("string").str.strip()
    dups = df.loc[s.duplicated(keep=False)]
    rows = []
    for k, g in dups.groupby(key):
        nun = g.nunique(dropna=False)
        diff_cols = nun[nun > 1].index.tolist()
        rows.append({"ID": k, "n_rows": len(g), "diff_cols": diff_cols})
    rep = pd.DataFrame(rows).sort_values(["n_rows","ID"], ascending=[False, True])
    return rep

# Linhas duplicadas por chave dupla (ex: ["ID_OEMA","UF"])
def get_duplicate_rows_multi(df: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    # normaliza espaços nas chaves
    norm = df.copy()
    for k in keys:
        norm[k] = norm[k].astype("string").str.strip()
    mask = norm.duplicated(subset=keys, keep=False)
    return df.loc[mask].sort_values(keys)

# Todas as linhas de uma chave composta específica
def get_rows_for_keys(df: pd.DataFrame, keys: list[str], values: list) -> pd.DataFrame:
    m = pd.Series(True, index=df.index)
    for c, v in zip(keys, values):
        m &= df[c].astype("string").str.strip().eq(str(v).strip())
    return df.loc[m]


#----------------------------- Salvar como 'UF'_estacoes ------------------------------------

def save_UF_estacoes_csv(df_final, uf):
    base = Path.cwd().parent  
    out_dir = base / "data" / "DADOS_ESTACOES"
    out_dir.mkdir(parents=True, exist_ok=True)

    out_file = out_dir / f"{uf}_estacoes.csv"
    df_final.to_csv(out_file, index=False, encoding="utf-8")
    print("Saved to:", out_file.resolve())
    return

#----------------------------- Aplicação das funções nas UFs ------------------------------------

# ##### a) Ceará

# uf = "CE" 

# # Conferir respostas do formulário 
# ce_forms = forms[forms["Unidade da Federação: "].str.contains(uf, case=False, na=False)]
# ce_forms.iloc[:, idxs].head()

# # Importar arquivos do estado
# base = Path.cwd().parent 
# df_dir = base / "data" / "DADOS_BRUTOS" 
# df_dir.mkdir(parents=True, exist_ok=True)
# ce_dir = df_dir / uf

# ce_dfs = load_csvs(ce_dir)

# # Renomear todas as colunas com data e hora para datetime
# manual_map = {"fecha":  "DATETIME",
#               "Date":  "DATETIME",
#               "Fecha":  "DATETIME",
# }

# ce_dfs = {name: df.rename(columns=manual_map) for name, df in ce_dfs.items()}

# # Transformar coluna datetime para formato desejado
# ce_dfs = {
#     name: convert_column_to_datetime(d, column_name="DATETIME", format="%d/%m/%Y %H:%M")
#     for name, d in ce_dfs.copy().items()
# }

# # Unir dataframes em único > Precisa ser feito antes de rodar a rotina de criação da planilha de estações
# ce_frame = merge_station_dfs(ce_dfs.copy(), uf)

# # Corrigir problemas com datetime
# ce_frame = fix_datetime_df(ce_frame, "DATETIME")
# diag_bad_stations(ce_frame, "DATETIME")

# # Criar planilha final
# ce_dfs = build_inventory_rows(ce_frame.copy(), df_cod, uf, datetime_col='DATETIME', mode="columns")
# ce_dfs = assign_id_mma(ce_dfs)

# save_UF_estacoes_csv(ce_dfs, uf)


# # ##### b) Rio de Janeiro

# uf = "RJ" 

# # Conferir respostas do formulário 
# rj_forms = forms[forms["Unidade da Federação: "].str.contains(uf, case=False, na=False)]
# rj_forms.iloc[:, idxs].head()

# # Importar arquivos do estado
# base = Path.cwd().parent 
# df_dir = base / "data" / "DADOS_ESTACOES" 
# df_dir.mkdir(parents=True, exist_ok=True)
# rj_dir = df_dir / uf 
# os.listdir(rj_dir)

# ''' Neste caso, a inspeção das pastas indiciou que existiam arquivos .XLSX e .CSV, 
#     necessitando aplicar duas operações diferentes para leitura dos arquivos'''

# rj_exls = load_excels(rj_dir) # Está organizado para ler sempre a primeira planilha
# rj_csvs = load_csvs(rj_dir)


# ''' Neste caso, como são dois dicionários diferentes - uma para arquivos .XLSX e uma para arquivos .CSV,
#     foi necessário fazer um merge entre eles. Esse passo vai existir nessas condições'''

# rj_dfs = rj_csvs | rj_exls 


# # Encontrar colunas diferentes e iguais dentro dos dicts 
# summary, stats = summarize_columns(rj_dfs, normalize=True)

# # Colunas iguais em todos
# cols_comuns = summary.loc[summary.is_common, "col"].tolist()

# # Colunas diferentes em todos
# cols_diff = summary.loc[~ summary.is_common, "col"].tolist()

# # Estatísticas por DataFrame
# stats[["df","n_cols","n_common_present","n_common_missing","extras_count"]].head()

# # Limpar caracteres indesejados
# for name, d in rj_dfs.items(): clean_df_all_text(d, in_place=True)

# # Depois de rodar pela primeira vez e identificar os conflitos, posso escolher a base de dados prioritária para sobrepor informações
# priority = ["RJ_estacoes_enviada", "RJ_estacoes_nao_preenchidas", "RJ_estacoes"]

# rj_frame, conflicts = merge_by_id_multi(
#     rj_dfs.copy(),
#     id_cols=['ID_OEMA','POLUENTE'],
#     source_priority=priority,
#     drop_empty_strings=True,
# )

# # Lista de colunas alvo que já existem no df (na ordem desejada)
# cols = [
#     "ID_OEMA","ID_MMA","CIDADE","CD_MUN","CATEGORIA",
#     "FUNCIONAMENTO","PROPRIETARIO","PROP_ENTIDADE","OPERADOR","OP_ENTIDADE",
#     "LATITUDE","LONGITUDE","MOBILIDADE","REALOCACAO","MARCA","METODO","FINALIDADE",
#     "STATUS","CALIBRACAO","OBS_CALIBRACAO","MONITORAR","FONTE",
#     "OBS_GERAIS","DADOS_MONITORAMENTO","RECONHECIDA","REP_ESPACIAL_DECLARADA",
#     "REP_ESPACIAL"
# ]

# def make_field_map(cols,
#                    prefer_mode=("CIDADE",),     # PT-BR: colunas que preferem moda
#                    use_group_key=("ID_OEMA",)): # PT-BR: colunas que vêm da chave do grupo
#     fm = {}
#     for c in cols:
#         if c in use_group_key:
#             fm[c] = ("group_key",)
#         elif c in prefer_mode:
#             fm[c] = ("col", c, {"strategy": "mode"})
#         else:
#             fm[c] = ("col", c, {"strategy": "first_non_null"})
#     return fm

# field_map = make_field_map(cols)
# teste = build_inventory_flexible(
#     rj_frame.copy(),
#     uf,
#     df_cod,
#     group_col="ID_OEMA",
#     datetime_col=None,  # ou "DATETIME" se desejar calcular INICIO/FIM
#     mode= "rows",
#     field_map=field_map
# )

# save_UF_estacoes_csv(teste, uf)


# # ##### c) Paraíba

# uf = "PB" 

# # Conferir respostas do formulário 
# pb_forms = forms[forms["Unidade da Federação: "].str.contains(uf, case=False, na=False)]
# pb_forms.iloc[:, idxs].head()


# # Importar arquivos do estado
# base = Path.cwd().parent 
# df_dir = base / "data" / "DADOS_BRUTOS" 
# df_dir.mkdir(parents=True, exist_ok=True)

# pb_dir = df_dir / uf

# pb_dfs = load_txts(pb_dir)


# # NOTA: Informações fornecidas pela UF
# # 
# # Localização:
# # 
# # Estação 1: 7°2'4.75"S 34°50'34.73"W
# # 
# # Estação 2: 7°5'11.20"S 34°50'56.19"W
# # 
# # Estação 3: 7°2'50.65"S 34°57'23.56"W
# # 
# # Formato do arquivo de dados:[Data]T[Hora];[Serial];[NOME DO ÓRGÃO];[PTS];[PM10];[PM2.5];[PM1];[VOLTAGEM DA BATERIA];

# # Adicionar informações de cabeçalho 
# # Manual_map foi montado com base nas informações fornecidas pelo estado sobre os arquivos .txt
# manual_map = [
#     "DATETIME", "serial", "PROPRIETARIO", "PTS",
#     "MP10", "MP25", "MP1", "voltagem_bateria"
# ]

# pb_dfs = {name: df.set_axis(manual_map, axis=1) for name, df in pb_dfs.items()}

# # Unir dfs
# pb_frame = merge_station_dfs(pb_dfs.copy(), uf)

# # Limpar linhas de datetime para aceitar o formato
# pb_frame["DATETIME"] = (pb_frame["DATETIME"].astype(str).str.replace("T", " "))

# # Criar planilha final 
# pb_dfs = build_inventory_rows(pb_frame.copy(), df_cod, uf, datetime_col='DATETIME', mode="columns")
# pb_dfs["PROPRIETARIO"] = pb_frame["PROPRIETARIO"]

# # Adicionar colunas de latitude e longitude
# lat_map = {
#     "Estação 1": -7.034652778,
#     "Estação 2": -7.086444444,
#     "Estação 3": -7.047402778,
# }
# lon_map = {
#     "Estação 1": -34.842980556,
#     "Estação 2": -34.848941667,
#     "Estação 3": -34.956544444,
# }

# pb_dfs["LATITUDE"]  = pb_dfs["ID_OEMA"].map(lat_map)
# pb_dfs["LONGITUDE"] = pb_dfs["ID_OEMA"].map(lon_map)

# # Adicionar ID_MMA
# pb_dfs = assign_id_mma(pb_dfs)

# save_UF_estacoes_csv(pb_dfs, uf)


# # ##### d) Pernambuco

# uf = "PE" 

# # Conferir respostas do formulário 
# pe_forms = forms[forms["Unidade da Federação: "].str.contains(uf, case=False, na=False)]
# pe_forms.iloc[:, idxs].head()

# # Importar arquivos do estado
# base = Path.cwd().parent 
# df_dir = base / "data" / "DADOS_BRUTOS" 
# df_dir.mkdir(parents=True, exist_ok=True)

# pe_dir = df_dir / uf
# pe_dfs = load_excels(pe_dir,sheets=0)


# # Limpar dataframes pois contém informações extras nas linhas que não são utilizadas

# bad_rows = {
#     "Data Precent","Avg","STD","Num",
#     "Maximum","Max Date","Max Time",
#     "Minimum","Min Date","Min Time",
# }

# for name, df in pe_dfs.items():
#     first_col = df.columns[0]
#     mask = df[first_col].astype(str).str.strip().isin(bad_rows)
#     pe_dfs[name] = df.loc[~mask].copy()


# # Criar um dataframe por df dentro do dict
# pe_out = {} 

# for name, df in pe_dfs.copy().items():

#     # 1) find the header start row
#     idx = df.index[df.iloc[:, 0].astype(str).str.strip().eq("Date Time")]
#     start = int(idx[0]) if len(idx) else 0
#     sub = df.iloc[start:].reset_index(drop=True)

#     # df is your raw frame
#     station = df.iloc[1].ffill()          # row 1, forward-fill across columns
#     pollutant = df.iloc[2].astype(str)                # row 2

#     new_cols = ["DATETIME"] + [f"{st}|{po}" for st, po in zip(station[1:], pollutant[1:])]

#     out = sub.iloc[4:].copy()                       # data rows
#     out.columns = new_cols

#     pe_out[name] = out  


# # Reparar coluna datetime
# pe_frame = {
#     name: fix_datetime_df(d, col="DATETIME", keep_dt_col=False)
#     for name, d in pe_out.copy().items()
# }


# # Nota: Nesse caso, as planilhas de estações seguem ordem cronológica de datetime, então o merge precisa conferir se a estação já existia ou se foi criada em um novo ano.

# def coalesce_duplicate_columns(df: pd.DataFrame) -> pd.DataFrame:
#     """If the same column name appears multiple times, keep one and fill with first non-null."""
#     counts = Counter(df.columns)
#     dups = [c for c, n in counts.items() if n > 1]
#     for c in dups:
#         cols = [k for k in df.columns if k == c]
#         df[c] = df[cols].bfill(axis=1).iloc[:, 0]  # take first non-null left-to-right
#         df.drop(columns=cols[1:], inplace=True)
#     return df

# def merge_by_datetime_union(dfs_dict: dict, keep_source=True):
#     frames = []
#     for name, df in dfs_dict.items():
#         t = df.copy()
#         if keep_source:
#             t["__source"] = name  # year or filename

#         frames.append(t)

#     if not frames:
#         return pd.DataFrame()

#     out = pd.concat(frames, axis=0, ignore_index=True, sort=True)  # union of columns
#     out = coalesce_duplicate_columns(out)

#     # keep DATETIME first if present
#     if "DATETIME" in out.columns:
#         cols = ["DATETIME"] + [c for c in out.columns if c != "DATETIME"]
#         out = out[cols]

#     return out

# pe_all = merge_by_datetime_union(pe_frame.copy(), keep_source=True)

# # Criar planilha com formato adequado usando MELT

# def make_station_layout(df_or_dict, keep_source=True):
#   # accept dicts of DataFrames too
#     df = (pd.concat(df_or_dict.values(), ignore_index=True, sort=False)
#           if isinstance(df_or_dict, dict) else df_or_dict)

#     id_vars = ["DATETIME"]
#     if keep_source and "__source" in df.columns:
#         id_vars.append("__source")

#     long = df.melt(id_vars=id_vars, var_name="pair", value_name="VALUE")
#     long = long[long["pair"].astype(str).str.contains(r"\|", na=False)].copy()

#     # critical line: force string and split on literal "|"
#     long["pair"] = long["pair"].astype("string")
#     long[["ESTACAO", "POLLUTANT"]] = long["pair"].str.split(
#         pat="|", n=1, expand=True, regex=False
#     )
#     long.drop(columns=["pair"], inplace=True)
#     long["ESTACAO"] = long["ESTACAO"].str.strip()
#     long["POLLUTANT"] = long["POLLUTANT"].str.strip()

#     index_cols = ["DATETIME", "ESTACAO"] + (["__source"] if "__source" in id_vars else [])
#     wide = (
#         long.pivot_table(index=index_cols, columns="POLLUTANT", values="VALUE", aggfunc="first")
#             .reset_index()
#             .sort_values(["DATETIME", "ESTACAO"], kind="stable")
#     )
#     wide.columns.name = None
#     return wide


# pe_all = make_station_layout(pe_all, keep_source=True)  # keeps "NoData"

# # Nota: Nota-se que existem anos que não há medição por poluente, discriminado como NoData. Neste caso, não podemos contabilizar o poluente na estação, por isso deve-se aplicar um filtro.

# pe_station = build_inventory_rows(pe_all.copy(), df_cod, uf, datetime_col='DATETIME', mode="columns", drop_after_underscore=True)
# pe_station = assign_id_mma(pe_station)

# save_UF_estacoes_csv(pe_station, uf)


# # ##### e) Roraima

# uf = "RR" 

# # Conferir respostas do formulário 
# rr_forms = forms[forms["Unidade da Federação: "].str.contains("RR" , case=False, na=False)]
# rr_forms.iloc[:, idxs].head()

# # Importar arquivos do estado
# base = Path.cwd().parent 
# df_dir = base / "data" / "DADOS_BRUTOS" 
# df_dir.mkdir(parents=True, exist_ok=True)

# rr_dir = df_dir / uf
# os.listdir(rr_dir)

# rr_dfs = load_excels(rr_dir)


# # Nota: Como os 3 dataframes possuem formatos diferentes, é necessário tratá-los conforme suas particularidades


# # 1) Fazer alterações somente no df Medições (29) dentro de rr_dfs dict
# data = rr_dfs.copy()
# key = "Medições (29)"              # exact key in rr_dfs
# df = data[key].copy()

# # 1) find the header start row
# idx = df.index[df.iloc[:, 0].astype(str).str.strip().eq("Data e Hora")]
# start = int(idx[0]) if len(idx) else 0
# sub = df.iloc[start:].reset_index(drop=True)

# # df is your raw frame
# station = df.iloc[0].ffill()          # row 1, forward-fill across columns
# pollutant = df.iloc[3].astype(str)                # row 2

# new_cols = ["DATETIME"] + [f"{st}|{po}" for st, po in zip(station[1:], pollutant[1:])]

# out = sub.iloc[7:].copy()                       # data rows
# out.columns = new_cols
# out["__source"] = key

# data[key]=out


# # 2) Fazer alterações nos dfs "FAZENDA-ENEVA" e "FEMARH-ENEVA" dentro de rr_dfs dict
# manual_map = {"Data": "DATETIME"}

# for key in ["FAZENDA-ENEVA", "FEMARH-ENEVA"]:
#     val = data.get(key)
#     if val is None:
#         continue

#     if isinstance(val, dict):
#         # rename inside nested dict
#         new = {}
#         for name, obj in val.items():
#             if isinstance(obj, pd.DataFrame):
#                 new[name] = obj.rename(columns=manual_map)
#         data[key] = new

#     elif isinstance(val, pd.DataFrame):
#         data[key] = val.rename(columns=manual_map)

#     elif isinstance(val, pd.Series):
#         data[key] = val.rename("DATETIME") if val.name == "Data" else val

# # Reparar coluna datetime
# rr_frame = {
#     name: fix_datetime_df(d, col="DATETIME", keep_dt_col=False)
#     for name, d in data.copy().items()
# }


# # 1) Fazer alterações somente no df Medições (29) dentro de rr_dfs dict
# key = "Medições (29)"              
# df = rr_frame[key].copy()

# medicoes = make_station_layout(df, keep_source=True)

# #Criar planilha final 

# rr_station = build_inventory_rows(medicoes.copy(), df_cod, uf, datetime_col='DATETIME', mode="columns", drop_after_underscore=True)
# rr_station = assign_id_mma(rr_station)

# save_UF_estacoes_csv(rr_station, uf)


# # ##### f) Acre

# uf = "AC" 

# # Conferir respostas do formulário 
# ac_forms = forms[forms["Unidade da Federação: "].str.contains(uf , case=False, na=False)]
# ac_forms.iloc[:, idxs].head()

# # Importar arquivos do estado
# base = Path.cwd().parent 
# df_dir = base / "data" / "DADOS_BRUTOS" 
# df_dir.mkdir(parents=True, exist_ok=True)

# ac_dir = df_dir / uf
# os.listdir(ac_dir)

# # Como foram apresentadas particularidades nesse arquivo csv, foi necessário fazer uma alteração na função read,
# # para transformar manualmente o tipo de encoding

# def _read_csv(path, sep=None, decimal=None, encoding="cp1252", **kw):
#     head = path.read_bytes()[:4096]
#     txt  = head.decode(encoding or "utf-8", errors="ignore")
#     sep_guess = sep or (";" if txt.count(";") > txt.count(",") else ",")
#     dec_guess = decimal or ("," if re.search(r"\d+,\d+", txt) and txt.count(",") > txt.count(".") else ".")
#     enc_guess = encoding or ("utf-8-sig" if txt.startswith("\ufeff")
#                              else ("latin-1" if ("Ã" in txt or "�" in txt) else "utf-8"))
#     try:
#         return pd.read_csv(path, sep=sep_guess, decimal=dec_guess, encoding=enc_guess, engine="c", **kw)
#     except Exception:
#         return pd.read_csv(path, sep=None, engine="python", decimal=dec_guess, encoding=enc_guess, **kw)


# ac_csv = load_csvs(ac_dir)

# # Nota: Como há apenas 1 df - fazer a conversão direta para dataframe
# ac_long = pd.DataFrame(list(ac_csv.values())[0])


# # Como a planilha de dados possui diversas particularidades, precisa passar por uma limpeza

# df = ac_long.copy()

# # 1) find the header start row
# idx = df.index[(df.iloc[:, 0].isna()) & (df.notna().sum(axis=1) >= 3)]
# start = int(idx[0]) if len(idx) else 0
# sub = df.iloc[start:].reset_index(drop=True)

# # 2) build column names: row 1 has stations from col 1 onward
# stations = (
#     sub.iloc[1, 1:]           # row with station names, skip first col
#        .astype(str).str.strip()
#        .tolist()
# )

# new_cols = ["DATETIME"] + stations 

# ac_dfc = sub.iloc[2:].copy() 
# ac_dfc.columns = new_cols 
# ac_dfc.head()


# # Criar coluna de ESTACOES com os nomes dos headers
# station_cols = ['Ministério Público do Estado do Acre (SEDE) A',
#        'Ministério Público do Estado do Acre (SEDE) B', 'UFAC A', 'UFAC B',
#        'RB-BACKUP (Estação particular FB) A',
#        'RB-BACKUP (Estação particular FB) B', 'AcreBioClima - UFAC A',
#        'AcreBioClima - UFAC B', 'MPAC_BJR_01_promotoria A',
#        'MPAC_BJR_01_promotoria B', 'MPAC_SNG_01_promotoria A',
#        'MPAC_SNG_01_promotoria B', 'MPAC_PTA_01_Sec.infraestrutura A',
#        'MPAC_PTA_01_Sec.infraestrutura B', 'MPAC_ACL_01_promotoria A',
#        'MPAC_ACL_01_promotoria B', 'MPAC_CPX_01_qpm A', 'MPAC_CPX_01_qpm B',
#        'MPAC_XAP_02_promotoria A', 'MPAC_XAP_02_promotoria B',
#        'MPAC_ABR_01_promotoria A', 'MPAC_ABR_01_promotoria B',
#        'MPAC_ABR_02_SEMSA A', 'MPAC_ABR_02_SEMSA B',
#        'MPAC_PLC_01_promotoria A', 'MPAC_PLC_01_promotoria B',
#        'MPAC_SNM_01_ifac A', 'MPAC_SNM_01_ifac B', 'MPAC_SNM_02_promotoria A',
#        'MPAC_SNM_02_promotoria B', 'MPAC_MNU_01_promotoria A',
#        'MPAC_MNU_01_promotoria B', 'MPAC_FIJ_01_promotoria A',
#        'MPAC_FIJ_01_promotoria B', 'MPAC_TRC_02_ifac A', 'MPAC_TRC_02_ifac B',
#        'MPAC_JRD_01_prefeitura A', 'MPAC_JRD_01_prefeitura B',
#        'MPAC_RDA_01_prefeitura A', 'MPAC_RDA_01_prefeitura B',
#        'MPAC_CZS_02_ciosp A', 'MPAC_CZS_02_ciosp B', 'UFACFloresta A',
#        'UFACFloresta B', 'MPAC_MTH_01_semec A', 'MPAC_MTH_01_semec B',
#        'MPAC_EPL_02_escola.joao.pedro A', 'MPAC_EPL_02_escola.joao.pedro B',
#        'MPAC_BRL_02_radio fm 90.3 A', 'MPAC_BRL_02_radio fm 90.3 B',
#        'MPAC_BRL_01_promotoria A', 'MPAC_BRL_01_promotoria B',
#        'MPAC_SRP_01_prefeitura A', 'MPAC_SRP_01_prefeitura B',
#        'MPAC_PTW_01_prefeitura A', 'MPAC_PTW_01_prefeitura B']

# ac_full = ac_dfc.melt(
#     id_vars=['DATETIME'],   # keep these as is
#     value_vars=station_cols,                      # columns to unpivot
#     var_name='ESTACAO',                           # new col with station names
#     value_name='VALOR'                            # new col with numeric values
# )
# ac_full

# # Criar planilha final 
# ac_station = build_inventory_rows(ac_full.copy(), df_cod, uf, datetime_col='DATETIME', mode="rows", drop_after_underscore=True)

# # Adicionar coluna de CIDADE
# df = ac_long.copy()

# # 1) find the header start row
# idx = df.index[(df.iloc[:, 0].isna()) & (df.notna().sum(axis=1) >= 3)]
# start = int(idx[0]) if len(idx) else 0
# sub = df.iloc[start:].reset_index(drop=True)

# # From your cleaned 'sub' with two header rows:
# cities   = sub.iloc[0, 1:].astype(str).tolist()      
# stations = sub.iloc[1, 1:].astype(str).tolist()     

# # 1) station -> city
# station_to_city = dict(zip(stations, cities))        

# # 2) map onto your dataframe
# ac_station["CIDADE"] = ac_station["ID_OEMA"].map(station_to_city)

# # Adicionar colunas conhecidas
# cols = {
#     "POLUENTE": "MP25",
#     "CATEGORIA": "Indicativa",
#     "MARCA": "PurpleAir",
# }

# targets = list(cols)

# # normalize empty strings and whitespace to NA
# ac_station[targets] = ac_station[targets].replace(r"^\s*$", pd.NA, regex=True)

# # fill only where missing
# for c, v in cols.items():
#     ac_station.loc[ac_station[c].isna(), c] = v

# # Adicionar ID_MMA
# ac_station = assign_id_mma(ac_station)

# save_UF_estacoes_csv(ac_station, uf)


# # ##### g) Mato Grosso do Sul

# uf = "MS" 

# # Conferir respostas do formulário 
# ms_forms = forms[forms["Unidade da Federação: "].str.contains(uf, case=False, na=False)]
# ms_forms.iloc[:, idxs].head()

# # Importar arquivos do estado
# base = Path.cwd().parent 
# df_dir = base / "data" / "DADOS_BRUTOS" 
# df_dir.mkdir(parents=True, exist_ok=True)

# ms_dir = df_dir / uf
# oad_excels(ms_dir)


# # Criar coluna DATETIME com merge de colunas Data e HOra (que estão separadas)

# for name, df in ms_dfs.items():
#     df["DATETIME"] = pd.to_datetime(df["Data"] + " " + df["Hora"], format="%d/%m/%Y %H:%M")

# # Unir dfs dentro do dict pela coluna Datetime para seguir ordem cronológica
# ms_full = merge_by_datetime_union(ms_dfs, keep_source=True)

# # Renomear colunas
# manual_map = {"Estação":  "ESTACAO",
#               "Sigla":  "POLUENTE"
# }

# ms_full = ms_full.rename(columns=manual_map) 

# # Converter formado datetime
# ms_full = convert_column_to_datetime(ms_full, column_name="DATETIME", format="%d/%m/%Y %H:%M")

# # Criar planilha final
# ms_station = build_inventory_rows(ms_full.copy(), df_cod, uf, datetime_col='DATETIME', mode="rows")
# ms_station = assign_id_mma(ms_station)

# # Adicionar valores em colunas conhecidas 
# cols = {
#     "CATEGORIA": "Referencia",
# }

# targets = list(cols)
# # normalize empty strings and whitespace to NA
# ms_station[targets] = ms_station[targets].replace(r"^\s*$", pd.NA, regex=True)
# # fill only where missing
# for c, v in cols.items():
#     ms_station.loc[ms_station[c].isna(), c] = v


# save_UF_estacoes_csv(ms_station, uf)

