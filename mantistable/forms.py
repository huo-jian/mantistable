from django import forms
from .models import GoldStandardsEnum

#Formulaire d'insertion de fichier JSON

class TableFromJSONForm(forms.Form):
    table_name = forms.CharField(
        widget=forms.TextInput(),
        label="Table name",
        max_length=200,
        required=True,
        label_suffix=""
    )
    json_file = forms.FileField(
        widget=forms.FileInput(attrs={'accept': '.json'}),
        label="Insert a JSON file",
        required=True,
        label_suffix=""
    )
    gs_type = forms.ChoiceField(
        widget=forms.Select(attrs={'class': 'form-control selectpicker'}),
        label="Gold Standard",
        initial=GoldStandardsEnum.NONE.value,
        choices=[(tag.name, tag.value)for tag in GoldStandardsEnum],
        required=True,
        label_suffix=""
    )
