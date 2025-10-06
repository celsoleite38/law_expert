# usuarios/admin.py

from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from .models import Ativacao, PerfilProfissional, Colaborador


# Personalizando a exibição dos usuários (opcional)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'is_active', 'is_staff', 'date_joined')
    search_fields = ('username', 'email')
    ordering = ('-date_joined',)

# Substitui o admin padrão por esta versão personalizada
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


@admin.register(Ativacao)
class AtivacaoAdmin(admin.ModelAdmin):
    list_display = ('user', 'email', 'ativo', 'token')
    list_filter = ('ativo',)
    search_fields = ('user__username', 'email', 'token')


#@admin.register(PerfilProfissional)
#class PerfilProfissionalAdmin(admin.ModelAdmin):
#    list_display = ('usuario', 'nome_completo', 'cpf', 'crefito', 'nomeclinica')
#    search_fields = ('nome_completo', 'cpf', 'crefito', 'usuario__username')



@admin.register(Colaborador)
class ColaboradorAdmin(admin.ModelAdmin):
    list_display = ('nome', 'email', 'usuario', 'funcao', 'advogado_responsavel')
    list_filter = ('funcao', 'advogado_responsavel')
    search_fields = ('nome', 'email', 'usuario__username', 'advogado_responsavel__username')

from usuarios.models import PermissaoColaborador

@admin.register(PermissaoColaborador)
class PermissaoColaboradorAdmin(admin.ModelAdmin):
    list_display = ('colaborador',)
    list_filter = ('colaborador__funcao',)
    search_fields = ('colaborador__nome', 'colaborador__email')

    fieldsets = (
        ('👥 Clientes', {
            'fields': [
                'listar_clientes', 'visualizar_cliente', 'cadastrar_cliente',
                'editar_cliente', 'excluir_cliente', 'exportar_clientes',
            ],
        }),
        ('⚖️ Processos', {
            'fields': [
                'listar_processos', 'visualizar_processo', 'cadastrar_processo',
                'editar_processo', 'excluir_processo', 'atualizar_status_processo',
            ],
        }),
        ('📅 Agenda e Audiências', {
            'fields': [
                'ver_agenda', 'adicionar_evento', 'editar_evento',
                'excluir_evento', 'compartilhar_agenda', 'editar_audiencias',
            ],
        }),
        ('📦 Documentos', {
            'fields': [
                'acessar_documentos', 'upload_documento', 'download_documento',
                'excluir_documento', 'visualizar_documentos',
            ],
        }),
        ('⚙️ Sistema', {
            'fields': [
                'gerenciar_colaboradores', 'configurar_layout', 'visualizar_relatorios',
            ],
        }),
    )
