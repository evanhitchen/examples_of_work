import django_filters
from django_filters import CharFilter

from .models import *


class dashboard_filter(django_filters.FilterSet):
    client_name = CharFilter(field_name='name', lookup_expr='icontains', label='Client Name')

    class Meta:
        model = Client
        fields = ['client_name']
        exclude = ['name']


class structure_filter(django_filters.FilterSet):

    structure_id = CharFilter(field_name='id_code', lookup_expr='icontains', label='Asset Reference')
    Asset_name = CharFilter(field_name='name', lookup_expr='icontains', label='Asset Name')

    class Meta:
        model = Structure
        fields = ['site', 'structure_id', 'Asset_name']
