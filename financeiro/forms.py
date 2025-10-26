from django import forms
from .models import CategoriaFinanceira, CondicaoPagamento, FormaPagamento, TransacaoFinanceira, ContaAPagar, ContaAReceber, Honorario
from processos.models import Processo

class CategoriaFinanceiraForm(forms.ModelForm):
    class Meta:
        model = CategoriaFinanceira
        fields = ["nome", "tipo"]
        widgets = {
            "nome": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Nome da Categoria"
            }),
            "tipo": forms.Select(attrs={
                "class": "form-select"
            }),
        }

    def __init__(self, *args, **kwargs):
        kwargs.pop('user', None)  # Remove user se existir (não é necessário para este form)
        super().__init__(*args, **kwargs)

class TransacaoFinanceiraForm(forms.ModelForm):
    class Meta:
        model = TransacaoFinanceira
        fields = ["categoria", "descricao", "valor", "data_transacao", "tipo", "processo"]
        widgets = {
            "categoria": forms.Select(attrs={
                "class": "form-select"
            }),
            "descricao": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Descrição da Transação"
            }),
            "valor": forms.NumberInput(attrs={
                "class": "form-control",
                "placeholder": "Valor",
                "step": "0.01"
            }),
            "data_transacao": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date"
            }),
            "tipo": forms.Select(attrs={
                "class": "form-select"
            }),
            "processo": forms.Select(attrs={
                "class": "form-select"
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # CORREÇÃO: Armazene o valor em 'user'
        super().__init__(*args, **kwargs)
        if user:
            self.fields["categoria"].queryset = CategoriaFinanceira.objects.filter(usuario_criador=user)
            self.fields["processo"].queryset = Processo.objects.filter(advogado_responsavel=user)

class ContaAPagarForm(forms.ModelForm):
    class Meta:
        model = ContaAPagar
        fields = ["data_vencimento", "pago", "data_pagamento"]
        widgets = {
            "data_vencimento": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date"
            }),
            "data_pagamento": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date"
            }),
            "pago": forms.CheckboxInput(attrs={
                "class": "form-check-input"
            }),
        }

    def __init__(self, *args, **kwargs):
        kwargs.pop('user', None)  # CORREÇÃO: Adicione este método
        super().__init__(*args, **kwargs)

class ContaAReceberForm(forms.ModelForm):
    class Meta:
        model = ContaAReceber
        fields = ["data_vencimento", "recebido", "data_recebimento"]
        widgets = {
            "data_vencimento": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date"
            }),
            "data_recebimento": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date"
            }),
            "recebido": forms.CheckboxInput(attrs={
                "class": "form-check-input"
            }),
        }

    def __init__(self, *args, **kwargs):
        kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

class HonorarioForm(forms.ModelForm):
    class Meta:
        model = Honorario
        fields = ["processo"]
        widgets = {
            "processo": forms.Select(attrs={
                "class": "form-select"
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # CORREÇÃO: Armazene o valor em 'user'
        super().__init__(*args, **kwargs)
        if user:
            self.fields["processo"].queryset = Processo.objects.filter(advogado_responsavel=user)
            
            FormaPagamento.objects.get_or_create(
            nome='Dinheiro',
            usuario_criador=user,
            defaults={'descricao': 'Pagamento em espécie'}
        )
        FormaPagamento.objects.get_or_create(
            nome='Transferência',
            usuario_criador=user,
            defaults={'descricao': 'Transferência bancária'}
        )
        
        # Criar condições de pagamento padrão
        CondicaoPagamento.objects.get_or_create(
            nome='À vista',
            numero_parcelas=1,
            usuario_criador=user,
            defaults={'intervalo_dias': 0}
        )
        CondicaoPagamento.objects.get_or_create(
            nome='2x',
            numero_parcelas=2,
            usuario_criador=user,
            defaults={'intervalo_dias': 30}
        )
        CondicaoPagamento.objects.get_or_create(
            nome='3x',
            numero_parcelas=3,
            usuario_criador=user,
            defaults={'intervalo_dias': 30}
        )
        
        self.fields['forma_pagamento'].queryset = FormaPagamento.objects.filter(usuario_criador=user)
        self.fields['condicao_pagamento'].queryset = CondicaoPagamento.objects.filter(usuario_criador=user)
            
class FormaPagamentoForm(forms.ModelForm):
    class Meta:
        model = FormaPagamento
        fields = ['nome', 'descricao']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class CondicaoPagamentoForm(forms.ModelForm):
    class Meta:
        model = CondicaoPagamento
        fields = ['nome', 'numero_parcelas', 'intervalo_dias']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_parcelas': forms.NumberInput(attrs={'class': 'form-control'}),
            'intervalo_dias': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class HonorarioForm(forms.ModelForm):
    parcelar = forms.BooleanField(
        required=False, 
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_parcelar'}),
        label='Parcelar honorário'
    )
    
    class Meta:
        model = Honorario
        fields = ['processo', 'forma_pagamento', 'condicao_pagamento', 'parcelar']
        widgets = {
            'processo': forms.Select(attrs={'class': 'form-select'}),
            'forma_pagamento': forms.Select(attrs={'class': 'form-select'}),
            'condicao_pagamento': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['processo'].queryset = Processo.objects.filter(advogado_responsavel=user)
            self.fields['forma_pagamento'].queryset = FormaPagamento.objects.filter(usuario_criador=user)
            self.fields['condicao_pagamento'].queryset = CondicaoPagamento.objects.filter(usuario_criador=user)