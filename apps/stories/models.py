from django.conf import settings
from django.db import models


class Story(models.Model):
    class Language(models.TextChoices):
        ENGLISH = "en", "English"
        SPANISH = "es", "Spanish"
        FRENCH = "fr", "French"
        HINDI = "hi", "Hindi"
        GERMAN = "de", "German"
        JAPANESE = "ja", "Japanese"

    class Genre(models.TextChoices):
        FANTASY = "fantasy", "Fantasy"
        ADVENTURE = "adventure", "Adventure"
        MYSTERY = "mystery", "Mystery"
        SCI_FI = "sci_fi", "Science Fiction"
        FAIRY_TALE = "fairy_tale", "Fairy Tale"
        HISTORICAL = "historical", "Historical"
        HUMOR = "humor", "Humor"
        HORROR = "horror", "Horror"

    class AgeGroup(models.TextChoices):
        TODDLER = "3-5", "3–5 years"
        CHILD = "6-8", "6–8 years"
        PRETEEN = "9-12", "9–12 years"
        TEEN = "13-17", "13–17 years"
        ADULT = "18+", "18+ years"

    class StoryLength(models.TextChoices):
        SHORT = "short", "Short (~150 words)"
        MEDIUM = "medium", "Medium (~350 words)"
        LONG = "long", "Long (~600 words)"
        EXTRA_LONG = "extra_long", "Extra Long (~1,000 words)"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="stories",
    )
    title = models.CharField(max_length=255)
    content = models.TextField()
    moral = models.TextField(blank=True)
    language = models.CharField(max_length=10, choices=Language.choices, default=Language.ENGLISH)
    genre = models.CharField(max_length=20, choices=Genre.choices, default=Genre.FANTASY)
    age_group = models.CharField(max_length=10, choices=AgeGroup.choices, default=AgeGroup.CHILD)
    story_length = models.CharField(
        max_length=12,
        choices=StoryLength.choices,
        default=StoryLength.MEDIUM,
    )
    prompt = models.TextField(blank=True)
    audio_converted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "stories"

    def __str__(self):
        return self.title
