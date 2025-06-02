from django import forms

class ImportFileForm(forms.Form):
    file = forms.FileField(label="Choose a CSV or JSON file")
    replace = forms.BooleanField(required=False, label="Replace selected rows?")