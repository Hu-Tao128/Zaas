"""Utilidades para normalizar cadenas de conexión a PostgreSQL/Supabase."""

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def normalizar_database_url(url):
    """Adapta URLs de Postgres de Coolify/Supabase/Heroku para SQLAlchemy.

    - ``postgres://`` (Heroku/Coolify) y ``postgresql://`` se fuerzan a usar el
      driver ``psycopg2`` que ya está instalado en la imagen.
    - Se eliminan parámetros propios de Prisma (``pgbouncer``,
      ``connection_limit``, ``schema``) que ``psycopg2``/libpq rechazan.
    - En hosts de Supabase se añade ``sslmode=require`` si no viene definido.
    """
    if url.startswith('postgres://'):
        url = 'postgresql+psycopg2://' + url[len('postgres://'):]
    elif url.startswith('postgresql://'):
        url = 'postgresql+psycopg2://' + url[len('postgresql://'):]

    partes = urlsplit(url)
    if not partes.scheme.startswith('postgresql'):
        return url

    excluir = {'pgbouncer', 'connection_limit', 'schema'}
    query = [
        (clave, valor)
        for clave, valor in parse_qsl(partes.query)
        if clave.lower() not in excluir
    ]

    host = (partes.hostname or '').lower()
    es_supabase = host.endswith('.supabase.co') or host.endswith('.supabase.com')
    tiene_sslmode = any(clave.lower() == 'sslmode' for clave, _ in query)
    if es_supabase and not tiene_sslmode:
        query.append(('sslmode', 'require'))

    return urlunsplit(partes._replace(query=urlencode(query)))
