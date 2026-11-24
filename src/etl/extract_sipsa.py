"""Extracción unificada de precios mayoristas SIPSA para Popayán (2015–2026).

Combina:
1. Paquetes ZIP mensuales (2013–2024) referenciados en datos.gov.co (dataset gkqq-k3k5 / DANE Microdatos 776).
2. Anexos Excel oficiales de series históricas mensuales (2025–2026) descubiertos vía web scraping
   en el portal del boletín mensual SIPSA del DANE.
"""

from __future__ import annotations

import io
import json
import re
import unicodedata
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from bs4 import BeautifulSoup

DATASET_ID = "gkqq-k3k5"
VIEWS_URL = f"https://www.datos.gov.co/api/views/{DATASET_ID}.json"
DANE_MENSUAL_URL = (
    "https://www.dane.gov.co/index.php/estadisticas-por-tema/agropecuario/"
    "sistema-de-informacion-de-precios-sipsa/mayoristas-boletin-mensual-1"
)
DANE_BASE = "https://www.dane.gov.co"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; Electiva3DataScience/1.0)"}

ROOT_DIR = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT_DIR / "data" / "raw"


def _strip_accents(text: str) -> str:
    return "".join(
        ch for ch in unicodedata.normalize("NFKD", str(text)) if not unicodedata.combining(ch)
    )


def _normalize_col(col: str) -> str:
    c = _strip_accents(str(col)).strip().lower().replace("\ufeff", "")
    c = re.sub(r"[^a-z0-9]+", "_", c).strip("_")
    if "fecha" in c:
        return "fecha_raw"
    if "grupo" in c:
        return "grupo"
    if "producto" in c or "articulo" in c:
        return "producto"
    if "cpc" in c:
        return "codigo_cpc"
    if "mercado" in c or "fuente" in c or "ciudad" in c:
        return "mercado"
    if "precio" in c:
        return "precio_raw"
    return c


def _read_csv_bytes(raw_bytes: bytes) -> pd.DataFrame:
    """Lee un CSV del DANE detectando codificación y separador (';' o ',')."""
    text_sample = ""
    chosen_enc = "utf-8-sig"
    for enc in ("utf-8-sig", "utf-8", "latin1", "cp1252"):
        try:
            text_sample = raw_bytes[:4096].decode(enc)
            chosen_enc = enc
            break
        except UnicodeDecodeError:
            continue

    first_line = text_sample.splitlines()[0] if text_sample else ""
    sep = ";" if first_line.count(";") >= first_line.count(",") else ","
    df = pd.read_csv(
        io.BytesIO(raw_bytes),
        sep=sep,
        encoding=chosen_enc,
        dtype=str,
        on_bad_lines="skip",
    )
    return df


def _filter_popayan(df: pd.DataFrame, source_label: str) -> pd.DataFrame:
    df = df.rename(columns={c: _normalize_col(c) for c in df.columns})
    if "mercado" not in df.columns:
        raise ValueError(f"Columna 'mercado' no encontrada en {source_label}: {df.columns.tolist()}")

    mask = df["mercado"].fillna("").map(lambda x: "popay" in _strip_accents(x).lower())
    sub = df.loc[mask].copy()
    sub["fuente_archivo"] = source_label
    for col in ("fecha_raw", "grupo", "producto", "codigo_cpc", "mercado", "precio_raw"):
        if col not in sub.columns:
            sub[col] = pd.NA
    return sub[["fecha_raw", "grupo", "producto", "codigo_cpc", "mercado", "precio_raw", "fuente_archivo"]]


def fetch_gkqq_zip_links() -> tuple[dict[str, Any], list[dict[str, str]]]:
    """Obtiene metadatos y URLs de descarga ZIP desde datos.gov.co (gkqq-k3k5)."""
    resp = requests.get(VIEWS_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    view = resp.json()
    aps = view.get("metadata", {}).get("additionalAccessPoints", [])
    links: list[dict[str, str]] = []
    for ap in aps:
        title = ap.get("title", "sin_titulo")
        urls = ap.get("urls", {})
        url = next(iter(urls.values()), None)
        if url:
            links.append({"title": title, "url": url})
    meta = {
        "dataset_id": DATASET_ID,
        "name": view.get("name"),
        "rowsUpdatedAt": (
            datetime.fromtimestamp(view["rowsUpdatedAt"], tz=timezone.utc).isoformat()
            if view.get("rowsUpdatedAt")
            else None
        ),
    }
    return meta, links


def scrape_dane_2025_2026_links() -> list[dict[str, str]]:
    """Descubre automáticamente las URLs Excel de series históricas SIPSA 2025 y 2026 en dane.gov.co."""
    resp = requests.get(DANE_MENSUAL_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    links: list[dict[str, str]] = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "seriehistoricamayorista" in href.lower() and any(y in href for y in ("2025", "2026")):
            full_url = href if href.startswith("http") else f"{DANE_BASE}{href}"
            if full_url not in seen:
                seen.add(full_url)
                year = "2026" if "2026" in href else "2025"
                links.append({"title": f"DANE-SerieHistoricaMayorista-{year}", "url": full_url})
    return sorted(links, key=lambda x: x["title"])


def _read_dane_excel_popayan(content: bytes, label: str) -> pd.DataFrame:
    """Lee la hoja de datos de un anexo Excel de serie histórica SIPSA y filtra Popayán."""
    xl = pd.ExcelFile(io.BytesIO(content))
    data_sheet = next((s for s in xl.sheet_names if s.strip().isdigit()), xl.sheet_names[0])
    preview = pd.read_excel(xl, sheet_name=data_sheet, nrows=15, header=None)
    header_row = 0
    for idx, row in preview.iterrows():
        vals = " ".join(str(v).lower() for v in row.dropna().tolist())
        if "fecha" in vals and "mercado" in vals:
            header_row = int(idx)
            break
    df = pd.read_excel(xl, sheet_name=data_sheet, header=header_row, dtype=str)
    return _filter_popayan(df, label)


def extract_all_sipsa_popayan() -> pd.DataFrame:
    """Descarga y consolida en crudo todos los registros de Popayán (2013–2026)."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    frames: list[pd.DataFrame] = []
    sources_log: list[dict[str, Any]] = []

    meta_gov, zip_links = fetch_gkqq_zip_links()
    print(f"Fuentes ZIP en datos.gov.co ({DATASET_ID}): {len(zip_links)}")
    for item in zip_links:
        title, url = item["title"], item["url"]
        print(f"  Descargando {title}...")
        r = requests.get(url, headers=HEADERS, timeout=120)
        r.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
            csv_names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
            if not csv_names:
                raise ValueError(f"No se encontró CSV dentro de {title}: {zf.namelist()}")
            csv_name = csv_names[0]
            df_raw = _read_csv_bytes(zf.read(csv_name))
            sub = _filter_popayan(df_raw, f"{title}/{csv_name}")
            frames.append(sub)
            sources_log.append(
                {
                    "title": title,
                    "url": url,
                    "inner_file": csv_name,
                    "total_rows_national": int(len(df_raw)),
                    "popayan_rows": int(len(sub)),
                }
            )
            print(f"    -> Nacional: {len(df_raw):,} | Popayán: {len(sub):,}")

    xlsx_links = scrape_dane_2025_2026_links()
    print(f"Fuentes Excel 2025–2026 descubiertas en dane.gov.co: {len(xlsx_links)}")
    for item in xlsx_links:
        title, url = item["title"], item["url"]
        print(f"  Descargando {title}...")
        r = requests.get(url, headers=HEADERS, timeout=120)
        r.raise_for_status()
        sub = _read_dane_excel_popayan(r.content, title)
        frames.append(sub)
        sources_log.append(
            {
                "title": title,
                "url": url,
                "popayan_rows": int(len(sub)),
            }
        )
        print(f"    -> Popayán: {len(sub):,}")

    df_all = pd.concat(frames, ignore_index=True)
    out_parquet = RAW_DIR / "sipsa_popayan_raw.parquet"
    out_csv = RAW_DIR / "sipsa_popayan_raw.csv"
    df_all.to_parquet(out_parquet, index=False)
    df_all.to_csv(out_csv, index=False)

    meta_out = {
        **meta_gov,
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "dane_mensual_page": DANE_MENSUAL_URL,
        "total_popayan_rows_raw": int(len(df_all)),
        "unique_markets_raw": sorted(df_all["mercado"].dropna().unique().tolist()),
        "unique_groups_raw": sorted(df_all["grupo"].dropna().unique().tolist()),
        "sources": sources_log,
    }
    (RAW_DIR / "sipsa_metadata.json").write_text(
        json.dumps(meta_out, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\nExtracción SIPSA Popayán completada: {len(df_all):,} filas guardadas en {out_parquet}")
    print(f"Mercados Popayán: {meta_out['unique_markets_raw']}")
    print(f"Grupos encontrados: {meta_out['unique_groups_raw']}")
    return df_all


if __name__ == "__main__":
    extract_all_sipsa_popayan()
