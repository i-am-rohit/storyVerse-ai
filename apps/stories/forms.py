from django import forms

from .models import Story


class StoryGeneratorForm(forms.Form):
    language = forms.ChoiceField(
        choices=Story.Language.choices,
        widget=forms.Select(attrs={"class": "form-select glass-input", "id": "language"}),
    )
    genre = forms.ChoiceField(
        choices=Story.Genre.choices,
        widget=forms.Select(attrs={"class": "form-select glass-input", "id": "genre"}),
    )
    age_group = forms.ChoiceField(
        choices=Story.AgeGroup.choices,
        widget=forms.Select(attrs={"class": "form-select glass-input", "id": "age_group"}),
    )
    story_length = forms.ChoiceField(
        choices=Story.StoryLength.choices,
        initial=Story.StoryLength.MEDIUM,
        widget=forms.Select(attrs={"class": "form-select glass-input", "id": "story_length"}),
        label="Story size",
        help_text="Controls approximate word count of the generated story.",
    )
    prompt = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "class": "form-control glass-input",
                "id": "prompt",
                "rows": 8,
                "placeholder": "Describe your story idea in English or Hindi… e.g. A brave little fox who discovers a hidden library / एक बहादुर लोमड़ी जो जंगल में एक जादुई पुस्तकालय खोजती है।",
            }
        ),
    )
