from django.db import migrations, models


def fill_missing_ticket_images(apps, schema_editor):
    Product = apps.get_model('main', 'Product')
    Product.objects.filter(image='').update(image='img/ticket.svg')


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0002_order_orderitem_product_discount_percent_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='performance_date',
            field=models.DateField(blank=True, null=True, verbose_name='Дата выступления'),
        ),
        migrations.AddField(
            model_name='category',
            name='performance_time',
            field=models.TimeField(blank=True, null=True, verbose_name='Время выступления'),
        ),
        migrations.AddField(
            model_name='category',
            name='performance_price',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True,
                                      verbose_name='Цена выступления'),
        ),
        migrations.AlterField(
            model_name='product',
            name='image',
            field=models.CharField(blank=True, default='img/ticket.svg', max_length=255,
                                   verbose_name='Изображение'),
        ),
        migrations.RunPython(fill_missing_ticket_images, migrations.RunPython.noop),
    ]
