# Cambios realizados en el proyecto

> Documento generado a partir de los cambios aplicados durante la sesión de trabajo sobre el módulo de pagos y ajustes relacionados.
> **Nota:** el árbol de trabajo puede contener otros cambios previos o paralelos; este documento resume los cambios implementados en esta sesión.

## 1. Visibilidad y acceso al módulo de pagos (frontend)

### Navegación y rutas

- **`frontend/src/App.jsx`**: verificación/uso de rutas existentes para pagos y disputas (`/contratos/:id/pagos`, `/disputas`).
- **`frontend/src/components/Navbar.jsx`**: acceso a **Disputas** desde la navegación.
- **`frontend/src/pages/contratos/ContratoDetalle.jsx`**:
  - Se agregó/reemplazó el acceso principal por **“Pagos y garantía”** hacia `/contratos/:id/pagos`.
  - El acceso se muestra mientras el contrato no esté `finalizado` ni `cancelado` (para evitar que aparezca una vez completado el proceso).
  - Se retiró el botón de liberación rápida del detalle para no mezclar la gestión del depósito con la liberación (la liberación se gestiona desde el apartado de pagos).

### Configuración

- **`frontend/vite.config.js`**: proxy de `/pagos/api` hacia el backend (verificado/configurado según el flujo del módulo).

## 2. Experiencia de pagos orientada a producción (frontend)

### Página de pagos por contrato

- **`frontend/src/pages/pagos/PagosContratoPage.jsx`**
  - Se eliminaron elementos de “modo demostración” en la UI: banner/ayuda y botón/listado de **“Ver tarjetas de prueba”**.
  - Textos actualizados a flujo de garantía (escrow): “Pagos y garantía del contrato”, “Depositar fondos en garantía”, mensajes de procesamiento/confirmación más neutros.
  - Formulario de depósito sin etiquetas/placeholders de prueba; aviso de que los datos sensibles del medio de pago no se almacenan en la plataforma.
  - El detalle de cada pago muestra el **método** en lugar de marca/últimos dígitos de tarjeta.
  - Estados de pago presentados con etiquetas más claras (ej. “Retenido en garantía”, “No completado”).
  - Campos de monto (depósito y liberación): `type="text"` con `inputMode="decimal"`, restricción de entrada numérica (hasta 2 decimales), validación de formato y de monto > 0 antes de enviar.

### Disputas

- **`frontend/src/pages/pagos/DisputasPage.jsx`**
  - Ajustes en campos numéricos donde aplica (ej. porcentaje para desarrollador en división: entrada numérica controlada en rango 0–100) para evitar controles de incremento por scroll y mejorar validación.

### Formularios relacionados (montos)

- **`frontend/src/pages/contratos/ContratoForm.jsx`**: costo acordado con entrada de texto numérica (`decimal`, hasta 2 decimales) y validación de formato/monto > 0.
- **`frontend/src/pages/catalogo/ProyectoFormPage.jsx`**: precio con entrada de texto numérica validada.
- **`frontend/src/pages/catalogo/OfertaFormPage.jsx`**: presupuesto (opcional) con validación numérica si se captura.

### Cliente API de pagos

- **`frontend/src/services/pagosApi.js`**: mantenimiento del cliente para consumo de `/pagos/api` (CSRF, cabeceras como `Idempotency-Key`, manejo de errores/respuestas) acorde a los cambios del flujo.

## 3. Notificaciones y conexión entre partes

- **`backend/app/catalogo/api.py`** (`POST /api/catalogo/proyectos/<id>/demo`)
  - Al solicitar información/demostración de un proyecto, se notifica al **desarrollador autor** del proyecto (asunto, mensaje con solicitante/proyecto y enlace al proyecto).
  - Mensaje de éxito orientado al usuario: “Solicitud enviada al desarrollador.”
- **`backend/app/catalogo/routes.py`** (`solicitar_demo`)
  - Notificación equivalente al desarrollador en el flujo HTML.
- **`backend/app/contratos/api.py`** (`/contratos/api/crear`)
  - Al crear un contrato, se notifica al **desarrollador** para revisar términos y continuar el proceso (enlace al contrato).
  - Mensaje de éxito ajustado para reflejar la notificación.

## 4. Privacidad de datos de pago

- **`backend/app/pagos/services.py`**: los nuevos registros de pago no persisten `marca_tarjeta` ni `ultimos4` (se guardan como `NULL`).
- **`backend/app/pagos/api.py`**: las respuestas de pago no exponen `marca_tarjeta` ni `ultimos4`.
- **Vistas legacy**:
  - `backend/app/templates/pagos/pagar.html`: textos y formulario alineados a “Depositar fondos en garantía”, sin listado de tarjetas de prueba y con aviso de no almacenamiento de datos sensibles; campo de monto como texto numérico.
  - `backend/app/templates/pagos/pago_detalle.html`: se omite la visualización de marca/últimos dígitos; se muestra el método de pago.
  - `backend/app/templates/pagos/liberar.html`: monto a liberar como texto numérico con validación de formato.
- **Documentación de apoyo (desarrollo)**:
  - **`docs/tarjetas-prueba-pagos.md`** (nuevo): tarjetas de prueba, resultados esperados, código de verificación y referencias técnicas (uso exclusivo en desarrollo/pruebas).

## 5. Auditoría y refactor del backend del módulo de pagos

### Auditoría (Paso 0)

Se realizó auditoría con evidencia sobre: alias `service.py`/`services.py`, rutas y plantillas legacy, responsabilidades de `api.py`, máquina de estados, tarjetas de prueba, confirmación HMAC/timestamp/idempotencia, tope de pagos, idempotencia, liberaciones, disputas, arbitrajes, expiración, recibos, restricciones en BD, uso de columnas de tarjeta y ausencia de logging de datos sensibles en el módulo. Se identificaron incumplimientos/parcialidades (transiciones no centralizadas, tope sin filtrar estados vigentes, bypass de reglas en rutas legacy, arbitraje/reparto y transaccionalidad, expiración no central, restricciones/validaciones incompletas, etc.) y se propuso plan priorizado aprobado.

### Fuente de verdad y arquitectura

- **`backend/app/pagos/services.py`** (reescritura/refactor): concentra las reglas de negocio del módulo (pagos, confirmación/verificación/expiración, recibos, liberaciones, disputas, arbitrajes). Las capas API y rutas legacy actúan como adaptadores.
- **`backend/app/pagos/api.py`**: adaptador JSON; delega en servicios y traduce errores de dominio a respuestas con `codigo` y `mensaje` preservando campos existentes (`ok`, `mensaje`, `errores`, datos).
- **`backend/app/pagos/routes.py`**: rutas HTML legacy adaptadas para usar servicios y respetar reglas (sin mutaciones directas de lógica crítica de arbitraje/disputa como antes; sin finalizar contrato desde el módulo de pagos).
- **`backend/app/pagos/errors.py`** (nuevo): jerarquía de errores de dominio con `codigo`, `mensaje`, `status_code` y `errores`; compatibilidad con `ValueError`/`PermissionError` donde aplica.
- **`backend/app/pagos/models.py`**: se agrega `intentos_verificacion` en `Pago` (aditivo, default 0) para verificación en BD.
- **`backend/app/pagos/service.py`**: se conserva como alias de compatibilidad.

### Máquina de estados

- **Pago:** `pendiente → retenido|fallido`, `retenido → liberado|reembolsado|dividido`; estados finales `fallido`, `liberado`, `reembolsado`, `dividido`.
- **Disputa:** `abierta → en_revision|resuelta|cerrada`, `en_revision → resuelta|cerrada`; finales `resuelta`, `cerrada`.
- Transiciones validadas centralmente en servicios (rechazo de transiciones inválidas).

### Reglas de negocio implementadas/ajustadas

- **Registro de pagos:** solo cliente del contrato; contrato en `aceptado|en_progreso|entregado`; monto > 0; tope contra `costo_acordado` considerando solo pagos vigentes (`retenido`, `liberado`, `dividido`, `pendiente` no vencido) y excluyendo `fallido`, `reembolsado` y `pendiente` vencido; idempotencia por clave con validación de consistencia; tarjetas de prueba cerradas y rechazo de números no admitidos sin persistir/registrar datos sensibles.
- **Confirmación inmediata opcional:** variable `PAGOS_CONFIRMACION_INMEDIATA` (default conserva comportamiento asíncrono actual). Con tarjeta aprobada y flag activo, el pago pasa a `retenido` en la misma petición usando las mismas funciones de confirmación/recibo.
- **Confirmación (webhook simulado):** validación de firma HMAC y marca de tiempo (ventana máxima 5 minutos), comparación en tiempo constante e idempotencia; endpoint protegido por firma/timestamp (exención CSRF cuando aplica).
- **Verificación:** código de prueba `123456`; contador de intentos en BD (`intentos_verificacion`); 3 intentos fallidos → `fallido` con `codigo_fallo = verificacion_fallida`.
- **Expiración:** pendientes que superan `PAGOS_EXPIRACION_MINUTOS` pasan a `fallido` con `codigo_fallo = expirado`; comprobación central aplicada en consulta/confirmación/verificación y cálculos de vigencia.
- **Recibos:** generación idempotente al pasar a `retenido`, folio único y `total = monto`.
- **Liberaciones:** cliente (o admin) sobre pago `retenido`; entregable del mismo contrato y aprobado si se indica; bloqueo si hay disputa abierta/en revisión; monto > 0 y suma ≤ saldo; control con bloqueo/`FOR UPDATE`; liberación parcial mantiene `retenido`, total pasa a `liberado`. El módulo de pagos no modifica estado de contrato/entregable/incidencia.
- **Disputas:** apertura por partes del contrato (no cerrado), origen único (contrato/pago/entregable), pertenencia al contrato, incidencia escalable una sola vez, una sola disputa abierta por origen; toma por admin con asignación de `id_admin` y paso a `en_revision`.
- **Arbitrajes:** solo admin, una sola vez por disputa, transacción atómica con rollback ante fallo de reembolso simulado.
  - `liberar`: libera saldo no liberado al desarrollador.
  - `reembolsar`: reembolsa saldo no liberado y registra `reembolso_id`/`fecha_reembolso`.
  - `dividir`: porcentaje 0–100 obligatorio, reparto con `Decimal` y redondeo explícito a centavos garantizando que las partes suman exactamente el saldo; libera parte del desarrollador y reembolsa parte del cliente.
  - Aplica a pago origen o, si no hay, a pagos retenidos del contrato (cada uno procesado según corresponda). TODO documentado para afinamiento de política en casos complejos.

### Integridad en base de datos y migración

- **`backend/migrate_pagos_integridad.py`** (nueva, aditiva e idempotente):
  - Agrega `pago.intentos_verificacion` si falta.
  - Valida datos existentes (montos, estados, origen de disputas, porcentajes, duplicados de recibos/arbitrajes/incidencias, disputas abiertas duplicadas por origen). Si hay incumplimientos, hace rollback y falla con listado claro de filas/casos afectados.
  - Crea/verifica índices únicos y parciales requeridos (incl. prevención de múltiples disputas abiertas por mismo origen, cuando el motor lo soporta).
  - **Downgrade:** elimina índices creados por la migración y conserva columnas para evitar pérdida de datos.

## 6. Códigos de error de dominio (API de pagos)

La API agrega `codigo` a las respuestas de error manteniendo `ok`, `mensaje` y `errores` (compatibilidad con clientes existentes). Códigos principales:

| Código                        | Significado                                            | HTTP típico |
| ----------------------------- | ------------------------------------------------------ | ----------- |
| `pago_error`                  | Error base de dominio.                                 | 400         |
| `validacion_invalida`         | Solicitud o datos no válidos.                          | 400/422     |
| `permiso_denegado`            | Sin permiso para la acción.                            | 403         |
| `no_autenticado`              | Sesión no iniciada.                                    | 401         |
| `pago_no_encontrado`          | Pago no encontrado.                                    | 404         |
| `contrato_no_encontrado`      | Contrato no encontrado.                                | 404         |
| `contrato_no_apto`            | Contrato no admite pagos en su estado actual.          | 409         |
| `contrato_cerrado`            | Contrato cerrado para la operación solicitada.         | 409         |
| `monto_invalido`              | Monto inválido.                                        | 400         |
| `tope_contrato_superado`      | Pagos vigentes superan el costo acordado.              | 400/409     |
| `tarjeta_no_admitida`         | Medio de pago no admitido/válido.                      | 422         |
| `idempotencia_conflicto`      | Clave de idempotencia reutilizada con datos distintos. | 409         |
| `transicion_pago_invalida`    | Transición de estado de pago no permitida.             | 409         |
| `pago_no_retenido`            | No hay fondos retenidos disponibles.                   | 409         |
| `saldo_insuficiente`          | Monto supera el saldo disponible.                      | 400/409     |
| `entregable_invalido`         | Entregable no válido para la operación.                | 400/409     |
| `disputa_activa`              | Existe disputa activa que impide la operación.         | 409         |
| `disputa_no_encontrada`       | Disputa no encontrada.                                 | 404         |
| `disputa_origen_invalido`     | Origen de disputa inválido.                            | 400/409     |
| `disputa_duplicada`           | Ya existe disputa abierta para el origen.              | 409         |
| `incidencia_ya_escalada`      | Incidencia ya vinculada a una disputa.                 | 409         |
| `transicion_disputa_invalida` | Transición de estado de disputa no permitida.          | 409         |
| `arbitraje_invalido`          | Decisión/estado de arbitraje inválido.                 | 409/422     |
| `arbitraje_duplicado`         | La disputa ya tiene arbitraje.                         | 409         |
| `reembolso_fallido`           | Falló el reembolso simulado.                           | 409         |
| `confirmacion_invalida`       | Confirmación de pago inválida.                         | 400         |
| `verificacion_invalida`       | Verificación de pago inválida/fallida.                 | 400         |
| `pago_no_pendiente`           | El pago no está pendiente.                             | 409         |
| `pago_expirado`               | El pago expiró.                                        | 409         |
| `recurso_no_encontrado`       | Recurso no encontrado.                                 | 404         |
| `error_interno`               | Error inesperado (sin detalles técnicos al cliente).   | 500         |

## 7. Compatibilidad y consideraciones importantes

- **Endpoint heredado de contratos:** `POST /contratos/api/<id>/liberar` debe seguir delegando en servicios de pagos y manteniendo su comportamiento esperado (incluida la finalización del contrato según la lógica del módulo de contratos).
- **Rutas y formatos existentes:** se preservaron rutas y estructuras de respuesta principales; se agregaron campos (`codigo` en errores) sin eliminar los ya consumidos.
- **Sin proveedores reales:** el procesamiento de pagos y reembolsos es simulado.
- **Sin almacenamiento/registro de datos sensibles de tarjeta:** no se guardan PAN/CVC/vencimiento ni marca/últimos dígitos en nuevos flujos; no se agregaron logs de datos de tarjeta en el módulo de pagos.
- **Esquema aditivo:** columnas históricas como `marca_tarjeta`/`ultimos4` pueden permanecer en BD por compatibilidad, pero no se utilizan en los nuevos registros ni se exponen.

## 8. Verificación realizada (resumen)

- **Compilación backend (módulo pagos y migración):** `python -m compileall app/pagos migrate_pagos_integridad.py` → OK.
- **Migración de integridad:** `python migrate_pagos_integridad.py` → completada en el entorno utilizado; validaciones incluidas para detectar incumplimientos y abortar con listado de filas/casos afectados.
- **Pruebas existentes de pagos:** `python -m unittest tests.test_pagos` → **17 tests, OK**.
- **Descubrimiento en `tests/`:** `python -m unittest discover -s tests -p "test*.py"` → **17 tests, OK** (según contenido disponible).
- **Validación de detección de incumplimientos (simulada):** verificación de consulta de duplicidad de disputas abiertas por mismo origen detectó correctamente el caso de ejemplo.

## 9. Archivos principales modificados/creados (sesión)

### Backend

- `backend/app/pagos/api.py` (modificado)
- `backend/app/pagos/services.py` (modificado)
- `backend/app/pagos/models.py` (modificado)
- `backend/app/pagos/routes.py` (modificado)
- `backend/app/pagos/errors.py` (creado)
- `backend/app/contratos/api.py` (modificado, integración/notificación y ajustes relacionados)
- `backend/app/catalogo/api.py` (modificado, notificación en solicitud de demo)
- `backend/app/catalogo/routes.py` (modificado, notificación en solicitud de demo)
- `backend/migrate_pagos_integridad.py` (creado)
- `backend/migrate_pagos.py`, `backend/migrate_pagos_realista.py` (presentes/modificados según estado del árbol de trabajo)
- `backend/app/templates/pagos/pagar.html` (modificado)
- `backend/app/templates/pagos/pago_detalle.html` (modificado/creado en el árbol según estado)
- `backend/app/templates/pagos/liberar.html` (modificado/creado en el árbol según estado)

### Frontend

- `frontend/src/pages/pagos/PagosContratoPage.jsx` (modificado)
- `frontend/src/pages/pagos/DisputasPage.jsx` (modificado)
- `frontend/src/services/pagosApi.js` (modificado)
- `frontend/src/pages/contratos/ContratoDetalle.jsx` (modificado)
- `frontend/src/pages/contratos/ContratoForm.jsx` (modificado)
- `frontend/src/pages/catalogo/ProyectoFormPage.jsx` (modificado)
- `frontend/src/pages/catalogo/OfertaFormPage.jsx` (modificado)
- `frontend/src/components/Navbar.jsx` (modificado)
- `frontend/src/App.jsx` (ajustes de rutas/flujo según estado)
- `frontend/vite.config.js` (proxy de pagos API)

### Documentación

- `docs/tarjetas-prueba-pagos.md` (creado)
- `CAMBIOS_REALIZADOS.md` (este documento)

## 10. Supuestos, pendientes y recomendaciones

- **Pruebas adicionales:** ampliar cobertura automatizada para todos los casos solicitados (transiciones inválidas exhaustivas, confirmación con firma/timestamp válidos-inválidos-vencidos, expiración en todos los accesos, concurrencia estricta, arbitraje con fallo de reembolso y rollback completo, usuarios ajenos en todos los endpoints, compatibilidad del endpoint heredado de contratos, verificación de no exposición/logging de datos sensibles) en el entorno de CI/suite del proyecto.
- **Índices parciales:** la prevención en BD de “una disputa abierta por origen” usa índices parciales; validar compatibilidad con el motor de base de datos objetivo en producción.
- **Idempotencia por usuario:** reforzada a nivel de servicio; la unicidad global de `idempotency_key` en esquema actual puede requerir ajuste futuro si se desea clave compuesta estricta en BD.
- **Expiración programada:** actualmente garantizada en puntos centrales de acceso/operación; evaluar tarea programada si se requiere actualización proactiva sin consultas.
- **Despliegue:** reiniciar backend/frontend tras cambios, aplicar migraciones pendientes (`migrate_pagos.py`, `migrate_pagos_realista.py`, `migrate_pagos_integridad.py` según corresponda) y limpiar caché del navegador (`Ctrl+F5`) para reflejar cambios en UI.

## 11. Actualización (continuación aprobada: A–H, fases backend y frontend pagos/garantía)

Fecha de actualización: 14/11/2026 (sesión de continuación).

### 11.1 Decisiones aplicadas
- **A. Aceptación de contrato sin depósito automático (`backend/app/contratos/api.py`, excepción autorizada):**
  - `aceptar_contrato` ya no llama a `_depositar_escrow`. La aceptación solo registra la firma y el estado (`aceptado` si firmas completas, `pendiente` si falta la otra parte).
  - Mensajes: `"Contrato aceptado por ambas partes."` / `"Tu aceptación fue registrada. Falta la firma de la otra parte."`
  - `acciones.puede_depositar_escrow` informativo por rol/estado (`cliente` y contrato en `aceptado|en_progreso|entregado`).
  - Llamadores verificados (`git grep`): `backend/app/contratos/api.py:613` define `_depositar_escrow` (sin invocaciones activas), `:614` invoca `pagos.services.depositar_escrow` dentro de esa definición; `backend/app/pagos/services.py:1009` define `depositar_escrow`. No quedan llamadores externos/activos; **no se borraron** las funciones de depósito en servicios. Pagos históricos creados por depósito automático no se migran/borra y se tratan como “Depósito de demostración” en UI.
  - No se modificaron pruebas existentes para cambiar lo que comprueban (la suite completa sigue pasando).
- **B. Contrato y botones (`frontend/src/pages/contratos/ContratoDetalle.jsx`):**
  - Botón **“Aceptar contrato”**.
  - **“Depositar fondos”** (a `/contratos/:id/pagos`) solo si cliente, contrato en `aceptado|en_progreso|entregado` y queda monto por depositar (según resumen). Si contrato en `pendiente`, se muestra **“Falta la firma del desarrollador para poder depositar.”** No se muestran botones que el backend rechace.
  - Panel lateral usa **resumen de pagos** (`/pagos/api/contrato/<id>/resumen`), no `contrato.escrow` para importes. **No se modificó `_escrow`**.
- **C. Resumen aditivo en pagos (solo lectura, `Decimal`, cadenas decimales):**
  - `GET /pagos/api/contrato/<id>/resumen` (mismos permisos de lectura que listado): `depositado` (retenido/liberado/dividido), `en_custodia` (Σ por pago retenido de `monto - liberado de ese pago`), `liberado` (Σ liberaciones del contrato), `por_depositar` (`costo_acordado - vigentes[retenido,liberado,dividido,pendiente vigente]`, mín. 0), `costo_acordado`, `moneda`.
  - Pagos en respuestas incluyen `liberado` y `disponible` (`monto - liberado`) como cadenas; importes monetarios serializados como cadenas.
- **D. Recibo:** modal con vista estructurada (folio, fecha, monto, proyecto, cliente, desarrollador, concepto). `contenido_html` no se renderiza crudo; si se muestra, va en `iframe` con `sandbox=""` (sin scripts).
- **E. Errores:** `PagoApiError` conserva `codigo`, `status`, `errores`. `mensajeError` (UI) mapea por `codigo` y `codigo_fallo` con mensajes claros.
- **F. Disputas:** `DisputasPage.jsx` usa selectores con descripciones legibles y **origen único** (depósito o entregable según tipo), sin IDs internos visibles; etiquetas legibles para tipo/estado/decisión.
- **G. Endpoint heredado `/contratos/api/<id>/liberar` (comportamiento confirmado):**
  - Libera **saldo pendiente** del pago (`monto - lo ya liberado`), no `pago.monto`.
  - Finaliza contrato **solo** si no queda dinero en custodia en ningún pago y lo liberado alcanza `costo_acordado`; si no, responde sin finalizar con mensaje claro.
  - Pruebas añadidas para ambos casos.
- **H.** Cálculos monetarios nuevos en backend usan `Decimal` (sin `float`).

### 11.2 Archivos modificados/creados en esta continuación
**Backend**
- `backend/app/contratos/api.py` — aceptar sin depósito, mensajes, flag; liberar saldo pendiente y finalización segura con `Decimal`.
- `backend/app/pagos/services.py` — `obtener_resumen_contrato` con `Decimal`/cadenas.
- `backend/app/pagos/api.py` — endpoint resumen, `liberado`/`disponible` y montos como cadenas en pagos, `_money_str`.
- `backend/tests/test_pagos_pendientes.py` — `HeredadoLiberarComportamientoTests` (2 casos).

**Frontend**
- `frontend/src/pages/contratos/ContratoDetalle.jsx` — botones/mensajes, panel con resumen, limpieza de IDs/técnicos en secciones de pagos/disputas.
- `frontend/src/pages/pagos/PagosContratoPage.jsx` — resumen, modales depósito/liberación, recibo modal estructurado (iframe sandbox), roles, `mensajeError`, sin IDs/códigos crudos.
- `frontend/src/pages/pagos/DisputasPage.jsx` — selectores legibles/origen único, etiquetas, `mensajeError`, sin IDs internos.
- `frontend/src/pages/pagos/pagosUtils.js` — **nuevo**: etiquetas y `mensajeError` por `codigo`/`codigo_fallo`, helpers de monto.
- `frontend/src/services/pagosApi.js` — `PagoApiError` preserva `codigo/status/errores`, `resumenContrato`, manejo de errores/red/CSRF.

### 11.3 Verificación
- **Backend (dir. `backend/`):** `.\env\Scripts\python.exe -m unittest tests.test_pagos_pendientes.HeredadoLiberarComportamientoTests` → **2 tests, OK**. `.\env\Scripts\python.exe -m unittest discover -s tests -p "test*.py"` → **Ran 36 tests, OK** (`RC=0`).
- **Frontend (dir. `frontend/`):** `npm run build` → **OK** (`vite v5.4.21`, `✓ built`, `RC=0`; warning de chunk >500 kB preexistente/no bloqueante).
- **Capturas 1366×768:** no generadas en este entorno CLI (sin navegador/GUI). Pendiente validación visual manual en 1366×768 y 1920×1080 (roles, estados de contrato, depósitos parcial/completo/múltiples/rechazado/verificación, liberaciones parcial/total, disputa abierta, textos largos, backend caído/sesión vencida, doble clic).

### 11.4 Notas
- `_escrow` no modificado; reglas/estados/modelos de pagos preservados.
- `depositar_escrow` permanece definido en servicios sin llamadores activos (por instrucción).
- Árbol de trabajo con cambios previos/no separados y archivos no seguidos adicionales; conviene revisar antes de commit.

## 12. Contratos: contratación contextual, plantillas por tipo y descarga en PDF

> Actualización aplicada únicamente sobre el área de contratos. El flujo descrito en este apartado se suma a lo documentado en las secciones anteriores; no reemplaza ni elimina los cambios previos.

### 12.1 Objetivo de la actualización

- Evitar que un contrato se cree “desde cero”: todo contrato debe nacer de un **proyecto del catálogo** o de una **oferta con postulación aceptada**, de modo que cliente, desarrollador, objeto y costo queden determinados por el contexto real.
- Quitar del módulo de contratos los accesos genéricos de creación (incluido el botón **“Nuevo contrato”** del panel y el estado vacío con “Crear mi primer contrato”).
- Permitir que las **partes involucradas** descarguen el contrato en **PDF** antes y después de firmarlo, sin importar el estado (`borrador`, `pendiente`, `aceptado`, `en_progreso`, `entregado`, `finalizado` o `cancelado`).
- Que la **plantilla legal cambie según el tipo de contrato**: desarrollo a medida, licencia de uso del software, compra del código fuente y soporte/mantenimiento.
- Conservar intacto el comportamiento de la versión 1.0: copia inmutable de la plantilla, aceptación mediante checkbox/botón, registro de fecha, hora, IP y folio (hash), permisos por rol y protección CSRF.

### 12.2 Flujo completo de contratación contextual

1. **Entrada desde el catálogo**
   - En el detalle de un proyecto se conserva la acción **“Contratar con Escrow”**, que enlaza a `/contratos/nuevo` con los parámetros `id_producto`, `id_desarrollador` y el costo de referencia.
   - En el detalle de una postulación aceptada se conserva la acción **“Contratar a este desarrollador”**, que enlaza con `id_encargo`, `id_cliente`, `id_desarrollador` y `costo_acordado`.
   - El frontend solo aporta contexto; el backend **no confía** en esos identificadores y los vuelve a resolver.

2. **Apertura de `/contratos/nuevo`**
   - La pantalla solo funciona con **exactamente uno** de `id_producto` o `id_encargo`.
   - Si no llega ninguno, llegan ambos o la URL se abre directamente sin contexto, el formulario **redirige a `/contratos`** con un mensaje explicativo (“Para crear un contrato, elige un proyecto o una oferta desde el catálogo”).
   - Al montar, el formulario consulta `GET /contratos/api/opciones?id_producto=…` o `GET /contratos/api/opciones?id_encargo=…`.

3. **Formulario contextual (`ContratoForm.jsx`)**
   - Ya **no** muestra selects de desarrollador, proyecto ni oferta.
   - Muestra en modo lectura: cliente autenticado, desarrollador, proyecto/oferta y costo sugerido.
   - Campos editables: **costo acordado**, **tipo de contrato** y **notas** (máximo 2000 caracteres).
   - La vista lateral resume el objeto, el tipo de contrato elegido y el monto.
   - El tipo de contrato se preselecciona según el contexto:
     - Proyecto/SaaS del catálogo → **Licencia de uso del software**.
     - Oferta/encargo con postulación aceptada → **Desarrollo de software a medida**.
     - El usuario puede cambiarlo antes de crear el contrato.

4. **Creación (`POST /contratos/api/crear`)**
   - Solo disponible para usuarios con rol **`cliente`**.
   - El backend resuelve el contexto y **deriva el desarrollador** del proyecto o de la postulación aceptada; cualquier `id_desarrollador` enviado por el navegador se ignora y se sobrescribe con el valor resuelto.
   - El cliente es siempre el usuario autenticado.
   - Al crear, se renderiza la plantilla seleccionada y el resultado se guarda como **copia inmutable** en `contrato.terminos_condiciones`.
   - La respuesta devuelve el contrato creado y el frontend navega al detalle.

5. **Firma y aceptación (sin cambios respecto a v1.0)**
   - Cada parte firma desde el detalle con checkbox de aceptación y botón de confirmación.
   - Se registra fecha/hora, dirección IP y folio de verificación (hash), además del registro de aceptaciones.
   - Los permisos se mantienen: solo las partes pueden firmar/operar; el administrador puede consultar; usuarios ajenos reciben `403`.

### 12.3 Reglas y validaciones del backend

- **Contexto obligatorio y único:** debe llegar `id_producto` **o** `id_encargo`, nunca ambos ni ninguno. Si la combinación es inválida, responde `400` con mensaje y error asociado al campo.
- **Proyecto/producto:**
  - Debe existir y estar en estado `activo`.
  - Debe pertenecer a un usuario con `tipo_usuario = 'desarrollador'`.
  - No se permite crear un contrato contra uno mismo.
- **Oferta/encargo:**
  - Debe existir y pertenecer al cliente autenticado.
  - Debe tener una **postulación en estado `aceptada`**.
  - El desarrollador de esa postulación debe ser válido y distinto del cliente.
  - El costo sugerido es el de la postulación aceptada (`costo_propuesto`), con el presupuesto de la oferta como respaldo.
- **Costo:** numérico, mayor a cero y con hasta dos decimales.
- **Plantilla:** debe existir y pertenecer a uno de los tipos disponibles.
- **Notas:** texto opcional, máximo 2000 caracteres; se escapa antes de convertirse en HTML.
- **CSRF y sesión:** se mantienen las protecciones existentes; sin sesión se responde `401` y sin permisos `403`.
- **Seguridad:** el cliente nunca puede inyectar un desarrollador, un cliente ni un objeto arbitrario; todo se deduce del producto/oferta y del usuario autenticado.

### 12.4 Tipos de contrato y plantillas legales

Las plantillas siguen viviendo en la tabla `plantilla_contrato` (sin cambio de esquema) y ahora existen cuatro plantillas base:

| Tipo (clave) | Etiqueta visible | Uso previsto | Plantilla |
|---|---|---|---|
| `desarrollo` | Desarrollo de software a medida | Encargos con entregables y cesión de derechos al liberar el pago | `Contrato de Desarrollo de Software a Medida v1.0` |
| `licencia_software` | Licencia de uso del software | Venta del derecho de uso de un SaaS/software sin transferir el código | `Contrato de Licencia de Uso de Software v1.0` |
| `compra_codigo` | Compra del código fuente | Transferencia del código, documentación y derechos patrimoniales | `Contrato de Compraventa de Código Fuente v1.0` |
| `soporte_mantenimiento` | Soporte y mantenimiento | Servicios recurrentes de soporte, corrección de errores y actualizaciones | `Contrato de Soporte y Mantenimiento v1.0` |

- Cada plantilla tiene cláusulas propias (objeto, alcance, restricciones, propiedad intelectual, confidencialidad, garantías, vigencia, cancelación, disputas y aceptación digital).
- `ensure_plantillas()` es **idempotente**: crea las plantillas faltantes al arrancar la aplicación y al ejecutar `seed.py`, sin sobrescribir plantillas personalizadas existentes.
- **Migración sin cambio de esquema:** la plantilla histórica `Contrato de Servicios Profesionales v1.0` se renombra a la plantilla de desarrollo; los contratos ya creados conservan su propio texto en `terminos_condiciones`.
- Los contratos existentes **no cambian** si después se edita una plantilla: el documento guardado es la fuente de verdad.
- La API expone el tipo y la etiqueta de cada plantilla (`tipo`, `etiqueta`, `descripcion`) en `/opciones` y en el detalle del contrato.
- El listado de contratos y el detalle muestran el **tipo de contrato** en lugar del nombre técnico de la plantilla.

### 12.5 Descarga del contrato en PDF

- **Endpoint:** `GET /contratos/api/<id>/pdf`.
- **Permisos:** cliente, desarrollador y administrador. Cualquier otro usuario recibe `403`; sin sesión, `401`.
- **Estados:** disponible en **cualquier estado**, incluidos `pendiente`, `cancelado` y `finalizado`, antes y después de la firma.
- **Generación:** se realiza en el servidor con **WeasyPrint** a partir de:
  - La copia inmutable de los términos (`contrato.terminos_condiciones`).
  - El resumen del acuerdo: cliente, desarrollador, tipo de contrato, objeto, costo, fecha de creación, estado del contrato y estado de Escrow.
  - El **registro de firmas** con nombre, estado y folio de verificación.
  - El **registro de aceptaciones digitales** con usuario, fecha/hora e IP.
  - Aviso de que el documento refleja el estado al momento de la descarga y que la versión vinculante es la copia guardada por Zaas.
- **Contratos antiguos:** si un contrato no tiene `terminos_condiciones`, el endpoint lo genera con su plantilla (o la plantilla base) antes de construir el PDF.
- **Respuesta:** `application/pdf` con `Content-Disposition: attachment; filename="contrato-<id>.pdf"` y `Cache-Control: private, no-store`.
- **UI:** botón **“Descargar PDF”** en el encabezado del detalle, visible para las partes y administradores, junto a “Imprimir documento”. También se añadió el enlace en la vista legacy `backend/app/templates/contratos/ver.html`.
- **Servicio frontend:** `contratosApi.pdfUrl(id)` construye la URL de descarga para usarla en un enlace del mismo origen (la sesión y las cookies se envían automáticamente).

### 12.6 Limpieza de accesos genéricos

- Se eliminó el botón **“Nuevo contrato”** del panel/listado de contratos.
- Se eliminó el acceso **“Crear mi primer contrato”** del estado vacío.
- El estado vacío ahora explica que los contratos se crean desde el catálogo (proyecto con “Contratar con Escrow” o postulación aceptada) y ofrece un enlace para explorar el catálogo.
- La ruta `/contratos/nuevo` sigue existiendo, pero **solo** como formulario contextual; sin contexto redirige al listado.
- No se modificaron otras áreas del producto.

### 12.7 Archivos modificados y creados

**Backend**
- `backend/app/contratos/api.py` — `/opciones` y `/crear` contextuales; resolución y validación del proyecto/oferta; serialización del tipo de plantilla; endpoint `GET /<id>/pdf`; generación del documento para contratos antiguos.
- `backend/app/contratos/plantillas.py` — cuatro plantillas legales, metadatos de tipo (`info_plantilla`), siembra idempotente (`ensure_plantillas`) y migración del nombre histórico.
- `backend/app/contratos/pdf.py` — **nuevo**: construcción del PDF con WeasyPrint, resumen, documento, firmas y aceptaciones.
- `backend/app/contratos/routes.py` — compatibilidad con la siembra de todas las plantillas en el flujo Flask heredado.
- `backend/app/__init__.py` — al arrancar se aseguran todas las plantillas base.
- `backend/seed.py` — usa `ensure_plantillas()` en lugar de crear una sola plantilla.
- `backend/requirements.txt` — agrega `weasyprint==70.0`.
- `backend/app/templates/contratos/ver.html` — enlace de descarga en la vista heredada.
- `backend/tests/test_contratos_contexto.py` — **nuevo**: creación contextual, validaciones y permisos.
- `backend/tests/test_contratos_pdf_tipos.py` — **nuevo**: cuatro tipos de plantilla, PDF en todos los estados, contratos antiguos y accesos denegados.

**Frontend**
- `frontend/src/pages/contratos/ContratoForm.jsx` — formulario contextual sin selects de desarrollador/proyecto, partes y objeto de solo lectura, selector de **tipo de contrato** con descripción y tipo sugerido según el contexto.
- `frontend/src/pages/contratos/ContratosList.jsx` — eliminación de accesos genéricos de creación y visualización del tipo de contrato.
- `frontend/src/pages/contratos/ContratoDetalle.jsx` — botón **“Descargar PDF”**, tipo de contrato visible y conservación de firma/impresión.
- `frontend/src/pages/contratos/contratos.css` — estilos del grupo de acciones del encabezado.
- `frontend/src/services/contratosApi.js` — `opciones` contextual y `pdfUrl`.
- `frontend/src/pages/catalogo/catalogoUtils.js` — referencia de las URLs de contratación desde proyecto y postulación; sin cambios en esta actualización.

### 12.8 Verificación realizada

- **Backend:** `python -m unittest discover -s backend/tests -q` → **56 tests, OK**.
  - Incluye los nuevos casos de contratación contextual, los cuatro tipos de contrato, descarga PDF en `pendiente`/`cancelado`/`finalizado`/`borrador`, generación para contratos antiguos, rechazo a terceros y exigencia de sesión.
- **Frontend:** `npm run build` → **OK** (`vite v5.4.21`, `✓ built`). Se mantiene únicamente el warning preexistente de chunk mayor a 500 kB.
- **Comprobación manual del PDF:** se generó un contrato de prueba tipo licencia y se validó con `pdftotext` que el contenido incluye el tipo, las partes, las cláusulas de licencia, las firmas y el registro de aceptaciones.
- **Calidad:** `python -m py_compile` sobre los módulos modificados y `git diff --check` sin errores.

### 12.9 Dependencia y despliegue

- Instalar la nueva dependencia:
  ```bash
  pip install -r backend/requirements.txt
  ```
- WeasyPrint requiere las bibliotecas de sistema de Pango/Cairo (en Debian/Ubuntu: `libpango-1.0-0`, `libpangoft2-1.0-0`, `libcairo2`, `libgdk-pixbuf-2.0-0` y fuentes como `fonts-dejavu`). En el entorno local ya están presentes y el PDF se generó correctamente.
- Reiniciar el backend después de instalar la dependencia.
- No se requiere migración de esquema: al arrancar, `ensure_plantillas()` agrega las plantillas nuevas a bases existentes y conserva los contratos ya creados.

### 12.10 Notas de compatibilidad

- Se conserva el comportamiento v1.0: snapshot de plantilla, checkbox y botón de aceptación, registro de fecha/hora/IP/folio, permisos por rol y CSRF.
- Las plantillas son texto con reemplazo de marcadores; no se evalúan como código, por lo que las notas del usuario no pueden ejecutar nada.
- El flujo Flask con plantillas HTML de contratos sigue presente como compatibilidad, pero la interfaz activa es la de React bajo `/contratos/*`.
- Los cambios de esta actualización quedaron **sin commit** en la rama `sidrac`.


## 13. Contratos: rechazo con motivo y monto negociable

### 13.1 Objetivo

- Permitir que el desarrollador rechace un contrato creado por el cliente indicando el motivo.
- Ocultar los contratos rechazados de los menús de ambas partes y notificar al cliente.
- Permitir que el desarrollador decida si el monto es negociable. Si no lo es, el cliente no puede modificarlo; si lo es, el cliente puede enviar una oferta y la interfaz muestra “Oferta” en lugar de “Monto acordado”.

> El detalle de disputas ya forma parte de la integración de `develop`; esta actualización no modifica esa área.

### 13.2 Modelo y migración

- `Contrato`: `notas`, `monto_negociable`, `rechazado`, `motivo_rechazo`, `fecha_rechazo`, `id_rechazado_por`, relación `rechazado_por` y propiedad `estado_visible` (`rechazado` cuando aplica).
- `Proyecto`: `precio_negociable`.
- `Postulacion`: `costo_negociable`.
- `backend/migrate_mr.py`: agrega las columnas con `DEFAULT FALSE` y tipos compatibles con SQLite/PostgreSQL.

### 13.3 Backend

- `/contratos/api/crear` deduce la negociabilidad del producto o de la postulación aceptada; si el monto es fijo, ignora el costo enviado por el navegador y usa el sugerido. Guarda el snapshot en `monto_negociable` y las notas en `notas`.
- `POST /contratos/api/<id>/rechazar`: solo el desarrollador, antes de su firma, con motivo obligatorio (10–1000 caracteres). Marca `rechazado`, guarda motivo/fecha/autor, pasa el contrato a `cancelado` y notifica al cliente.
- `POST /contratos/api/<id>/negociacion`: el desarrollador activa/desactiva la negociación antes de firmar y notifica al cliente cuando cambia.
- `POST /contratos/api/<id>/oferta`: el cliente propone un nuevo monto solo si `monto_negociable` es verdadero, no hay firmas y el contrato sigue en `borrador`/`pendiente`. Regenera el documento y notifica al desarrollador.
- El listado de contratos (API y flujo Flask heredado) filtra `rechazado=False`.
- Serialización con `estado_visible`, datos del rechazo y `monto_negociable`; acciones `puede_rechazar`, `puede_definir_negociacion` y `puede_ofertar`.
- PDF: estado “Rechazado”, motivo/fecha y etiqueta “Oferta” vs “Costo acordado”.
- Catálogo: formularios y respuestas JSON incluyen `precio_negociable` y `costo_negociable`; el flujo Flask heredado también los guarda.
- `GET /api/catalogo/proyectos/<id>` incluye `contrato_activo` (`id` y estado) para el cliente autenticado, de modo que la UI no vuelva a ofrecer la contratación.
- Creación de contratos: pre-validación del contrato activo por cliente+producto (o cliente+oferta) e interceptación de `IntegrityError`; ambos casos responden **409** con mensaje claro en lugar de **500**. El flujo Flask heredado aplica la misma validación sobre el formulario.

### 13.4 Frontend

- `ContratoForm.jsx`: si es fijo, el costo queda bloqueado; si es negociable, el campo se llama “Tu oferta (MXN)”.
- `ContratoDetalle.jsx`: banner de rechazo, control de negociación, formulario de rechazo, formulario de oferta del cliente y etiquetas correctas del monto.
- `ContratoUI.jsx` y `ContratosList.jsx`: estado visual “Rechazado”.
- `ProyectoFormPage.jsx` y `PostularPage.jsx`: casillas “Precio negociable” y “Costo negociable”; los detalles muestran la condición.
- `contratosApi.js`: métodos `rechazar`, `actualizarNegociacion` y `enviarOferta`.
- `DetalleProyectoPage.jsx`: si el cliente ya tiene un contrato activo para el proyecto, muestra el aviso “Ya tienes un contrato registrado para este proyecto” con enlace al contrato, en lugar del botón “Contratar con Escrow”.

### 13.5 Verificación

- `python -m unittest discover -s tests -q` desde `backend/` → **108 tests, OK** (19 en `test_contratos_rechazo_negociacion.py`).
- `npm run build` → **OK**; solo se mantiene el warning preexistente de chunk > 500 kB.
- Migración comprobada en SQLite: las columnas booleanas con `DEFAULT FALSE` se agregan y toman valor `0` en filas existentes.

### 13.6 Corrección del error 500 al crear contratos

- **Síntoma:** crear un contrato desde el área de cliente funcionaba con algunos proyectos (p. ej. Carlos Aya) y devolvía 500 con otros (Ana García, Luis Martínez).
- **Causa:** el índice único `uq_contrato_cliente_producto_activo` (`WHERE estado <> 'cancelado'`) impide más de un contrato activo por cliente y producto. El usuario de prueba ya tenía contratos `pendiente` para los proyectos de Ana y Luis, pero no para el de Carlos Aya; el `INSERT` lanzaba `UNIQUE constraint failed: contrato.id_cliente, contrato.id_producto` y se propagaba como 500.
- **Solución:** validar el duplicado antes de insertar y capturar `IntegrityError` como respaldo (carreras entre peticiones), devolviendo 409 con un mensaje que invita a revisar o cancelar el contrato existente. El detalle del proyecto informa `contrato_activo` y la UI reemplaza el botón de contratación por un aviso con enlace.
- Los contratos en estado `cancelado` (incluidos los rechazados, que pasan a `cancelado`) no bloquean la creación de uno nuevo.
- Pruebas añadidas: `test_contrato_duplicado_devuelve_409_no_500`, `test_contrato_duplicado_tras_cancelar_funciona` y `test_detalle_proyecto_informa_contrato_activo`.


## 14. Ejecución con Docker Compose

Fecha de actualización: 22/11/2026.

### 14.1 Objetivo

- Permitir levantar el proyecto completo en otra máquina sin instalar Python, Node ni dependencias del sistema.
- Mantener el backend Flask, el frontend React y la base de datos en contenedores separados, con persistencia y proxy de API.

### 14.2 Archivos creados

- `docker-compose.yml` (raíz): servicios `backend` y `frontend`, volumen `zaas_db`, healthcheck y puertos configurables.
- `backend/Dockerfile`: imagen `python:3.12-slim` con las bibliotecas de Pango/Cairo/DejaVu que requiere WeasyPrint y Gunicorn como servidor.
- `backend/docker-entrypoint.sh`: ejecuta `migrate_mr.py` de forma idempotente y arranca Gunicorn (1 worker y 4 hilos por defecto para SQLite).
- `backend/.dockerignore`: excluye `.env`, `instance/`, llaves, pruebas y cachés de la imagen.
- `frontend/Dockerfile`: compilación multi-etapa con Node 20 + pnpm 9 y servidor `nginx:1.27-alpine`.
- `frontend/nginx.conf`: sirve la SPA con fallback a `index.html` y hace proxy de `/api`, `/auth`, `/contratos/api` y `/pagos/api` hacia `backend:5000`.
- `frontend/.dockerignore`: excluye `node_modules`, `dist` y `pnpm-workspace.yaml` (usa opciones de pnpm 12, incompatible con la imagen de pnpm 9).
- `.env.example` (raíz): puertos, `SECRET_KEY`, `DATABASE_URL`, Supabase, ruta de la llave de Firebase y ajustes de Gunicorn.
- `DOCKER.md`: guía de preparación, ejecución, persistencia, PostgreSQL y solución de problemas.
- `README.md`: sección breve de inicio con Docker.

### 14.3 Funcionamiento

- El frontend se sirve en `http://localhost:8080` y el backend en `http://localhost:5000` (ambos configurables en `.env`).
- La SPA usa rutas relativas, por lo que nginx funciona como mismo origen y las cookies de sesión/CSRF viajan sin problemas de CORS.
- La base SQLite se guarda en el volumen nombrado `zaas_db`; se puede cambiar a `./backend/instance/zaas.db` o a PostgreSQL editando `docker-compose.yml`.
- La llave de Firebase Admin se monta desde `./backend/keys` en modo de solo lectura; la configuración web de Firebase se toma de `frontend/.env` al compilar.
- En una base nueva, `migrate_mr.py` crea las 27 tablas y aplica las columnas de contratos, pagos y disputas. Los usuarios se crean al iniciar sesión con Firebase.

### 14.4 Verificación

- `docker compose config` → configuración válida.
- `docker compose build backend` y `docker compose build frontend` → imágenes construidas correctamente.
- `docker compose up -d` → backend en estado **healthy** y frontend iniciado.
- Smoke test a través de nginx:
  - `GET /` y `GET /contratos/1` → **200** (`text/html`, fallback de la SPA).
  - `GET /contratos/api/csrf`, `GET /api/catalogo/proyectos` y `GET /pagos/api/csrf` → **200**.
  - Assets JS servidos con `application/javascript`.
- WeasyPrint dentro del contenedor generó un PDF de prueba correctamente.
- Esquema verificado en el volumen: columnas `monto_negociable`, `rechazado`, `motivo_rechazo`, `fecha_rechazo`, `id_rechazado_por`, `notas`, `proyecto.precio_negociable` y `postulacion.costo_negociable` presentes.

### 14.5 Notas

- No se ejecuta `seed.py` en Docker: la versión actual del archivo contiene referencias a variables de una mezcla anterior (`cliente1`, `dev1`, `disputa`, etc.) y falla. El login de Firebase crea los usuarios locales automáticamente.
- Cambiar `frontend/.env` requiere reconstruir la imagen (`docker compose up -d --build frontend`) porque Vite inserta esos valores en tiempo de compilación.
- La ruta heredada `/auth/login` (plantilla Flask) responde 500 en esta versión; la SPA usa `/login` y `/auth/firebase-login`, que sí funcionan.
