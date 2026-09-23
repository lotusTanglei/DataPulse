import asyncio
import io
import json
import subprocess
import sys

import pytest
from PIL import Image

from datapulse.screen.media import MediaInspector, MediaInvalid, MediaLimits, MediaUnavailable
from tests.support.media import image_bytes, wav_bytes

pytestmark = pytest.mark.anyio


async def test_images_are_decoded_and_thumbnails_have_no_source_metadata() -> None:
    inspected = await MediaInspector().inspect(image_bytes(size=(640, 480)), "image/png", ".png")
    assert inspected.metadata.validated
    assert (inspected.metadata.width, inspected.metadata.height) == (640, 480)
    with Image.open(io.BytesIO(inspected.thumbnail)) as thumbnail:
        assert thumbnail.size == (320, 240)
        assert "exif" not in thumbnail.info


@pytest.mark.parametrize(
    "mime,extension,content",
    [
        ("image/png", ".png", b"\x89PNG\r\n\x1a\nforged"),
        ("image/jpeg", ".jpg", image_bytes()),
        ("audio/wav", ".wav", b"RIFF\x00\x00\x00\x00WAVE"),
        ("audio/mpeg", ".mp3", b"ID3not-mp3"),
        ("video/mp4", ".mp4", b"\x00\x00\x00\x18ftypisomnot-mp4"),
        ("application/geo+json", ".geojson", b"[]"),
    ],
)
async def test_spoofed_or_mismatched_media_is_rejected(mime, extension, content) -> None:
    with pytest.raises(MediaInvalid):
        await MediaInspector().inspect(content, mime, extension)


async def test_pixel_and_duration_limits_apply_before_acceptance() -> None:
    inspector = MediaInspector(MediaLimits(max_pixels=100, max_duration_seconds=0.1))
    with pytest.raises(MediaInvalid, match="pixel"):
        await inspector.inspect(image_bytes(), "image/png", ".png")
    with pytest.raises(MediaInvalid, match="duration"):
        await inspector.inspect(wav_bytes(), "audio/wav", ".wav")


async def test_wav_metadata_comes_from_the_actual_audio_stream() -> None:
    inspected = await MediaInspector().inspect(wav_bytes(), "audio/wav", ".wav")
    assert inspected.metadata.duration_seconds == pytest.approx(0.25)
    assert inspected.metadata.channels == 1
    assert inspected.metadata.sample_rate == 16000
    assert inspected.metadata.audio_codec == "pcm_s16le"


@pytest.mark.parametrize(
    "mime,extension,codec,source",
    [
        ("audio/mpeg", ".mp3", ["-c:a", "libmp3lame"], "sine=frequency=440:sample_rate=16000"),
        ("audio/ogg", ".ogg", ["-c:a", "libopus"], "sine=frequency=440:sample_rate=16000"),
        (
            "video/mp4",
            ".mp4",
            ["-c:v", "libx264", "-pix_fmt", "yuv420p"],
            "color=c=0x14847c:s=64x48:r=10",
        ),
        ("video/webm", ".webm", ["-c:v", "libvpx-vp9"], "color=c=0x14847c:s=64x48:r=10"),
    ],
)
async def test_browser_codecs_are_probed_decoded_and_previewed(
    tmp_path, mime, extension, codec, source
) -> None:
    path = tmp_path / ("media" + extension)
    subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", source, "-t", "0.3", *codec, str(path)],
        check=True,
        timeout=20,
    )
    inspected = await MediaInspector().inspect(path.read_bytes(), mime, extension)
    assert inspected.metadata.duration_seconds > 0
    if mime.startswith("video"):
        assert inspected.metadata.width == 64
        assert inspected.metadata.height == 48
        assert inspected.thumbnail.startswith(b"\x89PNG")


async def test_audio_preview_is_transcoded_to_bounded_mp3_with_filters() -> None:
    tone = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=16000",
            "-t",
            "0.25",
            "-f",
            "wav",
            "pipe:1",
        ],
        check=True,
        capture_output=True,
        timeout=10,
    ).stdout
    preview, media_type = await MediaInspector().preview(
        tone,
        "audio/wav",
        ".wav",
        normalize_loudness=True,
        trim_silence=True,
    )
    assert media_type == "audio/mpeg"
    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=format_name:stream=codec_name,bit_rate",
            "-of",
            "json",
            "-",
        ],
        input=preview,
        check=True,
        capture_output=True,
        timeout=10,
    )
    payload = json.loads(probe.stdout)
    assert payload["format"]["format_name"] == "mp3"
    assert payload["streams"][0]["codec_name"] == "mp3"
    assert len(preview) < 20 * 1024 * 1024


async def test_preview_filter_and_encoding_arguments_are_explicit(monkeypatch) -> None:
    calls: list[tuple[tuple[str, ...], int]] = []

    async def capture(*command: str, output_limit: int = 0) -> bytes:
        calls.append((command, output_limit))
        return b"preview"

    inspector = MediaInspector()
    monkeypatch.setattr(inspector, "_run", capture)
    assert await inspector.preview(
        wav_bytes(),
        "audio/wav",
        ".wav",
        normalize_loudness=True,
        trim_silence=True,
    ) == (b"preview", "audio/mpeg")
    command, output_limit = calls[0]
    joined = " ".join(command)
    assert "loudnorm=I=-16:TP=-1.5:LRA=11" in joined
    assert "silenceremove=start_periods=1" in joined
    assert command[-5:] == ("-b:a", "64k", "-f", "mp3", "pipe:1")
    assert output_limit == 20 * 1024 * 1024


async def test_video_preview_is_scaled_and_encoded_as_low_bitrate_mp4(tmp_path) -> None:
    source = tmp_path / "source.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=0x14847c:s=1280x720:r=10",
            "-t",
            "0.5",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(source),
        ],
        check=True,
        timeout=20,
    )
    preview, media_type = await MediaInspector().preview(source.read_bytes(), "video/mp4", ".mp4")
    assert media_type == "video/mp4"
    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=format_name:stream=width,height,bit_rate,codec_name",
            "-of",
            "json",
            "-",
        ],
        input=preview,
        check=True,
        capture_output=True,
        timeout=10,
    )
    payload = json.loads(probe.stdout)
    stream = next(item for item in payload["streams"] if item["codec_name"] == "h264")
    assert (stream["width"], stream["height"]) == (640, 360)
    assert int(stream["bit_rate"]) <= 700_000
    assert payload["format"]["format_name"].split(",")[0] == "mov"


async def test_subtitle_timing_preserves_milliseconds_and_rejects_overlaps() -> None:
    inspector = MediaInspector()
    valid = (
        b"WEBVTT\n\n00:00:00.125 --> 00:00:01.250\nFirst sentence\n\n"
        b"00:00:01.250 --> 00:00:02.500\nSecond sentence\n"
    )
    inspected = await inspector.inspect(valid, "text/vtt", ".vtt")
    assert inspected.metadata.cues[0].start == 0.125
    assert inspected.metadata.cues[0].end == 1.25
    assert inspected.metadata.duration_seconds == 2.5
    with pytest.raises(MediaInvalid, match="overlapping"):
        await inspector.inspect(
            valid.replace(b"00:00:01.250 -->", b"00:00:01.000 -->"), "text/vtt", ".vtt"
        )


async def test_missing_processor_returns_a_stable_unavailable_error(monkeypatch) -> None:
    async def missing(*args, **kwargs):
        raise FileNotFoundError("private/path/ffprobe")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", missing)
    with pytest.raises(MediaUnavailable) as failure:
        await MediaInspector().inspect(wav_bytes(), "audio/wav", ".wav")
    assert "private/path" not in str(failure.value)


async def test_timed_out_media_process_is_killed_and_waited(monkeypatch) -> None:
    class Process:
        pid = 987654321
        returncode = None
        killed = False
        waited = False
        stdout = asyncio.StreamReader()
        stderr = asyncio.StreamReader()
        exited = asyncio.Event()

        def kill(self):
            self.killed = True
            self.stdout.feed_eof()
            self.stderr.feed_eof()
            self.exited.set()

        async def wait(self):
            await self.exited.wait()
            self.waited = True
            self.returncode = -9
            return self.returncode

    process = Process()
    monkeypatch.setattr("datapulse.screen.media.os.killpg", lambda pid, sig: process.kill())

    async def start(*args, **kwargs):
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", start)
    with pytest.raises(MediaInvalid, match="time limit"):
        await MediaInspector(MediaLimits(timeout_seconds=0.01)).inspect(
            wav_bytes(), "audio/wav", ".wav"
        )
    assert process.killed and process.waited


@pytest.mark.parametrize("stream", ["stdout", "stderr"])
async def test_processor_output_is_bounded_and_process_is_reaped(monkeypatch, stream) -> None:
    processes = []
    original_start = asyncio.create_subprocess_exec

    async def start(*args, **kwargs):
        process = await original_start(*args, **kwargs)
        processes.append(process)
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", start)
    with pytest.raises(MediaInvalid, match="output limit"):
        await MediaInspector()._run(
            sys.executable,
            "-c",
            f"import sys; stream = sys.{stream}.buffer\n"
            "while True: stream.write(b'x' * 65536); stream.flush()",
        )
    assert processes[0].returncode is not None


async def test_processor_cancellation_reaps_the_child(monkeypatch) -> None:
    processes = []
    started = asyncio.Event()
    original_start = asyncio.create_subprocess_exec

    async def start(*args, **kwargs):
        process = await original_start(*args, **kwargs)
        processes.append(process)
        started.set()
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", start)
    task = asyncio.create_task(
        MediaInspector()._run(sys.executable, "-c", "import time; time.sleep(30)")
    )
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert processes[0].returncode is not None


@pytest.mark.parametrize(
    "block",
    [
        "00:xx:01.000 --> 00:00:02.000\nBroken timing",
        "00:00:01.000 --> 00:00:02.000",
        "Misspelled cue\nThis must not silently disappear",
        "00:00:01.000 --> 00:00:02.000\nFirst\n00:00:02.000 --> 00:00:03.000\nSecond",
    ],
)
async def test_bad_subtitle_blocks_cannot_disappear_from_an_otherwise_valid_file(block) -> None:
    content = "WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nValid\n\n" + block
    with pytest.raises(MediaInvalid):
        await MediaInspector().inspect(content.encode(), "text/vtt", ".vtt")


async def test_subtitle_comments_styles_and_identifiers_are_supported() -> None:
    content = (
        b"WEBVTT\n\nNOTE Author comment\n\nSTYLE\n::cue { color: white; }\n\n"
        b"sentence-1\n00:00.125 --> 00:01.250 align:start\n<v Narrator>Hello</v>\n"
    )
    inspected = await MediaInspector().inspect(content, "text/vtt", ".vtt")
    assert inspected.metadata.cues[0].text == "Hello"
    assert inspected.metadata.cues[0].start == 0.125


async def test_cancelled_image_decode_reaps_child_before_releasing_slot(monkeypatch) -> None:
    inspector = MediaInspector(MediaLimits(concurrency=1))
    started = asyncio.Event()
    processes = []
    original = asyncio.create_subprocess_exec

    async def capture(*args, **kwargs):
        process = await original(*args, **kwargs)
        processes.append(process)
        started.set()
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", capture)
    task = asyncio.create_task(inspector.inspect(image_bytes(), "image/png", ".png"))
    try:
        await asyncio.wait_for(started.wait(), timeout=5)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    finally:
        if not task.done():
            task.cancel()
        await asyncio.gather(task, return_exceptions=True)
    assert processes[0].returncode is not None
    assert not inspector._slots.locked()
