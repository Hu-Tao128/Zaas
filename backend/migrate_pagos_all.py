"""Ejecuta en orden las migraciones del módulo de pagos.

Uso:
    python migrate_pagos_all.py
    python migrate_pagos_all.py --db sqlite:///ruta/a/copia.db

- Corre: migrate_pagos.py, migrate_pagos_realista.py, migrate_pagos_integridad.py
- Cada script es idempotente en sus operaciones seguras (create_all, columnas/índices
  con verificación o IF NOT EXISTS) y valida datos antes de aplicar restricciones.
- Nota: migrate_pagos_realista.py recrea la tabla `pago` para actualizar el CHECK de
  estado_escrow; no modifica filas de negocio, pero vuelve a ejecutar ese paso si se
  invoca nuevamente (operación repetible).
"""

from __future__ import annotations

import argparse
import os
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", dest="db", help="URI SQLAlchemy a usar (p. ej. sqlite:///copia.db)")
    args = parser.parse_args()

    if args.db:
        os.environ["DATABASE_URL"] = args.db

    base = os.path.dirname(os.path.abspath(__file__))
    if base not in sys.path:
        sys.path.insert(0, base)

    scripts = [
        ("migrate_pagos", "main"),
        ("migrate_pagos_realista", "main"),
        ("migrate_pagos_integridad", "main"),
    ]

    for module_name, func_name in scripts:
        print(f"==> Ejecutando {module_name}.{func_name}()")
        mod = __import__(module_name)
        func = getattr(mod, func_name)
        try:
            func()
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else 1
            if code != 0:
                print(f"Fallo en {module_name} (exit={code})")
                return code
        print(f"OK: {module_name}")

    print("Todas las migraciones de pagos se ejecutaron correctamente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
