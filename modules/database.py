"""
P2 #22, #23: Módulo de base de datos y migraciones separado de app.py
"""
import sqlite3
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("observatorio")


class DatabaseContext:
    """P1: Context manager que garantiza cierre explícito de conexiones SQLite"""
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
    
    def __enter__(self) -> sqlite3.Connection:
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        return self.conn
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            # Bug #1 CRÍTICO: commit automático si no hubo excepción (comportamiento nativo de sqlite3)
            if exc_type is None:
                self.conn.commit()
            self.conn.close()
        return False


def add_column_if_not_exists(db: sqlite3.Connection, table: str, column: str, col_type: str):
    """P2 #22: Helper de migración - agrega columna si no existe"""
    try:
        db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        logger.info(f"Migración: agregada columna {column} a {table}")
    except sqlite3.OperationalError:
        pass  # Columna ya existe


def run_migrations(db: sqlite3.Connection):
    """P2 #22: Ejecutar todas las migraciones en orden"""
    logger.info("Ejecutando migraciones...")
    
    # Migración 1: alert_level en alerts
    add_column_if_not_exists(db, "alerts", "alert_level", "TEXT DEFAULT 'OBSERVADO'")
    
    # Migración 2: title_hash en term_hits
    add_column_if_not_exists(db, "term_hits", "title_hash", "TEXT")
    
    logger.info("Migraciones completadas")


def init_db_module(db_path: Path):
    """P2 #22: Inicializar schema base (sin migraciones mezcladas)"""
    with DatabaseContext(db_path) as db:
        # Schema base - solo creación inicial
        db.execute("""
            CREATE TABLE IF NOT EXISTS samples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                ts REAL NOT NULL,
                region TEXT NOT NULL,
                source TEXT NOT NULL,
                geo TEXT NOT NULL,
                bucket TEXT NOT NULL,
                top_title TEXT,
                top_title_translated TEXT,
                en_title TEXT,
                raw_json TEXT
            )
        """)
        
        db.execute("""
            CREATE TABLE IF NOT EXISTS term_hits (
                run_id TEXT,
                source TEXT,
                geo TEXT,
                bucket TEXT,
                term TEXT,
                ts REAL,
                score REAL,
                url TEXT,
                title TEXT,
                word_count INTEGER DEFAULT 1,
                is_generic INTEGER DEFAULT 0,
                category TEXT,
                title_hash TEXT
            )
        """)
        
        db.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts REAL NOT NULL,
                type TEXT NOT NULL,
                term TEXT NOT NULL,
                level TEXT NOT NULL,
                confidence TEXT NOT NULL,
                alert_level TEXT NOT NULL,
                message TEXT NOT NULL,
                meta_json TEXT NOT NULL
            )
        """)
        
        db.execute("""
            CREATE TABLE IF NOT EXISTS samples_meta (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL UNIQUE,
                ts REAL NOT NULL,
                source_count INTEGER DEFAULT 0,
                sample_size INTEGER DEFAULT 0,
                region TEXT DEFAULT 'unknown'
            )
        """)
        
        db.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                term TEXT PRIMARY KEY,
                created_ts REAL NOT NULL,
                is_critical INTEGER DEFAULT 0
            )
        """)
        
        db.execute("""
            CREATE TABLE IF NOT EXISTS aliases (
                alias TEXT PRIMARY KEY,
                canonical TEXT NOT NULL,
                phenomenon TEXT,
                created_ts REAL NOT NULL
            )
        """)
        
        db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        
        db.execute("""
            CREATE TABLE IF NOT EXISTS observation_tray (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts REAL NOT NULL,
                term TEXT NOT NULL UNIQUE,
                estado TEXT NOT NULL,
                confidence TEXT NOT NULL,
                category TEXT,
                first_seen REAL NOT NULL,
                last_seen REAL NOT NULL,
                runs_count INTEGER DEFAULT 1,
                regions_count INTEGER DEFAULT 1,
                sources_count INTEGER DEFAULT 1,
                delta REAL DEFAULT 0,
                emergency REAL DEFAULT 0,
                promoted_to_alert INTEGER DEFAULT 0
            )
        """)
        
        # P2 #22: Ejecutar migraciones separadas después del schema base
        run_migrations(db)
        
        # Índices
        db.execute("CREATE INDEX IF NOT EXISTS idx_samples_run ON samples(run_id)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_term_hits_term ON term_hits(term)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_term_hits_title_hash ON term_hits(term, title_hash)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_alerts_ts ON alerts(ts)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_observation_tray_term ON observation_tray(term)")
        
        # Bug #4: Insertar defaults
        from datetime import datetime
        ts_now = datetime.now().timestamp()
        
        # Watchlist defaults
        watchlist_defaults = ["dragon ball", "messi", "ransomware", "openai"]
        for term in watchlist_defaults:
            db.execute(
                "INSERT OR IGNORE INTO watchlist(term, created_ts) VALUES (?, ?)",
                (term.lower().strip(), ts_now)
            )
        
        # Aliases defaults
        aliases_defaults = {
            "leo messi": "messi",
            "lionel messi": "messi",
            "inter miami": "messi",
            "chatgpt": "openai",
            "gpt": "openai",
            "gpt 5": "openai",
            "dragon ball daima": "dragon ball",
            "dbz": "dragon ball",
            "goku": "dragon ball",
            "goku vegeta": "dragon ball",
            "broly": "dragon ball",
            "dragon ball super": "dragon ball",
            "vegeta": "dragon ball",
            "bitcoin": "criptomonedas",
            "btc": "criptomonedas",
            "ethereum": "criptomonedas",
            "eth": "criptomonedas",
            "crypto": "criptomonedas",
            "altcoin": "criptomonedas",
            "covid": "pandemia",
            "coronavirus": "pandemia",
            "sars": "pandemia",
            "pandemia": "pandemia",
            "ia": "inteligencia artificial",
            "ai": "inteligencia artificial",
            "chat gpt": "openai",
            "gpt4": "openai",
            "gpt-4": "openai",
        }
        for alias, canonical in aliases_defaults.items():
            db.execute(
                "INSERT OR IGNORE INTO aliases(alias, canonical, created_ts) VALUES (?, ?, ?)",
                (alias.lower().strip(), canonical.lower().strip(), ts_now)
            )
        
        # Settings defaults
        settings_defaults = {
            "outbreak_threshold": "45",
            "telegram_enabled": "false",
            "telegram_bot_token": "",
            "telegram_chat_id": "",
            "api_reset_token": "",
        }
        for key, value in settings_defaults.items():
            db.execute(
                "INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)",
                (key, value)
            )
        
        db.commit()
        logger.info("Base de datos inicializada con defaults")
