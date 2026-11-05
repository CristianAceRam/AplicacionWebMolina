// Inicializa el tema (claro/oscuro) ANTES de pintar la página, para evitar el
// parpadeo. Es un fichero externo (no un <script> inline) para cumplir la CSP
// script-src 'self'. Debe mantenerse en sintonía con src/context/ThemeContext.jsx.
(function () {
  try {
    var saved = localStorage.getItem('tema');
    var dark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    document.documentElement.setAttribute(
      'data-theme',
      saved || (dark ? 'dark' : 'light')
    );
  } catch {
    // Sin localStorage/matchMedia: ThemeContext aplica el tema al montar React.
  }
})();
