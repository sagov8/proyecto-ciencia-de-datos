"""Pruebas automatizadas de calidad de datos, pipeline ETL, modelado y dashboard."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
MODELS = ROOT / "models"


def test_processed_datasets_exist_and_valid():
    canasta = pd.read_csv(PROC / "canasta_fresca_popayan.csv", parse_dates=["fecha"])
    panel = pd.read_parquet(PROC / "popayan_alimentos_frescos_mensual.parquet")
    core = pd.read_csv(PROC / "productos_core_frescos.csv")

    assert len(canasta) >= 140, "Debe cubrir al menos 140 meses (2015–2026)"
    assert canasta["fecha"].is_monotonic_increasing
    assert canasta["fecha"].nunique() == len(canasta), "No deben existir fechas duplicadas en la canasta"
    assert canasta[["fecha", "indice_canasta", "precio_promedio_kg", "oni", "enso_fase"]].isna().sum().sum() == 0
    assert (canasta["precio_promedio_kg"] > 0).all()
    assert canasta["oni"].between(-3.5, 3.5).all()
    assert set(canasta["enso_fase"].unique()).issubset({"El Niño", "Neutro", "La Niña"})
    assert len(core) >= 40, "Debe haber al menos 40 productos frescos core (>=90% cobertura)"
    assert (panel["precio_kg"] > 0).all()


def test_model_split_chronological_and_beats_baseline():
    metrics = json.loads((MODELS / "metrics_summary.json").read_text(encoding="utf-8"))
    preds = pd.read_csv(MODELS / "predictions_test.csv", parse_dates=["fecha"])

    train_end = pd.Timestamp(metrics["train_range"][1])
    test_start = pd.Timestamp(metrics["test_range"][0])
    assert train_end < test_start, "El split debe ser estrictamente cronológico sin fuga temporal"
    assert len(preds) == metrics["test_rows"]

    best_reg = metrics["regression"]["best_model"]
    best_mae = metrics["regression"]["models"][best_reg]["test_mae"]
    base_mae = metrics["regression"]["models"]["Baseline Estacional"]["test_mae"]
    assert best_mae < base_mae, "El modelo ganador debe superar al baseline estacional en MAE"

    best_clf = metrics["classification"]["best_model"]
    auc = metrics["classification"]["models"][best_clf]["test_roc_auc"]
    assert auc is not None and auc > 0.65, "El clasificador de alertas debe tener ROC-AUC > 0.65"


def test_streamlit_dashboard_renders_without_errors():
    at = AppTest.from_file(str(ROOT / "app" / "streamlit_app.py"), default_timeout=30)
    at.run()
    assert not at.exception, f"Errores en Streamlit: {at.exception}"
    assert len(at.tabs) == 4
    assert len(at.metric) >= 8
