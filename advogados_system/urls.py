from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('usuarios/', include('usuarios.urls', namespace='usuarios')),
    path('processos/', include('processos.urls', namespace='processos')),
    path('agenda/', include('agenda.urls',  namespace='agenda')),
    path('financeiro/', include('financeiro.urls', namespace='financeiro')),
    path('clientes/', include('clientes.urls',  namespace='clientes') ),
    path('notificacoes/', include('notificacoes.urls', namespace='notificacoes')),
     # API Rest (opcional)
    #path('api/', include('api.urls')),
] 
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
