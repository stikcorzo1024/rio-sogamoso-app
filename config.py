"""Configuración de la aplicación móvil Río Sogamoso."""
import os

# --- App ---
APP_NOMBRE = "Río Sogamoso"
APP_VERSION = "1.0.0"

# --- Central ---
CENTRAL_NOMBRE = "SOGAMOSO"
CENTRAL_ETIQUETA = "Sogamoso"
CENTRAL_TIENE_AGC = True
CENTRAL_POTENCIA_MAX = 819  # 3 × 273 MW

# --- XM (FTPS xmftps.xm.com.co:210) ---
# Las credenciales se guardan en el almacenamiento seguro del dispositivo
XM_HOST = "xmftps.xm.com.co"
XM_PORT = 210

# --- Ciclo de verificación (minutos) ---
CICLOVAR = 1

# --- Zona horaria Colombia ---
ZONA_HORARIA = "America/Bogota"

# --- PowerP (autorizaciones CND) ---
POWERP_API_ENDPOINT = "https://isgg.powerp.app/ops-api/"
POWERP_CLIENT_ID = "Client_ConsumerApp"
POWERP_CLIENT_SECRET = "pcnCG1aqPYkB+/ORj43uQOL+LjV5c/yieZgZHQTeifg="
POWERP_USERNAME = "svc-coi@isagen.com"
POWERP_PASSWORD = "v18y@<7Y7[nk"
