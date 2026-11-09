# Río Sogamoso - App Móvil

Aplicación móvil nativa para monitoreo de despacho/redespacho de la central Sogamoso.
Se conecta directamente al FTP de XM desde el celular.

## Estructura del proyecto

```
Modulo_RioSogamoso_Kivy/
├── main.py              # Aplicación principal
├── config.py            # Configuración
├── riosogamoso.kv       # Interfaz (KV language)
├── buildozer.spec       # Configuración para compilar APK
├── requirements.txt     # Dependencias Python
└── services/
    └── ftp_service.py   # Servicio de conexión a XM
```

## Requisitos

### Para desarrollo (Windows)
```bash
pip install -r requirements.txt
```

### Para compilar APK (Linux o WSL)
```bash
pip install buildozer
sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 cmake libffi-dev libssl-dev
```

## Ejecutar en Windows (desarrollo)

```bash
cd Modulo_RioSogamoso_Kivy
python main.py
```

## Compilar APK (Linux/WSL)

1. Instalar buildozer:
```bash
pip install buildozer cython
```

2. Compilar:
```bash
cd Modulo_RioSogamoso_Kivy
buildozer android debug
```

3. El APK queda en `bin/riosogamoso-1.0.0-arm64-v8a-debug.apk`

## Compilar con Google Colab (alternativa)

Si no tienes Linux, puedes usar Google Colab:

1. Sube los archivos a Google Drive
2. Abre un notebook de Colab
3. Ejecuta:
```python
!pip install buildozer cython
!sudo apt install -y ...  # (dependencias)
%cd /content/drive/MyDrive/Modulo_RioSogamoso_Kivy
!buildozer android debug
```

## Notas

- Las credenciales de XM se guardan en el almacenamiento local del celular
- Requiere conexión a internet para acceder al FTP de XM
- La app funciona en Android 5.0+ (API 21+)
