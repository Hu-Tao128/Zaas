# Informe de cambios: módulo de comunicación de Zaas

**Fecha:** 2 de noviembre de 2026.  
**Alcance:** servicios de comunicación y pantallas provisionales en React.  
**Estado:** implementación local, con pruebas automatizadas y revisión visual.

Este documento explica qué se agregó, qué comportamiento cambió, cómo probarlo
y qué debe integrar el resto del equipo. Complementa la
[referencia de la API](backend/docs/COMUNICACION_API.md).

## 1. Objetivo de la entrega

Preparar el módulo asignado de comunicación para que el frontend pueda utilizar
mensajes, notificaciones, solicitudes de demo, calificaciones e incidencias.
El panel administrativo completo se pospone hasta que estén disponibles las
funciones de los demás compañeros.

Antes de esta entrega, Flask ya tenía modelos y páginas HTML para varias de estas
funciones. React tenía las pantallas de inicio de sesión, registro e inicio, pero
no contaba con pantallas conectadas a los servicios de comunicación.

Ahora se dispone de:

- Una API que devuelve JSON para el consumo desde React.
- Servicios compartidos con las reglas de negocio del módulo.
- Una función central de notificaciones que los demás módulos pueden llamar.
- Una sección de React con cinco pantallas provisionales conectadas al backend.
- Pruebas de permisos, validaciones, persistencia y tratamiento de errores.
- Documentación para el equipo.

## 2. Arquitectura y modelos aprovechados

El flujo principal queda organizado así:

```text
Pantallas de React
        ↓
comunicacionService.js
        ↓
API Flask: /api/comunicacion
        ↓
Servicios compartidos: app/comunicacion/services.py
        ↓
Modelos existentes de SQLAlchemy y base local SQLite
```

Las rutas HTML anteriores de Flask se conservan. Las operaciones de mensajes,
calificaciones, demos e incidencias actualizadas reutilizan los servicios
compartidos para reducir diferencias entre la interfaz anterior y la nueva API.

| Modelo | Ubicación conservada | Uso en esta entrega |
|---|---|---|
| `Conversacion` | `backend/app/comunicacion/models.py` | Agrupar mensajes por contrato. |
| `Mensaje` | `backend/app/comunicacion/models.py` | Guardar contenido, participantes y lectura. |
| `Notificacion` | `backend/app/comunicacion/models.py` | Guardar avisos y enlaces para un destinatario. |
| `SolicitudDemo` | `backend/app/catalogo/models.py` | Registrar el contacto de un cliente interesado en una demo. |
| `Calificacion` | `backend/app/comunicacion/models.py` | Registrar la evaluación de la contraparte al finalizar un contrato. |
| `Incidencia` | `backend/app/comunicacion/models.py` | Registrar reportes, estado, resolución y administrador responsable. |

No se crearon modelos nuevos, no se alteraron columnas ni tablas y no se agregaron
migraciones. `SolicitudDemo` conserva su ubicación en catálogo para mantener las
referencias existentes. No se agregaron dependencias a los archivos de paquetes.

## 3. Cambios del backend

### 3.1 Servicios compartidos

Se creó [services.py](backend/app/comunicacion/services.py) con estas funciones:

| Función | Responsabilidad |
|---|---|
| `texto_requerido` | Validar texto obligatorio, quitar espacios exteriores y limitar longitud. |
| `verificar_participante` | Comprobar que el usuario sea cliente o desarrollador del contrato. |
| `crear_notificacion` | Agregar un aviso para un usuario existente. |
| `obtener_conversacion` | Buscar la conversación del contrato y crearla si todavía no existe. |
| `enviar_mensaje` | Validar y registrar un mensaje y su notificación. |
| `registrar_calificacion` | Validar el contrato y registrar la evaluación de su contraparte. |
| `registrar_solicitud_demo` | Validar disponibilidad, contacto y duplicados antes de solicitar una demo. |
| `registrar_incidencia` | Crear un reporte y avisar a los administradores existentes. |
| `resolver_incidencia` | Registrar una resolución administrativa y avisar al reportante. |

Se agregó `ErrorComunicacion`, una excepción con mensaje y código de respuesta.
Permite que la API devuelva un error JSON y que las rutas HTML muestren el mismo
motivo mediante sus mensajes de pantalla.

Los servicios no confirman por su cuenta la transacción: las rutas llaman a
`db.session.commit()` después de completar la operación y sus avisos.

### 3.2 Función central de notificaciones

Antes, `crear_notificacion` estaba definida en el archivo de rutas y hacía un
`commit` interno. Eso podía confirmar otros cambios pendientes cuando un módulo
solo pretendía agregar un aviso.

Ahora se importa de esta forma:

```python
from app.comunicacion.services import crear_notificacion
```

Su firma es:

```python
crear_notificacion(usuario, texto, link=None)
```

Comportamiento actual:

- Acepta un objeto `Usuario` o su identificador entero.
- Comprueba que el destinatario exista.
- Exige texto no vacío, con un máximo de 5000 caracteres.
- Usa los primeros 200 caracteres como asunto y conserva el texto como mensaje.
- Acepta enlaces internos de hasta 500 caracteres y rechaza enlaces externos,
  rutas que empiezan con `//`, barras invertidas y caracteres de control.
- Agrega la notificación a la sesión sin confirmar la transacción.
- Devuelve el objeto `Notificacion` creado.

El import desde `app.comunicacion.routes` sigue disponible por compatibilidad,
pero el import recomendado es desde `services`.

### 3.3 Mensajería

Se implementó la apertura de conversaciones y el envío y consulta de mensajes
desde la API. La conversación se vincula a un contrato existente.

Reglas principales:

1. Solo los dos participantes pueden acceder al chat o enviar mensajes.
2. Ser administrador no concede acceso automático a chats de otros usuarios.
3. El receptor se determina en el servidor a partir del contrato; no se confía
   en un identificador de receptor enviado por el navegador.
4. El mensaje debe tener contenido y no superar los 5000 caracteres.
5. El envío genera una notificación para la contraparte.
6. El historial se consulta por páginas, con los mensajes más recientes primero.
7. React invierte el orden dentro de cada página para presentarla cronológicamente.
8. Consultar el historial por la API no cambia el estado de lectura. Una operación
   separada marca únicamente los mensajes recibidos por el usuario actual.

La búsqueda de conversación reutiliza la primera existente para el contrato.
El chat funciona con recarga manual: no se incorporaron Flask-SocketIO,
temporizadores ni actualizaciones automáticas.

### 3.4 Notificaciones

Se agregaron consultas paginadas, filtro de pendientes y marcado de lectura.
Cada usuario solo puede consultar y modificar sus propias notificaciones.

La respuesta de la lista contiene `no_leidas`, un contador de todos los avisos
pendientes del usuario, independiente de la página que esté consultando.

Se permite marcar un aviso individual o todos los avisos propios. No se expuso
una ruta para que el navegador cree notificaciones arbitrarias para otros usuarios.

### 3.5 Solicitudes de demo

La ruta anterior de catálogo ahora utiliza el mismo servicio que la API.
Se agregaron estas comprobaciones:

- El solicitante debe tener rol `cliente` y no ser el autor del proyecto.
- El proyecto debe estar `activo` y tener la demo habilitada.
- El nombre de contacto es obligatorio y admite hasta 150 caracteres.
- El correo es obligatorio, admite hasta 150 caracteres y debe tener formato válido.
  La validación no comprueba que el buzón exista ni envía correos.
- Se rechaza una solicitud repetida del mismo cliente para el mismo proyecto.
- El autor del proyecto recibe una notificación.

La lista muestra solo solicitudes enviadas por el usuario o recibidas sobre sus
propios proyectos. No se agregaron agenda, aceptación de solicitudes ni envío
automático de una demo: esos estados no existen en el modelo actual.

### 3.6 Calificaciones

Se preparó el servicio y la API para evaluar a la contraparte de un contrato.

- El contrato debe estar `finalizado`.
- El evaluador debe participar en él.
- La contraparte se calcula en el servidor.
- El puntaje debe ser un entero entre 1 y 5; se rechazan valores decimales,
  booleanos, textos y valores fuera del rango.
- El comentario es opcional y admite hasta 2000 caracteres.
- Se rechaza una segunda calificación del mismo evaluador para ese contrato.
- La persona evaluada recibe una notificación.
- Cada usuario puede consultar sus evaluaciones enviadas y recibidas.

También se corrigió el acceso a la ruta HTML anterior: un usuario ajeno al
contrato recibe `403` en lugar de poder abrir el formulario de calificación.

### 3.7 Incidencias y servicios administrativos

Se agregaron servicios para reportar, consultar y resolver incidencias.
Los tipos admitidos son `acoso`, `fraude`, `incumplimiento`, `bug` y `otro`.

La descripción es obligatoria y admite hasta 5000 caracteres. Al crear el reporte
se obtiene su identificador antes de preparar las notificaciones a administradores.

El usuario puede listar sus reportes. Para consultar todos mediante `todas=true`
se requiere rol administrador. El detalle solo es accesible para el reportante
o para un administrador.

La resolución exige un administrador y texto no vacío de hasta 5000 caracteres.
Guarda el responsable, la fecha y el estado `resuelta`, y notifica al reportante.
No permite resolver nuevamente una incidencia `resuelta` o `cerrada`.

En la ruta HTML anterior se corrigió un comportamiento importante: entrar mediante
`GET` a la dirección de resolución ya no modifica el reporte. La modificación se
ejecuta al enviar la operación de escritura.

Estos servicios preparan la integración futura del panel. La pantalla provisional
de React muestra **Mis incidencias**, incluso para administradores; todavía no es
una consola para administrar todos los reportes.

## 4. API JSON y protección de solicitudes

Se creó [api.py](backend/app/comunicacion/api.py) y se registró su blueprint en
`backend/app/__init__.py` con el prefijo `/api/comunicacion`.

La API utiliza la sesión Flask establecida por el acceso existente de Firebase.
Si no hay usuario autenticado devuelve `401` en JSON, en vez de redirigir al HTML
del inicio de sesión.

`GET /sesion` entrega los datos del usuario local y un token CSRF. Todas las
escrituras de esta API exigen la cookie de sesión y la cabecera `X-CSRFToken`.
Esta protección busca impedir escrituras iniciadas desde otro sitio usando una
sesión del usuario. No sustituye los controles de permisos de cada operación.

Las listas admiten `page` y `per_page`: página inicial 1, tamaño predeterminado 20
y máximo 100. Devuelven `data` y `meta`, con total de registros, páginas y si existe
una página siguiente. Las fechas se serializan en ISO 8601 UTC.

### 4.1 Endpoints disponibles

Todas las rutas de esta tabla tienen el prefijo `/api/comunicacion`.

| Método | Ruta | Uso |
|---|---|---|
| GET | `/sesion` | Obtener usuario local y token CSRF. |
| GET | `/contratos` | Listar contratos propios, su estado y la contraparte. |
| GET | `/conversaciones` | Listar conversaciones propias y mensajes pendientes. |
| POST | `/contratos/<id>/conversacion` | Obtener o crear la conversación de un contrato. |
| GET | `/conversaciones/<id>/mensajes` | Consultar historial paginado. |
| POST | `/conversaciones/<id>/mensajes` | Enviar un mensaje. |
| POST | `/conversaciones/<id>/leer` | Confirmar lectura de mensajes recibidos. |
| GET | `/notificaciones` | Consultar avisos propios y contador de pendientes. |
| PATCH | `/notificaciones/<id>/leer` | Marcar un aviso propio. |
| POST | `/notificaciones/leer` | Marcar todos los avisos propios. |
| GET | `/proyectos-demo` | Consultar proyectos activos con demo, excluyendo los propios. |
| GET | `/solicitudes-demo` | Consultar solicitudes enviadas y recibidas. |
| POST | `/proyectos/<id>/solicitudes-demo` | Solicitar una demo. |
| GET | `/calificaciones` | Consultar evaluaciones enviadas y recibidas. |
| POST | `/contratos/<id>/calificaciones` | Evaluar a la contraparte. |
| GET | `/incidencias` | Consultar reportes propios; todos con `todas=true` si es administrador. |
| POST | `/incidencias` | Registrar un reporte. |
| GET | `/incidencias/<id>` | Consultar detalle autorizado. |
| PATCH | `/incidencias/<id>/resolver` | Resolver un reporte como administrador. |

### 4.2 Respuestas y errores

Las creaciones devuelven `201`. Abrir una conversación devuelve `200`, tanto si
ya existía como si se acaba de crear. Las demás operaciones exitosas usan `200`.

| Código | Significado |
|---|---|
| `400` | Campos inválidos, JSON incorrecto, paginación inválida o CSRF ausente/expirado. |
| `401` | Falta una sesión autenticada. |
| `403` | El usuario no tiene permiso para esa operación. |
| `404` | El registro solicitado no existe. |
| `409` | Operación incompatible con el estado actual o registro repetido. |
| `500` | Error de persistencia; la API evita mostrar detalles internos de la base. |

Los errores manejados por el módulo usan `{"error": "Descripción"}`. Ante errores
de negocio o de base de datos se revierte la transacción para evitar guardar
parcialmente la operación y sus notificaciones.

## 5. Cambios del frontend

### 5.1 Servicio de acceso a la API

Se creó [comunicacionService.js](frontend/src/services/comunicacionService.js).

- `consultar(path)` realiza consultas bajo `/api/comunicacion`.
- `guardar(path, data, method)` realiza escrituras; por defecto utiliza `POST`.
- Las solicitudes incluyen la cookie de sesión mediante `credentials: 'include'`.
- Antes de escribir se solicita el token CSRF de la sesión vigente, evitando
  conservar uno de una cuenta usada anteriormente.
- Los errores de la API se convierten en mensajes que las pantallas pueden mostrar.
- También se manejan respuestas que no son JSON y errores HTTP del servidor.

### 5.2 Ruta, navegación e inicio de sesión

En `App.jsx` se agregó `/comunicacion`, protegida con el componente `ProtectedRoute`
existente. En `HomePage.jsx` se agregó el enlace **Comunicación**.

En `LoginPage.jsx` se ajustaron tanto el acceso por correo como el de Google para
navegar a `/` después de una respuesta exitosa. Antes se utilizaba la redirección
`/catalogo/` entregada por Flask, que no corresponde a una pantalla de React.
Este ajuste mantiene la navegación en las rutas de React; no modifica Firebase,
contraseñas, roles ni el servicio de autenticación global.

### 5.3 Pantallas provisionales

Se creó [ComunicacionPage.jsx](frontend/src/pages/ComunicacionPage.jsx), con estas secciones:

| Sección | Elementos disponibles |
|---|---|
| Mensajes | Selector de contrato, lista de conversaciones, contador de mensajes pendientes, historial, envío y confirmación de lectura. |
| Notificaciones | Contador de pendientes, filtro de no leídas, marcado individual/general y enlaces de actividad reconocidos. |
| Solicitudes de demo | Formulario para clientes, proyectos disponibles y listado de solicitudes enviadas/recibidas. |
| Calificaciones | Selector de contratos finalizados, puntaje, comentario e historial enviado/recibido. |
| Incidencias | Formulario de reporte, listado propio, estado y resolución cuando existe. |

Las pantallas consultan los datos de la base local mediante la API. No se añadieron
tarjetas ficticias para aparentar conversaciones, contratos o solicitudes.
Cuando faltan registros se muestran estados vacíos que explican la situación.

El archivo también incluye utilidades para consultar recursos, paginar, ejecutar
acciones y mostrar carga, confirmaciones y errores. Los formularios conservan el
contenido cuando una solicitud falla y deshabilitan las acciones mientras se procesa
la operación. Los listados tienen botones de recarga manual.

Las pestañas se reflejan en la URL con `tab=mensajes`, `tab=notificaciones`,
`tab=demos`, `tab=calificaciones` o `tab=incidencias`. Un enlace puede incluir
`contrato=<id>` para preseleccionarlo en mensajes o calificaciones. En mensajes,
el usuario todavía pulsa **Abrir conversación**.

### 5.4 Estilos y accesibilidad básica

Se creó [comunicacion.css](frontend/src/pages/comunicacion.css) para dar a la sección
una presentación consistente sin rediseñar las demás pantallas del proyecto.
Incluye paneles, pestañas, mensajes diferenciados entre emisor y receptor,
etiquetas de estado y formularios adaptados a pantallas pequeñas.

Se añadieron indicadores visibles de enfoque, etiquetas de formulario, avisos
de carga y regiones para anunciar confirmaciones o errores. Se comprobó que la
pantalla móvil evaluada no tuviera desbordamiento horizontal. Esto es una revisión
básica, no una auditoría completa de accesibilidad o compatibilidad de navegadores.

## 6. Inventario de archivos

### 6.1 Archivos agregados

| Archivo | Contenido |
|---|---|
| `backend/app/comunicacion/services.py` | Reglas de negocio y función central de notificaciones. |
| `backend/app/comunicacion/api.py` | Endpoints JSON, sesión, CSRF, serialización y errores. |
| `backend/tests/test_comunicacion.py` | Trece pruebas automatizadas del backend. |
| `backend/docs/COMUNICACION_API.md` | Referencia técnica e instrucciones de integración. |
| `frontend/src/services/comunicacionService.js` | Cliente de la API para React. |
| `frontend/src/pages/ComunicacionPage.jsx` | Cinco pantallas provisionales del módulo. |
| `frontend/src/pages/comunicacion.css` | Estilos de la sección y adaptación móvil. |
| `frontend/tests/comunicacionService.test.js` | Cuatro pruebas del cliente de la API. |
| `CAMBIOS_COMUNICACION.md` | Este informe detallado. |

### 6.2 Archivos modificados

| Archivo | Cambio |
|---|---|
| `backend/app/__init__.py` | Importar y registrar el blueprint de la API de comunicación. |
| `backend/app/comunicacion/routes.py` | Reutilizar servicios, corregir permisos de calificación y evitar resolución mediante GET. |
| `backend/app/catalogo/routes.py` | Usar el servicio común para solicitudes de demo y presentar sus errores. |
| `frontend/src/App.jsx` | Registrar la ruta protegida `/comunicacion`. |
| `frontend/src/pages/HomePage.jsx` | Incorporar el enlace de acceso a Comunicación. |
| `frontend/src/pages/LoginPage.jsx` | Mantener la navegación posterior al acceso dentro de React. |
| `README.md` | Documentar el acceso y enlazar la referencia técnica y este informe. |

Los cambios preexistentes en archivos de configuración o credenciales no forman
parte de esta implementación y no se describen como trabajo del módulo.

## 7. Pruebas y resultados

### 7.1 Backend: 13 pruebas aprobadas

Se agregó una suite que crea una aplicación de pruebas con SQLite en memoria.
Las sesiones se controlan dentro de las pruebas; no se inicia sesión en cuentas
Firebase reales ni se contactan servicios remotos.

| Prueba | Comportamiento comprobado |
|---|---|
| Sesión y CSRF | Rechazo de consultas sin sesión y de escrituras sin token. |
| JSON y paginación | Rechazo de cuerpos no válidos y parámetros fuera de rango. |
| Privacidad de contratos/conversaciones | Un tercero no puede listar ni acceder a conversaciones ajenas. |
| Mensajes y lectura | Receptor calculado en servidor, aviso a la contraparte y lectura solo de recibidos. |
| Validación e historial | Rechazo de mensajes vacíos/demasiado largos y orden de páginas. |
| Transacción de notificaciones | El helper no confirma cambios y sus avisos se revierten con rollback. |
| Propiedad de notificaciones | Un usuario no puede marcar avisos de otro; marcado general limitado al propietario. |
| Solicitud de demo | Visibilidad para cliente/autor, notificación y rechazo de repetición. |
| Disponibilidad/contacto de demo | Rechazo de proyectos sin demo, cerrados y contactos inválidos. |
| Elegibilidad para calificar | Exige contrato finalizado y participación, incluida la ruta HTML anterior. |
| Datos de calificación | Puntaje válido, contraparte correcta, rechazo de repetición y aviso. |
| Ciclo de incidencia | Privacidad, permisos de administrador, resolución y notificación al reportante. |
| Incidencias inválidas | Rechazo de datos incorrectos sin dejar reportes o avisos parciales. |

### 7.2 Cliente frontend: 4 pruebas aprobadas

Se verificó que las consultas incluyan la sesión, las escrituras obtengan CSRF
antes de enviar datos, una sesión rechazada detenga la escritura y los errores
de validación o respuestas HTML no se presenten como operaciones exitosas.

### 7.3 Compilación y revisión visual

- `pnpm build` terminó correctamente.
- La revisión en navegador usó respuestas de API simuladas para recorrer mensajes,
  notificaciones, demos, calificaciones e incidencias.
- Se comprobó envío de mensajes, lectura de avisos, solicitud de demo, rechazo de
  una demo repetida, envío de una calificación y creación de una incidencia.
- Se revisaron vistas de escritorio y móvil, sin errores de ejecución registrados
  en esa prueba y sin desbordamiento horizontal en la vista móvil evaluada.
- `git diff --check` no detectó errores de espacios en los cambios revisados.

Estas comprobaciones no equivalen a una prueba completa con cuentas reales,
Firebase, Supabase y todos los módulos del equipo funcionando juntos.
El acceso posterior del usuario a `admin@zaas.com` fue una comprobación real hecha
por él; no implica que las contraseñas de otras cuentas se conozcan o se hayan probado.

### 7.4 Cómo volver a ejecutar las pruebas

Desde `backend`, usando el entorno `.venv` existente:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Desde `frontend`:

```powershell
node --test tests/comunicacionService.test.js
pnpm build
```

Si el entorno Python local se llama `venv`, sustituir `.venv` por `venv`.
Las pruebas automatizadas del backend crean y eliminan únicamente sus tablas
temporales en memoria; no utilizan la base local de trabajo.

## 8. Cómo probarlo con cuentas del proyecto

1. Iniciar Flask desde `backend` y React desde `frontend` como se describe en el README.
2. Abrir `http://localhost:3000` e iniciar sesión.
3. Pulsar **Comunicación** o abrir `http://localhost:3000/comunicacion`.
4. Para mensajes, utilizar un cliente y un desarrollador que compartan un contrato.
   Abrir cada cuenta en un perfil de navegador distinto o en una ventana privada.
5. Enviar un mensaje con uno de los participantes y pulsar **Recargar** con el otro.
6. Confirmar lectura con **Marcar recibidos como leídos** y revisar las notificaciones
   en su pestaña; marcar un mensaje y marcar una notificación son acciones distintas.
7. Para demos, entrar como cliente y seleccionar un proyecto activo de otro usuario
   con la demo habilitada. Comprobar la solicitud desde la cuenta del autor.
8. Para calificaciones, seleccionar un contrato finalizado del que se sea participante.
9. Para incidencias, enviar un reporte y comprobar que aparezca en **Mis incidencias**.
   La resolución administrativa se prueba por el servicio correspondiente; no hay
   un panel de resolución implementado en React en esta entrega.

### Consideraciones al usar la cuenta de administrador

El rol administrador no reemplaza los requisitos del negocio:

- No permite abrir conversaciones privadas de contratos ajenos.
- No permite calificar contratos de otros participantes.
- El formulario para solicitar demos se muestra a clientes, no a administradores.
- Las funciones administrativas de incidencias existen en la API, mientras que
  la pantalla provisional sigue mostrando los reportes propios.

Por eso, entrar con `admin@zaas.com` no permite demostrar por sí solo todos los
recorridos de cliente y desarrollador. Para esas pruebas hacen falta las cuentas
correspondientes y sus contraseñas, proporcionadas por sus responsables.

`seed.py` aporta registros locales y no define contraseñas ni crea las cuentas
Firebase. No es necesario ejecutarlo para utilizar esta entrega. Volver a ejecutarlo
borra y recrea las tablas locales; no debe usarse para recuperar contraseñas.

## 9. Integración pendiente con los demás compañeros

Los eventos de comunicación incluidos ya generan notificaciones. Para avisos
originados en contratos, pagos o entregables, sus responsables deben llamar a
`crear_notificacion` dentro de la transacción de su operación.

Ejemplo de integración, una vez que el módulo de contratos haya preparado un objeto
`contrato` con participantes válidos:

```python
from app.comunicacion.services import crear_notificacion
from app.extensions import db

try:
    db.session.add(contrato)
    db.session.flush()
    crear_notificacion(
        contrato.id_desarrollador,
        f'Nuevo contrato #{contrato.id}',
        f'/comunicacion?tab=mensajes&contrato={contrato.id}',
    )
    db.session.commit()
except Exception:
    db.session.rollback()
    raise
```

El ejemplo ilustra la transacción; la autorización y la validación del contrato
corresponden al módulo que lo crea. La notificación no sustituye esas verificaciones.

| Módulo responsable | Integración pendiente |
|---|---|
| Contratos | Avisar de creación, aceptación o cierre y proporcionar contratos con participantes válidos. |
| Pagos | Avisar de pago recibido, liberación o resolución según sus reglas de negocio. |
| Entregables | Avisar de entrega, aprobación o rechazo. |
| Catálogo | Proporcionar proyectos reales con autor, estado y disponibilidad de demo. |
| Autenticación | Mantener sesiones válidas y asegurar la asignación de roles. |
| Administración | Consumir los servicios de incidencias y agregar las funciones de los demás módulos al panel futuro. |

Para invitar a calificar al cerrar un contrato, el módulo responsable puede enviar
un aviso a cada participante con `/comunicacion?tab=calificaciones&contrato=<id>`.
La evaluación sigue siendo una acción voluntaria de cada usuario; el cierre no
genera una puntuación automáticamente.

## 10. Límites y pendientes técnicos

1. **Panel administrativo:** pendiente por acuerdo del alcance. Los servicios de
   incidencias no equivalen a un panel completo ni a la administración de otros módulos.
2. **Tiempo real:** pendiente para una fase posterior. El chat actual requiere recarga.
3. **Eventos externos:** contratos, pagos y entregables todavía deben conectar
   sus propias llamadas a la función de notificaciones.
4. **Duplicados simultáneos:** las validaciones actuales rechazan repeticiones
   secuenciales. Para garantizar unicidad con solicitudes concurrentes se necesitan
   restricciones únicas mediante una migración coordinada con el equipo, después
   de revisar posibles duplicados existentes.
5. **Autenticación global:** esta entrega reutiliza el sistema actual. Continúan
   pendientes los problemas identificados en la revisión anterior sobre tokens sin
   verificar cuando Firebase falta, asignación de roles en el registro y cierre de
   sesión global. No se considera resuelto ese trabajo por agregar CSRF a esta API.
6. **Datos compartidos:** el módulo usa la persistencia local existente; no incorpora
   sincronización con Supabase ni notificaciones por correo o push.
7. **Pruebas integradas:** falta validar todos los recorridos con cuentas reales y
   los módulos terminados del resto del equipo. Las pruebas visuales con datos
   simulados no sustituyen esa comprobación.
8. **Diseño final:** las pantallas son provisionales y sirven para consumir y
   demostrar los servicios; pueden adaptarse al diseño definitivo del proyecto.

No se modificaron los modelos de contratos o pagos, no se incorporaron cobros reales
y no se alteraron cuentas, contraseñas o datos reales durante las pruebas automatizadas.

## 11. Actualización del 6 de noviembre: estilo compartido y panel provisional

Esta actualización sustituye los pendientes anteriores sobre la ausencia de pantalla
administrativa y las dos vías de acceso inseguro indicadas en el informe inicial.
El panel completo y la integración de los otros módulos siguen pendientes.

### Estilo y navegación

Jean actualizó el catálogo; sus cambios no incluían las pantallas de Comunicación.
Se adaptaron estas últimas a sus colores rojo, negro y gris, fondos claros, paneles
blancos y controles del catálogo. La mensajería sigue funcionando por recarga manual.

Se creó `frontend/src/components/AppNavbar.jsx`, reutilizado desde catálogo,
Comunicación y Administración. El enlace administrativo solo aparece cuando el
usuario local obtenido del backend tiene rol `admin`.

Se extrajo la consulta de recursos a `frontend/src/hooks/useComunicacionResource.js`.
El servicio frontend conserva el código HTTP de los errores para distinguir una
sesión ausente, un acceso denegado y un fallo recuperable del servidor.

### Panel provisional

Se agregaron `frontend/src/pages/AdminPage.jsx`, `frontend/src/pages/admin.css`
y la ruta protegida `/admin`. Contiene contadores reales de incidencias totales,
pendientes y resueltas/cerradas, además de los últimos cinco reportes.

Las tarjetas de Incidencias y Comunicación tienen acceso disponible. Las de Usuarios,
Catálogo, Contratos y Pagos aparecen pendientes de integración y sus controles están
deshabilitados. No presentan cifras inventadas.

La tarjeta de Incidencias permite consultar los reportes recientes en el propio
panel; la resolución completa se agregará en una etapa posterior. Comunicación
abre los recursos propios y no concede acceso a chats de otros participantes.

### Restricción de acceso

Se agregó `GET /api/comunicacion/admin/resumen` en `backend/app/comunicacion/api.py`.
Comprueba el rol persistido antes de consultar o devolver información: sin sesión
responde `401` y con otro rol responde `403`. La pantalla no muestra las tarjetas
administrativas cuando la API deniega el acceso, incluso entrando por URL.

En `backend/app/auth/routes.py` se eliminó la lectura de tokens sin firma cuando
Firebase no estaba disponible. También se limitó el registro público a `cliente`
y `desarrollador`, para evitar que un solicitante se asigne `admin`. Se validan los
cuerpos JSON y el tipo de token; el preflight OPTIONS del registro no crea usuarios.
Estos cambios no modifican los roles existentes ni crean cuentas o contraseñas.

### Comprobaciones agregadas

Se añadieron cinco pruebas del backend: denegación por rol/sesión, resumen real y
límite de cinco reportes, bloqueo de rol administrador en registro público, rechazo
de tokens sin verificar y acceso con identidades verificadas simuladas. Se reforzó
la prueba del cliente frontend para verificar que conserva el código `401`.
Las identidades de esas pruebas son temporales; no se usan contraseñas reales.

Resultado de esta actualización: 18 pruebas del backend y 4 del servicio frontend
aprobadas, compilación de React correcta y revisión de escritorio/móvil con datos
simulados. Se comprobó el menú por rol, el bloqueo para cliente/desarrollador, la
redirección sin sesión, la recuperación de errores y el resumen sin incidencias.

## 12. Corrección del registro y de la sincronización duplicada

Se corrigió el error `UNIQUE constraint failed: usuario.firebase_uid`, observado
cuando el formulario y el observador de Firebase sincronizaban la misma identidad
en paralelo. Ambos podían consultar que la cuenta aún no existía; una petición
confirmaba el alta y el INSERT de la otra chocaba con la restricción de SQLite.

En `backend/app/auth/routes.py`, `find_or_create_user` ahora captura el conflicto,
revierte la transacción fallida y busca el usuario por el UID verificado. Si otra
petición ya lo guardó, lo reutiliza. Si el conflicto no corresponde a ese UID,
se devuelve un error JSON controlado. No se eliminan registros ni restricciones.

Los reintentos de `/auth/registro/callback` reutilizan la cuenta y conservan su rol
existente. El rol solicitado solo se aplica al crear un usuario nuevo; el registro
público sigue rechazando administradores. No se cambia el rol de una cuenta
administradora o desarrolladora que ya estaba registrada.

Se creó `frontend/src/services/authBackend.js` para compartir una sola promesa
cuando el formulario y el observador envían simultáneamente el mismo token.
Las sincronizaciones de distintas identidades se procesan en orden para que una
respuesta antigua no reemplace la cookie de una cuenta que acaba de entrar.
Un fallo permite volver a intentar la sincronización.

`LoginPage.jsx` y `RegisterPage.jsx` usan ese servicio común y comprueban su respuesta
antes de navegar. En `authService.js` se reemplazó el inicio de sesión usado por
error para registrar usuarios por `createUserWithEmailAndPassword`, que sí crea
la cuenta en Firebase. `AuthContext.jsx` descarta respuestas antiguas al cambiar
de usuario y mantiene el estado de carga durante la sincronización.

Se agregaron seis pruebas en `backend/tests/test_auth_sync.py`, incluida una
reproducción de la restricción UNIQUE real después de simular una consulta desactualizada.
También se añadieron cuatro pruebas en `frontend/tests/authBackend.test.js` para
peticiones compartidas, reintentos, orden de cuentas y errores del servidor.
Resultado: 24 pruebas del backend y 8 del frontend aprobadas; React compila.
Las pruebas usan datos temporales e identidades simuladas, sin crear cuentas reales.

Para comprobar el bloqueo administrativo después de reiniciar el servidor y
recargar React, iniciar sesión como cliente y abrir `/admin`: debe aparecer el
mensaje de acceso restringido. Si la cuenta ya se creó en Firebase durante el
intento anterior, usar el inicio de sesión con ese correo y contraseña; no volver
a crearla ni ejecutar `seed.py`.
