from django.db import models
from processos.models import Processo

class Honorario(models.Model):
    processo = models.ForeignKey(Processo, on_delete=models.CASCADE)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data_vencimento = models.DateField()
    pago = models.BooleanField(default=False)