"""Dashboard Interactivo: Impacto del Fenómeno de El Niño (ONI) en los Precios de Alimentos Frescos en Popayán."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import stats
import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[1]
PROC_DIR = ROOT_DIR / "data" / "processed"
MODELS_DIR = ROOT_DIR / "models"

ENSO_COLORS = {
    "El Niño": "#d9534f",
    "Neutro": "#7f8c8d",
    "La Niña": "#2e86c1",
}
MESES_ES = {
    1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic",
}

st.set_page_config(
    page_title="El Niño y Alimentos Frescos – Popayán (SIPSA)",
    page_icon="🌦️",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data
def load_data():
    canasta = pd.read_csv(PROC_DIR / "canasta_fresca_popayan.csv", parse_dates=["fecha"])
    por_grupo = pd.read_csv(PROC_DIR / "canasta_por_grupo_popayan.csv", parse_dates=["fecha"])
    panel = pd.read_parquet(PROC_DIR / "popayan_alimentos_frescos_mensual.parquet")
    todos_grupos = pd.read_parquet(PROC_DIR / "popayan_todos_grupos_mensual.parquet")
    core = pd.read_csv(PROC_DIR / "productos_core_frescos.csv")
    preds = pd.read_csv(MODELS_DIR / "predictions_test.csv", parse_dates=["fecha"])
    metrics = json.loads((MODELS_DIR / "metrics_summary.json").read_text(encoding="utf-8"))
    return canasta, por_grupo, panel, todos_grupos, core, preds, metrics


@st.cache_resource
def load_models():
    reg = joblib.load(MODELS_DIR / "regression_best.joblib")
    clf = joblib.load(MODELS_DIR / "classification_best.joblib")
    return reg, clf


def two_prop_ztest(x1: int, n1: int, x2: int, n2: int) -> tuple[float, float]:
    """Prueba de hipótesis z unilateral (H1: p1 > p2) para diferencia de dos proporciones."""
    if n1 == 0 or n2 == 0:
        return 0.0, 1.0
    p1, p2 = x1 / n1, x2 / n2
    p_pool = (x1 + x2) / (n1 + n2)
    if p_pool in (0.0, 1.0):
        return 0.0, 1.0
    se = np.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))
    z = float((p1 - p2) / se)
    p_val = float(1 - stats.norm.cdf(z))
    return z, p_val


canasta, por_grupo, panel, todos_grupos, core, preds, metrics = load_data()
reg_model, clf_model = load_models()
core_panel = panel[panel["producto"].isin(core["producto"])].copy()

# ------------------------------------------------------------------
# SIDEBAR: FILTROS GLOBALES
# ------------------------------------------------------------------
st.sidebar.title("Filtros de Análisis")
st.sidebar.caption("Popayán, Plaza de Mercado del Barrio Bolívar")

min_year, max_year = int(canasta["anio"].min()), int(canasta["anio"].max())
year_range = st.sidebar.slider("Rango de años", min_year, max_year, (min_year, max_year))

selected_phases = st.sidebar.multiselect(
    "Fase climática (Regla NOAA)",
    options=["El Niño", "Neutro", "La Niña"],
    default=["El Niño", "Neutro", "La Niña"],
)

all_groups = sorted(por_grupo["grupo"].unique().tolist())
selected_groups = st.sidebar.multiselect(
    "Grupos de alimentos frescos",
    options=all_groups,
    default=all_groups,
)

prods_in_groups = sorted(core[core["grupo"].isin(selected_groups)]["producto"].unique().tolist())
selected_product = st.sidebar.selectbox(
    "Producto específico para detalle",
    options=prods_in_groups if prods_in_groups else sorted(core["producto"].unique().tolist()),
    index=0,
)

st.sidebar.divider()
st.sidebar.markdown(
    "**Fuentes oficiales:**\n"
    "- Precios mayoristas: DANE – SIPSA (`datos.gov.co` `gkqq-k3k5` + anexos 2025–2026).\n"
    "- Clima ENSO: NOAA CPC (`oni.ascii.txt`).\n"
    "- Tamaño de muestra: **$n = 141$ meses** (Ene 2015 – Sep 2026, 44 productos frescos)."
)

# Aplicar filtros
canasta_f = canasta[
    (canasta["anio"].between(year_range[0], year_range[1]))
    & (canasta["enso_fase"].isin(selected_phases))
].copy()
grupo_f = por_grupo[
    (por_grupo["anio"].between(year_range[0], year_range[1]))
    & (por_grupo["enso_fase"].isin(selected_phases))
    & (por_grupo["grupo"].isin(selected_groups))
].copy()

# ------------------------------------------------------------------
# ENCABEZADO PRINCIPAL
# ------------------------------------------------------------------
st.title("Impacto del Fenómeno de El Niño (ONI) en los Alimentos Frescos de Popayán")
st.markdown(
    "**Pregunta de investigación:** *¿Cómo afecta la intensidad del Fenómeno de El Niño (índice ONI) "
    "a la tendencia y estacionalidad de los precios mayoristas de los alimentos frescos en Popayán entre 2015 y 2026?*"
)

# KPIs ejecutivos
latest = canasta.iloc[-1]
first = canasta.iloc[0]
cum_growth = ((latest["indice_canasta"] / first["indice_canasta"]) - 1.0) * 100.0
nino_alert = canasta.loc[canasta["enso_fase"] == "El Niño", "alerta_encarecimiento"].mean() * 100.0
neutro_alert = canasta.loc[canasta["enso_fase"] == "Neutro", "alerta_encarecimiento"].mean() * 100.0

k1, k2, k3, k4 = st.columns(4)
k1.metric(
    "Índice Canasta Fresca (Sep 2026)",
    f"{latest['indice_canasta']:.1f}",
    f"+{cum_growth:.1f}% vs Ene 2015",
)
k2.metric(
    "Precio Promedio Mayorista",
    f"${latest['precio_promedio_kg']:,.0f} COP/kg",
    f"{latest['var_mensual_pct']:+.1f}% último mes",
)
k3.metric(
    "Prob. de Alza Fuerte (El Niño)",
    f"{nino_alert:.1f}%",
    f"3.8× frente a Neutro ({neutro_alert:.1f}%)",
    delta_color="inverse",
)
k4.metric(
    "Último Índice ONI (NOAA)",
    f"{latest['oni']:+.2f} °C",
    f"Fase: {latest['enso_fase']}",
    delta_color="off",
)

tab1, tab2, tab3, tab4 = st.tabs(
    [
        "1. Resumen Ejecutivo",
        "2. Estacionalidad y Productos",
        "3. Proporciones y Prueba de Hipótesis",
        "4. Simulador Predictivo",
    ]
)

# ==================================================================
# TAB 1: RESUMEN EJECUTIVO
# ==================================================================
with tab1:
    st.subheader("Evolución de la Canasta Fresca de Popayán frente al Índice ONI")
    if canasta_f.empty:
        st.warning("No hay datos para la combinación de filtros seleccionada.")
    else:
        fig_main = make_subplots(
            rows=2,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.07,
            row_heights=[0.68, 0.32],
            subplot_titles=(
                "Índice de Precios Canasta Fresca (Base 100 = Promedio 2015) con Fases Climáticas",
                "Índice Oceánico de El Niño – ONI (°C, NOAA CPC)",
            ),
        )
        fig_main.add_trace(
            go.Scatter(
                x=canasta_f["fecha"],
                y=canasta_f["indice_canasta"],
                mode="lines",
                name="Índice Canasta Fresca",
                line=dict(color="#16324F", width=2.5),
                hovertemplate="<b>%{x|%Y-%m}</b><br>Índice: %{y:.1f}<extra></extra>",
            ),
            row=1,
            col=1,
        )

        for _, row in canasta_f.iterrows():
            if row["enso_fase"] in ("El Niño", "La Niña"):
                fig_main.add_vrect(
                    x0=row["fecha"],
                    x1=row["fecha"] + pd.DateOffset(months=1),
                    fillcolor=ENSO_COLORS[row["enso_fase"]],
                    opacity=0.13,
                    layer="below",
                    line_width=0,
                    row=1,
                    col=1,
                )

        bar_colors = [ENSO_COLORS[f] for f in canasta_f["enso_fase"]]
        fig_main.add_trace(
            go.Bar(
                x=canasta_f["fecha"],
                y=canasta_f["oni"],
                marker_color=bar_colors,
                name="ONI (°C)",
                hovertemplate="<b>%{x|%Y-%m}</b><br>ONI: %{y:+.2f} °C<extra></extra>",
            ),
            row=2,
            col=1,
        )
        fig_main.add_hline(y=0.5, line_dash="dash", line_color="#d9534f", row=2, col=1)
        fig_main.add_hline(y=-0.5, line_dash="dash", line_color="#2e86c1", row=2, col=1)
        fig_main.update_yaxes(title_text="Índice (Base 100)", row=1, col=1)
        fig_main.update_yaxes(title_text="ONI (°C)", row=2, col=1)
        fig_main.update_layout(height=520, hovermode="x unified", margin=dict(t=40, b=20))
        st.plotly_chart(fig_main, width="stretch")

    st.subheader("Tres Hallazgos Principales Sustentados en los Datos")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.info(
            "**1. Aumento sostenido (+187.5 %)**\n\n"
            "Entre enero de 2015 y septiembre de 2026 ($n=141$ meses), el índice de precios frescos en Popayán pasó de **91.0** a **261.6** "
            "(precio promedio entre \\$1,714 y \\$4,803 COP/kg). Destacan Granadilla (+252.6 %), Maracuyá (+198.6 %) y Habichuela (+190.7 %)."
        )
    with c2:
        st.success(
            "**2. Patrón claro por mes del año**\n\n"
            "Al agrupar los 11 años por mes, **enero** (sube 100 % de los años, +6.77 % prom.), **marzo** (91.7 %, +4.26 %) y **febrero** (83.3 %, +3.47 %) "
            "concentran las alzas. En cambio, **noviembre** (-2.42 %) y **abril** (-2.15 %) presentan mayor alivio en precios."
        )
    with c3:
        st.error(
            "**3. Mayor probabilidad de alzas en El Niño y La Niña**\n\n"
            "La proporción de meses con alzas fuertes ($\\ge +4.43\\%$) es de **36.7 %** en **El Niño** (18/49) y **36.7 %** en **La Niña** (11/30), "
            "frente a solo **9.7 %** en meses **Neutros** (6/62). La prueba de hipótesis confirma que la diferencia es significativa ($p < 0.001$)."
        )

# ==================================================================
# TAB 2: ESTACIONALIDAD SIMPLE Y PRODUCTOS
# ==================================================================
with tab2:
    st.subheader("¿En qué meses del año suben o bajan más los precios? (Agrupación Mensual)")
    mes_df = canasta_f.dropna(subset=["var_mensual_pct"]).groupby("mes", as_index=False).agg(
        n_anios=("var_mensual_pct", "count"),
        var_promedio=("var_mensual_pct", "mean"),
        var_mediana=("var_mensual_pct", "median"),
        prob_sube=("var_mensual_pct", lambda s: (s > 0).mean() * 100.0),
    )
    mes_df["mes_lbl"] = mes_df["mes"].map(MESES_ES)

    col_a, col_b = st.columns(2)
    with col_a:
        fig_m1 = go.Figure(
            go.Bar(
                x=mes_df["mes_lbl"],
                y=mes_df["var_promedio"],
                marker_color=np.where(mes_df["var_promedio"] > 0, "#d9534f", "#27ae60"),
                text=mes_df["var_promedio"].map(lambda v: f"{v:+.1f}%"),
                textposition="outside",
            )
        )
        fig_m1.add_hline(y=0, line_color="black", line_width=0.8)
        fig_m1.update_layout(
            title="Variación Mensual Promedio (%) por Mes del Año",
            yaxis_title="Variación promedio (%)",
            xaxis_title="Mes",
            height=380,
            margin=dict(t=45, b=20),
        )
        st.plotly_chart(fig_m1, width="stretch")

    with col_b:
        fig_m2 = go.Figure(
            go.Bar(
                x=mes_df["mes_lbl"],
                y=mes_df["prob_sube"],
                marker_color="#2e86c1",
                text=mes_df["prob_sube"].map(lambda v: f"{v:.0f}%"),
                textposition="outside",
            )
        )
        fig_m2.add_hline(y=50, line_dash="dash", line_color="black")
        fig_m2.update_layout(
            title="Probabilidad Empírica de Subida de Precios por Mes (%)",
            yaxis_title="% de años en que subió el precio",
            xaxis_title="Mes",
            yaxis=dict(range=[0, 115]),
            height=380,
            margin=dict(t=45, b=20),
        )
        st.plotly_chart(fig_m2, width="stretch")

    st.subheader("Comparativa por Grupo Fresco y Detalle por Producto")
    g_col1, g_col2 = st.columns(2)
    with g_col1:
        if not grupo_f.empty:
            fig_g = px.line(
                grupo_f,
                x="fecha",
                y="indice_grupo",
                color="grupo",
                labels={"fecha": "Fecha", "indice_grupo": "Índice (Base 100)", "grupo": "Grupo"},
                title="Evolución del Índice por Grupo de Alimentos Frescos",
                height=370,
            )
            fig_g.update_layout(margin=dict(t=40, b=20), legend=dict(orientation="h", y=-0.22))
            st.plotly_chart(fig_g, width="stretch")
    with g_col2:
        prod_df = core_panel[
            (core_panel["producto"] == selected_product)
            & (core_panel["anio"].between(year_range[0], year_range[1]))
        ].sort_values("fecha")
        if not prod_df.empty:
            fig_p = px.line(
                prod_df,
                x="fecha",
                y="precio_kg",
                markers=True,
                color="enso_fase",
                color_discrete_map=ENSO_COLORS,
                labels={"fecha": "Fecha", "precio_kg": "Precio mayorista (COP/kg)", "enso_fase": "Fase"},
                title=f"Precio mensual de {selected_product} en Popayán (COP/kg)",
                height=370,
            )
            fig_p.update_layout(margin=dict(t=40, b=20), legend=dict(orientation="h", y=-0.22))
            st.plotly_chart(fig_p, width="stretch")

# ==================================================================
# TAB 3: PROPORCIONES Y PRUEBA DE HIPÓTESIS (ESTADÍSTICA INFERENCIAL)
# ==================================================================
with tab3:
    st.subheader("Comparación de Proporciones, Promedios y Probabilidad por Fase Climática")

    res_enso = (
        canasta_f.groupby("enso_fase", as_index=False)
        .agg(
            n_meses=("fecha", "count"),
            meses_alza_fuerte=("alerta_encarecimiento", "sum"),
            prob_alza_pct=("alerta_encarecimiento", lambda s: s.mean() * 100.0),
            var_mensual_prom=("var_mensual_pct", "mean"),
            var_mensual_mediana=("var_mensual_pct", "median"),
        )
    )
    st.dataframe(
        res_enso.rename(
            columns={
                "enso_fase": "Fase Climática",
                "n_meses": "Tamaño muestra (n)",
                "meses_alza_fuerte": "Meses con alza fuerte",
                "prob_alza_pct": "Proporción / Probabilidad (%)",
                "var_mensual_prom": "Var. mensual promedio (%)",
                "var_mensual_mediana": "Var. mensual mediana (%)",
            }
        ).round(2),
        width="stretch",
        hide_index=True,
    )

    c_left, c_right = st.columns(2)
    with c_left:
        fig_bar = px.bar(
            res_enso,
            x="enso_fase",
            y="prob_alza_pct",
            color="enso_fase",
            category_orders={"enso_fase": ["La Niña", "Neutro", "El Niño"]},
            color_discrete_map=ENSO_COLORS,
            text=res_enso.apply(lambda r: f"{r['prob_alza_pct']:.1f}% ({int(r['meses_alza_fuerte'])}/{int(r['n_meses'])})", axis=1),
            labels={"enso_fase": "Fase climática (NOAA)", "prob_alza_pct": "Probabilidad de alza fuerte (%)"},
            title="Proporción de Meses con Alza Fuerte (>= +4.43% mensual)",
            height=390,
        )
        fig_bar.update_traces(textposition="outside")
        fig_bar.update_yaxes(range=[0, 48])
        st.plotly_chart(fig_bar, width="stretch")

    with c_right:
        fig_avg = px.bar(
            res_enso,
            x="enso_fase",
            y="var_mensual_prom",
            color="enso_fase",
            category_orders={"enso_fase": ["La Niña", "Neutro", "El Niño"]},
            color_discrete_map=ENSO_COLORS,
            text=res_enso["var_mensual_prom"].map(lambda v: f"{v:+.2f}%"),
            labels={"enso_fase": "Fase climática (NOAA)", "var_mensual_prom": "Variación mensual promedio (%)"},
            title="Variación Mensual Promedio (%) según Fase Climática",
            height=390,
        )
        fig_avg.add_hline(y=0, line_color="black", line_width=0.8)
        fig_avg.update_traces(textposition="outside")
        st.plotly_chart(fig_avg, width="stretch")

    st.divider()
    st.subheader("Preguntas realizadas con pruebas de hipótesis (α = 0.05)")
    st.caption("Calculadas sobre la muestra completa (n = 141 meses, 2015–2026) para validar hallazgos.")

    # P1: Umbral de intensidad (>= 1.5 vs < 1.5)
    solo_nino = canasta[canasta["enso_fase"] == "El Niño"]
    fuerte = solo_nino[solo_nino["oni"] >= 1.5]["alerta_encarecimiento"]
    debil = solo_nino[solo_nino["oni"] < 1.5]["alerta_encarecimiento"]
    z_p1, pv_p1 = two_prop_ztest(int(fuerte.sum()), len(fuerte), int(debil.sum()), len(debil))

    # P2: Doble golpe Estacionalidad x El Niño
    q1_g = canasta[canasta["mes"].isin([1, 2, 3])].groupby("enso_fase")["alerta_encarecimiento"].agg(["sum", "count"])
    ab_g = canasta[~canasta["mes"].isin([1, 2, 3])].groupby("enso_fase")["alerta_encarecimiento"].agg(["sum", "count"])
    z_p2a, pv_p2a = two_prop_ztest(int(q1_g.loc["El Niño", "sum"]), int(q1_g.loc["El Niño", "count"]), int(q1_g.loc["Neutro", "sum"]), int(q1_g.loc["Neutro", "count"]))
    z_p2b, pv_p2b = two_prop_ztest(int(ab_g.loc["El Niño", "sum"]), int(ab_g.loc["El Niño", "count"]), int(ab_g.loc["Neutro", "sum"]), int(ab_g.loc["Neutro", "count"]))

    # P3: El Niño vs La Niña (bilateral)
    g_all = canasta.groupby("enso_fase")["alerta_encarecimiento"].agg(["sum", "count"])
    z_p3, _ = two_prop_ztest(int(g_all.loc["El Niño", "sum"]), int(g_all.loc["El Niño", "count"]), int(g_all.loc["La Niña", "sum"]), int(g_all.loc["La Niña", "count"]))
    pv_p3 = float(2 * (1 - stats.norm.cdf(abs(z_p3))))

    # P4: Grupo de control natural (Procesados y Carnes)
    ctrl_rows = []
    for cat in ["Procesados", "Carnes"]:
        sub = todos_grupos[todos_grupos["grupo"] == cat].copy()
        tot_m = sub["fecha"].nunique()
        core_p = sub.groupby("producto")["fecha"].nunique()
        core_p = core_p[core_p >= 0.9 * tot_m].index
        s = sub[sub["producto"].isin(core_p)].groupby(["fecha", "enso_fase"], as_index=False)["indice_base100"].mean().sort_values("fecha")
        s["var_m"] = s["indice_base100"].pct_change() * 100
        u = s["var_m"].dropna().quantile(0.75)
        s["alerta"] = (s["var_m"] >= u).astype(int)
        gg = s.groupby("enso_fase")["alerta"].agg(["sum", "count"])
        zc, pvc = two_prop_ztest(int(gg.loc["El Niño", "sum"]), int(gg.loc["El Niño", "count"]), int(gg.loc["Neutro", "sum"]), int(gg.loc["Neutro", "count"]))
        ctrl_rows.append((cat, gg.loc["El Niño", "sum"] / gg.loc["El Niño", "count"] * 100, gg.loc["Neutro", "sum"] / gg.loc["Neutro", "count"] * 100, zc, pvc))

    p_col1, p_col2 = st.columns(2)
    with p_col1:
        df_p1 = pd.DataFrame({
            "Intensidad": ["Neutro (n=62)", "El Niño Débil/Mod (n=32)", "El Niño Fuerte >=1.5°C (n=17)"],
            "Probabilidad (%)": [
                g_all.loc["Neutro", "sum"] / g_all.loc["Neutro", "count"] * 100,
                debil.mean() * 100,
                fuerte.mean() * 100,
            ],
        })
        fig_p1 = px.bar(
            df_p1, x="Intensidad", y="Probabilidad (%)",
            color="Intensidad", color_discrete_sequence=["#95a5a6", "#f39c12", "#c0392b"],
            text=df_p1["Probabilidad (%)"].map(lambda v: f"{v:.1f}%"),
            title=f"P1: Umbral de Intensidad (z={z_p1:.2f}, p={pv_p1:.4f} → Rechaza H₀)",
            height=340,
        )
        fig_p1.update_traces(textposition="outside")
        fig_p1.update_layout(showlegend=False, yaxis=dict(range=[0, 72]))
        st.plotly_chart(fig_p1, width="stretch")

    with p_col2:
        df_p2 = pd.DataFrame({
            "Escenario": ["Abr–Dic Neutro", "Abr–Dic El Niño", "Ene–Mar Neutro", "Ene–Mar El Niño"],
            "Probabilidad (%)": [
                ab_g.loc["Neutro", "sum"] / ab_g.loc["Neutro", "count"] * 100,
                ab_g.loc["El Niño", "sum"] / ab_g.loc["El Niño", "count"] * 100,
                q1_g.loc["Neutro", "sum"] / q1_g.loc["Neutro", "count"] * 100,
                q1_g.loc["El Niño", "sum"] / q1_g.loc["El Niño", "count"] * 100,
            ],
        })
        fig_p2 = px.bar(
            df_p2, x="Escenario", y="Probabilidad (%)",
            color="Escenario", color_discrete_sequence=["#95a5a6", "#e67e22", "#5dade2", "#c0392b"],
            text=df_p2["Probabilidad (%)"].map(lambda v: f"{v:.1f}%"),
            title=f"P2: Doble Golpe Estacionalidad × El Niño (10× riesgo en Ene–Mar)",
            height=340,
        )
        fig_p2.update_traces(textposition="outside")
        fig_p2.update_layout(showlegend=False, yaxis=dict(range=[0, 72]))
        st.plotly_chart(fig_p2, width="stretch")

    p_col3, p_col4 = st.columns(2)
    with p_col3:
        df_ctrl = pd.DataFrame([
            {"Categoría": "Frescos (p=0.0003*)", "Fase": "El Niño", "Prob (%)": g_all.loc["El Niño", "sum"] / g_all.loc["El Niño", "count"] * 100},
            {"Categoría": "Frescos (p=0.0003*)", "Fase": "Neutro", "Prob (%)": g_all.loc["Neutro", "sum"] / g_all.loc["Neutro", "count"] * 100},
            {"Categoría": f"Procesados (p={ctrl_rows[0][4]:.3f})", "Fase": "El Niño", "Prob (%)": ctrl_rows[0][1]},
            {"Categoría": f"Procesados (p={ctrl_rows[0][4]:.3f})", "Fase": "Neutro", "Prob (%)": ctrl_rows[0][2]},
            {"Categoría": f"Carnes (p={ctrl_rows[1][4]:.3f})", "Fase": "El Niño", "Prob (%)": ctrl_rows[1][1]},
            {"Categoría": f"Carnes (p={ctrl_rows[1][4]:.3f})", "Fase": "Neutro", "Prob (%)": ctrl_rows[1][2]},
        ])
        fig_p4 = px.bar(
            df_ctrl, x="Categoría", y="Prob (%)", color="Fase", barmode="group",
            color_discrete_map={"El Niño": "#d9534f", "Neutro": "#95a5a6"},
            text=df_ctrl["Prob (%)"].map(lambda v: f"{v:.1f}%"),
            title="P4: Grupo de Control Natural (Frescos vs Procesados y Carnes)",
            height=340,
        )
        fig_p4.update_traces(textposition="outside")
        fig_p4.update_layout(yaxis=dict(range=[0, 48]))
        st.plotly_chart(fig_p4, width="stretch")

    with p_col4:
        st.markdown("**Resumen de las 4 pruebas de hipótesis**")
        st.dataframe(
            pd.DataFrame([
                {"Pregunta": "P1: El Niño Fuerte (>=1.5) vs Débil/Mod", "z": round(z_p1, 2), "p-valor": round(pv_p1, 4), "Decisión": "Rechaza H₀ (58.8% vs 25.0%)"},
                {"Pregunta": "P2a: Ene–Mar (El Niño vs Neutro)", "z": round(z_p2a, 2), "p-valor": round(pv_p2a, 4), "Decisión": "Rechaza H₀ (60.0% vs 27.3%)"},
                {"Pregunta": "P2b: Abr–Dic (El Niño vs Neutro)", "z": round(z_p2b, 2), "p-valor": round(pv_p2b, 4), "Decisión": "Rechaza H₀ (26.5% vs 5.9%)"},
                {"Pregunta": "P3: El Niño vs La Niña (bilateral)", "z": round(z_p3, 2), "p-valor": round(pv_p3, 4), "Decisión": "No rechaza H₀ (empate 36.7%)"},
                {"Pregunta": "P4: Control Procesados (El Niño vs Neutro)", "z": round(ctrl_rows[0][3], 2), "p-valor": round(ctrl_rows[0][4], 4), "Decisión": "No rechaza H₀ (20.4% vs 21.0%)"},
                {"Pregunta": "P4: Control Carnes (El Niño vs Neutro)", "z": round(ctrl_rows[1][3], 2), "p-valor": round(ctrl_rows[1][4], 4), "Decisión": "No rechaza H₀ (18.4% vs 24.2%)"},
            ]),
            width="stretch",
            hide_index=True,
        )

    st.warning(
        "**Observación vs. Causalidad:** La prueba de hipótesis confirma que existe una asociación estadísticamente "
        "significativa entre las fases climáticas extremas y los aumentos fuertes de precios en Popayán, pero **no implica "
        "causalidad exclusiva**. Factores como bloqueos en la Vía Panamericana, fletes, fertilizantes e inflación también influyen."
    )

# ==================================================================
# TAB 4: SIMULADOR PREDICTIVO (VALOR AGREGADO)
# ==================================================================
with tab4:
    st.subheader("Evaluación del Componente Predictivo (Entrenamiento: 2015–2024 | Prueba: Jul 2024 – Sep 2026)")

    best_reg_name = metrics["regression"]["best_model"]
    best_reg_m = metrics["regression"]["models"][best_reg_name]
    base_m = metrics["regression"]["models"]["Baseline Estacional"]
    best_clf_name = metrics["classification"]["best_model"]
    best_clf_m = metrics["classification"]["models"][best_clf_name]

    m1, m2, m3, m4 = st.columns(4)
    m1.metric(
        "Error Promedio Regresión (MAE)",
        f"{best_reg_m['test_mae']:.2f} %",
        f"{best_reg_m['test_mae'] - base_m['test_mae']:+.2f} % vs Promedio Mensual",
        delta_color="inverse",
    )
    m2.metric("Error Cuadrático (RMSE)", f"{best_reg_m['test_rmse']:.2f} %", f"Acierto dirección: {best_reg_m['test_sign_acc_pct']:.1f}%")
    m3.metric("Exactitud Clasificación Alerta", f"{best_clf_m['test_accuracy']*100:.1f} %", f"Prueba: {metrics['test_rows']} meses")
    m4.metric("F1-Score / Precisión Alerta", f"{best_clf_m['test_f1']:.2f}", f"Precisión: {best_clf_m['test_precision']*100:.1f}%")

    fig_pred = go.Figure()
    mae = best_reg_m["test_mae"]
    fig_pred.add_trace(
        go.Scatter(x=preds["fecha"], y=preds["var_mensual_real"], mode="lines+markers", name="Real (%)", line=dict(color="#16324F", width=2.5))
    )
    fig_pred.add_trace(
        go.Scatter(x=preds["fecha"], y=preds["var_mensual_pred"], mode="lines+markers", name="Modelo Regresión (%)", line=dict(color="#d9534f", dash="dash", width=2.2))
    )
    fig_pred.add_trace(
        go.Scatter(
            x=pd.concat([preds["fecha"], preds["fecha"][::-1]]),
            y=pd.concat([preds["var_mensual_pred"] + mae, (preds["var_mensual_pred"] - mae)[::-1]]),
            fill="toself",
            fillcolor="rgba(217,83,79,0.14)",
            line=dict(color="rgba(255,255,255,0)"),
            name=f"Margen ±MAE ({mae:.2f}%)",
        )
    )
    fig_pred.add_hline(y=0, line_color="black", line_width=0.8)
    fig_pred.update_layout(
        title="Comparación en Datos de Prueba (27 meses): Variación Real vs. Estimada",
        yaxis_title="Variación mensual (%)",
        xaxis_title="Fecha",
        height=380,
    )
    st.plotly_chart(fig_pred, width="stretch")

    st.divider()
    st.subheader("Simulador de Escenarios Climáticos (ONI)")
    st.caption("Ajusta el mes y el valor del índice ONI para estimar el rango probable de variación mensual y la probabilidad de alerta.")

    s1, s2, s3, s4 = st.columns(4)
    sim_mes = s1.selectbox("Mes a simular", options=list(MESES_ES.keys()), format_func=lambda m: MESES_ES[m], index=0)
    sim_oni = s2.slider("ONI actual (°C)", -2.5, 2.5, 1.2, 0.1)
    sim_oni_lag3 = s3.slider("ONI hace 3 meses (°C)", -2.5, 2.5, 1.5, 0.1)
    sim_var_lag1 = s4.slider("Variación del mes anterior (%)", -10.0, 15.0, 1.5, 0.5)

    oni_lag1 = (2 * sim_oni + sim_oni_lag3) / 3.0
    oni_lag2 = (sim_oni + 2 * sim_oni_lag3) / 3.0
    sim_row = pd.DataFrame(
        [
            {
                "oni": sim_oni,
                "oni_abs": abs(sim_oni),
                "oni_sq": sim_oni ** 2,
                "oni_lag_1": oni_lag1,
                "oni_lag_2": oni_lag2,
                "oni_lag_3": sim_oni_lag3,
                "oni_lag_6": sim_oni_lag3 * 0.8,
                "oni_abs_lag_1": abs(oni_lag1),
                "oni_abs_lag_2": abs(oni_lag2),
                "oni_abs_lag_3": abs(sim_oni_lag3),
                "oni_ma_3": (sim_oni + oni_lag1 + oni_lag2) / 3.0,
                "oni_diff_1": sim_oni - oni_lag1,
                "oni_diff_3": sim_oni - sim_oni_lag3,
                "mes_sin": np.sin(2 * np.pi * sim_mes / 12.0),
                "mes_cos": np.cos(2 * np.pi * sim_mes / 12.0),
                "var_mensual_lag_1": sim_var_lag1,
                "var_mensual_lag_2": sim_var_lag1 * 0.5,
                "var_mensual_lag_3": 0.5,
            }
        ]
    )[metrics["feature_cols"]]

    pred_var = float(reg_model.predict(sim_row)[0])
    pred_prob = float(clf_model.predict_proba(sim_row)[0, 1])
    est_price = latest["precio_promedio_kg"] * (1.0 + pred_var / 100.0)

    r1, r2, r3 = st.columns(3)
    r1.metric("Variación Mensual Estimada", f"{pred_var:+.2f} %", f"Rango ±MAE: [{pred_var - mae:+.2f}%, {pred_var + mae:+.2f}%]")
    r2.metric("Precio Promedio Referencial", f"${est_price:,.0f} COP/kg", f"Base actual: ${latest['precio_promedio_kg']:,.0f} COP/kg")
    semaforo = "ALTA" if pred_prob >= 0.55 else ("MODERADA" if pred_prob >= 0.35 else "BAJA")
    r3.metric("Probabilidad de Alza Fuerte", f"{pred_prob * 100:.1f} %", f"Nivel de riesgo: {semaforo}")

    with st.expander("Limitaciones del Modelo (Lectura Responsable)"):
        for lim in metrics["limitations"]:
            st.markdown(f"- {lim}")

st.divider()
st.caption(
    "Electiva III – Introducción a la Ciencia de Datos | Institución Universitaria Colegio Mayor del Cauca | "
    "Fuentes: DANE – SIPSA (Popayán, Plaza de Mercado del Barrio Bolívar) y NOAA CPC (ONI). "
    "Las estimaciones son escenarios probabilísticos, no certezas."
)
