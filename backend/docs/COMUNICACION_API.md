# Comunicación: servicios y pantallas provisionales

El módulo usa los modelos existentes de SQLite/SQLAlchemy: `Conversacion`,
`Mensaje`, `Notificacion`, `Calificacion`, `Incidencia` y `SolicitudDemo`.
Esta última conserva su ubicación en `app.catalogo.models` para no romper
las referencias del catálogo. No hay cambios de esquema ni dependencias nuevas.

## Probar desde React

1. Arrancar Flask en el puerto 5000 y React con `pnpm dev` en el 3000.
2. Iniciar sesión con una cuenta Firebase vinculada a un usuario local.
3. Abrir **Comunicación** en el inicio, o `http://localhost:3000/comunicacion`.
4. Elegir Mensajes, Notificaciones, Solicitudes de demo, Calificaciones o Incidencias.

Las pantallas usan datos reales de la base local, no tarjetas ficticias.
Para mensajes se necesita un contrato existente entre cliente y desarrollador;
para calificaciones, ese contrato debe estar `finalizado`. Para demos se necesita
un proyecto `activo` con `demo_habilitada=True`. Si no existen, se muestra un
estado vacío. No se ejecuta `seed.py` ni se crean contratos o pagos desde este módulo.

Usar dos perfiles de navegador (o una ventana privada) para probar ambos usuarios.
Enviar un mensaje con uno, abrir el mismo contrato con el otro y pulsar **Recargar**.
**Marcar recibidos como leídos** confirma explícitamente la lectura.
El chat no usa Socket.IO, temporizadores ni recarga automática.

## Sesión y protección de las escrituras

Base: `/api/comunicacion`. Se reutiliza la cookie de sesión Flask creada por
`/auth/callback`; las llamadas usan `credentials: 'include'`.
Una sesión ausente devuelve JSON con código `401`, sin redirigir a una página HTML.

`GET /sesion` devuelve el usuario local y un `csrf_token`. Todas las escrituras
requieren la cabecera `X-CSRFToken` con ese valor, además de la cookie de sesión.
Se obtiene un token de la sesión vigente antes de cada escritura en el servicio React.
Las rutas POST que no necesitan campos admiten `{}`.

Ejemplo de respuesta de sesión:

```json
{
  "data": {"id": 1, "nombre": "Carlos Lopez", "email": "carlos@mail.com", "tipo_usuario": "cliente"},
  "csrf_token": "..."
}
```

Las listas usan `page=1&per_page=20` (máximo 100). Devuelven:

```json
{
  "data": [],
  "meta": {"page": 1, "per_page": 20, "total": 0, "pages": 0, "has_next": false}
}
```

Las fechas se entregan en ISO 8601 UTC. Los errores usan `{"error": "Descripción"}`:
`400` validación/CSRF, `401` sesión ausente, `403` permisos, `404` registro inexistente,
`409` estado incompatible o duplicado. Las creaciones devuelven `201`, salvo la apertura
idempotente de conversación, que devuelve `200` tanto si existe como si se crea.

## Endpoints

| Método | Ruta relativa | Comportamiento |
|---|---|---|
| GET | `/sesion` | Usuario local y token CSRF. |
| GET | `/admin/resumen` | Solo administradores: conteos reales de incidencias y últimos cinco reportes. |
| GET | `/contratos` | Contratos en los que participa el usuario; incluye estado y contraparte. |
| GET | `/conversaciones` | Conversaciones propias y contador de mensajes recibidos sin leer. |
| POST | `/contratos/<id>/conversacion` | Obtener o crear una conversación para ese contrato. |
| GET | `/conversaciones/<id>/mensajes` | Historial paginado, más reciente primero. No marca lecturas. |
| POST | `/conversaciones/<id>/mensajes` | Enviar `contenido`; notificar al otro participante. |
| POST | `/conversaciones/<id>/leer` | Marcar únicamente los mensajes recibidos en esa conversación. |
| GET | `/notificaciones` | Avisos propios; `solo_no_leidas=true` filtra. Incluye contador global `no_leidas`. |
| PATCH | `/notificaciones/<id>/leer` | Marcar una notificación propia. |
| POST | `/notificaciones/leer` | Marcar todas las notificaciones propias. |
| GET | `/proyectos-demo` | Proyectos activos con demo, excluyendo los del propio usuario. |
| GET | `/solicitudes-demo` | Solicitudes enviadas o recibidas sobre proyectos propios. |
| POST | `/proyectos/<id>/solicitudes-demo` | Solicitar demo con `nombre_contacto` y `correo_contacto`. |
| GET | `/calificaciones` | Calificaciones enviadas y recibidas por el usuario. |
| POST | `/contratos/<id>/calificaciones` | Calificar a la contraparte con `puntaje` y `comentarios` opcionales. |
| GET | `/incidencias` | Reportes propios. `todas=true` exige rol administrador. |
| POST | `/incidencias` | Registrar `tipo` y `descripcion`; notificar a administradores. |
| GET | `/incidencias/<id>` | Detalle, solo autor o administrador. |
| PATCH | `/incidencias/<id>/resolver` | Servicio reservado a administradores; requiere `resolucion`. |

No hay endpoint público para crear notificaciones arbitrarias para otros usuarios.
Los avisos se generan desde las operaciones autorizadas del backend.

## Reglas de negocio

- Mensajes: solo los dos participantes del contrato; el receptor se calcula en el
  servidor. Mensajes no vacíos de hasta 5000 caracteres. El frontend invierte cada
  página del historial para mostrarla cronológicamente.
- Notificaciones: solo el destinatario puede consultarlas o marcarlas.
- Demos: solo un cliente puede solicitar a otro usuario; correo válido y nombre
  hasta 150 caracteres. Se rechazan proyectos sin demo/inactivos y solicitudes
  repetidas del mismo cliente al mismo proyecto. La solicitud no tiene estado de
  aceptación en el modelo actual: no se inventa ese flujo ni una agenda.
- Calificaciones: solo participantes, contrato `finalizado`, entero 1–5,
  comentario hasta 2000 caracteres; una por evaluador y contrato. El destinatario
  se calcula en el servidor; no se acepta uno enviado por el navegador.
- Incidencias: tipos `acoso`, `fraude`, `incumplimiento`, `bug`, `otro`;
  descripción y resolución hasta 5000 caracteres. Resolver requiere administrador
  y notifica al reportante. No se puede resolver de nuevo una incidencia cerrada.

## Integración de los otros módulos

Importación recomendada:

```python
from app.comunicacion.services import crear_notificacion
from app.extensions import db

# Después de agregar el evento de negocio y antes de confirmar su transacción:
db.session.add(contrato)
db.session.flush()  # obtener contrato.id sin confirmar todavía
crear_notificacion(
    contrato.id_desarrollador,  # también acepta un objeto Usuario
    f'Nuevo contrato #{contrato.id}',
    f'/comunicacion?tab=mensajes&contrato={contrato.id}',
)
db.session.commit()  # confirma el contrato y su aviso juntos
```

`crear_notificacion(usuario, texto, link=None)` agrega el aviso a la sesión y
**no hace commit**. Si el evento falla, `db.session.rollback()` también revierte
el aviso. No hay que agregar commits dentro de esta función. El enlace debe ser
una ruta interna, con máximo 500 caracteres. El texto admite hasta 5000.
El import anterior desde `app.comunicacion.routes` sigue disponible por compatibilidad,
pero se recomienda importar desde `services`.

Ejemplos para los compañeros: contrato nuevo/aceptado, pago registrado/liberado,
entregable revisado o contrato finalizado. Al finalizar pueden avisar a ambos
participantes con `/comunicacion?tab=calificaciones&contrato=<id>`.
Esos eventos de contratos/pagos **no se conectan automáticamente** en este cambio:
sus módulos deben llamar a la función dentro de su propia transacción.
Mensajes, solicitudes de demo, calificaciones e incidencias ya generan sus avisos.

## Pruebas

Desde `backend`:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Desde `frontend`:

```powershell
node --test tests/comunicacionService.test.js
node --test tests/authBackend.test.js
pnpm build
```

Las pruebas del backend usan SQLite en memoria y sesiones locales controladas;
no contactan Firebase/Supabase ni modifican bases o cuentas reales. Cubren permisos,
CSRF, validación, historial, lecturas, avisos, rollback, demos, calificaciones e incidencias.

## Límites de esta entrega

Incluye un panel administrativo provisional en `/admin`, con resumen de incidencias
y tarjetas de módulos por integrar. No incorpora dinero real, cambios en contratos/pagos,
Socket.IO ni sincronización con Supabase. El endpoint `/admin/resumen` devuelve `401`
sin sesión y `403` para cualquier rol distinto de `admin`. El menú solo muestra el
enlace administrativo a ese rol; escribir la URL directamente tampoco concede acceso.

Para proteger el panel se eliminó la alternativa de acceso con tokens sin firma y
se impidió asignar `admin` desde el registro público. Firebase debe estar configurado
para iniciar sesión; los administradores existentes conservan su rol local.
El resto de la autenticación global, incluido su cierre de sesión, requiere su
revisión independiente antes de publicar.

La sincronización de una misma cuenta es idempotente: un reintento no crea otro
usuario ni sobrescribe su rol. Si dos peticiones intentan insertar el mismo UID,
el backend revierte la transacción fallida y recupera al usuario que ya se guardó.
El frontend comparte las peticiones simultáneas del formulario y del observador
Firebase; al cambiar de cuenta se conserva el orden de las sincronizaciones.
El formulario de registro por correo crea una cuenta Firebase, y usa la misma
sincronización que el inicio de sesión para establecer una cuenta local de cliente.

Se conserva el esquema local existente. Las comprobaciones de duplicados de demos,
conversaciones y calificaciones cubren las peticiones secuenciales; para múltiples
peticiones simultáneas hace falta una migración con restricciones únicas, después de
depurar los posibles duplicados existentes. Esa migración debe coordinarse con el equipo.
