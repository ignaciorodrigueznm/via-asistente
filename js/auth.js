/**
 * VÍA · Módulo de Autenticación, Perfil y Personalización de AI
 * Gestiona el ciclo de vida de usuarios, tokens JWT, persistencia y estado visual.
 */
(() => {
  'use strict';

  const TOKEN_KEY = 'via_auth_token';

  // ---------------------------------------------------------------------------
  // Referencias a Elementos del DOM
  // ---------------------------------------------------------------------------
  const $ = (id) => document.getElementById(id);

  // Gateway (Pantalla de bienvenida y bloqueo)
  const authGateway = $('auth-gateway');
  const tabLogin = $('tab-login');
  const tabRegister = $('tab-register');
  const formLogin = $('form-login');
  const formRegister = $('form-register');
  const authAlert = $('auth-alert');
  const linkGoRegister = $('link-go-register');
  const linkGoLogin = $('link-go-login');
  const btnSubmitLogin = $('btn-submit-login');
  const btnSubmitRegister = $('btn-submit-register');

  // Topbar y Dropdown
  const userMenuWrapper = $('user-menu-wrapper');
  const btnUserProfile = $('btn-user-profile');
  const userDropdown = $('user-dropdown');
  const topbarAvatar = $('topbar-avatar');
  const topbarUsername = $('topbar-username');
  const dropdownFullName = $('dropdown-full-name');
  const dropdownUsername = $('dropdown-username');
  const dropdownBtnProfile = $('dropdown-btn-profile');
  const dropdownBtnAI = $('dropdown-btn-ai');
  const dropdownBtnLogout = $('dropdown-btn-logout');

  // Modal de Perfil & AI
  const profileModalScrim = $('profile-modal-scrim');
  const profileModal = $('profile-modal');
  const modalProfileClose = $('modal-profile-close');
  const modalTabPerfil = $('modal-tab-perfil');
  const modalTabAI = $('modal-tab-ai');
  const modalAlert = $('modal-alert');
  const modalContentPerfil = $('modal-content-perfil');
  const modalContentAI = $('modal-content-ai');

  // Formulario de Perfil
  const formUpdateProfile = $('form-update-profile');
  const profilePhotoInput = $('profile-photo-input');
  const profileAvatarPreview = $('profile-avatar-preview');
  const profileAvatarFallback = $('profile-avatar-fallback');
  const btnRemovePhoto = $('btn-remove-photo');
  const profileInputNombre = $('profile-input-nombre');
  const profileInputUsername = $('profile-input-username');
  const profileInputEmail = $('profile-input-email');

  // Formulario de IA
  const formUpdateAI = $('form-update-ai');
  const aiToneSelect = $('ai-tone-select');
  const aiPreferredName = $('ai-preferred-name');
  const aiCustomDirectives = $('ai-custom-directives');

  // Estado del usuario activo
  let currentUser = null;
  let stagedPhotoBase64 = null;

  // ---------------------------------------------------------------------------
  // Utilidades de Tokens y Red
  // ---------------------------------------------------------------------------
  function getToken() {
    return localStorage.getItem(TOKEN_KEY) || '';
  }

  function setToken(token) {
    if (token) {
      localStorage.setItem(TOKEN_KEY, token);
    } else {
      localStorage.removeItem(TOKEN_KEY);
    }
  }

  function clearToken() {
    localStorage.removeItem(TOKEN_KEY);
    currentUser = null;
  }

  async function authFetch(url, options = {}) {
    const headers = options.headers || {};
    const token = getToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    const response = await fetch(url, { ...options, headers });
    if (response.status === 401) {
      // Token expirado o inválido
      handleAuthExpired();
    }
    return response;
  }

  // ---------------------------------------------------------------------------
  // Manejo de Interfaz (Alertas y Spinners)
  // ---------------------------------------------------------------------------
  function showAlert(container, msg, type = 'error') {
    if (!container) return;
    container.textContent = msg;
    container.className = `auth-alert auth-alert--${type}`;
    container.hidden = false;
  }

  function hideAlert(container) {
    if (!container) return;
    container.hidden = true;
    container.textContent = '';
  }

  function setButtonLoading(btn, loading, defaultText) {
    if (!btn) return;
    const txt = btn.querySelector('.btn-text');
    const spinner = btn.querySelector('.btn-spinner');
    btn.disabled = loading;
    if (loading) {
      if (txt) txt.textContent = 'Procesando...';
      if (spinner) spinner.hidden = false;
    } else {
      if (txt) txt.textContent = defaultText;
      if (spinner) spinner.hidden = true;
    }
  }

  // ---------------------------------------------------------------------------
  // Pestañas del Gateway (Login / Registro)
  // ---------------------------------------------------------------------------
  function switchAuthTab(tab) {
    hideAlert(authAlert);
    const esLogin = tab === 'login';
    if (tabLogin) {
      tabLogin.classList.toggle('is-active', esLogin);
      tabLogin.setAttribute('aria-selected', String(esLogin));
    }
    if (tabRegister) {
      tabRegister.classList.toggle('is-active', !esLogin);
      tabRegister.setAttribute('aria-selected', String(!esLogin));
    }
    if (formLogin) formLogin.hidden = !esLogin;
    if (formRegister) formRegister.hidden = esLogin;
  }

  if (tabLogin) tabLogin.addEventListener('click', () => switchAuthTab('login'));
  if (tabRegister) tabRegister.addEventListener('click', () => switchAuthTab('register'));
  if (linkGoRegister) linkGoRegister.addEventListener('click', (e) => { e.preventDefault(); switchAuthTab('register'); });
  if (linkGoLogin) linkGoLogin.addEventListener('click', (e) => { e.preventDefault(); switchAuthTab('login'); });

  // Botones para alternar visibilidad de contraseña
  document.querySelectorAll('.btn-toggle-pw').forEach((btn) => {
    btn.addEventListener('click', () => {
      const input = btn.previousElementSibling;
      if (input && input.tagName === 'INPUT') {
        const isPw = input.type === 'password';
        input.type = isPw ? 'text' : 'password';
        btn.textContent = isPw ? 'Ocultar' : 'Ver';
        btn.setAttribute('aria-label', isPw ? 'Ocultar contraseña' : 'Mostrar contraseña');
      }
    });
  });

  // ---------------------------------------------------------------------------
  // Actualización de la Interfaz con los Datos del Usuario
  // ---------------------------------------------------------------------------
  function renderUserUI(user) {
    if (!user) {
      if (userMenuWrapper) userMenuWrapper.hidden = true;
      return;
    }

    if (userMenuWrapper) userMenuWrapper.hidden = false;

    // Nombre para mostrar
    const displayName = user.nombre || user.username;
    if (topbarUsername) topbarUsername.textContent = displayName;
    if (dropdownFullName) dropdownFullName.textContent = displayName;
    if (dropdownUsername) dropdownUsername.textContent = `@${user.username}`;

    // Avatar
    renderAvatar(user.foto_perfil, displayName);
  }

  function renderAvatar(photoUrlOrBase64, name) {
    const initial = (name || 'U').charAt(0).toUpperCase();

    // Topbar avatar
    if (topbarAvatar) {
      topbarAvatar.textContent = '';
      if (photoUrlOrBase64) {
        const img = document.createElement('img');
        img.src = photoUrlOrBase64;
        img.alt = name || '';
        topbarAvatar.appendChild(img);
      } else {
        topbarAvatar.textContent = initial;
      }
    }

    // Modal avatar
    if (profileAvatarPreview && profileAvatarFallback) {
      if (photoUrlOrBase64) {
        profileAvatarPreview.src = photoUrlOrBase64;
        profileAvatarPreview.hidden = false;
        profileAvatarFallback.hidden = true;
        if (btnRemovePhoto) btnRemovePhoto.hidden = false;
      } else {
        profileAvatarPreview.hidden = true;
        profileAvatarFallback.textContent = initial;
        profileAvatarFallback.hidden = false;
        if (btnRemovePhoto) btnRemovePhoto.hidden = true;
      }
    }
  }

  // ---------------------------------------------------------------------------
  // Flujo de Registro e Inicio de Sesión
  // ---------------------------------------------------------------------------
  if (formLogin) {
    formLogin.addEventListener('submit', async (e) => {
      e.preventDefault();
      hideAlert(authAlert);

      const identificador = $('login-identificador').value.trim();
      const password = $('login-password').value;

      if (!identificador || !password) {
        showAlert(authAlert, 'Por favor completa todos los campos.');
        return;
      }

      setButtonLoading(btnSubmitLogin, true, 'Iniciar Sesión');

      try {
        const res = await fetch('/api/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ identificador, password })
        });

        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.error || 'Credenciales inválidas.');
        }

        setToken(data.token);
        currentUser = data.usuario;
        onLoginSuccess();
      } catch (err) {
        showAlert(authAlert, err.message || 'Error al iniciar sesión.');
      } finally {
        setButtonLoading(btnSubmitLogin, false, 'Iniciar Sesión');
      }
    });
  }

  if (formRegister) {
    formRegister.addEventListener('submit', async (e) => {
      e.preventDefault();
      hideAlert(authAlert);

      const nombre = $('register-nombre').value.trim();
      const username = $('register-username').value.trim();
      const email = $('register-email').value.trim();
      const password = $('register-password').value;
      const confirm = $('register-confirm').value;

      if (password !== confirm) {
        showAlert(authAlert, 'Las contraseñas no coinciden.');
        return;
      }

      if (password.length < 6) {
        showAlert(authAlert, 'La contraseña debe tener al menos 6 caracteres.');
        return;
      }

      setButtonLoading(btnSubmitRegister, true, 'Crear Cuenta');

      try {
        const res = await fetch('/api/auth/register', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username, email, password, nombre })
        });

        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.error || 'Error al registrar usuario.');
        }

        setToken(data.token);
        currentUser = data.usuario;
        onLoginSuccess();
      } catch (err) {
        showAlert(authAlert, err.message || 'Error al crear la cuenta.');
      } finally {
        setButtonLoading(btnSubmitRegister, false, 'Crear Cuenta');
      }
    });
  }

  function onLoginSuccess() {
    renderUserUI(currentUser);
    if (authGateway) {
      authGateway.classList.add('is-hidden');
    }
    // Despacha evento para que el chat sincronice el usuario e historial
    window.dispatchEvent(new CustomEvent('via:authenticated', { detail: currentUser }));
  }

  function handleAuthExpired() {
    clearToken();
    renderUserUI(null);
    if (authGateway) {
      authGateway.classList.remove('is-hidden');
      switchAuthTab('login');
      showAlert(authAlert, 'Tu sesión ha expirado. Por favor inicia sesión nuevamente.');
    }
  }

  function logout() {
    clearToken();
    renderUserUI(null);
    if (userDropdown) userDropdown.hidden = true;
    if (profileModal) closeProfileModal();
    if (authGateway) {
      authGateway.classList.remove('is-hidden');
      switchAuthTab('login');
      hideAlert(authAlert);
    }
    window.dispatchEvent(new CustomEvent('via:logout'));
  }

  // ---------------------------------------------------------------------------
  // Dropdown del Menú de Usuario
  // ---------------------------------------------------------------------------
  if (btnUserProfile) {
    btnUserProfile.addEventListener('click', (e) => {
      e.stopPropagation();
      const isOpen = !userDropdown.hidden;
      userDropdown.hidden = isOpen;
      btnUserProfile.setAttribute('aria-expanded', String(!isOpen));
    });
  }

  document.addEventListener('click', (e) => {
    if (userDropdown && !userDropdown.hidden && !userMenuWrapper.contains(e.target)) {
      userDropdown.hidden = true;
      if (btnUserProfile) btnUserProfile.setAttribute('aria-expanded', 'false');
    }
  });

  if (dropdownBtnLogout) dropdownBtnLogout.addEventListener('click', logout);

  if (dropdownBtnProfile) {
    dropdownBtnProfile.addEventListener('click', () => {
      userDropdown.hidden = true;
      openProfileModal('perfil');
    });
  }

  if (dropdownBtnAI) {
    dropdownBtnAI.addEventListener('click', () => {
      userDropdown.hidden = true;
      openProfileModal('ai');
    });
  }

  // ---------------------------------------------------------------------------
  // Modal de Perfil y Personalizar AI
  // ---------------------------------------------------------------------------
  function openProfileModal(tab = 'perfil') {
    if (!currentUser) return;
    hideAlert(modalAlert);
    stagedPhotoBase64 = currentUser.foto_perfil || null;

    // Cargar datos en el formulario de perfil
    if (profileInputNombre) profileInputNombre.value = currentUser.nombre || '';
    if (profileInputUsername) profileInputUsername.value = `@${currentUser.username}`;
    if (profileInputEmail) profileInputEmail.value = currentUser.email || '';
    renderAvatar(currentUser.foto_perfil, currentUser.nombre || currentUser.username);

    // Cargar datos en el formulario de IA
    const prefs = currentUser.preferencias_ai || {};
    if (aiToneSelect) aiToneSelect.value = prefs.tono || 'cercano';
    if (aiPreferredName) aiPreferredName.value = prefs.nombre_usuario_preferido || '';
    if (aiCustomDirectives) aiCustomDirectives.value = prefs.directivas_extra || '';

    // Cambiar a la pestaña solicitada
    switchModalTab(tab);

    if (profileModalScrim) profileModalScrim.hidden = false;
    if (profileModal) profileModal.hidden = false;
  }

  function closeProfileModal() {
    if (profileModalScrim) profileModalScrim.hidden = true;
    if (profileModal) profileModal.hidden = true;
  }

  function switchModalTab(tab) {
    hideAlert(modalAlert);
    if (tab === 'perfil') {
      if (modalTabPerfil) modalTabPerfil.classList.add('is-active');
      if (modalTabAI) modalTabAI.classList.remove('is-active');
      if (modalContentPerfil) modalContentPerfil.hidden = false;
      if (modalContentAI) modalContentAI.hidden = true;
    } else {
      if (modalTabAI) modalTabAI.classList.add('is-active');
      if (modalTabPerfil) modalTabPerfil.classList.remove('is-active');
      if (modalContentAI) modalContentAI.hidden = false;
      if (modalContentPerfil) modalContentPerfil.hidden = true;
    }
  }

  if (modalTabPerfil) modalTabPerfil.addEventListener('click', () => switchModalTab('perfil'));
  if (modalTabAI) modalTabAI.addEventListener('click', () => switchModalTab('ai'));
  if (modalProfileClose) modalProfileClose.addEventListener('click', closeProfileModal);
  if (profileModalScrim) profileModalScrim.addEventListener('click', closeProfileModal);

  // Subir foto de perfil con compresión a canvas
  if (profilePhotoInput) {
    profilePhotoInput.addEventListener('change', (e) => {
      const file = e.target.files && e.target.files[0];
      if (!file) return;

      if (!file.type.startsWith('image/')) {
        showAlert(modalAlert, 'Por favor selecciona un archivo de imagen válido.');
        return;
      }

      if (file.size > 2 * 1024 * 1024) {
        showAlert(modalAlert, 'La imagen no debe superar los 2MB.');
        return;
      }

      const reader = new FileReader();
      reader.onload = (evt) => {
        const img = new Image();
        img.onload = () => {
          // Redimensionar a máx 256x256 para almacenamiento eficiente
          const canvas = document.createElement('canvas');
          const maxDim = 256;
          let w = img.width;
          let h = img.height;
          if (w > h && w > maxDim) {
            h = (h * maxDim) / w;
            w = maxDim;
          } else if (h > maxDim) {
            w = (w * maxDim) / h;
            h = maxDim;
          }
          canvas.width = w;
          canvas.height = h;
          const ctx = canvas.getContext('2d');
          ctx.drawImage(img, 0, 0, w, h);
          stagedPhotoBase64 = canvas.toDataURL('image/jpeg', 0.85);
          renderAvatar(stagedPhotoBase64, currentUser.nombre || currentUser.username);
        };
        img.src = evt.target.result;
      };
      reader.readAsDataURL(file);
    });
  }

  if (btnRemovePhoto) {
    btnRemovePhoto.addEventListener('click', () => {
      stagedPhotoBase64 = '';
      if (profilePhotoInput) profilePhotoInput.value = '';
      renderAvatar('', currentUser.nombre || currentUser.username);
    });
  }

  // Guardar Cambios de Perfil
  if (formUpdateProfile) {
    formUpdateProfile.addEventListener('submit', async (e) => {
      e.preventDefault();
      hideAlert(modalAlert);

      const nuevoNombre = profileInputNombre.value.trim();
      if (!nuevoNombre) {
        showAlert(modalAlert, 'El nombre no puede estar vacío.');
        return;
      }

      const saveBtn = $('btn-save-profile');
      if (saveBtn) saveBtn.disabled = true;

      try {
        const res = await authFetch('/api/usuario/perfil', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            nombre: nuevoNombre,
            foto_perfil: stagedPhotoBase64 !== null ? stagedPhotoBase64 : (currentUser.foto_perfil || '')
          })
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Error al actualizar perfil');

        currentUser = data.usuario;
        renderUserUI(currentUser);
        showAlert(modalAlert, '¡Perfil actualizado con éxito!', 'success');
        setTimeout(() => closeProfileModal(), 900);
      } catch (err) {
        showAlert(modalAlert, err.message || 'Error al guardar perfil.');
      } finally {
        if (saveBtn) saveBtn.disabled = false;
      }
    });
  }

  // Guardar Cambios de Personalizar AI
  if (formUpdateAI) {
    formUpdateAI.addEventListener('submit', async (e) => {
      e.preventDefault();
      hideAlert(modalAlert);

      const prefsActuales = currentUser.preferencias_ai || {};
      const preferencias = {
        ...prefsActuales,
        tono: aiToneSelect.value,
        nombre_usuario_preferido: aiPreferredName.value.trim(),
        directivas_extra: aiCustomDirectives.value.trim()
      };

      const saveBtn = $('btn-save-ai');
      if (saveBtn) saveBtn.disabled = true;

      try {
        const res = await authFetch('/api/usuario/preferencias-ai', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(preferencias)
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Error al guardar preferencias de IA');

        currentUser.preferencias_ai = data.preferencias_ai;
        showAlert(modalAlert, '¡Preferencias de IA actualizadas correctamente!', 'success');
        setTimeout(() => closeProfileModal(), 900);
      } catch (err) {
        showAlert(modalAlert, err.message || 'Error al guardar preferencias de IA.');
      } finally {
        if (saveBtn) saveBtn.disabled = false;
      }
    });
  }

  // ---------------------------------------------------------------------------
  // Inicialización Automática al Cargar la Página
  // ---------------------------------------------------------------------------
  async function initAuth() {
    const token = getToken();
    if (!token) {
      // Usuario no autenticado: mostrar pantalla de Login/Registro inmediatamente
      if (authGateway) authGateway.classList.remove('is-hidden');
      return;
    }

    try {
      const res = await fetch('/api/auth/me', {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (!res.ok) {
        throw new Error('Sesión no válida');
      }

      const data = await res.json();
      currentUser = data.usuario || data;
      renderUserUI(currentUser);
      if (authGateway) authGateway.classList.add('is-hidden');
      window.dispatchEvent(new CustomEvent('via:authenticated', { detail: currentUser }));
    } catch (_) {
      handleAuthExpired();
    }
  }

  // Expone API global de autenticación para que via.js u otros módulos puedan usarla
  window.viaAuth = {
    getToken,
    getCurrentUser: () => currentUser,
    authFetch,
    logout,
    openProfileModal
  };

  // Ejecuta la inicialización cuando el DOM esté listo
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAuth);
  } else {
    initAuth();
  }
})();
