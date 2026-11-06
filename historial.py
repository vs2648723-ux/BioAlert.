"""Historial: recupera de MySQL las consultas anteriores de un usuario."""
from flask import Blueprint, jsonify, request
from db import conectar

bp = Blueprint("historial", __name__)


@bp.get("/api/historial")
def historial():
    usuario = request.args.get("usuario", "").strip()
    if not usuario:
        return jsonify(error="Escribe tu nombre en el formulario para ver tu historial."), 400
    con = conectar()
    cur = con.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT c.id, c.creado_en, c.departamento, c.municipio, c.cultivo,
                   r.t_media, r.gda, r.hr_media, r.p_acum, r.riesgo
            FROM consultas c
            JOIN usuarios u ON u.id = c.usuario_id
            LEFT JOIN resultados_modelo r ON r.consulta_id = c.id
            WHERE u.nombre = %s
            ORDER BY c.id DESC
            LIMIT 20
        """, (usuario,))
        filas = cur.fetchall()
        for f in filas:
            f["creado_en"] = f["creado_en"].strftime("%Y-%m-%d %H:%M") if f["creado_en"] else None
        return jsonify(consultas=filas)
    finally:
        con.close()