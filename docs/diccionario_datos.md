# Diccionario de Datos y Auditoría de Fuentes

**Fecha de consulta:** 2026-11-23 (UTC: `2026-11-24`)  
**Alcance geográfico:** Popayán, Cauca (`Popayán, Plaza de Mercado del Barrio Bolívar`)  
**Periodo de análisis:** Enero 2015 – Septiembre 2026 (cruce efectivo SIPSA–ONI de 141 meses; SIPSA cuenta con datos hasta octubre 2026 y ONI hasta septiembre 2026).

---

## 1. Fuente 1: Precios Mayoristas SIPSA – DANE

- **Recurso principal (`datos.gov.co`):** [SIPSA – Componente de Precios Mayoristas 2013–2024 (`gkqq-k3k5`)](https://www.datos.gov.co/dataset/Sistema-de-Informaci-n-de-Precios-y-Abastecimiento/gkqq-k3k5)
  - Tipo de recurso en `datos.gov.co`: recurso federado (`federated_href`) que enlaza a los 8 paquetes ZIP mensuales oficiales en DANE Microdatos (Catálogo 776, años 2013–2024).
- **Complemento oficial 2025–2026 (`dane.gov.co`):** [Boletín Mensual SIPSA – Series Históricas Precios Mayoristas](https://www.dane.gov.co/index.php/estadisticas-por-tema/agropecuario/sistema-de-informacion-de-precios-sipsa/mayoristas-boletin-mensual-1)
  - Archivos Excel oficiales descubiertos automáticamente: `anex-SIPSA-SerieHistoricaMayorista-2025.xlsx` y `anex-SIPSA-SerieHistoricaMayorista-2026.xlsx`.
- **Volumen descargado (crudo Popayán 2013–2026):** 19,412 filas × 7 columnas (de >666,000 registros nacionales en 2013–2024 + anexos 2025–2026).
- **Datos personales sensibles:** Ninguno (estadísticas agregadas de precios mayoristas por mercado y alimento).

### Hallazgos de calidad detectados en la base cruda
1. **Tres formatos heterogéneos de fecha:** `d/m/yyyy` (2013–2021), `mmm-yy` en español como `ene-22`, `abr-23`, `dic-24` (2022–2024) y timestamp ISO `yyyy-mm-dd HH:MM:SS` (2025–2026).
2. **Formato de precios con separador de miles en 2022–2024:** valores como `' 1.371 '` con espacios y punto como separador de miles colombiano (requiere normalización explícita para evitar interpretarlos como decimales `1.371`).
3. **Inconsistencias de texto y tildes:** `mercado` alterna entre `'Popayán, Plaza de Mercado del Barrio Bolívar'` y `'Popayán, Plaza de mercado del barrio Bolívar'`; `grupo` alterna entre mayúsculas sin tilde (`TUBERCULOS, RAICES Y PLATANOS`) y formato título con tildes (`Tubérculos, Raíces y Plátanos`).
4. **Columna `codigo_cpc` incompleta:** 15,447 valores nulos porque el DANE solo incorporó el código CPC a partir de 2024.

---

## 2. Fuente 2: Índice Oceánico de El Niño (ONI) – NOAA CPC

- **URL oficial:** [https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt](https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt)
- **Entidad:** National Oceanic and Atmospheric Administration – Climate Prediction Center (NOAA CPC).
- **Volumen:** 921 registros históricos (1950–2026); 153 meses conservados desde enero 2014 hasta septiembre 2026 (se incluye 2014 para calcular rezagos climáticos de hasta 6 meses sin perder el primer semestre de 2015).
- **Definición de fase ENSO (criterio oficial NOAA):** Se clasifica como episodio **El Niño** cuando la anomalía ONI es $\ge +0.5\,^\circ\text{C}$ durante al menos 5 trimestres móviles consecutivos, y **La Niña** cuando es $\le -0.5\,^\circ\text{C}$ durante al menos 5 trimestres móviles consecutivos.

---

## 3. Variables del Dataset Depurado (`data/processed/`)

| Variable | Tipo | Unidad / Valores | Descripción |
| :--- | :--- | :--- | :--- |
| `fecha` | `datetime64` | `YYYY-MM-01` | Primer día del mes correspondiente |
| `anio`, `mes` | `int` | `2015–2026`, `1–12` | Año y mes calendario |
| `mercado` | `str` | Texto estandarizado | Plaza mayorista de Popayán |
| `grupo` | `str` | Categoría estandarizada | Grupo de alimento (énfasis en frescos: Frutas, Verduras y Hortalizas, Tubérculos, Raíces y Plátanos) |
| `producto` | `str` | Texto estandarizado | Nombre normalizado del alimento |
| `precio_kg` | `float` | COP / kg | Precio mayorista promedio mensual por kilogramo |
| `indice_base100` | `float` | Base 100 (prom. 2015) | Índice normalizado del precio respecto al promedio del producto en 2015 |
| `var_mensual_pct` | `float` | % | Variación porcentual mes a mes |
| `var_interanual_pct` | `float` | % | Variación porcentual frente al mismo mes del año anterior |
| `oni` | `float` | °C (anomalía SST) | Índice Oceánico de El Niño (trimestre móvil centrado en el mes) |
| `enso_fase` | `str` | `El Niño`, `Neutro`, `La Niña` | Fase ENSO bajo regla oficial NOAA de 5 trimestres consecutivos |
| `enso_intensidad` | `str` | Débil / Moderado / Fuerte / Muy Fuerte | Intensidad de la fase ENSO |
| `oni_lag_1` .. `oni_lag_6` | `float` | °C | Rezagos del índice ONI de 1 a 6 meses |
| `oni_ma_3` | `float` | °C | Media móvil de 3 meses del ONI |
| `mes_sin`, `mes_cos` | `float` | `[-1, 1]` | Codificación cíclica de la estacionalidad mensual |
| `alerta_encarecimiento` | `int` | `0` o `1` | Variable objetivo de clasificación: `1` si la variación supera el percentil 75 histórico |

---

## 4. Limitaciones Conocidas

1. **Solo precios mayoristas (no minoristas):** SIPSA mide precios en plaza mayorista (Barrio Bolívar), que suelen liderar pero no equivalen exactamente al precio final al consumidor.
2. **Desfase de 1 mes al cierre de 2026:** SIPSA cuenta con datos hasta octubre 2026, mientras que el ONI publicado por NOAA cierra en septiembre 2026 (trimestre ASO). El cruce efectivo abarca hasta **septiembre 2026** (141 meses).
3. **Factores exógenos no incluidos:** Los precios en el Cauca también se ven afectados por costos de transporte/combustibles, bloqueos en la Vía Panamericana, precios de fertilizantes, tasa de cambio (TRM) e inflación general. Por ello, los hallazgos describen asociaciones estadísticas y no causalidad aislada.
