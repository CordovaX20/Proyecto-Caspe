from django.contrib import admin
from .models import PlanComercial, Empresa, Interprete, SesionInterpretacion, CursoCapacitacion

admin.site.register(PlanComercial)
admin.site.register(Empresa)
admin.site.register(Interprete)
admin.site.register(SesionInterpretacion)
admin.site.register(CursoCapacitacion)