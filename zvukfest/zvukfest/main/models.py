from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator


class Category(models.Model):
    name = models.CharField('Название', max_length=255)
    alias = models.SlugField('Алиас', max_length=255, unique=True)
    performance_date = models.DateField('Дата выступления', null=True, blank=True)
    performance_time = models.TimeField('Время выступления', null=True, blank=True)

    class Meta:
        db_table = 'categories'
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'

    def __str__(self):
        return self.name


class Product(models.Model):
    manufacturer_id = models.SmallIntegerField('ID производителя', default=1)
    name = models.CharField('Название', max_length=255)
    alias = models.SlugField('Алиас', max_length=255, unique=True)
    short_description = models.TextField('Краткое описание')
    description = models.TextField('Описание', blank=True)
    price = models.DecimalField('Цена', max_digits=20, decimal_places=2)
    image = models.CharField('Изображение', max_length=255, blank=True,
                             default='img/ticket.svg')
    available = models.BooleanField('В наличии', default=True)
    discount_percent = models.PositiveSmallIntegerField('Скидка, %', default=0, validators=[MaxValueValidator(100)])
    meta_keywords = models.CharField(max_length=255, blank=True)
    meta_description = models.CharField(max_length=255, blank=True)
    meta_title = models.CharField(max_length=255, blank=True)
    # Один товар может лежать в нескольких категориях (таблица product_categories)
    categories = models.ManyToManyField(Category, db_table='product_categories',
                                        related_name='products', blank=True,
                                        verbose_name='Категории')

    class Meta:
        db_table = 'products'
        constraints = [models.CheckConstraint(condition=models.Q(discount_percent__lte=100), name='product_discount_0_100')]
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # У каждого билета всегда есть хотя бы стандартное изображение.
        if not self.image:
            self.image = 'img/ticket.svg'
        super().save(*args, **kwargs)


class ProductProperty(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='properties')
    property_name = models.CharField('Свойство', max_length=255)
    property_value = models.CharField('Значение', max_length=255)
    property_price = models.DecimalField('Цена', max_digits=20, decimal_places=2, default=0)

    class Meta:
        db_table = 'product_properties'
        verbose_name = 'Свойство'
        verbose_name_plural = 'Свойства'


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.CharField('Файл', max_length=255)
    title = models.CharField('Подпись', max_length=255, blank=True)

    class Meta:
        db_table = 'product_images'
        verbose_name = 'Изображение'
        verbose_name_plural = 'Изображения'


class UserManager(BaseUserManager):
    def create_user(self, email, name, password=None, **extra):
        user = self.model(email=self.normalize_email(email).lower(), name=name, **extra)
        user.set_password(password)          # пароль превращается в bcrypt-хэш
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, password):
        return self.create_user(email, name, password, role='admin')


class User(AbstractBaseUser):
    ROLES = [('user', 'Пользователь'), ('admin', 'Администратор')]

    name = models.CharField('Имя', max_length=100)
    email = models.EmailField('Email', unique=True)
    phone = models.CharField('Телефон', max_length=20, blank=True)
    password = models.CharField(max_length=128, db_column='password_hash')  # хэш пароля
    role = models.CharField('Роль', max_length=10, choices=ROLES, default='user')
    created_at = models.DateTimeField('Дата регистрации', auto_now_add=True)
    # поле last_login уже есть в AbstractBaseUser

    objects = UserManager()
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    class Meta:
        db_table = 'users'
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    # В Django-админку пускаем только роль admin
    @property
    def is_staff(self):
        return self.role == 'admin'

    def has_perm(self, perm, obj=None):
        return self.role == 'admin'

    def has_module_perms(self, app_label):
        return self.role == 'admin'

    def __str__(self):
        return self.email


class UserSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_sessions')
    session_token = models.CharField(max_length=64, unique=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = 'user_sessions'


class UserAction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='actions')
    action = models.CharField('Действие', max_length=50)
    page = models.CharField('Страница', max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_actions'
        ordering = ['-created_at']


class Feedback(models.Model):
    SUBJECTS = [('tickets', 'Вопрос по билетам'), ('partners', 'Сотрудничество'), ('other', 'Другое')]
    STATUSES = [('new', 'Новое'), ('in_progress', 'В работе'), ('resolved', 'Решено')]

    # Форма доступна и гостям, поэтому user может быть пустым
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True,
                             related_name='feedbacks')
    name = models.CharField('Имя', max_length=100)
    email = models.EmailField('Email')
    phone = models.CharField('Телефон', max_length=20, blank=True)
    subject = models.CharField('Тема', max_length=20, choices=SUBJECTS)
    message = models.TextField('Сообщение')
    rating = models.PositiveSmallIntegerField('Оценка', null=True, blank=True)
    status = models.CharField('Статус', max_length=20, choices=STATUSES, default='new')
    created_at = models.DateTimeField('Дата', auto_now_add=True)

    class Meta:
        db_table = 'feedback'
        ordering = ['-created_at']
        verbose_name = 'Обращение'
        verbose_name_plural = 'Обращения'
        constraints = [  # проверка на уровне БД: оценка от 1 до 5
            models.CheckConstraint(
                condition=models.Q(rating__isnull=True) | models.Q(rating__gte=1, rating__lte=5),
                name='feedback_rating_1_5'),
        ]


class CartItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cart_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveSmallIntegerField(default=1)

    class Meta:
        db_table = 'cart_items'
        constraints = [models.UniqueConstraint(fields=['user', 'product'], name='unique_cart_item')]


class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    request_id = models.UUIDField()
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField('Статус', max_length=20, default='new', choices=[('new', 'Создан, не оплачен')])
    subtotal = models.DecimalField('Без скидки', max_digits=24, decimal_places=2)
    discount = models.DecimalField('Скидка', max_digits=24, decimal_places=2)
    total = models.DecimalField('Итого', max_digits=24, decimal_places=2)

    class Meta:
        ordering = ['-created_at', '-id']
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        constraints = [models.UniqueConstraint(fields=['user', 'request_id'], name='unique_order_request')]


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    name = models.CharField('Билет', max_length=255)
    price = models.DecimalField('Исходная цена', max_digits=20, decimal_places=2)
    unit_price = models.DecimalField('Цена со скидкой', max_digits=20, decimal_places=2)
    quantity = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(20)])

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(quantity__gte=1, quantity__lte=20), name='order_quantity_1_20')]
