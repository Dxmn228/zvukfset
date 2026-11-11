from django.contrib import admin

from .models import (Category, Feedback, Product, ProductImage, ProductProperty,
                     User, UserAction, UserSession)


class PropertyInline(admin.TabularInline):
    model = ProductProperty
    extra = 1


class ImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'available', 'manufacturer_id')   # по клику на заголовок колонки идёт сортировка
    list_editable = ('price', 'available')
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