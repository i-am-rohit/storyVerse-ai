# Generated migration for story_length field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("stories", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="story",
            name="story_length",
            field=models.CharField(
                choices=[
                    ("short", "Short (~150 words)"),
                    ("medium", "Medium (~350 words)"),
                    ("long", "Long (~600 words)"),
                    ("extra_long", "Extra Long (~1,000 words)"),
                ],
                default="medium",
                max_length=12,
            ),
        ),
    ]
