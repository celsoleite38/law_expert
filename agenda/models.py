from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model

from clientes.models import Cliente

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
        related_name="compromissos",
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
    
    criado_em = models.DateTimeField(auto_now_add=True)
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
        # Remove a lógica condicional do criado_em
        self.full_clean()  # Garante que clean() seja executado antes do save
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
    
    @property
    def nome_cliente(self):
        """Retorna o nome do cliente de forma segura"""
        if self.processo and self.processo.cliente:
            return self.processo.cliente.nome
        elif self.cliente:
            return self.cliente.nome
        return "Cliente não definido"

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


class HorarioAtendimento(models.Model):
    DIAS_DA_SEMANA = [
        ('segunda', 'Segunda-feira'),
        ('terca', 'Terça-feira'),
        ('quarta', 'Quarta-feira'),
        ('quinta', 'Quinta-feira'),
        ('sexta', 'Sexta-feira'),
        ('sabado', 'Sábado'),
        ('domingo', 'Domingo'),
    ]
    
    profissional = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'groups__name': 'advogados'},
        related_name='horarios_atendimento',
        verbose_name=_("Profissional")
    )
    dia_semana = models.CharField(
        max_length=10, 
        choices=DIAS_DA_SEMANA,
        verbose_name=_("Dia da semana")
    )
    hora_inicio = models.TimeField(verbose_name=_("Hora de início"))
    hora_fim = models.TimeField(verbose_name=_("Hora de término"))
    duracao_slot = models.IntegerField(
        default=60, 
        help_text=_("Duração de cada slot em minutos"),
        verbose_name=_("Duração do slot")
    )
    max_compromissos = models.IntegerField(
        default=1, 
        help_text=_("Máximo de compromissos por slot"),
        verbose_name=_("Máx. compromissos/slot")
    )
    ativo = models.BooleanField(default=True, verbose_name=_("Ativo"))

    class Meta:
        verbose_name = _("Horário de Atendimento")
        verbose_name_plural = _("Horários de Atendimento")
        unique_together = ['profissional', 'dia_semana']
        ordering = ['profissional', 'dia_semana', 'hora_inicio']

    def clean(self):
        """Validação dos horários"""
        super().clean()
        
        if self.hora_fim <= self.hora_inicio:
            raise ValidationError(_("Hora de término deve ser posterior à hora de início"))
        
        if self.duracao_slot < 15:
            raise ValidationError(_("Duração mínima do slot é 15 minutos"))
        
        if self.max_compromissos < 1:
            raise ValidationError(_("Máximo de compromissos deve ser pelo menos 1"))

    def __str__(self):
        return f"{self.profissional.get_full_name()} - {self.get_dia_semana_display()} {self.hora_inicio.strftime('%H:%M')}-{self.hora_fim.strftime('%H:%M')}"

    @property
    def duracao_total(self):
        """Calcula a duração total em minutos"""
        from datetime import datetime, timedelta
        inicio = datetime.combine(datetime.today(), self.hora_inicio)
        fim = datetime.combine(datetime.today(), self.hora_fim)
        return int((fim - inicio).total_seconds() / 60)

    @property
    def total_slots(self):
        """Calcula o número total de slots disponíveis"""
        return self.duracao_total // self.duracao_slot


class BloqueioAgenda(models.Model):
    TIPOS_BLOQUEIO = [
        ('ferias', '🏖️ Férias'),
        ('congresso', '🎤 Congresso/Evento'),
        ('treinamento', '📚 Treinamento'),
        ('pessoal', '👤 Assunto Pessoal'),
        ('emergencia', '🚨 Emergência'),
        ('outro', '📌 Outro'),
    ]
    
    profissional = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'groups__name': 'advogados'},
        related_name='bloqueios_agenda',
        verbose_name=_("Profissional")
    )
    titulo = models.CharField(max_length=200, verbose_name=_("Título"))
    descricao = models.TextField(
        blank=True, 
        null=True,
        verbose_name=_("Descrição")
    )
    data_inicio = models.DateField(verbose_name=_("Data início"))
    data_fim = models.DateField(verbose_name=_("Data fim"))
    hora_inicio = models.TimeField(
        blank=True, 
        null=True,
        verbose_name=_("Hora início"),
        help_text=_("Opcional para bloqueios de dia todo")
    )
    hora_fim = models.TimeField(
        blank=True, 
        null=True,
        verbose_name=_("Hora fim"),
        help_text=_("Opcional para bloqueios de dia todo")
    )
    dia_todo = models.BooleanField(
        default=False,
        verbose_name=_("Dia todo"),
        help_text=_("Bloqueio para o dia inteiro")
    )
    tipo_bloqueio = models.CharField(
        max_length=20, 
        choices=TIPOS_BLOQUEIO,
        verbose_name=_("Tipo de bloqueio")
    )
    ativo = models.BooleanField(default=True, verbose_name=_("Ativo"))
    
    criado_em = models.DateTimeField( null=True,  # Permite nulo temporariamente
    blank=True,
    verbose_name=_("Criado em"))
    atualizado_em = models.DateTimeField( null=True,  # Permite nulo temporariamente  
    blank=True,
    verbose_name=_("Atualizado em"))

    class Meta:
        verbose_name = _("Bloqueio de Agenda")
        verbose_name_plural = _("Bloqueios de Agenda")
        ordering = ['-data_inicio', '-data_fim']

    def clean(self):
        """Validação dos dados do bloqueio"""
        super().clean()
        
        if self.data_fim < self.data_inicio:
            raise ValidationError(_("Data fim não pode ser anterior à data início"))
        
        if not self.dia_todo:
            if not self.hora_inicio or not self.hora_fim:
                raise ValidationError(_("Para bloqueio parcial, informe hora início e fim"))
            if self.hora_fim <= self.hora_inicio:
                raise ValidationError(_("Hora fim deve ser posterior à hora início"))
        else:
            # Para bloqueio de dia todo, limpa os horários
            self.hora_inicio = None
            self.hora_fim = None

    def __str__(self):
        periodo = f"{self.data_inicio} a {self.data_fim}" if self.data_inicio != self.data_fim else f"{self.data_inicio}"
        return f"{self.profissional.get_full_name()} - {self.titulo} ({periodo})"

    @property
    def periodo_formatado(self):
        """Retorna o período formatado"""
        if self.data_inicio == self.data_fim:
            return self.data_inicio.strftime('%d/%m/%Y')
        return f"{self.data_inicio.strftime('%d/%m/%Y')} a {self.data_fim.strftime('%d/%m/%Y')}"

    @property
    def horario_formatado(self):
        """Retorna o horário formatado"""
        if self.dia_todo:
            return "Dia todo"
        return f"{self.hora_inicio.strftime('%H:%M')} - {self.hora_fim.strftime('%H:%M')}"

    def esta_ativo(self):
        """Verifica se o bloqueio está ativo atualmente"""
        from django.utils import timezone
        hoje = timezone.now().date()
        return self.ativo and self.data_inicio <= hoje <= self.data_fim
    


class Compromisso(models.Model):
    # seus campos existentes...
    data_hora = models.DateTimeField()
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    # outros campos...
    
    def clean(self):
        # Validação de conflito de agendamento
        if self.cliente and self.data_hora:
            conflito = Compromisso.objects.filter(
                cliente=self.cliente,
                data_hora=self.data_hora
            ).exclude(pk=self.pk)  # Exclui a própria instância em caso de edição
            
            if conflito.exists():
                raise ValidationError({
                    'data_hora': 'Já existe um compromisso agendado para este cliente na data e hora selecionada. Por favor, escolha outro horário.'
                })
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['cliente', 'data_hora'],
                name='unique_compromisso_only_cliente_por_data'
            )
        ]

    def __str__(self):
        return f"{self.cliente} - {self.data_hora}"