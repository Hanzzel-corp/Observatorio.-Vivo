# Base de Datos SQLite - Estructura y Esquema

## Descripción

El Observatorio Vivo v6 utiliza **SQLite 3** con modo **WAL (Write-Ahead Logging)** para persistencia local. La base de datos se almacena en `data/observatorio.db`.

---

## Ubicación

```
data/
├── observatorio.db       # Base de datos principal
├── observatorio.db-shm   # Shared memory (WAL mode)
└── observatorio.db-wal   # Write-ahead log (WAL mode)
```

**Nota**: Los archivos `-shm` y `-wal` son parte del modo WAL y se generan automáticamente.

---

## Esquema de Tablas

### 1. samples

Almacena cada captura de fuente realizada durante un run.

```sql
CREATE TABLE samples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,           -- ID del run (ej: "run_1745730123456")
    ts REAL NOT NULL,               -- Timestamp UNIX (segundos)
    region TEXT NOT NULL,           -- Región seleccionada (hispano, anglo, etc.)
    source TEXT NOT NULL,           -- Fuente (wiki-es, gtrends-AR, reddit, etc.)
    geo TEXT NOT NULL,              -- Geografía específica (es, AR, reddit, etc.)
    bucket TEXT NOT NULL,           -- Clasificación: "es" o "intl"
    top_title TEXT,                 -- Título #1 de la muestra
    raw_json TEXT NOT NULL          -- Array JSON con todos los items
);
```

**Ejemplo de raw_json:**
```json
[
  {"title": "Messi", "traffic": "2.5M", "url": "https://..."},
  {"title": "Dragon Ball", "traffic": "1.8M", "url": "https://..."}
]
```

**Índices recomendados (implícitos por PK):**
- `id` (PK) - Búsquedas por muestra específica

**Consultas típicas:**
```sql
-- Últimas muestras
SELECT * FROM samples ORDER BY ts DESC LIMIT 80;

-- Muestras de un run específico
SELECT * FROM samples WHERE run_id = 'run_1745730123456';

-- Conteo total
SELECT COUNT(*) FROM samples;

-- Muestras por fuente
SELECT source, COUNT(*) FROM samples GROUP BY source;
```

---

### 2. term_hits

Impactos de términos extraídos de los títulos, con scoring ponderado.

```sql
CREATE TABLE term_hits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    term TEXT NOT NULL,             -- Término normalizado (ej: "messi")
    ts REAL NOT NULL,               -- Timestamp del hit
    run_id TEXT NOT NULL,           -- Run asociado
    region TEXT NOT NULL,           -- Región del run
    source TEXT NOT NULL,           -- Fuente específica
    geo TEXT NOT NULL,              -- Geografía
    bucket TEXT NOT NULL,           -- "es" o "intl"
    score REAL NOT NULL,            -- Puntuación ponderada
    title TEXT,                     -- Título original donde apareció
    url TEXT                        -- URL asociada
);
```

**Índices creados:**
```sql
CREATE INDEX idx_term_hits_term ON term_hits(term);   -- Búsqueda por término
CREATE INDEX idx_term_hits_run ON term_hits(run_id);  -- Búsqueda por run
CREATE INDEX idx_term_hits_ts ON term_hits(ts);      -- Ordenación temporal
```

**Consultas típicas:**
```sql
-- Score total por término
SELECT term, SUM(score) as total 
FROM term_hits 
GROUP BY term 
ORDER BY total DESC;

-- Evolución temporal de un término
SELECT run_id, ts, SUM(score) as score 
FROM term_hits 
WHERE term = 'messi' 
GROUP BY run_id 
ORDER BY ts;

-- Términos por bucket (hispano vs internacional)
SELECT 
  term,
  SUM(CASE WHEN bucket='es' THEN score ELSE 0 END) as es_score,
  SUM(CASE WHEN bucket='intl' THEN score ELSE 0 END) as intl_score
FROM term_hits
GROUP BY term;

-- Score por fuente para un término
SELECT source, SUM(score) as score 
FROM term_hits 
WHERE term = 'openai' 
GROUP BY source 
ORDER BY score DESC;
```

---

### 3. watchlist

Términos específicos que el usuario quiere monitorear.

```sql
CREATE TABLE watchlist (
    term TEXT PRIMARY KEY,          -- Término normalizado único
    created_ts REAL NOT NULL        -- Cuándo se agregó
);
```

**Valores por defecto** (insertados en `init_db()`):
- dragon ball
- messi
- ransomware
- openai

**API:**
```sql
-- Insertar
INSERT OR IGNORE INTO watchlist(term, created_ts) VALUES (?, ?);

-- Eliminar
DELETE FROM watchlist WHERE term = ?;

-- Listar
SELECT term FROM watchlist ORDER BY term;
```

---

### 4. aliases

Mapeo de variantes léxicas a términos canónicos.

```sql
CREATE TABLE aliases (
    alias TEXT PRIMARY KEY,         -- Variante (ej: "chatgpt")
    canonical TEXT NOT NULL,        -- Término base (ej: "openai")
    created_ts REAL NOT NULL        -- Timestamp de creación
);
```

**Valores por defecto** (insertados en `init_db()`):

| Alias | Canónico |
|-------|----------|
| leo messi | messi |
| lionel messi | messi |
| inter miami | messi |
| chatgpt | openai |
| gpt | openai |
| gpt 5 | openai |
| dragon ball daima | dragon ball |
| dbz | dragon ball |
| goku | dragon ball |
| malware | ransomware |
| cyber attack | ciberseguridad |
| cyberattack | ciberseguridad |

**API:**
```sql
-- Insertar/Actualizar
INSERT INTO aliases(alias, canonical, created_ts) 
VALUES (?, ?, ?) 
ON CONFLICT(alias) DO UPDATE SET canonical=excluded.canonical;

-- Mapeo completo
SELECT alias, canonical FROM aliases;

-- Eliminar (no implementado en API actual)
DELETE FROM aliases WHERE alias = ?;
```

**Uso en código** (`alias_map()` y `canonicalize()`):
```python
aliases = {r["alias"]: r["canonical"] for r in db.execute("SELECT alias, canonical FROM aliases")}
canonical = aliases.get(term, term)  # Si no hay alias, usa el término original
```

---

### 5. alerts

Alertas generadas por el detector de brotes.

```sql
CREATE TABLE alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,               -- Timestamp de la alerta
    type TEXT NOT NULL,             -- Tipo: 'brote', 'sistema', etc.
    term TEXT NOT NULL,             -- Término que generó la alerta
    level TEXT NOT NULL,            -- Nivel: 'alta', 'media', 'baja'
    message TEXT NOT NULL,          -- Mensaje descriptivo
    meta_json TEXT NOT NULL         -- Metadatos en JSON
);
```

**Ejemplo de meta_json:**
```json
{
  "term": "messi",
  "emergency": 78.5,
  "estado": "EVENTO",
  "delta": 12.3,
  "regions": 4,
  "sources": 5,
  "first_geo": "AR",
  "reading": "Evento fuerte: nació en Argentina...",
  "run_id": "run_1745730123456"
}
```

**API:**
```sql
-- Insertar (usado por detect_outbreak_alerts)
INSERT INTO alerts(ts, type, term, level, message, meta_json) 
VALUES (?, 'brote', ?, ?, ?, ?);

-- Listar recientes
SELECT * FROM alerts ORDER BY ts DESC LIMIT 50;

-- Alertas por término
SELECT * FROM alerts WHERE term = ? ORDER BY ts DESC;
```

---

### 6. settings

Configuración del sistema en formato clave-valor.

```sql
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
```

**Valores por defecto:**

| Key | Value | Descripción |
|-----|-------|-------------|
| outbreak_threshold | 45 | Umbral mínimo de emergencia para alertas |
| telegram_enabled | false | Activar/desactivar notificaciones Telegram |
| telegram_bot_token | "" | Token del bot de Telegram |
| telegram_chat_id | "" | ID del chat destino |

**API:**
```sql
-- Leer todas
SELECT key, value FROM settings;

-- Leer una
SELECT value FROM settings WHERE key = 'outbreak_threshold';

-- Insertar/Actualizar
INSERT INTO settings(key, value) VALUES (?, ?) 
ON CONFLICT(key) DO UPDATE SET value=excluded.value;
```

---

## Diagrama ER

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   samples    │     │  term_hits   │     │   alerts     │
├──────────────┤     ├──────────────┤     ├──────────────┤
│ PK id        │◄────┤ FK run_id    │     │ PK id        │
│ run_id       │     │ term         │     │ ts           │
│ ts           │     │ ts           │     │ type         │
│ region       │     │ score        │     │ term         │
│ source       │     │ title        │     │ level        │
│ geo          │     │ url          │     │ message      │
│ bucket       │     └──────────────┘     │ meta_json    │
│ top_title    │                          └──────────────┘
│ raw_json     │
└──────────────┘

┌──────────────┐     ┌──────────────┐
│  watchlist   │     │   aliases    │
├──────────────┤     ├──────────────┤
│ PK term      │     │ PK alias     │
│ created_ts   │     │ canonical    │
└──────────────┘     │ created_ts   │
                     └──────────────┘

┌──────────────┐
│   settings   │
├──────────────┤
│ PK key       │
│ value        │
└──────────────┘
```

---

## Consultas de Análisis

### Términos más populares (últimas 24h)
```sql
SELECT 
  term, 
  SUM(score) as total,
  COUNT(DISTINCT run_id) as runs
FROM term_hits 
WHERE ts > strftime('%s', 'now') - 86400
GROUP BY term 
ORDER BY total DESC 
LIMIT 20;
```

### Evolución de runs por hora
```sql
SELECT 
  datetime(ts, 'unixepoch', 'localtime') as hora,
  COUNT(DISTINCT run_id) as runs
FROM samples 
GROUP BY strftime('%H', ts, 'unixepoch')
ORDER BY hora DESC;
```

### Distribución por fuente
```sql
SELECT 
  source,
  COUNT(*) as muestras,
  COUNT(DISTINCT run_id) as runs_distintos
FROM samples 
GROUP BY source 
ORDER BY muestras DESC;
```

### Términos cruzados (hispano + internacional)
```sql
SELECT 
  term,
  SUM(CASE WHEN bucket='es' THEN score ELSE 0 END) as es,
  SUM(CASE WHEN bucket='intl' THEN score ELSE 0 END) as intl
FROM term_hits
GROUP BY term
HAVING es > 0 AND intl > 0
ORDER BY (es + intl) DESC
LIMIT 20;
```

---

## Mantenimiento

### Backup
```bash
# Copiar archivo (la app puede estar corriendo gracias a WAL)
cp data/observatorio.db data/observatorio_backup_$(date +%Y%m%d).db
```

### Reset completo
```bash
# Desde la API (recomendado)
curl -X DELETE "http://127.0.0.1:8765/api/reset?confirm=BORRAR"

# O manualmente (detener app primero)
rm data/observatorio.db*
# Reiniciar app - init_db() creará tablas nuevas
```

### Optimización

SQLite con WAL mode generalmente no requiere `VACUUM`, pero si la base crece mucho:
```sql
-- Ejecutar con app detenida
VACUUM;
```

---

## Especificaciones Técnicas

| Característica | Valor |
|----------------|-------|
| **Motor** | SQLite 3 |
| **Modo** | WAL (Write-Ahead Logging) |
| **Ubicación** | `data/observatorio.db` |
| **Tamaño típico** | ~2-10 MB (depende de muestreo) |
| **Tablas** | 6 |
| **Índices** | 3 explícitos + PKs |
| **Concurrencia** | Lecturas concurrentes, escritura serializada |
| **Portabilidad** | Archivo único, copiable entre sistemas |

---

## Archivo: `data/observatorio.db`
- **Formato**: SQLite 3
- **Tablas**: 6
- **Relaciones**: Mínimas (principalmente lookups)
- **Escritura**: Append-mostly (histórico)
