import logging
import random
import re
import textwrap

from .models import Story

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# English templates
# ---------------------------------------------------------------------------

EN_OPENINGS = {
    "fantasy": [
        "In a realm where stars whispered secrets to those who listened,",
        "Beyond the misty mountains, in a kingdom woven from moonlight,",
        "Deep within an enchanted forest where time moved differently,",
    ],
    "adventure": [
        "The map was torn and faded, but the X marked a place no explorer had returned from — until now.",
        "With nothing but a compass and unshakeable courage,",
        "The old ship creaked as it cut through uncharted waters, carrying",
    ],
    "mystery": [
        "The letter arrived without a return address, written in ink that shimmered like mercury.",
        "Every clock in the mansion stopped at precisely midnight, and",
        "Detective Mara Chen had seen many strange cases, but none like the one where",
    ],
    "sci_fi": [
        "The colony ship Aurora had traveled for three centuries, and on the morning of arrival,",
        "In the year 2247, when humanity had spread across seven star systems,",
        "The AI named Echo had one directive: protect the last seed vault on Earth. But today,",
    ],
    "fairy_tale": [
        "Once upon a time, in a village where flowers sang at dawn,",
        "There lived a kind soul who possessed the rarest gift of all — the ability to hear hearts,",
        "In a cottage at the edge of the Whispering Woods,",
    ],
    "historical": [
        "The year was 1847, and the world was changing faster than anyone could imagine.",
        "Through the cobblestone streets of a city alive with revolution,",
        "In the shadow of great monuments, where history was written in courage and sacrifice,",
    ],
    "humor": [
        "Nobody expected the town's annual talent show to be disrupted by a chicken wearing a top hat — but here we are.",
        "If you had told Marcus yesterday that he'd befriend a talking cactus, he would have laughed. Today,",
        "The rules were simple: don't wake the dragon. Naturally,",
    ],
    "horror": [
        "The house at the end of Thornfield Lane had been empty for fifty years — until the lights came on.",
        "She found the diary in the attic, its pages still warm to the touch, and read the final entry:",
        "They say you should never answer a knock at midnight. She answered anyway, and",
    ],
}

EN_MORALS = {
    "fantasy": [
        "True magic lives not in spells, but in the courage to believe in yourself.",
        "The greatest adventures begin when we choose kindness over fear.",
        "Wonder is never far away — we need only open our eyes and hearts.",
    ],
    "adventure": [
        "The journey matters as much as the destination.",
        "Bravery is not the absence of fear, but action in spite of it.",
        "Every explorer leaves footprints — make yours worth following.",
    ],
    "mystery": [
        "The truth, however hidden, always finds a way to the light.",
        "Patience and observation reveal what haste cannot.",
        "Not every question has a simple answer, but every answer teaches us something.",
    ],
    "sci_fi": [
        "Technology may change, but humanity's need for connection remains constant.",
        "The future belongs to those who dare to imagine it differently.",
        "Progress without compassion is not progress at all.",
    ],
    "fairy_tale": [
        "Kindness is the most powerful magic of all.",
        "Even the smallest act of goodness can change the world.",
        "True beauty is found in a generous heart.",
    ],
    "historical": [
        "History teaches us that ordinary people can do extraordinary things.",
        "The choices we make today become the stories of tomorrow.",
        "Courage in the face of adversity defines the human spirit.",
    ],
    "humor": [
        "Laughter is the best way to turn any day around.",
        "Sometimes the best plans are the ones that go completely wrong.",
        "Don't take life too seriously — nobody gets out alive anyway.",
    ],
    "horror": [
        "Some doors are better left unopened.",
        "Fear loses its power when we face it together.",
        "The darkest nights often reveal the brightest stars.",
    ],
}

EN_CONTINUE = [
    "And then, something unexpected happened.",
    "As the story unfolded further,",
    "Just when all seemed lost,",
    "With newfound determination,",
    "The adventure was far from over, for",
]

# ---------------------------------------------------------------------------
# Hindi templates (हिंदी)
# ---------------------------------------------------------------------------

HI_OPENINGS = {
    "fantasy": [
        "एक ऐसे राज्य में जहाँ तारे रहस्यमय फुसफुसाहट करते थे,",
        "धुंधले पहाड़ों के पार, चाँदनी से बुने गए एक राज्य में,",
        "जादुई जंगल की गहराई में, जहाँ समय अलग ही गति से बहता था,",
    ],
    "adventure": [
        "फटा हुआ नक्शा हाथ में था, और उस पर का निशान ऐसी जगह दिखाता था जहाँ कोई लौटकर नहीं आया था — आज तक।",
        "केवल एक कम्पास और अटूट साहस लेकर,",
        "पुराना जहाज अनजान पानी में आगे बढ़ रहा था, लेकर",
    ],
    "mystery": [
        "बिना पते का एक खत आया, जिस पर चाँदी जैसी स्याही से लिखा था।",
        "हवेली की हर घड़ी ठीक आधी रात पर रुक गई, और",
        "जासूस मीरा ने कई अजीब मामले देखे, पर ऐसा कभी नहीं जहाँ",
    ],
    "sci_fi": [
        "अंतरिक्ष जहाज 'अरोरा' तीन सदियों से यात्रा कर रहा था, और पहुँचने की सुबह,",
        "सन् 2247 में, जब मानवता सात तारा प्रणालियों तक फैल चुकी थी,",
        "एआई 'एको' का एक ही निर्देश था: पृथ्वी के अंतिम बीज को बचाना। पर आज,",
    ],
    "fairy_tale": [
        "एक बार की बात है, एक गाँव में जहाँ फूल सुबह-सुबह गाते थे,",
        "एक दयालु आत्मा रहती थी जिसे दिल की आवाज़ सुनने का दुर्लभ वरदान प्राप्त था,",
        "फुसफुसाते जंगल के किनारे एक छोटी झोपड़ी में,",
    ],
    "historical": [
        "सन् 1847 था, और दुनिया किसी से भी तेज़ बदल रही थी।",
        "क्रांति से गुलजार सड़कों पर,",
        "महान स्मारकों की छाया में, जहाँ इतिहास साहस और बलिदान से लिखा गया,",
    ],
    "humor": [
        "किसी ने सोचा भी नहीं था कि गाँव का वार्षिक कार्यक्रम एक टोप पहने मुर्गे से बिगड़ जाएगा — पर हुआ।",
        "अगर कल किसी ने राहुल से कहा होता कि वह एक बात करने वाले कैक्टस से दोस्ती करेगा, तो वह हँस देता। आज,",
        "नियम सरल था: ड्रैगन को मत जगाओ। स्वाभाविक रूप से,",
    ],
    "horror": [
        "गली के अंत में वह मकान पचास साल से खाली था — जब तक रोशनी न जली।",
        "उसे अटारी में एक डायरी मिली, जिसके पन्ने अभी भी गर्म थे, और उसने आखिरी प्रविष्टि पढ़ी:",
        "कहते हैं आधी रात को दस्तक का जवाब नहीं देना चाहिए। उसने दे दिया, और",
    ],
}

HI_MORALS = {
    "fantasy": [
        "असली जादू मंत्रों में नहीं, बल्कि खुद पर विश्वास करने के साहस में है।",
        "सबसे बड़े रोमांच तब शुरू होते हैं जब हम डर के बजाय दया चुनते हैं।",
        "अद्भुत चीज़ें हमेशा पास ही होती हैं — बस आँखें और दिल खोलने की ज़रूरत है।",
    ],
    "adventure": [
        "मंज़िल जितनी महत्वपूर्ण है, यात्रा भी उतनी ही है।",
        "साहस का अर्थ डर का न होना नहीं, डर के बावजूद आगे बढ़ना है।",
        "हर खोजकर्ता अपने पदचिन्ह छोड़ता है — अपने पदचिन्ह योग्य बनाएँ।",
    ],
    "mystery": [
        "सच, चाहे कितना भी छिपा हो, एक दिन प्रकाश में आ ही जाता है।",
        "धैर्य और निरीक्षा वही दिखाते हैं जो जल्दबाज़ी नहीं दिखा सकती।",
        "हर सवाल का सरल जवाब नहीं होता, पर हर जवाब कुछ सिखाता है।",
    ],
    "sci_fi": [
        "तकनीक बदल सकती है, पर मनुष्य की जुड़ाव की आवश्यकता वही रहती है।",
        "भविष्य उन्हीं का है जो इसे अलग तरह से कल्पना करने की हिम्मत रखते हैं।",
        "करुणा के बिना प्रगति, असली प्रगति नहीं है।",
    ],
    "fairy_tale": [
        "दया सबसे शक्तिशाली जादू है।",
        "सबसे छोटा नेक काम भी दुनिया बदल सकता है।",
        "असली सुंदरता उदार दिल में होती है।",
    ],
    "historical": [
        "इतिहास सिखाता है कि साधारण लोग भी असाधारण काम कर सकते हैं।",
        "आज के फैसले कल की कहानियाँ बनते हैं।",
        "मुश्किल समय में साहस ही मनुष्य की पहचान है।",
    ],
    "humor": [
        "हँसी किसी भी दिन को बेहतर बनाने का सबसे अच्छा तरीका है।",
        "कभी-कभी सबसे अच्छी योजनाएँ वही होती हैं जो पूरी तरह गलत हो जाती हैं।",
        "ज़िंदगी को बहुत गंभीरता से मत लो — आखिर कोई जीवित नहीं बचता!",
    ],
    "horror": [
        "कुछ दरवाज़े बंद ही रहने चाहिए।",
        "डर की ताकत तब कम होती है जब हम साथ मिलकर सामना करते हैं।",
        "सबसे अँधेरी रातें अक्सर सबसे चमकीले तारे दिखाती हैं।",
    ],
}

HI_CONTINUE = [
    "और फिर, कुछ अनपेक्षित हुआ।",
    "जैसे-जैसे कहानी आगे बढ़ी,",
    "जब सब कुछ खोता हुआ लग रहा था,",
    "नए हौसले के साथ,",
    "रोमांच अभी खत्म नहीं हुआ था, क्योंकि",
]

HI_GENRE_LABELS = {
    "fantasy": "कल्पना",
    "adventure": "रोमांच",
    "mystery": "रहस्य",
    "sci_fi": "विज्ञान कथा",
    "fairy_tale": "परी कथा",
    "historical": "ऐतिहासिक",
    "humor": "हास्य",
    "horror": "भय",
}

LENGTH_WORD_TARGETS = {
    "short": 150,
    "medium": 350,
    "long": 600,
    "extra_long": 1000,
}


class StoryGeneratorService:
    """Generates story content via Llama 3.1/3.2 when enabled, else templates."""

    @classmethod
    def _writer(cls):
        from agents.writer_agent import WriterAgent
        return WriterAgent()

    @classmethod
    def _llm_available(cls) -> bool:
        return cls._writer().is_available()

    @classmethod
    def _is_hindi(cls, language: str) -> bool:
        return language == Story.Language.HINDI

    @classmethod
    def _templates(cls, language: str):
        if cls._is_hindi(language):
            return HI_OPENINGS, HI_MORALS, HI_CONTINUE, HI_GENRE_LABELS
        return EN_OPENINGS, EN_MORALS, EN_CONTINUE, dict(Story.Genre.choices)

    @classmethod
    def _genre_label(cls, genre: str, language: str) -> str:
        _, _, _, genre_labels = cls._templates(language)
        return genre_labels.get(genre, genre)

    @classmethod
    def _build_title(cls, prompt: str, genre: str, language: str) -> str:
        words = [w.strip(".,!?।") for w in prompt.split() if len(w.strip(".,!?।")) > 1]
        if cls._is_hindi(language):
            if words:
                key_words = " ".join(words[:3])
                return f"{key_words} की कहानी"
            return f"एक {cls._genre_label(genre, language)} कहानी"
        if words:
            return f"The Tale of {' '.join(words[:3]).title()}"
        return f"A {cls._genre_label(genre, language)} Story"

    @classmethod
    def _age_label(cls, age_group: str, language: str) -> str:
        if cls._is_hindi(language):
            return f"{age_group} वर्ष"
        return age_group

    @classmethod
    def _word_count(cls, text: str) -> int:
        return len(text.split())

    @classmethod
    def _extra_paragraph(
        cls,
        *,
        prompt_snippet: str,
        genre_label: str,
        age_label: str,
        language: str,
        index: int,
        story_length: str = "medium",
    ) -> str:
        if cls._is_hindi(language):
            templates = [
                f"रास्ते में उन्होंने ऐसे रहस्य देखे जो {genre_label} की दुनिया को और गहरा बनाते थे।",
                f"हर मोड़ पर {prompt_snippet} की याद उन्हें आगे बढ़ने की हिम्मत देती रही।",
                f"दोस्तों और साथियों ने मिलकर चुनौतियों का सामना किया — {age_label} के पाठकों के लिए सुरक्षित रूप से।",
                f"धीरे-धीरे कहानी एक नए रंग में बदल गई, जहाँ हर पल सीख और रोमांच लेकर आया।",
                f"अंत में, सबने महसूस किया कि साहस और दया सबसे बड़ी ताकत हैं।",
                f"तारों भरी रात में उन्होंने मिलकर सपने देखे और नए रास्ते चुने।",
                f"हर दिन एक नई परीक्षा लेकर आया, पर उनका विश्वास कभी नहीं डगमगाया।",
            ]
        else:
            templates = [
                f"Along the way they uncovered wonders that deepened the {genre_label.lower()} world around them.",
                f"At every turn, the memory of \"{prompt_snippet}\" gave them courage to keep going.",
                f"Friends and allies faced challenges together — crafted carefully for readers aged {age_label}.",
                f"Slowly the tale changed hue, each moment bringing fresh lessons and excitement.",
                f"In the end, everyone learned that courage and kindness are the greatest powers of all.",
                f"Under starlit skies they dreamed together and chose paths none had walked before.",
                f"Each new day brought a test of heart, yet their belief never wavered.",
            ]
        parts_per_block = {"short": 1, "medium": 2, "long": 2, "extra_long": 3}.get(story_length, 1)
        chunks = [
            textwrap.fill(templates[(index + offset) % len(templates)], width=80)
            for offset in range(parts_per_block)
        ]
        return "\n\n".join(chunks)

    @classmethod
    def _build_content(
        cls,
        prompt: str,
        genre: str,
        age_group: str,
        language: str,
        story_length: str = "medium",
    ) -> str:
        openings, _, _, _ = cls._templates(language)
        opening = random.choice(openings.get(genre, openings["fantasy"]))
        prompt_snippet = prompt.strip().rstrip(".।")
        genre_label = cls._genre_label(genre, language)
        age_label = cls._age_label(age_group, language)

        if cls._is_hindi(language):
            if not prompt_snippet:
                prompt_snippet = "एक ऐसा नायक जिसका भाग्य अभी लिखा जाना बाकी था"
            paragraphs = [
                f"{opening} वहाँ एक कहानी रहती थी जो सुनाई जाने के लिए बेताब थी। "
                f"यह शुरू हुई {prompt_snippet} से।",
                textwrap.fill(
                    f"चारों ओर की दुनिया संभावनाओं से भरी थी। "
                    f"हर कदम नए अजूबे और चुनौतियाँ लेकर आया, "
                    f"जो {age_label} के पाठकों के लिए सावधानी से तैयार की गई थी। "
                    f"दोस्त बने, बाधाएँ पार हुईं, और रहस्य उजागर हुए — "
                    f"यह सब {genre_label} की भावना में रचा गया था।",
                    width=80,
                ),
                textwrap.fill(
                    f"जैसे ही क्षितिज पर सूरज उगा, यात्रा अपने महत्वपूर्ण मोड़ पर पहुँची। "
                    f"जो एक साधारण विचार — \"{prompt_snippet}\" — से शुरू हुआ था, "
                    f"वह एक अविस्मरणीय रोमांच में बदल गया, "
                    f"जिसने सुनने वाले सभी को बदल दिया।",
                    width=80,
                ),
            ]
        else:
            if not prompt_snippet:
                prompt_snippet = "a hero whose destiny was yet unwritten"
            paragraphs = [
                f"{opening} there lived a tale waiting to be told. "
                f"It began with {prompt_snippet.lower()}.",
                textwrap.fill(
                    f"The world around them pulsed with possibility. "
                    f"Every step forward revealed new wonders and challenges, "
                    f"shaped carefully for readers aged {age_label}. "
                    f"Friends were made, obstacles overcome, and secrets unveiled "
                    f"in a narrative crafted in the spirit of {genre_label.lower()}.",
                    width=80,
                ),
                textwrap.fill(
                    f"As dawn broke over the horizon, the journey reached its turning point. "
                    f"What started as a simple idea — \"{prompt_snippet}\" — "
                    f"had blossomed into an unforgettable adventure, "
                    f"leaving everyone who heard it changed forever.",
                    width=80,
                ),
            ]

        target = LENGTH_WORD_TARGETS.get(story_length, LENGTH_WORD_TARGETS["medium"])
        content = "\n\n".join(paragraphs)
        extra_index = 0
        max_extra = {"short": 4, "medium": 8, "long": 14, "extra_long": 20}.get(story_length, 8)
        while cls._word_count(content) < target and extra_index < max_extra:
            paragraphs.append(
                cls._extra_paragraph(
                    prompt_snippet=prompt_snippet,
                    genre_label=genre_label,
                    age_label=age_label,
                    language=language,
                    index=extra_index,
                    story_length=story_length,
                )
            )
            content = "\n\n".join(paragraphs)
            extra_index += 1

        return content

    @classmethod
    def generate(
        cls,
        *,
        prompt: str,
        language: str,
        genre: str,
        age_group: str,
        story_length: str = "medium",
    ) -> dict:
        if cls._llm_available():
            try:
                from agents.llm_client import LLMError

                draft = cls._writer().generate_story(
                    prompt=prompt,
                    genre=genre,
                    age_group=age_group,
                    language=language,
                    story_length=story_length,
                )
                _, morals, _, _ = cls._templates(language)
                moral = draft.moral or random.choice(morals.get(genre, morals["fantasy"]))
                return {
                    "title": draft.title,
                    "content": draft.content,
                    "moral": moral,
                    "language": language,
                    "genre": genre,
                    "age_group": age_group,
                    "story_length": story_length,
                    "word_count": draft.word_count,
                    "source": "llama",
                }
            except Exception as exc:
                logger.warning("Llama story generation failed, using templates: %s", exc)

        _, morals, _, _ = cls._templates(language)
        title = cls._build_title(prompt, genre, language)
        content = cls._build_content(prompt, genre, age_group, language, story_length)
        moral = random.choice(morals.get(genre, morals["fantasy"]))
        return {
            "title": title,
            "content": content,
            "moral": moral,
            "language": language,
            "genre": genre,
            "age_group": age_group,
            "story_length": story_length,
            "word_count": cls._word_count(content),
            "source": "template",
        }

    @classmethod
    def continue_story(
        cls,
        *,
        title: str,
        content: str,
        genre: str,
        age_group: str,
        language: str = Story.Language.ENGLISH,
        story_length: str = "medium",
    ) -> str:
        if cls._llm_available():
            try:
                return cls._writer().continue_story(
                    title=title,
                    content=content,
                    genre=genre,
                    age_group=age_group,
                    language=language,
                    story_length=story_length,
                )
            except Exception as exc:
                logger.warning("Llama continue failed, using templates: %s", exc)

        _, _, continue_phrases, _ = cls._templates(language)
        bridge = random.choice(continue_phrases)
        genre_label = cls._genre_label(genre, language)
        age_label = cls._age_label(age_group, language)
        target_extra = max(80, LENGTH_WORD_TARGETS.get(story_length, 350) // 4)

        if cls._is_hindi(language):
            extension = textwrap.fill(
                f"{bridge} पात्रों ने अपने जीवन में एक नया अध्याय खोजा। "
                f"{genre_label} की दुनिया उनके सामने और विस्तृत हो गई, "
                f"नई रहस्यमयी घटनाएँ और जीत {age_label} के लिए उपयुक्त लेकर। "
                f"आशा से भरे दिलों के साथ, वे आगे बढ़े, "
                f"और \"{title}\" का अगला पन्ना एक साथ लिखा।",
                width=80,
            )
        else:
            extension = textwrap.fill(
                f"{bridge} the characters discovered a new chapter in their lives. "
                f"The {genre_label.lower()} world expanded before them, "
                f"offering fresh mysteries and triumphs suited for ages {age_label}. "
                f"With hearts full of hope, they pressed onward, "
                f"writing the next page of {title} together.",
                width=80,
            )

        combined = f"{content}\n\n{extension}"
        extra_index = 0
        while cls._word_count(combined) < cls._word_count(content) + target_extra and extra_index < 4:
            combined = f"{combined}\n\n{cls._extra_paragraph(
                prompt_snippet=title,
                genre_label=genre_label,
                age_label=age_label,
                language=language,
                index=extra_index + 2,
                story_length=story_length,
            )}"
            extra_index += 1
        return combined
