"""Servicio de conexión FTP a XM para la app móvil."""
import re
import threading
import time
from datetime import datetime, timedelta
from ftplib import FTP_TLS
from io import BytesIO

import config


def conectar_ftp(usuario, contraseña, directorio=None):
    """Establece conexión FTP con el servidor XM."""
    try:
        print("[FTP] Creando objeto FTP_TLS...")
        ftps = FTP_TLS(timeout=30)
        ftps.debugging = 0
        ftps.encoding = 'latin-1'

        print(f"[FTP] Conectando a {config.XM_HOST}:{config.XM_PORT}...")
        ftps.connect(config.XM_HOST, port=config.XM_PORT, timeout=30)
        print("[FTP] Conexión TCP establecida")

        print("[FTP] Iniciando AUTH TLS...")
        ftps.auth()
        print("[FTP] AUTH TLS completado")

        print("[FTP] Configurando PROT P...")
        ftps.prot_p()
        print("[FTP] PROT P completado")

        try:
            print(f"[FTP] Iniciando login con usuario {usuario[:3]}***...")
            ftps.login(user=usuario, passwd=contraseña)
            print("[FTP] Login exitoso")
        except Exception as login_error:
            error_msg = str(login_error)
            print(f"[FTP] Error en login: {error_msg}")
            if "530" in error_msg:
                return None, False, "AUTH_ERROR"
            return None, False, str(login_error)

        if directorio:
            ftps.cwd(directorio)

        return ftps, True, None
    except Exception as e:
        print(f"[FTP] Error de conexión: {str(e)}")
        return None, False, str(e)


class BuscadorRedespachos:
    """Busca y procesa archivos de despacho/redespacho del FTP de XM."""

    def __init__(self, callback_estado=None, callback_datos=None):
        self.callback_estado = callback_estado
        self.callback_datos = callback_datos
        self.running = False
        self.ftps = None
        self.conectado = False

        self.central = config.CENTRAL_NOMBRE
        self.tiene_agc = config.CENTRAL_TIENE_AGC
        self.ciclo_minutos = config.CICLOVAR

        # Historial del día
        self.programado = {}
        self.historial_real = {}
        self.programado_agc = {}
        self.historial_real_agc = {}
        self.fecha_historial = None

        # Redespacho actual/siguiente
        self.redespacho_actual = None
        self.redespacho_siguiente = None

    def _emitir_estado(self, mensaje):
        if self.callback_estado:
            self.callback_estado(mensaje)
        print(f"[Estado] {mensaje}")

    def _emitir_datos(self):
        if self.callback_datos:
            self.callback_datos({
                'programado': self.programado,
                'historial_real': self.historial_real,
                'programado_agc': self.programado_agc,
                'historial_real_agc': self.historial_real_agc,
                'redespacho_actual': self.redespacho_actual,
                'redespacho_siguiente': self.redespacho_siguiente,
            })

    def iniciar_monitoreo(self, usuario, contraseña):
        """Inicia el monitoreo en un hilo separado."""
        self.usuario = usuario
        self.contraseña = contraseña
        self.running = True

        self._emitir_estado("Conectando a XM...")

        if not self._conectar_ftp():
            self._emitir_estado("Error de conexión")
            return False

        self._emitir_estado("Conectado")
        self._inicializar_historial_dia()

        while self.running:
            self._actualizar_periodos()
            self._inicializar_historial_dia()

            if self._es_tiempo_verificacion():
                if self._obtener_redespachos():
                    self._emitir_datos()

            self._esperar_siguiente_ciclo()

        return True

    def detener(self):
        self.running = False
        if self.ftps:
            try:
                self.ftps.quit()
            except:
                pass

    def _conectar_ftp(self, directorio=None):
        """Establece conexión con el servidor FTP de XM."""
        intentos = 0
        while self.running and intentos < 3:
            try:
                self.ftps, self.conectado, error_msg = conectar_ftp(
                    self.usuario, self.contraseña, directorio
                )
                if error_msg == "AUTH_ERROR":
                    self._emitir_estado("Error de autenticación")
                    return False
                if self.conectado:
                    return True
                time.sleep(5)
                intentos += 1
            except Exception as e:
                self._emitir_estado(f"Error: {str(e)}")
                return False
        return False

    def _actualizar_periodos(self):
        now = datetime.now()
        self.now = now
        self.mes = now.strftime('%m')
        self.año = now.strftime('%Y')
        self.dia = now.strftime('%d')
        self.dia_actual = now.strftime('%d')
        self.minuto = now.minute

        hora_p_actual = (now.hour + 1)
        hora_p_siguiente = (now.hour + 2)

        self.periodo_actual = "24" if hora_p_actual % 24 == 0 else str(hora_p_actual % 24)
        self.periodo_siguiente = "24" if hora_p_siguiente % 24 == 0 else str(hora_p_siguiente % 24)

    def _es_tiempo_verificacion(self):
        if self.minuto == 0:
            return True
        return self.minuto % self.ciclo_minutos == 0

    def _obtener_redespachos(self):
        """Obtiene archivos de redespacho del FTP."""
        try:
            ruta = f'/INFORMACION_XM/PUBLICO/Redespacho/Horario/{self.año}-{self.mes}/'

            if not self._conectar_ftp(ruta):
                return False

            periodo_actual_fmt = self.periodo_actual.zfill(2)
            periodo_siguiente_fmt = self.periodo_siguiente.zfill(2)

            filename_actual = f'redespacho{periodo_actual_fmt}_{self.mes}{self.dia_actual}.txt'

            if int(self.periodo_siguiente) < int(self.periodo_actual):
                mañana = self.now + timedelta(days=1)
                mes_mañana = mañana.strftime('%m')
                dia_mañana = mañana.strftime('%d')
                filename_siguiente = f'redespacho{periodo_siguiente_fmt}_{mes_mañana}{dia_mañana}.txt'
            else:
                filename_siguiente = f'redespacho{periodo_siguiente_fmt}_{self.mes}{self.dia_actual}.txt'

            # Procesar archivos
            self.redespacho_actual = self._procesar_archivo_redespacho(filename_actual)
            self.redespacho_siguiente = self._procesar_archivo_redespacho(filename_siguiente)

            # Actualizar historial desde rDEC
            self._actualizar_historial_desde_rdec()

            return True

        except Exception as e:
            self._emitir_estado(f"Error: {str(e)}")
            return False

    def _procesar_archivo_redespacho(self, nombre_archivo):
        """Descarga y procesa un archivo de redespacho."""
        try:
            buffer = BytesIO()
            self.ftps.retrbinary(f'RETR {nombre_archivo}', buffer.write)
            contenido = buffer.getvalue().decode('utf-8', errors='ignore')

            lineas = [l.strip() for l in contenido.strip().split('\n') if l.strip()]
            if not lineas:
                return None

            encabezados = lineas[0]
            nombres_columnas = re.split(r'\s{2,}', encabezados.strip())

            datos_procesados = []
            for linea in lineas[1:]:
                if not linea.strip():
                    continue
                valores = re.split(r'\s{2,}', linea.strip())
                fila = {}
                for i in range(min(len(valores), len(nombres_columnas))):
                    fila[nombres_columnas[i]] = self._formatear_valor(valores[i])

                if 'GENERADOR' in fila:
                    generador = fila['GENERADOR']
                    if generador == self.central or generador.startswith(self.central):
                        fila['GENERADOR'] = self.central
                        if 'PERIODO' in fila:
                            fila['PERIODO'] = 'P' + str(fila['PERIODO']).replace('P', '')
                        datos_procesados.append(fila)

            return datos_procesados if datos_procesados else None

        except Exception as e:
            print(f"Error procesando {nombre_archivo}: {e}")
            return None

    def _formatear_valor(self, valor):
        if valor is None or not str(valor).strip():
            return ""
        try:
            num = float(str(valor).replace(',', '.'))
            if num.is_integer():
                return str(int(num))
            return f"{round(num, 2):.2f}"
        except ValueError:
            return valor

    def _inicializar_historial_dia(self):
        """Carga el despacho programado del día (dDEC)."""
        hoy = datetime.now().strftime('%Y-%m-%d')
        if self.fecha_historial == hoy:
            return

        programado = self._obtener_dec()
        if programado is None:
            return

        self.programado = programado
        self.historial_real = dict(programado)
        self.fecha_historial = hoy
        self._emitir_estado("Despacho del día cargado")

    def _obtener_dec(self):
        """Descarga dDEC del FTP de XM."""
        try:
            now = datetime.now()
            año, mes, dia = now.strftime('%Y'), now.strftime('%m'), now.strftime('%d')
            ruta = f'/INFORMACION_XM/PUBLICO/DESPACHO/{año}-{mes}/'

            if not self._conectar_ftp(ruta):
                return None

            return self._procesar_archivo_despacho(f'dDEC{mes}{dia}.txt')
        except Exception as e:
            print(f"Error obteniendo dDEC: {e}")
            return None

    def _obtener_rdec(self):
        """Descarga rDEC del FTP de XM."""
        try:
            now = datetime.now()
            año, mes, dia = now.strftime('%Y'), now.strftime('%m'), now.strftime('%d')
            ruta = f'/INFORMACION_XM/PUBLICO/Redespacho/{año}-{mes}/'

            if not self._conectar_ftp(ruta):
                return None

            return self._procesar_archivo_despacho(f'rDEC{mes}{dia}.txt')
        except Exception as e:
            print(f"Error obteniendo rDEC: {e}")
            return None

    def _actualizar_historial_desde_rdec(self):
        """Actualiza el historial con el rDEC."""
        rdec = self._obtener_rdec()
        if rdec is not None:
            self.historial_real = rdec

    def _procesar_archivo_despacho(self, nombre_archivo):
        """Procesa archivos dDEC/rDEC."""
        try:
            buffer = BytesIO()
            self.ftps.retrbinary(f'RETR {nombre_archivo}', buffer.write)
            contenido = buffer.getvalue().decode('utf-8', errors='ignore')

            for linea in contenido.strip().split('\n'):
                linea = linea.strip()
                if not linea:
                    continue

                match = re.search(r'"([^"]+)"', linea)
                if not match or match.group(1).strip() != self.central:
                    continue

                valores_texto = linea[linea.rindex('"') + 1:].strip()
                if valores_texto.startswith(','):
                    valores_texto = valores_texto[1:].strip()

                valores = {}
                for i, val in enumerate(valores_texto.split(','), start=1):
                    if i > 24:
                        break
                    try:
                        num = float(val.strip().replace(',', '.'))
                        valores[f'P{i}'] = int(num) if num.is_integer() else round(num, 2)
                    except:
                        valores[f'P{i}'] = 0

                return valores

            return None

        except Exception as e:
            print(f"Error procesando {nombre_archivo}: {e}")
            return None

    def _esperar_siguiente_ciclo(self):
        """Espera hasta el siguiente ciclo de verificación."""
        minuto_actual = datetime.now().minute
        minutos_espera = self.ciclo_minutos - (minuto_actual % self.ciclo_minutos)
        if minutos_espera == 0:
            minutos_espera = self.ciclo_minutos

        segundos_espera = max(minutos_espera * 60, 60)

        for _ in range(segundos_espera):
            if not self.running:
                break
            time.sleep(1)
