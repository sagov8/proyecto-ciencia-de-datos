"""Limpieza, estandarización, auditoría de outliers, cruce SIPSA–ONI e ingeniería de variables."""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT_DIR / "data" / "raw"
PROCESSED_DIR = ROOT_DIR / "data" / "processed"

SPANISH_MONTHS = {
    "ene": 1,
    "feb": 2,
    "mar": 3,
    "abr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "ago": 8,
    "sep": 9,
    "sept": 9,
    "oct": 10,
    "nov": 11,
    "dic": 12,
}

GROUP_CANONICAL = {
    "FRUTAS": "Frutas",
    "VERDURAS Y HORTALIZAS": "Verduras y Hortalizas",
    "TUBERCULOS, RAICES Y PLATANOS": "Tubérculos, Raíces y Plátanos",
    "GRANOS Y CEREALES": "Granos y Cereales",
    "CARNES": "Carnes",
    "LACTEOS Y HUEVOS": "Lácteos y Huevos",
    "PESCADOS": "Pescados",
    "PROCESADOS": "Procesados",
}

FRESH_GROUPS = [
    "Frutas",
    "Verduras y Hortalizas",
    "Tubérculos, Raíces y Plátanos",
]


def _strip_accents(text: str) -> str:
    return "".join(
        ch for ch in unicodedata.normalize("NFKD", str(text)) if not unicodedata.combining(ch)
    )


def parse_sipsa_date(val: Any) -> pd.Timestamp:
    """Parsea los 3 formatos de fecha presentes en SIPSA (d/m/Y, mmm-yy en español, ISO)."""
    if pd.isna(val):
        return pd.NaT
    s = str(val).strip().lower()
    # Formato español mmm-yy (ej. ene-22, abr-24)
    m = re.match(r"^([a-z]{3,4})[-/](\d{2,4})$", s)
    if m:
        mon_str, yr_str = m.group(1), m.group(2)
        month = SPANISH_MONTHS.get(mon_str)
        if month is not None:
            year = int(yr_str)
            if year < 100:
                year += 2000
            return pd.Timestamp(year=year, month=month, day=1)

    # Formato ISO yyyy-mm-dd...
    if re.match(r"^\d{4}-\d{2}-\d{2}", s):
        dt = pd.to_datetime(s, errors="coerce")
        return pd.Timestamp(year=dt.year, month=dt.month, day=1) if pd.notna(dt) else pd.NaT

    # Formato d/m/yyyy (ej. 1/01/2013)
    dt = pd.to_datetime(s, format="%d/%m/%Y", errors="coerce")
    if pd.notna(dt):
        return pd.Timestamp(year=dt.year, month=dt.month, day=1)

    dt = pd.to_datetime(s, dayfirst=True, errors="coerce")
    return pd.Timestamp(year=dt.year, month=dt.month, day=1) if pd.notna(dt) else pd.NaT


def parse_sipsa_price(val: Any) -> float:
    """Convierte precio SIPSA manejando separadores de miles con punto (ej. ' 1.371 ') y decimales."""
    if pd.isna(val):
        return np.nan
    s = str(val).strip().replace("$", "").replace(" ", "")
    if not s:
        return np.nan

    # Caso colombiano con punto de miles y sin decimales: '1.371', '12.450'
    if re.match(r"^\d{1,3}(\.\d{3})+$", s):
        return float(s.replace(".", ""))
    # Caso con punto de miles y coma decimal: '1.371,50'
    if re.match(r"^\d{1,3}(\.\d{3})+,\d+$", s):
        return float(s.replace(".", "").replace(",", "."))
    # Caso solo coma decimal: '1371,5'
    if "," in s and "." not in s:
        return float(s.replace(",", "."))

    try:
        return float(s)
    except ValueError:
        return np.nan


def standardize_group(val: Any) -> str:
    key = re.sub(r"\s+", " ", _strip_accents(str(val)).strip().upper())
    return GROUP_CANONICAL.get(key, str(val).strip())


def standardize_product(val: Any) -> str:
    return re.sub(r"\s+", " ", str(val).strip())


def run_cleaning_pipeline() -> dict[str, Any]:
    """Ejecuta toda la limpieza, cruce con ONI y generación de features para Popayán (2015–2026)."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    raw_sipsa = pd.read_parquet(RAW_DIR / "sipsa_popayan_raw.parquet")
    oni = pd.read_csv(PROCESSED_DIR / "oni_mensual.csv", parse_dates=["fecha"])

    audit: dict[str, Any] = {
        "raw_rows_total_2013_2026": int(len(raw_sipsa)),
        "raw_nulls": raw_sipsa.isna().sum().to_dict(),
    }

    df = raw_sipsa.copy()
    df["fecha"] = df["fecha_raw"].map(parse_sipsa_date)
    df["precio_kg"] = df["precio_raw"].map(parse_sipsa_price)
    df["grupo"] = df["grupo"].map(standardize_group)
    df["producto"] = df["producto"].map(standardize_product)
    df["mercado"] = "Popayán, Plaza de Mercado del Barrio Bolívar"

    audit["unparsed_dates"] = int(df["fecha"].isna().sum())
    audit["unparsed_prices"] = int(df["precio_kg"].isna().sum())
    audit["non_positive_prices"] = int((df["precio_kg"] <= 0).sum())

    # Eliminar filas con fecha o precio inválido o <= 0
    df = df.dropna(subset=["fecha", "precio_kg"]).copy()
    df = df[df["precio_kg"] > 0].copy()

    # Filtrar periodo de estudio >= 2015-01-01
    df["anio"] = df["fecha"].dt.year
    df["mes"] = df["fecha"].dt.month
    df = df[df["anio"] >= 2015].copy()
    audit["rows_2015_2026_all_groups"] = int(len(df))

    # Auditoría y deduplicación por (fecha, grupo, producto)
    dup_mask = df.duplicated(subset=["fecha", "grupo", "producto"], keep=False)
    audit["duplicate_key_rows_before_agg"] = int(dup_mask.sum())
    df = (
        df.groupby(["fecha", "anio", "mes", "mercado", "grupo", "producto"], as_index=False)
        .agg(precio_kg=("precio_kg", "mean"))
        .sort_values(["grupo", "producto", "fecha"])
        .reset_index(drop=True)
    )
    audit["rows_after_dedup_all_groups"] = int(len(df))

    # Marcar si pertenece a alimentos frescos agrícolas de la canasta familiar
    df["es_alimento_fresco"] = df["grupo"].isin(FRESH_GROUPS)

    # Detección de outliers estadísticos (IQR por producto) — se marcan, NO se eliminan picos reales
    q1 = df.groupby("producto")["precio_kg"].transform(lambda s: s.quantile(0.25))
    q3 = df.groupby("producto")["precio_kg"].transform(lambda s: s.quantile(0.75))
    iqr = q3 - q1
    df["es_outlier_iqr"] = (df["precio_kg"] < (q1 - 1.5 * iqr)) | (df["precio_kg"] > (q3 + 1.5 * iqr))
    # Errores extremos de digitación (> 10x mediana del producto o < 0.1x mediana)
    med = df.groupby("producto")["precio_kg"].transform("median")
    extreme_error = (df["precio_kg"] > 10 * med) | (df["precio_kg"] < 0.1 * med)
    audit["extreme_error_rows_removed"] = int(extreme_error.sum())
    audit["statistical_outliers_flagged_kept"] = int(df.loc[~extreme_error, "es_outlier_iqr"].sum())
    df = df.loc[~extreme_error].copy()

    # Calcular rezagos de ONI (antes de filtrar ONI a >= 2015)
    oni = oni.sort_values("fecha").reset_index(drop=True)
    for lag in (1, 2, 3, 4, 6):
        oni[f"oni_lag_{lag}"] = oni["oni"].shift(lag)
    oni["oni_ma_3"] = oni["oni"].rolling(3, min_periods=1).mean()
    oni["oni_diff_1"] = oni["oni"].diff(1)
    oni["oni_diff_3"] = oni["oni"].diff(3)

    # Cruce SIPSA + ONI (inner join para periodo con ambas fuentes: 2015-01 a 2026-09)
    panel = df.merge(
        oni[
            [
                "fecha",
                "trimestre_movil",
                "sst_total",
                "oni",
                "enso_fase",
                "enso_intensidad",
                "oni_lag_1",
                "oni_lag_2",
                "oni_lag_3",
                "oni_lag_4",
                "oni_lag_6",
                "oni_ma_3",
                "oni_diff_1",
                "oni_diff_3",
            ]
        ],
        on="fecha",
        how="inner",
    )

    # Calcular métricas por producto (variación mensual, interanual e índice base 100 = prom. 2015 o primer año)
    panel = panel.sort_values(["producto", "fecha"]).reset_index(drop=True)
    panel["var_mensual_pct"] = panel.groupby("producto")["precio_kg"].pct_change(1) * 100.0
    panel["var_interanual_pct"] = panel.groupby("producto")["precio_kg"].pct_change(12) * 100.0

    # Base 100 por producto (promedio 2015 si tiene datos en 2015, si no promedio de sus primeros 12 meses)
    base_2015 = panel[panel["anio"] == 2015].groupby("producto")["precio_kg"].mean()
    base_fallback = panel.groupby("producto")["precio_kg"].apply(lambda s: s.head(12).mean())
    base_map = base_2015.combine_first(base_fallback)
    panel["precio_base"] = panel["producto"].map(base_map)
    panel["indice_base100"] = (panel["precio_kg"] / panel["precio_base"]) * 100.0

    # Variables cíclicas de estacionalidad
    panel["mes_sin"] = np.sin(2 * np.pi * panel["mes"] / 12.0)
    panel["mes_cos"] = np.cos(2 * np.pi * panel["mes"] / 12.0)

    # Guardar panel completo (todos los grupos) y panel de alimentos frescos
    panel_frescos = panel[panel["es_alimento_fresco"]].copy().reset_index(drop=True)

    # Identificar productos frescos con alta continuidad temporal (>= 90% de meses del periodo)
    total_months = panel_frescos["fecha"].nunique()
    prod_counts = panel_frescos.groupby(["grupo", "producto"])["fecha"].nunique().reset_index(name="meses_con_dato")
    prod_counts["cobertura_pct"] = (prod_counts["meses_con_dato"] / total_months) * 100.0
    core_products = prod_counts[prod_counts["cobertura_pct"] >= 90.0].sort_values(
        ["cobertura_pct", "grupo", "producto"], ascending=[False, True, True]
    )

    # Construir serie mensual agregada de la Canasta Fresca de Popayán (usando productos core >=90% cobertura)
    core_panel = panel_frescos[panel_frescos["producto"].isin(core_products["producto"])].copy()
    canasta = (
        core_panel.groupby(
            [
                "fecha",
                "anio",
                "mes",
                "trimestre_movil",
                "sst_total",
                "oni",
                "enso_fase",
                "enso_intensidad",
                "oni_lag_1",
                "oni_lag_2",
                "oni_lag_3",
                "oni_lag_4",
                "oni_lag_6",
                "oni_ma_3",
                "oni_diff_1",
                "oni_diff_3",
                "mes_sin",
                "mes_cos",
            ],
            as_index=False,
        )
        .agg(
            n_productos=("producto", "nunique"),
            precio_promedio_kg=("precio_kg", "mean"),
            precio_mediana_kg=("precio_kg", "median"),
            indice_canasta=("indice_base100", "mean"),
            indice_canasta_mediana=("indice_base100", "median"),
        )
        .sort_values("fecha")
        .reset_index(drop=True)
    )

    canasta["var_mensual_pct"] = canasta["indice_canasta"].pct_change(1) * 100.0
    canasta["var_interanual_pct"] = canasta["indice_canasta"].pct_change(12) * 100.0
    canasta["indice_lag_1"] = canasta["indice_canasta"].shift(1)
    canasta["indice_lag_3"] = canasta["indice_canasta"].shift(3)
    canasta["indice_lag_12"] = canasta["indice_canasta"].shift(12)
    canasta["var_mensual_lag_1"] = canasta["var_mensual_pct"].shift(1)
    canasta["var_mensual_lag_2"] = canasta["var_mensual_pct"].shift(2)
    canasta["var_mensual_lag_3"] = canasta["var_mensual_pct"].shift(3)
    canasta["tendencia_idx"] = np.arange(len(canasta))

    # Umbral de alerta de encarecimiento acelerado (percentil 75 de variación mensual positiva/alta)
    umbral_alerta_p75 = float(canasta["var_mensual_pct"].dropna().quantile(0.75))
    canasta["alerta_encarecimiento"] = (canasta["var_mensual_pct"] >= umbral_alerta_p75).astype(int)

    # Serie mensual por grupo fresco
    por_grupo = (
        core_panel.groupby(["fecha", "anio", "mes", "grupo", "oni", "enso_fase", "enso_intensidad"], as_index=False)
        .agg(
            n_productos=("producto", "nunique"),
            precio_promedio_kg=("precio_kg", "mean"),
            indice_grupo=("indice_base100", "mean"),
        )
        .sort_values(["grupo", "fecha"])
        .reset_index(drop=True)
    )
    por_grupo["var_mensual_pct"] = por_grupo.groupby("grupo")["indice_grupo"].pct_change(1) * 100.0
    por_grupo["var_interanual_pct"] = por_grupo.groupby("grupo")["indice_grupo"].pct_change(12) * 100.0

    # Guardar todos los archivos procesados
    panel.to_parquet(PROCESSED_DIR / "popayan_todos_grupos_mensual.parquet", index=False)
    panel_frescos.to_parquet(PROCESSED_DIR / "popayan_alimentos_frescos_mensual.parquet", index=False)
    panel_frescos.to_csv(PROCESSED_DIR / "popayan_alimentos_frescos_mensual.csv", index=False)
    canasta.to_csv(PROCESSED_DIR / "canasta_fresca_popayan.csv", index=False)
    por_grupo.to_csv(PROCESSED_DIR / "canasta_por_grupo_popayan.csv", index=False)
    core_products.to_csv(PROCESSED_DIR / "productos_core_frescos.csv", index=False)

    audit.update(
        {
            "merged_date_min": str(canasta["fecha"].min().date()),
            "merged_date_max": str(canasta["fecha"].max().date()),
            "total_months_merged": int(total_months),
            "panel_all_groups_rows": int(len(panel)),
            "panel_frescos_rows": int(len(panel_frescos)),
            "unique_fresh_products_total": int(panel_frescos["producto"].nunique()),
            "core_fresh_products_ge_90pct": int(len(core_products)),
            "core_products_by_group": core_products["grupo"].value_counts().to_dict(),
            "umbral_alerta_var_mensual_p75_pct": round(umbral_alerta_p75, 4),
            "alerta_encarecimiento_counts": canasta["alerta_encarecimiento"].value_counts().to_dict(),
        }
    )

    (PROCESSED_DIR / "cleaning_audit_report.json").write_text(
        json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print("Limpieza y consolidación completadas:")
    print(json.dumps(audit, indent=2, ensure_ascii=False))
    return audit


if __name__ == "__main__":
    run_cleaning_pipeline()
