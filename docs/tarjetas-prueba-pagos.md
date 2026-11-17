# Tarjetas de prueba — módulo de pagos (entorno de desarrollo)

> **Uso exclusivo en desarrollo/pruebas.** No utilizar en producción. Estas tarjetas solo funcionan con el proveedor de pago simulado del proyecto.

## Tarjetas disponibles

| Número de tarjeta       | Resultado esperado                         | Notas |
|-------------------------|--------------------------------------------|-------|
| `4242 4242 4242 4242`   | Aprobada                                   | El pago pasa a estado retenido en garantía (escrow) tras la confirmación. |
| `4000 0000 0000 0002`   | Rechazada (`tarjeta_rechazada`)            | La tarjeta es rechazada por el proveedor simulado. |
| `4000 0000 0000 9995`   | Rechazada (`fondos_insuficientes`)         | Simula fondos insuficientes. |
| `4000 0000 0000 3220`   | Requiere verificación                      | Usar código de verificación: `123456` (máximo 3 intentos). |

## Datos de formulario sugeridos

- **Vencimiento:** cualquier fecha futura en formato `MM/AA` (ej. `12/30`)
- **CVC:** cualquier 3 dígitos (ej. `123`)
- **Moneda:** MXN (según configuración del contrato)

## Comportamiento relevante

- Los pagos inician en estado **pendiente** y se confirman de forma asíncrona (según `PAGOS_CONFIRM_DELAY`).
- Los pagos pendientes expiran tras `PAGOS_EXPIRACION_MINUTOS` (por defecto 15 minutos).
- La verificación adicional usa el código `123456` para la tarjeta que lo requiere.

## Ubicación en código (referencia técnica)

- Proveedor simulado: `backend/app/pagos/services.py`
- API de pagos: `backend/app/pagos/api.py`
- UI de pagos por contrato: `frontend/src/pages/pagos/PagosContratoPage.jsx`
