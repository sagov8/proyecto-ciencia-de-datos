# Impacto del Fenómeno de El Niño (Índice ONI) en los Precios Mayoristas de Alimentos Frescos en Popayán (2015–2026)

**Asignatura:** Electiva III – Introducción a la Ciencia de Datos | **Docente:** Carlos E. Ruiz  
**Institución:** Institución Universitaria Colegio Mayor del Cauca  
**Formato:** Informe breve ejecutivo (diseñado para extensión máxima de 3 páginas sin anexos)

---

## 1. Objetivo y Pregunta de Investigación

**Objetivo:** Analizar mediante estadística descriptiva, estadística inferencial básica y modelado predictivo la relación entre el Fenómeno de El Niño (medido con el Índice Oceánico de El Niño, ONI) y la tendencia, estacionalidad y probabilidad de alzas fuertes de los alimentos frescos en Popayán (Cauca) entre enero de 2015 y septiembre de 2026.

**Pregunta problema:** *¿Cómo afecta la intensidad del Fenómeno de El Niño (medida a través del índice ONI) a la tendencia y estacionalidad de los precios de los alimentos en Popayán entre 2015 y 2026?*

---

## 2. Fuentes de Datos y Metodología

### Fuentes oficiales
1. **Precios Mayoristas SIPSA – DANE:**
   - **2013–2024:** Recurso federado en `datos.gov.co` (`gkqq-k3k5`), que enlaza a 8 paquetes ZIP mensuales oficiales de microdatos del DANE (Catálogo 776).
   - **2025–2026:** Anexos Excel oficiales (`anex-SIPSA-SerieHistoricaMayorista-2025.xlsx` y `2026.xlsx`) descargados del portal del boletín mensual SIPSA del DANE.
   - **Mercado analizado:** `Popayán, Plaza de Mercado del Barrio Bolívar` (19,412 registros crudos descargados; 0 datos personales sensibles).
2. **Índice Oceánico de El Niño (ONI) – NOAA CPC:** Archivo oficial `oni.ascii.txt` (153 meses conservados desde enero de 2014 hasta septiembre de 2026).

### Preparación y limpieza de datos
- **Homologación de formatos:** Se unificaron 3 formatos distintos de fecha (`d/m/yyyy` en 2013–2021, `mmm-yy` en español en 2022–2024 e ISO en 2025–2026) y se corrigió el punto separador de miles (` 1.371 `) en 2022–2024, logrando **0 errores de parseo** y **0 duplicados** por `(fecha, grupo, producto)`.
- **Canasta fresca core:** De los 53 alimentos frescos registrados en Popayán (6,575 registros), se seleccionaron los **44 productos** con cobertura mensual $\ge 90\%$ en la muestra de **$n = 141$ meses continuos** (`2015-01` a `2026-09`): 22 Frutas, 15 Verduras y Hortalizas, y 7 Tubérculos, Raíces y Plátanos.
- **Atípicos:** Se identificaron 211 valores atípicos estadísticos y **se conservaron** por corresponder a picos reales de escasez/clima (0 errores extremos de digitación $>10\times$ mediana).
- **Clasificación ENSO (regla oficial NOAA):** Episodio **El Niño** ($\ge +0.5\,^\circ\text{C}$) o **La Niña** ($\le -0.5\,^\circ\text{C}$) durante al menos 5 trimestres móviles consecutivos. Se construyó el Índice Canasta Fresca (Base 100 = promedio 2015) y la marca de **mes con alza fuerte** cuando la variación mensual supera el percentil 75 histórico (`>= +4.43 %`).

---

## 3. Principales Indicadores Descriptivos

| Indicador (Canasta Fresca Popayán, $n = 141$ meses) | Valor |
| :--- | :---: |
| Cobertura temporal efectiva (cruce SIPSA–ONI) | Ene 2015 – Sep 2026 ($n = 141$) |
| Índice Canasta Fresca (Ene 2015 → Sep 2026) | `91.0` → `261.6` (**+187.5 %** acumulado) |
| Precio promedio mayorista (mín. / mediana / máx.) | \$1,714 / \$2,521 / \$4,803 COP/kg |
| Variación mensual promedio / mediana | `+0.93 %` / `+0.27 %` |
| Variación anual promedio / mediana | `+8.97 %` / `+6.68 %` |
| Umbral de mes con alza fuerte (Percentil 75 mensual) | `>= +4.43 %/mes` (35 meses de 141) |

### Comparación de Conteos, Proporciones y Promedios por Fase Climática

| Fase Climática | Tamaño muestra ($n$) | Meses con alza fuerte | Proporción / Probabilidad | Var. Mensual Promedio | Var. Anual Mediana |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **El Niño** | 49 | 18 | **36.7 %** | **+1.61 %** | **+9.54 %** |
| **Neutro** | 62 | 6 | **9.7 %** | **-0.20 %** | **+1.92 %** |
| **La Niña** | 30 | 11 | **36.7 %** | **+2.20 %** | **+15.69 %** |

---

## 4. Hallazgos Sustentados (Estadística Descriptiva y 4 Pruebas de Hipótesis No Obvias)

1. **Encarecimiento acumulado (+187.5 %) y estacionalidad por mes:** Entre 2015 y 2026 ($n=141$), el índice pasó de 91.0 a 261.6 (liderado por Granadilla `+252.6 %`, Maracuyá `+198.6 %` y Habichuela `+190.7 %`). Al agrupar los 11 años por mes, **enero** subió en el **100 % de los años** (`+6.77 %` prom.) y **marzo** en el **91.7 %** (`+4.26 %`); en contraste, **noviembre** (`-2.42 %`) y **abril** (`-2.15 %`) registran 0 % de alzas fuertes.
2. **Umbral de intensidad de El Niño (P1) y Efecto "doble golpe" (P2):**
   - **P1 (Umbral $\ge +1.5\,^\circ\text{C}$):** El Niño **Fuerte/Muy Fuerte** presenta **`58.8 %`** (`10/17`) de meses con alza fuerte frente a **`25.0 %`** (`8/32`) en El Niño **Débil/Moderado** (**$z = 2.338, p = 0.0097 < 0.05$ → se rechaza $H_0$**). El riesgo crítico se dispara al superar $+1.5\,^\circ\text{C}$.
   - **P2 (Estacionalidad × El Niño):** Cuando El Niño coincide con **Ene–Mar**, la probabilidad de alza fuerte llega al **`60.0 %`** (`9/15`, vs. `27.3 %` en Ene–Mar Neutro, $p = 0.049$), es decir, **10 veces más riesgo** que en **Abr–Dic Neutro** (`5.9 %`, `3/51`; frente a `26.5 %` en Abr–Dic El Niño, $p = 0.0038$).
3. **Mito refutado (P3: El Niño vs. La Niña) y Grupo de control natural (P4: Frescos vs. Procesados y Carnes):**
   - **P3:** Al comparar **El Niño (`36.7 %`, 18/49)** frente a **La Niña (`36.7 %`, 11/30)**, **$z = 0.006, p = 0.995 > 0.05$ → no se rechaza $H_0$**: ambos extremos climáticos golpean con igual frecuencia a Popayán (y en Tubérculos/Plátanos el salto significativo ocurre en La Niña, $p = 0.036$).
   - **P4 (Control natural):** Mientras en **Alimentos Frescos** El Niño cuadruplica las alzas (`36.7 %` vs. `9.7 %`, $z = 3.439, p = 0.00029$), en **Procesados** (`20.4 %` vs. `21.0 %`, $p = 0.529$) y **Carnes** (`18.4 %` vs. `24.2 %`, $p = 0.771$) **no se rechaza $H_0$**, confirmando que el impacto se concentra en productos agrícolas frescos y no en inflación generalizada.

---

## 5. Componente Predictivo (Valor Agregado)

Separando los datos en orden cronológico (Entrenamiento: `2015-05` a `2024-06`, $n=110$ meses; Prueba: `2024-07` a `2026-09`, $n=27$ meses):
- **Modelo de Regresión (variación % mensual):** Logró un error promedio **`MAE = 2.81 %`** y **`RMSE = 3.67 %`**, superando al promedio histórico mensual (`MAE = 3.15 %`, `RMSE = 3.88 %`; 11 % menos error). El valor del ONI de 3 meses atrás resultó ser el predictor con mayor peso, coherente con los tiempos de cosecha.
- **Modelo de Clasificación (alerta de alza fuerte):** Alcanzó **`81.5 %` de exactitud**, **`66.7 %` de precisión** y **`F1 = 0.44`** sobre los 27 meses de prueba.

---

## 6. Limitaciones y Conclusiones

**Limitaciones (Observación vs. Causalidad):** (1) Rechazar $H_0$ demuestra una asociación estadística sólida, pero **no implica que el clima sea la única causa**: factores externos como bloqueos en la Vía Panamericana, costo del transporte/combustibles, fertilizantes e inflación general también inciden en Popayán. (2) SIPSA mide precios mayoristas, no minoristas. (3) Las predicciones del tablero tienen un margen de error (`±2.81 %`) y deben leerse como escenarios probables, nunca como certezas.

**Conclusiones:** A partir de datos oficiales depurados ($n=141$ meses), se evidenció con estadística descriptiva e inferencial que en Popayán los meses de **enero a marzo** y los episodios de **El Niño y La Niña** elevan significativamente la probabilidad de alzas fuertes en alimentos frescos frente a meses climáticamente neutros ($36.7\%$ vs. $9.7\%$, $p < 0.001$). El dashboard interactivo en Streamlit permite consultar estos indicadores, verificar la prueba de hipótesis y simular escenarios de riesgo de forma clara y reproducible.
