// ─── REVEAL ON SCROLL ───────────────────────────────
const revealObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('visible');
      revealObserver.unobserve(entry.target);
    }
  });
}, { threshold: 0.15 });
document.querySelectorAll('.reveal').forEach(el => revealObserver.observe(el));

// ─── NAVBAR SCROLL ──────────────────────────────────
const mainNav = document.getElementById('mainNav');
window.addEventListener('scroll', () => {
  if (window.scrollY > 40) {
    mainNav.classList.add('scrolled');
  } else {
    mainNav.classList.remove('scrolled');
  }
});

// ─── HAMBURGUESA (menú móvil) ───────────────────────
const hamburger = document.getElementById('hamburger');
const navLinks = document.getElementById('navLinks');
hamburger.addEventListener('click', () => {
  navLinks.classList.toggle('open');
});

// ─── ENVIAR CORREO (modal captura) ──────────────────
function enviarCorreo() {
  const email = document.getElementById('inputCorreo').value.trim();
  const acepta = document.getElementById('checkPrivacidad').checked;
  const mensaje = document.getElementById('mensajeModal');
  const emailRegex = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

  if (!email) {
    alert('Por favor ingresa tu correo.');
    return;
  }
  if (!emailRegex.test(email)) {
    alert('Por favor ingresa un correo válido.');
    return;
  }
  if (!acepta) {
    alert('Debes aceptar la Política de Privacidad para continuar.');
    return;
  }
  fetch('/suscribir', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: email, consentimiento: acepta })
  })
  .then(res => res.json())
  .then(data => {
    if (data.exito) {
      mensaje.textContent = '✅ ¡Listo! Revisa tu correo pronto.';
      mensaje.style.color = '#2a8f4d';
      mensaje.style.display = 'block';
      document.getElementById('inputCorreo').value = '';
      document.getElementById('checkPrivacidad').checked = false;
    } else {
      mensaje.textContent = '⚠️ ' + (data.mensaje || 'No se pudo procesar tu solicitud.');
      mensaje.style.color = '#c0392b';
      mensaje.style.display = 'block';
    }
  })
  .catch(err => {
    console.error(err);
    alert('Hubo un problema al enviar. Intenta de nuevo.');
  });
}

// ─── COPIAR DATOS DE PAGO ────────────────────────────
function copiarDato(id, btn) {
  const texto = document.getElementById(id).textContent.trim();
  const original = btn.textContent;
  navigator.clipboard.writeText(texto).then(() => {
    btn.textContent = '¡Copiado!';
    setTimeout(() => { btn.textContent = original; }, 1500);
  }).catch(() => {
    alert('No se pudo copiar automáticamente. Este es el dato: ' + texto);
  });
}


// ─── FORMULARIO DE CONTACTO ──────────────────────────
function enviarContacto() {
  const nombre = document.getElementById('nombre').value.trim();
  const telefono = document.getElementById('telefono').value.trim();
  const email = document.getElementById('email').value.trim();
  const mensaje = document.getElementById('mensaje').value.trim();
  const honeypot = document.getElementById('empresa_web').value.trim();
  const feedback = document.getElementById('mensajeContacto');
  const emailRegex = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

  if (!nombre || !email || !mensaje) {
    alert('Por favor completa nombre, correo y mensaje.');
    return;
  }
  if (!emailRegex.test(email)) {
    alert('Por favor ingresa un correo válido.');
    return;
  }

  fetch('/contactanos', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ nombre, telefono, email, mensaje, empresa_web: honeypot })
  })
  .then(res => res.json())
  .then(data => {
    if (data.exito) {
      feedback.textContent = '✅ ¡Mensaje enviado! Te contactaremos dentro de 24 horas.';
      feedback.style.color = '#2a8f4d';
      feedback.style.display = 'block';
      document.getElementById('nombre').value = '';
      document.getElementById('telefono').value = '';
      document.getElementById('email').value = '';
      document.getElementById('mensaje').value = '';
    } else {
      feedback.textContent = '⚠️ ' + (data.mensaje || 'No se pudo enviar. Intenta de nuevo o escríbenos por WhatsApp.');
      feedback.style.color = '#c0392b';
      feedback.style.display = 'block';
    }
  })
  .catch(err => {
    console.error(err);
    feedback.textContent = '⚠️ Hubo un problema de conexión. Intenta de nuevo o escríbenos por WhatsApp.';
    feedback.style.color = '#c0392b';
    feedback.style.display = 'block';
  });
}
