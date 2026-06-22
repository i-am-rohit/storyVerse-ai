"""ElevenLabs voice ID mapping for StoryVerse UI voices."""

ELEVENLABS_VOICE_MAP = {
    # Western (free-tier premade)
    "atlas": "CwhRBWXzGAHq8TQ4Fs17",
    "marcus": "JBFqnCBsd6RMkjVDRZzb",
    "ethan": "IKne3meq5aSn9XLyUdCD",
    "james": "JBFqnCBsd6RMkjVDRZzb",
    "nova": "FGY2WhTYpPnrIDTdsKH5",
    "sarah": "EXAVITQu4vr4xnSDxMaL",
    "luna": "SAz9YHcvj6GT2YYXdXww",
    "aria": "FGY2WhTYpPnrIDTdsKH5",
    # Indian — ElevenLabs premade & voice library
    "jennie": "lKryWyUoRl0p1jnatfo3",
    "sonal": "NyZqLdjqUb8SpOUKIlWT",
    "anya": "gYf9sqh3BkV9QqFMN9Hs",
    "apsara": "g19dpkfwlJXgbfszAJu4",
    "arjun_el": "sS4ouqpoDeVp4REpSCJj",
    "rahul": "txk8uOzZ0iCh0B9mFSRG",
    "nitin": "8WqHCYyrnUqoK70Px5EJ",
    "karthik": "cn9tQG5lDYsfG70MdIj0",
    "tarun": "alJGMewmY1WX0fzByVd2",
    "raj": "uavKGt8JpB2lo1bcty9J",
    # Legacy aliases
    "priya": "lKryWyUoRl0p1jnatfo3",
    "kavya": "NyZqLdjqUb8SpOUKIlWT",
    "arjun": "sS4ouqpoDeVp4REpSCJj",
    "dev": "nPczCjzI2devNBz1zQrb",
}

INDIAN_VOICE_FALLBACK_ID = "lKryWyUoRl0p1jnatfo3"  # Jennie — works on free tier

DEFAULT_MODEL = "eleven_multilingual_v2"
DEFAULT_OUTPUT_FORMAT = "mp3_44100_128"
MAX_CHUNK_CHARS = 4500

ELEVENLABS_LANGUAGE_MAP = {
    "en": "en",
    "hi": "hi",
    "es": "es",
    "fr": "fr",
    "de": "de",
    "ja": "ja",
}
