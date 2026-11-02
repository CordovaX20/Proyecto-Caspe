let state = {
    usuarioActual: null,
    cursos: [],
    empresas: [],
    interpretes: [],
    cola: [],
    llamadaActiva: null,
    historial: []
};

let timerInterval = null;
let segundosLlamada = 0;
let jitsiApi = null; // Instancia de videollamada real Jitsi Meet

async function cargarDatosDesdeDjango() {
    const res = await fetch('/api/estado/');
    const data = await res.json();
    state.cursos = data.cursos;
    state.empresas = data.empresas;
    state.interpretes = data.interpretes;
    state.cola = data.cola;
    state.historial = data.historial;
    renderAll();
}

function autofillDemoCredentials() {
    const rol = document.getElementById('login-role').value;
    document.getElementById('login-email').value = rol === 'admin' ? 'jherrera@caspe.com' : 'cliente@hospital.cl';
}

async function handleLogin(event) {
    event.preventDefault();
    const email = document.getElementById('login-email').value;
    const rol = document.getElementById('login-role').value;

    state.usuarioActual = {
        email: email,
        rol: rol,
        nombre: rol === 'admin' ? 'José Herrera (Admin CASPE)' : 'Coordinación Hospital Regional'
    };

    document.getElementById('login-screen').classList.add('hidden');
    document.getElementById('app-wrapper').classList.remove('hidden');

    document.getElementById('user-display-name').innerText = state.usuarioActual.nombre;
    document.getElementById('user-display-role').innerText = rol === 'admin' ? 'ADMINISTRADOR' : 'CLIENTE EMPRESA';

    document.querySelectorAll('.role-cliente').forEach(el => el.classList.toggle('hidden', rol !== 'cliente'));
    document.querySelectorAll('.role-admin').forEach(el => el.classList.toggle('hidden', rol !== 'admin'));

    navigateTo('cursos');
    await cargarDatosDesdeDjango();
}

function handleLogout() {
    state.usuarioActual = null;
    document.getElementById('app-wrapper').classList.add('hidden');
    document.getElementById('login-screen').classList.remove('hidden');
}

function navigateTo(viewName) {
    document.querySelectorAll('.view-section').forEach(sec => sec.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));

    const targetSection = document.getElementById('view-' + viewName);
    if (targetSection) targetSection.classList.add('active');

    const btnMap = {
        'cursos': 'nav-cursos',
        'solicitar': 'nav-solicitar',
        'mi-cuenta': 'nav-mi-cuenta',
        'admin-panel': 'nav-admin-panel',
        'admin-consola': 'nav-admin-consola'
    };
    const activeBtn = document.getElementById(btnMap[viewName]);
    if (activeBtn) activeBtn.classList.add('active');
}

// =======================================================
// CREACIÓN DE CURSOS Y EMPRESAS EN SQLITE (ADMIN)
// =======================================================
async function crearCurso(event) {
    event.preventDefault();
    const titulo = document.getElementById('nuevo-curso-titulo').value;
    const nivel = document.getElementById('nuevo-curso-nivel').value;
    const modulos = document.getElementById('nuevo-curso-modulos').value;
    const idioma = document.getElementById('nuevo-curso-idioma').value;

    await fetch('/api/cursos/crear/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ titulo, nivel, modulos, idioma })
    });

    document.getElementById('nuevo-curso-titulo').value = '';
    await cargarDatosDesdeDjango();
}

async function crearEmpresa(event) {
    event.preventDefault();
    const nombre = document.getElementById('nueva-emp-nombre').value;
    const pais = document.getElementById('nueva-emp-pais').value;
    const minutos_contratados = document.getElementById('nueva-emp-minutos').value;

    const res = await fetch('/api/empresas/crear/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nombre, pais, minutos_contratados })
    });
    const data = await res.json();

    document.getElementById('nueva-emp-nombre').value = '';
    await cargarDatosDesdeDjango();
    mostrarModalQR(nombre, data.token_qr);
}

// =======================================================
// GENERADOR DE CÓDIGOS QR PARA EMPRESAS
// =======================================================
function mostrarModalQR(nombreEmpresa, tokenQr) {
    document.getElementById('qr-modal-title').innerText = nombreEmpresa;
    document.getElementById('qr-modal-token').innerText = tokenQr;
    
    // URL institucional que codifica el QR
    const urlAcceso = `${window.location.origin}/?qr=${encodeURIComponent(tokenQr)}`;
    const qrApiUrl = `https://api.qrserver.com/v1/create-qr-code/?size=220x220&data=${encodeURIComponent(urlAcceso)}`;
    
    document.getElementById('qr-modal-img').src = qrApiUrl;
    document.getElementById('qr-modal').classList.remove('hidden');
}

function cerrarModalQR() {
    document.getElementById('qr-modal').classList.add('hidden');
}

// =======================================================
// SOLICITUD Y VIDEOLLAMADA REAL CON JITSI MEET
// =======================================================
async function solicitarInterprete() {
    const empresaId = parseInt(document.getElementById('qr-empresa').value);
    const modalidad = document.getElementById('qr-modalidad').value;
    const solicitante = document.getElementById('qr-usuario').value || 'Usuario Cliente';
    const motivo = document.getElementById('qr-motivo').value || 'Atención General';

    const res = await fetch('/api/solicitar/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            empresa_id: empresaId,
            solicitante: `${solicitante} (${modalidad})`,
            motivo: motivo
        })
    });
    const nuevaSolicitud = await res.json();
    await cargarDatosDesdeDjango();

    const disponibles = state.interpretes.filter(i => i.estado === 'disponible').length;
    const qrBox = document.getElementById('qr-status-box');

    if (disponibles > 0) {
        qrBox.innerHTML = `
            <div class="text-center" style="padding: 1.5rem;">
                <h3 class="text-success mb-medium">✅ Solicitud Creada • Sala ${nuevaSolicitud.codigo_sala}</h3>
                <p class="section-desc mb-medium">
                    Un intérprete está disponible. Puedes unirte directamente a la videollamada o contestarla desde la vista Administrador:
                </p>
                <a href="https://meet.jit.si/CASPE_Iberoamerica_${nuevaSolicitud.codigo_sala}" target="_blank" class="btn-primary btn-small" style="text-decoration:none; display:inline-block;">
                    🎥 Abrir Cámara del Cliente en Pestaña Nueva
                </a>
            </div>
        `;
    } else {
        qrBox.innerHTML = `
            <div class="text-center" style="padding: 1.5rem;">
                <h3 class="text-warning mb-medium">⏳ Todos los intérpretes están ocupados</h3>
                <p>Has ingresado a la <strong>Cola de Espera en SQLite</strong> (Posición #${state.cola.length}).</p>
                <p class="section-desc mt-small">Código de reserva: <strong>${nuevaSolicitud.codigo_sala}</strong></p>
            </div>
        `;
    }
}

async function toggleInterprete(id) {
    await fetch(`/api/interprete/${id}/toggle/`, { method: 'POST' });
    await cargarDatosDesdeDjango();
}

async function atenderSolicitud(solicitudId) {
    if (state.llamadaActiva) {
        alert('Ya hay una reunión en curso. Finalízala antes de contestar otra.');
        return;
    }

    const res = await fetch(`/api/atender/${solicitudId}/`, { method: 'POST' });
    state.llamadaActiva = await res.json();
    segundosLlamada = 0;

    iniciarVideollamadaJitsi();
    await cargarDatosDesdeDjango();
}

function iniciarVideollamadaJitsi() {
    clearInterval(timerInterval);
    const cabinBox = document.getElementById('cabin-box');
    const controls = document.getElementById('cabin-controls');
    const timerBadge = document.getElementById('live-timer-badge');

    cabinBox.innerHTML = ''; // Limpiar contenedor para montar Jitsi
    cabinBox.classList.add('active-call');
    controls.style.display = 'flex';
    timerBadge.classList.remove('hidden');

    document.getElementById('call-client-name').innerText = `${state.llamadaActiva.empresa_nombre} — ${state.llamadaActiva.solicitante}`;
    document.getElementById('call-interpreter-name').innerText = `Intérprete: ${state.llamadaActiva.interprete} | Sala: ${state.llamadaActiva.codigo_sala}`;

    // Montar Videollamada Real con Jitsi Meet API
    if (typeof JitsiMeetExternalAPI !== 'undefined') {
        const domain = 'meet.jit.si';
        const options = {
            roomName: `CASPE_Iberoamerica_${state.llamadaActiva.codigo_sala}`,
            width: '100%',
            height: '100%',
            parentNode: cabinBox,
            userInfo: {
                displayName: `Intérprete CASPE (${state.llamadaActiva.interprete})`
            },
            configOverwrite: {
                startWithAudioMuted: false,
                startWithVideoMuted: false,
                prejoinPageEnabled: false
            }
        };
        jitsiApi = new JitsiMeetExternalAPI(domain, options);
    } else {
        cabinBox.innerHTML = `<p class="text-warning">Cargando cámara WebRTC (${state.llamadaActiva.codigo_sala})...</p>`;
    }

    // Iniciar cronómetro de facturación de minutos
    timerInterval = setInterval(() => {
        segundosLlamada++;
        const mins = String(Math.floor(segundosLlamada / 60)).padStart(2, '0');
        const secs = String(segundosLlamada % 60).padStart(2, '0');
        timerBadge.innerText = `🔴 EN VIVO ${mins}:${secs}`;
    }, 1000);
}

async function finalizarLlamada() {
    if (!state.llamadaActiva) return;
    clearInterval(timerInterval);

    // Cerrar cámara de Jitsi si está activa
    if (jitsiApi) {
        jitsiApi.dispose();
        jitsiApi = null;
    }

    const res = await fetch(`/api/finalizar/${state.llamadaActiva.id}/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ duracion_segundos: segundosLlamada })
    });
    const data = await res.json();

    state.llamadaActiva = null;
    const cabinBox = document.getElementById('cabin-box');
    cabinBox.classList.remove('active-call');
    cabinBox.innerHTML = `<p class="text-success">✅ Videollamada finalizada y guardada en SQLite. Se facturaron ${data.minutos_facturados} min.</p>`;
    document.getElementById('cabin-controls').style.display = 'none';
    document.getElementById('live-timer-badge').classList.add('hidden');

    await cargarDatosDesdeDjango();
}

function renderAll() {
    document.getElementById('courses-container').innerHTML = state.cursos.map(c => `
        <div class="course-card">
            <div>
                <div class="course-meta">
                    <span class="badge">${c.idioma}</span>
                    <span>Nivel: <strong>${c.nivel}</strong></span>
                </div>
                <h4 style="font-size: 1.05rem; margin-bottom: 0.5rem;">${c.titulo}</h4>
                <p class="section-desc mb-medium">${c.modulos} módulos en video • Certificación Oficial CASPE</p>
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center; padding-top: 1rem; border-top: 1px solid var(--border);">
                <span class="text-small-muted">${c.progreso_texto}</span>
                <button class="btn-primary btn-small" onclick="alert('Abriendo aula virtual: ${c.titulo}')">Ingresar al Curso</button>
            </div>
        </div>
    `).join('');

    const dispCount = state.interpretes.filter(i => i.estado === 'disponible').length;
    document.getElementById('kpi-disponibles').innerText = `${dispCount} / ${state.interpretes.length}`;
    document.getElementById('kpi-cola').innerText = state.cola.length;
    document.getElementById('nav-queue-badge').innerText = state.cola.length;

    const totalMinutos = state.empresas.reduce((acc, e) => acc + e.minutos_utilizados, 0);
    document.getElementById('kpi-minutos').innerText = totalMinutos.toLocaleString();
    document.getElementById('kpi-atenciones').innerText = state.historial.length;

    if (state.empresas.length > 0) {
        const miEmpresa = state.empresas[0];
        document.getElementById('cliente-minutos-usados').innerText = miEmpresa.minutos_utilizados;
        document.getElementById('cliente-minutos-restantes').innerText = `Restan ${miEmpresa.minutos_contratados - miEmpresa.minutos_utilizados} minutos`;

        document.getElementById('tabla-historial-cliente').innerHTML = state.historial
            .filter(h => h.empresa === miEmpresa.nombre)
            .map(h => `
                <tr>
                    <td><code>${h.sala}</code></td>
                    <td>${h.interprete}</td>
                    <td>${h.fecha}</td>
                    <td>${h.duracionSeg} seg</td>
                    <td><span class="badge">${h.minutos} min</span></td>
                </tr>
            `).join('');
    }

    document.getElementById('tabla-interpretes').innerHTML = state.interpretes.map(i => `
        <tr>
            <td><strong>${i.nombre}</strong></td>
            <td>${i.lengua_senas}</td>
            <td><span class="status-dot ${i.estado === 'disponible' ? 'dot-disponible' : 'dot-ocupado'}"></span>${i.estado.toUpperCase()}</td>
            <td><button class="btn-outline btn-small" onclick="toggleInterprete(${i.id})">Cambiar Estado</button></td>
        </tr>
    `).join('');

    document.getElementById('tabla-empresas').innerHTML = state.empresas.map(e => {
        const pct = Math.min(100, Math.round((e.minutos_utilizados / e.minutos_contratados) * 100));
        return `
            <tr>
                <td><strong>${e.nombre}</strong><br><span class="text-small-muted">${e.pais}</span></td>
                <td>
                    <button class="btn-outline btn-small" onclick="mostrarModalQR('${e.nombre}', '${e.token_qr}')">
                        📱 Ver QR (${e.token_qr})
                    </button>
                </td>
                <td><strong>${e.minutos_utilizados}</strong> / ${e.minutos_contratados} min</td>
                <td style="width: 120px;"><div class="progress-bar"><div class="progress-fill" style="width: ${pct}%;"></div></div></td>
            </tr>
        `;
    }).join('');

    const tbodyConsola = document.getElementById('tabla-consola-interprete');
    if (state.cola.length === 0) {
        tbodyConsola.innerHTML = `<tr><td colspan="4" class="text-muted text-center">No hay solicitudes pendientes.</td></tr>`;
    } else {
        tbodyConsola.innerHTML = state.cola.map(c => `
            <tr>
                <td><strong>${c.empresa_nombre}</strong><br><span class="text-small-muted">${c.codigo_sala}</span></td>
                <td>${c.solicitante}<br><span class="text-small-muted">${c.motivo}</span></td>
                <td><span class="status-dot dot-espera"></span>En Espera</td>
                <td><button class="btn-success btn-small" onclick="atenderSolicitud(${c.id})">🎥 Contestar</button></td>
            </tr>
        `).join('');
    }

    document.getElementById('tabla-historial').innerHTML = state.historial.map(h => `
        <tr>
            <td><code>${h.sala}</code></td>
            <td><strong>${h.empresa}</strong></td>
            <td>${h.interprete}</td>
            <td>${h.fecha}</td>
            <td>${h.duracionSeg} seg</td>
            <td><span class="badge">${h.minutos} min</span></td>
        </tr>
    `).join('');

    const selectQr = document.getElementById('qr-empresa');
    selectQr.innerHTML = state.empresas.map(e => `<option value="${e.id}">${e.nombre} (${e.token_qr})</option>`).join('');
}

document.addEventListener('DOMContentLoaded', cargarDatosDesdeDjango);


// =======================================================
// LÓGICA DEL CHATBOT IA (PREGUNTAS FRECUENTES CASPE)
// =======================================================
function toggleChatbot() {
    const win = document.getElementById('chatbot-window');
    win.classList.toggle('hidden');
}

function enviarPreguntaRapida(texto) {
    document.getElementById('chatbot-input').value = texto;
    enviarMensajeChat(new Event('submit'));
}

async function enviarMensajeChat(event) {
    if (event.preventDefault) event.preventDefault();
    const input = document.getElementById('chatbot-input');
    const mensaje = input.value.trim();
    if (!mensaje) return;

    const msgContainer = document.getElementById('chatbot-messages');

    // 1. Mostrar pregunta del usuario
    msgContainer.innerHTML += `<div class="chat-msg user-msg">${mensaje}</div>`;
    input.value = '';
    msgContainer.scrollTop = msgContainer.scrollHeight;

    // 2. Indicador "Escribiendo..."
    const tempId = 'typing-' + Date.now();
    msgContainer.innerHTML += `<div id="${tempId}" class="chat-msg bot-msg text-muted">⏳ Analizando consulta...</div>`;
    msgContainer.scrollTop = msgContainer.scrollHeight;

    // 3. Consultar al endpoint IA en Django
    const res = await fetch('/api/chatbot/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mensaje })
    });
    const data = await res.json();

    // Formatear negritas simples (**texto**) a HTML
    const respuestaFormateada = data.respuesta.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    const typingEl = document.getElementById(tempId);
    if (typingEl) typingEl.remove();

    msgContainer.innerHTML += `<div class="chat-msg bot-msg">${respuestaFormateada}</div>`;
    msgContainer.scrollTop = msgContainer.scrollHeight;
}