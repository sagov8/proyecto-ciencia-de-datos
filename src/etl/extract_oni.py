"""Extracción y procesamiento inicial del Índice Oceánico de El Niño (ONI - NOAA CPC)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

ONI_URL = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"
ROOT_DIR = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT_DIR / "data" / "raw"
PROCESSED_DIR = ROOT_DIR / "data" / "processed"

SEAS_TO_MONTH = {
    "DJF": 1,
    "JFM": 2,
    "FMA": 3,
    "MAM": 4,
    "AMJ": 5,
    "MJJ": 6,
    "JJA": 7,
    "JAS": 8,
    "ASO": 9,
    "SON": 10,
    "OND": 11,
    "NDJ": 12,
}


def _flag_persistent_episodes(series: pd.Series, threshold: float, above: bool = True, min_len: int = 5) -> pd.Series:
    """Aplica la regla oficial NOAA: al menos `min_len` trimestres móviles consecutivos superando el umbral."""
    cond = (series >= threshold) if above else (series <= threshold)
    groups = (cond != cond.shift()).cumsum()
    run_lengths = cond.groupby(groups).transform("sum")
    return cond & (run_lengths >= min_len)


def _classify_intensity(anom: float, fase: str) -> str:
    if fase == "Neutro":
        return "Neutro"
    abs_val = abs(anom)
    if abs_val >= 2.0:
        return f"{fase} Muy Fuerte"
    if abs_val >= 1.5:
        return f"{fase} Fuerte"
    if abs_val >= 1.0:
        return f"{fase} Moderado"
    return f"{fase} Débil"


def extract_oni(start_year: int = 2014) -> pd.DataFrame:
    """Descarga, guarda en crudo y procesa el índice ONI desde la NOAA.

    Se conserva desde `start_year=2014` para poder calcular rezagos de hasta 6 meses
    sin perder observaciones en el primer semestre de 2015.
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    resp = requests.get(ONI_URL, timeout=30)
    resp.raise_for_status()

    raw_path = RAW_DIR / "oni.ascii.txt"
    raw_path.write_text(resp.text, encoding="utf-8")

    df = pd.read_csv(raw_path, sep=r"\s+")
    df.columns = [c.strip().upper() for c in df.columns]
    expected = {"SEAS", "YR", "TOTAL", "ANOM"}
    if not expected.issubset(df.columns):
        raise ValueError(f"Columnas inesperadas en oni.ascii.txt: {df.columns.tolist()}")

    df["SEAS"] = df["SEAS"].str.strip().str.upper()
    df["YR"] = pd.to_numeric(df["YR"], errors="coerce").astype("Int64")
    df["TOTAL"] = pd.to_numeric(df["TOTAL"], errors="coerce")
    df["ANOM"] = pd.to_numeric(df["ANOM"], errors="coerce")
    df = df.dropna(subset=["SEAS", "YR", "ANOM"]).copy()

    df["mes"] = df["SEAS"].map(SEAS_TO_MONTH)
    df = df.dropna(subset=["mes"]).copy()
    df["mes"] = df["mes"].astype(int)
    df["anio"] = df["YR"].astype(int)
    df["fecha"] = pd.to_datetime(dict(year=df["anio"], month=df["mes"], day=1))
    df = df.sort_values("fecha").reset_index(drop=True)

    # Clasificación oficial NOAA (5 trimestres móviles consecutivos >= +0.5 o <= -0.5)
    is_nino = _flag_persistent_episodes(df["ANOM"], threshold=0.5, above=True, min_len=5)
    is_nina = _flag_persistent_episodes(df["ANOM"], threshold=-0.5, above=False, min_len=5)

    df["enso_fase"] = "Neutro"
    df.loc[is_nino, "enso_fase"] = "El Niño"
    df.loc[is_nina, "enso_fase"] = "La Niña"
    df["enso_intensidad"] = [
        _classify_intensity(a, f) for a, f in zip(df["ANOM"], df["enso_fase"])
    ]

    df = df.rename(
        columns={
            "SEAS": "trimestre_movil",
            "TOTAL": "sst_total",
            "ANOM": "oni",
        }
    )

    # Filtrar desde start_year manteniendo continuidad para rezagos
    df_filtered = df[df["anio"] >= start_year][
        ["fecha", "anio", "mes", "trimestre_movil", "sst_total", "oni", "enso_fase", "enso_intensidad"]
    ].reset_index(drop=True)

    out_path = PROCESSED_DIR / "oni_mensual.csv"
    df_filtered.to_csv(out_path, index=False)

    meta = {
        "source_url": ONI_URL,
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "total_rows_raw": int(len(df)),
        "filtered_rows": int(len(df_filtered)),
        "min_date": str(df_filtered["fecha"].min().date()),
        "max_date": str(df_filtered["fecha"].max().date()),
        "fase_counts": df_filtered["enso_fase"].value_counts().to_dict(),
    }
    (RAW_DIR / "oni_metadata.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    print("ONI extraído exitosamente:")
    print(json.dumps(meta, indent=2, ensure_ascii=False))
    return df_filtered


if __name__ == "__main__":
    extract_oni()
