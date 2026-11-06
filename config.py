import os
from dotenv import load_dotenv
load_dotenv()

DB = dict(
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", "3306")),
    user=os.getenv("DB_USER", "root"),
    password=os.getenv("DB_PASSWORD", ""),
    database=os.getenv("DB_NAME", "bioalert"),
)

SOCRATA_URL = "https://www.datos.gov.co/resource/"
APP_TOKEN = os.getenv("SOCRATA_APP_TOKEN", "")

# IDs de los datasets del IDEAM en datos.gov.co
DATASETS = {
    "precipitacion": "s54a-sgyg",
    "temperatura": "sbwg-7ju4",
    "humedad": "uext-mhny",
    "viento_velocidad": "sgfv-3yp8",
    "viento_direccion": "kiw7-v9ta",
    "presion": "62tk-nxj5",
}

TEMP_BASE = 10.9        # Tb (°C): respaldo si la tabla parametros_plaga no existe (Yáñez et al. 2019)
GDA_GENERACION = 559.1  # grados-día por generación: respaldo (Yáñez et al. 2019)
VENTANA_DIAS = 30       # días hacia atrás que se analizan

# Clasificación PROVISIONAL del desarrollo potencial, según los días que tardaría una generación al ritmo de calor actual
DIAS_RAPIDO = 40        # hasta 40 días: dentro del rango típico de 24 a 40 días (CropLife)
DIAS_LENTO = 70         # más de 70 días: desarrollo lento

# --- Calidad de datos ---
# (mínimo, máximo) válidos para cada lectura individual; fuera de ese rango se descarta (p. ej. -999 o 9999 de sensores dañados)
LIMITES = {
    "temperatura": (-15, 50),
    "humedad": (0, 100),
    "precipitacion": (0, 300),
    "viento_velocidad": (0, 200),
    "viento_direccion": (0, 360),
}
MIN_FRACCION_OBS = 0.5   # se descarta un día si tiene menos de la mitad de lecturas que el día más completo de esa estación
UMBRAL_ATIPICO = 5.0     # °C de diferencia con la mediana para marcar un día de temperatura como atípico