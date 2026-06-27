from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=90, unique=True, blank=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Categories'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    tagline = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=9, decimal_places=2)
    compare_at = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True,
                                     help_text="Optional original price for showing a discount")
    image_url = models.URLField(max_length=500, blank=True,
                                help_text="External image URL (e.g., Unsplash). Used if no upload.")
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    stock = models.PositiveIntegerField(default=25)
    featured = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-featured', '-created']

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)[:170]
            slug = base
            i = 2
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{i}"
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('shop:product_detail', args=[self.slug])

    @property
    def display_image(self):
        if self.image:
            try:
                return self.image.url
            except Exception:
                pass
        return self.image_url or 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=800'

    @property
    def on_sale(self):
        return self.compare_at and self.compare_at > self.price

    @property
    def discount_pct(self):
        if not self.on_sale:
            return 0
        return int(round((1 - float(self.price) / float(self.compare_at)) * 100))

    def __str__(self):
        return self.name


class Order(models.Model):
    STATUS = [
        ('pending', 'Pending payment'),
        ('paid', 'Paid'),
        ('shipped', 'Shipped'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    METHOD = [
        ('chapa', 'Chapa (Ethiopia)'),
        ('crypto', 'Crypto'),
        ('cod', 'Cash on delivery'),
    ]
    full_name = models.CharField(max_length=120)
    email = models.EmailField()
    address = models.CharField(max_length=240)
    city = models.CharField(max_length=80)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=80)
    note = models.TextField(blank=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=12, choices=STATUS, default='pending')

    payment_method = models.CharField(max_length=16, choices=METHOD, default='cod')
    tx_ref = models.CharField(max_length=64, unique=True, blank=True,
                              help_text='Unique reference shared with the payment gateway.')
    payment_url = models.URLField(max_length=600, blank=True,
                                  help_text='Gateway checkout URL while pending.')
    paid_at = models.DateTimeField(null=True, blank=True)
    payment_meta = models.JSONField(default=dict, blank=True,
                                    help_text='Raw verification payload from the gateway.')

    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return f"Order #{self.pk} — {self.full_name}"

    @property
    def first_name(self):
        return (self.full_name or '').split(' ', 1)[0]

    @property
    def last_name(self):
        parts = (self.full_name or '').split(' ', 1)
        return parts[1] if len(parts) > 1 else ''


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    product_name = models.CharField(max_length=160)
    price = models.DecimalField(max_digits=9, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    @property
    def line_total(self):
        return self.price * self.quantity
