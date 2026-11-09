[app]
# Título de la aplicación
title = Rio Sogamoso

# Nombre del paquete
package.name = riosogamoso

# Dominio del paquete (para Android)
package.domain = com.isagen

# Código fuente
source.dir = .

# Archivos a incluir
source.include_exts = py,png,jpg,kv,atlas,json

# Versión
version = 1.0.0

# Requisitos de Python
requirements = python3,kivy==2.3.0,kivymd==1.2.0,pillow,certifi,requests

# Permisos de Android
android.permissions = INTERNET,ACCESS_NETWORK_STATE

# Orientación (portrait, landscape, all)
orientation = portrait

# Pantalla completa
fullscreen = 0

# API de Android (mínima y target)
android.minapi = 21
android.api = 33
android.ndk = 25b

# Arquitecturas a compilar
android.archs = arm64-v8a,armeabi-v7a

# Modo de release o debug
android.release_artifact = apk

# Presplash y icono (crear estos archivos)
# presplash.filename = %(source.dir)s/data/presplash.png
# icon.filename = %(source.dir)s/data/icon.png

# Configuración de log
log_level = 2

# Avisos
warn_on_root = 1

[buildozer]
# Directorio de build
build_dir = ./.buildozer

# Directorio de bin (donde queda el APK)
bin_dir = ./bin
