"""Create the initial artist categories and tickets for a new deployment."""

from datetime import date, time
from decimal import Decimal

from django.core.management.base import BaseCommand

from main.models import Category, Product


ARTISTS = (
    {
        'name': 'Шаман', 'alias': 'shaman', 'date': date(2027, 7, 16), 'time': time(18, 0),
        'price': Decimal('2500.00'), 'image': 'img/shaman.jpg',
        'tickets': (
            ('shaman-standard', 'Билет на выступление Шамана', 'Танцпол и доступ на выступление', Decimal('2500.00')),
            ('shaman-vip', 'VIP-билет на выступление Шамана', 'VIP-зона и отдельный вход', Decimal('4500.00')),
        ),
    },
    {
        'name': 'Ваня Дмитриенко', 'alias': 'vanya-dmitrienko', 'date': date(2027, 7, 16),
        'time': time(19, 30), 'price': Decimal('2200.00'), 'image': 'img/vanya.jpg',
        'tickets': (
            ('vanya-standard', 'Билет на выступление Вани Дмитриенко', 'Танцпол и доступ на выступление', Decimal('2200.00')),
            ('vanya-vip', 'VIP-билет на выступление Вани Дмитриенко', 'VIP-зона и отдельный вход', Decimal('3900.00')),
        ),
    },
    {
        'name': 'Стас Михайлов', 'alias': 'stas-mikhaylov', 'date': date(2027, 7, 16),
        'time': time(21, 0), 'price': Decimal('3500.00'), 'image': 'img/stas.jpg',
        'tickets': (
            ('stas-standard', 'Билет на выступление Стаса Михайлова', 'Танцпол и доступ на выступление', Decimal('3500.00')),
            ('stas-vip', 'VIP-билет на выступление Стаса Михайлова', 'VIP-зона и отдельный вход', Decimal('6500.00')),
        ),
    },
    {
        'name': 'Анна Асти', 'alias': 'anna-asti', 'date': date(2027, 7, 16),
        'time': time(22, 30), 'price': Decimal('3000.00'), 'image': 'img/anna.jpg',
        'tickets': (
            ('anna-standard', 'Билет на выступление Анны Асти', 'Танцпол и доступ на выступление', Decimal('3000.00')),
            ('anna-vip', 'VIP-билет на выступление Анны Асти', 'VIP-зона и отдельный вход', Decimal('5500.00')),
        ),
    },
)


class Command(BaseCommand):
    help = 'Create the permanent artist categories and tickets without overwriting admin edits.'

    def handle(self, *args, **options):
        created_categories = 0
        created_tickets = 0
        for artist in ARTISTS:
            category, created = Category.objects.get_or_create(
                alias=artist['alias'],
                defaults={
                    'name': artist['name'],
                    'performance_date': artist['date'],
                    'performance_time': artist['time'],
                    'performance_price': artist['price'],
                },
            )
            created_categories += int(created)
            if not created:
                missing = {}
                if category.performance_date is None:
                    missing['performance_date'] = artist['date']
                if category.performance_time is None:
                    missing['performance_time'] = artist['time']
                if category.performance_price is None:
                    missing['performance_price'] = artist['price']
                if missing:
                    Category.objects.filter(pk=category.pk).update(**missing)

            for alias, name, description, price in artist['tickets']:
                product, product_created = Product.objects.get_or_create(
                    alias=alias,
                    defaults={
                        'name': name,
                        'short_description': description,
                        'description': f'{description}. Выступление артиста: {artist["name"]}.',
                        'price': price,
                        'image': artist['image'],
                        'available': True,
                    },
                )
                created_tickets += int(product_created)
                if not product.image:
                    Product.objects.filter(pk=product.pk).update(image=artist['image'])
                product.categories.add(category)

        self.stdout.write(self.style.SUCCESS(
            f'Catalog ready: {created_categories} categories and {created_tickets} tickets created.'
        ))
