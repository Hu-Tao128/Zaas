"""
Script para crear las tablas iniciales en Supabase (PostgreSQL).
Ejecuta migraciones SQL directamente vía la API de Supabase.

Uso:
    python supabase_setup.py
"""

import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv(override=True)

SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Error: SUPABASE_URL y SUPABASE_KEY deben estar configuradas en .env")
    exit(1)

# La API de SQL de Supabase requiere la service_role key
API_URL = f"{SUPABASE_URL}/rest/v1"
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal",
}

# ── Tablas para datos compartidos/sincronizados ─────────────────────

# Estas tablas complementan las locales de SQLite y se usan para:
# - Notificaciones entre usuarios
# - Métricas y analytics compartidos
# - Logs de actividad
# - Configuración global (feature flags)

SQL_MIGRATIONS = """
-- Tabla de notificaciones push (compartidas entre instancias)
CREATE TABLE IF NOT EXISTS notificaciones_sync (
    id BIGSERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL,
    tipo VARCHAR(50) NOT NULL,
    titulo VARCHAR(200),
    mensaje TEXT,
    leido BOOLEAN DEFAULT FALSE,
    creado_en TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB
);

-- Índice para consultas frecuentes
CREATE INDEX IF NOT EXISTS idx_notificaciones_usuario 
    ON notificaciones_sync(usuario_id, leido) WHERE NOT leido;

-- Tabla de métricas/analytics compartidas
CREATE TABLE IF NOT EXISTS metricas_proyecto (
    id BIGSERIAL PRIMARY KEY,
    proyecto_id INTEGER,
    evento VARCHAR(50) NOT NULL,
    usuario_id INTEGER,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB
);

-- Índice para consultas por fecha
CREATE INDEX IF NOT EXISTS idx_metricas_timestamp 
    ON metricas_proyecto(timestamp DESC);

-- Tabla de logs de actividad (auditoría compartida)
CREATE TABLE IF NOT EXISTS actividad_log (
    id BIGSERIAL PRIMARY KEY,
    usuario_id INTEGER,
    accion VARCHAR(100) NOT NULL,
    entidad VARCHAR(50),
    entidad_id INTEGER,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    ip_address VARCHAR(45),
    metadata JSONB
);

-- Índice para auditoría por usuario
CREATE INDEX IF NOT EXISTS idx_actividad_usuario 
    ON actividad_log(usuario_id, timestamp DESC);

-- Tabla de configuración global (feature flags, settings)
CREATE TABLE IF NOT EXISTS config_global (
    id BIGSERIAL PRIMARY KEY,
    clave VARCHAR(100) UNIQUE NOT NULL,
    valor JSONB NOT NULL,
    descripcion TEXT,
    actualizado_en TIMESTAMPTZ DEFAULT NOW()
);

-- Datos iniciales de configuración
INSERT INTO config_global (clave, valor, descripcion) VALUES
    ('feature_ofertas', '{"enabled": true}', 'Habilitar sistema de ofertas de trabajo'),
    ('feature_contratos', '{"enabled": true}', 'Habilitar sistema de contratos'),
    ('feature_mensajes', '{"enabled": true}', 'Habilitar mensajería entre usuarios')
ON CONFLICT (clave) DO NOTHING;
"""


def ejecutar_sql():
    """Ejecuta SQL en Supabase vía la API REST."""
    print("📋 Creando tablas en Supabase...")
    print(f"🔗 URL: {SUPABASE_URL}")
    print()

    # Supabase no permite ejecutar SQL arbitrario vía REST API directamente.
    # La forma correcta es usar el SQL Editor en el dashboard o la CLI.
    # Pero podemos verificar si las tablas existen usando la API.

    print("⚠️  Supabase no permite ejecutar DDL (CREATE TABLE) vía REST API.")
    print("   Las tablas deben crearse manualmente en el SQL Editor.\n")
    
    print("=" * 70)
    print("📝 SQL para ejecutar en Supabase Dashboard:")
    print("=" * 70)
    print(SQL_MIGRATIONS)
    print("=" * 70)
    
    print("\n📌 Instrucciones:")
    print("1. Ve a: https://app.supabase.com → tu proyecto → SQL Editor")
    print("2. Pega el SQL de arriba y ejecútalo")
    print("3. Verifica con:")
    print("   python supabase_setup.py --verify")
    
    return True


def verificar_tablas():
    """Verifica que las tablas existen en Supabase."""
    print("🔍 Verificando tablas en Supabase...\n")
    
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    tablas_esperadas = [
        'notificaciones_sync',
        'metricas_proyecto', 
        'actividad_log',
        'config_global',
    ]
    
    todas_ok = True
    
    for tabla in tablas_esperadas:
        try:
            response = supabase.table(tabla).select('*').limit(1).execute()
            print(f"  ✅ {tabla}")
        except Exception as e:
            error_msg = str(e)[:80]
            print(f"  ❌ {tabla} — {error_msg}")
            todas_ok = False
    
    print()
    if todas_ok:
        print("✅ Todas las tablas están creadas y accesibles.")
    else:
        print("❌ Algunas tablas faltan. Ejecuta: python supabase_setup.py")
    
    return todas_ok


if __name__ == "__main__":
    import sys
    
    if "--verify" in sys.argv:
        verificar_tablas()
    else:
        ejecutar_sql()
