from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0003_artist_category_schedule_and_ticket_images'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='category',
            name='performance_price',
        ),
    ]
