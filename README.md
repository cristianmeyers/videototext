# Telegram Video Transcription Bot

Este es un bot de Telegram que permite a los usuarios enviar un video, y el bot extraerá el audio del video, lo transcribirá a texto utilizando el modelo Whisper de OpenAI, y devolverá la transcripción al usuario.

## Funcionalidades

- **Extracción de audio**: El bot extrae el audio del video enviado por el usuario.
- **Transcripción**: Utiliza el modelo Whisper para convertir el audio extraído a texto.
- **Manejo de archivos grandes**: El bot verifica si el video excede un tamaño permitido (por defecto 50MB) y notifica al usuario si el video es demasiado grande.
- **Respuestas**: Si la transcripción es demasiado larga, el bot la envía en partes o como un archivo de texto.
- **Archivos temporales**: Los archivos de video y audio se eliminan después de procesarlos.

## Requisitos

Antes de ejecutar el bot, asegúrate de tener los siguientes paquetes instalados:

- **Python 3.8+**
- **ffmpeg**
- **whisper**
- **python-dotenv**
- **python-telegram-bot**
- **moviepy**
- **SpeechRecognition**

Puedes instalar las dependencias necesarias ejecutando:

```bash
pip install -r requirements.txt
```

## Uso

1. Clona el repositorio o descarga los archivos.

2. Crea un archivo `.env` en la raíz del proyecto con tu **TOKEN** del bot de Telegram:

```ini
TELEGRAM_BOT_TOKEN="TU_TOKEN_AQUI"
```
