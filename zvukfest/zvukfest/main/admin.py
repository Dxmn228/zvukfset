from django.contrib import admin

from .models import (Category, Feedback, Product, ProductImage, ProductProperty,
                     User, UserAction, UserSession, Order, OrderItem)


class PropertyInline(admin.TabularInline):
    model = ProductProperty
    extra = 1


class ImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'discount_percent', 'available', 'manufacturer_id')
    list_editable = ('price', 'discount_percent', 'available')
    list_filter = ('available', 'categories')
    search_fields = ('name', 'description')
    filter_horizontal = ('categories',)
    inlines = [PropertyInline, ImageInline]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'alias')


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'name', 'role', 'created_at', 'last_login')
    list_filter = ('role',)
    search_fields = ('email', 'name')
    fields = ('name', 'email', 'phone', 'role', 'created_at', 'last_login')
    readonly_fields = ('created_at', 'last_login')

    def has_add_permission(self, request):    # пользователи создаются через регистрацию на сайте
        return False


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):        # модерация обращений
    list_display = ('subject', 'name', 'email', 'rating', 'status', 'created_at')
    list_filter = ('status', 'subject', 'rating')
    search_fields = ('name', 'email', 'message')
    actions = ['take_to_work', 'mark_resolved']

    @admin.action(description='Взять в работу')
    def take_to_work(self, request, queryset):
        queryset.update(status='in_progress')

    @admin.action(description='Отметить решённым')
    def mark_resolved(self, request, queryset):
        queryset.update(status='resolved')


admin.site.register(UserAction)
admin.site.register(UserSession)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'name', 'price', 'unit_price', 'quantity')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'created_at', 'status', 'total')
    readonly_fields = ('user', 'request_id', 'created_at', 'status', 'subtotal', 'discount', 'total')
    inlines = [OrderItemInline]

    def has_add_permission(self, request):
        return False
