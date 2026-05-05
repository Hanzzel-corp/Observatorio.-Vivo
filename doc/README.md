# Documentación del Observatorio Vivo v6

> 🌐 **English version available**: [README_EN.md](README_EN.md)

## Índice de Archivos

Esta carpeta `doc/` contiene documentación detallada de cada componente del sistema:

| Archivo | Descripción |
|---------|-------------|
| [`app.md`](app.md) | Backend FastAPI (endpoints y lógica principal) |
| [`modules.md`](modules.md) | Módulos separados (database, models) |
| [`frontend.md`](frontend.md) | Interfaz SPA vanilla JavaScript |
| [`database.md`](database.md) | Esquema SQLite y consultas SQL |
| [`api_reference.md`](api_reference.md) | Documentación completa de la API REST |
| [`run_sh.md`](run_sh.md) | Script de arranque automático |
| [`requirements.md`](requirements.md) | Dependencias Python |
| [`README.md`](README.md) | Documentación en español (este archivo) |
| [`README_EN.md`](README_EN.md) | Documentación en inglés |

---

## Estructura del Proyecto

```
observatorio_v6_backend/
├── app.py                 ← [Ver app.md](app.md) - Endpoints FastAPI
├── modules/               ← [Ver modules.md](modules.md)
│   ├── __init__.py
│   ├── database.py        ← Conexión SQLite + migraciones
│   └── models.py          ← Modelos Pydantic
├── test_core.py           ← Tests unitarios (pytest)
├── frontend/
│   └── index.html         ← [Ver frontend.md](frontend.md)
├── data/
│   └── observatorio.db    ← [Ver database.md](database.md)
├── doc/
│   ├── app.md
│   ├── modules.md         ← NUEVO: Documentación de módulos
│   ├── frontend.md
│   ├── database.md
│   ├── api_reference.md
│   ├── run_sh.md
│   ├── requirements.md
│   └── README.md          ← Este archivo
├── requirements.txt       ← [Ver requirements.md](requirements.md)
├── run.sh                 ← [Ver run_sh.md](run_sh.md)
└── README.md              ← Documentación principal del proyecto
```

---

## Cómo usar esta documentación

### Para entender el backend

1. Lee [`app.md`](app.md) - Explica la estructura de `app.py` sección por sección:
   - Constantes y configuración
   - Base de datos y esquema
   - Colectores de datos
   - Algoritmo de detección de brotes
   - Endpoints FastAPI

### Para modificar la interfaz

1. Lee [`frontend.md`](frontend.md) - Documenta:
   - Variables CSS y tema visual
   - Estructura de las 6 pestañas
   - JavaScript y manejo de estado
   - Comunicación con el backend

### Para trabajar con datos

1. Lee [`database.md`](database.md) - Incluye:
   - Esquema completo de las 6 tablas
   - Índices y optimización
   - Consultas SQL de análisis
   - Ejemplos de queries útiles

### Para integrar con otros sistemas

1. Lee [`api_reference.md`](api_reference.md) - Proporciona:
   - Todos los 17 endpoints documentados
   - Ejemplos en bash, Python y JavaScript
   - Códigos de error
   - Formato de requests/responses

### Para desplegar o mantener

1. Lee [`run_sh.md`](run_sh.md) - Explica:
   - Cómo funciona el script de arranque
   - Creación de entornos virtuales
   - Troubleshooting común

2. Lee [`requirements.md`](requirements.md) - Detalla:
   - Cada dependencia y su propósito
   - Árbol de dependencias
   - Versiones y compatibilidad

---

## Diagrama de Flujo del Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                         USUARIO                                │
│  (Navegador Web)                                                │
└─────────────────┬───────────────────────────────────────────────┘
                  │ HTTP
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    frontend/index.html                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Radar     │  │   Brotes    │  │  Histórico  │             │
│  │  (Dashboard)│  │  (Detector) │  │  (Muestras) │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  Watchlist  │  │   Config    │  │   Informe   │             │
│  │ (Seguimiento)│  │ (Telegram)  │  │   (TXT)     │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                      ↑ JavaScript (fetch API)                   │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                         app.py (FastAPI)                        │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐   │
│  │    /api/run     │───▶│  Colectores     │───▶│  SQLite DB  │   │
│  │  (POST)         │    │  (async)        │    │  (WAL mode) │   │
│  └─────────────────┘    └─────────────────┘    └─────────────┘   │
│         ↑                    │  • Wikipedia                     │
│         │                    │  • Google Trends                 │
│  ┌──────┴───────────────────┤  • Reddit                        │
│  │    API REST (17 endpoints)  • Mastodon                       │
│  │                           │  • Hacker News                   │
│  │  • /api/state             │                                  │
│  │  • /api/terms             │                                  │
│  │  • /api/outbreaks         │                                  │
│  │  • /api/alerts            │                                  │
│  │  • /api/watchlist         │                                  │
│  │  • /api/export/*          │                                  │
│  │                           │                                  │
│  │  Detector de Brotes ◄─────┘                                  │
│  │  (Algoritmo de scoring)                                      │
│  │                                                              │
│  └──────────────────────────────────────────────────────────────┘
                       │
                       ▼ (opcional)
              ┌─────────────────┐
              │   Telegram API  │
              │  (alertas push) │
              └─────────────────┘
```

---

## Glosario de Términos

| Término | Significado |
|---------|-------------|
| **Run** | Una ejecución completa de captura de todas las fuentes |
| **Muestra** | Datos capturados de una fuente específica en un run |
| **Hit** | Aparición de un término en un título procesado |
| **Score** | Puntuación ponderada según fuente y posición |
| **Emergencia** | Métrica compuesta del detector de brotes (0-150) |
| **Delta** | Diferencia de score entre el último run y el anterior |
| **Bucket** | Clasificación geográfica: "es" (hispano) o "intl" (internacional) |
| **Canónico** | Forma normalizada de un término (después de aplicar alias) |
| **WAL** | Write-Ahead Logging (modo de SQLite para concurrencia) |

---

## Enlaces Rápidos

### Por tarea

| Quiero... | Documentación |
|-----------|---------------|
| Entender el algoritmo de brotes | [app.md - Sección 9](app.md#9-algoritmo-detector-de-brotes-líneas-583-705) |
| Modificar el tema visual | [frontend.md - Estilos CSS](frontend.md#estilos-css-líneas-10-20) |
| Agregar una nueva fuente de datos | [app.md - Colectores](app.md#6-colectores-de-datos-líneas-319-446) |
| Consultar datos directamente | [database.md - Consultas](database.md#consultas-de-análisis) |
| Integrar con mi aplicación | [api_reference.md](api_reference.md) |
| Solucionar problemas de arranque | [run_sh.md - Troubleshooting](run_sh.md#troubleshooting) |

### Por componente

| Componente | Archivo principal | Documentación |
|------------|-------------------|---------------|
| Backend | `app.py` | [app.md](app.md) |
| Módulos | `modules/` | [modules.md](modules.md) |
| Frontend | `frontend/index.html` | [frontend.md](frontend.md) |
| Base de datos | `data/observatorio.db` | [database.md](database.md) |
| API REST | Endpoints en `app.py` | [api_reference.md](api_reference.md) |
| Script de inicio | `run.sh` | [run_sh.md](run_sh.md) |
| Dependencias | `requirements.txt` | [requirements.md](requirements.md) |
| Tests | `test_core.py` | - |

---

## Actualizaciones

Para mantener esta documentación actualizada después de cambios en el código:

1. **Si modificas `app.py`**: Actualizar [app.md](app.md)
2. **Si modificas `modules/`**: Actualizar [modules.md](modules.md)
3. **Si modificas `frontend/index.html`**: Actualizar [frontend.md](frontend.md)
4. **Si agregas endpoints**: Actualizar [api_reference.md](api_reference.md)
5. **Si cambias el esquema SQL**: Actualizar [database.md](database.md)
6. **Si cambias dependencias**: Actualizar [requirements.md](requirements.md)

---

## Archivo: `doc/README.md`
- **Propósito**: Índice y guía de navegación de la documentación
- **Archivos referenciados**: 6 documentos técnicos
- **Público objetivo**: Desarrolladores y usuarios avanzados
