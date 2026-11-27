from django.db import migrations


STANDARD_ALIASES = (
    'shaman-standard',
    'vanya-standard',
    'stas-standard',
    'anna-standard',
)

VIP_ALIASES = (
    'shaman-vip',
    'vanya-vip',
    'stas-vip',
    'anna-vip',
)


def assign_ticket_category_images(apps, schema_editor):
    product = apps.get_model('main', 'Product')
    product.objects.filter(alias__in=STANDARD_ALIASES).update(
        image='img/ticket-dance-floor.png',
    )
    product.objects.filter(alias__in=VIP_ALIASES).update(
        image='img/ticket-vip-zone.png',
    )


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0004_remove_category_performance_price'),
    ]

    operations = [
        migrations.RunPython(assign_ticket_category_images, migrations.RunPython.noop),
    ]
