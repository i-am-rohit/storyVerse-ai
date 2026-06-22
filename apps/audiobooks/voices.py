"""Audiobook voice and music style definitions."""

VOICES = [
    # Western voices
    {"id": "atlas", "name": "Atlas", "gender": "male", "region": "western", "accent": "American", "style": "Deep & Warm", "icon": "bi-broadcast", "languages": ["en"]},
    {"id": "marcus", "name": "Marcus", "gender": "male", "region": "western", "accent": "American", "style": "Classic Narrator", "icon": "bi-mic", "languages": ["en"]},
    {"id": "ethan", "name": "Ethan", "gender": "male", "region": "western", "accent": "American", "style": "Young & Energetic", "icon": "bi-lightning", "languages": ["en"]},
    {"id": "james", "name": "James", "gender": "male", "region": "western", "accent": "British", "style": "Elegant & Refined", "icon": "bi-cup-hot", "languages": ["en"]},
    {"id": "nova", "name": "Nova", "gender": "female", "region": "western", "accent": "American", "style": "Soft & Expressive", "icon": "bi-stars", "languages": ["en"]},
    {"id": "sarah", "name": "Sarah", "gender": "female", "region": "western", "accent": "American", "style": "Professional", "icon": "bi-briefcase", "languages": ["en"]},
    {"id": "luna", "name": "Luna", "gender": "female", "region": "western", "accent": "British", "style": "Warm Storyteller", "icon": "bi-moon-stars", "languages": ["en"]},
    {"id": "aria", "name": "Aria", "gender": "female", "region": "western", "accent": "American", "style": "Clear & Bright", "icon": "bi-soundwave", "languages": ["en"]},
    # ElevenLabs Indian voices (premade + voice library)
    {"id": "jennie", "name": "Jennie", "gender": "female", "region": "indian", "accent": "Indian English", "style": "ElevenLabs · Free tier", "icon": "bi-flower1", "languages": ["en", "hi"], "elevenlabs": True, "free_tier": True},
    {"id": "sonal", "name": "Sonal", "gender": "female", "region": "indian", "accent": "Premium Indian English", "style": "ElevenLabs · Storyteller", "icon": "bi-stars", "languages": ["en", "hi"], "elevenlabs": True},
    {"id": "anya", "name": "Anya", "gender": "female", "region": "indian", "accent": "Neutral Indian Pro", "style": "ElevenLabs · Professional", "icon": "bi-briefcase", "languages": ["en", "hi"], "elevenlabs": True},
    {"id": "apsara", "name": "Apsara", "gender": "female", "region": "indian", "accent": "Indian Storytelling", "style": "ElevenLabs · Podcast", "icon": "bi-book", "languages": ["en", "hi"], "elevenlabs": True},
    {"id": "arjun_el", "name": "Arjun", "gender": "male", "region": "indian", "accent": "Warm Hindi/English", "style": "ElevenLabs · Instructor", "icon": "bi-mic", "languages": ["en", "hi"], "elevenlabs": True},
    {"id": "rahul", "name": "Rahul", "gender": "male", "region": "indian", "accent": "Natural Indian English", "style": "ElevenLabs · Warm", "icon": "bi-broadcast", "languages": ["en", "hi"], "elevenlabs": True},
    {"id": "nitin", "name": "Nitin", "gender": "male", "region": "indian", "accent": "Indian with Emotion", "style": "ElevenLabs · Expressive", "icon": "bi-emoji-smile", "languages": ["en", "hi"], "elevenlabs": True},
    {"id": "karthik", "name": "Karthik", "gender": "male", "region": "indian", "accent": "South Indian English", "style": "ElevenLabs · Regional", "icon": "bi-globe-asia-australia", "languages": ["en", "hi"], "elevenlabs": True},
    {"id": "tarun", "name": "Tarun", "gender": "male", "region": "indian", "accent": "Desi Indian Male", "style": "ElevenLabs · Deep", "icon": "bi-volume-up", "languages": ["en", "hi"], "elevenlabs": True},
    {"id": "raj", "name": "Raj", "gender": "male", "region": "indian", "accent": "Indian English Agent", "style": "ElevenLabs · Conversational", "icon": "bi-chat-dots", "languages": ["en", "hi"], "elevenlabs": True},
]

MUSIC_STYLES = [
    {"id": "none", "name": "No Music", "description": "Narration only", "icon": "bi-volume-mute", "free": True},
    {"id": "indian_classical", "name": "Indian Classical", "description": "Free · Tanpura drone & raga", "icon": "bi-music-note-beamed", "free": True},
    {"id": "bollywood", "name": "Bollywood", "description": "Free · Upbeat cinematic", "icon": "bi-film", "free": True},
    {"id": "sitar", "name": "Sitar Fusion", "description": "Free · Mystical sitar tones", "icon": "bi-brightness-high", "free": True},
    {"id": "bansuri", "name": "Bansuri Flute", "description": "Free · Peaceful bamboo flute", "icon": "bi-wind", "free": True},
    {"id": "tabla", "name": "Tabla Rhythm", "description": "Free · Gentle tabla beats", "icon": "bi-disc", "free": True},
]

GENRE_MUSIC = {
    "fantasy": {"en": "sitar", "hi": "sitar"},
    "adventure": {"en": "bollywood", "hi": "bollywood"},
    "mystery": {"en": "indian_classical", "hi": "indian_classical"},
    "sci_fi": {"en": "sitar", "hi": "sitar"},
    "fairy_tale": {"en": "bansuri", "hi": "bansuri"},
    "historical": {"en": "indian_classical", "hi": "tabla"},
    "humor": {"en": "bollywood", "hi": "bollywood"},
    "horror": {"en": "indian_classical", "hi": "indian_classical"},
}

# Backward compatible alias
GENRE_DEFAULT_MUSIC = {genre: mapping["hi"] for genre, mapping in GENRE_MUSIC.items()}

INDIAN_VOICE_FALLBACK = "jennie"


def get_voice(voice_id: str) -> dict | None:
    return next((v for v in VOICES if v["id"] == voice_id), None)


def get_music_style(style_id: str) -> dict | None:
    return next((m for m in MUSIC_STYLES if m["id"] == style_id), None)


def resolve_story_music(genre: str | None, language: str = "en", music_style: str = "auto") -> str:
    """Pick background music from story genre + language."""
    if music_style and music_style != "auto":
        return music_style

    if genre and genre in GENRE_MUSIC:
        lang_key = "hi" if language == "hi" else "en"
        return GENRE_MUSIC[genre].get(lang_key, GENRE_MUSIC[genre]["en"])

    return "bansuri" if language == "hi" else "indian_classical"


def recommend_voices_for_story(language: str = "en") -> list[str]:
    """Voice IDs suggested for a story language."""
    if language == "hi":
        return ["jennie", "sonal", "arjun_el", "rahul", "anya", "nitin"]
    return ["aria", "sarah", "marcus", "nova"]


def music_styles_for_story(genre: str | None, language: str = "en") -> list[dict]:
    """Return music styles with recommended flag for UI."""
    recommended_id = resolve_story_music(genre, language, "auto")
    styles = []
    for style in MUSIC_STYLES:
        entry = {**style, "recommended": style["id"] == recommended_id}
        styles.append(entry)
    return styles
