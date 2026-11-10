[app]
# Título de la aplicación
title = Rio Sogamoso

# Nombre del paquete
package.name = riosogamoso

# Dominio del paquete (para Android)
package.domain = com.isagen

# Código fuente
source.dir = .

# Archivos a incluir (incluyendo servicios)
source.include_exts = py,png,jpg,kv,atlas,json
source.include_patterns = services/*.py

# Excluir archivos innecesarios
source.exclude_dirs = __pycache__,.git,.github,bin,.buildozer
source.exclude_patterns = *.pyc,*.pyo,*.json

# Versión
version = 1.0.0

# Requisitos de Python - versiones específicas que funcionan
requirements = python3,kivy==2.2.1,kivymd==1.1.1,pillow,certifi,requests,urllib3,charset-normalizer,idna

# Permisos de Android
android.permissions = INTERNET,ACCESS_NETWORK_STATE

# Orientación (portrait, landscape, all)
orientation = portrait

# Pantalla completa
fullscreen = 0

# API de Android
android.minapi = 21
android.api = 33
android.ndk = 25b

# Arquitecturas - arm64 para dispositivos modernos
android.archs = arm64-v8a

# Aceptar licencias automáticamente
android.accept_sdk_license = True

# Gradle específico
android.gradle_dependencies =

# Skip update para evitar problemas
android.skip_update = False

# Bootstrap
p4a.bootstrap = sdl2

# Configuración de log
log_level = 2

# Avisos
warn_on_root = 1

[buildozer]
# Directorio de build
build_dir = ./.buildozer

# Directorio de bin (donde queda el APK)
bin_dir = ./bin
