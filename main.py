import os
import uuid
import logging
from dotenv import load_dotenv
import ffmpeg
import whisper
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# Cargar variables de entorno
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Configuración de logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Carpeta temporal para archivos
TMP_FOLDER = "tmp"
if not os.path.exists(TMP_FOLDER):
    os.makedirs(TMP_FOLDER)

# Tamaño máximo permitido para el video (50 MB)
MAX_VIDEO_SIZE = 50 * 1024 * 1024  # bytes

# Estado del ConversationHandler
CHOOSING_MODEL = 1

def extraer_audio(video_path: str, audio_path: str) -> str:
    try:
        ffmpeg.input(video_path).output(audio_path, format="mp3").run(overwrite_output=True)
        logger.info(f"Audio extraído correctamente: {audio_path}")
        return audio_path
    except Exception as e:
        logger.error(f"Error al extraer audio: {e}")
        return None

def transcribir_audio(audio_path: str, model_choice: str) -> str:
    try:
        logger.info(f"Cargando modelo Whisper ({model_choice})...")
        model = whisper.load_model(model_choice)
        logger.info("Transcribiendo audio...")
        result = model.transcribe(audio_path)
        return result["text"]
    except Exception as e:
        logger.error(f"Error al transcribir: {e}")
        return None

# Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "¡Hola! Envía un video y te daré la transcripción.\n\nEl video debe pesar máximo 50 MB."
    )

# Comando /help: Envía una descripción de lo que hace el bot y cómo usarlo
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🤖 **Welcome to the Video Transcription Bot\!** 🎥➡️💬\n\n"
        "🔹 **How to use it:**\n"
        "1️⃣ Send a video \(up to 50 MB\) 📹.\n"
        "2️⃣ Choose the transcription model ⚙️:\n\n"
        "   • Large: High accuracy but slower 🏋️‍♂️\n"
        "   • Base: Recommended for most users ⚡\n"
        "   • Tiny: Fast but less accurate 🚀\n\n"
        "🔹 **To stop the current process:**\n"
        "   /cancel - Cancel the current process ❌\n\n"
        "🔹 **Receive your transcription:**\n"
        "   If it's too long \(over 4096 characters\), a text file will be sent 📄.\n\n"
        "📌 **Note:** Ensure your video is under 50 MB for smooth processing.\n\n"
    )
    await update.message.reply_text(help_text)


# Primer paso: Procesar el video y guardar el archivo temporal
async def procesar_video_init(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    video = await update.message.video.get_file()
    unique_id = uuid.uuid4().hex  # Genera un ID único
    video_path = os.path.join(TMP_FOLDER, f"video_{unique_id}.mp4")
    await video.download_to_drive(video_path)
    context.user_data["video_path"] = video_path

    # Verificar el tamaño del video
    if os.path.getsize(video_path) > MAX_VIDEO_SIZE:
        await update.message.reply_text("El video es demasiado grande. Envía un video de menos de 50 MB.")
        os.remove(video_path)
        return ConversationHandler.END

    # Enviar botones para elegir el modelo
    keyboard = [
        [InlineKeyboardButton("Large", callback_data="large")],
        [InlineKeyboardButton("Base (recommended)", callback_data="base")],
        [InlineKeyboardButton("Tiny", callback_data="tiny")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Elige el modelo de transcripción:", reply_markup=reply_markup)
    return CHOOSING_MODEL

# Segundo paso: Recibir la elección del modelo mediante botones y procesar la transcripción
async def choose_model(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()  # Responde para quitar el "loading"
    model_choice = query.data  # "large", "base" o "tiny"
    context.user_data["model_choice"] = model_choice
    await query.edit_message_text(f"Has elegido el modelo {model_choice}. Procesando video...")

    video_path = context.user_data.get("video_path")
    if not video_path or not os.path.exists(video_path):
        await query.edit_message_text("Error: no se encontró el archivo de video.")
        return ConversationHandler.END

    # Definir ruta para el audio
    base_filename = os.path.splitext(os.path.basename(video_path))[0]
    audio_path = os.path.join(TMP_FOLDER, f"{base_filename}.mp3")

    # Extraer audio
    audio_path = extraer_audio(video_path, audio_path)
    if not audio_path:
        await query.edit_message_text("Error al extraer el audio del video.")
        return ConversationHandler.END

    # Transcribir audio usando el modelo elegido
    transcription = transcribir_audio(audio_path, model_choice)
    if not transcription:
        await query.edit_message_text("Error al transcribir el audio.")
    else:
        if len(transcription) > 4096:
            # Enviar primer bloque y luego el resto en un archivo
            await query.edit_message_text(f"Transcripción (parcial):\n\n{transcription[:4096]}")
            transcripcion_filename = os.path.join(TMP_FOLDER, f"transcripcion_{base_filename}.txt")
            with open(transcripcion_filename, "w", encoding="utf-8") as f:
                f.write(transcription)
            await update.effective_message.reply_document(
                document=open(transcripcion_filename, "rb"),
                filename=f"transcripcion_{base_filename}.txt",
            )
            os.remove(transcripcion_filename)
        else:
            await query.edit_message_text(f"Transcripción completada:\n\n{transcription}")

    # Limpieza de archivos temporales
    if os.path.exists(video_path):
        os.remove(video_path)
    if os.path.exists(audio_path):
        os.remove(audio_path)

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Operación cancelada.")
    video_path = context.user_data.get("video_path")
    if video_path and os.path.exists(video_path):
        os.remove(video_path)
    return ConversationHandler.END

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.VIDEO, procesar_video_init)],
        states={
            CHOOSING_MODEL: [CallbackQueryHandler(choose_model)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(conv_handler)

    logger.info("El bot está funcionando...")
    app.run_polling()

if __name__ == "__main__":
    main()
