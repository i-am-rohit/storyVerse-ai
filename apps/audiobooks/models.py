import io
import math
import struct
import wave

from django.conf import settings
from django.db import models


class Audiobook(models.Model):
    class VoiceGender(models.TextChoices):
        MALE = "male", "Male"
        FEMALE = "female", "Female"

    class AudioSource(models.TextChoices):
        ELEVENLABS = "elevenlabs", "ElevenLabs"
        DEMO = "demo", "Demo"

    class GenerationStatus(models.TextChoices):
        PROCESSING = "processing", "Processing"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="audiobooks",
    )
    story = models.ForeignKey(
        "stories.Story",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audiobooks",
    )
    title = models.CharField(max_length=255)
    voice_id = models.CharField(max_length=50)
    voice_name = models.CharField(max_length=100)
    voice_gender = models.CharField(max_length=10, choices=VoiceGender.choices)
    duration_seconds = models.PositiveIntegerField(default=0)
    music_style = models.CharField(max_length=30, default="none", blank=True)
    audio_file = models.FileField(upload_to="audio/", blank=True)
    background_music_file = models.FileField(upload_to="audio/music/", blank=True)
    audio_source = models.CharField(
        max_length=20,
        choices=AudioSource.choices,
        default=AudioSource.DEMO,
    )
    status = models.CharField(
        max_length=20,
        choices=GenerationStatus.choices,
        default=GenerationStatus.READY,
    )
    progress = models.PositiveSmallIntegerField(default=0)
    status_message = models.CharField(max_length=255, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    @property
    def cover_gradient(self):
        gradients = {
            "fantasy": ("#3b82f6", "#8b5cf6"),
            "adventure": ("#f59e0b", "#ef4444"),
            "mystery": ("#6366f1", "#1e1b4b"),
            "sci_fi": ("#06b6d4", "#3b82f6"),
            "fairy_tale": ("#ec4899", "#8b5cf6"),
            "historical": ("#78716c", "#44403c"),
            "humor": ("#22c55e", "#eab308"),
            "horror": ("#7f1d1d", "#1c1917"),
        }
        genre = self.story.genre if self.story else "fantasy"
        return gradients.get(genre, ("#1db954", "#191414"))


def generate_demo_wav(duration_seconds: int = 5, sample_rate: int = 44100) -> bytes:
    """Generate a demo WAV file with layered tones simulating narration rhythm."""
    num_samples = sample_rate * duration_seconds
    buffer = io.BytesIO()

    with wave.open(buffer, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)

        for i in range(num_samples):
            t = i / sample_rate
            beat = math.sin(2 * math.pi * 2 * t) * 0.5 + 0.5
            freq = 220 + 80 * math.sin(2 * math.pi * 0.3 * t)
            sample = (
                0.35 * math.sin(2 * math.pi * freq * t)
                + 0.15 * math.sin(2 * math.pi * (freq * 1.5) * t)
                + 0.1 * math.sin(2 * math.pi * (freq * 2) * t)
            ) * (0.3 + 0.7 * beat)
            sample *= min(1.0, t * 2) * min(1.0, (duration_seconds - t) * 2)
            wf.writeframes(struct.pack("<h", int(sample * 32767 * 0.6)))

    buffer.seek(0)
    return buffer.read()
