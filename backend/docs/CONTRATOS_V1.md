# cambios en contratos

---

## Resumen

Esta versión implementa la plantilla base de contratos y corrige el flujo
backend del módulo:

- Cada contrato genera un documento con los nombres de ambas partes.
- El documento queda guardado como una copia inmutable de los términos.
- Cada parte acepta el contrato desde una página de revisión, con casilla de
  confirmación y botón.
- Se registra la firma (hash), la fecha, la hora y la IP.
- Se corrigieron permisos, validaciones, formularios y transiciones de estado.
- No se modificó el esquema de la base de datos.

---
- `borrador`: contrato recién creado, sin firmas.
- `pendiente`: una de las partes ya firmó.
- `aceptado`: ambas partes firmaron.
- `en_progreso`: el desarrollador ya subió al menos un entregable.
- `entregado`: el cliente aprobó los entregables y ya no hay pendientes.
- `finalizado`: el módulo de pagos liberó el escrow.
- `cancelado`: alguna de las partes canceló antes de finalizar.



## Archivos agregados

| Archivo | Descripción |
|---|---|
| `backend/app/contratos/plantillas.py` | Plantilla base v1.0, renderizado de marcadores y creación/actualización automática de la plantilla en la base. |
| `backend/app/templates/contratos/_documento.html` | Fragmento reutilizable que muestra el documento del contrato en el detalle y en la página de aceptación. |
| `backend/app/templates/contratos/aceptar.html` | Página de revisión y aceptación: documento completo, casilla de aceptación y botón de confirmación. |
| `backend/docs/CONTRATOS_V1.md` | Este documento. |

---

## Archivos modificados

| Archivo | Cambios |
|---|---|
| `backend/app/contratos/forms.py` | Se reemplazaron los campos de IDs por `SelectField`. Se agregaron `AceptacionForm`, `RevisionEntregableForm` y `ConfirmarForm`. Se agregó validación de costo y notas. |
| `backend/app/contratos/models.py` | Propiedades `nombre_cliente`, `nombre_desarrollador`, `objeto` y `firmas_completas`. |
| `backend/app/contratos/routes.py` | Validaciones, permisos, generación de términos, aceptación con checkbox, cancelación, entregables y revisión. |
| `backend/app/auth/models.py` | Propiedad `nombre_completo` en `Usuario`. |
| `backend/app/templates/contratos/form.html` | Formulario con selects de desarrollador, producto, oferta y plantilla; ya no pide IDs manuales. |
| `backend/app/templates/contratos/listar.html` | Nombres correctos de las partes, objeto del contrato, estado de firmas y estados. |
| `backend/app/templates/contratos/ver.html` | Documento, tabla de firmas, registro de aceptaciones, acciones y entregables con formularios CSRF. |
| `backend/app/templates/base.html` | Estilos del documento de contrato y estilos de impresión. |
| `backend/app/__init__.py` | Crea la plantilla base automáticamente al arrancar la aplicación. |
| `backend/seed.py` | Usa la plantilla base v1.0 al sembrar una base nueva. |
| `.gitignore` | Ignora `backend/keys/*.json` para no subir la llave real de Firebase. |
| `README.md` | Se agregó la sección “Contratos (v1.0)” y el enlace a este documento. |


## Funcionamiento de la plantilla

La plantilla está en:

```text
backend/app/contratos/plantillas.py
```

Contiene marcadores como:

```text
{{contrato_id}}
{{fecha}}
{{cliente_nombre}}
{{cliente_email}}
{{desarrollador_nombre}}
{{desarrollador_email}}
{{objeto}}
{{costo}}
{{notas_html}}
```

Al crear un contrato:

1. Se selecciona una plantilla en el formulario.
2. Se guarda el contrato en estado `borrador`.
3. Se reemplazan los marcadores con los datos reales.
4. El resultado se guarda en `contrato.terminos_condiciones`.

Esto significa que **si la plantilla se edita después, los contratos ya
creados conservan su versión original**.


## Rutas del módulo

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/contratos/` | Lista los contratos del usuario autenticado. |
| `GET` | `/contratos/nuevo` | Formulario para crear un contrato. |
| `POST` | `/contratos/nuevo` | Crea el contrato y genera los términos. |
| `GET` | `/contratos/<id>` | Detalle del contrato, firmas, entregables y pagos. |
| `GET` | `/contratos/<id>/aceptar` | Página de revisión y aceptación. |
| `POST` | `/contratos/<id>/aceptar` | Registra la firma de la parte autenticada. |
| `POST` | `/contratos/<id>/cancelar` | Cancela el contrato. |
| `GET` | `/contratos/<id>/entregable/nuevo` | Formulario para subir un entregable. |
| `POST` | `/contratos/<id>/entregable/nuevo` | Registra el entregable. |
| `POST` | `/contratos/entregable/<id>/revisar` | El cliente aprueba o rechaza un entregable. |

Todas las rutas requieren sesión iniciada con Flask-Login. La sesión se crea
desde el login de React mediante `/auth/callback`.