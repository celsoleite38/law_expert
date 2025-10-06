from django.db import models
from django.contrib.auth import get_user_model
#from usuarios.models import Usuario
from clientes.models import Cliente # Importa o modelo Cliente do app clientes

User = get_user_model()

class Processo(models.Model):
    STATUS_CHOICES = [
        ('ANDAMENTO', 'Em Andamento'),
        ('ARQUIVADO', 'Arquivado'),
        ('CONCLUIDO', 'Concluído')
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
    
    numero = models.CharField(max_length=50, unique=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    advogado_responsavel = models.ForeignKey(User, on_delete=models.PROTECT)
    descricao = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ANDAMENTO')
    area_direito = models.CharField(
        max_length=20,
        choices=AREAS_DIREITO,
        verbose_name='Área de Atuação do Processo',
        blank=True, # Permite que o campo seja opcional
        null=True # Permite que o campo seja nulo no banco de dados
    )
    data_cadastro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Processo'
        verbose_name_plural = 'Processos'
        ordering = ['-data_cadastro']

    def __str__(self):
        return f"{self.numero} - {self.cliente.nome}"

class Andamento(models.Model):
    TIPO_CHOICES = [
        ('PETICAO', 'Petição'),
        ('AUDIENCIA', 'Audiência'),
        ('SENTENCA', 'Sentença'),
        ('RECURSO', 'Recurso'),
        ('OUTROS', 'Outros')
    ]
    
    processo = models.ForeignKey(Processo, on_delete=models.CASCADE, related_name='andamentos')
    data = models.DateField()
    descricao = models.TextField()
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    usuario = models.ForeignKey(User, on_delete=models.PROTECT)
    arquivo = models.FileField(upload_to='andamentos/', blank=True, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Andamento Processual'
        verbose_name_plural = 'Andamentos Processuais'
        ordering = ['-data']

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.processo.numero}" 
