from django.contrib import admin
from .models import *

class SaldoListFilter(admin.SimpleListFilter):
    title = 'Saldo'
    parameter_name = 'saldo'
    
    def lookups(self, request, model_admin):
        return (
            ('negativo', 'Em divida'),
        )

    def queryset(self, _request, queryset):
        if self.value() == 'negativo':
            return queryset.filter(saldo__lt=-1)
        return queryset
