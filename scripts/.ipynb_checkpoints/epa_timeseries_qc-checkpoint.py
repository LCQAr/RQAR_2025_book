#!/usr/bin/env python3
"""
epa_timeseries_qc.py
--------------------
Ready-to-use EPA-style Level 1 automated time-series QA checks for air quality data.

Assumptions (tweakable via CLI):
- Columns/units:
    O3, NO2, NOx, SO2 in ppb
    CO in ppm
    PM25, PM10 in µg/m3
- Timestamp column is named "datetime" (can change via --time-col).
- Data are at regular intervals (e.g., 1-min, 5-min, 1-hr). Script auto-detects frequency to scale ROC limits.
- Outputs a CSV with added *_QC_FLAGS columns (semicolon-separated flags) and *_QC_PASS booleans.
- Also writes a summary JSON of flag counts per pollutant.

Usage:
    python epa_timeseries_qc.py --input data.csv --output qc_data.csv

Example custom limits:
    python epa_timeseries_qc.py --roc-limit O3=60 --range O3=0:500 --flatline-n 5

Author: ChatGPT (EPA-style screening checks)
"""

import argparse
import json
from pathlib import Path
import pandas as pd
import numpy as np
import os
# -------------------- Default Parameters (tune as needed) --------------------
# Plausible physical ranges (min:max). Units noted above.
DEFAULT_RANGE_LIMITS = {
    "O3": (0, 500),
    "CO": (0, 50),
    "NO2": (0, 1000),
    "NOx": (0, 2000),
    "SO2": (0, 1000),
    "PM25": (0, 1000),
    "PM10": (0, 2000),
}

# Rate-of-change (ROC) absolute change thresholds for 1-hour data.
# These scale by sqrt(dt_hours) for other time steps, assuming random-walk-ish variability.
DEFAULT_ROC_LIMITS_PER_HOUR = {
    "O3": 60,    # ppb / hour
    "CO": 5,     # ppm / hour
    "NO2": 150,  # ppb / hour
    "NOx": 200,  # ppb / hour
    "SO2": 150,  # ppb / hour
    "PM25": 200, # µg/m3 per hour
    "PM10": 300, # µg/m3 per hour
}

# Negative tolerance (allows small negative values to pass due to noise/zero correction).
DEFAULT_NEGATIVE_LIMITS = {
    "O3": -2,
    "CO": -0.2,
    "NO2": -2,
    "NOx": -2,
    "SO2": -2,
    "PM25": -2,
    "PM10": -2,
}

# Flatline: N consecutive identical (within resolution) values
DEFAULT_FLATLINE_N = 5
# Instrument resolution tolerance for "identical" (absolute diff <= tol)
DEFAULT_RESOLUTION_TOL = {
    "O3": 1.0,
    "CO": 0.1,
    "NO2": 1.0,
    "NOx": 1.0,
    "SO2": 1.0,
    "PM25": 0.5,
    "PM10": 1.0,
}

# Step-change detector: compares window means before/after a point
DEFAULT_STEP_WINDOW = 3  # samples on each side
DEFAULT_STEP_LIMITS = {
    "O3": 80,
    "CO": 6,
    "NO2": 200,
    "NOx": 300,
    "SO2": 200,
    "PM25": 250,
    "PM10": 350,
}

# Internal consistency relationships
# PM logic: PM10 >= PM25 (within a tolerance), else flag
PM_TOL = 2.0  # µg/m3 tolerance
# NOx vs NO2: NO2 <= NOx + tol
NOX_TOL = 2.0 # ppb tolerance

RECOG_POLLUTANTS = ["O3", "CO", "NO2", "NOx", "SO2", "PM25", "PM10"]


def parse_range_arg(arg_list):
    """Parse --range args like O3=0:500 NO2=0:1000 into dict."""
    out = {}
    for item in arg_list or []:
        if "=" not in item or ":" not in item:
            raise ValueError(f"Invalid --range '{item}', use NAME=min:max")
        name, span = item.split("=", 1)
        mn, mx = span.split(":", 1)
        out[name] = (float(mn), float(mx))
    return out


def parse_scalar_arg(arg_list, cast=float):
    """Parse args like O3=60 into dict of scalars."""
    out = {}
    for item in arg_list or []:
        if "=" not in item:
            raise ValueError(f"Invalid arg '{item}', use NAME=value")
        name, val = item.split("=", 1)
        out[name] = cast(val)
    return out


def autodetect_dt_hours(ts: pd.Series) -> float:
    """Detect typical time delta in hours using median diff."""
    deltas = ts.diff().dropna().dt.total_seconds() / 3600.0
    if deltas.empty:
        return 1.0
    return float(np.median(deltas))


def scale_roc_limits(base_limits: dict, dt_hours: float) -> dict:
    """Scale ROC limits from 1-hr to dt using sqrt(dt_hours)."""
    scale = max(dt_hours, 1e-9) ** 0.5
    return {k: v * scale for k, v in base_limits.items()}


def add_flag(flags_arr, idx, label):
    if isinstance(flags_arr[idx], list):
        flags_arr[idx].append(label)
    elif flags_arr[idx] is None:
        flags_arr[idx] = [label]
    else:
        # shouldn't happen; initialize cleanly
        flags_arr[idx] = [label]


def _append_flag_string(cell, label):
    """Append a flag label into a semicolon-separated string cell."""
    if cell is None or (isinstance(cell, float) and np.isnan(cell)):
        return label
    if isinstance(cell, str):
        parts = set(cell.split(";")) if cell else set()
        parts.add(label)
        return ";".join(sorted(parts))
    if isinstance(cell, list):
        parts = set(cell)
        parts.add(label)
        return ";".join(sorted(parts))
    # Fallback: coerce to string
    return f"{cell};{label}"


def run_qc(df: pd.DataFrame,
           time_col: str,
           pollutants: list,
           range_limits: dict,
           roc_limits_per_hour: dict,
           negative_limits: dict,
           flatline_n: int,
           resolution_tol: dict,
           step_window: int,
           step_limits: dict,
           ) -> (pd.DataFrame, dict):
    """Apply automated screening checks and return augmented DF + summary."""
    df = df.copy()
    #df[pollutants] = df[pollutants].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False).astype(float)

    if time_col not in df.columns:
        raise KeyError(f"Time column '{time_col}' not in input.")
    df[time_col] = pd.to_datetime(df[time_col], errors="coerce")
    df = df.sort_values(time_col).reset_index(drop=True)
    dt_hours = autodetect_dt_hours(df[time_col])

    roc_limits = scale_roc_limits(roc_limits_per_hour, dt_hours)

    summary = {}
    for p in pollutants:
        if p not in df.columns:
            continue

        x = pd.to_numeric(df[p], errors="coerce").values.astype(float)
        n = len(x)
        flags = [None] * n

        # 1) Range / plausibility
        if p in range_limits:
            mn, mx = range_limits[p]
            rng_fail = (x < mn) | (x > mx)
            for i, bad in enumerate(rng_fail):
                if bad and not np.isnan(x[i]):
                    add_flag(flags, i, "RANGE")
        # 2) Negative tolerance
        if p in negative_limits:
            neg_lim = negative_limits[p]
            neg_fail = x < neg_lim
            for i, bad in enumerate(neg_fail):
                if bad and not np.isnan(x[i]):
                    add_flag(flags, i, "NEGATIVE")

        # 3) ROC / spike detection (abs diff from previous sample)
        if p in roc_limits:
            roc_lim = roc_limits[p]
            dx = np.abs(np.diff(x))
            for i in range(1, n):
                if not np.isnan(x[i]) and not np.isnan(x[i-1]) and dx[i-1] > roc_lim:
                    add_flag(flags, i, "ROC")

        # 4) Flatline / persistence
        tol = resolution_tol.get(p, 0.0)
        if flatline_n >= 2:
            count = 1
            for i in range(1, n):
                if not np.isnan(x[i]) and not np.isnan(x[i-1]) and abs(x[i] - x[i-1]) <= tol:
                    count += 1
                else:
                    count = 1
                if count >= flatline_n:
                    add_flag(flags, i, f"FLATLINE({flatline_n})")

        # 5) Step-change detector (windowed mean before vs after)
        # Only run if enough points exist
        if step_window > 0 and p in step_limits and n >= (2 * step_window + 1):
            step_lim = step_limits[p]
            # Rolling means (centered) are tricky at edges; do explicit loop
            for i in range(step_window, n - step_window):
                pre = x[i - step_window:i]
                post = x[i + 1:i + 1 + step_window]
                if np.isnan(x[i]) or np.any(np.isnan(pre)) or np.any(np.isnan(post)):
                    continue
                diff = abs(np.nanmean(post) - np.nanmean(pre))
                if diff > step_lim:
                    add_flag(flags, i, "STEP")

        # Collect flags into columns
        flag_str = [None if f is None else ";".join(sorted(set(f))) for f in flags]
        df[f"{p}_QC_FLAGS"] = flag_str
        df[f"{p}_QC_PASS"] = [f is None for f in flags]

        # Summary
        counts = {}
        for f in flag_str:
            if f is None:
                continue
            for lab in f.split(";"):
                counts[lab] = counts.get(lab, 0) + 1
        summary[p] = counts

    # 6) Internal consistency checks (multivariate)
    # PM10 >= PM25 - PM_TOL
    if "PM10" in df.columns and "PM25" in df.columns:
        pm10 = pd.to_numeric(df["PM10"], errors="coerce").values.astype(float)
        pm25 = pd.to_numeric(df["PM25"], errors="coerce").values.astype(float)
        cond = (~np.isnan(pm10)) & (~np.isnan(pm25)) & (pm10 + PM_TOL < pm25)
        if "PM10_QC_FLAGS" not in df.columns:
            df["PM10_QC_FLAGS"] = None
            df["PM10_QC_PASS"] = True
        for i, bad in enumerate(cond):
            if bad:
                df.at[i, "PM10_QC_FLAGS"] = _append_flag_string(df.at[i, "PM10_QC_FLAGS"], "CONSISTENCY(PM10<PM25)")
                df.at[i, "PM10_QC_PASS"] = False

    # NO2 <= NOx + NOX_TOL
    if "NO2" in df.columns and "NOx" in df.columns:
        no2 = pd.to_numeric(df["NO2"], errors="coerce").values.astype(float)
        nox = pd.to_numeric(df["NOx"], errors="coerce").values.astype(float)
        cond = (~np.isnan(no2)) & (~np.isnan(nox)) & (no2 > nox + NOX_TOL)
        if "NO2_QC_FLAGS" not in df.columns:
            df["NO2_QC_FLAGS"] = None
            df["NO2_QC_PASS"] = True
        for i, bad in enumerate(cond):
            if bad:
                df.at[i, "NO2_QC_FLAGS"] = _append_flag_string(df.at[i, "NO2_QC_FLAGS"], "CONSISTENCY(NO2>NOx)")
                df.at[i, "NO2_QC_PASS"] = False

    return df, summary


def main(in_path, out_path, summary_json, pollutant):
    # ap = argparse.ArgumentParser(description="EPA-style Level 1 time-series QC checks for air quality.")
    # ap.add_argument("--input", required=True, help="Input CSV with a datetime column and pollutant columns.")
    # ap.add_argument("--output", required=True, help="Output CSV with QC columns added.")
    # ap.add_argument("--summary-json", default=None, help="Optional path to save a JSON summary of flags.")
    # ap.add_argument("--time-col", default="datetime", help="Name of the timestamp column (default: datetime).")
    # ap.add_argument("--pollutants", nargs="*", default=None, help=f"Subset of pollutants to check (default: all). Options: {RECOG_POLLUTANTS}")
    # Override defaults via CLI
    # ap.add_argument("--range", nargs="*", help="Overrides like O3=0:500 NO2=0:1000")
    # ap.add_argument("--roc-limit", nargs="*", help="Overrides like O3=60 CO=4 (per hour).")
    # ap.add_argument("--neg-limit", nargs="*", help="Overrides like O3=-1 NO2=-1")
    # ap.add_argument("--flatline-n", type=int, default=DEFAULT_FLATLINE_N, help="Consecutive identical values to flag (default 5).")
    # ap.add_argument("--resolution", nargs="*", help="Instrument resolution tolerance like PM25=0.5 O3=1.0")
    # ap.add_argument("--step-window", type=int, default=DEFAULT_STEP_WINDOW, help="Window size for step-change (default 3).")
    # ap.add_argument("--step-limit", nargs="*", help="Step-change thresholds like O3=80 PM25=250")

    # args = ap.parse_args()

    # Load data
    # in_path = Path(args.input)
    # out_path = Path(args.output)
    if not os.path.exists(in_path):
        raise FileNotFoundError(f"Input file not found: {in_path}")

    df = pd.read_csv(in_path)
    df.rename(columns={'VALOR': pollutant}, inplace=True)

    # Pollutants to run
    # if pollutants:
    #     pollutants = [p for p in pollutants if p in RECOG_POLLUTANTS]
    # else:
    #     pollutants = [p for p in RECOG_POLLUTANTS if p in df.columns]

    # Assemble limits (apply overrides)
    range_limits = DEFAULT_RANGE_LIMITS.copy()
    #range_limits.update(parse_range_arg(args.range or []))

    roc_limits = DEFAULT_ROC_LIMITS_PER_HOUR.copy()
    #roc_limits.update(parse_scalar_arg(args.roc_limit or [], float))

    neg_limits = DEFAULT_NEGATIVE_LIMITS.copy()
    #neg_limits.update(parse_scalar_arg(args.neg_limit or [], float))

    res_tol = DEFAULT_RESOLUTION_TOL.copy()
    #res_tol.update(parse_scalar_arg(args.resolution or [], float))

    step_limits = DEFAULT_STEP_LIMITS.copy()
    #step_limits.update(parse_scalar_arg(args.step_limit or [], float))

    flatline_n = DEFAULT_FLATLINE_N
    step_window = DEFAULT_STEP_WINDOW
    
    qc_df, summary = run_qc(
        df=df,
        time_col='DATETIME',
        pollutants=pollutant,
        range_limits=range_limits,
        roc_limits_per_hour=roc_limits,
        negative_limits=neg_limits,
        flatline_n=flatline_n,
        resolution_tol=res_tol,
        step_window=step_window,
        step_limits=step_limits,
    )

    # Save outputs
    qc_df.to_csv(out_path, index=False)

    if summary_json:
        with open(summary_json, "w") as f:
            json.dump(summary, f, indent=2)

    # Print a tiny human summary to stdout
    print("QC complete.")
    print(f"- Input:  {in_path}")
    print(f"- Output: {out_path}")
    if summary_json:
        print(f"- Summary JSON: {summary_json}")
    print("- Flags per pollutant:")
    for p in summary:
        total = sum(summary[p].values()) if summary[p] else 0
        print(f"  {p}: {summary[p]} (total flagged points: {total})")


