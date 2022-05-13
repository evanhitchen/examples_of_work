import os
from django.core.exceptions import ValidationError


def docxvalidate_file_extension(value):

    ext = os.path.splitext(value.name)[1]  # [0] returns path+filename
    valid_extensions = ['.docx']
    if not ext.lower() in valid_extensions:
        raise ValidationError('Unsupported file extension. Must be .docx')


def excel_validate_file_extension(value):

    ext = os.path.splitext(value.name)[1]  # [0] returns path+filename
    valid_extensions = ['.xlsx']
    if not ext.lower() in valid_extensions:
        raise ValidationError('Unsupported file extension. Must be .xlsx')


def image_validate_file_extension(value):

    ext = os.path.splitext(value.name)[1]  # [0] returns path+filename
    valid_extensions = ['.jpg', 'png']
    if not ext.lower() in valid_extensions:
        raise ValidationError('Unsupported file extension. Must be .jpg or .png')