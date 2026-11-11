# Changelog

Todas las versiones notables de ZaaS se documentan aquí.
El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/)
y el versionamiento semántico [SemVer](https://semver.org/lang/es/).

## [2.0.0] - 2026-11-09

### Added

- Modelo Relacional corregido en backend, frontend y Supabase:
  `habilidad`, `perfil_habilidad`, `tecnologia` y `perfil_tecnologia`.
- `contrato.id_plantilla`, `pago.metodo_pago`, `pago.transaccion_id`,
  `liberacion.id_entregable`, `recibo.total`, `disputa.id_pago`,
  `disputa.id_entregable`, `disputa.id_incidencia` e `incidencia.id_contrato`.
- API JSON de comunicación: notificaciones, conversaciones/mensajes,
  calificaciones e incidencias.
- Acciones de contrato en la API/React: subir y revisar entregables, liberar
  fondos, abrir/resolver disputas y calificar.
- Páginas React de notificaciones e incidencias, y chat dentro del contrato.
- Endpoint `POST /auth/firebase-login`: verifica Firebase y guarda directamente
  `usuario` y `perfil` en Supabase desde el backend con la `service_role` key.
- Script `backend/migrate_mr.py` para migrar bases SQLite existentes sin perder datos.
- Script `backend/supabase_setup.py` con verificación del MR y sincronización
  masiva de usuarios de Firebase.
- `VERSION`, `CHANGELOG.md` y actualización automática de versión en `scripts/release.sh`.

### Changed

- `perfil` dejó de usar `habilidades`/`stack_tecnologico` como texto; ahora se
  normalizan en tablas intermedias.
- El perfil público y el editor de perfil consumen listas de habilidades y tecnologías.
- `seed.py` crea habilidades, tecnologías y sus relaciones.
- El detalle de contrato muestra plantilla, pagos, recibos, liberaciones, disputas,
  entregables y mensajes.
- La navegación incorpora Notificaciones e Incidencias.

### Breaking Changes

- El esquema de base de datos cambia: es necesario ejecutar
  `python backend/migrate_mr.py` (base existente) o `python backend/seed.py`
  (base nueva).
- `POST /contratos/api/crear` ahora exige exactamente un producto o una oferta.
- Los clientes que enviaban `perfil.habilidades`/`perfil.stack_tecnologico` como
  texto deben enviar `habilidades` y `tecnologias` como listas.

## [1.0.0]

- Versión inicial de producción.
