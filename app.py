from concurrent.futures import ThreadPoolExecutor
from flask import Flask, render_template, request, jsonify
from db import conectar
from config import DATASETS
import ideam, modelo, conocimiento
from explicacion import explicar
from historial import bp as historial_bp

app = Flask(__name__)
app.register_blueprint(historial_bp)

def bajar(variable, dep, mun):
    try:
        return variable, ideam.descargar_diario(variable, dep, mun), None
    except Exception as e:
        return variable, [], str(e)


@app.get("/")
def inicio():
    return render_template("index.html")


@app.post("/api/consulta")
def consulta():
    d = request.get_json(force=True)
    nombre, dep, mun, cultivo = (d.get(k, "").strip() for k in ("usuario", "departamento", "municipio", "cultivo"))
    if not all([nombre, dep, mun, cultivo]):
        return jsonify(error="Completa nombre, departamento, municipio y cultivo."), 400
    if ideam.normalizar(cultivo) not in ("MAIZ", "MAIZ AMARILLO", "MAIZ BLANCO"):
        return jsonify(error="Por ahora BioAlert solo analiza maíz."), 400

    con = conectar(); cur = con.cursor(dictionary=True)
    try:
        cur.execute("INSERT INTO usuarios (nombre) VALUES (%s) ON DUPLICATE KEY UPDATE nombre=nombre", (nombre,))
        cur.execute("SELECT id FROM usuarios WHERE nombre=%s", (nombre,)); uid = cur.fetchone()["id"]
        cur.execute("INSERT INTO consultas (usuario_id, departamento, municipio, cultivo) VALUES (%s,%s,%s,%s)",
                    (uid, dep, mun, cultivo)); cid = cur.lastrowid

        # Descarga de las 6 variables al mismo tiempo
        with ThreadPoolExecutor(max_workers=len(DATASETS)) as pool:
            resultados = list(pool.map(lambda v: bajar(v, dep, mun), DATASETS))

        avisos = []
        for variable, filas, error in resultados:
            if error:
                avisos.append(f"No se pudo descargar {variable}: {error}")
            elif filas:
                ideam.guardar_clima(cur, variable, filas, dep, mun)
            else:
                avisos.append(f"Sin datos de {variable} para {mun}.")
        con.commit()

        res = modelo.calcular(cur, ideam.normalizar(dep), ideam.normalizar(mun))
        if not res:
            return jsonify(error="El IDEAM no tiene datos para ese municipio. Prueba con otro cercano.", avisos=avisos), 404
        cur.execute("""INSERT INTO resultados_modelo (consulta_id, fecha_desde, fecha_hasta, n_dias, t_media, gda, hr_media, p_acum, riesgo)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (cid, res["desde"], res["hasta"], res["n_dias"], res["t_media"], res["gda"], res["hr_media"], res["p_acum"], res["riesgo"]))
        con.commit()

        explicacion = explicar(res)
        explicacion["puntos"].insert(1, res["calidad"]["punto"])   # "Calidad de los datos" después del periodo
        return jsonify(res | {"avisos": avisos, "explicacion": explicacion})
    finally:
        con.close()


@app.post("/api/pregunta")
def pregunta():
    d = request.get_json(force=True)
    texto = d.get("pregunta", "").strip()
    if not texto:
        return jsonify(error="Escribe una pregunta."), 400
    con = conectar(); cur = con.cursor(dictionary=True)
    try:
        respuesta, fuente = conocimiento.responder(cur, texto)
        cur.execute("INSERT INTO preguntas (usuario_id, pregunta, respuesta) VALUES ((SELECT id FROM usuarios WHERE nombre=%s), %s, %s)",
                    (d.get("usuario", ""), texto, respuesta))
        con.commit()
        return jsonify(respuesta=respuesta, fuente=fuente)
    finally:
        con.close()


if __name__ == "__main__":
    app.run(debug=True)