from django.db import models
from django.core.validators import MinLengthValidator, RegexValidator
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()

class Cliente(models.Model):
    TIPO_CHOICES = [
        ('PF', 'Pessoa Física'),
        ('PJ', 'Pessoa Jurídica'),
    ]

    AREAS_DIREITO = [
        ('TRABALHISTA', 'Trabalhista'),
        ('CIVIL', 'Cível'),
        ('FAMILIA', 'Família'),
        ('TRIBUTARIO', 'Tributário'),
        ('EMPRESARIAL', 'Empresarial'),
        ('CRIMINAL', 'Criminal'),
        ('OUTRO', 'Outro'),
    ]

    tipo = models.CharField(max_length=2, choices=TIPO_CHOICES, default='PF')
    nome = models.CharField(max_length=100, verbose_name='Nome Completo/Razão Social')
    cpf_cnpj = models.CharField(
        max_length=18,
        unique=True,
        verbose_name='CPF/CNPJ',
        validators=[
            MinLengthValidator(11),
            RegexValidator(regex='^[0-9]*$', message='Apenas números são permitidos')
        ]
    )
    email = models.EmailField(blank=True, null=True)
    telefone = models.CharField(max_length=15)

    advogado_responsavel = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='clientes_atendidos',
        verbose_name='Advogado Responsável'
    )

    area_direito = models.CharField(
        max_length=20,
        choices=AREAS_DIREITO,
        verbose_name='Área de Atuação'
    )

    endereco = models.TextField(blank=True, null=True)
    observacoes = models.TextField(blank=True, null=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)

    lgpd_consentimento = models.BooleanField(
        verbose_name='Consentimento LGPD',
        default=False
    )

    def clean(self):
        cpf_cnpj = self.cpf_cnpj.replace('.', '').replace('-', '').replace('/', '')
        if self.tipo == 'PF' and len(cpf_cnpj) != 11:
            raise ValidationError({'cpf_cnpj': 'CPF deve conter 11 dígitos'})
        if self.tipo == 'PJ' and len(cpf_cnpj) != 14:
            raise ValidationError({'cpf_cnpj': 'CNPJ deve conter 14 dígitos'})

    def save(self, *args, **kwargs):
        print(f"Salvando cliente {self.nome} (CPF/CNPJ: {self.cpf_cnpj})")
        super().save(*args, **kwargs)
        print(f"Cliente salvo com ID: {self.id}")

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.nome}"

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['nome']
