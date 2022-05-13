from django.forms import ModelForm
from .models import *
from django import forms


# Client Forms
class ClientForm(ModelForm):

    class Meta:
        model = Client
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'})
        }


class CustomSelect(forms.Select):
    option_inherits_attrs = True


class SiteForm(ModelForm):

    class Meta:
        model = Site
        fields = ['client', 'name', 'location']
        widgets = {'client': CustomSelect(attrs={'class': 'form-control'}),
                    'name': forms.TextInput(attrs={'class': 'form-control'}),
                    'location': forms.TextInput(attrs={'class': 'form-control'})}


class StructureForm(ModelForm):

    class Meta:
        model = Structure
        fields = ['name', 'id_code', 'site', 'date_of_inspection']
        widgets = {'site': CustomSelect(attrs={'class': 'form-control'}),
                   'name': forms.TextInput(attrs={'class': 'form-control'}),
                   'id_code': forms.TextInput(attrs={'class': 'form-control'}),
                   'date_of_inspection': forms.DateInput(attrs={'class': 'form-control'}),
                   }


class Client_select_Form(forms.Form):
    client_name = forms.ModelChoiceField(queryset=Client.objects.all().order_by('name'),
                                         widget=CustomSelect(attrs={'class': 'form-control'}))


class Structure_select_Form(forms.Form):
    id_code = forms.ModelChoiceField(queryset=Structure.objects.all().order_by('id_code'),
                                         widget=CustomSelect(attrs={'class': 'form-control'}))


class StructureR8R9Form(ModelForm):

    class Meta:
        model = Structure
        fields = ['name', 'id_code', 'date_of_inspection']
        widgets = {'name': forms.TextInput(attrs={'class': 'form-control'}),
                   'id_code': forms.TextInput(attrs={'class': 'form-control'}),
                   'date_of_inspection': forms.DateInput(attrs={'class': 'form-control'}),
                   }


class ElementR8R9Form(ModelForm):

    class Meta:
        model = Element
        fields = ['element', 'discipline']
        widgets = {'element': forms.TextInput(attrs={'class': 'form-control'}),
                   'discipline': CustomSelect(attrs={'class': 'form-control'})
                   }


class DefectR8R9Form(ModelForm):

    class Meta:
        model = Defect
        fields = ['defect_description', 'remedial', 'safe']
        widgets = {'defect_description': forms.TextInput(attrs={'class': 'form-control'}),
                   'safe': forms.TextInput(attrs={'class': 'form-control'}),
                   'remedial': forms.TextInput(attrs={'class': 'form-control'})
                   }


# Form to capture docx file
class DocxForm(ModelForm):
    class Meta:
        model = Docxfile
        fields = ['file_name',]


# Form to capture Excel file
class ExcelForm(ModelForm):
    class Meta:
        model = ExcelFile
        fields = ['file_name',]


# Form to capture Excel file
class ImageForm(ModelForm):
    class Meta:
        model = ImageFile
        fields = ['file_name',]