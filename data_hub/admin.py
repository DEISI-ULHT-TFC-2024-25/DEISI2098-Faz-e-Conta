from django.contrib import admin
from django.apps import apps
from .models import *
from django.db.models import Sum

class DefaultAdmin(admin.ModelAdmin):
    def __init__(self, model, admin_site):
        self.list_display = [field.name for field in model._meta.fields if not field.primary_key]
        self.ordering = [field.name for field in model._meta.fields if field.name == 'id' and not field.primary_key]
        super().__init__(model, admin_site)

class AlunoAdmin(admin.ModelAdmin):
    list_display = ('nome_completo', 'numero_documento', 'processo')
    search_fields = ('nome_proprio', 'apelido', 'numero_documento', 'processo')
    list_filter = ('sala_id', 'cuidados_especias')
    ordering = [field.name for field in Aluno._meta.fields]
    
    def nome_completo(self, obj):
        return f"{obj.nome_proprio} {obj.apelido}"
    
    nome_completo.short_description = 'Nome Completo'
    
class ResponsavelEducativoAdmin(admin.ModelAdmin):
    list_display = ('nome_completo', 'numero_documento', 'telefone', 'email')
    search_fields = ('nome_proprio', 'apelido', 'numero_documento')
    list_filter = ('concelho',)
    
    def nome_completo(self, obj):
        return f"{obj.nome_proprio} {obj.apelido}"
    nome_completo.short_description = 'Nome Completo'

class TipoProblemaAdmin(admin.ModelAdmin):
    list_display = ('tipo_problema',)
    search_fields = ('tipo_problema',)
    ordering = ('tipo_problema',)

class TipoImagemAdmin(admin.ModelAdmin):
    list_display = ('tipo_imagem',)
    search_fields = ('tipo_imagem',)
    ordering = ('tipo_imagem',)

class DividaAdmin(admin.ModelAdmin):
    list_display = ('nome_completo', 'aluno_id__processo', 'total_valor')
    search_fields = ('aluno_id__processo', 'aluno_id__nome_proprio', 'aluno_id__apelido')

    from django.db.models import F, ExpressionWrapper, DecimalField

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Annotate each Divida with the total per row
        qs = qs.annotate(
            total=Sum('valor_pagar') - Sum('valor_pago')
        )
        # Only include rows where total > 0
        return qs.filter(total__gt=0)

    def aluno_id__processo(self, obj):
        return obj.aluno_id.processo

    def nome_completo(self, obj):
        return f"{obj.aluno_id.nome_proprio} {obj.aluno_id.apelido}"

    def total_valor(self, obj):
        # Use the annotated value if available, otherwise calculate
        total = getattr(obj, 'total', None)
        if total is None:
            total = type(obj).objects.filter(aluno_id=obj.aluno_id).aggregate(
                total=Sum('valor_pagar') - Sum('valor_pago')
            )['total']

        return total


    nome_completo.short_description = 'Aluno'
    total_valor.short_description = 'Divida Total'
    aluno_id__processo.short_description = 'Processo'

admin.site.register(Aluno, AlunoAdmin)
admin.site.register(ResponsavelEducativo, ResponsavelEducativoAdmin)
admin.site.register(TipoProblema, TipoProblemaAdmin)
admin.site.register(TipoImagem, TipoImagemAdmin)
admin.site.register(Divida, DividaAdmin)


# Dynamically register all models with DefaultAdmin
models = apps.get_models()
for model in models:
    try:
        admin.site.register(model, type(f"{model.__name__}Admin", (DefaultAdmin,), {
            
        }))
    except admin.sites.AlreadyRegistered:
        # If the model is already registered, skip it
        pass

