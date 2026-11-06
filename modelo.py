"""Modelo matemático (Tmedia, grados-día, HR media, precipitación acumulada) con control de calidad de datos."""
from datetime import timedelta
from statistics import median
from config import (TEMP_BASE, GDA_GENERACION, VENTANA_DIAS, MIN_FRACCION_OBS, UMBRAL_ATIPICO,
                    DIAS_RAPIDO, DIAS_LENTO)

CONTINUAS = ("temperatura", "humedad")   # variables medidas todo el día: se exige un mínimo de lecturas
FUENTE_DEFECTO = "Yáñez et al. (2019), Rev. Mex. Cienc. Agríc. 10(2):405-416"


def promedio(valores):
    valores = [v for v in valores if v is not None]
    return sum(valores) / len(valores) if valores else None


def redondear(valor):
    return round(valor, 1) if valor is not None else None


def cargar_parametros(cur):
    """Lee de MySQL la temperatura base y los grados-día por generación (con respaldo en config.py)."""
    p = {"temp_base_c": TEMP_BASE, "gda_generacion": GDA_GENERACION, "fuente": FUENTE_DEFECTO}
    try:
        cur.execute("SELECT clave, valor, fuente FROM parametros_plaga WHERE clave IN ('temp_base_c','gda_generacion')")
        for r in cur.fetchall():
            p[r["clave"]] = float(r["valor"])
            if r["fuente"]:
                p["fuente"] = r["fuente"]
    except Exception:
        pass
    return p


def calcular(cur, dep, mun):
    params = cargar_parametros(cur)
    tb, gda_gen = params["temp_base_c"], params["gda_generacion"]

    # 1. Última fecha con datos para este lugar
    cur.execute("SELECT MAX(fecha) AS f FROM clima_diario WHERE departamento=%s AND municipio=%s", (dep, mun))
    fin = cur.fetchone()["f"]
    if not fin:
        return None

    # 2. Registros diarios por estación en la ventana de días
    cur.execute("""
        SELECT fecha, variable, estacion_codigo, valor_medio, valor_min, valor_max, valor_suma, n_obs
        FROM clima_diario
        WHERE departamento=%s AND municipio=%s AND fecha>=%s
        ORDER BY fecha
    """, (dep, mun, fin - timedelta(days=VENTANA_DIAS)))
    filas = cur.fetchall()

    # 3. Control de calidad: descartar días incompletos (temperatura y humedad)
    maximo = {}
    for r in filas:
        k = (r["estacion_codigo"], r["variable"])
        maximo[k] = max(maximo.get(k, 0), r["n_obs"] or 0)
    buenas, descartados = [], 0
    for r in filas:
        incompleto = (r["n_obs"] or 0) < MIN_FRACCION_OBS * maximo[(r["estacion_codigo"], r["variable"])]
        if r["variable"] in CONTINUAS and incompleto:
            descartados += 1
        else:
            buenas.append(r)

    # 4. Un valor por día y variable (promedio entre estaciones)
    grupos = {}
    for r in buenas:
        grupos.setdefault((r["fecha"], r["variable"]), []).append(r)
    dias = {}
    for (fecha, variable), rs in grupos.items():
        d = dias.setdefault(fecha, {})
        if variable == "temperatura":
            d["tmedia"] = (promedio([x["valor_max"] for x in rs]) + promedio([x["valor_min"] for x in rs])) / 2   # (Tmax+Tmin)/2
        elif variable == "humedad":
            d["hr"] = promedio([x["valor_medio"] for x in rs])
        elif variable == "precipitacion":
            d["p"] = promedio([x["valor_suma"] for x in rs])
        # viento y presión se guardan, pero este modelo todavía no los usa
    if not dias:
        return None

    # 5. Días atípicos de temperatura (se marcan, no se borran)
    temps = [d["tmedia"] for d in dias.values() if "tmedia" in d]
    mediana = median(temps) if temps else None
    atipicos = []
    for fecha in sorted(dias):
        d = dias[fecha]
        if mediana is not None and "tmedia" in d and abs(d["tmedia"] - mediana) > UMBRAL_ATIPICO:
            d["atipico"] = True
            atipicos.append((fecha, d["tmedia"]))

    # 6. Grados-día diarios y acumulados
    serie, gda, hay_temperatura = [], 0.0, False
    for fecha in sorted(dias):
        d = dias[fecha]
        if "tmedia" in d:
            hay_temperatura = True
            d["gd"] = max(0.0, d["tmedia"] - tb)       # GDd = max(0, Tmedia - Tb)
            gda += d["gd"]                             # GDA = suma de los GDd
            d["gda"] = gda
        fila = {"fecha": fecha.isoformat()}
        for clave, valor in d.items():
            fila[clave] = valor if isinstance(valor, bool) or valor is None else round(valor, 2)
        serie.append(fila)

    # 7. Resúmenes del periodo
    t_media = promedio(temps)
    hr_media = promedio([d.get("hr") for d in dias.values()])
    lluvias = [d["p"] for d in dias.values() if "p" in d]
    p_acum = sum(lluvias) if lluvias else None

    # 8. Desarrollo potencial de la plaga: días que tardaría una generación al ritmo de calor del periodo
    generaciones, dias_gen = None, None
    if hay_temperatura:
        generaciones = gda / gda_gen
        gd_por_dia = gda / len(temps)
        dias_gen = gda_gen / gd_por_dia if gd_por_dia > 0 else None
    if dias_gen is None:
        riesgo = "Bajo"
    elif dias_gen <= DIAS_RAPIDO:
        riesgo = "Alto"
    elif dias_gen <= DIAS_LENTO:
        riesgo = "Medio"
    else:
        riesgo = "Bajo"

    # 9. Informe de calidad
    total = VENTANA_DIAS + 1
    cobertura = {nombre: min(100, round(100 * sum(1 for d in dias.values() if clave in d) / total))
                 for nombre, clave in (("temperatura", "tmedia"), ("humedad", "hr"), ("precipitacion", "p"))}
    base = min(cobertura["temperatura"], cobertura["humedad"])
    nivel = "Buena" if base >= 80 else ("Regular" if base >= 50 else "Baja")
    partes = [f"Días con dato: temperatura {cobertura['temperatura']} %, humedad {cobertura['humedad']} %, lluvia {cobertura['precipitacion']} %."]
    if descartados:
        partes.append(f"Se descartaron {descartados} registros diarios incompletos (menos de la mitad de las lecturas esperadas).")
    if atipicos:
        lista = ", ".join(f"{f.isoformat()} ({t:.1f} °C)" for f, t in atipicos)
        partes.append(f"Días atípicos (conviene revisarlos, se incluyen en los cálculos): {lista}; "
                      f"se alejan más de {UMBRAL_ATIPICO:g} °C de la mediana ({mediana:.1f} °C).")
    if cobertura["precipitacion"] < 50:
        partes.append("La lluvia tiene pocos días con dato: el total puede ser menor al real.")
    punto = {"icono": "🔍", "titulo": "Calidad de los datos", "clave": nivel, "detalle": " ".join(partes)}

    return {
        "desde": min(dias).isoformat(), "hasta": fin.isoformat(), "n_dias": len(dias),
        "t_media": redondear(t_media), "gda": redondear(gda) if hay_temperatura else None,
        "hr_media": redondear(hr_media), "p_acum": redondear(p_acum),
        "riesgo": riesgo, "serie": serie,
        "desarrollo": {"tb": tb, "gda_generacion": gda_gen, "generaciones": round(generaciones, 2) if generaciones is not None else None,
                       "dias_por_generacion": round(dias_gen) if dias_gen is not None else None, "fuente": params["fuente"]},
        "calidad": {"nivel": nivel, "cobertura": cobertura, "descartados": descartados,
                    "atipicos": [{"fecha": f.isoformat(), "valor": round(t, 1)} for f, t in atipicos], "punto": punto},
    }