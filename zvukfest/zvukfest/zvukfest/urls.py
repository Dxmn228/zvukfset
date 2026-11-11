from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

from main.views import page

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('main.urls')),
    path('', page),                                # главная
    path('<str:name>.html', page),                 # остальные html-страницы
    # css, js, картинки из папки frontend
    re_path(r'^(?P<path>(?:css|js|img|docs)/.+)$', serve, {'document_root': settings.FRONTEND_DIR}),
]