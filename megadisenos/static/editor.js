/* ─────────────────────────────────────────────────────────
   editor.js — Editor visual de Megadiseños
   Solo se carga en /admin/editor. Convierte la página de inicio
   real en editable: textos, imágenes, enlaces, estrellas y el
   orden/visibilidad de las secciones. Todo se guarda solo como
   BORRADOR; el sitio público cambia únicamente al Publicar.
   ───────────────────────────────────────────────────────── */
(function () {
  'use strict';

  const CFG = window.ED_CONFIG;
  if (!CFG) return;

  const MAX_MB = 8;
  const PREFIJOS_LINK = ['/', '#', 'https://', 'http://', 'mailto:', 'tel:'];

  // Estado: una copia de cada sección (id, tipo, orden, visible, datos)
  const estado = {};
  CFG.estado.forEach(s => { estado[s.id] = s; });

  const $estado = document.getElementById('edEstado');
  let hayBorrador = $estado.dataset.borrador === '1';

  // ── Utilidades ─────────────────────────────────────────
  function obtenerRuta(obj, ruta) {
    return ruta.split('.').reduce((o, k) => (o == null ? o : o[k]), obj);
  }
  function fijarRuta(obj, ruta, valor) {
    const partes = ruta.split('.');
    const ultimo = partes.pop();
    const destino = partes.reduce((o, k) => (o == null ? o : o[k]), obj);
    if (destino != null) destino[ultimo] = valor;
  }
  function seccionDe(el) {
    return estado[el.dataset.sec] || estado[(el.closest('[data-sec]') || {}).dataset?.sec];
  }

  let toastTimer = null;
  const $toast = document.createElement('div');
  $toast.className = 'ed-ui ed-toast';
  document.body.appendChild($toast);
  function avisar(texto, tipo) {
    $toast.textContent = texto;
    $toast.className = 'ed-ui ed-toast ed-toast-visible' + (tipo ? ' ed-toast-' + tipo : '');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { $toast.classList.remove('ed-toast-visible'); }, 3500);
  }
  document.querySelectorAll('.ed-toast[data-auto]').forEach(t => {
    setTimeout(() => t.classList.remove('ed-toast-visible'), 4000);
  });

  function pintarEstado(texto, clase) {
    $estado.textContent = texto;
    $estado.className = 'ed-estado' + (clase ? ' ' + clase : '');
  }
  function pintarEstadoNormal() {
    if (hayBorrador) pintarEstado('● Cambios sin publicar', 'ed-pendiente');
    else pintarEstado('✓ Todo publicado');
  }
  pintarEstadoNormal();

  async function llamar(url, opciones) {
    const res = await fetch(url, Object.assign({
      credentials: 'same-origin',
      headers: { 'X-CSRF-Token': CFG.csrf }
    }, opciones || {}));
    const tipo = res.headers.get('content-type') || '';
    if (res.redirected || !tipo.includes('application/json')) {
      throw new Error('sesion');
    }
    const data = await res.json();
    if (!res.ok || data.ok === false) {
      const err = new Error(data.mensaje || 'error');
      err.mensaje = data.mensaje;
      throw err;
    }
    return data;
  }

  function mensajeError(err) {
    if (err.message === 'sesion') return 'Tu sesión expiró. Vuelve a iniciar sesión (tus cambios ya guardados no se pierden).';
    return err.mensaje || 'No se pudo conectar. Revisa tu internet e intenta de nuevo.';
  }

  // ── Guardado automático del borrador ──────────────────
  let timerGuardar = null;
  let guardando = null;
  let pendiente = false;

  function ordenActual() {
    document.querySelectorAll('.ed-seccion').forEach((el, i) => {
      const s = estado[el.dataset.sec];
      if (s) s.orden = i + 1;
    });
  }

  function programarGuardado() {
    pendiente = true;
    pintarEstado('Guardando…', 'ed-pendiente');
    clearTimeout(timerGuardar);
    timerGuardar = setTimeout(guardarAhora, 700);
  }

  async function guardarAhora() {
    clearTimeout(timerGuardar);
    if (guardando) await guardando.catch(() => {});
    if (!pendiente) return;
    pendiente = false;
    ordenActual();
    const cuerpo = JSON.stringify({ secciones: Object.values(estado) });
    guardando = llamar(CFG.urls.guardar, {
      method: 'POST',
      headers: { 'X-CSRF-Token': CFG.csrf, 'Content-Type': 'application/json' },
      body: cuerpo
    }).then(data => {
      hayBorrador = !!data.hay_borrador;
      if (!pendiente) pintarEstadoNormal();
    }).catch(err => {
      pendiente = true;
      pintarEstado('⚠ No se pudo guardar', 'ed-error');
      avisar(mensajeError(err), 'error');
      throw err;
    }).finally(() => { guardando = null; });
    return guardando;
  }

  window.addEventListener('beforeunload', e => {
    if (pendiente || guardando) { e.preventDefault(); e.returnValue = ''; }
  });

  // ── Textos ────────────────────────────────────────────
  document.querySelectorAll('.ed-texto').forEach(el => {
    el.addEventListener('input', () => {
      const s = seccionDe(el);
      if (!s) return;
      fijarRuta(s.datos, el.dataset.ruta, el.textContent);
      programarGuardado();
    });
    el.addEventListener('blur', () => {
      const limpio = el.textContent.replace(/\s+/g, ' ').trim();
      if (limpio !== el.textContent) {
        el.textContent = limpio;
        const s = seccionDe(el);
        if (s) { fijarRuta(s.datos, el.dataset.ruta, limpio); programarGuardado(); }
      }
    });
    el.addEventListener('keydown', e => {
      if (e.key === 'Enter' || e.key === 'Escape') { e.preventDefault(); el.blur(); }
    });
    // Pegar siempre como texto plano (sin formatos de Word, colores, etc.)
    el.addEventListener('paste', e => {
      e.preventDefault();
      const texto = (e.clipboardData || window.clipboardData).getData('text/plain').replace(/\s+/g, ' ');
      document.execCommand('insertText', false, texto);
    });
    el.addEventListener('drop', e => e.preventDefault());
  });

  // ── Estrellas de las reseñas ──────────────────────────
  function marcarEstrellas(bloque, n) {
    bloque.querySelectorAll('i[data-n]').forEach(i => {
      i.classList.toggle('ed-estrella-off', Number(i.dataset.n) > n);
    });
  }

  // ── Imágenes ──────────────────────────────────────────
  const $archivo = document.createElement('input');
  $archivo.type = 'file';
  $archivo.accept = 'image/jpeg,image/png,image/webp';
  $archivo.style.display = 'none';
  document.body.appendChild($archivo);
  let pictureActual = null;

  function elegirImagen(picture) {
    pictureActual = picture;
    $archivo.value = '';
    $archivo.click();
  }

  $archivo.addEventListener('change', async () => {
    const archivo = $archivo.files[0];
    const picture = pictureActual;
    if (!archivo || !picture) return;
    if (archivo.size > MAX_MB * 1024 * 1024) {
      avisar('La imagen pesa más de ' + MAX_MB + ' MB. Usa una más liviana.', 'error');
      return;
    }
    const s = seccionDe(picture);
    const ruta = picture.dataset.edImg;
    const form = new FormData();
    form.append('imagen', archivo);
    form.append('nombre', (s ? s.tipo : 'seccion') + '-' + ruta.replace(/\./g, '-'));

    picture.classList.add('ed-subiendo');
    avisar('Subiendo imagen…');
    try {
      const data = await llamar(CFG.urls.imagen, { method: 'POST', body: form });
      picture.querySelectorAll('source').forEach(src => { src.srcset = data.webp; });
      const img = picture.querySelector('img');
      if (img) img.src = data.jpg;
      if (s) { fijarRuta(s.datos, ruta, data.base); programarGuardado(); }
      avisar('Imagen cambiada ✓', 'exito');
    } catch (err) {
      avisar(mensajeError(err), 'error');
    } finally {
      picture.classList.remove('ed-subiendo');
    }
  });

  // ── Enlaces de botones ────────────────────────────────
  const $pop = document.createElement('div');
  $pop.className = 'ed-ui ed-pop';
  $pop.innerHTML =
    '<label for="edPopInput">¿A dónde lleva este botón?</label>' +
    '<input id="edPopInput" type="text" autocomplete="off" spellcheck="false">' +
    '<small>Ejemplos: <b>/contactanos</b>, <b>/servicios</b>, <b>https://wa.me/569…</b></small>' +
    '<div class="ed-pop-acciones">' +
    '<button type="button" class="ed-btn ed-btn-sec" data-accion="cancelar">Cancelar</button>' +
    '<button type="button" class="ed-btn ed-btn-pri" data-accion="guardar">Guardar enlace</button>' +
    '</div>';
  document.body.appendChild($pop);
  const $popInput = $pop.querySelector('input');
  const $popAyuda = $pop.querySelector('small');
  const ayudaOriginal = $popAyuda.innerHTML;
  let linkActual = null;

  function normalizarLink(v) {
    v = v.trim();
    if (/^(www\.|wa\.me\/)/i.test(v)) v = 'https://' + v;
    return v;
  }

  function abrirLink(el) {
    linkActual = el;
    const s = seccionDe(el);
    $popInput.value = s ? (obtenerRuta(s.datos, el.dataset.edLink) || '') : el.getAttribute('href');
    $popAyuda.innerHTML = ayudaOriginal;
    $popAyuda.classList.remove('ed-pop-error');
    const r = el.getBoundingClientRect();
    $pop.classList.add('ed-visible');
    const ancho = $pop.offsetWidth;
    $pop.style.left = Math.max(16, Math.min(r.left, window.innerWidth - ancho - 16)) + 'px';
    const abajo = r.bottom + 10;
    $pop.style.top = (abajo + $pop.offsetHeight > window.innerHeight ? Math.max(70, r.top - $pop.offsetHeight - 10) : abajo) + 'px';
    ocultarChip();
    $popInput.focus();
    $popInput.select();
  }
  function cerrarLink() { $pop.classList.remove('ed-visible'); linkActual = null; }

  function guardarLink() {
    if (!linkActual) return;
    const valor = normalizarLink($popInput.value);
    if (!PREFIJOS_LINK.some(p => valor.toLowerCase().startsWith(p))) {
      $popAyuda.textContent = 'El enlace debe empezar con / (página del sitio) o con https://';
      $popAyuda.classList.add('ed-pop-error');
      $popInput.focus();
      return;
    }
    const s = seccionDe(linkActual);
    linkActual.setAttribute('href', valor);
    if (s) { fijarRuta(s.datos, linkActual.dataset.edLink, valor); programarGuardado(); }
    cerrarLink();
    avisar('Enlace actualizado ✓', 'exito');
  }

  $pop.addEventListener('click', e => {
    const b = e.target.closest('[data-accion]');
    if (!b) return;
    if (b.dataset.accion === 'guardar') guardarLink(); else cerrarLink();
  });
  $popInput.addEventListener('keydown', e => {
    if (e.key === 'Enter') { e.preventDefault(); guardarLink(); }
    if (e.key === 'Escape') cerrarLink();
  });
  document.addEventListener('mousedown', e => {
    if ($pop.classList.contains('ed-visible') && !e.target.closest('.ed-pop')) cerrarLink();
  });

  // ── Chip flotante "Cambiar imagen" / "Cambiar enlace" ─
  const $chip = document.createElement('button');
  $chip.type = 'button';
  $chip.className = 'ed-ui ed-chip';
  document.body.appendChild($chip);
  let chipDe = null;
  let timerChip = null;

  function mostrarChip(el) {
    clearTimeout(timerChip);
    chipDe = el;
    const esImagen = el.hasAttribute('data-ed-img');
    $chip.innerHTML = esImagen
      ? '<i class="fa-solid fa-image"></i> Cambiar imagen'
      : '<i class="fa-solid fa-link"></i> Cambiar enlace';
    const r = el.getBoundingClientRect();
    $chip.classList.add('ed-visible');
    const w = $chip.offsetWidth;
    if (esImagen) {
      $chip.style.left = (r.left + r.width / 2 - w / 2) + 'px';
      $chip.style.top = (r.top + r.height / 2 - 16) + 'px';
    } else {
      $chip.style.left = Math.min(r.right - w, window.innerWidth - w - 8) + 'px';
      $chip.style.top = Math.max(60, r.top - 36) + 'px';
    }
  }
  function ocultarChip() { $chip.classList.remove('ed-visible'); chipDe = null; }
  function ocultarChipLuego() { clearTimeout(timerChip); timerChip = setTimeout(ocultarChip, 350); }

  document.addEventListener('mouseover', e => {
    if (e.target.closest('.ed-chip')) { clearTimeout(timerChip); return; }
    const el = e.target.closest('[data-ed-img], [data-ed-link]');
    if (el) mostrarChip(el);
    else if (chipDe) ocultarChipLuego();
  });
  document.addEventListener('focusin', e => {
    const el = e.target.closest('[data-ed-link]');
    if (el) mostrarChip(el);
  });
  // Al hacer scroll, el botón flotante sigue al elemento (o se esconde si salió de pantalla)
  window.addEventListener('scroll', () => {
    if (!chipDe) return;
    const r = chipDe.getBoundingClientRect();
    if (r.bottom < 60 || r.top > window.innerHeight) ocultarChip();
    else mostrarChip(chipDe);
  }, { passive: true });
  $chip.addEventListener('click', e => {
    e.preventDefault();
    e.stopPropagation();
    const el = chipDe;
    if (!el) return;
    if (el.hasAttribute('data-ed-img')) { ocultarChip(); elegirImagen(el); }
    else abrirLink(el);
  });

  // ── Bloquear la navegación normal del sitio ───────────
  // En el editor, hacer clic en un botón o enlace NO debe salir de la página.
  document.addEventListener('click', e => {
    if (e.target.closest('.ed-ui, .ed-seccion-fija')) return;

    const estrella = e.target.closest('[data-ed-estrellas] i[data-n]');
    if (estrella) {
      e.preventDefault(); e.stopPropagation();
      const bloque = estrella.closest('[data-ed-estrellas]');
      const n = Number(estrella.dataset.n);
      marcarEstrellas(bloque, n);
      const s = seccionDe(bloque);
      if (s) { fijarRuta(s.datos, bloque.dataset.edEstrellas, n); programarGuardado(); }
      return;
    }

    const picture = e.target.closest('[data-ed-img]');
    if (picture) { e.preventDefault(); e.stopPropagation(); elegirImagen(picture); return; }

    if (e.target.closest('a, button, [onclick]')) {
      e.preventDefault();
      e.stopPropagation();
      const link = e.target.closest('[data-ed-link]');
      if (link && !e.target.closest('.ed-texto')) abrirLink(link);
    }
  }, true);
  document.addEventListener('submit', e => {
    if (!e.target.closest('.ed-ui')) e.preventDefault();
  }, true);

  // ── Secciones: mover y ocultar ────────────────────────
  function actualizarBotonesOrden() {
    const todas = Array.from(document.querySelectorAll('.ed-seccion'));
    todas.forEach((el, i) => {
      el.querySelector('[data-accion="subir"]').disabled = i === 0;
      el.querySelector('[data-accion="bajar"]').disabled = i === todas.length - 1;
    });
  }

  document.querySelectorAll('.ed-seccion').forEach(el => {
    const fija = document.createElement('div');
    fija.className = 'ed-seccion-fija';
    const barra = document.createElement('div');
    barra.className = 'ed-seccion-barra';
    fija.appendChild(barra);
    barra.innerHTML =
      '<span class="ed-seccion-nombre"></span>' +
      '<button type="button" data-accion="subir" title="Subir sección"><i class="fa-solid fa-arrow-up"></i></button>' +
      '<button type="button" data-accion="bajar" title="Bajar sección"><i class="fa-solid fa-arrow-down"></i></button>' +
      '<button type="button" data-accion="ocultar"></button>' +
      '<span class="ed-seccion-aviso">Oculta — no se verá en el sitio</span>';
    barra.querySelector('.ed-seccion-nombre').textContent = el.dataset.nombre || 'Sección';
    el.prepend(fija);
    pintarBotonOcultar(el);

    barra.addEventListener('click', e => {
      const b = e.target.closest('button[data-accion]');
      if (!b || b.disabled) return;
      const s = estado[el.dataset.sec];
      if (b.dataset.accion === 'subir' && el.previousElementSibling?.classList.contains('ed-seccion')) {
        el.parentNode.insertBefore(el, el.previousElementSibling);
      } else if (b.dataset.accion === 'bajar' && el.nextElementSibling?.classList.contains('ed-seccion')) {
        el.parentNode.insertBefore(el.nextElementSibling, el);
      } else if (b.dataset.accion === 'ocultar' && s) {
        s.visible = !s.visible;
        el.classList.toggle('ed-oculta', !s.visible);
        pintarBotonOcultar(el);
        avisar(s.visible ? 'La sección volverá a verse al publicar' : 'La sección se ocultará al publicar');
      }
      actualizarBotonesOrden();
      if (b.dataset.accion !== 'ocultar') el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      programarGuardado();
    });
  });
  actualizarBotonesOrden();

  function pintarBotonOcultar(el) {
    const s = estado[el.dataset.sec];
    const b = el.querySelector('[data-accion="ocultar"]');
    b.innerHTML = s && s.visible
      ? '<i class="fa-solid fa-eye-slash"></i> Ocultar'
      : '<i class="fa-solid fa-eye"></i> Mostrar';
  }

  // Las animaciones de entrada del sitio no deben esconder contenido mientras se edita
  document.querySelectorAll('.reveal').forEach(el => el.classList.add('visible'));

  // ── Barra superior: vista previa, publicar, descartar ─
  document.getElementById('edPrevia').addEventListener('click', async () => {
    const ventana = window.open('about:blank', '_blank');
    try {
      await guardarAhora();
      if (ventana) ventana.location = CFG.urls.previa;
      else window.location = CFG.urls.previa;
    } catch (err) {
      if (ventana) ventana.close();
    }
  });

  document.getElementById('edPublicar').addEventListener('click', async () => {
    try { await guardarAhora(); } catch (err) { return; }
    if (!hayBorrador) { avisar('No hay cambios nuevos para publicar.'); return; }
    if (!confirm('¿Publicar los cambios? Se verán de inmediato en el sitio.')) return;
    const boton = document.getElementById('edPublicar');
    boton.disabled = true;
    try {
      await llamar(CFG.urls.publicar, { method: 'POST', headers: { 'X-CSRF-Token': CFG.csrf, 'Content-Type': 'application/json' }, body: '{}' });
      hayBorrador = false;
      pintarEstadoNormal();
      avisar('¡Cambios publicados! Ya se ven en el sitio.', 'exito');
    } catch (err) {
      avisar(mensajeError(err), 'error');
    } finally {
      boton.disabled = false;
    }
  });

  document.getElementById('edDescartar').addEventListener('click', async () => {
    if (!hayBorrador && !pendiente) { avisar('No hay cambios sin publicar.'); return; }
    if (!confirm('¿Descartar todos los cambios sin publicar? La página volverá a como está en el sitio.')) return;
    clearTimeout(timerGuardar);
    pendiente = false;
    if (guardando) await guardando.catch(() => {});
    try {
      await llamar(CFG.urls.descartar, { method: 'POST', headers: { 'X-CSRF-Token': CFG.csrf, 'Content-Type': 'application/json' }, body: '{}' });
      window.location.reload();
    } catch (err) {
      avisar(mensajeError(err), 'error');
    }
  });

  // ── Ayuda ─────────────────────────────────────────────
  // Se muestra la primera vez y se cierra sola al empezar a editar,
  // para no tapar la página. El botón "?" de la barra la vuelve a abrir.
  const $ayuda = document.getElementById('edAyuda');
  function cerrarAyuda() {
    $ayuda.classList.add('ed-cerrada');
    try { localStorage.setItem('edAyudaCerrada', '1'); } catch (e) {}
  }
  try { if (localStorage.getItem('edAyudaCerrada') === '1') $ayuda.classList.add('ed-cerrada'); } catch (e) {}
  document.getElementById('edAyudaCerrar').addEventListener('click', cerrarAyuda);
  document.getElementById('edAyudaAbrir').addEventListener('click', e => {
    e.stopPropagation();
    $ayuda.classList.toggle('ed-cerrada');
  });
  document.addEventListener('mousedown', e => {
    if (!$ayuda.classList.contains('ed-cerrada') && !e.target.closest('.ed-ayuda, #edAyudaAbrir')) cerrarAyuda();
  }, true);
})();
