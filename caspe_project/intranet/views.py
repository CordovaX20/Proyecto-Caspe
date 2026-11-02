import json
import math
import random
import urllib.request
import urllib.error
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import PlanComercial, Empresa, Interprete, SesionInterpretacion, CursoCapacitacion

def inicializar_datos_semilla():
    if Empresa.objects.count() == 0:
        plan_corp = PlanComercial.objects.create(nombre='Plan Corporativo 24/7', minutos_incluidos=2500, cobertura='24/7', precio_mensual=600)
        plan_basico = PlanComercial.objects.create(nombre='Plan Institucional', minutos_incluidos=500, cobertura='Horario Hábil', precio_mensual=150)

        h_reg = Empresa.objects.create(nombre='Hospital Regional', identificador_fiscal='61.101.000-K', pais='Chile', plan=plan_corp, minutos_contratados=2500, minutos_utilizados=340, token_qr='QR-HOSP-REG-01')
        aero = Empresa.objects.create(nombre='Aeropuerto Internacional', identificador_fiscal='76.890.123-4', pais='Chile', plan=plan_corp, minutos_contratados=2500, minutos_utilizados=1120, token_qr='QR-AERO-INT-02')
        Empresa.objects.create(nombre='Municipalidad Central', identificador_fiscal='69.070.100-1', pais='Colombia', plan=plan_basico, minutos_contratados=500, minutos_utilizados=125, token_qr='QR-MUNI-CEN-03')

        camila = Interprete.objects.create(nombre='Camila Rojas', email='crojas@caspe.com', lengua_senas='LSCh / SSI', estado='disponible')
        diego = Interprete.objects.create(nombre='Diego Muñoz', email='dmunoz@caspe.com', lengua_senas='LSCh', estado='ocupado')

        CursoCapacitacion.objects.create(titulo='Lengua de Señas Chilena (LSCh) - Nivel Inicial A1', nivel='Básico', modulos=12, idioma='LSCh', progreso_texto='Inscripción Abierta')
        CursoCapacitacion.objects.create(titulo='Atención Inclusiva en Salud y Urgencias Médicas', nivel='Intermedio', modulos=8, idioma='LSCh / Internacional', progreso_texto='En Curso (65%)')
        CursoCapacitacion.objects.create(titulo='Sistema de Señas Internacional (SSI) para Aeropuertos', nivel='Avanzado', modulos=10, idioma='Internacional', progreso_texto='Inscripción Abierta')
        CursoCapacitacion.objects.create(titulo='Cultura Sorda y Accesibilidad Comunicacional en Empresas', nivel='Básico', modulos=6, idioma='Multi-país', progreso_texto='Completado')

        SesionInterpretacion.objects.create(codigo_sala='CASPE-8821', empresa=h_reg, interprete=camila, solicitante='Urgencias', motivo='Atención médica', estado='finalizada', duracion_segundos=420, minutos_facturados=7)
        SesionInterpretacion.objects.create(codigo_sala='CASPE-8822', empresa=aero, interprete=diego, solicitante='Puerta 4', motivo='Asistencia embarque', estado='finalizada', duracion_segundos=185, minutos_facturados=4)

def index(request):
    inicializar_datos_semilla()
    return render(request, 'intranet/index.html')

def api_estado_sistema(request):
    cursos = list(CursoCapacitacion.objects.values('id', 'titulo', 'nivel', 'modulos', 'idioma', 'progreso_texto'))
    empresas = list(Empresa.objects.values('id', 'nombre', 'pais', 'token_qr', 'minutos_contratados', 'minutos_utilizados'))
    interpretes = list(Interprete.objects.values('id', 'nombre', 'lengua_senas', 'estado'))

    cola_qs = SesionInterpretacion.objects.filter(estado='en_espera').select_related('empresa').order_by('fecha_solicitud')
    cola = [{
        'id': s.id,
        'codigo_sala': s.codigo_sala,
        'empresa_id': s.empresa.id,
        'empresa_nombre': s.empresa.nombre,
        'solicitante': s.solicitante,
        'motivo': s.motivo,
        'estado': s.estado
    } for s in cola_qs]

    hist_qs = SesionInterpretacion.objects.filter(estado='finalizada').select_related('empresa', 'interprete').order_by('-id')[:20]
    historial = [{
        'sala': s.codigo_sala,
        'empresa': s.empresa.nombre,
        'interprete': s.interprete.nombre if s.interprete else 'Asignado',
        'fecha': s.fecha_solicitud.strftime('%d/%m %H:%M'),
        'duracionSeg': s.duracion_segundos,
        'minutos': s.minutos_facturados
    } for s in hist_qs]

    return JsonResponse({
        'cursos': cursos,
        'empresas': empresas,
        'interpretes': interpretes,
        'cola': cola,
        'historial': historial
    })

@csrf_exempt
def api_solicitar_reunion(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        empresa = Empresa.objects.get(id=data['empresa_id'])
        codigo = f"CASPE-{random.randint(1000, 9999)}"
        sesion = SesionInterpretacion.objects.create(
            codigo_sala=codigo,
            empresa=empresa,
            solicitante=data.get('solicitante', 'Usuario Cliente'),
            motivo=data.get('motivo', 'Atención General'),
            estado='en_espera'
        )
        return JsonResponse({'id': sesion.id, 'codigo_sala': sesion.codigo_sala})

@csrf_exempt
def api_toggle_interprete(request, interprete_id):
    if request.method == 'POST':
        inter = Interprete.objects.get(id=interprete_id)
        inter.estado = 'ocupado' if inter.estado == 'disponible' else 'disponible'
        inter.save()
        return JsonResponse({'estado': inter.estado})

@csrf_exempt
def api_atender_solicitud(request, sesion_id):
    if request.method == 'POST':
        sesion = SesionInterpretacion.objects.get(id=sesion_id)
        interprete = Interprete.objects.filter(estado='disponible').first() or Interprete.objects.first()
        interprete.estado = 'ocupado'
        interprete.save()

        sesion.interprete = interprete
        sesion.estado = 'en_curso'
        sesion.save()

        return JsonResponse({
            'id': sesion.id,
            'codigo_sala': sesion.codigo_sala,
            'empresa_id': sesion.empresa.id,
            'empresa_nombre': sesion.empresa.nombre,
            'solicitante': sesion.solicitante,
            'interprete': interprete.nombre
        })

@csrf_exempt
def api_finalizar_reunion(request, sesion_id):
    if request.method == 'POST':
        data = json.loads(request.body)
        segundos = int(data.get('duracion_segundos', 0))
        minutos_facturados = max(1, math.ceil(segundos / 60))

        sesion = SesionInterpretacion.objects.get(id=sesion_id)
        sesion.estado = 'finalizada'
        sesion.duracion_segundos = segundos
        sesion.minutos_facturados = minutos_facturados
        sesion.save()

        empresa = sesion.empresa
        empresa.minutos_utilizados += minutos_facturados
        empresa.save()

        if sesion.interprete:
            sesion.interprete.estado = 'disponible'
            sesion.interprete.save()

        return JsonResponse({'minutos_facturados': minutos_facturados})

@csrf_exempt
def api_crear_curso(request):
    """Permite al Admin crear un nuevo curso en SQLite desde el Frontend."""
    if request.method == 'POST':
        data = json.loads(request.body)
        curso = CursoCapacitacion.objects.create(
            titulo=data['titulo'],
            nivel=data.get('nivel', 'Básico'),
            modulos=int(data.get('modulos', 8)),
            idioma=data.get('idioma', 'LSCh'),
            progreso_texto='Inscripción Abierta'
        )
        return JsonResponse({'id': curso.id, 'titulo': curso.titulo})

@csrf_exempt
def api_crear_empresa(request):
    """Permite al Admin registrar una nueva empresa con Token QR único en SQLite."""
    if request.method == 'POST':
        data = json.loads(request.body)
        prefijo = data['nombre'][:4].upper().replace(' ', '')
        token_qr = f"QR-{prefijo}-{random.randint(100, 999)}"
        plan = PlanComercial.objects.first()

        empresa = Empresa.objects.create(
            nombre=data['nombre'],
            pais=data.get('pais', 'Chile'),
            plan=plan,
            minutos_contratados=int(data.get('minutos_contratados', 1000)),
            minutos_utilizados=0,
            token_qr=token_qr
        )
        return JsonResponse({'id': empresa.id, 'token_qr': empresa.token_qr})



    # ==========================================================
# CHATBOT IA - ASISTENTE VIRTUAL CASPE
# ==========================================================
# Opcional: Si quieres conectar Gemini AI en vivo, pega tu API Key aquí.
# Si lo dejas vacío (""), usará el motor inteligente local de respaldo sin fallar.
GEMINI_API_KEY = "" 

CONTEXTO_CASPE = """
Eres el Asistente Virtual Oficial con IA de CASPE Iberoamérica.
CASPE presta servicios de interpretación, capacitación (e-learning) y accesibilidad comunicacional en lengua de señas (LSCh en Chile, LSE, ASL y Sistema de Señas Internacional) con presencia en caspe.com y caspe.cl.
Reglas del sistema que debes explicar de forma breve, amable y clara:
1. Solicitud de Intérprete / QR: Las empresas clientes (hospitales, aeropuertos, municipalidades) acceden mediante un código QR o desde la pestaña 'Solicitar Reunión'. Si hay un intérprete disponible, se abre una videollamada inmediata en Jitsi Meet. Si todos están ocupados, el usuario entra en una Cola de Espera prioritaria hasta que uno se libere.
2. Cobro y Planes de Minutos: Al finalizar la videollamada, el sistema registra automáticamente los segundos y descuenta los minutos del plan contratado por la empresa (ej. Plan Institucional en horario hábil o Plan Corporativo 24/7).
3. Cursos de Capacitación: En la página de inicio (E-Learning) están disponibles los cursos de Lengua de Señas certificados por CASPE.
"""

def respuesta_inteligente_local(mensaje):
    """Motor de IA local para responder preguntas frecuentes sin requerir API externa."""
    msg = mensaje.lower()
    
    if any(k in msg for k in ['qr', 'escanear', 'enlace', 'tótem', 'totem', 'codigo']):
        return "📱 **Acceso por Código QR:** Cada empresa registrada cuenta con un Token QR único. Al escanearlo en un hospital, aeropuerto o municipalidad, el usuario entra directo a solicitar un intérprete. Puedes ver e imprimir tu QR en la pestaña **'Mi Plan y Minutos'** o en el **'Panel Administrador'**."
    
    if any(k in msg for k in ['espera', 'ocupado', 'cola', 'demora', 'disponible']):
        return "⏳ **Cola de Espera Inteligente:** Si al solicitar una atención todos los intérpretes de turno están ocupados en otra llamada, el sistema te mantendrá automáticamente en una **Cola de Espera Prioritaria** y te conectará apenas se libere el primer intérprete."
    
    if any(k in msg for k in ['minuto', 'plan', 'cobro', 'factura', 'precio', '24/7', 'horario']):
        return "📊 **Control de Planes y Minutos:** CASPE ofrece planes por franja horaria, horario hábil o cobertura **24/7**. Cuando finaliza una videollamada, el cronómetro calcula la duración exacta y descuenta los minutos automáticamente de la bolsa contratada por tu institución."
    
    if any(k in msg for k in ['curso', 'capacitacion', 'capacitación', 'aprender', 'certificado', 'e-learning', 'lsch']):
        return "🎓 **Academia E-Learning CASPE:** En la pestaña principal **'Cursos de Capacitación'** encontrarás programas certificados de Lengua de Señas Chilena (LSCh), Sistema de Señas Internacional (SSI) y atención inclusiva en salud y urgencias."
    
    if any(k in msg for k in ['videollamada', 'camara', 'cámara', 'jitsi', 'reunion', 'reunión', 'intérprete', 'interprete']):
        return "🎥 **Servicio de Videointerpretación:** Para conectarte, ve a **'Solicitar Reunión / Intérprete'**, ingresa el motivo de atención y presiona iniciar. La llamada se realiza por videollamada WebRTC en tiempo real."

    return "🤟 ¡Hola! Soy el **Asistente IA de CASPE Iberoamérica**. Puedo ayudarte con dudas sobre:\n• Cómo solicitar un **intérprete por videollamada**\n• Funcionamiento del **Código QR** y la **Cola de Espera**\n• Descuento de **minutos y planes 24/7**\n• **Cursos de capacitación** en Lengua de Señas.\n\n¿Sobre qué tema necesitas ayuda?"

@csrf_exempt
def api_chatbot_ia(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        mensaje_usuario = data.get('mensaje', '').strip()

        if not mensaje_usuario:
            return JsonResponse({'respuesta': 'Por favor escribe una consulta.'})

        # Si hay API Key configurada, consulta a Gemini 2.5 Flash
        if GEMINI_API_KEY:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
                payload = {
                    "contents": [{
                        "parts": [{"text": f"{CONTEXTO_CASPE}\n\nPregunta del usuario: {mensaje_usuario}"}]
                    }]
                }
                req = urllib.request.Request(
                    url, 
                    data=json.dumps(payload).encode('utf-8'),
                    headers={'Content-Type': 'application/json'}
                )
                with urllib.request.urlopen(req, timeout=8) as response:
                    res_data = json.loads(response.read().decode('utf-8'))
                    texto_ia = res_data['candidates'][0]['content']['parts'][0]['text']
                    return JsonResponse({'respuesta': texto_ia})
            except Exception:
                pass # Si falla la red, usa automáticamente el motor local

        # Respuesta inmediata con el motor entrenado local
        respuesta = respuesta_inteligente_local(mensaje_usuario)
        return JsonResponse({'respuesta': respuesta})
