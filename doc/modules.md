# Módulos Separados (`modules/`)

> **P2 #23**: Separación de código de `app.py` en módulos reutilizables

---

## Propósito

La carpeta `modules/` contiene código separado de `app.py` para mejorar la organización, mantenibilidad y testabilidad del proyecto. Los módulos son puros Python sin dependencias de FastAPI, permitiendo su reutilización y testing independiente.

---

## Estructura

```
modules/
├── __init__.py           ← Exporta las clases públicas
├── database.py           ← Conexión SQLite y migraciones
└── models.py             ← Modelos Pydantic
```

---

## `database.py`

### Propósito

Gestiona la conexión a SQLite, migraciones de schema y utilidades de base de datos.

### Clases y Funciones

#### `DatabaseContext`

Context manager que garantiza cierre explícito de conexiones SQLite.

```python
from modules import DatabaseContext

with DatabaseContext(DB_PATH) as db:
    rows = db.execute("SELECT * FROM samples").fetchall()
# Conexión cerrada automáticamente
```

**Atributos:**
- `db_path: Path` - Ruta al archivo SQLite
- `conn: sqlite3.Connection` - Conexión activa (solo dentro del contexto)

**Métodos:**
- `__enter__() -> sqlite3.Connection` - Abre conexión con `row_factory = sqlite3.Row`
- `__exit__(exc_type, exc_val, exc_tb)` - Cierra conexión explícitamente

---

#### `add_column_if_not_exists()`

**P2 #22**: Helper de migración que agrega columna si no existe.

```python
def add_column_if_not_exists(
    db: sqlite3.Connection, 
    table: str, 
    column: str, 
    col_type: str
)
```

**Uso:**
```python
add_column_if_not_exists(db, "term_hits", "title_hash", "TEXT")
```

---

#### `run_migrations()`

Ejecuta todas las migraciones en orden.

```python
from modules import run_migrations

with DatabaseContext(DB_PATH) as db:
    run_migrations(db)
```

**Migraciones actuales:**
1. `alert_level` en tabla `alerts`
2. `title_hash` en tabla `term_hits`

---

#### `init_db_module()`

Inicializa el schema base de la base de datos (tablas e índices).

```python
from modules import init_db_module

init_db_module(DB_PATH)
```

**Tablas creadas:**
- `samples` - Datos crudos de cada fuente
- `term_hits` - Apariciones de términos
- `alerts` - Alertas generadas
- `samples_meta` - Metadata de ejecuciones
- `watchlist` - Términos monitoreados
- `aliases` - Sinónimos y mapeos
- `settings` - Configuración del sistema
- `observation_tray` - Bandeja de observación

---

## `models.py`

### Propósito

Define modelos Pydantic para validación de datos y documentación automática de la API.

### Clases

#### `SettingsModel`

Modelo para configuración del sistema.

```python
class SettingsModel(BaseModel):
    outbreak_threshold: Optional[float] = 45.0
    api_reset_token: Optional[str] = ""
```

---

#### `SignalOriginResponse`

Modelo de respuesta para el endpoint `/api/signal-origin/{term}`.

```python
class SignalOriginResponse(BaseModel):
    term: str
    signal_type: str
    explanation: str
    summary: Dict[str, Any]
    outbreak: Optional[Dict[str, Any]]
    sources_breakdown: Dict[str, int]
    regions_breakdown: Dict[str, int]
    first_signal: Optional[Dict[str, Any]]
    last_signal: Optional[Dict[str, Any]]
    evidence_titles: List[Dict[str, Any]]
    timeline: List[Dict[str, Any]]
    total_hits: int
```

---

## Uso en `app.py`

```python
# P2 #23: Importar desde módulos
from modules import DatabaseContext, init_db_module
from modules import SettingsModel, SignalOriginResponse

def get_db():
    """Factory que retorna DatabaseContext"""
    return DatabaseContext(DB_PATH)

def init_db():
    """Inicializar DB usando el módulo separado"""
    init_db_module(DB_PATH)
```

---

## Testing

Los módulos son puros Python sin dependencias de FastAPI, permitiendo testing simple:

```python
# test_database.py
from modules import DatabaseContext, init_db_module
import tempfile
from pathlib import Path

def test_database_connection():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        init_db_module(db_path)
        
        with DatabaseContext(db_path) as db:
            db.execute("INSERT INTO samples (run_id, source) VALUES ('test', 'test')")
            db.commit()
            
            rows = db.execute("SELECT * FROM samples").fetchall()
            assert len(rows) == 1
```

---

## Archivo: `modules/database.py`

- **Propósito**: Gestión de conexiones SQLite y migraciones
- **Dependencias**: `sqlite3`, `pathlib`, `logging`
- **Líneas**: ~150

## Archivo: `modules/models.py`

- **Propósito**: Modelos Pydantic para validación
- **Dependencias**: `pydantic`
- **Líneas**: ~50

## Archivo: `modules/__init__.py`

- **Propósito**: Exportar clases públicas
- **Exports**: `DatabaseContext`, `init_db_module`, `run_migrations`, `SettingsModel`, `SignalOriginResponse`

---

<p align="center">
  <b>Live Observatory v6.1.5</b><br>
  <i>Modular architecture for maintainability</i>
</p>
