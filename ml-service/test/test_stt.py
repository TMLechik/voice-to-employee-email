from pathlib import Path
import sys

ML_SERVICE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ML_SERVICE_DIR))

from ml_service import SpeechToTextService

def main() -> None:
    audio_path = ML_SERVICE_DIR / "samples" / "test_voice.mp3"

    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    
    stt = SpeechToTextService(model_size="base", device="cpu")

    text = stt.transcribe(audio_path=audio_path)

    print("Regonized text:")
    print(text)

if __name__ == "__main__":
    main()
