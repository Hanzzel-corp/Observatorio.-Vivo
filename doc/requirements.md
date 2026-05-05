# requirements.txt - Dependencias del Proyecto

## Descripción

Archivo de definición de dependencias Python para el Observatorio Vivo v6. Especifica versiones exactas para garantizar reproducibilidad.

---

## Ubicación

```
observatorio_v6_backend/
└── requirements.txt
```

---

## Contenido

```
fastapi==0.115.6
uvicorn[standard]==0.34.0
httpx==0.28.1
pydantic==2.10.5
```

---

## Dependencias Detalladas

### 1. FastAPI (0.115.6)

**Propósito:** Framework web moderno y rápido para construir APIs.

**Características utilizadas:**
- Decoradores de rutas (`@app.get`, `@app.post`)
- Inyección automática de parámetros
- Respuestas automáticas JSON
- Documentación automática OpenAPI/Swagger
- Servidor estático (`StaticFiles`)

**Uso en el proyecto:**
```python
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Observatorio Vivo v6", version="6.0.0")
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/api/health")
def health():
    return {"ok": True}
```

**Dependencias incluidas:**
- Starlette (motor ASGI subyacente)
- Pydantic (validación, ya listado separadamente)

**Documentación:** https://fastapi.tiangolo.com/

---

### 2. Uvicorn [standard] (0.34.0)

**Propósito:** Servidor ASGI de alto rendimiento.

**¿Por qué [standard]?**

Incluye dependencias adicionales optimizadas:
```
[standard] = uvloop + httptools + websockets
```

| Extra | Función |
|-------|---------|
| `uvloop` | Loop de eventos más rápido que asyncio estándar |
| `httptools` | Parser HTTP en C (más rápido) |
| `websockets` | Soporte para WebSockets |

**Uso en el proyecto:**
```bash
# Desarrollo (con reload automático)
uvicorn app:app --reload --host 127.0.0.1 --port 8765

# La versión [standard] se ejecuta automáticamente más rápido
```

**Uso programático (opcional):**
```python
import uvicorn

if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8765, reload=True)
```

**Documentación:** https://www.uvicorn.org/

---

### 3. HTTPX (0.28.1)

**Propósito:** Cliente HTTP moderno para Python, compatible con `requests` pero con soporte async.

**Características utilizadas:**
- Cliente asíncrono (`AsyncClient`)
- Timeouts configurables
- Follow redirects automático
- Manejo de JSON nativo
- Soporte HTTP/2 (opcional)

**Uso en el proyecto:**
```python
import httpx

async def collect_wikipedia(client: httpx.AsyncClient, lang: str):
    url = f"https://wikimedia.org/api/rest_v1/metrics/..."
    r = await client.get(url)
    return r.json()

# Uso concurrente
timeout = httpx.Timeout(14.0, connect=8.0)
async with httpx.AsyncClient(timeout=timeout) as client:
    tasks = [collect_wikipedia(client, "es"), collect_reddit(client)]
    results = await asyncio.gather(*tasks)
```

**Ventajas sobre requests:**
- Nativamente async/await
- Mejor rendimiento en I/O concurrente
- API similar (drop-in replacement en muchos casos)

**Documentación:** https://www.python-httpx.org/

---

### 4. Pydantic (2.10.5)

**Propósito:** Validación de datos usando tipos de Python.

**Características utilizadas:**
- Modelos de datos con tipos
- Validación automática de requests
- Serialización/deserialización JSON
- Documentación automática de esquemas

**Uso en el proyecto:**
```python
from pydantic import BaseModel
from typing import Optional

class WatchIn(BaseModel):
    term: str

class AliasIn(BaseModel):
    alias: str
    canonical: str

class SettingsIn(BaseModel):
    outbreak_threshold: Optional[float] = None
    telegram_enabled: Optional[bool] = None
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None

# FastAPI usa automáticamente estos modelos para:
# - Validar requests POST
# - Generar documentación OpenAPI
# - Serializar responses
```

**Beneficios:**
```python
# Sin Pydantic (manual)
data = await request.json()
if "term" not in data:
    raise HTTPException(400, "Falta 'term'")
if not isinstance(data["term"], str):
    raise HTTPException(400, "'term' debe ser string")
term = data["term"]

# Con Pydantic (automático)
item: WatchIn  # FastAPI valida automáticamente
term = item.term  # Garantizado string
```

**Documentación:** https://docs.pydantic.dev/

---

## Árbol de Dependencias

Cuando instalas `requirements.txt`, se instalan:

```
fastapi 0.115.6
├── starlette 0.41.x
├── pydantic 2.10.5 (ya listado)
└── typing-extensions

uvicorn[standard] 0.34.0
├── click
├── h11
├── uvloop (extra standard)
├── httptools (extra standard)
└── websockets (extra standard)

httpx 0.28.1
├── certifi
├── httpcore
│   ├── h11 (compartido con uvicorn)
│   └── certifi
├── idna
├── sniffio
└── anyio

pydantic 2.10.5
├── annotated-types
├── pydantic-core (Rust)
└── typing-extensions (compartido)
```

---

## Instalación

### Desde requirements.txt (recomendado)

```bash
pip install -r requirements.txt
```

### Instalación individual

```bash
pip install fastapi==0.115.6
pip install "uvicorn[standard]==0.34.0"
pip install httpx==0.28.1
pip install pydantic==2.10.5
```

### Verificación post-instalación

```bash
python -c "
import fastapi
import uvicorn
import httpx
import pydantic

print(f'FastAPI: {fastapi.__version__}')
print(f'Uvicorn: {uvicorn.__version__}')
print(f'HTTPX: {httpx.__version__}')
print(f'Pydantic: {pydantic.__version__}')
"
```

---

## Actualización de Dependencias

### Comando seguro (dentro de entorno virtual)

```bash
# Actualizar todas
pip install --upgrade -r requirements.txt

# Actualizar una específica
pip install --upgrade fastapi
```

### Verificar compatibilidad

```bash
# Ejecutar tests/verificaciones
./run.sh
# Probar endpoints: /api/health, /api/state, etc.
```

---

## Versiones y Compatibilidad

| Paquete | Versión | Python mínima | Notas |
|---------|---------|---------------|-------|
| FastAPI | 0.115.6 | 3.8+ | Versión estable |
| Uvicorn | 0.34.0 | 3.8+ | Soporte HTTP/2 |
| HTTPX | 0.28.1 | 3.8+ | Cliente moderno |
| Pydantic | 2.10.5 | 3.8+ | V2 (rewrite en Rust) |

**Python requerido:** 3.8 o superior

**Verificar versión de Python:**
```bash
python3 --version  # Python 3.8.10+
```

---

## Dependencias del Sistema

Además de los paquetes Python, se requiere:

| Sistema | Dependencias |
|---------|--------------|
| Python | 3.8+ con venv support |
| pip | 20.0+ (viene con Python) |
| bash | Para ejecutar run.sh (Linux/Mac) |
| SQLite | Incluido en Python estándar |

**Instalación en Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
```

**Instalación en macOS:**
```bash
brew install python3
```

---

## Archivo: `requirements.txt`
- **Dependencias directas**: 4
- **Dependencias totales**: ~20 (incluyendo sub-dependencias)
- **Tamaño de instalación**: ~50 MB
- **Tiempo de instalación**: ~10-30 segundos
