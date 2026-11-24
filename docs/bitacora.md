# Bitácora Paso a Paso – Proyecto Final Electiva III

**Proyecto:** Modelado predictivo del impacto del Fenómeno de El Niño (índice ONI) en el encarecimiento acelerado de los alimentos frescos de la canasta familiar en Popayán, Cauca (2015–2026).

---

## Fase 0: Configuración del Proyecto y Planificación

### Decisiones tomadas
1. **Conversión de guía académica:** Se transcribió [Guia_Proyecto_Final_Electiva_III.docx.pdf](Guia_Proyecto_Final_Electiva_III.docx.pdf) a [guia_proyecto_final.md](guia_proyecto_final.md) para consulta directa y trazabilidad de cada criterio de la rúbrica.
2. **Estrategia de fuentes (Enfoque Híbrido):**
   - Fuente principal de precios mayoristas: API Socrata de `datos.gov.co` (`gkqq-k3k5`, SIPSA – DANE).
   - Fuente climática: índice ONI oficial de la NOAA (`oni.ascii.txt`).
   - Contingencia temporal: validar la cobertura real 2015–2026 en `gkqq-k3k5` y, si los años 2025–2026 no están incluidos, complementar con anexos oficiales SIPSA del DANE o documentar el corte oficial disponible.
3. **Arquitectura híbrida:** Proyecto modular en Python (`src/`) gestionado con `uv` + notebooks reproducibles compatibles con Google Colab (`notebooks/`).
4. **Dashboard interactivo:** `Streamlit + Plotly` (`app/streamlit_app.py`) por experiencia previa, integración nativa del simulador predictivo y despliegue gratuito en Streamlit Community Cloud.
5. **Componente predictivo dual:** Regresión temporal (principal) para variación/índice de precios mensuales + Clasificación binaria (complementaria) para alerta de encarecimiento acelerado.

### Estructura creada
- `src/etl/`: extracción, limpieza, consolidación y generación de variables.
- `src/models/`: entrenamiento, validación temporal y evaluación de modelos.
- `notebooks/`: notebooks reproducibles para Colab/Jupyter.
- `app/`: dashboard interactivo Streamlit + Plotly.
- `data/raw/` y `data/processed/`: datos originales y depurados.
- `models/`: modelos serializados (`.joblib`) y resumen de métricas (`.json`).
- `tests/`: pruebas automatizadas de calidad de datos y pipeline.
- `docs/`: guía, objetivo, diccionario de datos, bitácora, informe final, guion de sustentación y capturas.

---

## Fase 1: Selección, Extracción y Auditoría de Datos

### Hallazgos clave de la extracción
1. **NOAA ONI (`src/etl/extract_oni.py`):** Descarga directa de `oni.ascii.txt` (921 filas históricas). Se conservaron **153 meses** (`2014-01` a `2026-09`) con distribución: 71 meses Neutro, 52 El Niño y 30 La Niña (regla oficial NOAA de 5 trimestres consecutivos).
2. **SIPSA `datos.gov.co` (`gkqq-k3k5`):** Al consultar los metadatos Socrata se verificó que `gkqq-k3k5` es un recurso federado (`federated_href`) que apunta a 8 archivos ZIP de microdatos mensuales del DANE (2013–2024).
3. **Complemento oficial 2025–2026 (`dane.gov.co`):** Mediante web scraping (`BeautifulSoup`) sobre el portal del boletín mensual SIPSA del DANE se descubrieron e ingirieron los anexos oficiales `anex-SIPSA-SerieHistoricaMayorista-2025.xlsx` y `2026.xlsx`, logrando cubrir el periodo completo **2015–2026** (19,412 registros crudos de Popayán).
4. **Auditoría de calidad previa a limpieza:** Se documentaron en `docs/diccionario_datos.md` 3 formatos distintos de fecha, separadores de miles con punto (` 1.371 `) en 2022–2024, inconsistencias de mayúsculas/tildes en `grupo` y `mercado`, y 15,447 nulos en `codigo_cpc` (introducido desde 2024).

---

## Fase 2: Preparación, Limpieza e Ingeniería de Variables

### Decisiones y resultados (`src/etl/clean_merge.py`)
- **Parseo de fechas y precios:** 0 errores de parseo en fechas (3 formatos unificados) y 0 precios inválidos (corregido el punto separador de miles en 2022–2024).
- **Consolidación 2015–2026:** 16,687 registros en todos los grupos (0 duplicados por llave `fecha-grupo-producto`), de los cuales **6,575 registros** corresponden a **53 alimentos frescos** cruzados con el índice ONI en **141 meses continuos** (`2015-01` a `2026-09`).
- **Canasta Core Fresca:** Para evitar distorsiones por productos discontinuados, se seleccionaron los **44 alimentos frescos** con cobertura mensual $\ge 90\%$ (22 Frutas, 15 Verduras y Hortalizas, 7 Tubérculos, Raíces y Plátanos).
- **Atípicos (IQR):** Se marcaron 211 observaciones atípicas estadísticas y **se conservaron** por reflejar choques climáticos y de oferta reales; se verificaron 0 errores extremos de digitación (>10x o <0.1x mediana).
- **Ingeniería de variables:** Índice base 100 (referencia 2015), variaciones mensual e interanual, rezagos climáticos `oni_lag_1..6`, media móvil `oni_ma_3`, variables cíclicas `mes_sin/mes_cos`, y etiqueta binaria `alerta_encarecimiento` (percentil 75 de variación mensual = **+4.43 %**, generando 35 meses en alerta y 106 normales).
- **Evidencia reproducible:** Notebook [01_extraccion_y_limpieza.ipynb](../notebooks/01_extraccion_y_limpieza.ipynb) ejecutado y verificado.

---

## Fase 3: Análisis Descriptivo e Inferencial Básico (EDA)

### Ajuste metodológico al nivel académico del curso
Para alinear todas las visualizaciones, el dashboard, el informe y las diapositivas con los temas vistos en clase (estadística descriptiva + inferencial básica: tamaño de muestra, proporciones, probabilidad y prueba de hipótesis), se reemplazaron técnicas avanzadas (descomposición STL y mapas de calor de rezagos) por herramientas directas y explicables:
1. **Tendencia y productos ($n = 141$ meses):** El índice pasó de `91.0` (ene-2015) a `261.6` (sep-2026, **+187.5 %**), con precios promedio entre \$1,714 y \$4,803 COP/kg. Top aumentos: Granadilla (+252.6 %), Maracuyá (+198.6 %), Habichuela (+190.7 %), Piña manzana (+186.8 %) y Aguacate papelillo (+185.9 %).
2. **Estacionalidad simple por mes del año:** Agrupando los 11 años por mes calendario, **enero** subió el **100 % de los años** (`+6.77 %` prom.), **marzo** el **91.7 %** (`+4.26 %`) y **febrero** el **83.3 %** (`+3.47 %`); mientras que **noviembre** (`-2.42 %`, 0 % alertas) y **abril** (`-2.15 %`, 0 % alertas) muestran las mayores bajas.
3. **Proporciones y 4 Pruebas de Hipótesis No Obvias ($\alpha = 0.05$):**
   - **Base (Frescos El Niño vs. Neutro):** $18/49 = \mathbf{36.7\%}$ vs. $6/62 = \mathbf{9.7\%}$ ($z = 3.439, p = 0.00029 < 0.05$ → se rechaza $H_0$).
   - **P1 (Umbral de intensidad $\ge +1.5\,^\circ\text{C}$):** El Niño Fuerte (`58.8 %`, 10/17) vs. Débil/Moderado (`25.0 %`, 8/32) → $z = 2.338, p = 0.0097 < 0.05$ (se rechaza $H_0$).
   - **P2 (Doble golpe Estacionalidad × El Niño):** Ene–Mar El Niño (`60.0 %`, 9/15) vs. Ene–Mar Neutro (`27.3 %`, 3/11, $p = 0.049$) y Abr–Dic El Niño (`26.5 %`, 9/34) vs. Abr–Dic Neutro (`5.9 %`, 3/51, $p = 0.0038$) → **10× más riesgo** en Ene–Mar El Niño vs. Abr–Dic Neutro.
   - **P3 (Mito El Niño vs. La Niña):** `36.7 %` (18/49) vs. `36.7 %` (11/30) → $z = 0.006, p = 0.995 > 0.05$ (no se rechaza $H_0$; ambos extremos afectan con igual frecuencia).
   - **P4 (Grupo de control natural):** Procesados (`20.4 %` vs. `21.0 %`, $p = 0.529$) y Carnes (`18.4 %` vs. `24.2 %`, $p = 0.771$) no muestran diferencia significativa en El Niño, aislando el efecto sobre los productos agrícolas frescos.
4. **Rigor causal:** Se diferencia explícitamente asociación estadística de causalidad exclusiva (factores externos: Vía Panamericana, fletes, fertilizantes e inflación).

---

## Fase 4: Componente Predictivo Dual (Valor Agregado)

### Resultados (`src/models/train_evaluate.py` y `notebooks/03_modelado_predictivo.ipynb`)
- **Partición temporal estricta (sin fuga de datos):** Entrenamiento `2015-05` a `2024-06` (110 meses) y Prueba `2024-07` a `2026-09` (27 meses).
- **Regresión (Principal – Variación % mensual):**
  - `Baseline Estacional`: `MAE = 3.152 %`, `RMSE = 3.877 %`.
  - **`Ridge (L2)` (ganador):** **`MAE = 2.805 %`** (-11.0 % de error frente al baseline), **`RMSE = 3.674 %`**, acierto direccional `66.7 %`.
  - Variables más importantes en Random Forest: `oni_lag_3` (25.1 %), `oni_abs_lag_2` (8.5 %) y `oni_lag_6` (8.5 %), confirmando el efecto rezagado del ciclo agrícola y la no linealidad de `|ONI|`.
- **Clasificación (Complementario – Alerta de encarecimiento acelerado $\ge +4.65\%$):**
  - **`RandomForestClassifier` (ganador):** **`Accuracy = 81.5 %`**, **`ROC-AUC = 0.746`**, **`Precision = 66.7 %`**, `F1 = 0.444`.
  - `LogisticRegression`: `Accuracy = 74.1 %`, `ROC-AUC = 0.698`, `F1 = 0.462`, `Recall = 50.0 %`.
- **Artefactos guardados:** `models/regression_best.joblib`, `models/classification_best.joblib`, `models/predictions_test.csv` y `models/metrics_summary.json`.

---

## Fase 5: Dashboard Interactivo (Streamlit + Plotly)

- Se construyó [app/streamlit_app.py](../app/streamlit_app.py) con filtros globales (rango de años, fase ENSO, grupos frescos y producto específico) y 4 pestañas:
  1. **Resumen Ejecutivo:** KPIs clave, serie dual Canasta Fresca vs. ONI con bandas climáticas y síntesis de hallazgos.
  2. **Tendencia y Estacionalidad:** descomposición STL interactiva, perfil estacional mensual, evolución por grupo y detalle en `COP/kg` por producto.
  3. **Impacto ENSO y Rezagos:** boxplots por fase, frecuencia de alertas (patrón en U) y mapas de calor de correlación cruzada (`ONI` vs. `|ONI|`).
  4. **Simulador Predictivo Dual:** desempeño real vs. predicho en prueba + simulador en vivo con rango `±MAE`, precio referencial y semáforo probabilístico de alerta.
- Se generó [requirements.txt](../requirements.txt) listo para despliegue gratuito en Streamlit Community Cloud.

---

## Fase 6: Pruebas Automatizadas y Entregables de Socialización

- **Suite de verificación:** [tests/test_pipeline.py](../tests/test_pipeline.py) valida la integridad de `data/processed/`, el split estrictamente cronológico sin fuga temporal, la mejora sobre el baseline estacional y el renderizado sin errores del dashboard con `streamlit.testing.v1.AppTest`.
- **Entregables académicos:** [informe_final.md](informe_final.md) (máx. 3 páginas sin anexos), [guion_sustentacion.md](guion_sustentacion.md) (10–12 minutos), [sustentacion_canva_editable.pptx](sustentacion_canva_editable.pptx), diseño nativo en **Canva** (`DAHbyormBaU`: https://canva.link/sige5gsku645lae) y [README.md](../README.md).





