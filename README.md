# Zaas

Plataforma de servicios de desarrollo de software con escrow, contratos y mensajería.

## Estructura del proyecto

```
app/
  __init__.py          # create_app()
  extensions.py        # db, login_manager
  auth/                # Aya — usuarios, perfiles, login
  catalogo/            # Jean — proyectos, ofertas, postulaciones
  contratos/           # Sidrac — contratos, entregables, aceptaciones
  pagos/               # Daniel — pagos escrow, disputas, recibos
  comunicacion/        # Gael — mensajes, notificaciones, calificaciones, admin
  templates/
    base.html          # plantilla base con navbar
    auth/
    catalogo/
    contratos/
    pagos/
    comunicacion/
config.py
run.py
requirements.txt
```

## Instalación

```bash
# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Crear la base de datos y tablas
python seed.py

# Ejecutar
python run.py
```

## Ramas

- `main` — rama estable
- `develop` — rama de desarrollo (aquí van los commits)
- Una rama por persona para cada feature

## Roles

| Persona | Módulo | Tablas principales |
|---|---|---|
| Aya | auth | usuario, perfil |
| Jean | catalogo | proyecto, oferta_trabajo, postulacion, solicitud_demo |
| Sidrac | contratos | contrato, entregable, aceptacion, plantilla_contrato |
| Daniel | pagos | pago, liberacion, recibo, disputa, arbitraje |
| Gael | comunicacion | conversacion, mensaje, notificacion, calificacion, incidencia |
