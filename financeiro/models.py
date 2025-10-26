from django.db import models
from django.contrib.auth.models import User
from processos.models import Processo


class FormaPagamento(models.Model):
    nome = models.CharField(max_length=50)
    descricao = models.TextField(blank=True)
    usuario_criador = models.ForeignKey(User, on_delete=models.CASCADE)
    
    def __str__(self):
        return self.nome

class CondicaoPagamento(models.Model):
    nome = models.CharField(max_length=50)  # Ex: "À vista", "3x", "5x"
    numero_parcelas = models.IntegerField(default=1)
    intervalo_dias = models.IntegerField(default=30)  # Dias entre parcelas
    usuario_criador = models.ForeignKey(User, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"{self.nome} ({self.numero_parcelas}x)"

class ParcelaHonorario(models.Model):
    honorario = models.ForeignKey('Honorario', on_delete=models.CASCADE, related_name='parcelas')
    numero_parcela = models.IntegerField()
    valor_parcela = models.DecimalField(max_digits=10, decimal_places=2)
    data_vencimento = models.DateField()
    transacao = models.OneToOneField('TransacaoFinanceira', on_delete=models.CASCADE, null=True, blank=True)
    conta_a_receber = models.OneToOneField('ContaAReceber', on_delete=models.CASCADE, null=True, blank=True)
    pago = models.BooleanField(default=False)
    data_pagamento = models.DateField(null=True, blank=True)
    
    class Meta:
        ordering = ['numero_parcela']
    
    def __str__(self):
        return f"Parcela {self.numero_parcela} - {self.honorario.processo.numero}"

class CategoriaFinanceira(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    tipo = models.CharField(max_length=10, choices=[('RECEITA', 'Receita'), ('DESPESA', 'Despesa')])
    usuario_criador = models.ForeignKey(User, on_delete=models.CASCADE, related_name='categorias_criadas')

    def __str__(self):
        return f'{self.nome} ({self.tipo})'

class TransacaoFinanceira(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transacoes_financeiras')
    categoria = models.ForeignKey(CategoriaFinanceira, on_delete=models.SET_NULL, null=True, blank=True)
    descricao = models.CharField(max_length=255)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data_transacao = models.DateField()
    tipo = models.CharField(max_length=10, choices=[('RECEITA', 'Receita'), ('DESPESA', 'Despesa')])
    processo = models.ForeignKey(Processo, on_delete=models.SET_NULL, null=True, blank=True)
    data_criacao = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data_transacao']

    def __str__(self):
        return f'{self.tipo} - {self.descricao} - {self.valor}'

class Honorario(models.Model):
    transacao = models.OneToOneField(TransacaoFinanceira, on_delete=models.CASCADE, default=1, related_name='honorario_transacao')
    processo = models.ForeignKey(Processo, on_delete=models.CASCADE)
    forma_pagamento = models.ForeignKey(FormaPagamento, on_delete=models.SET_NULL, null=True, blank=True)
    condicao_pagamento = models.ForeignKey(CondicaoPagamento, on_delete=models.SET_NULL, null=True, blank=True)
    parcelado = models.BooleanField(default=False)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f'Honorário do Processo {self.processo.numero_processo} - {self.transacao.valor}'

    def save(self, *args, **kwargs):
        if self.transacao:
            self.valor_total = self.transacao.valor
        super().save(*args, **kwargs)

class ContaAPagar(models.Model):
    transacao = models.OneToOneField(TransacaoFinanceira, on_delete=models.CASCADE, related_name='conta_a_pagar')
    data_vencimento = models.DateField()
    data_pagamento = models.DateField(null=True, blank=True)
    pago = models.BooleanField(default=False)

    class Meta:
        ordering = ['data_vencimento']

    def __str__(self):
        return f'Pagar: {self.transacao.descricao} - {self.transacao.valor} (Venc: {self.data_vencimento})'

class ContaAReceber(models.Model):
    transacao = models.OneToOneField(TransacaoFinanceira, on_delete=models.CASCADE, related_name='conta_a_receber')
    data_vencimento = models.DateField()
    data_recebimento = models.DateField(null=True, blank=True)
    recebido = models.BooleanField(default=False)
    honorario_vinculado = models.OneToOneField(Honorario, on_delete=models.SET_NULL, null=True, blank=True, related_name='conta_a_receber_honorario')

    class Meta:
        ordering = ['data_vencimento']

    def __str__(self):
        return f'Receber: {self.transacao.descricao} - {self.transacao.valor} (Venc: {self.data_vencimento})'
    
