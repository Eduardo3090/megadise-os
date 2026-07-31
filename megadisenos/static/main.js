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
  if (!email) {
    alert('Por favor ingresa tu correo.');
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
    mensaje.style.display = 'block';
    document.getElementById('inputCorreo').value = '';
    document.getElementById('checkPrivacidad').checked = false;
  })
  .catch(err => {
    console.error(err);
    alert('Hubo un problema al enviar. Intenta de nuevo.');
  });
}
