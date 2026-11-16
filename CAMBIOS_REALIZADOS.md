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
