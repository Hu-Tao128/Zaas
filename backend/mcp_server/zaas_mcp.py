import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from mcp.server.fastmcp import FastMCP

from app import create_app
from app.services.ecbd_service import (
    ejecutar_etl_saneamiento,
    exportar_dataset_limpio,
    obtener_kpis_dashboard,
)

flask_app = create_app()

MCP_TRANSPORT = os.environ.get('MCP_TRANSPORT', 'stdio').strip().lower()
if MCP_TRANSPORT not in ('stdio', 'sse'):
    MCP_TRANSPORT = 'stdio'

mcp = FastMCP(
    'Zaas-Backend-MCP',
    host=os.environ.get('MCP_HOST', '0.0.0.0'),
    port=int(os.environ.get('MCP_PORT', '8001')),
)


@mcp.tool()
def obtener_estado_ecbd() -> dict:
    """Devuelve KPIs, latencia promedio y anomalías detectadas por el ECBD."""
    with flask_app.app_context():
        return obtener_kpis_dashboard()


@mcp.tool()
def ejecutar_pipeline_etl() -> dict:
    """Sanea telemetrías pendientes y las marca como procesadas por el ETL."""
    with flask_app.app_context():
        return ejecutar_etl_saneamiento()


@mcp.tool()
def generar_dataset_analitico(limite: int = 500) -> list:
    """Genera un dataset limpio y plano listo para entrenamiento o análisis."""
    with flask_app.app_context():
        return exportar_dataset_limpio(limite=limite)


if __name__ == '__main__':
    mcp.run(transport=MCP_TRANSPORT)
