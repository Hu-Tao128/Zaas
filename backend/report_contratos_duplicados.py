"""Reporte de SOLO LECTURA de contratos activos duplicados.

Uso:
    python backend/report_contratos_duplicados.py

- No modifica datos ni esquema.
- Lista grupos que incumplen unicidad (cliente+proyecto y oferta/encargo),
  incluyendo id, estado, fecha, número de pagos, estado de cada pago,
  dinero retenido, y si tiene disputas, incidencias o entregables.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from sqlalchemy import text


def _mappings(rows):
    return [dict(r) for r in rows]


def reporte_contrato(cid):
    c = db.session.execute(
        text(
            "SELECT id, estado, fecha_creacion, id_cliente, id_producto, id_encargo, costo_acordado "
            "FROM contrato WHERE id=:id"
        ),
        {"id": cid},
    ).mappings().first()
    pagos = _mappings(db.session.execute(
        text("SELECT id, estado_escrow, monto FROM pago WHERE id_contrato=:id ORDER BY id"),
        {"id": cid},
    ).mappings().all())

    retenido = 0.0
    pagos_info = []
    for p in pagos:
        libs = db.session.execute(
            text("SELECT COALESCE(SUM(monto_liberado),0) as s FROM liberacion WHERE id_pago=:id"),
            {"id": p["id"]},
        ).mappings().first()["s"]
        lib = float(libs or 0)
        monto = float(p["monto"] or 0)
        if p["estado_escrow"] == "retenido":
            retenido += max(monto - lib, 0.0)
        pagos_info.append({
            "id": p["id"],
            "estado_escrow": p["estado_escrow"],
            "monto": round(monto, 2),
            "liberado": round(lib, 2),
        })

    disputas = db.session.execute(
        text(
            "SELECT COUNT(*) n, "
            "SUM(CASE WHEN estado IN ('abierta','en_revision') THEN 1 ELSE 0 END) abiertas "
            "FROM disputa WHERE id_contrato=:id"
        ),
        {"id": cid},
    ).mappings().first()
    incidencias = db.session.execute(
        text("SELECT COUNT(*) n FROM incidencia WHERE id_contrato=:id"),
        {"id": cid},
    ).mappings().first()
    entregables = db.session.execute(
        text("SELECT COUNT(*) n FROM entregable WHERE id_contrato=:id"),
        {"id": cid},
    ).mappings().first()

    return {
        "id": c["id"],
        "estado": c["estado"],
        "fecha": str(c["fecha_creacion"]),
        "id_cliente": c["id_cliente"],
        "id_producto": c["id_producto"],
        "id_encargo": c["id_encargo"],
        "costo_acordado": round(float(c["costo_acordado"] or 0), 2),
        "num_pagos": len(pagos),
        "pagos": pagos_info,
        "dinero_retenido": round(retenido, 2),
        "disputas_total": int(disputas["n"] or 0),
        "disputas_abiertas": int(disputas["abiertas"] or 0),
        "incidencias": int(incidencias["n"] or 0),
        "entregables": int(entregables["n"] or 0),
    }


def main():
    app = create_app()
    with app.app_context():
        dup_prod = _mappings(db.session.execute(text(
            """
            SELECT id_cliente, id_producto
            FROM contrato
            WHERE id_producto IS NOT NULL AND (estado IS NULL OR estado <> 'cancelado')
            GROUP BY id_cliente, id_producto
            HAVING COUNT(*) > 1
            ORDER BY id_cliente, id_producto
            """
        )).mappings().all())
        dup_enc = _mappings(db.session.execute(text(
            """
            SELECT id_encargo
            FROM contrato
            WHERE id_encargo IS NOT NULL AND (estado IS NULL OR estado <> 'cancelado')
            GROUP BY id_encargo
            HAVING COUNT(*) > 1
            ORDER BY id_encargo
            """
        )).mappings().all())

        print("REPORTE SOLO LECTURA - CONTRATOS ACTIVOS DUPLICADOS")
        print("(No se realizaron modificaciones)\n")

        print("=== GRUPOS DUPLICADOS: mismo cliente y producto (estado <> cancelado) ===")
        if not dup_prod:
            print("(ninguno)")
        for g in dup_prod:
            rows = _mappings(db.session.execute(text(
                """
                SELECT id FROM contrato
                WHERE id_cliente=:c AND id_producto=:p AND (estado IS NULL OR estado <> 'cancelado')
                ORDER BY id
                """
            ), {"c": g["id_cliente"], "p": g["id_producto"]}).mappings().all())
            ids = [r["id"] for r in rows]
            print(f"\nGRUPO cliente={g['id_cliente']} producto={g['id_producto']} cantidad={len(ids)} ids={ids}")
            for r in rows:
                print(json.dumps(reporte_contrato(r["id"]), ensure_ascii=False, sort_keys=True))

        print("\n=== GRUPOS DUPLICADOS: misma oferta/encargo (estado <> cancelado) ===")
        if not dup_enc:
            print("(ninguno)")
        for g in dup_enc:
            rows = _mappings(db.session.execute(text(
                """
                SELECT id FROM contrato
                WHERE id_encargo=:e AND (estado IS NULL OR estado <> 'cancelado')
                ORDER BY id
                """
            ), {"e": g["id_encargo"]}).mappings().all())
            ids = [r["id"] for r in rows]
            print(f"\nGRUPO encargo={g['id_encargo']} cantidad={len(ids)} ids={ids}")
            for r in rows:
                print(json.dumps(reporte_contrato(r["id"]), ensure_ascii=False, sort_keys=True))

        print("\nRESUMEN")
        print(f"grupos_cliente_producto={len(dup_prod)} grupos_encargo={len(dup_enc)}")


if __name__ == "__main__":
    main()
