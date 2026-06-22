"""Mix narration WAV with background music (pure Python, no ffmpeg)."""

import io
import struct
import wave


def pcm_to_wav(pcm: bytes, sample_rate: int = 44100, channels: int = 1, sample_width: int = 2) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm)
    buffer.seek(0)
    return buffer.read()


def wav_duration_seconds(wav_bytes: bytes) -> float:
    with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
        return wf.getnframes() / float(wf.getframerate())


def _read_wav(wav_bytes: bytes) -> tuple[list[int], int, int]:
    with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
        if wf.getsampwidth() != 2:
            raise ValueError("Only 16-bit WAV is supported.")
        channels = wf.getnchannels()
        rate = wf.getframerate()
        frames = wf.readframes(wf.getnframes())

    samples = list(struct.unpack(f"<{len(frames) // 2}h", frames))
    if channels == 2:
        samples = [(samples[i] + samples[i + 1]) // 2 for i in range(0, len(samples), 2)]
    return samples, rate, 1


def _write_wav(samples: list[int], sample_rate: int) -> bytes:
    clipped = [max(-32767, min(32767, int(s))) for s in samples]
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f"<{len(clipped)}h", *clipped))
    buffer.seek(0)
    return buffer.read()


def _loop_samples(samples: list[int], target_len: int) -> list[int]:
    if not samples:
        return [0] * target_len
    out = []
    while len(out) < target_len:
        out.extend(samples)
    return out[:target_len]


def mix_voice_and_music(
    voice_wav: bytes,
    music_wav: bytes,
    music_volume: float = 0.22,
) -> bytes:
    """Overlay background music under narration."""
    voice_samples, voice_rate, _ = _read_wav(voice_wav)
    music_samples, music_rate, _ = _read_wav(music_wav)

    if music_rate != voice_rate:
        ratio = voice_rate / music_rate
        music_samples = [
            music_samples[min(int(i / ratio), len(music_samples) - 1)]
            for i in range(int(len(music_samples) * ratio))
        ]

    music_samples = _loop_samples(music_samples, len(voice_samples))
    mixed = [
        int(v + m * music_volume * 32767)
        for v, m in zip(voice_samples, music_samples, strict=False)
    ]
    return _write_wav(mixed, voice_rate)
