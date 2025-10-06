from django import forms
from .models import Processo, Andamento
from clientes.models import Cliente
from usuarios.utils import advogado_dono

class ProcessoForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)
        if self.request:
            dono = advogado_dono(self.request)
            self.fields["cliente"].queryset = Cliente.objects.filter(advogado_responsavel=dono)

    class Meta:
        model = Processo
        fields = ["numero", "cliente", "descricao", "status", "area_direito"]
        widgets = {
            "numero": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex: 0001234-56.2023.8.26.0000"}),
            "cliente": forms.Select(attrs={"class": "form-control"}),
            "descricao": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "status": forms.Select(attrs={"class": "form-control"}),
            "area_direito": forms.Select(attrs={"class": "form-control"}),
        }

    def clean_numero(self):
        numero = self.cleaned_data.get('numero')
        processo_qs = Processo.objects.filter(numero__iexact=numero)
        if self.instance.pk:
            processo_qs = processo_qs.exclude(pk=self.instance.pk)
        if processo_qs.exists():
            raise forms.ValidationError("Já existe um processo com esse número cadastrado.")
        return numero


class AndamentoForm(forms.ModelForm):
    class Meta:
        model = Andamento
        fields = ["data", "descricao", "tipo", "arquivo"]
        widgets = {
            "data": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "descricao": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "tipo": forms.Select(attrs={"class": "form-control"}),
            "arquivo": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }
