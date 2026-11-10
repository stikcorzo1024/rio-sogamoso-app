"""Río Sogamoso - App móvil de monitoreo de despacho.

Aplicación Kivy/KivyMD que se conecta directamente al FTP de XM
para mostrar el despacho y redespacho de la central Sogamoso.
"""
import threading
from datetime import datetime

from kivy.clock import Clock, mainthread
from kivy.properties import StringProperty, BooleanProperty
from kivy.storage.jsonstore import JsonStore
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.metrics import dp

from kivymd.app import MDApp
from kivymd.uix.list import MDList
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.card import MDCard

import config
from services.ftp_service import BuscadorRedespachos
from services.powerp_service import consultar_autorizaciones


class PeriodoItem(MDCard):
    """Item de la lista para cada período."""

    def __init__(self, periodo="", despacho="--", redespacho="--",
                 autorizacion="", es_actual=False, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        self.size_hint_y = None
        self.height = dp(60)
        self.padding = dp(10)
        self.spacing = dp(10)
        self.md_bg_color = (0.15, 0.3, 0.3, 1) if es_actual else (0.1, 0.15, 0.2, 1)
        self.radius = [10]

        # Período - KivyMD 1.2.0 usa font_style H6 en lugar de Title
        periodo_label = MDLabel(
            text=periodo,
            font_style="H6",
            size_hint_x=0.15,
            halign="center",
            theme_text_color="Custom",
            text_color=(0.2, 0.8, 0.7, 1) if es_actual else (0.6, 0.7, 0.8, 1)
        )
        self.add_widget(periodo_label)

        # Despacho
        desp_box = MDBoxLayout(orientation="vertical", size_hint_x=0.30)
        desp_box.add_widget(MDLabel(
            text="Despacho",
            font_style="Caption",
            theme_text_color="Secondary",
            size_hint_y=0.4
        ))
        desp_box.add_widget(MDLabel(
            text=f"{despacho} MW",
            font_style="Body1",
            size_hint_y=0.6
        ))
        self.add_widget(desp_box)

        # Redespacho
        redesp_box = MDBoxLayout(orientation="vertical", size_hint_x=0.30)
        redesp_box.add_widget(MDLabel(
            text="Redespacho",
            font_style="Caption",
            theme_text_color="Secondary",
            size_hint_y=0.4
        ))

        # Resaltar si es diferente
        es_diferente = despacho != redespacho and redespacho != "--"
        redesp_box.add_widget(MDLabel(
            text=f"{redespacho} MW",
            font_style="Body1",
            theme_text_color="Custom" if es_diferente else "Primary",
            text_color=(1, 0.75, 0.2, 1) if es_diferente else (1, 1, 1, 1),
            size_hint_y=0.6
        ))
        self.add_widget(redesp_box)

        # Indicador de autorización
        es_autorizado = autorizacion == "AUTOR"
        tiene_causa = autorizacion and autorizacion != ""

        # Color según tipo de autorización
        if es_autorizado:
            aut_color = (0.2, 0.8, 0.2, 1)  # Verde para AUTOR
            aut_text = "A"
        elif tiene_causa:
            aut_color = (1, 0.75, 0.2, 1)  # Amarillo para otras causas
            aut_text = autorizacion[:1] if autorizacion else ""
        else:
            aut_color = (0.5, 0.5, 0.5, 1)
            aut_text = ""

        aut_label = MDLabel(
            text=aut_text,
            font_style="H6",
            size_hint_x=0.25,
            halign="center",
            theme_text_color="Custom",
            text_color=aut_color
        )
        self.add_widget(aut_label)


class LoginScreen(Screen):
    """Pantalla de login con credenciales XM."""

    def iniciar_sesion(self):
        usuario = self.ids.usuario.text.strip()
        contrasena = self.ids.contrasena.text.strip()

        if not usuario or not contrasena:
            self.ids.error_label.text = "Ingrese usuario y contraseña"
            return

        self.ids.error_label.text = ""
        app = MDApp.get_running_app()
        app.conectar_xm(usuario, contrasena)


class TablaDespachoScreen(Screen):
    """Pantalla principal con la tabla de despacho."""

    def on_enter(self):
        app = MDApp.get_running_app()
        app.actualizar_ui()

    def refrescar(self):
        app = MDApp.get_running_app()
        # Refrescar autorizaciones también
        app.consultar_autorizaciones_async()
        if app.buscador and app.buscador.running:
            app.actualizar_ui()

    def cerrar_sesion(self):
        app = MDApp.get_running_app()
        app.desconectar()

    def abrir_menu(self):
        pass  # Por implementar: menú lateral


class GraficoScreen(Screen):
    """Pantalla con gráfico de generación."""

    def volver(self):
        self.manager.current = 'tabla'


class RioSogamosoApp(MDApp):
    """Aplicación principal."""

    estado_conexion = StringProperty("Desconectado")
    periodo_actual = StringProperty("P--")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.buscador = None
        self.hilo_monitoreo = None
        self.datos_actuales = {}
        self.autorizaciones = {}  # {1: 'AUTOR', 2: '', ...}
        self.store = JsonStore('riosogamoso.json')

    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Teal"

        self.title = config.APP_NOMBRE

        sm = ScreenManager()
        sm.add_widget(LoginScreen(name='login'))
        sm.add_widget(TablaDespachoScreen(name='tabla'))
        sm.add_widget(GraficoScreen(name='grafico'))

        # Cargar credenciales guardadas
        if self.store.exists('credenciales'):
            creds = self.store.get('credenciales')
            Clock.schedule_once(lambda dt: self._auto_login(creds), 0.5)

        # Actualizar reloj y período cada segundo
        Clock.schedule_interval(self._actualizar_reloj, 1)

        return sm

    def _auto_login(self, creds):
        """Intenta login automático con credenciales guardadas."""
        login_screen = self.root.get_screen('login')
        login_screen.ids.usuario.text = creds.get('usuario', '')
        login_screen.ids.contrasena.text = creds.get('contrasena', '')

    def conectar_xm(self, usuario, contrasena):
        """Inicia conexión al FTP de XM."""
        self.estado_conexion = "Conectando..."

        # Guardar credenciales
        self.store.put('credenciales', usuario=usuario, contrasena=contrasena)

        # Crear buscador
        self.buscador = BuscadorRedespachos(
            callback_estado=self._on_estado,
            callback_datos=self._on_datos
        )

        # Iniciar en hilo separado
        self.hilo_monitoreo = threading.Thread(
            target=self._iniciar_monitoreo,
            args=(usuario, contrasena),
            daemon=True
        )
        self.hilo_monitoreo.start()

        # Consultar autorizaciones PowerP en paralelo
        self.consultar_autorizaciones_async()

        # Cambiar a pantalla de tabla
        self.root.current = 'tabla'

    def _iniciar_monitoreo(self, usuario, contrasena):
        """Ejecuta el monitoreo en hilo separado."""
        self.buscador.iniciar_monitoreo(usuario, contrasena)

    def consultar_autorizaciones_async(self):
        """Consulta autorizaciones PowerP en hilo separado."""
        def _consultar():
            try:
                print("[PowerP] Consultando autorizaciones...")
                autorizaciones = consultar_autorizaciones(config.CENTRAL_NOMBRE)
                self._on_autorizaciones(autorizaciones)
            except Exception as e:
                print(f"[PowerP] Error: {e}")

        threading.Thread(target=_consultar, daemon=True).start()

    @mainthread
    def _on_autorizaciones(self, autorizaciones):
        """Callback cuando llegan las autorizaciones de PowerP."""
        self.autorizaciones = autorizaciones
        print(f"[PowerP] Autorizaciones recibidas: {sum(1 for v in autorizaciones.values() if v)} períodos con causa")
        self.actualizar_ui()

    @mainthread
    def _on_estado(self, mensaje):
        """Callback cuando cambia el estado de conexión."""
        self.estado_conexion = mensaje
        self._actualizar_chip_estado()

    @mainthread
    def _on_datos(self, datos):
        """Callback cuando llegan nuevos datos."""
        self.datos_actuales = datos
        self.actualizar_ui()

    def _actualizar_reloj(self, dt):
        """Actualiza el período actual según la hora."""
        now = datetime.now()
        hora_p = now.hour + 1
        self.periodo_actual = f"P{hora_p if hora_p <= 24 else hora_p - 24}"

        # Actualizar chip de período
        if self.root and self.root.current == 'tabla':
            tabla = self.root.get_screen('tabla')
            if hasattr(tabla.ids, 'chip_periodo'):
                tabla.ids.chip_periodo.text = self.periodo_actual

    def _actualizar_chip_estado(self):
        """Actualiza el chip de estado de conexión."""
        if self.root and self.root.current == 'tabla':
            tabla = self.root.get_screen('tabla')
            if hasattr(tabla.ids, 'chip_estado'):
                chip = tabla.ids.chip_estado
                chip.text = self.estado_conexion

    def actualizar_ui(self):
        """Actualiza la interfaz con los datos actuales."""
        if not self.datos_actuales:
            return

        if self.root.current != 'tabla':
            return

        tabla = self.root.get_screen('tabla')
        lista = tabla.ids.lista_periodos
        lista.clear_widgets()

        programado = self.datos_actuales.get('programado', {})
        historial = self.datos_actuales.get('historial_real', {})

        # Período actual numérico
        try:
            p_actual = int(self.periodo_actual.replace('P', ''))
        except:
            p_actual = 0

        for i in range(1, 25):
            periodo = f'P{i}'
            desp = programado.get(periodo, '--')
            redesp = historial.get(periodo, desp)
            autorizacion = self.autorizaciones.get(i, '')

            item = PeriodoItem(
                periodo=periodo,
                despacho=str(desp) if desp != '--' else '--',
                redespacho=str(redesp) if redesp != '--' else '--',
                autorizacion=autorizacion,
                es_actual=(i == p_actual)
            )
            lista.add_widget(item)

    def desconectar(self):
        """Detiene el monitoreo y vuelve al login."""
        if self.buscador:
            self.buscador.detener()
            self.buscador = None

        self.datos_actuales = {}
        self.autorizaciones = {}
        self.estado_conexion = "Desconectado"
        self.root.current = 'login'

    def on_stop(self):
        """Limpieza al cerrar la app."""
        if self.buscador:
            self.buscador.detener()


if __name__ == '__main__':
    RioSogamosoApp().run()
