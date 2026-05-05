# API Reference - Endpoints del Observatorio Vivo v6.1

## Base URL

```
http://127.0.0.1:8765
```

---

## Endpoints de Estado

### GET /api/health

Health check simple del sistema.

**Response:**
```json
{
  "ok": true,
  "db": "/path/to/data/observatorio.db",
  "ts": 1745730123.456
}
```

**Códigos:**
- `200 OK` - Sistema funcionando

---

### GET /api/state

Estado completo del sistema con todas las métricas y niveles de alerta.

**Response:**
```json
{
  "settings": {
    "outbreak_threshold": "45",
    "telegram_enabled": "false",
    "telegram_bot_token": "",
    "telegram_chat_id": ""
  },
  "samples_count": 91,
  "hits_count": 6264,
  "runs_count": 10,
  "watchlist": ["dragon ball", "messi", "openai", "ransomware"],
  "aliases": [
    {"alias": "chatgpt", "canonical": "openai", "phenomenon": "OpenAI/IA"},
    {"alias": "messi", "canonical": "messi", "phenomenon": null}
  ],
  "regions": { ... },
  "latest_samples": [...],
  "alerts": [...],
  "alert_levels": {
    "detectado": 12,
    "observado": 8,
    "alertado": 3
  },
  "categories": ["deporte", "ia_tecnologia", "ciberseguridad", ...]
}
```

**Campos:**
- `settings` - Configuración actual
- `samples_count` - Total de muestras capturadas
- `hits_count` - Total de impactos de términos
- `runs_count` - Cantidad de ejecuciones únicas
- `watchlist` - Lista de términos monitoreados
- `aliases` - Mapeo de alias a canónicos con fenómeno opcional
- `regions` - Configuración de regiones disponibles
- `latest_samples` - Últimas 40 muestras (deserializadas)
- `alerts` - Últimas 30 alertas
- `alert_levels` - Contadores por nivel (detectado/observado/alertado)
- `categories` - Lista de categorías temáticas disponibles

---

## Endpoints de Operación

### POST /api/run

Ejecuta una captura de datos completa.

**Query Parameters:**
| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| region | string | "hispano" | Región a monitorear |

**Regiones válidas:** `hispano`, `anglo`, `europa`, `latam`, `asia`, `mundo`

**Response:**
```json
{
  "run_id": "run_1745730123456",
  "region": "hispano",
  "region_label": "Hispanoamérica",
  "sources": [
    {
      "source": "wiki-es",
      "geo": "es",
      "bucket": "es",
      "items": [...],
      "ok": true
    },
    {
      "source": "gtrends-AR",
      "geo": "AR",
      "bucket": "es",
      "items": [...],
      "ok": true
    },
    {
      "source": "reddit",
      "ok": false,
      "error": "Rate limited"
    }
  ],
  "outbreak_alerts": [
    {
      "term": "messi",
      "level": "alta",
      "message": "EVENTO: \"messi\" emergencia 78...",
      "meta": {...}
    }
  ]
}
```

**Códigos:**
- `200 OK` - Captura completada (puede incluir fuentes con error)
- `400 Bad Request` - Región inválida

**Notas:**
- Ejecución asíncrona de colectores
- Cada fuente puede fallar independientemente
- Alertas se generan automáticamente si hay brotes
- Notificaciones Telegram se envían si están habilitadas

---

### GET /api/terms

Lista términos agregados con métricas.

**Query Parameters:**
| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| limit | int | 80 | Cantidad máxima de resultados |

**Response:**
```json
{
  "terms": [
    {
      "term": "messi",
      "total": 145.5,
      "es_score": 45.2,
      "intl_score": 100.3,
      "first_seen": 1745730000.0,
      "last_seen": 1745733600.0,
      "hits": 12,
      "runs": 3,
      "regions": 4,
      "sources": 6,
      "geos": [
        {"geo": "AR", "name": "Argentina", "score": 52.1},
        {"geo": "ES", "name": "España", "score": 38.4}
      ],
      "source_breakdown": [
        {"source": "gtrends-AR", "score": 45.0},
        {"source": "wiki-es", "score": 32.5}
      ]
    }
  ]
}
```

---

### GET /api/outbreaks

Detecta y clasifica brotes/fenómenos nacientes con sistema de 3 niveles.

**Query Parameters:**
| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| limit | int | 80 | Cantidad máxima de resultados |
| filter_level | string | "all" | Filtrar por nivel: "detectado", "observado", "alertado", "all" |

**Response:**
```json
{
  "outbreaks": [
    {
      "term": "messi",
      "total": 145.5,
      "es_score": 45.2,
      "intl_score": 100.3,
      "hits": 12,
      "runs": 3,
      "regions": 4,
      "sources": 6,
      "geos": [...],
      "source_breakdown": [...],
      "last_run_score": 65.3,
      "prev_run_score": 53.0,
      "delta": 12.3,
      "age_hours": 6.5,
      "emergency": 78.5,
      "threshold": 45,
      "first_geo": "AR",
      "first_geo_name": "Argentina",
      "estado": "EVENTO",
      "reading": "Evento fuerte: nació en Argentina, combina varias fuentes y regiones. Requiere verificación externa.",
      "alert_level": "ALERTADO",
      "confidence": "ALTA",
      "category": "deporte",
      "phenomenon": "Deporte",
      "word_count": 1,
      "is_generic": false
    }
  ]
}
```

**Estados posibles:** `EVENTO`, `PROPAGACIÓN`, `BROTE`, `SEMILLA`, `RUIDO`

**Niveles de alerta:**
- `DETECTADO` - Señal en bandeja de observación (confianza BAJA)
- `OBSERVADO` - Brote visible sin alerta activa (confianza MEDIA)
- `ALERTADO` - Notificación activa (confianza ALTA)

**Confianza:**
- `BAJA` - 1 muestra/fuente
- `MEDIA` - 2+ muestras/fuentes
- `ALTA` - 3+ regiones/fuentes/runs

---

### GET /api/observation-tray

Bandeja de observación: señales detectadas con confianza BAJA que están siendo monitoreadas.

**Query Parameters:**
| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| limit | int | 50 | Cantidad máxima de resultados |

**Response:**
```json
{
  "tray": [
    {
      "term": "dragon ball movie",
      "estado": "SEMILLA",
      "confidence": "BAJA",
      "category": "anime_entretenimiento",
      "first_seen": 1745730000,
      "last_seen": 1745733600,
      "runs_count": 1,
      "regions_count": 1,
      "sources_count": 2,
      "delta": 0.5,
      "emergency": 25.3,
      "promoted_to_alert": 0
    }
  ]
}
```

---

### GET /api/hot-topics

Temas calientes por volumen (vs brotes que son por aceleración).

**Query Parameters:**
| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| limit | int | 20 | Cantidad máxima de resultados |

**Response:**
```json
{
  "hot_topics": [
    {
      "term": "openai",
      "total": 245.8,
      "confidence": "ALTA",
      "category": "ia_tecnologia",
      "type": "volumen"
    }
  ]
}
```

---

### GET /api/categories/{category}

Obtener brotes filtrados por categoría temática.

**Path Parameters:**
| Parámetro | Descripción |
|-----------|-------------|
| category | Nombre de la categoría (deporte, ia_tecnologia, ciberseguridad, etc.) |

**Query Parameters:**
| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| limit | int | 30 | Cantidad máxima de resultados |

**Response:**
```json
{
  "category": "ia_tecnologia",
  "outbreaks": [...]
}
```

---

### GET /api/phenomena

Obtener lista de fenómenos agrupados desde aliases.

**Response:**
```json
{
  "phenomena": ["OpenAI/IA", "Dragon Ball", "Ciberseguridad", "Deporte"]
}
```

---

### GET /api/term/{term}

Detalle histórico de un término específico.

**Path Parameters:**
| Parámetro | Descripción |
|-----------|-------------|
| term | Término a consultar (se normaliza automáticamente) |

**Response:**
```json
{
  "term": "messi",
  "summary": {
    "term": "messi",
    "total": 145.5,
    "es_score": 45.2,
    "intl_score": 100.3,
    "hits": 12,
    "runs": 3,
    "regions": 4,
    "sources": 6
  },
  "hits": [
    {
      "id": 1234,
      "term": "messi",
      "ts": 1745730123.0,
      "run_id": "run_1745730123456",
      "region": "hispano",
      "source": "gtrends-AR",
      "geo": "AR",
      "bucket": "es",
      "score": 5.2,
      "title": "Messi hattrick Inter Miami",
      "url": "https://..."
    }
  ]
}
```

---

### GET /api/alerts

Alertas históricas generadas por el sistema.

**Query Parameters:**
| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| limit | int | 50 | Cantidad máxima de resultados |

**Response:**
```json
{
  "alerts": [
    {
      "id": 42,
      "ts": 1745730123.0,
      "type": "brote",
      "term": "messi",
      "level": "alta",
      "message": "EVENTO: \"messi\" emergencia 78, delta +12.3...",
      "meta": {
        "term": "messi",
        "estado": "EVENTO",
        "emergency": 78.5,
        "delta": 12.3,
        "run_id": "run_1745730123456"
      }
    }
  ]
}
```

---

## Endpoints de Gestión

### POST /api/watchlist

Agrega un término a la watchlist.

**Request Body:**
```json
{
  "term": "inteligencia artificial"
}
```

**Response:**
```json
{
  "ok": true,
  "term": "inteligencia artificial"
}
```

**Códigos:**
- `200 OK` - Término agregado
- `400 Bad Request` - Término vacío

---

### DELETE /api/watchlist/{term}

Elimina un término de la watchlist.

**Path Parameters:**
| Parámetro | Descripción |
|-----------|-------------|
| term | Término a eliminar (URL encoded) |

**Response:**
```json
{
  "ok": true,
  "term": "inteligencia artificial"
}
```

---

### POST /api/aliases

Crea o actualiza un alias con fenómeno opcional.

**Request Body:**
```json
{
  "alias": "chatgpt",
  "canonical": "openai",
  "phenomenon": "OpenAI/IA"
}
```

**Campos:**
| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| alias | string | Sí | Variante léxica a normalizar |
| canonical | string | Sí | Término canónico objetivo |
| phenomenon | string | No | Fenómeno temático para agrupar variantes |

**Response:**
```json
{
  "ok": true,
  "alias": "chatgpt",
  "canonical": "openai",
  "phenomenon": "OpenAI/IA"
}
```

**Códigos:**
- `200 OK` - Alias creado/actualizado
- `400 Bad Request` - Alias o canónico vacío

**Ejemplos de fenómenos:**
- `OpenAI/IA` - agrupa chatgpt, gpt-5, openai agent
- `Dragon Ball` - agrupa dragon ball daima, dbz, goku
- `Ciberseguridad` - agrupa malware, cve, exploit, ransomware

---

### POST /api/settings

Actualiza configuración del sistema.

**Request Body:**
```json
{
  "outbreak_threshold": 50.0,
  "telegram_enabled": true,
  "telegram_bot_token": "123456:ABC-DEF...",
  "telegram_chat_id": "-1001234567890"
}
```

**Campos opcionales:** Todos son opcionales; solo se actualizan los enviados.

**Response:**
```json
{
  "ok": true,
  "settings": {
    "outbreak_threshold": "50",
    "telegram_enabled": "true",
    "telegram_bot_token": "123456:ABC-DEF...",
    "telegram_chat_id": "-1001234567890"
  }
}
```

---

### POST /api/telegram/test

Envía un mensaje de prueba a Telegram.

**Response:**
```json
{
  "ok": true
}
```

**Notas:**
- Requiere `telegram_enabled=true` y credenciales válidas
- No hay confirmación de entrega (fire-and-forget)

---

## Endpoints de Exportación

### GET /api/report

Genera informe TXT completo.

**Response:** `text/plain`

```
================================================================================
OBSERVATORIO VIVO v6 · INFORME DE INTELIGENCIA DE TENDENCIAS
Generado: 2025-04-27 14:32:15
Muestras: 91
Impactos de términos: 6264
================================================================================

BROTES / FENÓMENOS NACIENTES
01. EVENTO · messi · emergencia 78 · delta +12.3 · regiones 4 · fuentes 6
    Evento fuerte: nació en Argentina, combina varias fuentes y regiones...

TOP TÉRMINOS
01. messi · score 145.5 · hispano 45.2 · intl 100.3 · regiones 4 · fuentes 6
...
```

---

### GET /api/export/json

Exportación JSON completa de todo el sistema.

**Response:** `application/json`

```json
{
  "state": {...},
  "terms": [...],
  "outbreaks": [...],
  "alerts": [...]
}
```

---

### GET /api/export/csv

Exportación CSV del histórico de muestras.

**Response:** `text/csv`

```csv
ts,datetime,run_id,region,source,geo,bucket,top_title
1745730123.456,2025-04-27 14:32:15,run_1745730123456,hispano,wiki-es,es,es,Messi
...
```

---

### DELETE /api/reset

Reset completo de la base de datos (⚠️ Irreversible).

**Query Parameters:**
| Parámetro | Descripción |
|-----------|-------------|
| confirm | Debe ser exactamente "BORRAR" |

**Response:**
```json
{
  "ok": true
}
```

**Códigos:**
- `200 OK` - Base reseteada
- `400 Bad Request` - Confirmación incorrecta

---

## Endpoints de Frontend

### GET /

Sirve la interfaz web (frontend/index.html).

**Response:** `text/html`

---

### GET /static/{path}

Sirve archivos estáticos del directorio frontend/.

**Ejemplos:**
- `/static/index.html` → frontend/index.html
- `/static/style.css` → frontend/style.css (si existe)

---

## Códigos de Error

| Código | Descripción |
|--------|-------------|
| `200 OK` | Éxito |
| `400 Bad Request` | Parámetros inválidos o faltantes |
| `404 Not Found` | Endpoint o recurso no existe |
| `422 Unprocessable Entity` | Error de validación Pydantic |
| `500 Internal Server Error` | Error inesperado del servidor |

---

## Ejemplos de Uso

### Bash/Curl

```bash
# Estado del sistema
curl http://127.0.0.1:8765/api/state | jq

# Ejecutar captura
curl -X POST "http://127.0.0.1:8765/api/run?region=mundo" | jq

# Agregar a watchlist
curl -X POST -H "Content-Type: application/json" \
  -d '{"term": "bitcoin"}' \
  http://127.0.0.1:8765/api/watchlist

# Exportar a archivo
curl http://127.0.0.1:8765/api/export/csv > tendencias.csv
```

### Python

```python
import requests

# Cliente base
BASE = "http://127.0.0.1:8765"

# Ejecutar run
response = requests.post(f"{BASE}/api/run", params={"region": "hispano"})
data = response.json()
print(f"Run ID: {data['run_id']}")

# Obtener brotes
response = requests.get(f"{BASE}/api/outbreaks", params={"limit": 10})
brotes = response.json()["outbreaks"]
for b in brotes:
    print(f"{b['estado']}: {b['term']} (emergencia: {b['emergency']})")
```

### JavaScript

```javascript
// Ejecutar run y actualizar
async function capturar(region = 'hispano') {
  const response = await fetch(`/api/run?region=${region}`, {
    method: 'POST'
  });
  const data = await response.json();
  console.log('Fuentes capturadas:', data.sources.filter(s => s.ok).length);
  return data;
}

// Obtener estado
async function estado() {
  const response = await fetch('/api/state');
  return await response.json();
}
```

---

## Rate Limiting

No hay rate limiting implementado en el backend. Sin embargo:

- **Reddit**: Puede retornar 429 si se hacen demasiadas peticiones
- **Colectores externos**: Respetan timeouts de 14s
- **Recomendación**: No ejecutar más de 1 run por minuto para evitar bloqueos

---

## Archivo de referencia: `doc/api_reference.md`
- **Endpoints documentados**: 17
- **Métodos HTTP**: GET, POST, DELETE
- **Formatos**: JSON, TXT, CSV, HTML
