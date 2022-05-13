from django.db import models
from django.urls import reverse
from .validators import *
from django.utils import timezone


# Create your models here.
class Client(models.Model):
    name = models.CharField(max_length=30)

    # display question text instead of <Question: Question object (1)>
    def __str__(self):
        return self.name

    def get_absolute_url(self):
        """Returns the url to access a particular instance of MyModelName."""
        return reverse('client-detail-view', args=[str(self.id)])


class Site(models.Model):
    name = models.CharField(max_length=30)
    location = models.CharField(max_length=100)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)

    # display question text instead of <Question: Question object (1)>
    def __str__(self):
        return self.name

    def get_absolute_url(self):
        """Returns the url to access a particular instance of MyModelName."""
        return reverse('site-detail-view', args=[str(self.id)])


class Structure(models.Model):
    id_code = models.CharField(max_length=30)
    name = models.CharField(max_length=30)
    site = models.ForeignKey(Site, on_delete=models.CASCADE)
    date_of_inspection = models.DateField(auto_now=False, default=timezone.now)

    # display question text instead of <Question: Question object (1)>
    def __str__(self):
        return self.id_code

    def get_absolute_url(self):
        """Returns the url to access a particular instance of MyModelName."""
        return reverse('structure-detail-view', args=[str(self.id)])

    class Meta:
        ordering = ['-date_of_inspection']


class Element(models.Model):
    element = models.CharField(max_length=150)
    element_description = models.CharField(max_length=500)
    structure = models.ForeignKey(Structure, on_delete=models.CASCADE)

    # civil, mechanical, electrical or access
    CIVIL = 'CIVIL'
    MECH = 'MECHANICAL'
    ELEC = 'ELECTRICAL'
    ACCESS = 'ACCESS'
    ENGINEERING_FIELD_CHOICES = [
        (CIVIL, 'Civil'),
        (MECH, 'Mechanical'),
        (ELEC, 'Electricity'),
        (ACCESS, 'Access'),
    ]

    discipline = models.CharField(
        max_length=10,
        choices=ENGINEERING_FIELD_CHOICES,
        default=CIVIL,
    )

    # display question text instead of <Question: Question object (1)>
    def __str__(self):
        return self.element

    def get_absolute_url(self):
        """Returns the url to access a particular instance of MyModelName."""
        return reverse('element-detail-view', args=[str(self.id)])


class Defect(models.Model):
    defect_description = models.CharField(max_length=500)
    remedial = models.CharField(max_length=500)
    safe = models.CharField(max_length=1)
    element = models.ForeignKey(Element, on_delete=models.CASCADE)

    def get_absolute_url(self):
        """Returns the url to access a particular instance of MyModelName."""
        return reverse('defect-detail-view', args=[str(self.id)])


class ImageFile(models.Model):
    file_name = models.ImageField(upload_to='dashboard', validators=[image_validate_file_extension])
    defect = models.ForeignKey(Defect, on_delete=models.CASCADE, null=True)
    uploaded = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image id:{self.file_name}"


class Docxfile(models.Model):
    file_name = models.FileField(upload_to='dashboard', validators=[docxvalidate_file_extension])
    uploaded = models.DateTimeField(auto_now_add=True)
    activated = models.BooleanField(default=False)

    def __str__(self):
        return f"File id:{self.file_name}"


class ExcelFile(models.Model):
    file_name = models.FileField(upload_to='dashboard', validators=[excel_validate_file_extension])
    uploaded = models.DateTimeField(auto_now_add=True)
    activated = models.BooleanField(default=False)

    def __str__(self):
        return f"File id:{self.file_name}"


