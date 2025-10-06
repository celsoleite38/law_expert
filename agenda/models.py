from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model

User = get_user_model()

class Audiencia(models.Model):
    TIPOS_AUDIENCIA = [
        ('forum', '🧑‍⚖️ Audiência Fórum'),
        ('virtual', '💻 Audiência Virtual'),
        ('atendimento', '📞 Atendimento'),
        ('sessao', '⚖️ Sessão de Julgamento'),
        ('conciliacao', '🤝 Mediação / Conciliação'),
        ('reuniao', '📋 Reunião Estratégica'),
    ]

    processo = models.ForeignKey(
        'processos.Processo',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="audiencias",
        verbose_name=_("Processo vinculado"),
        help_text=_("Opcional se cliente estiver preenchido")
    )
    
    cliente = models.ForeignKey(
        'clientes.Cliente',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="compromissos",  # Nome mais descritivo
        verbose_name=_("Cliente direto"),
        help_text=_("Opcional se processo estiver preenchido")
    )
    
    data_hora = models.DateTimeField(
        verbose_name=_("Data e hora"),
        help_text=_("Data e hora do compromisso")
    )
    
    tipo = models.CharField(
        max_length=50,
        choices=TIPOS_AUDIENCIA,
        verbose_name=_("Tipo de compromisso")
    )
    
    local = models.CharField(
        max_length=200,
        verbose_name=_("Local"),
        default=_("Escritório")
    )
    
    vara = models.CharField(
        max_length=200,
        verbose_name=_("Vara/Fórum"),
        blank=True,
        default=''
    )
    
    resultado = models.TextField(
        verbose_name=_("Resultado"),
        blank=True,
        null=True
    )
    
    criado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='compromissos_criados',
        verbose_name=_("Criado por")
    )
    
    criado_em = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Compromisso")
        verbose_name_plural = _("Compromissos")
        ordering = ['data_hora']
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(processo__isnull=False, cliente__isnull=True) | 
                    models.Q(processo__isnull=True, cliente__isnull=False)
                ),
                name='check_processo_ou_cliente_exclusivos'
            ),
            models.UniqueConstraint(
                fields=['processo', 'data_hora'],
                condition=models.Q(processo__isnull=False),
                name='unique_compromisso_processo_por_data'
            ),
            models.UniqueConstraint(
                fields=['cliente', 'data_hora'],
                condition=models.Q(cliente__isnull=False),
                name='unique_compromisso_cliente_por_data'
            )
        ]

    def clean(self):
        """Validação em nível de aplicação"""
        super().clean()
        
        if self.processo and self.cliente:
            raise ValidationError({
                'cliente': _("Selecione apenas Processo OU Cliente."),
                'processo': _("Selecione apenas Processo OU Cliente.")
            })
            
        if not self.processo and not self.cliente:
            raise ValidationError({
                'cliente': _("Informe um Cliente se não houver Processo."),
                'processo': _("Informe um Processo se não houver Cliente.")
            })

    def save(self, *args, **kwargs):
        if not self.pk and not self.criado_por:  # Se for novo e não tiver criador
            from django.contrib.auth import get_user_model
            User = get_user_model()
            if hasattr(self, 'request_user'):  # Se passou o usuário no request
                self.criado_por = self.request_user
        super().save(*args, **kwargs)

    def __str__(self):
        base = f"{self.get_tipo_display()} {self.data_hora.strftime('%d/%m/%Y %H:%M')}"
        if self.processo:
            return f"{base} (Proc. {self.processo.numero})"
        return f"{base} (Cliente: {self.cliente.nome})"

    @property
    def vinculacao(self):
        """Retorna a string de vinculação para uso no admin"""
        if self.processo:
            return f"Processo: {self.processo.numero}"
        elif self.cliente:
            return f"Cliente: {self.cliente.nome}"
        return "Sem vinculação"
    
class LogAudiencia(models.Model):
    audiencia = models.ForeignKey(
        Audiencia,
        on_delete=models.CASCADE,
        related_name='logs'
    )
    alterado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_("Usuário responsável")
    )
    data_anterior = models.DateTimeField(
        verbose_name=_("Data original")
    )
    nova_data = models.DateTimeField(
        verbose_name=_("Nova data")
    )
    data_alteracao = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Data do registro")
    )
    motivo = models.TextField(
        blank=True,
        verbose_name=_("Motivo da alteração")
    )

    class Meta:
        verbose_name = _("Log de alteração")
        verbose_name_plural = _("Logs de alteração")
        ordering = ['-data_alteracao']

    def __str__(self):
        return _("Alteração em {audiencia} por {usuario}").format(
            audiencia=self.audiencia,
            usuario=self.alterado_por or _("Sistema")
        )