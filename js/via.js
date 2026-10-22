/**
 * VÍA · Asistente virtual de la historia de Las Varillas
 * Frontend sin dependencias. Toda la lógica técnica (MCP, Ollama, estado del
 * servidor) ocurre en segundo plano: el usuario solo ve la conversación.
 *
 * AUDITORÍA SOLID (resumen de este archivo):
 *  - SRP: el archivo agrupa varias áreas (historial, markdown, mensajes, streaming,
 *    libro histórico, logo). Cada área está separada en una sección y en funciones
 *    de una sola tarea. Se extrajeron tres piezas repetidas o mezcladas:
 *      · HISTORY_EMPTY_HTML  (texto de "sin conversaciones", estaba duplicado)
 *      · showProse(bot)      (mostrar la respuesta; estaba repetido 3 veces)
 *      · readSSE(res, fn)    (lectura del stream; estaba dentro de ask(), que
 *                             mezclaba UI + red + parseo)
 *  - OCP: las sugerencias, saludos y textos salen de data/bienvenida.json; el
 *    markdown y el historial se pueden ampliar sin tocar el resto.
 *  - LSP/ISP: cada función recibe solo lo que necesita (ej. addSources(bot, chunks)).
 *  - DIP: la UI no conoce el formato del servidor más allá de los eventos SSE
 *    (mcp_context / token / error) que procesa `handle` dentro de ask().
 *  - Comportamiento, textos, estilos y orden de ejecución: IDÉNTICOS al original.
 */
// Función autoejecutable: aísla todas las variables (nada se filtra al ámbito global).
(() => {
  // Modo estricto: el navegador avisa de errores silenciosos.
  'use strict';

  // ---------------------------------------------------------------------------
  // Referencias
  // ---------------------------------------------------------------------------
  // Atajo para buscar un elemento por su id.
  const $ = (id) => document.getElementById(id);
  // Contenedor principal de la app.
  const app = $('app');
  // Zona con scroll de la conversación.
  const thread = $('thread');
  // Contenedor interno donde se agregan los mensajes.
  const threadInner = $('thread-inner');
  // Formulario de chat.
  const form = $('chat-form');
  // Caja de texto del usuario.
  const input = $('user-input');
  // Botón de enviar.
  const sendBtn = $('send-button');
  // Contenedor de preguntas sugeridas.
  const chipsEl = $('chips');
  // Botón "Nueva conversación".
  const btnNew = $('btn-new');
  // Botón del libro histórico.
  const btnBook = $('btn-book');
  // Botón del historial.
  const btnHistory = $('btn-history');
  // Panel (drawer) del libro histórico.
  const drawer = $('drawer');
  // Fondo oscuro del panel del libro.
  const scrim = $('scrim');
  // Botón de cerrar el libro.
  const drawerClose = $('drawer-close');
  // Lista de acordeones del libro.
  const acc = $('acc');
  // Indicador de carga del libro.
  const drawerLoading = $('drawer-loading');
  // Contenedor general (para el modo dividido).
  const shell = $('shell');
  // Botón para anclar/soltar el libro.
  const drawerMode = $('drawer-mode');
  // Marca (logo) del encabezado.
  const brand = document.querySelector('.brand');
  // Historia
  // Panel del historial de conversaciones.
  const historyPanel = $('history-panel');
  // Fondo oscuro del historial.
  const historyScrim = $('history-scrim');
  // Botón de cerrar el historial.
  const historyClose = $('history-close');
  // Lista donde se dibujan las conversaciones guardadas.
  const historyList = $('history-list');

  // Respaldo por si data/bienvenida.json no está disponible
  // [OCP] Valores por defecto: si el JSON de bienvenida falla, la app igual funciona.
  const DEFAULT_WELCOME = {
    // Saludos posibles.
    saludos: ['Hola, soy VÍA'],
    // Título principal.
    titulo: 'Comencemos. ¿Qué quieres saber sobre la historia de Las Varillas?',
    // Texto de ayuda de la caja de entrada.
    placeholder: 'Pregúntale a VÍA sobre Las Varillas',
    // Preguntas sugeridas.
    sugerencias: [
      // Sugerencia 1.
      '¿A qué postura suscribe el Arq. Valter Dabbene?',
      // Sugerencia 2.
      '¿Qué afirma el Centro de Estudios Parada KM 81?',
      // Sugerencia 3.
      'Dame un resumen de las tres teorías fundacionales'
    // Cierra la lista de sugerencias.
    ]
  // Cierra el objeto.
  };

  // Logo en resolución normal.
  const LOGO_1X = 'assets/VIA%20LOGO%20(512%20x%20512%20px).svg';
  // Logo en alta densidad de píxeles.
  const LOGO_2X = 'assets/VIA%20LOGO%20(1024%20x%201024%20px).svg';

  // Datos de bienvenida activos (empiezan con los de respaldo).
  let welcome = DEFAULT_WELCOME;
  // Indica si hay una respuesta generándose.
  let generating = false;
  // Última pregunta (para "Reintentar").
  let lastQuestion = '';

  // ---------------------------------------------------------------------------
  // Historial de conversaciones (localStorage)
  // [SRP] Esta sección solo guarda/lee conversaciones; no toca la interfaz.
  // ---------------------------------------------------------------------------
  // Clave de localStorage.
  const HISTORY_KEY = 'via_history';
  // Cantidad máxima de conversaciones guardadas.
  const HISTORY_MAX = 40;       // máximo de conversaciones guardadas

  // [SRP] Texto de "sin conversaciones" (antes estaba escrito 2 veces).
  const HISTORY_EMPTY_HTML = '<p class="hist__empty">Todavía no hay conversaciones guardadas.<br>¡Hazme una pregunta para empezar!</p>';

  // Conversación activa en memoria
  // Sesión actual (null si no hay).
  let activeSession = null;     // { id, title, ts, messages: [{role, text, chunks?}] }

  // Lee la lista guardada (o [] si falla o no existe).
  function loadHistory() {
    // Intenta leer y convertir el JSON; si falla devuelve lista vacía.
    try { return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]'); } catch (_) { return []; }
  }
  // Guarda la lista (recortada al máximo permitido).
  function saveHistory(list) {
    // Intenta guardar; si no hay espacio, lo ignora.
    try { localStorage.setItem(HISTORY_KEY, JSON.stringify(list.slice(0, HISTORY_MAX))); } catch (_) { /* sin espacio */ }
  }

  // Guarda la conversación activa al inicio de la lista.
  function saveActiveSession() {
    // Si no hay sesión o está vacía, no hace nada.
    if (!activeSession || !activeSession.messages.length) return;
    // Lee el historial actual.
    const list = loadHistory();
    // Busca si esta sesión ya estaba guardada.
    const idx = list.findIndex((s) => s.id === activeSession.id);
    // Si estaba, la quita (para reubicarla al principio).
    if (idx >= 0) list.splice(idx, 1);
    // La agrega al principio.
    list.unshift(activeSession);
    // Persiste la lista.
    saveHistory(list);
  }

  // Crea una sesión nueva a partir de la primera pregunta.
  function startNewSession(firstQuestion) {
    // Define la sesión activa.
    activeSession = {
      // Id único (hora + azar en base 36).
      id: Date.now().toString(36) + Math.random().toString(36).slice(2, 6),
      // Título: primeros 80 caracteres de la pregunta.
      title: firstQuestion.slice(0, 80),
      // Momento de creación.
      ts: Date.now(),
      // Mensajes (vacío al inicio).
      messages: []
    // Cierra el objeto.
    };
  }

  // Registra un mensaje del usuario en la sesión.
  function pushUserMsg(text) {
    // Sin sesión no hace nada.
    if (!activeSession) return;
    // Agrega el mensaje del usuario.
    activeSession.messages.push({ role: 'user', text });
  }

  // Registra un mensaje de VÍA y guarda la sesión.
  function pushBotMsg(text, chunks) {
    // Sin sesión no hace nada.
    if (!activeSession) return;
    // Agrega el mensaje del bot con sus fuentes.
    activeSession.messages.push({ role: 'bot', text, chunks: chunks || [] });
    // Guarda la sesión en el historial.
    saveActiveSession();
  }

  // ---------------------------------------------------------------------------
  // Panel de historial
  // [SRP] Esta sección solo abre/cierra y dibuja el panel de historial.
  // ---------------------------------------------------------------------------
  // Indica si el panel de historial está abierto.
  const isHistoryOpen = () => historyPanel.classList.contains('is-open');

  // Abre el panel de historial.
  function openHistory() {
    // Dibuja la lista actualizada.
    renderHistoryList();
    // Muestra el fondo oscuro.
    historyScrim.hidden = false;
    // Hace el panel interactivo.
    historyPanel.inert = false;
    // Accesibilidad: el panel es visible.
    historyPanel.setAttribute('aria-hidden', 'false');
    // Accesibilidad: el botón indica que está expandido.
    btnHistory.setAttribute('aria-expanded', 'true');
    // Espera al siguiente cuadro para animar.
    requestAnimationFrame(() => {
      // Activa el fondo.
      historyScrim.classList.add('is-on');
      // Activa el panel.
      historyPanel.classList.add('is-open');
    });
    // Lleva el foco al botón de cerrar.
    historyClose.focus({ preventScroll: true });
  }

  // Cierra el panel de historial.
  function closeHistory() {
    // Si ya está cerrado, no hace nada.
    if (!isHistoryOpen()) return;
    // Quita la clase de abierto.
    historyPanel.classList.remove('is-open');
    // Oculta el fondo con animación.
    historyScrim.classList.remove('is-on');
    // Accesibilidad: el panel no es visible.
    historyPanel.setAttribute('aria-hidden', 'true');
    // Desactiva la interacción con el panel.
    historyPanel.inert = true;
    // Accesibilidad: el botón indica que está contraído.
    btnHistory.setAttribute('aria-expanded', 'false');
    // Tras la animación (260 ms) oculta el fondo.
    setTimeout(() => { historyScrim.hidden = true; }, 260);
  }

  // Convierte una fecha en texto relativo ("Hace 5 min").
  function relativeDate(ts) {
    // Milisegundos transcurridos.
    const diff = Date.now() - ts;
    // Minutos transcurridos.
    const m = Math.floor(diff / 60000);
    // Menos de 1 minuto.
    if (m < 1) return 'Ahora mismo';
    // Menos de 1 hora.
    if (m < 60) return `Hace ${m} min`;
    // Horas transcurridas.
    const h = Math.floor(m / 60);
    // Menos de 1 día.
    if (h < 24) return `Hace ${h} h`;
    // Días transcurridos.
    const d = Math.floor(h / 24);
    // Exactamente 1 día.
    if (d === 1) return 'Ayer';
    // Menos de una semana.
    if (d < 7) return `Hace ${d} días`;
    // Más antiguo: fecha corta en español de Argentina.
    return new Date(ts).toLocaleDateString('es-AR', { day: 'numeric', month: 'short' });
  }

  // Dibuja la lista de conversaciones guardadas.
  function renderHistoryList() {
    // Lee el historial.
    const list = loadHistory();
    // Limpia la lista actual.
    historyList.innerHTML = '';
    // Si no hay conversaciones...
    if (!list.length) {
      // ...muestra el mensaje vacío...
      historyList.innerHTML = HISTORY_EMPTY_HTML;
      // ...y termina.
      return;
    }
    // Recorre cada conversación.
    list.forEach((session) => {
      // Crea el contenedor del ítem.
      const item = document.createElement('div');
      // Clase base del ítem.
      item.className = 'hist__item';
      // Marca la conversación activa.
      if (activeSession && session.id === activeSession.id) item.classList.add('is-active');
      // Inserta los botones de retomar y eliminar (texto escapado contra HTML inyectado).
      item.innerHTML = `
        <button class="hist__btn" type="button" aria-label="Retomar: ${escapeHtml(session.title)}">
          <span class="hist__title">${escapeHtml(session.title)}</span>
          <span class="hist__date">${relativeDate(session.ts)}</span>
        </button>
        <button class="hist__del" type="button" aria-label="Eliminar esta conversación" title="Eliminar">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12"/></svg>
        </button>`;
      // Al hacer clic en el título, retoma la conversación.
      item.querySelector('.hist__btn').addEventListener('click', () => restoreSession(session));
      // Al hacer clic en la X...
      item.querySelector('.hist__del').addEventListener('click', (e) => {
        // ...evita que el clic afecte a otros elementos...
        e.stopPropagation();
        // ...y elimina la conversación.
        deleteSession(session.id, item);
      });
      // Agrega el ítem a la lista.
      historyList.appendChild(item);
    });
  }

  // [SRP] Muestra la respuesta ya lista: quita el cursor de streaming, oculta el
  // esqueleto y muestra el texto. Antes estas 3 líneas se repetían en
  // restoreSession, showError y ask.
  function showProse(bot) {
    // Quita la animación de "escribiendo".
    bot.wrap.classList.remove('is-streaming');
    // Oculta el esqueleto de carga.
    bot.skeleton.hidden = true;
    // Muestra el área de texto.
    bot.prose.hidden = false;
  }

  // Retoma una conversación guardada.
  function restoreSession(session) {
    // Si se está generando una respuesta, no hace nada.
    if (generating) return;
    // Cierra el panel de historial.
    closeHistory();
    // Guardar sesión actual antes de cambiar
    // Guarda la sesión que estaba abierta.
    saveActiveSession();
    // Copia profunda de la sesión elegida.
    activeSession = JSON.parse(JSON.stringify(session)); // copia profunda
    // Reconstruir el hilo visualmente
    // Vacía el hilo actual.
    threadInner.innerHTML = '';
    // Pasa a modo conversación.
    setConversationMode(true);
    // Recorre los mensajes guardados.
    session.messages.forEach((msg) => {
      // Mensaje del usuario.
      if (msg.role === 'user') {
        // Lo dibuja.
        addUserMessage(msg.text);
      // Mensaje de VÍA.
      } else {
        // Crea la estructura del mensaje.
        const bot = addBotShell();
        // Muestra el texto en lugar del esqueleto.
        showProse(bot);
        // Escribe el texto con formato markdown.
        bot.prose.innerHTML = markdown(msg.text || '');
        // Si hay fuentes, las agrega.
        if (msg.chunks && msg.chunks.length) addSources(bot, msg.chunks);
        // Agrega el botón de copiar.
        addActions(bot, msg.text || '');
      }
    });
    // Baja al final de la conversación.
    scrollToBottom(true);
    // Lleva el foco a la caja de texto.
    input.focus({ preventScroll: true });
  }

  // Elimina una conversación del historial.
  function deleteSession(id, itemEl) {
    // Lista sin la conversación eliminada.
    const list = loadHistory().filter((s) => s.id !== id);
    // Guarda la nueva lista.
    saveHistory(list);
    // Inicia la animación de salida.
    itemEl.classList.add('hist__item--removing');
    // Cuando termina la animación (300 ms)...
    setTimeout(() => {
      // ...quita el ítem del DOM...
      itemEl.remove();
      // ...y si no quedan ítems...
      if (!historyList.querySelector('.hist__item')) {
        // ...muestra el mensaje vacío.
        historyList.innerHTML = HISTORY_EMPTY_HTML;
      }
    }, 300);
    // Si se eliminó la conversación activa, la desvincula.
    if (activeSession && activeSession.id === id) activeSession = null;
  }

  // Botón del historial: abre o cierra el panel.
  btnHistory.addEventListener('click', () => (isHistoryOpen() ? closeHistory() : openHistory()));
  // Botón X: cierra el historial.
  historyClose.addEventListener('click', closeHistory);
  // Clic en el fondo: cierra el historial.
  historyScrim.addEventListener('click', closeHistory);
  // Escucha el teclado en toda la página.
  document.addEventListener('keydown', (e) => {
    // Escape cierra el historial si está abierto.
    if (e.key === 'Escape' && isHistoryOpen()) closeHistory();
  });

  // ---------------------------------------------------------------------------
  // Utilidades
  // ---------------------------------------------------------------------------
  // Escapa caracteres especiales de HTML (seguridad contra inyección de código).
  const escapeHtml = (s) =>
    // Convierte a texto (null/undefined -> vacío).
    String(s ?? '')
      // Escapa & < >.
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      // Escapa comillas dobles y simples.
      .replace(/"/g, '&quot;').replace(/'/g, '&#039;');

  // Parte principal del título (antes de " - ").
  const shortTitle = (t) => String(t || '').split(' - ')[0].trim();
  // Subtítulo (lo que sigue a " - ").
  const subTitle = (t) => String(t || '').split(' - ').slice(1).join(' - ').trim();

  // Crea un elemento con clase y HTML opcionales.
  function el(tag, className, html) {
    // Crea el nodo.
    const node = document.createElement(tag);
    // Asigna la clase si se indicó.
    if (className) node.className = className;
    // Asigna el HTML interno si se indicó.
    if (html !== undefined) node.innerHTML = html;
    // Devuelve el nodo.
    return node;
  }

  // Indica si el usuario está cerca del final del scroll.
  function nearBottom() {
    // Distancia restante hasta el final menor a 140 px.
    return thread.scrollHeight - thread.scrollTop - thread.clientHeight < 140;
  }
  // Baja al final (siempre si `force`, o solo si ya estaba cerca).
  function scrollToBottom(force) {
    // Mueve el scroll al final.
    if (force || nearBottom()) thread.scrollTop = thread.scrollHeight;
  }

  // Marca del logo (mismo recorte y resoluciones que el encabezado)
  // Devuelve el HTML de la marca con imagen 1x/2x.
  function logoMark(extraClass = '') {
    // Estructura del logo con srcset para alta densidad.
    return `<span class="via-mark ${extraClass}" aria-hidden="true"><img src="${LOGO_1X}" srcset="${LOGO_1X} 1x, ${LOGO_2X} 2x" alt="" decoding="async"></span>`;
  }

  // ---------------------------------------------------------------------------
  // Markdown ligero y seguro (se escapa todo el HTML antes de formatear)
  // [SRP] Solo convierte texto -> HTML; no conoce el chat ni la red.
  // ---------------------------------------------------------------------------
  // Formato en línea: `código`, **negrita** y *cursiva*.
  function inline(text) {
    // Primero escapa el HTML y luego aplica el formato.
    return escapeHtml(text)
      // `texto` -> <code>.
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      // **texto** -> <strong>.
      .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
      // *texto* -> <em>.
      .replace(/(^|[^*\w])\*([^*\n]+)\*(?!\*)/g, '$1<em>$2</em>');
  }

  // Convierte un texto markdown simple en HTML.
  function markdown(src) {
    // Divide el texto en líneas (sin retornos de carro).
    const lines = String(src || '').replace(/\r/g, '').split('\n');
    // Acumulador del HTML resultante.
    const out = [];
    // Lista abierta actualmente.
    let list = null; // 'ul' | 'ol'
    // Cierra la lista abierta, si hay una.
    const closeList = () => { if (list) { out.push(`</${list}>`); list = null; } };

    // Procesa línea por línea.
    for (const raw of lines) {
      // Quita espacios finales.
      const line = raw.trimEnd();
      // Resultado de cada expresión regular.
      let m;
      // Línea vacía: cierra la lista y sigue.
      if (!line.trim()) { closeList(); continue; }
      // Títulos (# a ####) -> <h3>.
      if ((m = line.match(/^#{1,4}\s+(.*)$/))) {
        // Cierra lista y agrega el título.
        closeList(); out.push(`<h3>${inline(m[1])}</h3>`);
      // Viñetas (-, * o •).
      } else if ((m = line.match(/^\s*[-*•]\s+(.*)$/))) {
        // Abre una lista no ordenada si hace falta.
        if (list !== 'ul') { closeList(); out.push('<ul>'); list = 'ul'; }
        // Agrega el ítem.
        out.push(`<li>${inline(m[1])}</li>`);
      // Listas numeradas (1. o 1)).
      } else if ((m = line.match(/^\s*\d+[.)]\s+(.*)$/))) {
        // Abre una lista ordenada si hace falta.
        if (list !== 'ol') { closeList(); out.push('<ol>'); list = 'ol'; }
        // Agrega el ítem.
        out.push(`<li>${inline(m[1])}</li>`);
      // Cualquier otra línea: párrafo.
      } else {
        // Cierra lista y agrega el párrafo.
        closeList(); out.push(`<p>${inline(line)}</p>`);
      }
    }
    // Cierra una lista que haya quedado abierta.
    closeList();
    // Devuelve todo el HTML unido.
    return out.join('');
  }

  // ---------------------------------------------------------------------------
  // Bienvenida dinámica (data/bienvenida.json)
  // ---------------------------------------------------------------------------
  // Carga los textos de bienvenida desde el servidor.
  async function loadWelcome() {
    // Protege contra errores de red/formato.
    try {
      // Pide el JSON sin usar caché.
      const res = await fetch('data/bienvenida.json', { cache: 'no-cache' });
      // Si la respuesta no es correcta, lanza error.
      if (!res.ok) throw new Error(res.status);
      // Lee el JSON.
      const data = await res.json();
      // Combina los valores por defecto con los recibidos.
      welcome = { ...DEFAULT_WELCOME, ...data };
    // Si algo falla...
    } catch (_) {
      // ...usa los valores por defecto.
      welcome = DEFAULT_WELCOME;
    }
    // Dibuja la bienvenida.
    renderWelcome();
  }

  // Dibuja saludo, título, placeholder y sugerencias.
  function renderWelcome() {
    // Lista de saludos (o la de respaldo si está vacía).
    const saludos = welcome.saludos?.length ? welcome.saludos : DEFAULT_WELCOME.saludos;
    // Elige un saludo al azar.
    $('hero-greeting').textContent = saludos[Math.floor(Math.random() * saludos.length)];
    // Título principal.
    $('hero-title').textContent = welcome.titulo || DEFAULT_WELCOME.titulo;
    // Texto de ayuda de la caja de entrada.
    input.placeholder = welcome.placeholder || DEFAULT_WELCOME.placeholder;

    // Limpia las sugerencias anteriores.
    chipsEl.innerHTML = '';
    // Crea un botón por cada sugerencia.
    (welcome.sugerencias || []).forEach((q, i) => {
      // Acepta texto simple u objeto con `texto`.
      const text = typeof q === 'string' ? q : q.texto;
      // Ignora sugerencias sin texto.
      if (!text) return;
      // Crea el botón.
      const b = el('button', 'chip');
      // Tipo botón (no envía formularios).
      b.type = 'button';
      // Accesibilidad: elemento de lista.
      b.setAttribute('role', 'listitem');
      // Retardo escalonado de la animación de entrada.
      b.style.animationDelay = `${120 + i * 70}ms`;
      // Texto visible.
      b.textContent = text;
      // Al hacer clic, envía esa pregunta.
      b.addEventListener('click', () => ask(text));
      // Agrega el botón al contenedor.
      chipsEl.appendChild(b);
    });
  }

  // ---------------------------------------------------------------------------
  // Caja de entrada
  // ---------------------------------------------------------------------------
  // Ajusta el alto de la caja y el estado del botón de enviar.
  function syncInput() {
    // Reinicia el alto para medir bien.
    input.style.height = 'auto';
    // Alto según el contenido (máximo 200 px).
    input.style.height = Math.min(input.scrollHeight, 200) + 'px';
    // Deshabilita enviar si se está generando o la caja está vacía.
    sendBtn.disabled = generating || !input.value.trim();
  }

  // Al escribir, sincroniza la caja.
  input.addEventListener('input', syncInput);
  // Al presionar teclas en la caja...
  input.addEventListener('keydown', (e) => {
    // Enter sin Shift (y sin composición de teclado IME) envía el formulario.
    if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
      // Evita el salto de línea.
      e.preventDefault();
      // Envía el formulario.
      form.requestSubmit();
    }
  });
  // Al enviar el formulario...
  form.addEventListener('submit', (e) => {
    // Evita recargar la página.
    e.preventDefault();
    // Pregunta sin espacios sobrantes.
    const q = input.value.trim();
    // Si hay texto, pregunta.
    if (q) ask(q);
  });

  // ---------------------------------------------------------------------------
  // Mensajes
  // [SRP] Cada función crea una pieza concreta de la conversación.
  // ---------------------------------------------------------------------------
  // Alterna entre pantalla de bienvenida y conversación.
  function setConversationMode(on) {
    // Agrega/quita la clase "is-empty".
    app.classList.toggle('is-empty', !on);
    // Muestra el botón "nueva conversación" solo en modo conversación.
    btnNew.hidden = !on;
  }

  // Agrega la burbuja del usuario.
  function addUserMessage(text) {
    // Contenedor del mensaje.
    const wrap = el('article', 'msg msg--user');
    // Burbuja de texto.
    const bubble = el('div', 'msg__bubble');
    // Texto como texto plano (seguro).
    bubble.textContent = text;
    // Inserta la burbuja.
    wrap.appendChild(bubble);
    // Agrega el mensaje al hilo.
    threadInner.appendChild(wrap);
    // Devuelve el contenedor.
    return wrap;
  }

  // Crea la estructura vacía de un mensaje de VÍA (con esqueleto de carga).
  function addBotShell() {
    // Contenedor del mensaje, en estado "escribiendo".
    const wrap = el('article', 'msg msg--bot is-streaming');
    // Contenido: logo, esqueleto de carga y área de texto oculta.
    wrap.innerHTML = `
      ${logoMark()}
      <div class="msg__main">
        <div class="skel-lines" data-role="skeleton" aria-label="VÍA está escribiendo">
          <div class="skel skel--line" style="width:92%"></div>
          <div class="skel skel--line" style="width:78%"></div>
          <div class="skel skel--line" style="width:54%"></div>
        </div>
        <div class="prose" data-role="prose" hidden></div>
      </div>`;
    // Agrega el mensaje al hilo.
    threadInner.appendChild(wrap);
    // Devuelve referencias a sus partes.
    return {
      // Contenedor.
      wrap,
      // Columna principal.
      main: wrap.querySelector('.msg__main'),
      // Esqueleto de carga.
      skeleton: wrap.querySelector('[data-role=skeleton]'),
      // Área de texto.
      prose: wrap.querySelector('[data-role=prose]')
    // Cierra el objeto.
    };
  }

  // Agrega los botones de fuentes bajo la respuesta.
  function addSources(bot, chunks) {
    // Conjunto para evitar fuentes repetidas.
    const seen = new Set();
    // Fuentes únicas y con id.
    const items = (chunks || []).filter((c) => c && c.id && !seen.has(c.id) && seen.add(c.id));
    // Si no hay fuentes, termina.
    if (!items.length) return;
    // Contenedor de fuentes.
    const row = el('div', 'sources');
    // Etiqueta "Fuentes".
    row.appendChild(el('span', 'sources__label', 'Fuentes'));
    // Un botón por fuente.
    items.forEach((c) => {
      // Crea el botón.
      const b = el('button', 'source');
      // Tipo botón.
      b.type = 'button';
      // Texto: título corto o el id.
      b.textContent = shortTitle(c.titulo) || c.id;
      // Ayuda al pasar el cursor.
      b.title = 'Ver en el libro histórico';
      // Al hacer clic, abre esa sección del libro.
      b.addEventListener('click', () => openDrawer(c.id));
      // Agrega el botón a la fila.
      row.appendChild(b);
    });
    // Agrega la fila al mensaje.
    bot.main.appendChild(row);
  }

  // Agrega el botón "Copiar" bajo la respuesta.
  function addActions(bot, text) {
    // Contenedor de acciones.
    const row = el('div', 'actions');
    // Botón de copiar con su ícono.
    const copy = el('button', 'action',
      '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg><span>Copiar</span>');
    // Tipo botón.
    copy.type = 'button';
    // Al hacer clic...
    copy.addEventListener('click', async () => {
      // Protege si no hay permiso de portapapeles.
      try {
        // Copia el texto al portapapeles.
        await navigator.clipboard.writeText(text);
        // Cambia la etiqueta a "Copiado".
        copy.querySelector('span').textContent = 'Copiado';
        // A los 1,8 s vuelve a "Copiar".
        setTimeout(() => (copy.querySelector('span').textContent = 'Copiar'), 1800);
      // Si no hay portapapeles, no hace nada.
      } catch (_) { /* sin portapapeles disponible */ }
    });
    // Agrega el botón a la fila.
    row.appendChild(copy);
    // Agrega la fila al mensaje.
    bot.main.appendChild(row);
  }

  // Muestra el mensaje de error con botón de reintentar.
  function showError(bot) {
    // Muestra el área de texto (sin cursor ni esqueleto).
    showProse(bot);
    // Escribe el mensaje de error.
    bot.prose.innerHTML = '<p>No pude responder en este momento. Inténtalo de nuevo en unos segundos.</p>';
    // Botón "Reintentar".
    const retry = el('button', 'retry', 'Reintentar');
    // Tipo botón.
    retry.type = 'button';
    // Al hacer clic...
    retry.addEventListener('click', () => {
      // ...elimina el mensaje de error...
      bot.wrap.remove();
      // ...y repite la última pregunta sin duplicar la burbuja del usuario.
      ask(lastQuestion, { reuseUser: true });
    });
    // Agrega el botón al mensaje.
    bot.main.appendChild(retry);
  }

  // ---------------------------------------------------------------------------
  // Envío y streaming (SSE sobre POST /api/chat/stream)
  // ---------------------------------------------------------------------------
  // [SRP] Responsabilidad única: leer un stream SSE y entregar cada evento ya
  // interpretado. Antes este bloque estaba dentro de ask(), junto con la UI.
  // [DIP] `ask` depende de un callback (`onEvent`), no de cómo se parsea el stream.
  async function readSSE(res, onEvent) {
    // Lector del cuerpo de la respuesta.
    const reader = res.body.getReader();
    // Decodificador de bytes a texto UTF-8.
    const decoder = new TextDecoder('utf-8');
    // Texto pendiente de completar.
    let buffer = '';

    // Bucle infinito hasta que termine el stream.
    for (;;) {
      // Lee el siguiente bloque de datos.
      const { value, done } = await reader.read();
      // Si terminó, sale del bucle.
      if (done) break;
      // Agrega el bloque decodificado al buffer.
      buffer += decoder.decode(value, { stream: true });
      // Los eventos SSE se separan por línea en blanco.
      const parts = buffer.split('\n\n');
      // Guarda el último fragmento (posiblemente incompleto).
      buffer = parts.pop();
      // Procesa cada evento completo.
      for (const part of parts) {
        // Busca la línea que empieza con "data:".
        const line = part.split('\n').find((l) => l.startsWith('data:'));
        // Si no hay línea de datos, la ignora.
        if (!line) continue;
        // Interpreta el JSON y lo entrega; si está incompleto, lo ignora.
        try { onEvent(JSON.parse(line.slice(5).trim())); } catch (_) { /* evento incompleto */ }
      }
    }
  }

  // Envía una pregunta y muestra la respuesta en streaming.
  async function ask(question, opts = {}) {
    // Si ya se genera una respuesta o no hay pregunta, no hace nada.
    if (generating || !question) return;
    // Marca que se está generando.
    generating = true;
    // Recuerda la pregunta para "Reintentar".
    lastQuestion = question;

    // Iniciar sesión si no hay una activa
    // Crea la sesión si no existe.
    if (!activeSession) startNewSession(question);

    // Vacía la caja de texto.
    input.value = '';
    // Sincroniza la caja y el botón.
    syncInput();
    // Pasa a modo conversación.
    setConversationMode(true);
    // Si no es un reintento...
    if (!opts.reuseUser) {
      // ...dibuja la burbuja del usuario...
      addUserMessage(question);
      // ...y la guarda en la sesión.
      pushUserMsg(question);
    }

    // Crea el mensaje de VÍA con esqueleto de carga.
    const bot = addBotShell();
    // Baja al final.
    scrollToBottom(true);

    // Texto acumulado de la respuesta.
    let text = '';
    // Fuentes recibidas.
    let chunks = [];
    // Id del cuadro de animación pendiente.
    let raf = 0;
    // Indica si la respuesta falló.
    let failed = false;

    // Redibuja el texto acumulado.
    const paint = () => {
      // Libera el pedido de animación.
      raf = 0;
      // ¿Estaba el usuario cerca del final?
      const stick = nearBottom();
      // Escribe el texto con formato.
      bot.prose.innerHTML = markdown(text);
      // Si estaba cerca del final, lo mantiene abajo.
      if (stick) scrollToBottom(true);
    };

    // Intenta comunicar primero por WebSocket (Plan Taller MCP)
    let wsSuccess = false;
    try {
      wsSuccess = await new Promise((resolve) => {
        const wsProto = location.protocol === 'https:' ? 'wss:' : 'ws:';
        const ws = new WebSocket(`${wsProto}//${location.host}/ws/chat`);
        const timer = setTimeout(() => {
          try { ws.close(); } catch (_) {}
          resolve(false);
        }, 3500);

        ws.onopen = () => {
          clearTimeout(timer);
          ws.send(JSON.stringify({ text: question, message: question, use_mcp: true }));
        };

        ws.onmessage = (event) => {
          try {
            const evt = JSON.parse(event.data);
            if (evt.type === 'status') {
              if (bot.skeleton && !bot.skeleton.hidden) {
                let st = bot.skeleton.querySelector('.skel--status');
                if (!st) {
                  st = document.createElement('div');
                  st.className = 'skel--status';
                  st.style.fontSize = '12px';
                  st.style.color = '#94a3b8';
                  st.style.marginTop = '6px';
                  bot.skeleton.appendChild(st);
                }
                st.textContent = evt.message;
              }
            } else if (evt.type === 'token') {
              if (bot.skeleton && !bot.skeleton.hidden) {
                bot.skeleton.hidden = true;
                bot.prose.hidden = false;
              }
              text += evt.token;
              if (!raf) raf = requestAnimationFrame(paint);
            } else if (evt.type === 'response') {
              if (bot.skeleton && !bot.skeleton.hidden) {
                bot.skeleton.hidden = true;
                bot.prose.hidden = false;
              }
              text = evt.content;
              paint();
            } else if (evt.type === 'mcp_context') {
              chunks = Array.isArray(evt.mcp?.chunks) ? evt.mcp.chunks : [];
            } else if (evt.type === 'done') {
              try { ws.close(); } catch (_) {}
              resolve(true);
            } else if (evt.type === 'error') {
              if (!text) failed = true;
            }
          } catch (_) {}
        };

        ws.onerror = () => {
          clearTimeout(timer);
          resolve(false);
        };

        ws.onclose = () => {
          clearTimeout(timer);
          resolve(Boolean(text));
        };
      });
    } catch (_) {
      wsSuccess = false;
    }

    // Si WebSocket no respondió o no se pudo conectar, recurre a HTTP POST /api/chat/stream
    if (!wsSuccess && !text) {
      try {
        const res = await fetch('/api/chat/stream', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: question, use_mcp: true })
        });
        if (!res.ok || !res.body) throw new Error('http ' + res.status);
        const handle = (evt) => {
          if (evt.type === 'mcp_context') {
            chunks = Array.isArray(evt.mcp?.chunks) ? evt.mcp.chunks : [];
          } else if (evt.type === 'token') {
            if (bot.skeleton && !bot.skeleton.hidden) {
              bot.skeleton.hidden = true;
              bot.prose.hidden = false;
            }
            text += evt.token;
            if (!raf) raf = requestAnimationFrame(paint);
          } else if (evt.type === 'error') {
            failed = !text;
          }
        };
        await readSSE(res, handle);
      } catch (_) {
        failed = !text;
      }
    }

    // Cancela un redibujado pendiente.
    if (raf) cancelAnimationFrame(raf);

    // Si falló o no hay texto...
    if (failed || !text.trim()) {
      // ...muestra el error.
      showError(bot);
    // Si todo salió bien...
    } else {
      // Muestra el texto final (sin cursor ni esqueleto).
      showProse(bot);
      // Dibuja el texto definitivo con formato.
      bot.prose.innerHTML = markdown(text);
      // Agrega las fuentes.
      addSources(bot, chunks);
      // Agrega el botón de copiar.
      addActions(bot, text);
      // Guarda la respuesta en el historial.
      pushBotMsg(text, chunks);
    }

    // Baja al final.
    scrollToBottom(true);
    // Marca que terminó la generación.
    generating = false;
    // Sincroniza la caja y el botón.
    syncInput();
    // Devuelve el foco a la caja.
    input.focus({ preventScroll: true });
  }

  // ---------------------------------------------------------------------------
  // Nueva conversación
  // ---------------------------------------------------------------------------
  // Botón "Nueva conversación".
  btnNew.addEventListener('click', () => {
    // No permite cambiar mientras se genera una respuesta.
    if (generating) return;
    // Guarda la conversación actual.
    saveActiveSession();
    // Desvincula la sesión.
    activeSession = null;
    // Vacía el hilo.
    threadInner.innerHTML = '';
    // Vuelve a la pantalla de bienvenida.
    setConversationMode(false);
    // Redibuja la bienvenida.
    renderWelcome();
    // Vacía la caja de texto.
    input.value = '';
    // Sincroniza la caja y el botón.
    syncInput();
    // Lleva el foco a la caja.
    input.focus();
  });

  // ---------------------------------------------------------------------------
  // Libro histórico: panel con acordeones y carga progresiva
  // ---------------------------------------------------------------------------
  // Lista liviana del libro (id, título, tags).
  let bookIndex = null;       // lista liviana (id, titulo, tags)
  // Promesa de carga del índice (evita pedirlo dos veces).
  let bookIndexPromise = null;
  // Caché de documentos completos por id.
  const bookDocs = new Map(); // id -> documento completo
  // Último elemento con foco antes de abrir el panel.
  let lastFocus = null;

  // Carga el índice del libro (una sola vez).
  function loadIndex() {
    // Si ya hay una carga en curso o terminada, la reutiliza.
    if (bookIndexPromise) return bookIndexPromise;
    // Pide el índice al servidor.
    bookIndexPromise = fetch('/api/fundacion')
      // Interpreta la respuesta como JSON.
      .then((r) => r.json())
      // Guarda el índice y dibuja los acordeones.
      .then((data) => {
        // Acepta lista directa o data.raw (formato completo del plan MCP).
        bookIndex = Array.isArray(data) ? data : (data && Array.isArray(data.raw) ? data.raw : []);
        // Dibuja el acordeón.
        renderAccordion();
      })
      // Si falla...
      .catch(() => {
        // ...permite reintentar más tarde...
        bookIndexPromise = null;
        // ...y muestra un aviso.
        drawerLoading.innerHTML = '<p class="drawer__sub">No pude cargar el libro. Inténtalo de nuevo.</p>';
      });
    // Devuelve la promesa.
    return bookIndexPromise;
  }

  // Dibuja los acordeones del libro.
  function renderAccordion() {
    // Limpia la lista.
    acc.innerHTML = '';
    // Un acordeón por documento del índice.
    bookIndex.forEach((item) => {
      // Título corto.
      const label = shortTitle(item.titulo);
      // Subtítulo.
      const sub = subTitle(item.titulo);
      // Año detectado en el título (o "Fuente").
      const year = (label.match(/\b(1[89]\d\d|20\d\d)\b/) || [])[1] || 'Fuente';

      // Elemento de lista del acordeón.
      const li = el('li', 'acc__item');
      // Guarda el id del documento.
      li.dataset.id = item.id;
      // Cabecera y panel (todo el texto va escapado).
      li.innerHTML = `
        <button class="acc__head" type="button" aria-expanded="false">
          <span class="acc__year">${escapeHtml(year)}</span>
          <span class="acc__label"><strong>${escapeHtml(label)}</strong>${sub ? `<span>${escapeHtml(sub)}</span>` : ''}</span>
          <svg class="acc__chev" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg>
        </button>
        <div class="acc__panel" role="region"><div><div class="acc__content"></div></div></div>`;
      // Al hacer clic en la cabecera, abre/cierra el ítem.
      li.querySelector('.acc__head').addEventListener('click', () => toggleItem(li));
      // Agrega el ítem a la lista.
      acc.appendChild(li);
    });
    // Oculta el indicador de carga.
    drawerLoading.hidden = true;
    // Muestra los acordeones.
    acc.hidden = false;
  }

  // Abre o cierra un acordeón (y carga su contenido la primera vez).
  async function toggleItem(li, forceOpen) {
    // Decide si abrir (forzado o alternando).
    const open = forceOpen ?? !li.classList.contains('is-open');
    // Cierra los demás acordeones abiertos.
    acc.querySelectorAll('.acc__item.is-open').forEach((o) => {
      // Cierra solo los distintos al actual.
      if (o !== li) setItemOpen(o, false);
    });
    // Aplica el estado al ítem actual.
    setItemOpen(li, open);
    // Si se cerró, no hay nada que cargar.
    if (!open) return;

    // Contenedor del contenido.
    const content = li.querySelector('.acc__content');
    // Si ya se cargó antes, termina.
    if (content.dataset.loaded) return;
    // Muestra un esqueleto mientras carga.
    content.innerHTML = '<div class="skel-lines"><div class="skel skel--line" style="width:90%"></div><div class="skel skel--line" style="width:72%"></div><div class="skel skel--line" style="width:40%"></div></div>';

    // Protege contra errores de red.
    try {
      // Busca el documento en la caché.
      let doc = bookDocs.get(li.dataset.id);
      // Si no está en la caché...
      if (!doc) {
        // ...lo pide al servidor...
        const res = await fetch('/api/fundacion?id=' + encodeURIComponent(li.dataset.id));
        // ...interpreta la respuesta...
        const data = await res.json();
        // ...toma el primer documento...
        doc = Array.isArray(data) ? data[0] : null;
        // ...y lo guarda en la caché.
        if (doc) bookDocs.set(li.dataset.id, doc);
      }
      // Sin documento, lanza error.
      if (!doc) throw new Error('sin datos');
      // Dibuja el documento.
      content.innerHTML = renderDoc(doc);
      // Marca como cargado.
      content.dataset.loaded = '1';
      // Botón "Preguntar a VÍA" (si existe).
      content.querySelector('.ask')?.addEventListener('click', () => {
        // Título corto del documento.
        const label = shortTitle(doc.titulo);
        // Pregunta con la primera letra en minúscula.
        ask(`Explícame la ${label.charAt(0).toLowerCase() + label.slice(1)}`);
      });
    // Si falla...
    } catch (_) {
      // ...muestra un aviso.
      content.innerHTML = '<p class="acc__text">No pude cargar esta sección.</p>';
    }
  }

  // Aplica el estado abierto/cerrado a un acordeón.
  function setItemOpen(li, open) {
    // Agrega/quita la clase "is-open".
    li.classList.toggle('is-open', open);
    // Accesibilidad: indica si está expandido.
    li.querySelector('.acc__head').setAttribute('aria-expanded', String(open));
  }

  // Genera el HTML del contenido de un documento.
  function renderDoc(doc) {
    // Metadatos (o vacío).
    const meta = doc.metadata || {};
    // Datos clave a mostrar, solo los que existen.
    const facts = [
      // Fecha clave.
      ['Fecha clave', meta.fecha_clave],
      // Promotor.
      ['Impulsada por', meta.promotor],
      // Criterio.
      ['Criterio', meta.criterio]
    // Descarta los que no tienen valor.
    ].filter(([, v]) => v);

    // HTML de la lista de datos (valor escapado).
    const dl = facts.map(([k, v]) =>
      `<div class="fact"><dt>${k}</dt><dd>${escapeHtml(v)}</dd></div>`).join('');

    // Devuelve el HTML completo del documento.
    return `
      <dl class="facts">${dl}</dl>
      <p class="acc__text">${escapeHtml(doc.contenido || '')}</p>
      <button class="ask" type="button">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
        Preguntar a VÍA
      </button>`;
  }

  // Modo del panel: 'float' (tarjeta flotante) o 'dock' (pantalla dividida)
  // Detecta pantallas de móvil (≤ 820 px).
  const mqMobile = window.matchMedia('(max-width: 820px)');
  // Modo actual del panel (flotante por defecto).
  let bookMode = 'float';
  // Recupera el modo guardado; si no hay almacenamiento, deja el valor por defecto.
  try { bookMode = localStorage.getItem('via_book_mode') === 'dock' ? 'dock' : 'float'; } catch (_) { /* sin almacenamiento */ }

  // Indica si el panel del libro está abierto.
  const isOpen = () => drawer.classList.contains('is-open');

  // Aplica el modo (flotante/anclado) a la interfaz.
  function applyMode() {
    // ¿Es pantalla de móvil?
    const mobile = mqMobile.matches;
    // Anclado solo si se eligió y no es móvil.
    const docked = bookMode === 'dock' && !mobile;
    // Clase de anclado en el panel.
    drawer.classList.toggle('is-docked', docked);
    // Clase de anclado en el contenedor general.
    shell.classList.toggle('is-docked', docked);
    // En móvil se oculta el botón de modo.
    drawerMode.hidden = mobile;
    // Texto del botón según el modo.
    drawerMode.querySelector('span').textContent = docked ? 'Flotante' : 'Anclar';
    // Ícono de anclar visible solo si no está anclado.
    drawerMode.querySelector('.ico-dock').hidden = docked;
    // Ícono de flotar visible solo si está anclado.
    drawerMode.querySelector('.ico-float').hidden = !docked;
    // Ayuda del botón.
    drawerMode.title = docked ? 'Soltar como ventana flotante' : 'Anclar al costado (pantalla dividida)';
    // Accesibilidad: misma descripción.
    drawerMode.setAttribute('aria-label', drawerMode.title);
  }

  // Cambiar de modo sin animaciones intermedias raras
  // Ejecuta `fn` con las transiciones desactivadas.
  function withoutAnimation(fn) {
    // Desactiva las animaciones.
    shell.classList.add('no-anim');
    // Ejecuta el cambio.
    fn();
    // Reactiva las animaciones dos cuadros después.
    requestAnimationFrame(() => requestAnimationFrame(() => shell.classList.remove('no-anim')));
  }

  // Abre el panel del libro (y opcionalmente una sección).
  async function openDrawer(itemId) {
    // Recuerda dónde estaba el foco.
    lastFocus = document.activeElement;
    // ¿Es móvil?
    const mobile = mqMobile.matches;
    // Aplica el modo actual.
    applyMode();
    // Fondo oscuro solo en móvil.
    scrim.hidden = !mobile;               // en escritorio no bloquea el chat
    // Hace el panel interactivo.
    drawer.inert = false;
    // Accesibilidad: el panel es visible.
    drawer.setAttribute('aria-hidden', 'false');
    // Accesibilidad: el botón indica que está expandido.
    btnBook.setAttribute('aria-expanded', 'true');
    // Espera al siguiente cuadro para animar.
    requestAnimationFrame(() => {
      // Activa el fondo en móvil.
      if (mobile) scrim.classList.add('is-on');
      // Abre el panel.
      drawer.classList.add('is-open');
      // Marca el contenedor general.
      shell.classList.add('book-open');
    });
    // En móvil, lleva el foco al botón de cerrar.
    if (mobile) drawerClose.focus({ preventScroll: true });

    // Espera a que cargue el índice.
    await loadIndex();
    // Si se pidió una sección concreta...
    if (itemId) {
      // ...la busca en los acordeones...
      const li = acc.querySelector(`.acc__item[data-id="${CSS.escape(itemId)}"]`);
      // ...y si existe...
      if (li) {
        // ...la abre...
        toggleItem(li, true);
        // ...y la lleva a la vista con desplazamiento suave.
        setTimeout(() => li.scrollIntoView({ block: 'nearest', behavior: 'smooth' }), 120);
      }
    }
  }

  // Cierra el panel del libro.
  function closeDrawer() {
    // Si ya está cerrado, no hace nada.
    if (!isOpen()) return;
    // Quita la clase de abierto del panel.
    drawer.classList.remove('is-open');
    // Quita la marca del contenedor general.
    shell.classList.remove('book-open');
    // Oculta el fondo con animación.
    scrim.classList.remove('is-on');
    // Accesibilidad: el panel no es visible.
    drawer.setAttribute('aria-hidden', 'true');
    // Desactiva la interacción con el panel.
    drawer.inert = true;
    // Accesibilidad: el botón indica que está contraído.
    btnBook.setAttribute('aria-expanded', 'false');
    // Tras la animación (260 ms) oculta el fondo.
    setTimeout(() => { scrim.hidden = true; }, 260);
    // En móvil, devuelve el foco a donde estaba.
    if (mqMobile.matches && lastFocus && lastFocus.focus) lastFocus.focus({ preventScroll: true });
  }

  // Botón del libro: abre o cierra el panel.
  btnBook.addEventListener('click', () => (isOpen() ? closeDrawer() : openDrawer()));
  // Botón X: cierra el panel.
  drawerClose.addEventListener('click', closeDrawer);
  // Clic en el fondo: cierra el panel.
  scrim.addEventListener('click', closeDrawer);

  // Botón anclar/soltar.
  drawerMode.addEventListener('click', () => {
    // Alterna el modo.
    bookMode = bookMode === 'dock' ? 'float' : 'dock';
    // Guarda la elección (si hay almacenamiento).
    try { localStorage.setItem('via_book_mode', bookMode); } catch (_) { /* opcional */ }
    // Aplica el modo sin animaciones intermedias.
    withoutAnimation(applyMode);
  });

  // Cuando cambia entre móvil y escritorio...
  mqMobile.addEventListener('change', () => {
    // ...reajusta sin animaciones.
    withoutAnimation(() => {
      // Reaplica el modo.
      applyMode();
      // Si el panel está abierto...
      if (isOpen()) {
        // ...ajusta el fondo oscuro según el tamaño de pantalla.
        scrim.hidden = !mqMobile.matches;
        // Activa/desactiva el fondo según corresponda.
        scrim.classList.toggle('is-on', mqMobile.matches);
      }
    });
  });

  // Escape cierra el panel solo si el foco está dentro de él (o en móvil)
  document.addEventListener('keydown', (e) => {
    // Cierra con Escape cuando corresponde.
    if (e.key === 'Escape' && isOpen() && (mqMobile.matches || drawer.contains(document.activeElement))) closeDrawer();
  });

  // ---------------------------------------------------------------------------
  // Logo: el engranaje gira al pasar el cursor y frena suavemente en su posición
  // original (el tren del centro permanece quieto).
  // [SRP] Animación aislada en su propia función autoejecutable.
  // ---------------------------------------------------------------------------
  // Función autoejecutable del logo.
  (function logoSpin() {
    // Capa del engranaje que gira.
    const spin = document.querySelector('.brand .via-mark__spin');
    // Sin logo o con "reducir movimiento" activado, no anima.
    if (!spin || !brand || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    // Velocidad máxima de giro.
    const MAX_SPEED = 320;            // grados por segundo
    // Estado de la animación.
    let angle = 0, velocity = 0, target = null, hovering = false, raf = 0, last = 0;

    // Cuadro de animación.
    function tick(now) {
      // Tiempo desde el cuadro anterior (máx. 40 ms).
      const dt = Math.min(0.04, (now - last) / 1000);
      // Guarda el instante actual.
      last = now;

      // Mientras el cursor está encima...
      if (hovering) {
        // ...acelera hacia la velocidad máxima...
        velocity += (MAX_SPEED - velocity) * Math.min(1, dt * 4);   // acelera
        // ...y avanza el ángulo.
        angle += velocity * dt;
      // Cuando el cursor sale...
      } else {
        // frena como un resorte amortiguado hasta la siguiente vuelta completa
        // Calcula el ángulo objetivo (próxima vuelta completa).
        if (target === null) target = Math.ceil((angle + 60) / 360) * 360;
        // Aplica fuerza de resorte con amortiguación.
        velocity += (30 * (target - angle) - 11 * velocity) * dt;
        // Avanza el ángulo.
        angle += velocity * dt;
        // Si llegó al objetivo y casi no se mueve...
        if (Math.abs(target - angle) < 0.2 && Math.abs(velocity) < 2) {
          // ...reinicia el estado...
          angle = 0; velocity = 0; target = null; raf = 0;
          // ...quita la rotación...
          spin.style.transform = '';
          // ...y detiene la animación.
          return;
        }
      }
      // Aplica la rotación actual.
      spin.style.transform = `rotate(${angle}deg)`;
      // Pide el siguiente cuadro.
      raf = requestAnimationFrame(tick);
    }

    // Inicia el giro.
    const start = () => {
      // Marca que el cursor está encima y cancela el frenado.
      hovering = true; target = null;
      // Si no hay animación en curso, la inicia.
      if (!raf) { last = performance.now(); raf = requestAnimationFrame(tick); }
    };
    // Inicia el frenado.
    const stop = () => { hovering = false; };

    // Cursor entra: gira.
    brand.addEventListener('pointerenter', start);
    // Cursor sale: frena.
    brand.addEventListener('pointerleave', stop);
    // Foco por teclado: gira.
    brand.addEventListener('focus', start);
    // Pérdida de foco: frena.
    brand.addEventListener('blur', stop);
  })();

  // ---------------------------------------------------------------------------
  // Arranque
  // ---------------------------------------------------------------------------
  // Ajusta la caja de entrada inicial.
  syncInput();
  // Aplica el modo del libro.
  applyMode();
  // Carga la bienvenida.
  loadWelcome();

  // Calentamiento silencioso del backend y del índice del libro (sin UI)
  // Despierta el backend (el error se ignora).
  fetch('/api/status').catch(() => {});
  // Cuando el navegador está libre (o a los 1,2 s), precarga el índice del libro.
  (window.requestIdleCallback || ((f) => setTimeout(f, 1200)))(() => loadIndex());
})();
