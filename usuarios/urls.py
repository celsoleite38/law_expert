from django.urls import path
from . import views

app_name = 'usuarios'

urlpatterns = [
    # Autenticação e conta
    path('login/', views.logar_usuario, name='login'),
    path('logout/', views.logout_usuario, name='logout'),
    path('cadastro/', views.cadastrar_usuario, name='cadastro'),
    path('ativar/<str:token>/', views.ativar_conta, name='ativar_conta'),

    # Painel
    path('dashboard/', views.dashboard, name='dashboard'),

    # Perfil do advogado
    path('editar/', views.editar_advogado, name='editar_advogado'),

    # Gestão de colaboradores
    path('colaboradores/cadastrar/', views.colaborador, name='colaborador'),
    path('colaborador/<int:pk>/editar/', views.editar_colaborador, name='editar_colaborador'),
    path('colaboradores/<int:colaborador_id>/permissoes/', views.gerenciar_permissoes_colaborador, name='gerenciar_permissoes'),
    path('colaboradores/<int:colaborador_id>/alterar-senha/', views.alterar_senha_colaborador, name='alterar_senha_colaborador'),

    # Clientes
    path('clientes/', views.listar_clientes, name='listar_clientes'),
    path('clientes/cadastrar/', views.cadastrar_cliente, name='cadastrar_cliente'),

    # Processos
    path('processos/', views.listar_processos, name='listar_processos'),
    
    path('diagnostico/', views.diagnostico_acesso_colaborador, name='diagnostico_acesso'),

]
