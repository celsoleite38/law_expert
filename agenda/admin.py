from django.contrib import admin
from .models import Audiencia, LogAudiencia

@admin.register(Audiencia)
class AudienciaAdmin(admin.ModelAdmin):
    list_display = ('tipo', 'data_hora', 'vinculacao', 'local', 'criado_por')
    list_filter = ('tipo', 'processo', 'cliente', 'criado_por')
    search_fields = ('processo__numero', 'cliente__nome', 'local')
    date_hierarchy = 'data_hora'
    readonly_fields = ('criado_em', 'atualizado_em')
    
    fieldsets = (
        ('Vinculação', {
            'fields': (('processo', 'cliente'),)
        }),
        ('Detalhes do Compromisso', {
            'fields': ('data_hora', 'tipo', 'local', 'vara')
        }),
        ('Resultado', {
            'fields': ('resultado',),
            'classes': ('collapse',)
        }),
        ('Metadados', {
            'fields': ('criado_por', 'criado_em', 'atualizado_em'),
            'classes': ('collapse',)
        })
    )

    def vinculacao(self, obj):
        return obj.vinculacao
    vinculacao.short_description = 'Vinculação'
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:  # Se for novo
            obj.criado_por = request.user
        super().save_model(request, obj, form, change)

@admin.register(LogAudiencia)
class LogAudienciaAdmin(admin.ModelAdmin):
    list_display = ('audiencia', 'alterado_por', 'data_anterior', 'nova_data', 'data_alteracao')
    list_filter = ('alterado_por', 'data_alteracao')
    search_fields = ('audiencia__id', 'motivo')
    readonly_fields = ('data_alteracao',)
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('audiencia', 'alterado_por')
        }),
        ('Alteração de Data', {
            'fields': ('data_anterior', 'nova_data')
        }),
        ('Registro', {
            'fields': ('motivo', 'data_alteracao')
        })
    )