from django import forms
from data_hub.models import *

class ImportFileForm(forms.Form):
    file = forms.FileField(label="Choose a CSV or JSON file")
    replace = forms.BooleanField(required=False, label="Replace selected rows?")


class TransacaoForm(forms.ModelForm):
    class Meta:
        model = Transacao
        fields = ['aluno_id', 'valor', 'descricao', 'tipo_transacao']
        widgets = {
            'tipo_transacao': forms.HiddenInput(),
        }
