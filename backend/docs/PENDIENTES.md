# Pendientes técnicos

## Contratos: tres errores `NameError` de `Decimal`

La línea base de la suite del backend (19 de noviembre de 2026) detectó tres
errores preexistentes al probar el endpoint heredado de liberar fondos en
`app/contratos/api.py`. En los tres casos, `liberar_fondos` usa `Decimal` sin
tenerlo definido en ese módulo. Se mantienen pendientes y fuera del alcance de
los cambios de disputas.

Pruebas afectadas:

- `test_endpoint_heredado_liberar`
- `test_finaliza_si_no_queda_custodia_y_liberado_alcanza_costo`
- `test_no_finaliza_si_queda_dinero_en_custodia`

La suite final conserva estos mismos tres errores y no presenta fallos nuevos.
