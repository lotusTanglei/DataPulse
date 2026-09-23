import io
import wave

from PIL import Image


def image_bytes(
    format: str = "PNG", color: str = "#14847c", size: tuple[int, int] = (32, 24)
) -> bytes:
    output = io.BytesIO()
    Image.new("RGB", size, color).save(output, format=format)
    return output.getvalue()


def wav_bytes(seconds: float = 0.25, rate: int = 16000) -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(rate)
        audio.writeframes(b"\x00\x00" * int(seconds * rate))
    return output.getvalue()
