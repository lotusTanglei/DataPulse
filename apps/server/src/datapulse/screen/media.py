import asyncio
import base64
import io
import json
import math
import os
import signal
import warnings
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory

import webvtt
from PIL import Image, ImageOps, UnidentifiedImageError
from webvtt.models import Caption, Style
from webvtt.utils import iter_blocks_of_lines
from webvtt.vtt import parse_item

from datapulse.contracts.screen_asset import AssetMediaMetadata, SubtitleCue
from datapulse.operations.process_runner import bounded_command, processor_environment
from datapulse.operations.processing import (
    ProcessorBusy,
    ProcessorFailed,
    ProcessorInputInvalid,
    run_json_worker,
)


class MediaInvalid(ValueError):
    code = "ASSET_INVALID"


class MediaUnavailable(ValueError):
    code = "ASSET_PROCESSOR_UNAVAILABLE"


class MediaBusy(ValueError):
    code = "ASSET_PROCESSOR_BUSY"


@dataclass(frozen=True)
class MediaLimits:
    max_pixels: int = 33_554_432
    max_duration_seconds: float = 300
    timeout_seconds: float = 30
    concurrency: int = 2


@dataclass(frozen=True)
class InspectedMedia:
    metadata: AssetMediaMetadata
    thumbnail: bytes | None = None


class MediaInspector:
    def __init__(self, limits: MediaLimits | None = None) -> None:
        self.limits = limits or MediaLimits()
        self._slots = asyncio.Semaphore(self.limits.concurrency)

    async def inspect(self, content: bytes, mime_type: str, extension: str) -> InspectedMedia:
        try:
            await asyncio.wait_for(self._slots.acquire(), timeout=1)
        except TimeoutError as error:
            raise MediaBusy("Media processing is busy. Retry shortly.") from error
        try:
            if mime_type.startswith("image/"):
                return await self._image_process(content, mime_type)
            if mime_type in {"application/json", "application/geo+json"}:
                try:
                    payload = json.loads(content)
                except (ValueError, UnicodeDecodeError, RecursionError) as error:
                    raise MediaInvalid("The file is not valid GeoJSON.") from error
                if (
                    not isinstance(payload, dict)
                    or payload.get("type") != "FeatureCollection"
                    or not isinstance(payload.get("features"), list)
                ):
                    raise MediaInvalid("GeoJSON must be a FeatureCollection.")
                return InspectedMedia(AssetMediaMetadata(validated=True))
            if mime_type == "text/vtt":
                return self._subtitles(content)
            return await self._av(content, mime_type, extension)
        finally:
            self._slots.release()

    async def _image_process(self, content: bytes, mime_type: str) -> InspectedMedia:
        with TemporaryDirectory(prefix="datapulse-image-") as temporary:
            stage = Path(temporary).resolve()
            path = stage / "input"
            path.write_bytes(content)
            path.chmod(0o600)
            try:
                result = await run_json_worker(
                    {
                        "operation": "image",
                        "path": str(path),
                        "mime_type": mime_type,
                        "max_pixels": self.limits.max_pixels,
                    },
                    directory=stage,
                    timeout_seconds=self.limits.timeout_seconds,
                )
                return InspectedMedia(
                    AssetMediaMetadata.model_validate(result["metadata"]),
                    base64.b64decode(result["thumbnail"], validate=True),
                )
            except ProcessorBusy as error:
                raise MediaBusy("Image processing is busy. Retry shortly.") from error
            except ProcessorInputInvalid as error:
                raise MediaInvalid(str(error)) from error
            except ProcessorFailed as error:
                raise MediaUnavailable("Image processing failed or exceeded its limits.") from error
            except (ValueError, KeyError) as error:
                raise MediaInvalid("The image processor returned invalid output.") from error

    def _image(self, content: bytes, mime_type: str) -> InspectedMedia:
        expected = {"image/png": "PNG", "image/jpeg": "JPEG", "image/webp": "WEBP"}[mime_type]
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(content)) as image:
                    if image.format != expected:
                        raise MediaInvalid("Image content does not match its MIME type.")
                    width, height = image.size
                    if width * height > self.limits.max_pixels:
                        raise MediaInvalid("The image exceeds the pixel limit.")
                    if getattr(image, "n_frames", 1) != 1:
                        raise MediaInvalid(
                            "Animated images are not supported. Upload a video instead."
                        )
                    image.verify()
                with Image.open(io.BytesIO(content)) as image:
                    image.load()
                    has_alpha = "A" in image.getbands() or "transparency" in image.info
                    preview = ImageOps.exif_transpose(image).convert("RGBA" if has_alpha else "RGB")
                    preview.thumbnail((320, 320))
                    output = io.BytesIO()
                    preview.save(output, format="PNG")
            return InspectedMedia(
                AssetMediaMetadata(
                    validated=True,
                    width=width,
                    height=height,
                    has_alpha=has_alpha,
                    thumbnail_size_bytes=len(output.getvalue()),
                ),
                output.getvalue(),
            )
        except (
            UnidentifiedImageError,
            OSError,
            SyntaxError,
            Image.DecompressionBombError,
            Image.DecompressionBombWarning,
            ValueError,
        ) as error:
            if isinstance(error, MediaInvalid):
                raise
            raise MediaInvalid("The image cannot be decoded.") from error

    def _subtitles(self, content: bytes) -> InspectedMedia:
        try:
            lines = content.decode("utf-8-sig").splitlines()
            if not lines or not (
                lines[0] == "WEBVTT" or lines[0].startswith(("WEBVTT ", "WEBVTT\t"))
            ):
                raise MediaInvalid("The subtitle file must begin with a WebVTT header.")
            blocks = iter_blocks_of_lines(lines)
            header = next(blocks)
            if len(header) != 1 or "-->" in header[0]:
                raise MediaInvalid("Separate the WebVTT header and each cue with a blank line.")
            cues = []
            previous_end = 0.0
            # The library deliberately ignores unknown blocks; uploads must not lose cues silently.
            for block in blocks:
                if block[0] == "NOTE" or block[0].startswith(("NOTE ", "NOTE\t")):
                    continue
                caption = parse_item(block)
                if isinstance(caption, Style):
                    continue
                if not isinstance(caption, Caption) or sum("-->" in line for line in block) != 1:
                    raise MediaInvalid(
                        "The subtitle file contains a malformed or unsupported block."
                    )
                start = float(caption.start_in_seconds)
                end = float(caption.end_in_seconds)
                start += caption.start_time.milliseconds / 1000
                end += caption.end_time.milliseconds / 1000
                if start < previous_end or end <= start or end > self.limits.max_duration_seconds:
                    raise MediaInvalid(
                        "Subtitle cues must be ordered, non-overlapping "
                        "and within the duration limit."
                    )
                cues.append(SubtitleCue(start=start, end=end, text=caption.text.strip()))
                previous_end = end
            if not cues or len(cues) > 500:
                raise MediaInvalid("A subtitle file must contain between 1 and 500 cues.")
            return InspectedMedia(
                AssetMediaMetadata(validated=True, duration_seconds=previous_end, cues=tuple(cues))
            )
        except (
            ValueError,
            UnicodeDecodeError,
            webvtt.errors.MalformedFileError,
            webvtt.errors.MalformedCaptionError,
        ) as error:
            if isinstance(error, MediaInvalid):
                raise
            raise MediaInvalid("The subtitle file must be valid UTF-8 WebVTT.") from error

    async def _run(self, *command: str, output_limit: int = 2 * 1024 * 1024) -> bytes:
        try:
            process = await asyncio.create_subprocess_exec(
                *bounded_command(
                    list(command), cpu_seconds=max(1, math.ceil(self.limits.timeout_seconds))
                ),
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=processor_environment(),
                start_new_session=True,
            )
        except FileNotFoundError as error:
            raise MediaUnavailable(
                "FFmpeg and FFprobe are required for audio/video uploads."
            ) from error

        async def read_output(stream: asyncio.StreamReader) -> bytes:
            output = bytearray()
            while chunk := await stream.read(65536):
                if len(output) + len(chunk) > output_limit:
                    raise MediaInvalid("Media processing exceeded its output limit.")
                output.extend(chunk)
            return bytes(output)

        async def drain(stream: asyncio.StreamReader) -> None:
            while await stream.read(65536):
                pass

        assert process.stdout is not None and process.stderr is not None
        tasks = [
            asyncio.create_task(read_output(process.stdout)),
            asyncio.create_task(read_output(process.stderr)),
            asyncio.create_task(process.wait()),
        ]
        try:
            output, _, returncode = await asyncio.wait_for(
                asyncio.gather(*tasks), timeout=self.limits.timeout_seconds
            )
            if returncode in {126, 127}:
                raise MediaUnavailable("FFmpeg and FFprobe are required for audio/video uploads.")
            if returncode:
                raise MediaInvalid("The media cannot be decoded with a supported browser codec.")
            return output
        except BaseException:
            if process.returncode is None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            # Drain bounded pipe buffers after termination so wait() cannot deadlock.
            await asyncio.gather(drain(process.stdout), drain(process.stderr), process.wait())
            raise

    async def _av(self, content: bytes, mime_type: str, extension: str) -> InspectedMedia:
        demuxer = {
            "audio/mpeg": "mp3",
            "audio/ogg": "ogg",
            "audio/wav": "wav",
            "video/mp4": "mov",
            "video/webm": "matroska",
        }[mime_type]
        try:
            with TemporaryDirectory(prefix="datapulse-media-") as directory:
                source = Path(directory) / ("source" + extension)
                source.write_bytes(content)
                input_args = ["-protocol_whitelist", "file,pipe", "-f", demuxer]
                if demuxer == "mov":
                    input_args += ["-enable_drefs", "0", "-use_absolute_path", "0"]
                probed = await self._run(
                    "ffprobe",
                    "-v",
                    "error",
                    "-max_alloc",
                    "67108864",
                    *input_args,
                    "-show_entries",
                    "format=duration,format_name:stream=codec_type,codec_name,width,height,pix_fmt,sample_rate,channels,avg_frame_rate:stream_tags=alpha_mode",
                    "-of",
                    "json",
                    str(source),
                )
                payload = json.loads(probed)
                streams = payload.get("streams", [])
                video = [stream for stream in streams if stream.get("codec_type") == "video"]
                audio = [stream for stream in streams if stream.get("codec_type") == "audio"]
                if len(video) > 1 or len(audio) > 1 or len(streams) > len(video) + len(audio):
                    raise MediaInvalid("Only one video track and one audio track are supported.")
                if mime_type.startswith("audio/") and (video or len(audio) != 1):
                    raise MediaInvalid("An audio upload must contain one audio track and no video.")
                if mime_type.startswith("video/") and len(video) != 1:
                    raise MediaInvalid("A video upload must contain one video track.")
                duration = float(payload.get("format", {}).get("duration", 0))
                if (
                    not math.isfinite(duration)
                    or not 0 < duration <= self.limits.max_duration_seconds
                ):
                    raise MediaInvalid(
                        "The media duration is missing or exceeds the configured limit."
                    )
                values: dict[str, object] = {"validated": True, "duration_seconds": duration}
                if video:
                    track = video[0]
                    allowed = {"h264"} if mime_type == "video/mp4" else {"vp8", "vp9"}
                    if track.get("codec_name") not in allowed:
                        raise MediaInvalid(
                            "Use H.264 in MP4 or VP8/VP9 in WebM for browser playback."
                        )
                    width, height = int(track.get("width", 0)), int(track.get("height", 0))
                    if width <= 0 or height <= 0 or width * height > self.limits.max_pixels:
                        raise MediaInvalid("The video exceeds the pixel limit.")
                    frame_rate = float(Fraction(track.get("avg_frame_rate", "0/1")))
                    if not 0 < frame_rate <= 120:
                        raise MediaInvalid("The video frame rate must be between 0 and 120 FPS.")
                    values.update(
                        width=width,
                        height=height,
                        frame_rate=frame_rate,
                        video_codec=track["codec_name"],
                        has_alpha="a" in track.get("pix_fmt", "").replace("gray", "")
                        or str(track.get("tags", {}).get("alpha_mode")) == "1",
                    )
                if audio:
                    track = audio[0]
                    allowed = {
                        "audio/mpeg": {"mp3"},
                        "audio/wav": {"pcm_s16le", "pcm_s24le", "pcm_f32le"},
                        "audio/ogg": {"vorbis", "opus"},
                        "video/mp4": {"aac", "mp3"},
                        "video/webm": {"vorbis", "opus"},
                    }[mime_type]
                    rate, channels = int(track.get("sample_rate", 0)), int(track.get("channels", 0))
                    if (
                        track.get("codec_name") not in allowed
                        or not 8000 <= rate <= 96000
                        or not 1 <= channels <= 2
                    ):
                        raise MediaInvalid("Use a supported mono/stereo audio codec at 8-96 kHz.")
                    values.update(
                        audio_codec=track["codec_name"], sample_rate=rate, channels=channels
                    )
                # Decode the full file with bounded dimensions, duration, threads and wall time.
                await self._run(
                    "ffmpeg",
                    "-v",
                    "error",
                    "-xerror",
                    "-max_alloc",
                    "67108864",
                    "-threads",
                    "1",
                    *input_args,
                    "-err_detect",
                    "explode",
                    "-i",
                    str(source),
                    "-map",
                    "0:v?",
                    "-map",
                    "0:a?",
                    "-threads",
                    "1",
                    "-f",
                    "null",
                    "-",
                )
                thumbnail = None
                if video:
                    thumbnail = await self._run(
                        "ffmpeg",
                        "-v",
                        "error",
                        "-threads",
                        "1",
                        *input_args,
                        "-i",
                        str(source),
                        "-frames:v",
                        "1",
                        "-vf",
                        "scale=320:320:force_original_aspect_ratio=decrease",
                        "-threads",
                        "1",
                        "-f",
                        "image2pipe",
                        "-c:v",
                        "png",
                        "-",
                    )
                values["thumbnail_size_bytes"] = len(thumbnail or b"")
                return InspectedMedia(AssetMediaMetadata.model_validate(values), thumbnail)
        except TimeoutError as error:
            raise MediaInvalid("Media decoding exceeded its time limit.") from error
        except (ValueError, KeyError, TypeError, ZeroDivisionError) as error:
            if isinstance(error, (MediaInvalid, MediaUnavailable)):
                raise
            raise MediaInvalid("The media metadata is invalid.") from error

    async def preview(
        self,
        content: bytes,
        mime_type: str,
        extension: str,
        *,
        normalize_loudness: bool = False,
        trim_silence: bool = False,
    ) -> tuple[bytes, str]:
        """Create a bounded, transient preview without modifying the stored asset."""
        if not mime_type.startswith(("audio/", "video/")):
            raise MediaInvalid("Only audio and video assets support transformed previews.")
        with TemporaryDirectory(prefix="datapulse-preview-") as directory:
            source = Path(directory) / ("source" + extension)
            source.write_bytes(content)
            filters: list[str] = []
            if normalize_loudness:
                filters.append("loudnorm=I=-16:TP=-1.5:LRA=11")
            if trim_silence:
                filters.append(
                    "silenceremove=start_periods=1:start_duration=0.15:start_threshold=-45dB:"
                    "stop_periods=1:stop_duration=0.25:stop_threshold=-45dB"
                )
            if mime_type.startswith("audio/"):
                command = [
                    "ffmpeg",
                    "-v",
                    "error",
                    "-threads",
                    "1",
                    "-i",
                    str(source),
                    "-vn",
                ]
                if filters:
                    command.extend(["-af", ",".join(filters)])
                command.extend(["-c:a", "libmp3lame", "-b:a", "64k", "-f", "mp3", "pipe:1"])
                return await self._run(*command, output_limit=20 * 1024 * 1024), "audio/mpeg"
            command = [
                "ffmpeg",
                "-v",
                "error",
                "-threads",
                "1",
                "-i",
                str(source),
                "-vf",
                "scale=640:-2",
            ]
            if filters:
                command.extend(["-af", ",".join(filters)])
            command.extend(
                [
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-b:v",
                    "600k",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "96k",
                    "-movflags",
                    "frag_keyframe+empty_moov",
                    "-f",
                    "mp4",
                    "pipe:1",
                ]
            )
            return await self._run(*command, output_limit=20 * 1024 * 1024), "video/mp4"
