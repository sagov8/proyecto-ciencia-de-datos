# Guion de Sustentación (10 – 12 minutos)

**Proyecto:** Impacto del Fenómeno de El Niño (ONI) en los Precios Mayoristas de Alimentos Frescos en Popayán (2015–2026)  
**Enfoque expositivo:** Lenguaje claro de estadística descriptiva + estadística inferencial básica (tamaño de muestra $n$, proporciones, probabilidad y prueba de hipótesis).  
**Formato:** Presentación editable en Canva ([Abrir diseño en Canva](https://canva.link/sige5gsku645lae), ID `DAHbyormBaU`) / respaldo local [sustentacion_canva_editable.pptx](sustentacion_canva_editable.pptx) + demostración en vivo del dashboard Streamlit (~11 minutos totales).

---

## Distribución de Tiempos y Diapositivas

### Bloque 1: Contextualización del Proyecto (2 min | Diapositivas 1–2)
- **Diapositiva 1 – Portada y Problemática (1 min):**
  - Presentar título, equipo, asignatura y pregunta de investigación: *¿Cómo afecta la intensidad del Fenómeno de El Niño (ONI) a la tendencia y estacionalidad de los precios en Popayán (2015–2026)?*
- **Diapositiva 2 – Fuentes Oficiales y Tamaño de Muestra (1 min):**
  - **SIPSA – DANE:** `datos.gov.co` (`gkqq-k3k5`, 2013–2024) + anexos Excel oficiales 2025–2026 de `dane.gov.co` (19,412 registros crudos de la Plaza del Barrio Bolívar).
  - **NOAA CPC (`oni.ascii.txt`):** Índice ONI y regla oficial de 5 trimestres consecutivos.
  - **Tamaño de muestra final:** **$n = 141$ meses continuos** (`2015-01` a `2026-09`) y **44 alimentos frescos** con cobertura $\ge 90\%$.

### Bloque 2: Preparación y Limpieza de Datos (2 min | Diapositivas 3–4)
- **Diapositiva 3 – Auditoría de Calidad (1 min):**
  - Problemas reales corregidos: 3 formatos distintos de fecha (`1/01/2018`, `ene-22`, `2025-01-01`), separador de miles con punto (` 1.371 `) en 2022–2024, diferencias de tildes/mayúsculas en `grupo` y `mercado`.
  - Resultado: 0 errores de parseo, 0 duplicados.
- **Diapositiva 4 – Decisiones Justificadas e Indicadores Base (1 min):**
  - Conservamos 211 valores atípicos porque son picos reales de escasez/clima (0 errores de digitación).
  - Construimos el Índice Base 100 (referencia 2015), la variación porcentual mensual y la definición de **mes con alza fuerte** (percentil 75 = `>= +4.43 %`).

### Bloque 3: Análisis Descriptivo e Inferencial apoyado en el Dashboard (3.5 min | Diapositivas 5–7 + Demo)
- **Diapositiva 5 – Hallazgo 1: Tendencia (+187.5 %) y Productos que Más Subieron (1 min):**
  - Mostrar **Pestaña 1 del Dashboard**: de `91.0` a `261.6` (`$1,714` a `$4,803 COP/kg`). Top productos: Granadilla (`+252.6 %`), Maracuyá (`+198.6 %`), Habichuela (`+190.7 %`).
- **Diapositiva 6 – Hallazgo 2: Estacionalidad por Mes del Año (1 min):**
  - Mostrar **Pestaña 2 del Dashboard**: al agrupar los 11 años por mes, **enero** subió el **100 % de los años** (`+6.77 %` prom.), **marzo** el **91.7 %** (`+4.26 %`) y **febrero** el **83.3 %** (`+3.47 %`). En cambio, **noviembre** (`-2.42 %`) y **abril** (`-2.15 %`) registran bajas y 0 % de alzas fuertes.
- **Diapositiva 7 – Hallazgo 3: Cuatro Pruebas de Hipótesis No Obvias ($\alpha = 0.05$) (1.5 min):**
  - Mostrar **Pestaña 3 del Dashboard** y explicar cómo fuimos más allá de lo obvio usando la prueba $z$ de dos proporciones:
    - **P1 (Umbral de intensidad):** El Niño Fuerte ($\ge +1.5\,^\circ\text{C}$) dispara las alzas a **`58.8 %`** vs. **`25.0 %`** en Débil/Moderado ($z=2.338, p=0.0097$ → se rechaza $H_0$).
    - **P2 (Doble golpe Estacionalidad × El Niño):** Ene–Mar con El Niño llega al **`60.0 %`** (**10×** frente al **`5.9 %`** de Abr–Dic Neutro).
    - **P3 (Mito refutado):** El Niño (`36.7 %`) vs. La Niña (`36.7 %`, $p=0.995$ → no se rechaza $H_0$): ambos extremos golpean igual a Popayán.
    - **P4 (Grupo de control natural):** En **Frescos** sí hay diferencia ($p=0.00029$), pero en **Procesados** ($p=0.529$) y **Carnes** ($p=0.771$) no se rechaza $H_0$.

### Bloque 4: Componente Predictivo – Valor Agregado (2 min | Diapositivas 8–9 + Demo Simulador)
- **Diapositiva 8 – Modelos Sencillos y Métricas Honestas (1 min):**
  - Separación cronológica: entrenamiento (`2015–2024`, $n=110$) y prueba (`2024–2026`, $n=27$).
  - **Regresión:** error promedio **`MAE = 2.81 %`** (`RMSE = 3.67 %`), reduciendo en **11 %** el error frente al promedio mensual (`3.15 %`).
  - **Clasificación de alerta:** **`81.5 %` de exactitud**, **`66.7 %` de precisión** (`F1 = 0.44`).
- **Diapositiva 9 – Demo en Vivo del Simulador (1 min):**
  - Abrir **Pestaña 4 del Dashboard**: elegir **Enero** o **Marzo**, mover el slider de `ONI` de `0.0 °C` (Neutro) a `+1.5 °C` (El Niño Fuerte) y mostrar cómo cambia la estimación (`±2.81 %`) y la probabilidad de alza fuerte.

### Bloque 5: Limitaciones y Conclusiones (1.5 min | Diapositiva 10)
- **Diapositiva 10 – Observación vs. Causalidad y Conclusiones:**
  - Aclarar que una prueba de hipótesis significativa prueba asociación, **no causalidad única** (también pesan bloqueos en la Vía Panamericana, fletes, fertilizantes e inflación).
  - Enfatizar que las predicciones son escenarios probables, no certezas, y cerrar invitando a preguntas.
