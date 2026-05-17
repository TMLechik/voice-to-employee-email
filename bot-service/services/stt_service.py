from __future__ import annotations

from pathlib import Path

from faster_whisper import WhisperModel

class SpeechToTextService:
    def __init__(self, model_size: str = "base", device: str = "cpu") -> None:
        self.model = WhisperModel(model_size, device=device, compute_type="int8")

    def transcribe(self,audio_path: Path) -> str:
        segments, _info = self.model.transcribe(
            str(audio_path),
            language="ru",
            vad_filter=True,
        )

        text_parts = [segment.text.strip() for segment in segments]
        return " ".join(part for part in text_parts if part).strip()