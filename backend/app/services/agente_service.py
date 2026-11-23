"""Motor conversacional del agente ECBD de Zaas (basado en reglas, sin LLM).

Traduce mensajes en lenguaje natural a las mismas herramientas que expone el
servidor MCP (`mcp_server/zaas_mcp.py`), reutilizando `ecbd_service`. El
emparejamiento de intenciones es determinista y auditable: no depende de un
proveedor de IA externo ni de una API key.
"""

from __future__ import annotations

import re
import unicodedata

from app.services.ecbd_service import (
    ejecutar_etl_saneamiento,
    exportar_dataset_limpio,
    obtener_kpis_dashboard,
)

MENSAJE_AYUDA = (
    'Soy el agente del ECBD de Zaas. Puedo ayudarte con estas acciones:\n'
    '• "¿Cuál es el estado del ECBD?" → KPIs, latencia y anomalías.\n'
    '• "Ejecuta el ETL" → sanea las telemetrías pendientes (solo administradores).\n'
    '• "Genera un dataset de 50 registros" → exporta datos limpios para análisis.\n'
    'Escribe una de esas frases o usa los accesos rápidos.'
)

_PALABRAS_ETL = (
    'etl', 'pipeline', 'sanea', 'saneamiento', 'saneando', 'procesa',
    'procesar', 'procesamiento', 'limpieza', 'limpia', 'depura', 'pendientes',
)
_PALABRAS_DATASET = (
    'dataset', 'datos', 'exporta', 'exportar', 'exportacion', 'entrenamiento',
    'analisis', 'analitico', 'csv', 'descarga', 'descargar', 'muestra',
)
_PALABRAS_ESTADO = (
    'estado', 'kpi', 'kpis', 'salud', 'resumen', 'metrica', 'metricas',
    'latencia', 'anomalia', 'anomalias', 'telemetria', 'monitor', 'monitoreo',
    'como esta', 'que tal', 'diagnostico',
)
_PALABRAS_AYUDA = (
    'ayuda', 'help', 'hola', 'buenas', 'que puedes', 'que haces', 'opciones',
    'comandos', 'menu', 'instrucciones',
)

_ACCIONES = ('etl', 'dataset', 'estado')


def _normalizar(texto: str) -> str:
    """Minúsculas y sin acentos para comparar palabras clave."""
    base = unicodedata.normalize('NFKD', texto or '')
    sin_acentos = ''.join(c for c in base if not unicodedata.combining(c))
    return re.sub(r'\s+', ' ', sin_acentos.lower()).strip()


def _coincidencias(texto: str, palabras) -> int:
    return sum(1 for palabra in palabras if palabra in texto)


def detectar_intencion(mensaje: str) -> dict:
    """Devuelve la intención dominante y el límite pedido para el dataset."""
    texto = _normalizar(mensaje)
    if not texto:
        return {'intencion': 'ayuda', 'limite': 100}

    puntajes = {
        'etl': _coincidencias(texto, _PALABRAS_ETL),
        'dataset': _coincidencias(texto, _PALABRAS_DATASET),
        'estado': _coincidencias(texto, _PALABRAS_ESTADO),
        'ayuda': _coincidencias(texto, _PALABRAS_AYUDA),
    }
    # Las acciones reales pesan más que un simple saludo ("hola, ¿cómo está?").
    peso = {clave: (valor * 2 if clave in _ACCIONES else valor)
            for clave, valor in puntajes.items()}
    intencion = max(peso, key=peso.get)
    if peso[intencion] == 0:
        intencion = 'ayuda'

    return {'intencion': intencion, 'limite': _extraer_limite(texto)}


def _extraer_limite(texto: str, por_defecto: int = 100) -> int:
    coincidencia = re.search(r'(\d{1,4})', texto)
    if not coincidencia:
        return por_defecto
    return max(1, min(int(coincidencia.group(1)), 5000))


def _resumen_kpis(datos: dict) -> str:
    lineas = [
        f"Registros totales: {datos.get('total_registros', 0)}",
        f"Anomalías detectadas: {datos.get('total_anomalias', 0)}",
        f"Latencia promedio: {datos.get('latencia_promedio_ms', 0.0)} ms",
    ]
    modulos = datos.get('eventos_por_modulo') or {}
    if modulos:
        detalle = ', '.join(f"{modulo}: {cantidad}" for modulo, cantidad in sorted(modulos.items()))
        lineas.append(f'Eventos por módulo: {detalle}')
    else:
        lineas.append('Aún no hay eventos por módulo registrados.')
    return '\n'.join(lineas)


def _vista_previa_dataset(filas: list) -> str:
    if not filas:
        return ('No hay registros procesados todavía. Ejecuta primero el ETL '
                'para poder exportar un dataset.')
    lineas = ['Vista previa (primeros 5):']
    for fila in filas[:5]:
        anomalia = 'sí' if fila.get('anomalia_detectada') else 'no'
        lineas.append(
            f"• #{fila.get('id_registro')} · {fila.get('modulo_evaluado') or 'general'}"
            f" · {fila.get('latencia_ms')} ms · anomalía: {anomalia}"
        )
    return '\n'.join(lineas)


def responder(mensaje: str, es_admin: bool = False) -> dict:
    """Resuelve un mensaje del usuario y devuelve la respuesta del agente.

    El resultado siempre incluye `accion` (para que el frontend pueda mostrar
    la etiqueta de la acción ejecutada), `respuesta` (texto para el chat) y
    `datos` (payload estructurado opcional).
    """
    deteccion = detectar_intencion(mensaje)
    intencion = deteccion['intencion']

    if intencion == 'estado':
        datos = obtener_kpis_dashboard()
        return {
            'accion': 'estado_ecbd',
            'respuesta': 'Este es el estado actual del ECBD:\n' + _resumen_kpis(datos),
            'datos': datos,
        }

    if intencion == 'etl':
        if not es_admin:
            return {
                'accion': 'etl_denegado',
                'respuesta': ('La ejecución del ETL solo está disponible para '
                              'administradores. Inicia sesión con una cuenta admin '
                              'para autorizar el saneamiento.'),
                'datos': None,
            }
        datos = ejecutar_etl_saneamiento()
        return {
            'accion': 'etl',
            'respuesta': (
                'Pipeline ETL ejecutado.\n'
                f"Saneados: {datos.get('saneados', 0)}\n"
                f"Descartados: {datos.get('descartados', 0)}\n"
                f"Total procesados: {datos.get('total_procesados', 0)}"
            ),
            'datos': datos,
        }

    if intencion == 'dataset':
        limite = deteccion['limite']
        filas = exportar_dataset_limpio(limite=limite)
        respuesta = (
            f'Generé un dataset analítico con {len(filas)} registros limpios.\n\n'
            + _vista_previa_dataset(filas)
        )
        return {
            'accion': 'dataset',
            'respuesta': respuesta,
            'datos': {'total': len(filas), 'muestra': filas[:5]},
        }

    return {'accion': 'ayuda', 'respuesta': MENSAJE_AYUDA, 'datos': None}
