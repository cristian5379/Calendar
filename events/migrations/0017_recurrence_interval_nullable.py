from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0016_remove_country_timezone'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='recurrence_interval',
            field=models.PositiveIntegerField(blank=True, default=1, help_text='Interval for recurrence (e.g., every N days/weeks/months)', null=True),
        ),
    ]
