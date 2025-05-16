from django.contrib import admin
from django.apps import apps
from .models import *

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



admin.site.register(Aluno, AlunoAdmin)
admin.site.register(ResponsavelEducativo, ResponsavelEducativoAdmin)
admin.site.register(TipoProblema, TipoProblemaAdmin)
admin.site.register(TipoImagem, TipoImagemAdmin)

# Dynamically register all models with DefaultAdmin
models = apps.get_models()

for model in models:
    try:
        admin.site.register(model, type(f"{model.__name__}Admin", (DefaultAdmin,), {
            
        }))
    except admin.sites.AlreadyRegistered:
        # If the model is already registered, skip it
        pass

