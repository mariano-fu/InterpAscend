// favorites_popout.js (utility-only; state is managed by IAFavorites in favorites.js)
(function () {
  // Usage: onclick="openFavoritesPopout('/terminology/favorites/')"
  // If url not provided, defaults to '/terminology/favorites/'
  window.openFavoritesPopout = function (url = '/terminology/favorites/') {
    const size = { width: 720, height: 680 };

    // Unique name to avoid reusing stale window instances
    const name = 'interpascend_favorites_' + Date.now();

    // Open the popup (let favorites.js manage popout state + sidebar hiding)
    const features = [
      'popup=yes',
      `width=${size.width}`,
      `height=${size.height}`,
      'scrollbars=yes',
      'resizable=yes',
      'toolbar=no',
      'menubar=no',
      'location=no',
      'status=no',
      'noopener',
      'noreferrer'
    ].join(',');

    const win = window.open(url, name, features);
    if (!win) {
      console.warn('Favorites popout blocked by browser.');
      return null;
    }

    function center() {
      try {
        const s = window.screen || {};
        const availLeft = s.availLeft ?? 0;
        const availTop = s.availTop ?? 0;
        const availWidth = s.availWidth ?? s.width ?? 0;
        const availHeight = s.availHeight ?? s.height ?? 0;
        const left = Math.max(availLeft, Math.round(availLeft + (availWidth - size.width) / 2));
        const top = Math.max(availTop, Math.round(availTop + (availHeight - size.height) / 2));
        try { win.resizeTo(size.width, size.height); } catch {}
        try { win.moveTo(left, top); } catch {}
      } catch {}
    }

    // Try to center a few times to handle late metrics/DPI changes
    const tries = [0, 120, 300, 800];
    tries.forEach(t => setTimeout(center, t));

    // Recenter if the opener is resized/moved
    const onResize = () => { if (!win.closed) center(); };
    window.addEventListener('resize', onResize);

    // Cleanup listener when the popup closes
    const checkClosed = setInterval(() => {
      try {
        if (win.closed) {
          clearInterval(checkClosed);
          window.removeEventListener('resize', onResize);
        }
      } catch {
        clearInterval(checkClosed);
        window.removeEventListener('resize', onResize);
      }
    }, 1500);

    try { win.focus(); } catch {}
    return win;
  };
})();