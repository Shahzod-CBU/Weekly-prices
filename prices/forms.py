from django import forms

class Price_input(forms.Form):
    price = forms.IntegerField(label='', min_value=0)

class dataImportForm(forms.Form):
    xlsx_file = forms.FileField(
        label="Browse .xlsx file", 
    )

