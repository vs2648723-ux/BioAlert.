"""Base de conocimiento sobre el gusano cogollero: resúmenes con palabras propias + buscador por palabras clave (sin IA).

Fuente de la información: CropLife Latin America (s. f.), página sobre el gusano cogollero.
Los textos de base_conocimiento.json son resúmenes redactados por el equipo, no copias del original.
"""
import json
import math
import os
import re
from ideam import sin_tildes

URL = "https://croplifela.org/es/plagas/listado-de-plagas/gusano-cogollero"
ARCHIVO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "base_conocimiento.json")


def guardar(cur):
    """Carga en MySQL los resúmenes de base_conocimiento.json (reemplaza lo que hubiera antes)."""
    with open(ARCHIVO, encoding="utf-8") as f:
        fragmentos = json.load(f)
    cur.execute("""INSERT INTO plagas (nombre_comun, nombre_cientifico, cultivo)
                   VALUES ('Gusano cogollero','Spodoptera frugiperda','maiz')
                   ON DUPLICATE KEY UPDATE nombre_comun=VALUES(nombre_comun)""")
    cur.execute("SELECT id FROM plagas WHERE nombre_cientifico='Spodoptera frugiperda'")
    pid = cur.fetchone()["id"]
    cur.execute("DELETE FROM conocimiento_plaga WHERE plaga_id=%s", (pid,))
    for fr in fragmentos:
        cur.execute("INSERT INTO conocimiento_plaga (plaga_id, seccion, contenido, fuente_url) VALUES (%s,%s,%s,%s)",
                    (pid, fr["seccion"][:255], fr["texto"], URL))
    return len(fragmentos)


STOP = set("el la los las de del en y a que un una es para por con se al lo como mas su sus o cual cuales donde "
           "puede pueden hay son ser esta este esto ese eso me mi quiero saber dime sobre cuanto cuantos cuanta tiene "
           "causa causar causan provoca produce ataca atacan afecta afectan gusano cogollero oruga isoca plaga plagas "
           "hacer hago debo deben puedo todo toda muy tambien segun entre desde hasta".split())
SINONIMOS = {"daña": "daño", "dañan": "daño", "dañar": "daño", "dañino": "daño", "oruga": "gusano", "isoca": "gusano", "veneno": "insecticida", "combatir": "controlar", "eliminar": "controlar",
             "mariposa": "polilla", "tarda": "dura", "duracion": "dura", "huevecillos": "huevos", "danos": "daño"}


def _raiz(p):
    p = p[:-1] if p.endswith("s") and len(p) > 4 else p      # quita la "s" del plural
    return p[:5] if len(p) > 5 else p                        # raíz simple: "identificar" e "identifico" quedan iguales


def _tokens(t):
    palabras = re.findall(r"[a-zñ]{3,}|\d+", sin_tildes(t.lower().replace("ñ", "#")).replace("#", "ñ"))
    return {_raiz(SINONIMOS.get(p, p)) for p in palabras if p not in STOP}


def ordenar(filas, pregunta):
    """Ordena los fragmentos por parecido con la pregunta. Las palabras que aparecen en casi todos los
    fragmentos (como 'gusano' o 'maíz') pesan poco; las poco frecuentes pesan más."""
    q = _tokens(pregunta)
    info = [(r, _tokens(r["contenido"]), _tokens(r["seccion"])) for r in filas]
    n = len(info)
    df = {}
    for _, tc, ts in info:
        for p in tc | ts:
            df[p] = df.get(p, 0) + 1
    puntuados = []
    for r, tc, ts in info:
        puntos = sum(math.log(1 + n / df.get(p, 1)) * (1 + 3 * (p in ts)) for p in q if p in tc or p in ts)
        if puntos > 0:
            puntuados.append((puntos, r))
    puntuados.sort(key=lambda x: -x[0])
    return puntuados


def responder(cur, pregunta):
    cur.execute("SELECT seccion, contenido, fuente_url FROM conocimiento_plaga")
    puntuados = ordenar(cur.fetchall(), pregunta)
    if not puntuados or puntuados[0][0] < 2.5:
        return ("No encontré información sobre eso en mi base de conocimiento. Prueba con preguntas sobre: "
                "cómo identificar la plaga, su ciclo de vida, los daños que causa o cuándo y cómo controlarla.", None)
    mejores = [r for p, r in puntuados[:2] if p >= puntuados[0][0] * 0.7]
    texto = "\n\n".join(r["contenido"] for r in mejores)
    return texto + "\n\n(Resumen basado en CropLife Latin America)", mejores[0]["fuente_url"]