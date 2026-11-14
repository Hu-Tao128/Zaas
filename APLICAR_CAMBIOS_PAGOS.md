# Guía para aplicar los cambios realizados (Pagos y garantía)

Este documento describe los pasos recomendados para aplicar en un entorno local, de pruebas o despliegue los cambios realizados en el módulo de pagos/escrow, contratos y frontend.

> **Importante:** no se ejecuta ningún commit/push automáticamente. Revisa y selecciona los archivos que correspondan antes de versionar o desplegar. El árbol de trabajo puede contener cambios previos o no relacionados.

## 1. Requisitos y consideraciones previas

- **Respaldo:** realiza respaldo de la base de datos y del código/configuración antes de aplicar cambios.
- **Entorno Python (backend):** usar el entorno virtual del proyecto (ej. `backend\env\Scripts\python.exe` en Windows) con dependencias instaladas.
- **Entorno Node (frontend):** Node/npm disponibles y dependencias instaladas (`npm install` en `frontend/` si es necesario).
- **Base de datos:** configuración en `backend/config.py` / variables de entorno (`DATABASE_URL`). Por defecto se usa SQLite (`sqlite:///zaas.db`). Si el entorno objetivo es PostgreSQL, validar compatibilidad y ejecutar migraciones/pruebas en ese motor antes de desplegar.
- **Sin proveedores reales:** los pagos siguen siendo simulados (tarjetas de prueba en `docs/tarjetas-prueba-pagos.md`).
- **Cambios de comportamiento relevantes:**
  - **Aceptar contrato** ya no deposita fondos automáticamente en escrow; solo registra la aceptación/firma y el estado (`aceptado` o `pendiente`). El fondeo se realiza mediante el flujo de depósito en garantía.
  - **Endpoint heredado** `POST /contratos/api/<id>/liberar`: libera el **saldo pendiente** del pago (`monto - lo ya liberado`) y **finaliza el contrato solo** si no queda dinero en custodia en ningún pago y lo liberado alcanza el costo acordado; en caso contrario responde sin finalizar con mensaje claro.
  - **Resumen de fondos:** nuevo endpoint de solo lectura `GET /pagos/api/contrato/<id>/resumen` (mismos permisos que listado de pagos).

## 2. Aplicar cambios de backend

### 2.1 Actualizar código
Asegúrate de tener en el entorno los archivos modificados/creados del backend, incluyendo (según corresponda al alcance):
- `backend/app/contratos/api.py`
- `backend/app/pagos/api.py`, `services.py`, `models.py`, `routes.py`, `errors.py`
- `backend/app/templates/pagos/*` (vistas legacy)
- `backend/migrate_pagos.py`, `backend/migrate_pagos_realista.py`, `backend/migrate_pagos_integridad.py`, `backend/migrate_pagos_all.py`
- `backend/tests/*` (si se incluyen pruebas)

> Limpieza aplicada en módulo pagos: se eliminó `backend/app/pagos/service.py` (alias sin usos). No se eliminó `pagos.services.depositar_escrow` ni el helper en contratos, aunque no tengan llamadores activos.

### 2.2 Migraciones de base de datos (pagos)
Ejecutar en orden desde el directorio `backend/` (con el intérprete/entorno correcto):

```bash
# Opción recomendada: ejecutar todas en orden e idempotente
python migrate_pagos_all.py
```

O de forma individual, en este orden:
```bash
python migrate_pagos.py
python migrate_pagos_realista.py
python migrate_pagos_integridad.py
```

Notas:
- `migrate_pagos_realista.py` recrea la tabla `pago` solo si el `CHECK` de `estado_escrow` no está actualizado (re-ejecuciones idempotentes en ese caso).
- `migrate_pagos_integridad.py` es aditiva (columnas/validaciones/índices, p. ej. `intentos_verificacion` e índices parciales para disputa abierta por origen). Puede **abortar con listado** si detecta datos que incumplen las restricciones; corregir datos antes de reintentar.
- Verificar que el motor de BD soporte las características usadas (p. ej. índices parciales en SQLite 3.45+ / PostgreSQL). Validar en el motor objetivo.

### 2.3 Variables de entorno (opcional/revisar)
Valores por defecto preservados; ajustar solo si es necesario:
- `PAGOS_CONFIRMACION_INMEDIATA` (por defecto asíncrono)
- `PAGOS_CONFIRM_DELAY`
- `PAGOS_EXPIRACION_MINUTOS` (por defecto 15)
- `PAGOS_WEBHOOK_SECRET`
- `PAGOS_TEST_MODE` / entorno de pruebas (afecta simulaciones como `FAILRF` solo en modo test)

### 2.4 Reiniciar backend
Reiniciar el servidor Flask/backend para cargar cambios de código y modelos.

## 3. Aplicar cambios de frontend

### 3.1 Actualizar código
Asegúrate de incluir, según alcance:
- `frontend/src/pages/contratos/ContratoDetalle.jsx`
- `frontend/src/pages/pagos/PagosContratoPage.jsx`, `DisputasPage.jsx`, `pagosUtils.js`
- `frontend/src/services/pagosApi.js`
- Otros ajustes de UI/rutas/proxy ya presentes en el árbol (`Navbar.jsx`, `vite.config.js`, etc.) si forman parte del despliegue.

### 3.2 Construir para producción
Desde `frontend/`:
```bash
npm install   # si faltan dependencias
npm run build
```
Verificar que el build finalice correctamente (salida en `dist/` según configuración de Vite).

### 3.3 Despliegue/servicio y caché
- Publicar/servir el contenido generado (`dist/`) según la infraestructura del proyecto.
- En desarrollo, reiniciar `npm run dev` si aplica.
- **Limpiar caché del navegador** (`Ctrl+F5`) para asegurar que se carguen los cambios de UI.

## 4. Verificación recomendada

### 4.1 Pruebas automatizadas (backend)
Desde `backend/` con el entorno del proyecto:
```bash
python -m unittest tests.test_pagos_pendientes.HeredadoLiberarComportamientoTests
python -m unittest discover -s tests -p "test*.py"
```
Resultado esperado en el entorno validado: suite de pagos/pruebas disponibles en verde (ej. 36 tests OK en la sesión de cambios).

### 4.2 Compilación/build
- Backend: `python -m compileall app/pagos app/contratos` (opcional, verificación rápida).
- Frontend: `npm run build` sin errores.

### 4.3 Validación funcional manual (recomendada)
Validar en escritorio **1366×768** y **1920×1080**:
- **Roles:** cliente, desarrollador, admin (permisos y acciones visibles/ocultas correctamente).
- **Contrato:** `pendiente` muestra “Falta la firma del desarrollador para poder depositar”; tras firmas completas pasa a `aceptado` sin depósito automático; depósito disponible en `aceptado/en_progreso/entregado` solo si hay monto por depositar.
- **Depósitos:** sin/parcial/completo, múltiples depósitos, pago rechazado, verificación pendiente/código, prevención de doble clic/envíos duplicados.
- **Liberaciones:** parcial y total, múltiples depósitos, saldo disponible correcto; contrato finaliza solo cuando no hay custodia y lo liberado alcanza el costo acordado (incluye comportamiento heredado de liberación).
- **Disputas:** apertura con origen único (depósito/entregable) y descripciones legibles; disputa abierta/en revisión; arbitraje admin según reglas.
- **Errores/estados:** mensajes claros por `codigo`/`codigo_fallo`, sin IDs técnicos crudos en UI, recibo estructurado (sin HTML crudo ejecutable), textos largos, backend caído, sesión vencida.
- **Datos sensibles:** no se almacenan ni exponen datos de tarjeta.

## 5. Notas adicionales
- `_escrow` en `backend/app/contratos/api.py` no se modificó; el panel/UI consume el resumen de pagos.
- No se cambiaron reglas/estados/modelos de negocio de pagos fuera de lo indicado; rutas y formatos de respuesta se preservaron de forma aditiva (`codigo` en errores, campos `liberado`/`disponible`, endpoint de resumen).
- Revisar `CAMBIOS_REALIZADOS.md` y `docs/tarjetas-prueba-pagos.md` para detalle de cambios y tarjetas de prueba.
- Si el despliegue es a producción, planificar ventana de mantenimiento para migraciones y reinicios, y contar con rollback (respaldo de BD y versión anterior).
