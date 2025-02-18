import whisper
import ffmpeg

def extraer_audio(video_path, audio_path="audio.mp3"):
    """
    Extrae el audio del video y lo guarda como un archivo MP3.
    """
    try:
        ffmpeg.input(video_path).output(audio_path, format='mp3').run(overwrite_output=True)
        print(f"Audio extraído correctamente: {audio_path}")
        return audio_path
    except Exception as e:
        print(f"Error al extraer audio: {e}")
        return None

def transcribir_audio(audio_path):
    """
    Transcribe el audio usando el modelo Whisper.
    """
    try:
        print("Cargando modelo Whisper (base)...")
        model = whisper.load_model("large")  # Cambiado a "large" para mayor precisión.
        print("Transcribiendo audio...")
        result = model.transcribe(audio_path)
        return result['text']
    except Exception as e:
        print(f"Error al transcribir: {e}")
        return None

if __name__ == "__main__":
    # Solicitar al usuario la ruta del video
    video_path = input("Introduce la ruta del video (ejemplo: video.mp4): ")
    
    # Extraer el audio del video
    audio_path = extraer_audio(video_path)
    
    if audio_path:
        # Transcribir el audio
        texto = transcribir_audio(audio_path)
        if texto:
            print("Transcripción completada:")
            print(texto)
            # Guardar la transcripción en un archivo de texto
            with open("transcripcion.txt", "w", encoding="utf-8") as f:
                f.write(texto)
            print("La transcripción se guardó en 'transcripcion.txt'.")
        else:
            print("No se pudo transcribir el audio.")
