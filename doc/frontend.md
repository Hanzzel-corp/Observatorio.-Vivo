# frontend/index.html - Interfaz de Usuario

## Descripción

Single Page Application (SPA) vanilla JavaScript que proporciona la interfaz visual del Observatorio Vivo v6. No requiere frameworks externos - todo el código está contenido en un único archivo HTML.

---

## Estructura General (~373 líneas)

```
index.html
├── <head>        → CSS inline + fuentes de Google
└── <body>        → Estructura HTML + JavaScript inline
    ├── <header>  → Título, reloj, indicador LIVE
    ├── <div class="control"> → Controles principales
    ├── <div class="tabs">    → 6 pestañas de navegación
    ├── <section> × 6       → Contenido de cada pestaña
    └── <footer>            → Información del sistema
```

---

## Estilos CSS (líneas 10-20)

### Variables CSS ( `:root` )

| Variable | Color | Uso |
|----------|-------|-----|
| `--bg` | `#090807` | Fondo principal (muy oscuro) |
| `--b2` | `#12100e` | Paneles secundarios |
| `--b3` | `#1b1713` | Fondos de tarjetas |
| `--line` | `#2d261f` | Bordes y separadores |
| `--ink` | `#efe5d6` | Texto principal (crema) |
| `--mut` | `#a99b87` | Texto secundario (muted) |
| `--dim` | `#74685a` | Texto tenue |
| `--a` | `#e8a33d` | Acento dorado/naranja |
| `--a2` | `#ffbf5f` | Acento hover |
| `--r` | `#d45b5b` | Rojo (alertas, peligro) |
| `--g` | `#89ad5f` | Verde (éxito, LIVE) |
| `--bl` | `#6f9dc9` | Azul (información) |
| `--p` | `#b284cb` | Púrpura |

### Fuentes

- **Títulos**: `'Instrument Serif', serif` (serif italica elegante)
- **UI/Texto**: `'JetBrains Mono', monospace` (monospace técnico)

### Grid System

| Clase | Columnas | Responsive |
|-------|----------|------------|
| `.c4` | 4 columnas | 2 cols en <1050px, 1 col en <720px |
| `.c3` | 3 columnas | 2 cols en <1050px, 1 col en <720px |
| `.c2` | 2 columnas | 1 col en <720px |

### Componentes UI

**Badges de Estado:**
```css
.badge.evento      → Rojo (peligro/alerta máxima)
.badge.propagacion → Verde (expansión activa)
.badge.brote       → Dorado (señal temprana)
.badge.semilla     → Azul (primera aparición)
```

**KPI Cards:**
```css
.panel      → Tarjeta estándar
.panel.hot  → Tarjeta destacada (gradiente dorado)
```

---

## Pestañas (Tabs)

### 1. Radar (líneas 73-84)

Dashboard principal con métricas en tiempo real.

**KPIs mostrados:**
- Tema caliente (término con mayor score)
- Brote principal (término con mayor emergencia)
- Base local (muestras e impactos totales)
- Alertas (total acumulado y estado Telegram)

**Secciones:**
- Nube de términos (`#termCloud`) - términos con frecuencia
- Fuentes capturadas (`#sourcesGrid`) - últimas 3-4 fuentes

### 2. Brotes (líneas 86-94)

Detector de fenómenos nacientes.

**Controles:**
- Slider de sensibilidad (`#threshold`) - ajusta umbral 20-90
- Display del valor actual (`#thresholdLabel`)

**Tabla principal:**
| Columna | Descripción |
|---------|-------------|
| Estado | Badge con clasificación |
| Término | Nombre normalizado |
| Emergencia | Puntuación numérica |
| Delta | Cambio vs muestra anterior |
| Regiones | Cantidad de regiones |
| Fuentes | Cantidad de fuentes |
| Origen | Primera región detectada |
| Lectura | Interpretación en lenguaje natural |

### 3. Histórico (líneas 96-99)

Muestras persistentes en tabla cronológica.

| Columna | Descripción |
|---------|-------------|
| Fecha | Timestamp formateado |
| Región | Región seleccionada |
| Fuente | Wikipedia, GTrends, Reddit, etc. |
| Geo | País o idioma específico |
| Bucket | es (hispano) o intl (internacional) |
| Top capturado | Título #1 de esa fuente |

### 4. Watchlist/Alias (líneas 101-118)

Gestión de términos y equivalencias.

**Formularios:**
- Input para nuevo término + botón Agregar
- Dos inputs para alias → canónico + botón Guardar

**Listados:**
- Nube de términos en watchlist (`#watchCloud`)
- Alertas recientes (`#alertsBox`)

### 5. Config (líneas 120-138)

Configuración del sistema.

**Sección Telegram:**
- Checkbox activar/desactivar
- Input BOT_TOKEN
- Input CHAT_ID
- Botón Guardar config
- Botón Probar Telegram

**Sección Exportar/Reset:**
- Botón Exportar JSON → `/api/export/json`
- Botón Exportar CSV → `/api/export/csv`
- Botón Borrar muestras (rojo, peligro)

**Nota:** Explica ubicación de la base SQLite.

### 6. Informe (líneas 140-145)

Reporte TXT generado automáticamente.

- Textarea de solo lectura con el informe
- Botón Copiar informe (clipboard)
- Botón Abrir TXT → `/api/report`

---

## JavaScript (líneas 152-373)

### Variables Globales

```javascript
appState   → Estado completo del sistema (de /api/state)
terms      → Array de términos agregados
outbreaks  → Array de brotes detectados
autoTimer  → ID del interval para auto-muestreo
```

### Funciones Principales

| Función | Descripción |
|---------|-------------|
| `$(id)` | Alias de getElementById |
| `fmt(ts)` | Formatea timestamp a fecha local |
| `esc(s)` | Escapa HTML para prevenir XSS |
| `setStatus(s)` | Actualiza indicador de estado |
| `badge(state)` | Genera HTML del badge según estado |

### Ciclo de Vida

```javascript
boot()           → Carga estado inicial, pobla selector de regiones
refreshAll()     → Recarga datos: state, terms, outbreaks
render()         → Actualiza toda la UI con datos actuales
renderRadar()    → Actualiza pestaña Radar
renderOutbreaks()→ Actualiza tabla de brotes
renderHistory()  → Actualiza tabla histórica
renderWatch()    → Actualiza watchlist y alias
renderAlerts()   → Actualiza lista de alertas
loadReport()     → Carga informe TXT en textarea
```

### Event Listeners

| Elemento | Evento | Acción |
|----------|--------|--------|
| `#runBtn` | click | POST /api/run → refreshAll() |
| `#autoBtn` | click | Toggle setInterval 15min |
| `#reportBtn` | click | Descargar /api/report |
| `#region` | change | Actualizar región seleccionada |
| `#threshold` | input | Actualizar label y POST /api/settings |
| `#addWatch` | click | POST /api/watchlist |
| `#addAlias` | click | POST /api/aliases |
| `#saveSettings` | click | POST /api/settings |
| `#testTelegram` | click | POST /api/telegram/test |
| `#resetBtn` | click | DELETE /api/reset?confirm=BORRAR |
| `#copyReport` | click | Copiar textarea a clipboard |
| `.tab` | click | Cambiar pestaña activa |

### Actualización en Tiempo Real

```javascript
// Reloj
setInterval(() => {
  $('clock').textContent = new Date().toLocaleTimeString('es-AR')
}, 1000)

// Auto-refresh del estado cada 30 segundos (si no está auto-activo)
setInterval(() => {
  if (!autoTimer) refreshAll()
}, 30000)
```

---

## Comunicación con Backend

### Función API

```javascript
async function api(path, opts={}) {
  const r = await fetch(path, opts)
  if (!r.ok) throw new Error(await r.text())
  const ct = r.headers.get('content-type') || ''
  return ct.includes('application/json') ? r.json() : r.text()
}
```

### Endpoints Utilizados

| Método | Endpoint | Uso en UI |
|--------|----------|-----------|
| GET | /api/state | Carga inicial y refrescos |
| GET | /api/terms | Nube de términos |
| GET | /api/outbreaks | Tabla de brotes |
| GET | /api/alerts | Lista de alertas |
| GET | /api/report | Textarea de informe |
| POST | /api/run | Botón "Tomar muestra" |
| POST | /api/watchlist | Agregar término |
| DELETE | /api/watchlist/{term} | Eliminar término (×) |
| POST | /api/aliases | Crear alias |
| POST | /api/settings | Guardar configuración |
| POST | /api/telegram/test | Probar bot |
| DELETE | /api/reset | Borrar todo |

---

## Diseño Responsive

### Breakpoints

| Media Query | Cambios |
|-------------|---------|
| `max-width: 1050px` | Grids de 4/3 cols → 2 cols |
| `max-width: 720px` | Grids → 1 columna, título más pequeño |

### UX Mobile

- Controles se apilan verticalmente
- Tablas con `overflow: auto` para scroll horizontal
- Botones de acceso rápido en la parte superior

---

## Características Especiales

### Indicador LIVE (líneas 13, 30)

```css
.live:before {
  content: '';
  display: inline-block;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--g);
  box-shadow: 0 0 12px var(--g);
  margin-right: 7px;
  animation: pulse 1.4s infinite
}
```

Punto verde pulsante que indica el backend está activo.

### Fondos con Gradiente (línea 12)

```css
background: 
  radial-gradient(circle at 12% 8%, rgba(232,163,61,.11), transparent 35%),
  radial-gradient(circle at 88% 20%, rgba(111,157,201,.06), transparent 35%),
  var(--bg);
```

Efecto de luces tenues en las esquinas superior izquierda (dorada) y superior derecha (azulada).

---

## Archivo: `frontend/index.html`
- **Líneas**: ~373
- **CSS**: Inline, ~90 líneas de estilos
- **JavaScript**: Inline, ~220 líneas de lógica
- **Dependencias externas**: Google Fonts (2 familias)
- **Frameworks**: Ninguno (vanilla JS)

---

## Notas para Desarrolladores

1. **No modificar estructura de IDs**: El JavaScript depende de IDs específicos (`#runBtn`, `#termCloud`, etc.)

2. **Clases CSS reutilizables**:
   - `.panel` para tarjetas
   - `.btn` para botones primarios
   - `.btn.ghost` para botones secundarios
   - `.badge.*` para estados

3. **Eventos globales**: La función `api()` maneja automáticamente JSON vs texto plano según Content-Type

4. **Estado compartido**: `appState`, `terms`, `outbreaks` son globales intencionalmente para compartir entre funciones de renderizado
