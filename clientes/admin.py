from django.contrib import admin
from .models import Cliente

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nome', 'tipo', 'email', 'telefone', 'advogado_responsavel')
    list_filter = ('tipo', 'advogado_responsavel')
    search_fields = ('nome', 'cpf_cnpj', 'email')
    raw_id_fields = ('advogado_responsavel',)