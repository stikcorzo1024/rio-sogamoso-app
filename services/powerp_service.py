"""Cliente de la API de PowerP para consultar autorizaciones CND.

Consulta el estado de autorización de cada período para la central Sogamoso.
"""
import uuid
import logging
from datetime import datetime

import requests

import config

logger = logging.getLogger(__name__)


class PowerPAuthService:
    """Cliente HTTP autenticado para la API de PowerP."""

    def __init__(self):
        self.session = requests.Session()
        self.session.verify = True
        self.token = None

    def _get_access_token(self):
        token_url = f"{config.POWERP_API_ENDPOINT}connect/token"
        token_url = token_url.replace('//connect', '/connect')

        data = {
            'grant_type': 'password',
            'client_id': config.POWERP_CLIENT_ID,
            'client_secret': config.POWERP_CLIENT_SECRET,
            'username': config.POWERP_USERNAME,
            'password': config.POWERP_PASSWORD,
            'scope': 'Ops'
        }

        response = self.session.post(token_url, data=data, timeout=30)
        if response.status_code == 200:
            self.token = response.json().get('access_token')
            return self.token
        else:
            raise Exception(f"Error obteniendo token PowerP: {response.status_code}")

    def _ensure_authenticated(self):
        if not self.token:
            self._get_access_token()
        self.session.headers.update({
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        })

    def get_power_system_resources(self):
        self._ensure_authenticated()
        url = f"{config.POWERP_API_ENDPOINT}api/app/power-system-resource/for-user"
        params = {"includeAll": "false"}

        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                self.token = None
                self._ensure_authenticated()
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                return response.json()
            raise

    def get_dispatch(self, resource_id, dispatch_date):
        self._ensure_authenticated()
        url = f"{config.POWERP_API_ENDPOINT}api/app/dispatch/generate-dispatch-program"
        params = {
            "powerSystemResourceId": str(resource_id),
            "dispatchDate": dispatch_date.strftime("%Y-%m-%d"),
            "skipCount": "0",
            "maxResultCount": "24"
        }

        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                self.token = None
                self._ensure_authenticated()
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                return response.json()
            raise


def _extract_list_from_response(data):
    if isinstance(data, dict):
        for v in data.values():
            if isinstance(v, list):
                return v
        return [data]
    elif isinstance(data, list):
        return data
    return [data]


def consultar_autorizaciones(central_nombre="SOGAMOSO", fecha=None):
    """Consulta la API de PowerP y retorna dict {periodo: causa} para la central.

    Args:
        central_nombre: Nombre de la central (default SOGAMOSO)
        fecha: datetime o None para hoy

    Returns:
        dict con {1: 'AUTOR', 2: '', 3: 'AUTOR', ...} para P1-P24
    """
    if fecha is None:
        fecha = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    resultado = {i: '' for i in range(1, 25)}  # P1-P24 vacíos por defecto

    try:
        service = PowerPAuthService()

        # Obtener recursos
        resources_raw = service.get_power_system_resources()
        if not resources_raw:
            logger.warning("[PowerP] No se obtuvieron recursos")
            return resultado

        resources = _extract_list_from_response(resources_raw)

        # Buscar la central
        central_recurso = None
        for item in resources:
            name = item.get("name") or item.get("displayName") or item.get("resourceName") or ""
            if central_nombre.upper() in name.upper():
                central_recurso = item
                break

        if not central_recurso:
            logger.warning(f"[PowerP] No se encontró la central {central_nombre}")
            return resultado

        # Obtener ID del recurso
        rid = central_recurso.get("id") or central_recurso.get("resourceId") or central_recurso.get("powerSystemResourceId")
        resource_id = uuid.UUID(str(rid))

        # Consultar despacho
        dispatch_raw = service.get_dispatch(resource_id, fecha)
        if not dispatch_raw:
            return resultado

        dispatch_data = _extract_list_from_response(dispatch_raw)

        # Extraer autorizaciones por período
        for row in dispatch_data:
            period = row.get('period')
            if period is None:
                continue
            try:
                period_num = int(period)
            except (ValueError, TypeError):
                continue
            if period_num < 1 or period_num > 24:
                continue

            causa = row.get('causeOfDeviationType', '')
            causa_str = str(causa).upper() if causa else ''
            resultado[period_num] = causa_str

        logger.info(f"[PowerP] Autorizaciones obtenidas para {central_nombre}")
        return resultado

    except Exception as e:
        logger.error(f"[PowerP] Error consultando autorizaciones: {e}")
        return resultado
