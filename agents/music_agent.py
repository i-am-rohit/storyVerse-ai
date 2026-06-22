"""Music agent — Indian-inspired procedural background music."""

import io
import math
import struct
import wave
from dataclasses import dataclass


SAMPLE_RATE = 44100


@dataclass
class MusicResult:
    audio_bytes: bytes
    mood: str
    duration_seconds: float


class MusicAgent:
    """Generates ambient Indian-style background tracks as WAV bytes."""

    def compose(self, mood: str, duration_seconds: float) -> MusicResult:
        duration_seconds = max(5.0, float(duration_seconds))
        generators = {
            "indian_classical": self._indian_classical,
            "bollywood": self._bollywood,
            "sitar": self._sitar,
            "bansuri": self._bansuri,
            "tabla": self._tabla,
        }
        generator = generators.get(mood, self._indian_classical)
        samples = generator(duration_seconds)
        return MusicResult(
            audio_bytes=self._to_wav(samples),
            mood=mood,
            duration_seconds=duration_seconds,
        )

    def _to_wav(self, samples: list[float]) -> bytes:
        buffer = io.BytesIO()
        with wave.open(buffer, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            frames = b"".join(
                struct.pack("<h", max(-32767, min(32767, int(s * 32767))))
                for s in samples
            )
            wf.writeframes(frames)
        buffer.seek(0)
        return buffer.read()

    def _envelope(self, t: float, duration: float, attack: float = 1.5, release: float = 2.0) -> float:
        fade_in = min(1.0, t / attack)
        fade_out = min(1.0, (duration - t) / release)
        return fade_in * fade_out

    def _indian_classical(self, duration: float) -> list[float]:
        """Tanpura drone with slow raga-style notes (Sa Re Ga Ma Pa)."""
        n = int(SAMPLE_RATE * duration)
        notes = [261.63, 293.66, 329.63, 349.23, 392.00]  # C D E F G
        samples = []
        for i in range(n):
            t = i / SAMPLE_RATE
            env = self._envelope(t, duration)
            drone = 0.12 * math.sin(2 * math.pi * 130.81 * t) + 0.08 * math.sin(2 * math.pi * 196.0 * t)
            note_idx = int(t / 4) % len(notes)
            mel = 0.06 * math.sin(2 * math.pi * notes[note_idx] * t)
            shimmer = 0.02 * math.sin(2 * math.pi * 3.5 * t)
            samples.append((drone + mel + shimmer) * env)
        return samples

    def _bollywood(self, duration: float) -> list[float]:
        """Bright major-scale melody with rhythmic pulse."""
        n = int(SAMPLE_RATE * duration)
        scale = [261.63, 293.66, 329.63, 392.00, 440.00, 523.25]
        samples = []
        for i in range(n):
            t = i / SAMPLE_RATE
            env = self._envelope(t, duration, attack=0.8, release=1.5)
            beat = max(0, math.sin(2 * math.pi * 2 * t)) ** 3
            note = scale[int(t * 1.5) % len(scale)]
            melody = 0.1 * math.sin(2 * math.pi * note * t)
            pulse = 0.07 * beat * math.sin(2 * math.pi * 196 * t)
            samples.append((melody + pulse) * env)
        return samples

    def _sitar(self, duration: float) -> list[float]:
        """FM-modulated sitar-like tones with sympathetic resonance."""
        n = int(SAMPLE_RATE * duration)
        samples = []
        for i in range(n):
            t = i / SAMPLE_RATE
            env = self._envelope(t, duration)
            vibrato = 1 + 0.015 * math.sin(2 * math.pi * 5.5 * t)
            carrier = 220 * vibrato
            mod = 0.5 * math.sin(2 * math.pi * 3 * t)
            sitar = 0.11 * math.sin(2 * math.pi * carrier * t + mod * 4)
            sympathetic = 0.04 * math.sin(2 * math.pi * 440 * t) * math.sin(2 * math.pi * 0.5 * t)
            samples.append((sitar + sympathetic) * env)
        return samples

    def _bansuri(self, duration: float) -> list[float]:
        """Soft breathy flute melody."""
        n = int(SAMPLE_RATE * duration)
        notes = [392.0, 440.0, 493.88, 523.25, 587.33]
        samples = []
        for i in range(n):
            t = i / SAMPLE_RATE
            env = self._envelope(t, duration, attack=2.0, release=2.5)
            note = notes[int(t / 3) % len(notes)]
            breath = 0.5 + 0.5 * math.sin(2 * math.pi * 0.8 * t)
            flute = 0.1 * math.sin(2 * math.pi * note * t) * breath
            harmonic = 0.03 * math.sin(2 * math.pi * note * 2 * t)
            samples.append((flute + harmonic) * env)
        return samples

    def _tabla(self, duration: float) -> list[float]:
        """Gentle tabla-style rhythmic bed."""
        n = int(SAMPLE_RATE * duration)
        samples = []
        for i in range(n):
            t = i / SAMPLE_RATE
            env = self._envelope(t, duration, attack=0.5, release=1.0)
            # 4-beat cycle: bass, tap, tap, rest
            beat_pos = t % 1.0
            if beat_pos < 0.12:
                hit = math.exp(-beat_pos * 40) * math.sin(2 * math.pi * 120 * beat_pos)
            elif 0.25 < beat_pos < 0.35:
                hit = 0.6 * math.exp(-(beat_pos - 0.25) * 50) * math.sin(2 * math.pi * 200 * (beat_pos - 0.25))
            elif 0.5 < beat_pos < 0.58:
                hit = 0.5 * math.exp(-(beat_pos - 0.5) * 55) * math.sin(2 * math.pi * 250 * (beat_pos - 0.5))
            else:
                hit = 0
            pad = 0.03 * math.sin(2 * math.pi * 146.83 * t)
            samples.append((hit * 0.15 + pad) * env)
        return samples
