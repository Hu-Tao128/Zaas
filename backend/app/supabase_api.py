"""
Blueprint de ejemplo para demostrar el uso del cliente de Supabase.
Este archivo muestra cómo consultar, insertar y actualizar datos desde Supabase
usando el cliente centralizado en extensions.py.

Puedes adaptar estos patrones a tus propios blueprints o eliminar este archivo
cuando ya no lo necesites como referencia.
"""

from flask import Blueprint, jsonify, request, current_app
from app.extensions import get_supabase

supabase_bp = Blueprint('supabase_api', __name__, url_prefix='/api/supabase')


@supabase_bp.route('/health')
def health_check():
    """Verifica que el cliente de Supabase está conectado y funcional."""
    try:
        client = get_supabase()
        # Consulta simple para verificar conexión
        response = client.rpc('ping').execute()
        return jsonify({'status': 'ok', 'supabase': 'connected'})
    except RuntimeError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 503
    except Exception as e:
        current_app.logger.error(f'Error en Supabase health check: {e}')
        return jsonify({'status': 'error', 'message': 'Supabase no responde'}), 503


@supabase_bp.route('/todos', methods=['GET'])
def get_todos():
    """Ejemplo: obtener todos los registros de una tabla 'todos'."""
    try:
        client = get_supabase()
        response = client.table('todos').select('*').execute()
        todos = response.data
        return jsonify({'data': todos, 'count': len(todos)})
    except RuntimeError as e:
        return jsonify({'error': str(e)}), 503
    except Exception as e:
        current_app.logger.error(f'Error al obtener todos: {e}')
        return jsonify({'error': 'Error al obtener los datos'}), 500


@supabase_bp.route('/todos', methods=['POST'])
def create_todo():
    """Ejemplo: insertar un nuevo registro en la tabla 'todos'."""
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({'error': 'El campo "name" es obligatorio'}), 400

    try:
        client = get_supabase()
        response = client.table('todos').insert({'name': data['name']}).execute()
        return jsonify({'data': response.data}), 201
    except RuntimeError as e:
        return jsonify({'error': str(e)}), 503
    except Exception as e:
        current_app.logger.error(f'Error al crear todo: {e}')
        return jsonify({'error': 'Error al crear el registro'}), 500


@supabase_bp.route('/todos/<int:todo_id>', methods=['PATCH'])
def update_todo(todo_id):
    """Ejemplo: actualizar un registro existente en la tabla 'todos'."""
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({'error': 'El campo "name" es obligatorio'}), 400

    try:
        client = get_supabase()
        response = (
            client.table('todos')
            .update({'name': data['name']})
            .eq('id', todo_id)
            .execute()
        )
        if not response.data:
            return jsonify({'error': 'Todo no encontrado'}), 404
        return jsonify({'data': response.data})
    except RuntimeError as e:
        return jsonify({'error': str(e)}), 503
    except Exception as e:
        current_app.logger.error(f'Error al actualizar todo: {e}')
        return jsonify({'error': 'Error al actualizar el registro'}), 500


@supabase_bp.route('/todos/<int:todo_id>', methods=['DELETE'])
def delete_todo(todo_id):
    """Ejemplo: eliminar un registro de la tabla 'todos'."""
    try:
        client = get_supabase()
        response = client.table('todos').delete().eq('id', todo_id).execute()
        if not response.data:
            return jsonify({'error': 'Todo no encontrado'}), 404
        return jsonify({'message': 'Todo eliminado'}), 200
    except RuntimeError as e:
        return jsonify({'error': str(e)}), 503
    except Exception as e:
        current_app.logger.error(f'Error al eliminar todo: {e}')
        return jsonify({'error': 'Error al eliminar el registro'}), 500
