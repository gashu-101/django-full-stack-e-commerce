from decimal import Decimal
from django.core.management.base import BaseCommand
from shop.models import Category, Product


CATEGORIES = ['Ceramics', 'Lighting', 'Textiles', 'Objects']

PRODUCTS = [
    # name, category, price, compare_at, tagline, image_url, featured
    ('Hinoki Stoneware Vase', 'Ceramics', '68.00', None,
     'A quiet vase, hand-thrown in matte stone.',
     'https://images.unsplash.com/photo-1578500494198-246f612d3b3d?w=900&q=80', True),

    ('Linen Throw — Sand', 'Textiles', '120.00', '160.00',
     'Heavyweight stone-washed linen, the colour of pale dunes.',
     'https://images.unsplash.com/photo-1616627781729-a3f31a48e1c5?w=900&q=80', True),

    ('Akari Paper Lamp', 'Lighting', '184.00', None,
     'Hand-folded mulberry paper. Warm, atmospheric light.',
     'https://images.unsplash.com/photo-1513506003901-1e6a229e2d15?w=900&q=80', True),

    ('Walnut Salad Server', 'Objects', '42.00', None,
     'Carved from a single block of black walnut.',
     'https://images.unsplash.com/photo-1577128893755-3a4d3e63a017?w=900&q=80', True),

    ('Ribbed Tumbler — set of 4', 'Objects', '56.00', '72.00',
     'Mouth-blown, beautifully imperfect.',
     'https://images.unsplash.com/photo-1610631066894-62452ccb927c?w=900&q=80', False),

    ('Earth Ceramic Bowl', 'Ceramics', '38.00', None,
     'Wheel-thrown, raw-glaze finish.',
     'https://images.unsplash.com/photo-1610701596061-2ecf227e85b2?w=900&q=80', False),

    ('Brass Candle Holder', 'Objects', '74.00', None,
     'Solid brass, will patina beautifully.',
     'https://images.unsplash.com/photo-1602874801007-aa5d27c4a39d?w=900&q=80', False),

    ('Wool Floor Cushion', 'Textiles', '142.00', None,
     'Hand-woven oatmeal wool, oversize and inviting.',
     'https://images.unsplash.com/photo-1555041469-a586c61ea9bc?w=900&q=80', False),

    ('Pendant Lamp — Clay', 'Lighting', '298.00', '340.00',
     'A soft halo of light from raw stoneware.',
     'https://images.unsplash.com/photo-1565814329452-e1efa11c5b89?w=900&q=80', False),

    ('Olivewood Cutting Board', 'Objects', '88.00', None,
     'Slow-grown Mediterranean olivewood.',
     'https://images.unsplash.com/photo-1556910638-6cdbc60ce0e1?w=900&q=80', False),

    ('Speckled Mug', 'Ceramics', '24.00', None,
     'For long mornings.',
     'https://images.unsplash.com/photo-1514228742587-6b1558fcca3d?w=900&q=80', False),

    ('Wave Wall Sconce', 'Lighting', '210.00', None,
     'Sculptural plaster, washes light up the wall.',
     'https://images.unsplash.com/photo-1540932239986-30128078f3c5?w=900&q=80', False),
]


class Command(BaseCommand):
    help = 'Seed the database with sample categories and products.'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Delete existing products/categories first.')

    def handle(self, *args, **opts):
        if opts.get('reset'):
            Product.objects.all().delete()
            Category.objects.all().delete()
            self.stdout.write(self.style.WARNING('Cleared existing products and categories.'))

        cats = {}
        for name in CATEGORIES:
            cat, _ = Category.objects.get_or_create(name=name)
            cats[name] = cat

        created = 0
        for name, cat_name, price, compare_at, tagline, image_url, featured in PRODUCTS:
            obj, was_created = Product.objects.get_or_create(
                name=name,
                defaults={
                    'category': cats[cat_name],
                    'price': Decimal(price),
                    'compare_at': Decimal(compare_at) if compare_at else None,
                    'tagline': tagline,
                    'description': f"{tagline}\n\nA Nova object — selected for its honest materials and quiet presence. Designed to be used daily, and to age well over the years.",
                    'image_url': image_url,
                    'stock': 25,
                    'featured': featured,
                }
            )
            if was_created:
                created += 1

        self.stdout.write(self.style.SUCCESS(
            f'Seeding complete. {created} new products, {len(PRODUCTS) - created} already existed.'
        ))
