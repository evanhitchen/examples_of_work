from django.contrib import admin
from django.contrib import admin
from .models import Client, Site, Structure, Element, Defect, Docxfile, ExcelFile, ImageFile

# Register your models here.
admin.site.register(Client)
admin.site.register(Site)
admin.site.register(Structure)
admin.site.register(Element)
admin.site.register(Defect)
admin.site.register(Docxfile)
admin.site.register(ExcelFile)
admin.site.register(ImageFile)