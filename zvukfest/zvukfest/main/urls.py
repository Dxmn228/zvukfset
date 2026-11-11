from django.urls import path

from . import views

urlpatterns = [
    path('health', views.health),
    path('register', views.register),
    path('login', views.login_view),
    path('logout', views.logout_view),
    path('profile', views.profile),
    path('password', views.change_password),
    path('feedback', views.feedback),
    path('search', views.search),
    path('actions', views.actions),
    path('products', views.products),
    path('products/<int:pk>', views.product_detail),
    path('cart', views.cart),
]