from django.urls import path
from .views import (
    ClienteListView,
    ClienteCreateView,
    ClienteDetailView,
    ClienteUpdateView,
)

app_name = 'clientes'

urlpatterns = [
    path('', ClienteListView.as_view(), name='lista'),  # Página principal: lista de clientes
    path('novo/', ClienteCreateView.as_view(), name='novo'),  # Cadastro de novo cliente
    path('<int:pk>/', ClienteDetailView.as_view(), name='detalhe'),  # Detalhes do cliente
    path('<int:pk>/editar/', ClienteUpdateView.as_view(), name='editar'),  # Edição do cliente
]
