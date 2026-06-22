from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("books", "0002_booksummary_chapter_short_summaries_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="booksummary",
            name="main_points",
            field=models.JSONField(default=list),
        ),
        migrations.AddField(
            model_name="booksummary",
            name="short_stories",
            field=models.JSONField(default=list),
        ),
    ]
