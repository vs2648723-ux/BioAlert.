"""Genera la explicación en viñetas a partir de los resultados del modelo (sin IA)."""
from config import DIAS_RAPIDO, DIAS_LENTO


def _promedio(valores):
    valores = [v for v in valores if v is not None]
    return sum(valores) / len(valores) if valores else None


def explicar(res):
    serie = res["serie"]
    dev = res["desarrollo"]
    temps = [(s["fecha"], s["tmedia"]) for s in serie if s.get("tmedia") is not None]
    lluvias = [(s["fecha"], s["p"]) for s in serie if s.get("p") is not None]
    puntos = []

    # Periodo
    puntos.append({
        "icono": "📈", "titulo": "Periodo analizado",
        "clave": f"{res['n_dias']} días ({res['desde']} a {res['hasta']})",
        "detalle": "Línea naranja: temperatura media diaria. Barras azules: lluvia en mm.",
    })

    # Temperatura
    if res.get("t_media") is not None:
        if len(temps) >= 4:
            mitad = len(temps) // 2
            dif = _promedio([t for _, t in temps[mitad:]]) - _promedio([t for _, t in temps[:mitad]])
            tendencia = "tendencia a subir" if dif > 0.5 else ("tendencia a bajar" if dif < -0.5 else "estable")
            dia_max = max(temps, key=lambda x: x[1])
            dia_min = min(temps, key=lambda x: x[1])
            puntos.append({
                "icono": "🌡️", "titulo": "Temperatura",
                "clave": f"{res['t_media']} °C de promedio, {tendencia}",
                "detalle": f"Día más cálido: {dia_max[0]} ({dia_max[1]} °C). Día más fresco: {dia_min[0]} ({dia_min[1]} °C).",
            })
        else:
            puntos.append({"icono": "🌡️", "titulo": "Temperatura", "clave": f"{res['t_media']} °C de promedio",
                           "detalle": "Hay pocos días de datos para ver una tendencia."})
    else:
        puntos.append({"icono": "🌡️", "titulo": "Temperatura", "clave": "Sin datos",
                       "detalle": "El IDEAM no entregó temperatura para este lugar, así que no se calculó el calor acumulado."})

    # Lluvia
    if lluvias:
        dias_lluvia = [x for x in lluvias if x[1] >= 1]
        mas = max(lluvias, key=lambda x: x[1])
        puntos.append({
            "icono": "🌧️", "titulo": "Lluvia",
            "clave": f"{res['p_acum']} mm en total",
            "detalle": (f"Llovió (1 mm o más) en {len(dias_lluvia)} de {len(lluvias)} días. "
                        f"Día más lluvioso: {mas[0]} ({round(mas[1], 1)} mm). "
                        f"Se muestra como contexto: el indicador de desarrollo no la usa."),
        })

    # Humedad (informativa)
    if res.get("hr_media") is not None:
        puntos.append({"icono": "💧", "titulo": "Humedad relativa", "clave": f"{res['hr_media']} % de promedio",
                       "detalle": "Se muestra como información: el indicador de desarrollo no la usa."})

    # Grados-día
    if res.get("gda") is not None:
        pct = round(100 * dev["generaciones"])
        puntos.append({
            "icono": "🔥", "titulo": "Grados-día acumulados",
            "clave": f"{res['gda']} °C·día ({pct} % de una generación)",
            "detalle": (f"Calor acumulado sobre la temperatura base de {dev['tb']:g} °C. "
                        f"Una generación necesita unos {dev['gda_generacion']:g} grados-día (desde el huevo hasta la preoviposición)."),
        })

    # Desarrollo potencial
    if dev["dias_por_generacion"] is not None:
        ritmo = {"Alto": "rápido", "Medio": "moderado", "Bajo": "lento"}[res["riesgo"]]
        detalle = (f"Al ritmo de calor de este periodo, una generación tardaría unos {dev['dias_por_generacion']} días "
                   f"(ritmo {ritmo}). Según CropLife, el ciclo completo dura aproximadamente entre 24 y 40 días.")
    else:
        detalle = "No se pudo estimar la duración de una generación porque faltan datos de temperatura o no hay calor acumulado."
    puntos.append({"icono": "🐛", "titulo": "Desarrollo potencial de la plaga", "clave": res["riesgo"], "detalle": detalle})

    acciones = [
        "Monitorea el cultivo una vez por semana.",
        "Revisa el envés de las hojas en busca de posturas de huevos.",
        "Busca las \"ventanitas\" (daño grado 1): es el mejor momento para controlar, porque la larva aún está expuesta.",
        "Presta más atención en la fase vegetativa inicial (alrededor de 30 días después de la siembra), cuando se presentan los ataques más severos.",
    ]
    aviso = (f"Este indicador estima qué tan rápido podría desarrollarse la plaga con el calor observado; no mide si hay "
             f"plaga en tu cultivo ni el daño. Los parámetros (temperatura base y grados-día por generación) vienen de {dev['fuente']}, "
             f"y los límites de {DIAS_RAPIDO} y {DIAS_LENTO} días para clasificarlo son provisionales. Los datos son de estaciones del "
             f"IDEAM cercanas, no de tu finca. Fuentes: datos del IDEAM, parámetros de Yáñez et al. (2019) y recomendaciones de "
             f"CropLife Latin America. Úsalo como orientación y consulta a un técnico agrícola.")
    return {"puntos": puntos, "acciones": acciones, "fuente_acciones": "CropLife Latin America", "aviso": aviso}