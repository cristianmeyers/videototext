import os
import uuid
import logging
import asyncio
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
        "Hello! Send a video, and I'll provide you with the transcription.\n\nThe video must be a maximum of 50 MB."
    )

# Comando /help: Envía una descripción de cómo usar el bot
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🤖 <b>Welcome to the Video Transcription Bot!</b> 🎥➡️💬\n\n"
        "🔹 <b>How to use it:</b>\n\n"
        "1️⃣ Send a video (up to 50 MB) 📹.\n\n"
        "2️⃣ Choose the transcription model ⚙️:\n\n"
        "   • <b>Large:</b> High accuracy but slower 🏋️‍♂️\n"
        "   • <b>Base:</b> Recommended for most users ⚡\n"
        "   • <b>Tiny:</b> Fast but less accurate 🚀\n\n"
        "🔹 <b>To stop the current process:</b>\n"
        "   /cancel - Cancel the current process ❌\n\n"
        "🔹 <b>Receive your transcription:</b>\n\n"
        "   If it's over 4096 characters, a text file will be sent 📄.\n\n"
        "📌 <b>Note:</b> Ensure your video is under 50 MB for smooth processing.\n"
    )
    await update.message.reply_text(help_text, parse_mode="HTML")

# Comando /about: Envía información sobre el bot
async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Comando /about recibido")
    about_text = (
        "🤖 <b>About the Video Transcription Bot</b> 🎥➡️💬\n\n"
        "This bot transcribes videos you send into text effortlessly. 📄✨\n\n"
        "🔹 <b>Features:</b>\n"
        "   • Transcribe videos up to 50 MB.\n"
        "   • Choose from three transcription models:\n"
        "      - Large: High accuracy but slower 🏋️‍♂️.\n"
        "      - Base: Recommended for most users ⚡.\n"
        "      - Tiny: Fast but less accurate 🚀.\n\n"
        "🔹 <b>Developer:</b>\n"
        "   Created by Criss with ❤️ using AI.\n\n"
        "🔗 <b>GitHub Repository:</b>\n"
        "   <a href='https://github.com/cristianmeyers'>github.com/cristianmeyers</a>\n\n"
        "📩 For feedback or suggestions, feel free to contact the developer!"
    )
    await update.message.reply_text(about_text, parse_mode="HTML", disable_web_page_preview=True)

# Función para procesar la transcripción en una tarea asíncrona
async def process_transcription(video_path: str, model_choice: str) -> str:
    base_filename = os.path.splitext(os.path.basename(video_path))[0]
    audio_path = os.path.join(TMP_FOLDER, f"{base_filename}.mp3")
    audio_path = extraer_audio(video_path, audio_path)
    if not audio_path:
        raise Exception("Error al extraer el audio del video.")
    transcription = transcribir_audio(audio_path, model_choice)
    if os.path.exists(audio_path):
        os.remove(audio_path)
    return transcription

# Primer paso: Procesar el video y guardar el archivo temporal, luego solicitar modelo
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

# Segundo paso: Recibir la elección del modelo y comenzar la tarea de transcripción
async def choose_model(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()  # Responde para quitar el "loading"
    model_choice = query.data  # "large", "base" o "tiny"
    context.user_data["model_choice"] = model_choice
    await query.edit_message_text(f"Has elegido el modelo {model_choice}. Processing video...")

    video_path = context.user_data.get("video_path")
    if not video_path or not os.path.exists(video_path):
        await query.edit_message_text("Error: no se encontró el archivo de video.")
        return ConversationHandler.END


    # Crear una tarea asíncrona para la transcripción, utilizando asyncio.to_thread
    transcription_task = asyncio.create_task(
        asyncio.to_thread(transcribir_audio, video_path, model_choice)
    )
    context.user_data["transcription_task"] = transcription_task

    try:
        # Esperar el resultado de la transcripción
        transcription = await transcription_task
        if not transcription:
            await query.edit_message_text("Error al transcribir el audio.")
        else:
            base_filename = os.path.splitext(os.path.basename(video_path))[0]
            if len(transcription) > 4096:
                # Enviar una parte y el resto en un archivo
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
    except asyncio.CancelledError:
        # Notificar al usuario que el proceso fue cancelado
        await query.edit_message_text("El proceso ha sido cancelado.")
    except Exception as e:
        # Manejar errores durante la transcripción
        await query.edit_message_text(f"Hubo un error: {e}")
    finally:
        # Limpieza de archivos temporales
        if os.path.exists(video_path):
            os.remove(video_path)
        context.user_data.pop("transcription_task", None)
    return ConversationHandler.END

# Comando /cancel para detener el proceso actual sin finalizar la conversación permanentemente
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Notificar inmediatamente al usuario
    await update.message.reply_text("Cancellation requested. Stopping process...")
    
    # Ejecutar la cancelación en una tarea separada para no bloquear la respuesta
    asyncio.create_task(_cancel_process(update, context))
    
    return ConversationHandler.END

async def _cancel_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Intentar cancelar la tarea de transcripción si existe
    transcription_task = context.user_data.get("transcription_task")
    if transcription_task:
        transcription_task.cancel()
        try:
            await transcription_task
        except asyncio.CancelledError:
            pass

    # Actualizar el mensaje de procesamiento (si se guardó)
    processing_message_id = context.user_data.get("processing_message_id")
    if processing_message_id:
        try:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=processing_message_id,
                text="Process canceled successfully."
            )
        except Exception as e:
            logger.error(f"Error updating processing message: {e}")

    # Limpiar archivos temporales
    video_path = context.user_data.get("video_path")
    if video_path and os.path.exists(video_path):
        os.remove(video_path)


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
    app.add_handler(CommandHandler("about", about_command))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(conv_handler)

    logger.info("El bot está funcionando...")
    app.run_polling()

if __name__ == "__main__":
    main()
