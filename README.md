# Impacto del Fenómeno de El Niño (ONI) en los Precios de Alimentos Frescos en Popayán (2015–2026)

Proyecto final de **Electiva III – Introducción a la Ciencia de Datos** (Institución Universitaria Colegio Mayor del Cauca).

## Pregunta de Investigación
> *¿Cómo afecta la intensidad del Fenómeno de El Niño (medida a través del índice ONI) a la tendencia y estacionalidad de los precios de los alimentos en Popayán entre 2015 y 2026?*

## Estructura del Repositorio

```text
├── app/
│   └── streamlit_app.py                     # Dashboard interactivo (Streamlit + Plotly)
├── data/
│   ├── raw/                                 # Respaldo de datos crudos descargados y metadatos
│   └── processed/                           # Bases limpias (canasta mensual, panel frescos, auditoría)
├── docs/
│   ├── objetivo.md                          # Temática, problemática y fuentes
│   └── diccionario_datos.md                 # Diccionario de variables, fuentes y limitaciones
├── models/                                  # Modelos serializados (.joblib), predicciones y métricas
├── notebooks/
│   ├── 01_extraccion_y_limpieza.ipynb       # Extracción, auditoría y limpieza de datos
│   ├── 02_analisis_descriptivo_eda.ipynb    # Estadística descriptiva y pruebas de hipótesis
│   └── 03_modelado_predictivo.ipynb         # Modelado predictivo (regresión y clasificación)
├── src/
│   ├── etl/
│   │   ├── extract_oni.py                   # Extractor oficial NOAA CPC (oni.ascii.txt)
│   │   ├── extract_sipsa.py                 # Extractor híbrido datos.gov.co (gkqq-k3k5) + DANE 2025–2026
│   │   └── clean_merge.py                   # Limpieza, estandarización, atípicos, cruce y variables
│   └── models/
│       └── train_evaluate.py                # Entrenamiento y evaluación cronológica
├── tests/
│   └── test_pipeline.py                     # Pruebas automatizadas (calidad de datos, modelos, dashboard)
├── pyproject.toml                           # Dependencias gestionadas con uv
├── requirements.txt                         # Dependencias para despliegue en Streamlit Community Cloud
└── uv.lock                                  # Archivo de bloqueo de dependencias (uv)
```

## Ejecución Rápida (con `uv`)

```bash
# 1. Instalar dependencias
uv sync

# 2. (Opcional) Re-ejecutar extracción en vivo desde NOAA, datos.gov.co y DANE
uv run python src/etl/extract_oni.py
uv run python src/etl/extract_sipsa.py

# 3. Ejecutar limpieza, cruce SIPSA–ONI y generación de variables
uv run python src/etl/clean_merge.py

# 4. Entrenar y evaluar modelos predictivos
uv run python src/models/train_evaluate.py

# 5. Ejecutar pruebas automatizadas
uv run pytest

# 6. Lanzar el dashboard interactivo localmente
uv run streamlit run app/streamlit_app.py
```

## Resumen de Resultados Clave
- **Tamaño de muestra:** $n = 141$ meses continuos (`2015-01` a `2026-09`), 44 alimentos frescos core (cobertura $\ge 90\%$) en la Plaza de Mercado del Barrio Bolívar (Popayán).
- **Estacionalidad por mes:** **Enero** subió en el **100 % de los años** (`+6.77 %` prom.) y **marzo** en el **91.7 %** (`+4.26 %`); **noviembre** (`-2.42 %`) y **abril** (`-2.15 %`) registran las mayores bajas.
- **Cuatro pruebas de hipótesis ($\alpha = 0.05$):**
  1. **Umbral de intensidad:** El Niño Fuerte ($\ge +1.5\,^\circ\text{C}$) dispara las alzas a **`58.8 %`** vs. **`25.0 %`** en Débil/Moderado ($z = 2.338, p = 0.0097$).
  2. **Doble golpe Estacionalidad × El Niño:** **Ene–Mar con El Niño** alcanza **`60.0 %`** (**10×** frente al **`5.9 %`** de Abr–Dic Neutro).
  3. **El Niño vs. La Niña:** Empate estadístico (`36.7 %` vs. `36.7 %`, $p = 0.995$, no se rechaza $H_0$).
  4. **Control natural (Frescos vs. Procesados y Carnes):** En Frescos sí hay diferencia ($p = 0.00029$), mientras en Procesados ($p = 0.529$) y Carnes ($p = 0.771$) no se rechaza $H_0$.
- **Modelado predictivo (prueba cronológica 2024-07 a 2026-09):** Regresión con **`MAE = 2.81 %`** (`RMSE = 3.67 %`, -11 % error vs. promedio mensual) y clasificación de alerta con **`81.5 %` de exactitud** (`F1 = 0.44`).
