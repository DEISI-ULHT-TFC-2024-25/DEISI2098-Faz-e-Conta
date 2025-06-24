from django import forms
from data_hub.models import *

class ImportFileForm(forms.Form):
    file = forms.FileField(label="Choose a JSON file")


class TransacaoForm(forms.ModelForm):
    class Meta:
        model = Transacao
        fields = ['aluno_id', 'valor', 'descricao', 'tipo_transacao']
        widgets = {
            'tipo_transacao': forms.HiddenInput(),
        }
