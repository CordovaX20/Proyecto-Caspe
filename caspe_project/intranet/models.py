from django.db import models

class PlanComercial(models.Model):
    nombre = models.CharField(max_length=100)
    minutos_incluidos = models.IntegerField(default=500)
    cobertura = models.CharField(max_length=50, default='Horario Hábil')
    precio_mensual = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.nombre} ({self.cobertura})"

class Empresa(models.Model):
    nombre = models.CharField(max_length=150)
    identificador_fiscal = models.CharField(max_length=50, blank=True)
    pais = models.CharField(max_length=80, default='Chile')
    plan = models.ForeignKey(PlanComercial, on_delete=models.SET_NULL, null=True)
    minutos_contratados = models.IntegerField(default=2500)
    minutos_utilizados = models.IntegerField(default=0)
    token_qr = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return f"{self.nombre} ({self.token_qr})"

class Interprete(models.Model):
    ESTADOS = [
        ('disponible', 'Disponible'),
        ('ocupado', 'Ocupado'),
        ('desconectado', 'Fuera de Turno'),
    ]
    nombre = models.CharField(max_length=120)
    email = models.EmailField(unique=True)
    lengua_senas = models.CharField(max_length=60, default='LSCh / Internacional')
    estado = models.CharField(max_length=20, choices=ESTADOS, default='disponible')

    def __str__(self):
        return f"{self.nombre} - {self.estado}"

class SesionInterpretacion(models.Model):
    ESTADOS_SESION = [
        ('en_espera', 'En Cola de Espera'),
        ('en_curso', 'En Videollamada'),
        ('finalizada', 'Finalizada'),
    ]
    codigo_sala = models.CharField(max_length=60, unique=True)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    interprete = models.ForeignKey(Interprete, on_delete=models.SET_NULL, null=True, blank=True)
    solicitante = models.CharField(max_length=150, default='Usuario QR')
    motivo = models.CharField(max_length=250, default='Atención General')
    estado = models.CharField(max_length=20, choices=ESTADOS_SESION, default='en_espera')
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    duracion_segundos = models.IntegerField(default=0)
    minutos_facturados = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.codigo_sala} - {self.empresa.nombre} ({self.estado})"

class CursoCapacitacion(models.Model):
    titulo = models.CharField(max_length=180)
    nivel = models.CharField(max_length=50, default='Básico')
    modulos = models.IntegerField(default=8)
    idioma = models.CharField(max_length=60, default='LSCh')
    progreso_texto = models.CharField(max_length=60, default='Inscripción Abierta')

    def __str__(self):
        return self.titulo