from django import forms
from .models import Cliente

AREAS_DIREITO = [
    ('', 'Selecione uma área'),
    ('TRABALHISTA', 'Trabalhista'),
    ('CIVIL', 'Cível'),
    ('FAMILIA', 'Família'),
    ('TRIBUTARIO', 'Tributário'),
    ('EMPRESARIAL', 'Empresarial'),
    ('CRIMINAL', 'Criminal'),
    ('OUTRO', 'Outro'),
]


class ClienteForm(forms.ModelForm):
    tipo = forms.ChoiceField(
        choices=Cliente.TIPO_CHOICES, # Usar as choices do modelo
        required=True,
        label="Tipo de Pessoa",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    area_direito = forms.ChoiceField(
        choices=AREAS_DIREITO,
        required=True,
        label="Área de Direito",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    lgpd_consentimento = forms.BooleanField(
        label='Concordo com o tratamento de dados conforme LGPD',
        required=True, # Torna o campo obrigatório
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    class Meta:
        model = Cliente
        fields = ['tipo', 'nome', 'cpf_cnpj', 'email', 'telefone', 'endereco', 'area_direito', 'observacoes', 'lgpd_consentimento']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'cpf_cnpj': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control'}),
            'endereco': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    def clean_cpf_cnpj(self):
        cpf_cnpj = self.cleaned_data.get('cpf_cnpj')

        # Remove pontuação para comparar com consistência
        filtro = Cliente.objects.filter(
            cpf_cnpj__iexact=cpf_cnpj.replace('.', '').replace('-', '').replace('/', '')
        )

        # Exclui a instância atual se estiver em edição
        if self.instance.pk:
            filtro = filtro.exclude(pk=self.instance.pk)

        if filtro.exists():
            raise forms.ValidationError('Já existe um cliente com esse CPF ou CNPJ cadastrado.')

        return cpf_cnpj