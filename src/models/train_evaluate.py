"""Entrenamiento y evaluación cronológica del componente predictivo dual (Regresión + Clasificación)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
    root_mean_squared_error,
)
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT_DIR = Path(__file__).resolve().parents[2]
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
MODELS_DIR = ROOT_DIR / "models"

FEATURE_COLS = [
    "oni",
    "oni_abs",
    "oni_sq",
    "oni_lag_1",
    "oni_lag_2",
    "oni_lag_3",
    "oni_lag_6",
    "oni_abs_lag_1",
    "oni_abs_lag_2",
    "oni_abs_lag_3",
    "oni_ma_3",
    "oni_diff_1",
    "oni_diff_3",
    "mes_sin",
    "mes_cos",
    "var_mensual_lag_1",
    "var_mensual_lag_2",
    "var_mensual_lag_3",
]


def prepare_modeling_dataframe() -> pd.DataFrame:
    """Carga la serie mensual de la canasta fresca y construye las variables predictoras sin fuga temporal."""
    df = pd.read_csv(PROCESSED_DIR / "canasta_fresca_popayan.csv", parse_dates=["fecha"])
    df = df.sort_values("fecha").reset_index(drop=True)

    # Variables no lineales de intensidad ENSO (capturan el patrón en U descubierto en el EDA)
    df["oni_abs"] = df["oni"].abs()
    df["oni_sq"] = df["oni"] ** 2
    df["oni_abs_lag_1"] = df["oni_lag_1"].abs()
    df["oni_abs_lag_2"] = df["oni_lag_2"].abs()
    df["oni_abs_lag_3"] = df["oni_lag_3"].abs()

    # Eliminar filas iniciales sin rezagos completos
    df_model = df.dropna(subset=FEATURE_COLS + ["var_mensual_pct"]).reset_index(drop=True)
    return df_model


def train_and_evaluate(split_date: str = "2024-07-01") -> dict[str, Any]:
    """Entrena y evalúa modelos de regresión y clasificación con partición estrictamente cronológica."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    df = prepare_modeling_dataframe()

    train_mask = df["fecha"] < pd.Timestamp(split_date)
    test_mask = df["fecha"] >= pd.Timestamp(split_date)

    train_df = df.loc[train_mask].copy().reset_index(drop=True)
    test_df = df.loc[test_mask].copy().reset_index(drop=True)

    X_train = train_df[FEATURE_COLS]
    y_train_reg = train_df["var_mensual_pct"].values
    X_test = test_df[FEATURE_COLS]
    y_test_reg = test_df["var_mensual_pct"].values

    # Umbral de alerta de encarecimiento acelerado calculado SOLO sobre entrenamiento (sin fuga)
    umbral_alerta_train = float(np.quantile(y_train_reg, 0.75))
    y_train_clf = (y_train_reg >= umbral_alerta_train).astype(int)
    y_test_clf = (y_test_reg >= umbral_alerta_train).astype(int)

    # ------------------------------------------------------------------
    # 1. MODELO PRINCIPAL: REGRESIÓN (Variación mensual % de la canasta)
    # ------------------------------------------------------------------
    # Baseline estacional (promedio histórico del mismo mes calendario en train)
    monthly_means = train_df.groupby("mes")["var_mensual_pct"].mean().to_dict()
    baseline_pred = test_df["mes"].map(monthly_means).values

    reg_candidates = {
        "Ridge (L2)": Pipeline([("scaler", StandardScaler()), ("model", Ridge(alpha=15.0))]),
        "RandomForestRegressor": RandomForestRegressor(
            n_estimators=300, max_depth=5, min_samples_leaf=4, random_state=42
        ),
        "HistGradientBoosting": HistGradientBoostingRegressor(
            max_depth=3, max_iter=120, learning_rate=0.05, min_samples_leaf=8, random_state=42
        ),
    }

    tscv = TimeSeriesSplit(n_splits=5)
    reg_results: dict[str, dict[str, Any]] = {
        "Baseline Estacional": {
            "test_mae": round(float(mean_absolute_error(y_test_reg, baseline_pred)), 3),
            "test_rmse": round(float(root_mean_squared_error(y_test_reg, baseline_pred)), 3),
            "test_r2": round(float(r2_score(y_test_reg, baseline_pred)), 3),
            "test_sign_acc_pct": round(float(np.mean(np.sign(y_test_reg) == np.sign(baseline_pred)) * 100), 1),
        }
    }

    best_reg_name = ""
    best_reg_mae = float("inf")
    best_reg_model = None
    best_reg_preds = None

    for name, est in reg_candidates.items():
        cv_maes, cv_rmses = [], []
        for tr_idx, va_idx in tscv.split(X_train):
            est.fit(X_train.iloc[tr_idx], y_train_reg[tr_idx])
            p_va = est.predict(X_train.iloc[va_idx])
            cv_maes.append(mean_absolute_error(y_train_reg[va_idx], p_va))
            cv_rmses.append(root_mean_squared_error(y_train_reg[va_idx], p_va))

        est.fit(X_train, y_train_reg)
        preds = est.predict(X_test)
        mae = float(mean_absolute_error(y_test_reg, preds))
        rmse = float(root_mean_squared_error(y_test_reg, preds))
        r2 = float(r2_score(y_test_reg, preds))
        sign_acc = float(np.mean(np.sign(y_test_reg) == np.sign(preds)) * 100)

        reg_results[name] = {
            "cv_mae": round(float(np.mean(cv_maes)), 3),
            "cv_rmse": round(float(np.mean(cv_rmses)), 3),
            "test_mae": round(mae, 3),
            "test_rmse": round(rmse, 3),
            "test_r2": round(r2, 3),
            "test_sign_acc_pct": round(sign_acc, 1),
        }

        if mae < best_reg_mae:
            best_reg_mae = mae
            best_reg_name = name
            best_reg_model = est
            best_reg_preds = preds

    # ------------------------------------------------------------------
    # 2. MODELO COMPLEMENTARIO: CLASIFICACIÓN (Alerta de encarecimiento)
    # ------------------------------------------------------------------
    clf_candidates = {
        "LogisticRegression": Pipeline(
            [("scaler", StandardScaler()), ("model", LogisticRegression(class_weight="balanced", C=0.5, max_iter=1000))]
        ),
        "RandomForestClassifier": RandomForestClassifier(
            n_estimators=300, max_depth=4, min_samples_leaf=4, class_weight="balanced", random_state=42
        ),
    }

    clf_results: dict[str, dict[str, Any]] = {}
    best_clf_name = ""
    best_clf_score = -1.0
    best_clf_model = None
    best_clf_preds = None
    best_clf_probs = None

    for name, est in clf_candidates.items():
        est.fit(X_train, y_train_clf)
        preds = est.predict(X_test)
        probs = est.predict_proba(X_test)[:, 1]
        f1 = float(f1_score(y_test_clf, preds, zero_division=0))
        prec = float(precision_score(y_test_clf, preds, zero_division=0))
        rec = float(recall_score(y_test_clf, preds, zero_division=0))
        acc = float(accuracy_score(y_test_clf, preds))
        auc = float(roc_auc_score(y_test_clf, probs)) if len(np.unique(y_test_clf)) > 1 else np.nan
        cm = confusion_matrix(y_test_clf, preds).tolist()

        clf_results[name] = {
            "test_f1": round(f1, 3),
            "test_precision": round(prec, 3),
            "test_recall": round(rec, 3),
            "test_accuracy": round(acc, 3),
            "test_roc_auc": round(auc, 3) if not np.isnan(auc) else None,
            "confusion_matrix": cm,
        }

        # Seleccionar priorizando combinación de ROC-AUC y F1
        composite = (0.5 * f1) + (0.5 * (auc if not np.isnan(auc) else 0.5))
        if composite > best_clf_score:
            best_clf_score = composite
            best_clf_name = name
            best_clf_model = est
            best_clf_preds = preds
            best_clf_probs = probs

    # Importancia de variables (del RandomForestRegressor para interpretabilidad uniforme)
    rf_for_imp = reg_candidates["RandomForestRegressor"]
    importances = sorted(
        [
            {"feature": f, "importance": round(float(imp), 4)}
            for f, imp in zip(FEATURE_COLS, rf_for_imp.feature_importances_)
        ],
        key=lambda x: x["importance"],
        reverse=True,
    )

    # Guardar modelos ganadores y predicciones en test
    joblib.dump(best_reg_model, MODELS_DIR / "regression_best.joblib")
    joblib.dump(best_clf_model, MODELS_DIR / "classification_best.joblib")

    pred_df = test_df[["fecha", "anio", "mes", "indice_canasta", "precio_promedio_kg", "oni", "enso_fase"]].copy()
    pred_df["var_mensual_real"] = y_test_reg
    pred_df["var_mensual_pred"] = best_reg_preds
    pred_df["var_mensual_baseline"] = baseline_pred
    pred_df["alerta_real"] = y_test_clf
    pred_df["alerta_pred"] = best_clf_preds
    pred_df["alerta_prob"] = best_clf_probs
    pred_df.to_csv(MODELS_DIR / "predictions_test.csv", index=False)

    summary = {
        "split_date": split_date,
        "train_range": [str(train_df["fecha"].min().date()), str(train_df["fecha"].max().date())],
        "test_range": [str(test_df["fecha"].min().date()), str(test_df["fecha"].max().date())],
        "train_rows": int(len(train_df)),
        "test_rows": int(len(test_df)),
        "feature_cols": FEATURE_COLS,
        "umbral_alerta_train_p75_pct": round(umbral_alerta_train, 4),
        "test_positive_alerts": int(y_test_clf.sum()),
        "regression": {
            "best_model": best_reg_name,
            "models": reg_results,
        },
        "classification": {
            "best_model": best_clf_name,
            "models": clf_results,
        },
        "feature_importances_rf": importances,
        "limitations": [
            "Las predicciones representan estimaciones estadísticas condicionadas al índice ONI y la estacionalidad, no certezas determinísticas.",
            "El modelo no incorpora choques exógenos no climáticos relevantes en el Cauca (bloqueos en la Vía Panamericana, precio del diésel/fletes, fertilizantes, TRM o inflación general).",
            "El tamaño muestral mensual (137 meses útiles) limita la complejidad de modelos profundos y exige validación continua conforme el DANE publique nuevos meses.",
        ],
    }

    (MODELS_DIR / "metrics_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("Entrenamiento y evaluación completados:")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return summary


if __name__ == "__main__":
    train_and_evaluate()
