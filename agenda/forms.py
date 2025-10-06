from django import forms
from .models import Audiencia
from clientes.models import Cliente
from processos.models import Processo

class AudienciaForm(forms.ModelForm):

    class Meta:
        model = Audiencia
        # 1. Lista de campos correta, usando apenas strings.
        fields = ['processo', 'cliente', 'data_hora', 'tipo', 'local', 'vara', 'resultado']
        
        widgets = {
            'processo': forms.Select(attrs={'class': 'form-select'}),
            'cliente': forms.Select(attrs={'class': 'form-select'}), # Chave 'cliente' como string
            'data_hora': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-control'},
                format='%Y-%m-%dT%H:%M'
            ),
            'tipo': forms.Select(attrs={'class': 'form-select tipo-select'}),
            'local': forms.TextInput(attrs={'class': 'form-control'}),
            'vara': forms.TextInput(attrs={'class': 'form-control'}),
            'resultado': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        # Lógica de campos não obrigatórios
        self.fields['processo'].required = False
        self.fields['cliente'].required = False

        # Lógica de filtragem dos dropdowns
        if request:
            from usuarios.utils import advogado_dono
            dono = advogado_dono(request)
            self.fields['processo'].queryset = Processo.objects.filter(advogado_responsavel=dono).order_by('-data_cadastro')
            self.fields['cliente'].queryset = Cliente.objects.filter(advogado_responsavel=dono).order_by('nome')

        # ==================================================
        # INÍCIO DA LÓGICA DE EDIÇÃO CORRIGIDA
        # ==================================================
        # Verifica se estamos editando um objeto existente
        if self.instance and self.instance.pk:
            # Formata a data e hora para o widget (como já tínhamos)
            if self.instance.data_hora:
                self.initial['data_hora'] = self.instance.data_hora.strftime('%Y-%m-%dT%H:%M')
            
            # AQUI ESTÁ A NOVA LÓGICA:
            # Se o compromisso já tem um processo, desabilita a escolha de cliente.
            if self.instance.processo:
                self.fields['cliente'].disabled = True
            # Se o compromisso já tem um cliente (e não um processo), desabilita a escolha de processo.
            elif self.instance.cliente:
                self.fields['processo'].disabled = True

    def clean(self):
        # 6. Lógica de validação "um ou outro".
        cleaned_data = super().clean()
        processo = cleaned_data.get("processo")
        cliente = cleaned_data.get("cliente")

        if processo and cliente:
            raise forms.ValidationError(
                "Um compromisso deve ser ligado a um Processo OU a um Cliente, não a ambos.",
                code='invalid_choice'
            )
        if not processo and not cliente:
            raise forms.ValidationError(
                "Um compromisso precisa estar ligado a um Processo ou a um Cliente.",
                code='required'
            )
        
        return cleaned_data
