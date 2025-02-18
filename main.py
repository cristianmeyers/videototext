import os
from dotenv import load_dotenv
import ffmpeg
import whisper
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# Cargar variables de entorno
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Función para extraer audio del video
def extraer_audio(video_path, audio_path="audio.mp3"):
    try:
        ffmpeg.input(video_path).output(audio_path, format='mp3').run(overwrite_output=True)
        print(f"Audio extraído correctamente: {audio_path}")
        return audio_path
    except Exception as e:
        print(f"Error al extraer audio: {e}")
        return None

# Función para transcribir el audio
def transcribir_audio(audio_path):
    try:
        print("Cargando modelo Whisper (large)...")
        model = whisper.load_model("large")
        print("Transcribiendo audio...")
        result = model.transcribe(audio_path)
        return result['text']
    except Exception as e:
        print(f"Error al transcribir: {e}")
        return None

# Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¡Hola! Envíame un video y lo transcribiré por ti.")

# Procesar mensajes de video
async def procesar_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensaje_procesando = await update.message.reply_text("Procesando tu video, esto puede tardar un momento...")
    video = await update.message.video.get_file()
    video_path = "video.mp4"
    audio_path = "audio.mp3"
    
    try:
        # Descargar el video
        await video.download_to_drive(video_path)
        # Extraer el audio
        audio_path = extraer_audio(video_path)
        if not audio_path:
            raise Exception("Error al extraer audio.")
        # Transcribir el audio
        texto = transcribir_audio(audio_path)
        if not texto:
            raise Exception("Error al transcribir el audio.")
        # Editar el mensaje con el resultado
        await mensaje_procesando.edit_text(f"Transcripción completada:\n\n{texto}")
    except Exception as e:
        await mensaje_procesando.edit_text(f"Hubo un error: {e}")
    finally:
        # Borrar archivos temporales
        if os.path.exists(video_path):
            os.remove(video_path)
        if os.path.exists(audio_path):
            os.remove(audio_path)

# Configuración del bot
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VIDEO, procesar_video))

    print("El bot está funcionando...")
    app.run_polling()

if __name__ == "__main__":
    main()
