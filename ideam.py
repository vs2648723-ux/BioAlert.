"""Descarga datos del IDEAM desde datos.gov.co (API Socrata) y los guarda en MySQL."""
import unicodedata
from datetime import datetime, timedelta
import requests
from config import SOCRATA_URL, APP_TOKEN, DATASETS, VENTANA_DIAS, LIMITES

ACENTOS = {"A": "Á", "E": "É", "I": "Í", "O": "Ó", "U": "Ú", "N": "Ñ"}


def sin_tildes(t):
    return "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")


def normalizar(t):
    return sin_tildes(t.strip().upper())


def variantes(valor):
    """Escrituras posibles del nombre: sin tilde, con una tilde en cada letra posible, y en formato Título."""
    base = normalizar(valor)
    res = {base, valor.strip().upper()}
    for i, ch in enumerate(base):
        if ch in ACENTOS:
            res.add(base[:i] + ACENTOS[ch] + base[i + 1:])
    res |= {v.title() for v in list(res)}
    return res


def _en(campo, valor):
    lista = ",".join("'" + v.replace("'", "''") + "'" for v in sorted(variantes(valor)))
    return f"{campo} in({lista})"


def _get(dataset, params):
    headers = {"X-App-Token": APP_TOKEN} if APP_TOKEN else {}
    r = requests.get(f"{SOCRATA_URL}{dataset}.json", params=params, headers=headers, timeout=120)
    r.raise_for_status()
    return r.json()


def descargar_diario(variable, departamento, municipio, dias=VENTANA_DIAS):
    """Devuelve una fila por estación y día (promedio, mínimo, máximo, suma)."""
    ds = DATASETS[variable]
    lugar = f"{_en('departamento', departamento)} AND {_en('municipio', municipio)}"
    lim = LIMITES.get(variable)   # descarta lecturas imposibles (sensores dañados)
    rango = f" AND valorobservado >= {lim[0]} AND valorobservado <= {lim[1]}" if lim else ""
    for ventana in (dias, 365):          # primero los últimos días; si no hay nada, el último año
        ini = datetime.now() - timedelta(days=ventana)
        filas = _get(ds, {
            "$select": ("codigoestacion, nombreestacion, date_trunc_ymd(fechaobservacion) as dia, "
                        "avg(valorobservado) as media, min(valorobservado) as minimo, "
                        "max(valorobservado) as maximo, sum(valorobservado) as suma, count(*) as n"),
            "$where": f"{lugar}{rango} AND fechaobservacion >= '{ini:%Y-%m-%dT00:00:00}'",
            "$group": "codigoestacion, nombreestacion, dia",
            "$order": "dia",
            "$limit": 50000,
        })
        if filas:
            return filas
    return []


def guardar_clima(cur, variable, filas, departamento, municipio):
    dep, mun = normalizar(departamento), normalizar(municipio)
    for f in filas:
        cur.execute("""
            INSERT INTO clima_diario (departamento, municipio, estacion_codigo, estacion_nombre, fecha,
                                      variable, valor_medio, valor_min, valor_max, valor_suma, n_obs)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE valor_medio=VALUES(valor_medio), valor_min=VALUES(valor_min),
                valor_max=VALUES(valor_max), valor_suma=VALUES(valor_suma), n_obs=VALUES(n_obs)
        """, (dep, mun, f["codigoestacion"], f.get("nombreestacion"), f["dia"][:10], variable,
              float(f["media"]), float(f["minimo"]), float(f["maximo"]), float(f["suma"]), int(f["n"])))
    return len(filas)