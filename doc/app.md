# app.py - Backend Principal

## Descripción

Backend completo del Observatorio Vivo v6 construido con **FastAPI**. Gestiona la captura de datos, procesamiento de términos, detección de brotes con sistema de 3 niveles, clasificación por categorías y persistencia en SQLite.

---

## Nuevas Funcionalidades v6.1

### Sistema de 3 Niveles de Alerta
- **DETECTADO**: Señal en bandeja de observación (confianza BAJA)
- **OBSERVADO**: Brote visible sin alerta activa (confianza MEDIA)
- **ALERTADO**: Notificación activa (confianza ALTA)

### Filtro Anti-Ruido
- Palabras genéricas solas (`game`, `people`, `show`) no generan alertas
- Frases específicas (`lakers game`, `dragon ball movie`) sí alertan

### Sistema de Confianza
- **BAJA**: 1 muestra o 1 fuente → observación
- **MEDIA**: 2+ muestras/fuentes → brote visible
- **ALTA**: 3+ regiones/fuentes/runs → alerta

### Categorías Temáticas
- Deporte, Anime/Entretenimiento, IA/Tecnología, Ciberseguridad, Política, Economía, Salud, Producto

### Cooldown de Alertas
- 6 horas entre alertas del mismo término
- Excepción: escalamiento de estado (SEMILLA→BROTE→PROPAGACIÓN→EVENTO)

---

## Estructura del Archivo (~1400 líneas)

### 1. Configuración y Constantes (líneas 1-150)

**Rutas principales:**
```python
APP_DIR   → Directorio de la aplicación
DATA_DIR  → data/ (base de datos)
FRONTEND_DIR → frontend/ (interfaz web)
DB_PATH   → data/observatorio.db
```

**Regiones disponibles** (`REGIONS` dict):
- `hispano` - Argentina, México, Chile, Colombia, España
- `anglo` - EE.UU., Reino Unido, Canadá, Australia
- `europa` - España, Francia, Alemania, Italia, Reino Unido
- `latam` - Argentina, México, Brasil, Colombia, Chile
- `asia` - Japón, India, Corea
- `mundo` - Mix global

**Stopwords** (`STOP` set): Palabras filtradas durante tokenización (~150 palabras comunes en español e inglés)

**Palabras Genéricas** (`GENERIC_WORDS` set): ~100 palabras que solas no generan alerta (game, people, show, video, movie, etc.)

**Categorías** (`CATEGORIES` dict): 8 categorías temáticas con palabras clave asociadas

---

### 2. Funciones de Utilidad (líneas 111-133)

| Función | Descripción |
|---------|-------------|
| `now_ts()` | Timestamp actual (float) |
| `normalize(text)` | Minúsculas, sin acentos, sin puntuación extra |
| `tokenize(text)` | Extrae tokens ≥4 caracteres, excluye stopwords |
| `get_db()` | Conexión SQLite con row_factory=Row |

---

### 3. Inicialización de Base de Datos (líneas 135-229)

**Función `init_db()`**: Crea todas las tablas y datos iniciales.

**Tablas creadas:**

```sql
samples          → Capturas por fuente y región
term_hits        → Términos extraídos con scoring + metadatos (word_count, is_generic, category)
watchlist        → Términos seguidos (default: dragon ball, messi, ransomware, openai)
aliases          → Mapeo de variantes a canónicos + fenómeno asociado
alerts           → Alertas generadas con nivel de confianza y alert_level
observation_tray → Bandeja de observación (señales en monitoreo)
settings         → Configuración del sistema
```

**Aliases por defecto (con fenómenos):**
- leo messi, lionel messi, inter miami → messi (fenómeno: Deporte)
- chatgpt, gpt, gpt 5 → openai (fenómeno: OpenAI/IA)
- dragon ball daima, dbz, goku → dragon ball (fenómeno: Dragon Ball)
- malware, cyber attack → ciberseguridad (fenómeno: Ciberseguridad)

**Settings por defecto:**
- outbreak_threshold = 45
- telegram_enabled = false

**Configuración de alertas:**
- ALERT_COOLDOWN_HOURS = 6 (cooldown entre alertas)
- MIN_DELTA_FOR_ALERT = 0.1 (delta mínimo para alertar)
- MIN_WORDS_FOR_PHRASE = 2 (mínimo de palabras para frase específica)

---

### 4. Gestión de Configuración (líneas 231-252)

```python
get_settings()         → Dict con todas las configuraciones
set_setting(k, v)      → Inserta o actualiza un valor
alias_map()            → Dict {alias: canónico}
canonicalize(term)     → Aplica alias y normaliza
get_phenomenon(term)   → Obtiene fenómeno asociado al término
classify_category(term) → Clasifica término en categoría temática
is_generic_term(term)  → Verifica si es palabra genérica sola
calculate_confidence(stat) → Calcula BAJA/MEDIA/ALTA
should_alert(outbreak, is_watchlist) → Determina si debe alertar
get_alert_level(estado, confidence) → DETECTADO/OBSERVADO/ALERTADO
check_alert_cooldown(term, estado) → Verifica cooldown de 6 horas
update_observation_tray(outbreak) → Actualiza bandeja de observación
get_observation_tray(limit) → Obtiene señales en observación
```

---

### 5. Sistema de Scoring (líneas 254-317)

**Ponderación por fuente** (`source_weight`):
```python
gtrends-*:   base + 1.2   # Mayor prioridad
wiki-*:      base + 0.7
reddit/mastodon/hn: base + 0.4
Ranura 1-10: (12 - rank) / 10.0  # Decreciente
```

**Extracción de frases** (`phrases_from_title`):
- Unigramas: peso 1.0
- Bigramas: peso 0.95
- Trigramas: peso 1.15
- 4-gramas: peso 1.25

**Registro de fuente** (`record_source`):
1. Guarda muestra en tabla `samples`
2. Tokeniza títulos y guarda en `term_hits` con scoring

---

### 6. Colectores de Datos (líneas 319-446)

| Colector | Fuente | Datos extraídos |
|----------|--------|-----------------|
| `collect_wikipedia()` | Wikimedia API | Top 10 artículos por pageviews |
| `collect_google_trends()` | RSS Trends | Tendencias con volumen aproximado |
| `collect_reddit()` | Reddit API | Posts populares de r/popular, r/all |
| `collect_mastodon_tags()` | mastodon.social | Tags trending |
| `collect_mastodon_links()` | mastodon.social | Links trending |
| `collect_hacker_news()` | HN API | Top stories |

**Tiempos de timeout:** 14s lectura, 8s conexión

---

### 7. Ejecución de Captura (líneas 448-519)

**Función `run_collection(region)`**:

1. Valida la región
2. Genera `run_id` único (timestamp)
3. Lanza colectores en paralelo con `asyncio.gather()`
4. Ejecuta `detect_outbreak_alerts()`
5. Envía alertas Telegram si están habilitadas

**Colectores ejecutados por run:**
- Wikipedia (por cada idioma de la región)
- Google Trends (por cada país de la región)
- Reddit (único)
- Mastodon tags (único)
- Mastodon links (único)
- Hacker News (único)

---

### 8. Agregación de Términos (líneas 521-582)

**Función `aggregate_terms(limit, min_score)`**:

Devuelve métricas agregadas por término:
```python
{
  "term": "openai",
  "total": 145.5,           # Score acumulado
  "es_score": 45.2,         # Score hispanohablante
  "intl_score": 100.3,      # Score internacional
  "first_seen": 1745730000, # Primera aparición
  "last_seen": 1745733600,  # Última aparición
  "hits": 12,               # Total impactos
  "runs": 3,                # Muestras donde apareció
  "regions": 4,             # Regiones distintas
  "sources": 6,             # Fuentes distintas
  "geos": [...],            # Desglose por geografía
  "source_breakdown": [...] # Desglose por fuente
}
```

---

### 9. Algoritmo Detector de Brotes (líneas 583-705)

**Funciones principales:**

| Función | Propósito |
|---------|-----------|
| `run_scores_for_term(term)` | Histórico de scores por run |
| `first_hit_for_term(term)` | Primera aparición del término |
| `classify_outbreak(stat)` | Clasifica en EVENTO/PROPAGACIÓN/BROTE/SEMILLA/RUIDO |
| `outbreak_reading(stat)` | Genera lectura interpretativa en lenguaje natural |
| `detect_outbreaks(limit)` | Ejecuta el algoritmo completo |
| `detect_outbreak_alerts(run_id)` | Genera alertas para el run actual |

**Fórmulas de scoring de emergencia:**

```python
novelty      = 25 * (1 - age_hours/48)          # si age ≤ 48h
growth       = min(35, (delta/prev) * 22)       # si prev > 0
delta_score  = min(30, delta * 7)
region_score = (regions - 1) * 12
source_score = (sources - 1) * 10
repeat_score = min(runs, 5) * 4
cross_score  = 12 if es_score > 0 and intl_score > 0 else 0
small_bonus  = 12 if total < 24 and (regions ≥ 2 or sources ≥ 3)

emergency = Σ todas las métricas
```

**Umbrales de clasificación:**
- EVENTO: ≥3 regiones + ≥3 fuentes + ≥2 runs + emergency≥70
- PROPAGACIÓN: (≥2 regiones o ≥3 fuentes) + emergency≥52
- BROTE: ≥2 runs + delta>0 + emergency≥38
- SEMILLA: ≤30h o 1 run
- RUIDO: ninguna condición anterior

---

### 10. Alertas Telegram (líneas 707-728)

**Función `maybe_send_telegram_alerts(alerts)`**:

- Verifica si Telegram está habilitado
- Valida BOT_TOKEN y CHAT_ID
- Envía mensajes asíncronos vía API de Telegram
- Formato: `🚨 BROTE DETECTADO\n\n{message}`

---

### 11. Reportes y Exportación (líneas 730-825)

| Función | Formato | Contenido |
|---------|---------|-----------|
| `latest_samples(limit)` | JSON | Últimas muestras con items deserializados |
| `get_alerts(limit)` | JSON | Alertas con metadata parseada |
| `build_report()` | TXT | Informe completo con brotes, términos top, alertas |
| `export_csv()` | CSV | Histórico de muestras para Excel/análisis |

---

### 12. Modelos Pydantic (líneas 827-841)

```python
WatchIn      → {term: str}
AliasIn      → {alias: str, canonical: str}
SettingsIn   → {outbreak_threshold?, telegram_enabled?, ...}
```

---

### 13. Endpoints FastAPI (líneas 843-998)

#### Endpoints de Estado
```
GET  /api/health              → {"ok": true, "db": "...", "ts": ...}
GET  /api/state               → Estado completo del sistema
```

#### Endpoints de Operación
```
POST /api/run?region={r}      → Ejecutar captura manual
GET  /api/terms?limit={n}     → Listar términos agregados
GET  /api/outbreaks?limit={n}→ Detectar brotes
GET  /api/term/{term}         → Detalle de un término específico
GET  /api/alerts?limit={n}    → Alertas históricas
```

#### Endpoints de Gestión
```
POST /api/watchlist           → Agregar término (body: {term})
DELETE /api/watchlist/{term}  → Eliminar término
POST /api/aliases             → Crear alias (body: {alias, canonical})
POST /api/settings            → Guardar configuración
POST /api/telegram/test       → Probar notificaciones
```

#### Endpoints de Exportación
```
GET /api/report               → Informe TXT
GET /api/export/json          → Exportación JSON completa
GET /api/export/csv           → Exportación CSV
DELETE /api/reset?confirm=BORRAR → Reset completo de base
```

#### Servidor Estático
```
GET /                         → Sirve frontend/index.html
/static/*                     → Archivos estáticos del frontend
```

---

## Flujo de Datos

```
Usuario → POST /api/run
              ↓
        run_collection(region)
              ↓
    ┌─────────┼─────────┬─────────┬─────────┐
    ↓         ↓         ↓         ↓         ↓
 Wikipedia  GTrends   Reddit   Mastodon    HN
    │         │         │         │         │
    └─────────┴─────────┴─────────┴─────────┘
              ↓
      record_source() → samples + term_hits
              ↓
      detect_outbreak_alerts()
              ↓
    ┌─────────┴─────────┐
    ↓                   ↓
 alerts (SQLite)   Telegram (opcional)
```

---

## Dependencias Utilizadas

```python
import asyncio        # Concurrencia async/await
import csv            # Exportación CSV
import io             # Buffers en memoria
import json           # Serialización
import math           # Operaciones matemáticas
import os             # Sistema operativo
import re             # Expresiones regulares
import sqlite3        # Base de datos
import time           # Timestamps
import uuid           # IDs únicos (no usado actualmente)
import xml.etree.ElementTree  # Parseo RSS
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote  # URL encoding

import httpx          # Cliente HTTP async
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
```

---

## Notas de Implementación

- **WAL Mode**: SQLite usa Write-Ahead Logging para permitir lecturas concurrentes
- **Async/Await**: Todos los colectores HTTP usan `httpx.AsyncClient` con timeout de 14s
- **Fallback Wikipedia**: Si un día no tiene datos, intenta hasta 4 días atrás
- **Múltiples endpoints Reddit**: Intenta varios endpoints si el primero falla (rate limiting)
- **Normalización Unicode**: Usa `unicodedata.normalize("NFD")` para eliminar acentos

---

## Archivo: `app.py`
- **Líneas**: ~1000
- **Dependencias**: 6 librerías externas
- **Endpoints**: 17 rutas API + servidor estático
- **Tablas SQL**: 6 tablas
- **Regiones**: 6 configuraciones geográficas
- **Fuentes**: 5 tipos de colectores
