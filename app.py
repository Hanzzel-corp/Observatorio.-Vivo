#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Observatorio Vivo v6
Backend local con:
- FastAPI
- SQLite persistente
- colectores públicos
- detector de brotes/fenómenos nacientes
- watchlist
- alias/fenómenos
- alertas Telegram opcionales

Uso:
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
  uvicorn app:app --reload --host 127.0.0.1 --port 8765
"""

from __future__ import annotations

import asyncio
import csv
import hashlib
import io
import json
import logging
import math
import os
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set
import time
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from urllib.parse import quote

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel


APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
FRONTEND_DIR = APP_DIR / "frontend"
DB_PATH = DATA_DIR / "observatorio.db"
LOG_PATH = DATA_DIR / "observatorio.log"

# P2 #23: Importar desde módulos separados
from modules.database import DatabaseContext, init_db_module
from modules.models import WatchIn, AliasIn, SettingsIn

# P2 #25: Logging estructurado con archivo
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    handlers=[
        logging.FileHandler(LOG_PATH, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("observatorio")

# P1: Cache en memoria para detect_outbreaks (TTL 30 segundos)
_outbreaks_cache: Dict[str, Any] = {}
_outbreaks_cache_ts: float = 0.0
OUTBREAKS_CACHE_TTL = 30.0  # segundos

DATA_DIR.mkdir(exist_ok=True)

REGIONS: Dict[str, Dict[str, Any]] = {
    "hispano": {
        "label": "Hispanoamérica",
        "trends": [["AR", "Argentina"], ["MX", "México"], ["CL", "Chile"], ["CO", "Colombia"], ["ES", "España"]],
        "wiki": [["es", "Español"]],
    },
    "anglo": {
        "label": "Anglosfera",
        "trends": [["US", "EE.UU."], ["GB", "Reino Unido"], ["CA", "Canadá"], ["AU", "Australia"]],
        "wiki": [["en", "English"]],
    },
    "europa": {
        "label": "Europa",
        "trends": [["ES", "España"], ["FR", "Francia"], ["DE", "Alemania"], ["IT", "Italia"], ["GB", "Reino Unido"]],
        "wiki": [["es", "Español"], ["en", "English"]],
    },
    "latam": {
        "label": "LATAM",
        "trends": [["AR", "Argentina"], ["MX", "México"], ["BR", "Brasil"], ["CO", "Colombia"], ["CL", "Chile"]],
        "wiki": [["es", "Español"], ["pt", "Português"]],
    },
    "asia": {
        "label": "Asia",
        "trends": [["JP", "Japón"], ["IN", "India"], ["KR", "Corea"]],
        "wiki": [["ja", "日本語"], ["en", "English"]],
    },
    "mundo": {
        "label": "Mundo",
        "trends": [["US", "EE.UU."], ["AR", "Argentina"], ["ES", "España"], ["BR", "Brasil"], ["DE", "Alemania"], ["JP", "Japón"]],
        "wiki": [["es", "Español"], ["en", "English"]],
    },
}

GEO_NAMES = {
    "AR": "Argentina", "MX": "México", "CL": "Chile", "CO": "Colombia", "ES": "España",
    "US": "EE.UU.", "GB": "Reino Unido", "CA": "Canadá", "AU": "Australia",
    "FR": "Francia", "DE": "Alemania", "IT": "Italia", "BR": "Brasil",
    "JP": "Japón", "IN": "India", "KR": "Corea",
    "es": "Wikipedia ES", "en": "Wikipedia EN", "pt": "Wikipedia PT", "ja": "Wikipedia JA",
    "reddit": "Reddit", "mastodon": "Mastodon", "hn": "Hacker News",
}

HISPANO_GEOS = {
    "AR", "MX", "CL", "CO", "ES", "PE", "VE", "UY", "PY", "BO", "EC", "CR",
    "DO", "GT", "HN", "NI", "PA", "SV", "PR", "CU"
}
HISPANO_LANGS = {"es"}

STOP = set("""
a al algo algun alguna algunas algunos ante antes aquel aquella aquellas aquellos aqui aquí asi así aun aún aunque cada como cómo con contra cual cuales
cuando cuándo de del desde donde dónde dos el la los las le les un una unos unas en entre era es eran esa ese esas eso esos esta está este estas estos esto
fue fueron ha han hasta hay he hubo lo me mi mis muy ni no nos para pero por porque que qué se sea sean si sí sin sobre solo sólo son su sus tan te tu tus y ya
mas más uno otro hace tres sino the of and to in for on with as is at by it that this from be are was were has have not but or an its their they them we our you your
i do does did will would could should may can about more most some such than then there these those over under into out up down off so very just also like new top
why how what when where who which year years day days first last here live news update updates latest breaking official video says after before into from
""".split())

# Palabras genéricas que solas no generan alerta (filtro anti-ruido)
GENERIC_WORDS = set("""
game people show video real today movie official series season episode livestream
stream channel user account page site web online app download free full hd 4k
music song album artist band singer actor actress director producer company brand
product service app application software program system platform network
world global international national local public general common popular famous
top best new latest recent old first last big small large huge tiny major minor
main primary secondary high low more less most least many few several some all
none good bad better worse best worst great nice fine okay cool hot cold warm
true false right wrong left yes no maybe perhaps probably definitely certainly
actually really truly surely absolutely completely totally entirely almost quite
very much many well badly simply easily quickly slowly fast hard early late soon
now then here there everywhere somewhere anywhere everywhere nowhere
home house room place space area spot point location position situation condition
state status level degree rate amount number quantity part piece bit section
piece portion share half third quarter group set list line row column side
back front top bottom inside outside center middle edge end start beginning
origin source result effect outcome output input process method way means
form type kind sort class category style manner mode fashion trend
issue matter problem question topic subject theme idea concept notion thought
thing object item element component factor aspect feature detail point element
""".split())

# Categorías temáticas para clasificación
CATEGORIES = {
    "deporte": {"messi", "lakers", "futbol", "basket", "nba", "fifa", "mundial", "copa", "partido", "gol", "jugador", "equipo", "deporte", "olimpiadas", "tenis", "f1", "formula", "carrera", "maraton", "atleta", "campeon", "liga", "torneo", "estadio", "club"},
    "anime_entretenimiento": {"dragon", "ball", "goku", "daima", "anime", "manga", "otaku", "netflix", "disney", "hbo", "streaming", "serie", "pelicula", "cine", "actor", "actriz", "director", "estreno", "temporada", "capitulo", "episodio", "marvel", "dc", "star", "wars", "trek", "juego", "tronos", "breaking", "bad", "stranger", "things", "witcher", "anillo", "poder"},
    "ia_tecnologia": {"openai", "chatgpt", "gpt", "llm", "inteligencia", "artificial", "ai", "machine", "learning", "deep", "neural", "modelo", "gemini", "google", "microsoft", "azure", "aws", "cloud", "computacion", "chip", "nvidia", "amd", "intel", "procesador", "gpu", "tecnologia", "software", "hardware", "app", "aplicacion", "robot", "automation", "code", "programacion", "developer"},
    "ciberseguridad": {"ransomware", "malware", "virus", "trojan", "phishing", "hacker", "hack", "breach", "exploit", "vulnerability", "cve", "security", "ciberseguridad", "ciberataque", "ataque", "cyber", "firewall", "encryption", "password", "credential", "data", "leak", "stolen", "dark", "web", "tor", "bitcoin", "crypto", "ransom"},
    "politica": {"trump", "biden", "eleccion", "voto", "politica", "gobierno", "presidente", "ministro", "congreso", "senado", "parlamento", "ley", "reforma", "protesta", "manifestacion", "corrupcion", "escandalo", "partido", "oposicion", "oficialismo", "candidato", "campaña", "debate"},
    "economia": {"economia", "mercado", "bolsa", "acciones", "inversion", "inflacion", "recesion", "crisis", "banco", "bancario", "dinero", "dolar", "euro", "peso", "moneda", "crypto", "bitcoin", "ethereum", "nft", "finanzas", "fiscal", "impuestos", "deuda", "presupuesto", "pib", "desempleo", "empleo", "trabajo"},
    "salud": {"salud", "medico", "hospital", "clinica", "enfermedad", "virus", "pandemia", "epidemia", "vacuna", "tratamiento", "medicamento", "droga", "pharma", "covid", "cancer", "salud", "mental", "psicologia", "terapia", "doctor", "enfermera", "paciente", "sintoma", "diagnostico"},
    "producto": {"iphone", "samsung", "apple", "xiaomi", "android", "ios", "windows", "mac", "linux", "playstation", "xbox", "nintendo", "switch", "consola", "celular", "movil", "smartphone", "laptop", "notebook", "tablet", "smartwatch", "auricular", "camara", "auto", "tesla", "toyota", "ford", "vehiculo", "electric"},
}

# Configuración de niveles de alerta
ALERT_COOLDOWN_HOURS = 6  # Horas de cooldown entre alertas del mismo término
MIN_DELTA_FOR_ALERT = 0.5  # P2: Subido de 0.1 a 0.5 para alertas más significativas
MIN_WORDS_FOR_PHRASE = 2  # Mínimo de palabras para considerar frase específica


def now_ts() -> float:
    return time.time()


def normalize(text: str) -> str:
    import unicodedata
    s = str(text or "").lower().strip()
    s = "".join(ch for ch in unicodedata.normalize("NFD", s) if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", s)


def tokenize(text: str) -> List[str]:
    s = normalize(text)
    s = re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE)
    parts = [p for p in s.split() if len(p) >= 4 and p not in STOP]
    return parts[:80]


# P2 #23: get_db y init_db importados desde database.py
# DatabaseContext definido en database.py

def get_db():
    """P2 #23: Factory function que retorna DatabaseContext desde database.py"""
    return DatabaseContext(DB_PATH)

def init_db():
    """P2 #22, #23: Inicializar DB usando el módulo separado"""
    init_db_module(DB_PATH)
    
    # Generar api_reset_token aleatorio si está vacío
    import secrets
    with get_db() as db:
        token_row = db.execute("SELECT value FROM settings WHERE key = 'api_reset_token'").fetchone()
        token = token_row["value"] if token_row else ""
        if not token:
            new_token = secrets.token_urlsafe(16)
            db.execute(
                "INSERT OR REPLACE INTO settings(key, value) VALUES ('api_reset_token', ?)",
                (new_token,)
            )
            logger.info(f"API Reset Token generado: {new_token}")

def get_settings() -> Dict[str, str]:
    with get_db() as db:
        return {r["key"]: r["value"] for r in db.execute("SELECT key, value FROM settings")}


def set_setting(key: str, value: str) -> None:
    with get_db() as db:
        db.execute(
            "INSERT INTO settings(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )


def alias_map() -> Dict[str, str]:
    with get_db() as db:
        return {r["alias"]: r["canonical"] for r in db.execute("SELECT alias, canonical FROM aliases")}


def canonicalize(term: str, aliases: Optional[Dict[str, str]] = None) -> str:
    t = normalize(term)
    aliases = aliases if aliases is not None else alias_map()
    return aliases.get(t, t)


def get_phenomenon(term: str, aliases: Optional[Dict[str, str]] = None) -> Optional[str]:
    """Obtener el fenómeno asociado a un término (ej: 'chatgpt' -> 'OpenAI/IA')"""
    t = normalize(term)
    with get_db() as db:
        row = db.execute("SELECT phenomenon FROM aliases WHERE alias = ?", (t,)).fetchone()
        if row and row["phenomenon"]:
            return row["phenomenon"]
    return None


def classify_category(term: str) -> Optional[str]:
    """Clasificar término en categoría temática"""
    words = set(term.lower().split())
    scores = {}
    for cat, keywords in CATEGORIES.items():
        score = len(words & keywords)
        if score > 0:
            scores[cat] = score
    if not scores:
        return None
    return max(scores, key=scores.get)


def is_generic_term(term: str) -> bool:
    """Verificar si es una palabra genérica que sola no debe generar alerta"""
    words = term.lower().split()
    # Palabra única y genérica
    if len(words) == 1 and words[0] in GENERIC_WORDS:
        return True
    return False


def is_numeric_noise(term: str) -> bool:
    """
    Verificar si es ruido numérico (número o año aislado).
    2026 → no alertar
    world cup 2026 → sí alertar (porque es frase)
    """
    words = term.strip().split()
    # Solo si es una palabra única
    if len(words) != 1:
        return False
    w = words[0]
    # Número puro
    if w.isdigit():
        return True
    # Año tipo 2026, 1999, etc.
    if re.fullmatch(r"20\d{2}", w):
        return True
    if re.fullmatch(r"19\d{2}", w):
        return True
    return False


def is_component_of_better_phrase(term: str, all_terms: List[str]) -> bool:
    """
    Verificar si este término es componente de una frase más completa existente.
    Ejemplo: "jimmy" y "kimmel" se suprimen si existe "jimmy kimmel"
    """
    words = term.lower().split()
    if len(words) != 1:
        return False  # Solo verificar palabras sueltas
    
    word = words[0]
    for t in all_terms:
        t_lower = t.lower()
        other_words = t_lower.split()
        # Si existe una frase de 2+ palabras que contiene esta palabra
        if len(other_words) >= 2 and word in other_words and t_lower != word:
            return True
    return False


def find_better_phrase(term: str, all_terms: List[str]) -> Optional[str]:
    """
    Encontrar la frase más específica que contiene este término.
    Retorna la frase más larga que contiene el término, o None.
    """
    words = term.lower().split()
    if len(words) != 1:
        return None
    
    word = words[0]
    candidates = []
    
    for t in all_terms:
        t_lower = t.lower()
        other_words = t_lower.split()
        if len(other_words) >= 2 and word in other_words:
            candidates.append(t)
    
    # Retornar la frase más larga (más específica)
    if candidates:
        return max(candidates, key=lambda x: len(x.split()))
    return None


def calculate_specificity_score(term: str, word_count: int, is_watchlist: bool, 
                                category: Optional[str], is_generic: bool,
                                all_terms: List[str]) -> Tuple[float, str]:
    """
    Calcular score de especificidad para ranking visual.
    Retorna: (specificity_score, visual_reason)
    
    Reglas:
    - Frases de 3-4 palabras: +25 puntos (alta especificidad)
    - Frases de 2 palabras: +15 puntos (media especificidad)
    - Palabra suelta no genérica: 0 puntos (base)
    - Palabra suelta genérica: -20 puntos (penalización)
    - Watchlist: +10 puntos (bonus)
    - Categoría detectada: +8 puntos (bonus)
    - Componente de frase mejor: -30 puntos (penalización fuerte)
    - Número/año aislado: -40 puntos (penalización muy fuerte)
    """
    score = 0.0
    reasons = []
    
    # Base por longitud de frase
    if word_count >= 4:
        score += 25
        reasons.append("frase 4+ palabras")
    elif word_count == 3:
        score += 25
        reasons.append("frase 3 palabras")
    elif word_count == 2:
        score += 15
        reasons.append("frase 2 palabras")
    elif word_count == 1:
        if is_generic:
            score -= 20
            reasons.append("palabra genérica")
        else:
            reasons.append("palabra suelta")
    
    # Bonuses
    if is_watchlist:
        score += 10
        reasons.append("watchlist")
    
    if category:
        score += 8
        reasons.append(f"categoría {category}")
    
    # Penalizaciones
    if is_numeric_noise(term):
        score -= 40
        reasons.append("número aislado")
    
    if is_component_of_better_phrase(term, all_terms):
        score -= 30
        better = find_better_phrase(term, all_terms)
        if better:
            reasons.append(f"componente de '{better}'")
        else:
            reasons.append("componente de frase")
    
    # Construir razón visual
    visual_reason = "; ".join(reasons) if reasons else "base"
    
    return score, visual_reason


def calculate_visual_score(outbreak: Dict[str, Any], all_terms: List[str], 
                           watchlist_terms: set) -> Tuple[float, str]:
    """
    Calcular score visual para ranking de brotes.
    visual_score = emergency + specificity_score - penalties
    
    Retorna: (visual_score, visual_reason)
    """
    term = outbreak.get("term", "")
    emergency = outbreak.get("emergency", 0)
    word_count = outbreak.get("word_count", 1)
    category = outbreak.get("category")
    is_generic = outbreak.get("is_generic", False)
    is_watchlist = term in watchlist_terms
    
    # Calcular especificidad
    specificity, reason = calculate_specificity_score(
        term, word_count, is_watchlist, category, is_generic, all_terms
    )
    
    # Score visual final
    visual_score = emergency + specificity
    
    return visual_score, reason


def filter_and_rank_outbreaks(outbreaks: List[Dict[str, Any]], 
                              watchlist_terms: set,
                              min_emergency: float = 20.0) -> List[Dict[str, Any]]:
    """
    Filtrar y ordenar brotes para visualización priorizando especificidad.
    
    Reglas de filtrado visual:
    1. Descartar componentes de frases mejores (a menos que sean watchlist)
    2. Descartar números/años aislados
    3. Descartar términos con emergency muy bajo
    4. Ordenar por visual_score (emergency + especificidad)
    """
    all_terms = [o["term"] for o in outbreaks]
    result = []
    
    for outbreak in outbreaks:
        term = outbreak.get("term", "")
        emergency = outbreak.get("emergency", 0)
        
        # Filtrar por emergency mínimo
        if emergency < min_emergency:
            continue
        
        # Si es watchlist, siempre incluir (aunque sea componente)
        is_watchlist = term in watchlist_terms
        
        # Filtrar números/años aislados (excepto watchlist)
        if not is_watchlist and is_numeric_noise(term):
            continue
        
        # Calcular score visual y razón
        visual_score, visual_reason = calculate_visual_score(outbreak, all_terms, watchlist_terms)
        
        # Agregar metadatos al outbreak
        outbreak["specificity_score"] = visual_score - emergency
        outbreak["visual_score"] = visual_score
        outbreak["visual_reason"] = visual_reason
        outbreak["is_visual_primary"] = True  # Por defecto, luego se ajusta
        
        result.append(outbreak)
    
    # Ordenar por visual_score descendente
    result.sort(key=lambda x: x["visual_score"], reverse=True)
    
    # Marcar brotes principales (los primeros que no son componentes)
    seen_phrases = set()
    for outbreak in result:
        term = outbreak.get("term", "")
        is_watchlist = term in watchlist_terms
        
        # Si es watchlist, siempre es primario
        if is_watchlist:
            outbreak["is_visual_primary"] = True
            continue
        
        # Si es componente de una frase mejor que ya apareció, marcar como secundario
        if is_component_of_better_phrase(term, all_terms):
            better = find_better_phrase(term, all_terms)
            if better and better in seen_phrases:
                outbreak["is_visual_primary"] = False
                outbreak["visual_reason"] += " [suprimido por frase mejor]"
        
        seen_phrases.add(term)
    
    return result


def calculate_confidence(stat: Dict[str, Any]) -> str:
    """
    Calcular nivel de confianza:
    - BAJA: apareció una vez o en una sola fuente
    - MEDIA: apareció en 2+ muestras o 2+ fuentes
    - ALTA: apareció en varias fuentes, regiones y repitió
    """
    runs = stat.get("runs", 1)
    sources = stat.get("sources", 1)
    regions = stat.get("regions", 1)
    
    if regions >= 3 and sources >= 3 and runs >= 3:
        return "ALTA"
    elif (regions >= 2 or sources >= 2) and runs >= 2:
        return "MEDIA"
    else:
        return "BAJA"


def should_alert(outbreak: Dict[str, Any], is_watchlist: bool = False, all_terms: Optional[List[str]] = None) -> Tuple[bool, str]:
    """
    Determinar si un brote debe generar alerta.
    Retorna: (debe_alertar, razón)
    """
    estado = outbreak.get("estado", "RUIDO")
    delta = outbreak.get("delta", 0)
    confidence = outbreak.get("confidence", "BAJA")
    term = outbreak.get("term", "")
    
    # 1. No alertar si es ruido
    if estado == "RUIDO":
        return False, "Estado RUIDO: no alcanza umbral de detección"
    
    # 2. No alertar si es palabra genérica sola (excepto watchlist)
    if not is_watchlist and is_generic_term(term):
        return False, "Término genérico aislado"
    
    # 3. No alertar si es número/año aislado (excepto watchlist)
    if not is_watchlist and is_numeric_noise(term):
        return False, "Número/año aislado"
    
    # 4. No alertar si es componente de una frase mejor (excepto watchlist)
    if not is_watchlist and all_terms and is_component_of_better_phrase(term, all_terms):
        return False, "Componente de frase completa"
    
    # 5. Delta obligatorio (excepto watchlist)
    if not is_watchlist and delta < MIN_DELTA_FOR_ALERT:
        return False, f"Sin crecimiento positivo (delta {delta:.1f})"
    
    # 6. Nivel de alerta según confianza y estado
    # BAJA: mostrar en tabla (observación)
    # MEDIA: mostrar como brote
    # ALTA: generar alerta
    
    if confidence == "BAJA":
        return False, "Confianza BAJA: observación pendiente"
    
    if estado in ["EVENTO", "PROPAGACIÓN"]:
        return True, f"{estado} con confianza {confidence}"
    
    if estado == "BROTE" and confidence in ["MEDIA", "ALTA"]:
        return True, f"BROTE confirmado con confianza {confidence}"
    
    if estado == "SEMILLA" and confidence == "ALTA":
        return False, "SEMILLA con confianza ALTA: esperando repetición"
    
    return False, f"No cumple criterios: {estado}/{confidence}"


def check_alert_cooldown(term: str, estado: str, cooldown_hours: int = ALERT_COOLDOWN_HOURS) -> bool:
    """
    Verificar si ha pasado el cooldown desde la última alerta de este término.
    Retorna True si puede alertar (cooldown expirado o no hay alerta previa).
    
    CORREGIDO: Lee el estado real desde meta_json en lugar de 'level' (que guarda alta/media/baja).
    """
    with get_db() as db:
        # Buscar última alerta del mismo término (incluyendo meta_json)
        row = db.execute(
            "SELECT ts, meta_json FROM alerts WHERE term = ? ORDER BY ts DESC LIMIT 1",
            (term,)
        ).fetchone()
        
        if not row:
            return True  # Nunca alertó, puede alertar
        
        last_alert_ts = row["ts"]
        hours_since = (now_ts() - last_alert_ts) / 3600
        
        # Extraer estado previo desde meta_json (no desde 'level' que es alta/media/baja)
        last_estado = None
        try:
            meta = json.loads(row["meta_json"] or "{}")
            last_estado = meta.get("estado")
        except (json.JSONDecodeError, TypeError):
            pass
        
        # Si cambió de estado significativamente, permitir alerta incluso dentro del cooldown
        estado_escalation = {"SEMILLA": 1, "BROTE": 2, "PROPAGACIÓN": 3, "EVENTO": 4}
        current_level = estado_escalation.get(estado, 0)
        previous_level = estado_escalation.get(last_estado, 0)
        
        if current_level > previous_level:
            return True  # Escaló de estado, alertar
        
        return hours_since >= cooldown_hours


def get_alert_level(estado: str, confidence: str) -> str:
    """
    Determinar nivel de alerta final:
    - DETECTADO: en bandeja de observación
    - OBSERVADO: visible como brote pero sin alerta activa
    - ALERTADO: genera notificación
    """
    if estado == "RUIDO":
        return "DETECTADO"
    
    if confidence == "BAJA":
        return "OBSERVADO"
    
    if estado in ["EVENTO", "PROPAGACIÓN"]:
        return "ALERTADO"
    
    if estado == "BROTE" and confidence in ["MEDIA", "ALTA"]:
        return "ALERTADO"
    
    return "OBSERVADO"


def update_observation_tray(outbreak: Dict[str, Any]) -> None:
    """
    Actualizar bandeja de observación con un brote detectado.
    P0: No inserta si estado es RUIDO, y limpia entradas > 7 días.
    """
    term = outbreak.get("term", "")
    estado = outbreak.get("estado", "RUIDO")
    confidence = outbreak.get("confidence", "BAJA")
    category = outbreak.get("category")
    
    # P0: No insertar RUIDO en la bandeja
    if estado == "RUIDO":
        return
    
    with get_db() as db:
        # P0: Cleanup de entradas viejas (> 7 días) cada cierto tiempo
        # Usamos un contador estático para no hacer esto en cada llamada
        if not hasattr(update_observation_tray, '_cleanup_counter'):
            update_observation_tray._cleanup_counter = 0
        update_observation_tray._cleanup_counter += 1
        
        if update_observation_tray._cleanup_counter % 100 == 0:
            cutoff_ts = now_ts() - (7 * 24 * 3600)  # 7 días en segundos
            db.execute(
                "DELETE FROM observation_tray WHERE last_seen < ?",
                (cutoff_ts,)
            )
        
        # Verificar si ya existe
        existing = db.execute(
            "SELECT * FROM observation_tray WHERE term = ?", (term,)
        ).fetchone()
        
        if existing:
            # Actualizar si hay cambios significativos
            db.execute(
                """
                UPDATE observation_tray 
                SET last_seen = ?, estado = ?, confidence = ?, 
                    runs_count = ?, regions_count = ?, sources_count = ?,
                    delta = ?, emergency = ?
                WHERE term = ?
                """,
                (
                    now_ts(), estado, confidence,
                    outbreak.get("runs", existing["runs_count"]),
                    outbreak.get("regions", existing["regions_count"]),
                    outbreak.get("sources", existing["sources_count"]),
                    outbreak.get("delta", 0),
                    outbreak.get("emergency", 0),
                    term
                )
            )
            
            # Si fue promovido a alerta, marcarlo
            alert_level = get_alert_level(estado, confidence)
            if alert_level == "ALERTADO" and not existing["promoted_to_alert"]:
                db.execute(
                    "UPDATE observation_tray SET promoted_to_alert = 1 WHERE term = ?",
                    (term,)
                )
        else:
            # Insertar nuevo
            db.execute(
                """
                INSERT INTO observation_tray 
                (ts, term, estado, confidence, category, first_seen, last_seen, 
                 runs_count, regions_count, sources_count, delta, emergency)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    now_ts(), term, estado, confidence, category,
                    outbreak.get("first_seen", now_ts()),
                    now_ts(),
                    outbreak.get("runs", 1),
                    outbreak.get("regions", 1),
                    outbreak.get("sources", 1),
                    outbreak.get("delta", 0),
                    outbreak.get("emergency", 0)
                )
            )


def get_observation_tray(limit: int = 50) -> List[Dict[str, Any]]:
    """Obtener bandeja de observación"""
    with get_db() as db:
        rows = db.execute(
            """
            SELECT * FROM observation_tray 
            ORDER BY emergency DESC, last_seen DESC 
            LIMIT ?
            """,
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def source_weight(source: str, rank: int) -> float:
    rank_weight = (12 - min(rank, 10)) / 10.0
    base = 1.0 + rank_weight
    if source.startswith("gtrends"):
        base += 1.2
    if source.startswith("wiki"):
        base += 0.7
    if source in {"reddit", "hacker-news", "mastodon-tags", "mastodon-links"}:
        base += 0.4
    return base


def phrases_from_title(title: str) -> List[Tuple[str, float]]:
    """
    Extrae frases significativas de un título con reducción de solapamiento.
    P0: Reduce de ~34 n-grams a ~10 por título, priorizando frases sobre palabras sueltas.
    """
    words = tokenize(title)
    if not words:
        return []
    
    out: List[Tuple[str, float]] = []
    word_count = len(words)
    
    # Para títulos cortos (≤5 palabras): incluir palabras sueltas + frases
    # Para títulos largos: solo frases, no palabras sueltas
    include_single_words = word_count <= 5
    
    if include_single_words:
        # Solo palabras con contenido semántico (no conectores)
        stop_words = {"el", "la", "los", "las", "un", "una", "de", "del", "al", "y", "o", "en", "a", "por", "para", "con", "sin", "sobre", "entre", "hasta", "desde", "the", "a", "an", "and", "or", "of", "in", "on", "at", "to", "for", "with", "by"}
        for w in words:
            if w not in stop_words and len(w) > 2:
                out.append((w, 0.8))  # Peso menor que frases
    
    # Generar frases de 2-4 palabras con ventanas estratégicas (no todas solapadas)
    # Estrategia: usar saltos para reducir solapamiento total
    if word_count <= 6:
        # Títulos cortos: ventanas consecutivas (máximo solapamiento permitido)
        step_sizes = {2: 1, 3: 2, 4: 2}  # n -> step
    else:
        # Títulos largos: saltos mayores para reducir redundancia
        step_sizes = {2: 2, 3: 3, 4: 3}
    
    for n in (4, 3, 2):  # Orden inverso: priorizar frases más largas
        step = step_sizes[n]
        max_start = max(0, word_count - n + 1)
        
        for i in range(0, max_start, step):
            phrase = " ".join(words[i : i + n])
            if len(phrase) <= 60:
                # Peso base por longitud de frase
                if n == 4:
                    weight = 1.35
                elif n == 3:
                    weight = 1.15
                else:
                    weight = 0.95
                
                # Bonus por posición (inicio del título es más importante)
                if i == 0:
                    weight *= 1.2
                
                out.append((phrase, weight))
    
    # Limitar a máximo 12 términos por título para evitar explosión
    if len(out) > 12:
        # Ordenar por peso y tomar los mejores
        out.sort(key=lambda x: x[1], reverse=True)
        out = out[:12]
    
    return out


def record_source(
    run_id: str,
    region: str,
    source: str,
    geo: str,
    bucket: str,
    items: List[Dict[str, Any]],
) -> None:
    aliases = alias_map()
    ts = now_ts()
    raw_json = json.dumps(items, ensure_ascii=False)
    top_title = items[0]["title"] if items else ""

    with get_db() as db:
        db.execute(
            """
            INSERT INTO samples(run_id, ts, region, source, geo, bucket, top_title, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (run_id, ts, region, source, geo, bucket, top_title, raw_json),
        )

        def insert_term_hits(run_id: str, source: str, geo: str, bucket: str, title: str, url: str = "", base_score: float = 1.0):
            """
            Insertar hits de términos procesados de un título.
            P1: Filtra términos numéricos y genéricos ANTES de insertar.
            P1 #15: Agrega title_hash para colapsar duplicados del mismo título.
            """
            phrases = phrases_from_title(title)
            ts = now_ts()
            
            # P1 #15: Computar hash del título para colapsar duplicados
            title_hash = hashlib.md5(title.lower().encode()).hexdigest()[:16]
            
            for phrase, weight in phrases:
                # P1: Skip términos numéricos (años como 2026, 1999)
                if is_numeric_noise(phrase):
                    continue
                # P1: Skip palabras genéricas solas
                if is_generic_term(phrase):
                    continue
                
                canonical = canonicalize(phrase, aliases)
                score = base_score * weight
                
                # Calcular metadatos adicionales
                word_count = len(phrase.split())
                is_generic_flag = 1 if (word_count == 1 and phrase.lower() in GENERIC_WORDS) else 0
                category = classify_category(phrase)
                
                # P1 #15: Insertar con title_hash
                db.execute(
                    """
                    INSERT INTO term_hits(term, ts, run_id, region, source, geo, bucket, score, title, url, word_count, is_generic, category, title_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (canonical, ts, run_id, region, source, geo, bucket, score, title, url, word_count, is_generic_flag, category, title_hash),
                )
        
        # Bug #2 CRÍTICO: Procesar cada item y llamar insert_term_hits
        for idx, item in enumerate(items, start=1):
            base_score = source_weight(source, idx)
            insert_term_hits(run_id, source, geo, bucket, item.get("title", ""), item.get("url", ""), base_score)


async def fetch_json(client: httpx.AsyncClient, url: str, headers: Optional[dict] = None) -> Any:
    r = await client.get(url, headers=headers)
    r.raise_for_status()
    return r.json()


async def fetch_text(client: httpx.AsyncClient, url: str, headers: Optional[dict] = None) -> str:
    r = await client.get(url, headers=headers)
    r.raise_for_status()
    return r.text


async def collect_wikipedia(client: httpx.AsyncClient, lang: str) -> List[Dict[str, Any]]:
    for days_back in range(2, 6):
        t = time.gmtime(time.time() - days_back * 86400)
        url = f"https://wikimedia.org/api/rest_v1/metrics/pageviews/top/{lang}.wikipedia/all-access/{t.tm_year}/{t.tm_mon:02d}/{t.tm_mday:02d}"
        try:
            j = await fetch_json(client, url)
            articles = j.get("items", [{}])[0].get("articles", [])
            items = []
            for a in articles:
                article = a.get("article", "")
                if re.search(r"^(Special:|Wikipedia:|Portal:|Main_Page$|Página_principal$|Especial:|Wikipédia:|Portail:)", article, re.I):
                    continue
                items.append({
                    "title": article.replace("_", " "),
                    "traffic": f"{int(a.get('views', 0)):,}",
                    "url": f"https://{lang}.wikipedia.org/wiki/{quote(article)}",
                })
                if len(items) >= 10:
                    return items
        except Exception:
            continue
    raise RuntimeError(f"Wikipedia {lang} sin datos")


def xml_text(node: ET.Element, suffix: str) -> str:
    for child in list(node):
        tag = child.tag.split("}", 1)[-1]
        if tag == suffix:
            return (child.text or "").strip()
    return ""


async def collect_google_trends(client: httpx.AsyncClient, geo: str) -> List[Dict[str, Any]]:
    rss_url = f"https://trends.google.com/trending/rss?geo={geo}"
    xml = await fetch_text(client, rss_url, headers={"User-Agent": "Mozilla/5.0"})
    root = ET.fromstring(xml)
    items: List[Dict[str, Any]] = []
    for item in root.findall(".//item")[:10]:
        title = xml_text(item, "title")
        link = xml_text(item, "link") or f"https://trends.google.com/trending?geo={geo}"
        traffic = xml_text(item, "approx_traffic")
        if title:
            items.append({"title": title, "traffic": (traffic + "+") if traffic else "", "url": link})
    if not items:
        raise RuntimeError(f"Google Trends {geo} sin items")
    return items


async def collect_reddit(client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    headers = {"User-Agent": "ObservatorioVivo/6.0 by local-user"}
    endpoints = [
        "https://www.reddit.com/r/popular.json?limit=10",
        "https://www.reddit.com/r/all/top.json?t=day&limit=10",
        "https://old.reddit.com/r/popular.json?limit=10",
    ]
    last_error = None
    for url in endpoints:
        try:
            j = await fetch_json(client, url, headers=headers)
            posts = [c.get("data", {}) for c in j.get("data", {}).get("children", [])]
            items = []
            for p in posts[:10]:
                if not p.get("title"):
                    continue
                items.append({
                    "title": p.get("title", ""),
                    "traffic": f"{round((p.get('score') or 0)/1000, 1)}k · r/{p.get('subreddit', '')}",
                    "url": "https://www.reddit.com" + p.get("permalink", ""),
                })
            if items:
                return items
        except Exception as e:
            last_error = e
    raise RuntimeError(f"Reddit falló: {last_error}")


async def collect_mastodon_tags(client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    j = await fetch_json(client, "https://mastodon.social/api/v1/trends/tags")
    items = []
    for t in j[:10]:
        usage = 0
        for h in (t.get("history") or [])[:2]:
            try:
                usage += int(h.get("uses") or 0)
            except Exception:
                pass
        items.append({"title": "#" + t.get("name", ""), "traffic": f"{usage} usos" if usage else "", "url": t.get("url", "")})
    return items


async def collect_mastodon_links(client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    j = await fetch_json(client, "https://mastodon.social/api/v1/trends/links")
    return [
        {"title": l.get("title") or l.get("url", ""), "traffic": l.get("provider_name", ""), "url": l.get("url", "")}
        for l in j[:10]
    ]


async def collect_hacker_news(client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    ids = await fetch_json(client, "https://hacker-news.firebaseio.com/v0/topstories.json")
    ids = ids[:10]
    async def one(story_id: int) -> Optional[Dict[str, Any]]:
        try:
            s = await fetch_json(client, f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json")
            if not s or not s.get("title"):
                return None
            return {
                "title": s.get("title", ""),
                "traffic": f"{s.get('score', 0)} pts",
                "url": s.get("url") or f"https://news.ycombinator.com/item?id={story_id}",
            }
        except Exception:
            return None
    stories = await asyncio.gather(*[one(i) for i in ids])
    return [s for s in stories if s][:10]


async def run_collection(region: str) -> Dict[str, Any]:
    if region not in REGIONS:
        raise HTTPException(status_code=400, detail=f"Región inválida: {region}")

    run_id = "run_" + str(int(time.time() * 1000))
    region_def = REGIONS[region]
    results: List[Dict[str, Any]] = []

    timeout = httpx.Timeout(14.0, connect=8.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        tasks = []

        for lang, _name in region_def["wiki"]:
            async def task_wiki(lang=lang):
                source = f"wiki-{lang}"
                items = await collect_wikipedia(client, lang)
                bucket = "es" if lang in HISPANO_LANGS else "intl"
                record_source(run_id, region, source, lang, bucket, items)
                return {"source": source, "geo": lang, "bucket": bucket, "items": items, "ok": True}
            tasks.append(task_wiki())

        for geo, _name in region_def["trends"]:
            async def task_trends(geo=geo):
                source = f"gtrends-{geo}"
                items = await collect_google_trends(client, geo)
                bucket = "es" if geo in HISPANO_GEOS else "intl"
                record_source(run_id, region, source, geo, bucket, items)
                return {"source": source, "geo": geo, "bucket": bucket, "items": items, "ok": True}
            tasks.append(task_trends())

        async def task_reddit():
            items = await collect_reddit(client)
            record_source(run_id, region, "reddit", "reddit", "intl", items)
            return {"source": "reddit", "geo": "reddit", "bucket": "intl", "items": items, "ok": True}
        tasks.append(task_reddit())

        async def task_masto_tags():
            items = await collect_mastodon_tags(client)
            record_source(run_id, region, "mastodon-tags", "mastodon", "intl", items)
            return {"source": "mastodon-tags", "geo": "mastodon", "bucket": "intl", "items": items, "ok": True}
        tasks.append(task_masto_tags())

        async def task_masto_links():
            items = await collect_mastodon_links(client)
            record_source(run_id, region, "mastodon-links", "mastodon", "intl", items)
            return {"source": "mastodon-links", "geo": "mastodon", "bucket": "intl", "items": items, "ok": True}
        tasks.append(task_masto_links())

        async def task_hn():
            items = await collect_hacker_news(client)
            record_source(run_id, region, "hacker-news", "hn", "intl", items)
            return {"source": "hacker-news", "geo": "hn", "bucket": "intl", "items": items, "ok": True}
        tasks.append(task_hn())

        settled = await asyncio.gather(*tasks, return_exceptions=True)

    for r in settled:
        if isinstance(r, Exception):
            results.append({"ok": False, "error": str(r)})
        else:
            results.append(r)

    outbreak_alerts = detect_outbreak_alerts(run_id)
    await maybe_send_telegram_alerts(outbreak_alerts)

    return {
        "run_id": run_id,
        "region": region,
        "region_label": REGIONS[region]["label"],
        "sources": results,
        "outbreak_alerts": outbreak_alerts,
    }


def aggregate_terms(limit: int = 100, min_score: float = 0.0, filter_numeric: bool = True, window_hours: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Aggregate terms with optional numeric noise filtering and time window.
    Set filter_numeric=False to include years like 2026, 1999 in results.
    Set window_hours to filter hits within last N hours (e.g., 24 for last day).
    """
    with get_db() as db:
        # P2 #18: Build query with optional time window
        where_clause = ""
        params = [min_score, limit * 2]
        
        if window_hours:
            cutoff_ts = now_ts() - (window_hours * 3600)
            where_clause = f"WHERE ts >= {cutoff_ts}"
            params = [min_score, limit * 2]
        
        query = f"""
            SELECT
              term,
              SUM(score) AS total,
              SUM(CASE WHEN bucket='es' THEN score ELSE 0 END) AS es_score,
              SUM(CASE WHEN bucket='intl' THEN score ELSE 0 END) AS intl_score,
              MIN(ts) AS first_seen,
              MAX(ts) AS last_seen,
              COUNT(DISTINCT title_hash) AS hits,
              COUNT(DISTINCT run_id) AS runs,
              COUNT(DISTINCT geo) AS regions,
              COUNT(DISTINCT source) AS sources
            FROM term_hits
            {where_clause}
            GROUP BY term
            HAVING total >= ?
            ORDER BY total DESC
            LIMIT ?
        """
        
        rows = db.execute(query, params).fetchall()  # Fetch more to account for filtering

        out = []
        for r in rows:
            # P0: Filter numeric noise (years like 2026, 1999)
            if filter_numeric and is_numeric_noise(r["term"]):
                continue
            geos = db.execute("""
                SELECT geo, SUM(score) AS score
                FROM term_hits WHERE term=?
                GROUP BY geo ORDER BY score DESC
            """, (r["term"],)).fetchall()
            sources = db.execute("""
                SELECT source, SUM(score) AS score
                FROM term_hits WHERE term=?
                GROUP BY source ORDER BY score DESC
            """, (r["term"],)).fetchall()
            # P1: Calcular score de diversidad (favorece términos en múltiples fuentes/títulos)
            # Fórmula: total × log(1 + sources) × log(1 + regions) / log(1 + hits)
            # Esto premia términos que aparecen en muchas fuentes distintas vs. uno viral
            diversity_multiplier = (
                (1 + math.log1p(r["sources"])) * 
                (1 + math.log1p(r["regions"])) / 
                (1 + math.log1p(r["hits"]))
            )
            diversity_score = round((r["total"] or 0) * diversity_multiplier, 3)
            
            out.append({
                "term": r["term"],
                "total": round(r["total"] or 0, 3),
                "es_score": round(r["es_score"] or 0, 3),
                "intl_score": round(r["intl_score"] or 0, 3),
                "first_seen": r["first_seen"],
                "last_seen": r["last_seen"],
                "hits": r["hits"],
                "runs": r["runs"],
                "regions": r["regions"],
                "sources": r["sources"],
                "diversity_score": diversity_score,  # P1: Score con componente de diversidad
                "geos": [{"geo": g["geo"], "name": GEO_NAMES.get(g["geo"], g["geo"]), "score": round(g["score"], 3)} for g in geos],
                "source_breakdown": [{"source": s["source"], "score": round(s["score"], 3)} for s in sources],
            })
        return out


def run_scores_for_term(term: str) -> List[Tuple[str, float, float]]:
    with get_db() as db:
        rows = db.execute("""
            SELECT run_id, MAX(ts) AS ts, SUM(score) AS score
            FROM term_hits
            WHERE term=?
            GROUP BY run_id
            ORDER BY ts ASC
        """, (term,)).fetchall()
    return [(r["run_id"], r["ts"], r["score"] or 0.0) for r in rows]


def first_hit_for_term(term: str) -> Optional[Dict[str, Any]]:
    with get_db() as db:
        r = db.execute("""
            SELECT * FROM term_hits WHERE term=? ORDER BY ts ASC LIMIT 1
        """, (term,)).fetchone()
    return dict(r) if r else None


def classify_outbreak(stat: Dict[str, Any]) -> str:
    if stat["regions"] >= 3 and stat["sources"] >= 3 and stat["runs"] >= 2 and stat["emergency"] >= 70:
        return "EVENTO"
    if (stat["regions"] >= 2 or stat["sources"] >= 3) and stat["emergency"] >= 52:
        return "PROPAGACIÓN"
    if stat["runs"] >= 2 and stat["delta"] > 0 and stat["emergency"] >= 38:
        return "BROTE"
    if stat["age_hours"] <= 30 or stat["runs"] == 1:
        return "SEMILLA"
    return "RUIDO"


def outbreak_reading(stat: Dict[str, Any]) -> str:
    origin = stat.get("first_geo_name") or "—"
    if stat["estado"] == "EVENTO":
        return f"Evento fuerte: nació en {origin}, combina varias fuentes y regiones. Requiere verificación externa."
    if stat["estado"] == "PROPAGACIÓN":
        return f"Se está propagando: origen {origin}; alcanzó {stat['regions']} regiones y {stat['sources']} fuentes."
    if stat["estado"] == "BROTE":
        return f"Brote temprano: repite en muestras y aceleró {stat['delta']:+.1f}. Conviene seguirlo."
    if stat["estado"] == "SEMILLA":
        return f"Semilla nueva: primera señal en {origin}. Puede ser ruido o inicio de fenómeno."
    if stat["es_score"] > 0 and stat["intl_score"] > 0:
        return "Tiene cruce hispano/internacional, pero sin aceleración fuerte todavía."
    return "Señal débil: mirar si repite en la próxima muestra."


def detect_outbreaks(limit: int = 100) -> List[Dict[str, Any]]:
    """
    Detector de brotes mejorado con:
    - Filtro anti-ruido (palabras genéricas)
    - Priorización de frases sobre palabras sueltas
    - Clasificación por categorías
    - Nivel de confianza
    - P0: Optimizado para eliminar N+1 queries (3 queries totales en lugar de 3000-4000)
    - P1: Cache en memoria con TTL de 30 segundos
    """
    global _outbreaks_cache, _outbreaks_cache_ts
    
    # P1: Verificar cache - solo recalcular si pasaron 30 segundos o cambió el limit
    cache_key = f"outbreaks_{limit}"
    now = now_ts()
    if cache_key in _outbreaks_cache and (now - _outbreaks_cache_ts) < OUTBREAKS_CACHE_TTL:
        return _outbreaks_cache[cache_key][:limit]
    
    t_now = now_ts()
    settings = get_settings()
    threshold = float(settings.get("outbreak_threshold", "45") or 45)
    
    # P0: Single optimized query to get all term data with run scores and first hit
    with get_db() as db:
        # Main query: get aggregated terms with all needed metrics
        rows = db.execute("""
            SELECT 
                term,
                SUM(score) AS total,
                SUM(CASE WHEN bucket='es' THEN score ELSE 0 END) AS es_score,
                SUM(CASE WHEN bucket='intl' THEN score ELSE 0 END) AS intl_score,
                MIN(ts) AS first_seen,
                MAX(ts) AS last_seen,
                COUNT(*) AS hits,
                COUNT(DISTINCT run_id) AS runs,
                COUNT(DISTINCT geo) AS regions,
                COUNT(DISTINCT source) AS sources
            FROM term_hits
            GROUP BY term
            HAVING total >= 0.5
            ORDER BY total DESC
            LIMIT 1000
        """).fetchall()
        
        # Query 2: Get last two run scores for all terms (for delta calculation)
        run_scores_rows = db.execute("""
            SELECT term, run_id, MAX(ts) as ts, SUM(score) as score
            FROM term_hits
            GROUP BY term, run_id
            ORDER BY term, ts ASC
        """).fetchall()
        
        # Query 3: Get first hit geo for all terms
        first_geo_rows = db.execute("""
            SELECT term, geo
            FROM term_hits
            GROUP BY term
            HAVING MIN(ts)
        """).fetchall()
    
    # Build lookup dicts
    term_runs: Dict[str, List[Tuple[str, float, float]]] = {}
    for r in run_scores_rows:
        if r["term"] not in term_runs:
            term_runs[r["term"]] = []
        term_runs[r["term"]].append((r["run_id"], r["ts"], r["score"] or 0.0))
    
    first_geo_map: Dict[str, str] = {r["term"]: r["geo"] for r in first_geo_rows}
    
    out: List[Dict[str, Any]] = []
    
    for r in rows:
        term = r["term"]
        scores = term_runs.get(term, [])
        
        if len(scores) < 1:
            continue
            
        last = scores[-1][2]
        prev = scores[-2][2] if len(scores) > 1 else 0.0
        delta = last - prev
        age_hours = max(0.01, (t_now - (r["first_seen"] or t_now)) / 3600.0)
        
        # Contar palabras en el término
        word_count = len(term.split())
        
        # Filtro anti-ruido: palabras genéricas solas
        is_generic = is_generic_term(term)
        
        # Bonus por frases específicas
        phrase_bonus = 0
        if word_count == 2:
            phrase_bonus = 5
        elif word_count == 3:
            phrase_bonus = 12
        elif word_count >= 4:
            phrase_bonus = 18
        
        generic_penalty = -15 if (is_generic and word_count == 1) else 0

        novelty = 25 * (1 - age_hours / 48.0) if age_hours <= 48 else 0
        growth = min(35, max(0, (delta / max(prev, 1.0)) * 22)) if prev > 0 else min(28, last * 6)
        delta_score = min(30, max(0, delta * 7))
        region_score = max(0, r["regions"] - 1) * 12
        source_score = max(0, r["sources"] - 1) * 10
        repeat_score = min(r["runs"], 5) * 4
        cross_score = 12 if r["es_score"] > 0 and r["intl_score"] > 0 else 0
        small_bonus = 12 if r["total"] < 24 and (r["regions"] >= 2 or r["sources"] >= 2 or delta > 1.2) else 0

        emergency = max(0, novelty + growth + delta_score + region_score + source_score + repeat_score + cross_score + small_bonus + phrase_bonus + generic_penalty)
        
        # Build term dict for calculate_confidence
        t = {
            "term": term,
            "total": r["total"],
            "es_score": r["es_score"],
            "intl_score": r["intl_score"],
            "first_seen": r["first_seen"],
            "last_seen": r["last_seen"],
            "hits": r["hits"],
            "runs": r["runs"],
            "regions": r["regions"],
            "sources": r["sources"],
        }
        
        confidence = calculate_confidence(t)
        category = classify_category(term)
        phenomenon = get_phenomenon(term)
        first_geo = first_geo_map.get(term, "")

        stat = {
            **t,
            "last_run_score": round(last, 3),
            "prev_run_score": round(prev, 3),
            "delta": round(delta, 3),
            "age_hours": round(age_hours, 2),
            "emergency": round(emergency, 2),
            "threshold": threshold,
            "first_geo": first_geo,
            "first_geo_name": GEO_NAMES.get(first_geo, first_geo),
            "word_count": word_count,
            "is_generic": is_generic,
            "category": category,
            "phenomenon": phenomenon,
            "confidence": confidence,
        }
        stat["estado"] = classify_outbreak(stat)
        stat["reading"] = outbreak_reading(stat)
        stat["alert_level"] = get_alert_level(stat["estado"], confidence)
        
        # Actualizar bandeja de observación
        update_observation_tray(stat)
        
        out.append(stat)

    # P2 #20: Eliminado ordenamiento por emergency aquí. 
    # filter_and_rank_outbreaks en api_outbreaks ordena por visual_score.
    # Evita doble reordenamiento innecesario.
    
    # P1: Guardar en cache (sin ordenar)
    _outbreaks_cache[cache_key] = out
    _outbreaks_cache_ts = now_ts()
    
    return out


def detect_outbreak_alerts(run_id: str) -> List[Dict[str, Any]]:
    """
    Generar alertas con el nuevo sistema de 3 niveles:
    - DETECTADO: en bandeja de observación
    - OBSERVADO: visible como brote
    - ALERTADO: notificación activa (con cooldown)
    """
    settings = get_settings()
    threshold = float(settings.get("outbreak_threshold", "45") or 45)
    outbreaks = detect_outbreaks(limit=50)
    created = []
    
    # Extraer lista de todos los términos para supresión de componentes
    all_terms = [s["term"] for s in outbreaks]

    with get_db() as db:
        for s in outbreaks:
            if s["emergency"] < threshold:
                continue
            
            # Verificar si es término de watchlist
            is_watchlist = db.execute(
                "SELECT 1 FROM watchlist WHERE term = ?", (s["term"],)
            ).fetchone() is not None
            
            # Decidir si debe alertar según nuevas reglas (con supresión de componentes)
            should_alert_flag, alert_reason = should_alert(s, is_watchlist, all_terms)
            
            if not should_alert_flag:
                continue
            
            # Verificar cooldown
            if not check_alert_cooldown(s["term"], s["estado"]):
                continue
            
            # Only alert if term appeared in the current run.
            current = db.execute("""
                SELECT SUM(score) AS score FROM term_hits WHERE run_id=? AND term=?
            """, (run_id, s["term"])).fetchone()
            if not current or not (current["score"] or 0) > 0:
                continue

            # Verificar si ya existe alerta para este run
            exists = db.execute("""
                SELECT id FROM alerts
                WHERE type='brote' AND term=? AND json_extract(meta_json, '$.run_id')=?
                LIMIT 1
            """, (s["term"], run_id)).fetchone()
            if exists:
                continue

            # Construir mensaje con categoría si existe
            category_prefix = f"[{s['category'].upper()}] " if s.get('category') else ""
            phenomenon_suffix = f" (fenómeno: {s['phenomenon']})" if s.get('phenomenon') else ""
            
            confidence = s.get("confidence", "BAJA")
            alert_level = s.get("alert_level", "OBSERVADO")
            
            level = "alta" if s["estado"] == "EVENTO" else ("media" if s["estado"] == "PROPAGACIÓN" else "baja")
            msg = f"{category_prefix}{s['estado']}: '{s['term']}'{phenomenon_suffix} · emergencia {s['emergency']:.0f} · confianza {confidence} · delta {s['delta']:+.1f}. {s['reading']}"
            
            meta = {**s, "run_id": run_id, "alert_reason": alert_reason}
            
            db.execute(
                "INSERT INTO alerts(ts, type, term, level, confidence, alert_level, message, meta_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (now_ts(), "brote", s["term"], level, confidence, alert_level, msg, json.dumps(meta, ensure_ascii=False)),
            )
            created.append({"term": s["term"], "level": level, "confidence": confidence, "alert_level": alert_level, "message": msg, "meta": meta})

    return created


async def maybe_send_telegram_alerts(alerts: List[Dict[str, Any]]) -> None:
    if not alerts:
        return
    settings = get_settings()
    if settings.get("telegram_enabled", "false").lower() != "true":
        return
    token = settings.get("telegram_bot_token", "").strip()
    chat_id = settings.get("telegram_chat_id", "").strip()
    if not token or not chat_id:
        return

    async with httpx.AsyncClient(timeout=10.0) as client:
        for a in alerts:
            text = "🚨 BROTE DETECTADO\n\n" + a["message"]
            try:
                await client.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={"chat_id": chat_id, "text": text},
                )
            except Exception as e:
                # P1: Loguear errores de Telegram en lugar de silenciar
                print(f"[Telegram Error] {type(e).__name__}: {str(e)[:100]}")


def latest_samples(limit: int = 80) -> List[Dict[str, Any]]:
    with get_db() as db:
        rows = db.execute("""
            SELECT * FROM samples ORDER BY ts DESC LIMIT ?
        """, (limit,)).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        try:
            d["items"] = json.loads(d.pop("raw_json"))
        except Exception:
            d["items"] = []
        d["geo_name"] = GEO_NAMES.get(d["geo"], d["geo"])
        return_region = REGIONS.get(d["region"], {})
        d["region_label"] = return_region.get("label", d["region"])
        out.append(d)
    return out


def get_alerts(limit: int = 50) -> List[Dict[str, Any]]:
    with get_db() as db:
        rows = db.execute("SELECT * FROM alerts ORDER BY ts DESC LIMIT ?", (limit,)).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        try:
            d["meta"] = json.loads(d.pop("meta_json"))
        except Exception:
            d["meta"] = {}
        out.append(d)
    return out


def build_report() -> str:
    terms = aggregate_terms(limit=40)
    outbreaks = detect_outbreaks(limit=20)
    alerts = get_alerts(limit=20)
    with get_db() as db:
        samples_count = db.execute("SELECT COUNT(*) AS n FROM samples").fetchone()["n"]
        hits_count = db.execute("SELECT COUNT(*) AS n FROM term_hits").fetchone()["n"]

    lines = []
    lines.append("=" * 80)
    lines.append("OBSERVATORIO VIVO v6 · INFORME DE INTELIGENCIA DE TENDENCIAS")
    lines.append(time.strftime("Generado: %Y-%m-%d %H:%M:%S"))
    lines.append(f"Muestras: {samples_count}")
    lines.append(f"Impactos de términos: {hits_count}")
    lines.append("=" * 80)
    lines.append("")
    lines.append("BROTES / FENÓMENOS NACIENTES")
    for i, s in enumerate(outbreaks, start=1):
        lines.append(
            f"{i:02d}. {s['estado']} · {s['term']} · emergencia {s['emergency']:.0f} · "
            f"delta {s['delta']:+.1f} · regiones {s['regions']} · fuentes {s['sources']}"
        )
        lines.append(f"    {s['reading']}")
    lines.append("")
    lines.append("TOP TÉRMINOS")
    for i, t in enumerate(terms, start=1):
        lines.append(
            f"{i:02d}. {t['term']} · score {t['total']:.1f} · hispano {t['es_score']:.1f} · "
            f"intl {t['intl_score']:.1f} · regiones {t['regions']} · fuentes {t['sources']}"
        )
    lines.append("")
    lines.append("ÚLTIMAS ALERTAS")
    for a in alerts:
        lines.append(f"- {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(a['ts']))} · {a['level']} · {a['message']}")
    lines.append("")
    lines.append("Fuentes públicas: Wikipedia Pageviews · Google Trends RSS · Reddit · Mastodon · Hacker News")
    lines.append("Persistencia local: SQLite")
    lines.append("=" * 80)
    return "\n".join(lines)


def export_csv() -> str:
    with get_db() as db:
        rows = db.execute("""
            SELECT ts, run_id, region, source, geo, bucket, top_title
            FROM samples ORDER BY ts DESC
        """).fetchall()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["ts", "datetime", "run_id", "region", "source", "geo", "bucket", "top_title"])
    for r in rows:
        writer.writerow([
            r["ts"],
            time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(r["ts"])),
            r["run_id"],
            r["region"],
            r["source"],
            r["geo"],
            r["bucket"],
            r["top_title"],
        ])
    return buf.getvalue()


init_db()
app = FastAPI(title="Observatorio Vivo v6.1.5", version="6.1.5")

# P2: CORSMiddleware para permitir consumo desde apps locales
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")


@app.get("/api/health")
def health() -> Dict[str, Any]:
    return {"ok": True, "db": str(DB_PATH), "ts": now_ts()}


@app.get("/api/state")
def state() -> Dict[str, Any]:
    with get_db() as db:
        samples_count = db.execute("SELECT COUNT(*) AS n FROM samples").fetchone()["n"]
        hits_count = db.execute("SELECT COUNT(*) AS n FROM term_hits").fetchone()["n"]
        runs_count = db.execute("SELECT COUNT(DISTINCT run_id) AS n FROM samples").fetchone()["n"]
        watch = [r["term"] for r in db.execute("SELECT term FROM watchlist ORDER BY term")]
        aliases = [dict(r) for r in db.execute("SELECT alias, canonical, phenomenon FROM aliases ORDER BY canonical, alias")]
        
        # P1: Contadores por nivel usando SQL directo sobre observation_tray (más rápido que detect_outbreaks)
        # DETECTADO = RUIDO, OBSERVADO = BAJA sin alerta, ALERTADO = MEDIA/ALTA con estado activo
        detected_count = db.execute(
            "SELECT COUNT(*) AS n FROM observation_tray WHERE estado = 'RUIDO'"
        ).fetchone()["n"]
        observed_count = db.execute(
            "SELECT COUNT(*) AS n FROM observation_tray WHERE confidence = 'BAJA' AND estado != 'RUIDO'"
        ).fetchone()["n"]
        alerted_count = db.execute(
            """SELECT COUNT(*) AS n FROM observation_tray 
               WHERE confidence IN ('MEDIA', 'ALTA') 
               AND estado IN ('BROTE', 'PROPAGACIÓN', 'EVENTO')"""
        ).fetchone()["n"]
        
        # NUEVO: Contadores históricos de alertas
        alerts_total_count = db.execute("SELECT COUNT(*) AS n FROM alerts WHERE type='brote'").fetchone()["n"]
        alerts_alerted_count = db.execute(
            "SELECT COUNT(*) AS n FROM alerts WHERE type='brote' AND alert_level='ALERTADO'"
        ).fetchone()["n"]
        alerts_observed_count = db.execute(
            "SELECT COUNT(*) AS n FROM alerts WHERE type='brote' AND alert_level='OBSERVADO'"
        ).fetchone()["n"]
        
    return {
        "settings": get_settings(),
        "samples_count": samples_count,
        "hits_count": hits_count,
        "runs_count": runs_count,
        "watchlist": watch,
        "aliases": aliases,
        "regions": REGIONS,
        "latest_samples": latest_samples(limit=40),
        "alerts": get_alerts(limit=30),
        "alert_levels": {
            "detectado": detected_count,
            "observado": observed_count,
            "alertado": alerted_count,
        },
        "categories": list(CATEGORIES.keys()),
        # NUEVO: Contadores históricos de alertas
        "alerts_stats": {
            "visible_count": 30,  # Las que se devuelven en "alerts"
            "total_count": alerts_total_count,
            "alerted_count": alerts_alerted_count,
            "observed_count": alerts_observed_count,
        },
    }


@app.post("/api/run")
async def api_run(region: str = "hispano") -> Dict[str, Any]:
    return await run_collection(region)


@app.get("/api/terms")
def api_terms(limit: int = Query(80, ge=1, le=500)) -> Dict[str, Any]:
    """
    Obtener términos agregados con filtro de componentes.
    No muestra términos que son parte de frases más largas (evita duplicados).
    """
    all_terms = aggregate_terms(limit=limit * 2)  # Fetch more for filtering
    # P0: Filter out components of better phrases
    filtered = [t for t in all_terms if not is_component_of_better_phrase(t["term"], [x["term"] for x in all_terms])]
    return {"terms": filtered[:limit]}


@app.get("/api/outbreaks")
def api_outbreaks(limit: int = 80, filter_level: str = "all", visual_ranking: bool = True) -> Dict[str, Any]:
    """
    Obtener brotes con ranking visual mejorado.
    
    Args:
        limit: Cantidad máxima de resultados
        filter_level: Filtrar por nivel de alerta (detectado/observado/alertado/all)
        visual_ranking: Si True, aplica ranking por especificidad (default: True)
    """
    # Obtener watchlist para el ranking
    with get_db() as db:
        watchlist_terms = {r["term"] for r in db.execute("SELECT term FROM watchlist")}
    
    # Detectar brotes
    outbreaks = detect_outbreaks(limit=limit * 2 if visual_ranking else limit)
    
    # Aplicar ranking visual si está habilitado
    if visual_ranking:
        outbreaks = filter_and_rank_outbreaks(outbreaks, watchlist_terms, min_emergency=20.0)
    
    # Filtrar por nivel de alerta si se especifica
    if filter_level != "all":
        outbreaks = [o for o in outbreaks if o.get("alert_level", "").lower() == filter_level.lower()]
    
    # Limitar resultados
    outbreaks = outbreaks[:limit]
    
    return {"outbreaks": outbreaks}


@app.get("/api/observation-tray")
def api_observation_tray(limit: int = 50) -> Dict[str, Any]:
    """Bandeja de observación: señales detectadas que están siendo monitoreadas"""
    return {"tray": get_observation_tray(limit=limit)}


@app.get("/api/hot-topics")
def api_hot_topics(limit: int = 20) -> Dict[str, Any]:
    """Temas calientes por volumen (vs brotes que son por aceleración)"""
    terms = aggregate_terms(limit=100, min_score=2.0)
    
    # Filtrar solo temas de alta confianza o volumen
    hot = []
    for t in terms[:limit]:
        confidence = calculate_confidence(t)
        category = classify_category(t["term"])
        hot.append({
            **t,
            "confidence": confidence,
            "category": category,
            "type": "volumen" if t["runs"] >= 3 else "emergente",
        })
    
    return {"hot_topics": hot}


@app.get("/api/categories/{category}")
def api_category(category: str, limit: int = 30) -> Dict[str, Any]:
    """Obtener brotes filtrados por categoría temática"""
    outbreaks = detect_outbreaks(limit=200)
    filtered = [o for o in outbreaks if o.get("category") == category.lower()]
    return {"category": category, "outbreaks": filtered[:limit]}


@app.get("/api/phenomena")
def api_phenomena() -> Dict[str, Any]:
    """Obtener lista de fenómenos agrupados desde aliases"""
    with get_db() as db:
        rows = db.execute("SELECT DISTINCT phenomenon FROM aliases WHERE phenomenon IS NOT NULL").fetchall()
        phenomena = [r["phenomenon"] for r in rows if r["phenomenon"]]
    return {"phenomena": phenomena}


@app.get("/api/term/{term}")
def api_term(term: str) -> Dict[str, Any]:
    canonical = canonicalize(term)
    with get_db() as db:
        hits = [dict(r) for r in db.execute("""
            SELECT * FROM term_hits WHERE term=? ORDER BY ts ASC LIMIT 500
        """, (canonical,))]
    if not hits:
        return {"term": canonical, "hits": [], "summary": None}

    summary = next((t for t in aggregate_terms(limit=1000) if t["term"] == canonical), None)
    return {"term": canonical, "summary": summary, "hits": hits}


@app.get("/api/signal-origin/{term}")
def api_signal_origin(term: str) -> Dict[str, Any]:
    """
    Endpoint de trazabilidad estricta: muestra el origen completo de una señal.
    Combina información de tema caliente (términos) y brote (outbreaks).
    La evidencia proviene EXCLUSIVAMENTE de term_hits para evitar ruido de samples generales.
    
    P1: Optimizado para llamar aggregate_terms solo una vez (antes 3 veces).
    """
    canonical = canonicalize(term)
    
    # P1: Single call to aggregate_terms - reused for summary and hot_rank
    all_terms = aggregate_terms(limit=1000)
    summary = next((t for t in all_terms if t["term"] == canonical), None)
    
    with get_db() as db:
        # 1. Obtener hits del término directamente de term_hits (evidencia estricta)
        # Campos: title, url, source, geo, region, ts, score, run_id, bucket
        hits = [dict(r) for r in db.execute("""
            SELECT term, title, url, source, geo, region, ts, score, run_id, bucket
            FROM term_hits
            WHERE term = ?
            ORDER BY ts DESC, score DESC
            LIMIT 100
        """, (canonical,))]
        
        # 2. Información de brote (si existe)
        outbreak_info = None
        all_outbreaks = detect_outbreaks(limit=200)
        for o in all_outbreaks:
            if o.get("term") == canonical:
                outbreak_info = o
                break
        
        # 3. Determinar tipo de señal (con regla delta > 0 para "both")
        is_hot = summary is not None and summary.get("total", 0) > 0
        is_outbreak = outbreak_info is not None
        outbreak_delta = outbreak_info.get("delta", 0) if outbreak_info else 0
        
        signal_type = "unknown"
        if is_hot and is_outbreak and outbreak_delta > 0:
            signal_type = "both"  # Es tema caliente Y brote activo (delta > 0)
        elif is_hot and is_outbreak and outbreak_delta <= 0:
            signal_type = "hot_topic"  # Es tema caliente, brote sin aceleración actual
        elif is_hot:
            signal_type = "hot_topic"  # Solo tema caliente
        elif is_outbreak:
            signal_type = "outbreak"  # Solo brote
        
        # 4. Calcular ranking en listas (reuse all_terms)
        hot_rank = None
        if is_hot:
            for i, t in enumerate(all_terms):
                if t["term"] == canonical:
                    hot_rank = i + 1
                    break
        
        # 6. Construir breakdown de fuentes y regiones desde term_hits
        sources_breakdown = {}
        regions_breakdown = {}
        evidence_titles = []
        timeline = []
        
        for hit in hits:
            # Fuentes directamente del hit
            source = hit.get("source") or "unknown"
            sources_breakdown[source] = sources_breakdown.get(source, 0) + 1
            
            # Regiones directamente del hit
            region = hit.get("region") or hit.get("geo") or "unknown"
            regions_breakdown[region] = regions_breakdown.get(region, 0) + 1
            
            # Evidencia: título ORIGINAL que generó el hit (desde term_hits.title)
            # Si no hay title, usamos bucket como fallback
            original_title = hit.get("title") or hit.get("bucket") or ""
            if original_title:
                evidence_titles.append({
                    "title": original_title,
                    "source": source,
                    "region": region,
                    "ts": hit.get("ts"),
                    "score": hit.get("score"),
                    "url": hit.get("url"),
                    "run_id": hit.get("run_id")
                })
            
            # Timeline
            timeline.append({
                "ts": hit.get("ts"),
                "run_id": hit.get("run_id"),
                "score": hit.get("score"),
                "source": source,
                "region": region
            })
        
        # 7. Construir explicaciones según tipo (más descriptivas)
        explanation = ""
        explanation_short = ""
        if signal_type == "hot_topic":
            if is_outbreak and outbreak_delta <= 0:
                explanation = "Domina por volumen acumulado en term_hits, pero no muestra aceleración actual (delta ≤ 0). Es tema caliente sin brote activo."
                explanation_short = "Sale del score acumulado en term_hits. Tema caliente por volumen, sin aceleración actual."
            else:
                explanation = "Sale del score acumulado en term_hits. Es un tema caliente por volumen de menciones."
                explanation_short = "Tema caliente: sale del score acumulado en term_hits."
        elif signal_type == "outbreak":
            explanation = "Sale del ranking visual por emergencia + especificidad + delta positivo + cruces de regiones/fuentes. Es un brote por aceleración detectada."
            explanation_short = "Brote: sale de emergencia + especificidad + delta + regiones + fuentes."
        elif signal_type == "both":
            explanation = "Es tanto tema caliente (por volumen acumulado en term_hits) como brote activo (por aceleración con delta > 0)."
            explanation_short = "Tema caliente + Brote activo: volumen en term_hits + aceleración detectada."
        else:
            explanation = "Término registrado pero sin actividad significativa reciente en term_hits."
            explanation_short = "Sin actividad significativa reciente."
        
        # 8. Primera y última señal (timeline está ordenado DESC, así que invertimos)
        timeline_asc = list(reversed(timeline))
        first_signal = timeline_asc[0] if timeline_asc else None
        last_signal = timeline_asc[-1] if timeline_asc else None
        
        return {
            "term": canonical,
            "original_term": term,
            "signal_type": signal_type,
            "explanation": explanation,
            "explanation_short": explanation_short,
            "summary": {
                "hot_rank": hot_rank,
                "total_score": summary.get("total") if summary else 0,
                "es_score": summary.get("es_score") if summary else 0,
                "intl_score": summary.get("intl_score") if summary else 0,
                "regions_count": summary.get("regions") if summary else 0,
                "sources_count": summary.get("sources") if summary else 0,
            },
            "outbreak": outbreak_info,
            "sources_breakdown": sources_breakdown,
            "regions_breakdown": regions_breakdown,
            "first_signal": first_signal,
            "last_signal": last_signal,
            "evidence_titles": evidence_titles[:20],  # Últimos 20 títulos de term_hits
            "timeline": timeline_asc,
            "total_hits": len(hits),
            "evidence_source": "term_hits",  # Indica que la evidencia es estricta desde term_hits
        }


@app.get("/api/state")
def api_state() -> Dict[str, Any]:
    return {"alerts": get_alerts(limit=50)}


@app.post("/api/watchlist")
def api_add_watch(item: WatchIn) -> Dict[str, Any]:
    term = normalize(item.term)
    if not term:
        raise HTTPException(400, "Término vacío")
    with get_db() as db:
        db.execute("INSERT OR IGNORE INTO watchlist(term, created_ts) VALUES (?, ?)", (term, now_ts()))
    return {"ok": True, "term": term}


@app.delete("/api/watchlist/{term}")
def api_del_watch(term: str) -> Dict[str, Any]:
    term = normalize(term)
    with get_db() as db:
        db.execute("DELETE FROM watchlist WHERE term=?", (term,))
    return {"ok": True, "term": term}


@app.post("/api/aliases")
def api_add_alias(item: AliasIn) -> Dict[str, Any]:
    alias = normalize(item.alias)
    canonical = normalize(item.canonical)
    phenomenon = item.phenomenon.strip() if item.phenomenon else None
    if not alias or not canonical:
        raise HTTPException(400, "Alias o canonical vacío")
    with get_db() as db:
        db.execute(
            "INSERT INTO aliases(alias, canonical, phenomenon, created_ts) VALUES (?, ?, ?, ?) ON CONFLICT(alias) DO UPDATE SET canonical=excluded.canonical, phenomenon=excluded.phenomenon",
            (alias, canonical, phenomenon, now_ts()),
        )
    return {"ok": True, "alias": alias, "canonical": canonical, "phenomenon": phenomenon}


@app.post("/api/settings")
def api_settings(item: SettingsIn) -> Dict[str, Any]:
    if item.outbreak_threshold is not None:
        set_setting("outbreak_threshold", str(item.outbreak_threshold))
    if item.telegram_enabled is not None:
        set_setting("telegram_enabled", "true" if item.telegram_enabled else "false")
    if item.telegram_bot_token is not None:
        set_setting("telegram_bot_token", item.telegram_bot_token)
    if item.telegram_chat_id is not None:
        set_setting("telegram_chat_id", item.telegram_chat_id)
    return {"ok": True, "settings": get_settings()}


@app.post("/api/telegram/test")
async def api_telegram_test() -> Dict[str, Any]:
    await maybe_send_telegram_alerts([{
        "message": "Prueba de Telegram desde Observatorio Vivo v6.",
        "term": "test",
        "level": "info",
        "meta": {},
    }])
    return {"ok": True}


@app.get("/api/report", response_class=PlainTextResponse)
def api_report() -> str:
    return build_report()


@app.get("/api/export/json")
def api_export_json() -> JSONResponse:
    """
    Exportar datos completos en JSON.
    P1: Optimizado para evitar trabajo redundante (state() ya no llama detect_outbreaks).
    """
    # P1: Llamar state() una sola vez - ya no incluye detect_outbreaks() pesado
    state_data = state()
    
    # P1: Una sola llamada a aggregate_terms, reutilizada
    terms_data = aggregate_terms(limit=1000)
    
    # P1: detect_outbreaks usa cache TTL (30s), así que esta llamada es rápida si ya se ejecutó
    outbreaks_data = detect_outbreaks(limit=200)
    
    with get_db() as db:
        watchlist_data = [r["term"] for r in db.execute("SELECT term FROM watchlist ORDER BY term")]
        aliases_data = [dict(r) for r in db.execute("SELECT alias, canonical, phenomenon FROM aliases ORDER BY canonical, alias")]
    
    return JSONResponse({
        "state": state_data,
        "terms": terms_data,
        "outbreaks": outbreaks_data,
        "alerts": get_alerts(limit=50),
        "watchlist": watchlist_data,
        "aliases": aliases_data,
    })


@app.get("/api/export/csv")
def api_export_csv() -> Response:
    return Response(export_csv(), media_type="text/csv; charset=utf-8")


@app.delete("/api/reset")
def api_reset(confirm: str = "", token: str = "") -> Dict[str, Any]:
    """
    Reset completo de la base de datos (⚠️ Irreversible).
    P2: Requiere token de autenticación desde settings (api_reset_token).
    """
    # P2: Verificar token de autenticación
    settings = get_settings()
    expected_token = settings.get("api_reset_token", "")
    if expected_token and token != expected_token:
        raise HTTPException(401, "Token de autenticación inválido")
    
    if confirm != "BORRAR":
        raise HTTPException(400, "Usá confirm=BORRAR para resetear")
    with get_db() as db:
        db.execute("DELETE FROM samples")
        db.execute("DELETE FROM term_hits")
        db.execute("DELETE FROM alerts")
        db.execute("DELETE FROM observation_tray")  # P0: Vaciar también bandeja de observación
    return {"ok": True}
