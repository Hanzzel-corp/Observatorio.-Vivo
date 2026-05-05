# run.sh - Script de Arranque Automático

## Descripción

Script bash que automatiza la configuración inicial y el arranque del Observatorio Vivo v6. Gestiona la creación del entorno virtual, instalación de dependencias e inicio del servidor.

---

## Ubicación

```
observatorio_v6_backend/
└── run.sh
```

---

## Código Completo

```bash
#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo ""
echo "Observatorio Vivo v6 iniciado en:"
echo "  http://127.0.0.1:8765"
echo ""

uvicorn app:app --reload --host 127.0.0.1 --port 8765
```

---

## Línea por Línea

### Shebang y Modo Estricto

```bash
#!/usr/bin/env bash
set -e
```

- `#!/usr/bin/env bash` - Usa el bash disponible en el PATH
- `set -e` - **Modo estricto**: el script se detiene si cualquier comando falla

### Cambio al Directorio del Script

```bash
cd "$(dirname "$0")"
```

- `$0` - Nombre del script
- `dirname "$0"` - Directorio donde está ubicado el script
- Garantiza que el script funcione desde cualquier directorio

**Ejemplo:**
```bash
# Funciona desde cualquier lugar
cd /tmp
/home/user/observatorio_v6_backend/run.sh  # OK
```

### Creación del Entorno Virtual

```bash
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
```

- Verifica si existe el directorio `.venv/`
- Si no existe, lo crea con `python3 -m venv`
- Si ya existe, lo reutiliza (preservando dependencias ya instaladas)

**¿Qué es un entorno virtual?**

Aislamiento de dependencias Python. Cada proyecto tiene sus propias librerías sin interferir con el sistema.

```
.venv/
├── bin/
│   ├── activate      # Script para activar el entorno
│   ├── python        # Python del entorno
│   └── pip           # Pip del entorno
├── lib/
│   └── python3.x/
│       └── site-packages/  ← Aquí se instalan las dependencias
└── pyvenv.cfg
```

### Activación del Entorno

```bash
source .venv/bin/activate
```

- Carga el entorno virtual en la shell actual
- Modifica `PATH` para usar Python/pip del entorno
- Modifica el prompt (opcionalmente) para indicar el entorno activo

**Indicadores de activación:**
```bash
# Antes
$ which python
/usr/bin/python3

# Después de source
(.venv) $ which python
/home/user/observatorio_v6_backend/.venv/bin/python
```

### Actualización de pip

```bash
python -m pip install --upgrade pip
```

- Asegura tener la última versión de pip
- Previene errores de instalación por versiones antiguas

### Instalación de Dependencias

```bash
python -m pip install -r requirements.txt
```

- Lee `requirements.txt`
- Instala cada paquete listado
- Si ya están instalados, los mantiene (no reinstala)

**Contenido de requirements.txt:**
```
fastapi==0.115.6
uvicorn[standard]==0.34.0
httpx==0.28.1
pydantic==2.10.5
```

### Mensaje de Inicio

```bash
echo ""
echo "Observatorio Vivo v6 iniciado en:"
echo "  http://127.0.0.1:8765"
echo ""
```

- Línea en blanco para separación visual
- Información clara de dónde acceder
- Otra línea en blanco antes del servidor

### Inicio del Servidor

```bash
uvicorn app:app --reload --host 127.0.0.1 --port 8765
```

**Parámetros:**

| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| `app:app` | módulo:objeto | Importa `app` desde `app.py` |
| `--reload` | flag | Recarga automática si cambia el código |
| `--host` | 127.0.0.1 | Solo accesible localmente (no desde red) |
| `--port` | 8765 | Puerto de escucha |

**Opciones de producción (no incluidas):**
```bash
# Sin reload, más workers, acceso remoto
uvicorn app:app --host 0.0.0.0 --port 8765 --workers 4
```

---

## Flujo de Ejecución

```
Usuario ejecuta ./run.sh
         ↓
    ┌────┴────┐
    ↓         ↓
 .venv      .venv
 existe?    no existe?
    │         ↓
    │    crear con
    │    python3 -m venv
    │         ↓
    └────┬────┘
         ↓
    activar entorno
    source .venv/bin/activate
         ↓
    actualizar pip
         ↓
    instalar dependencias
    pip install -r requirements.txt
         ↓
    mostrar mensaje de inicio
         ↓
    iniciar uvicorn
    http://127.0.0.1:8765
```

---

## Permisos

Para que el script sea ejecutable:

```bash
chmod +x run.sh
```

**Verificación:**
```bash
ls -l run.sh
# -rwxr-xr-x 1 user user 350 Apr 27 02:10 run.sh
#  ^^^
#  ejecutable
```

---

## Uso

### Ejecución directa

```bash
./run.sh
```

### Desde otro directorio

```bash
/path/to/observatorio_v6_backend/run.sh
```

### Con variables de entorno (opcional)

```bash
export UVICORN_WORKERS=4
./run.sh
```

---

## Detención

El script corre en primer plano. Para detener:

```bash
# En la terminal donde corre el servidor
Ctrl + C
```

Esto envía SIGTERM a uvicorn, que cierra gracefully las conexiones.

---

## Troubleshooting

### "Permission denied"

```bash
chmod +x run.sh
./run.sh
```

### "python3: command not found"

Instalar Python 3.8+:
```bash
# Ubuntu/Debian
sudo apt install python3 python3-venv

# macOS
brew install python3
```

### "Port already in use"

Otro proceso usa el puerto 8765:
```bash
# Encontrar y matar proceso
lsof -i :8765
kill -9 <PID>

# O cambiar puerto editando run.sh
uvicorn app:app --port 8766
```

### Dependencias no se instalan

```bash
# Borrar entorno corrupto y reintentar
rm -rf .venv
./run.sh
```

---

## Alternativa: Instalación Manual

Si prefieres control total:

```bash
# 1. Crear entorno
python3 -m venv .venv

# 2. Activar
source .venv/bin/activate

# 3. Instalar dependencias
pip install fastapi uvicorn httpx pydantic

# 4. Iniciar servidor
uvicorn app:app --reload --host 127.0.0.1 --port 8765
```

---

## Archivo: `run.sh`
- **Líneas**: 18
- **Dependencias**: bash, python3
- **Automatiza**: 4 pasos de configuración
- **Tiempo ahorrado**: ~30 segundos por ejecución
