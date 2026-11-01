const IAFavorites = (() => {
  const STORAGE_KEY = 'ia_favorites_v1';
  // Normalized storage keys
  const SIDEBAR_STATE_KEY = 'ia_fav_sidebar_state';
  const POPOUT_PREFERENCE_KEY = 'ia_favorites_popout_preference';
  const LAST_USED_METHOD_KEY = 'ia_fav_last_method';
  const POPOUT_ACTIVE_KEY = 'ia_fav_popout_active';
  const POPOUT_TS_KEY = 'ia_fav_popout_ts';
  let elements = {};
  // Re-entrancy guard to satisfy popup blockers and avoid multi-click races
  let openingPopout = false;

  // Reusable hidden anchor fallback (works well on iOS/Safari)
  function getOrCreatePopoutAnchor(url) {
    let a = document.getElementById('ia-popout-fallback-anchor');
    if (!a) {
      a = document.createElement('a');
      a.id = 'ia-popout-fallback-anchor';
      a.style.display = 'none';
      document.body.appendChild(a);
    }
    a.href = url;
    a.target = '_blank';   // open new tab/window
    // Avoid rel=noreferrer to improve compatibility on some iOS versions
    return a;
  }
  
  // Migrate legacy localStorage keys to new normalized keys (idempotent)
  function migrateLegacyKeys() {
    try {
      const legacySidebar = localStorage.getItem('ia_sidebar_state');
      if (legacySidebar && !localStorage.getItem(SIDEBAR_STATE_KEY)) {
        localStorage.setItem(SIDEBAR_STATE_KEY, legacySidebar);
        localStorage.removeItem('ia_sidebar_state');
      }
      const legacyActive = localStorage.getItem('ia_popout_active');
      const legacyTs = localStorage.getItem('ia_popout_timestamp');
      if (legacyActive && !localStorage.getItem(POPOUT_ACTIVE_KEY)) {
        localStorage.setItem(POPOUT_ACTIVE_KEY, legacyActive);
        if (legacyTs) localStorage.setItem(POPOUT_TS_KEY, legacyTs);
        localStorage.removeItem('ia_popout_active');
        localStorage.removeItem('ia_popout_timestamp');
      }
      const legacyMethod = localStorage.getItem('ia_favorites_last_used_method');
      if (legacyMethod && !localStorage.getItem(LAST_USED_METHOD_KEY)) {
        localStorage.setItem(LAST_USED_METHOD_KEY, legacyMethod);
        localStorage.removeItem('ia_favorites_last_used_method');
      }
    } catch (e) {}
  }
  
  function generateId(item) {
    return `${item.srcLang}:${item.tgtLang}:${item.src}→${item.tgt}`.toLowerCase();
  }

  function getFavorites() {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
    } catch {
      return [];
    }
  }

  function saveFavorites(favorites) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(favorites));
      return true;
    } catch {
      console.error('Failed to save favorites (storage full or private mode)');
      return false;
    }
  }

  function renderList(favorites = null) {
    const items = favorites || getFavorites();
    const searchTerm = (elements.searchEl?.value || '').toLowerCase();
    
    const filtered = searchTerm ? items.filter(item => 
      item.src.toLowerCase().includes(searchTerm) || 
      item.tgt.toLowerCase().includes(searchTerm) ||
      (item.domain || '').toLowerCase().includes(searchTerm)
    ) : items;

    if (elements.listEl) {
      elements.listEl.innerHTML = filtered.map(item => `
        <div class="favorite-item p-3 border-bottom" data-id="${item.id}">
          <div class="d-flex justify-content-between align-items-start">
            <div>
              <strong class="d-block">${item.src}</strong>
              <span class="text-muted">→</span>
              <em>${item.tgt}</em>
            </div>
            <button
              class="btn btn-sm btn-link text-danger"
              onclick="IAFavorites.removeById('${item.id}')"
              aria-label="Remove from favorites">
              ✕
            </button>
          </div>
        </div>
      `).join('');
    }

    if (elements.countEl) {
      elements.countEl.textContent = items.length;
      // Update any navbar badges
      document.querySelectorAll('.favorites-count-badge').forEach(badge => {
        badge.textContent = items.length;
      });
    }
  }

  function add(item) {
    const favorites = getFavorites();
    const newItem = {
      ...item,
      id: generateId(item),
      timestamp: Date.now()
    };

    if (!favorites.some(f => f.id === newItem.id)) {
      favorites.unshift(newItem);
      if (saveFavorites(favorites)) {
        renderList(favorites);
      }
    }
  }

  function removeById(id) {
    const favorites = getFavorites().filter(f => f.id !== id);
    if (saveFavorites(favorites)) {
      renderList(favorites);
    }
  }

  function toggleSidebar() {
    const sidebar = document.querySelector('.favorites-sidebar');
    const toggleBtn = document.querySelector('.favorites-toggle');
    const body = document.body;
    
    if (sidebar) {
      const isMobile = window.innerWidth < 768;
      
      // NEW: Record that user chose to use sidebar
      setLastUsedMethod('sidebar');
      
      if (isMobile) {
        // Mobile: Toggle .is-hidden class on sidebar
        const isVisible = !sidebar.classList.contains('is-hidden');
        sidebar.classList.toggle('is-hidden');
        
        // Update button for mobile
        if (toggleBtn) {
          toggleBtn.setAttribute('aria-expanded', !isVisible);
          toggleBtn.innerHTML = isVisible ? '⭐' : '✕';
          toggleBtn.setAttribute('aria-label', isVisible ? 'Show favorites drawer' : 'Hide favorites drawer');
          toggleBtn.title = isVisible ? 'Tap to show favorites' : 'Tap to hide favorites';
        }
        
        // Save state for mobile
        localStorage.setItem(SIDEBAR_STATE_KEY, isVisible ? 'hidden' : 'visible');
      } else {
        // Desktop: Toggle favorites-hidden class on body
        const isVisible = !body.classList.contains('favorites-hidden');
        body.classList.toggle('favorites-hidden');
        
        // Update button for desktop
        if (toggleBtn) {
          toggleBtn.setAttribute('aria-expanded', !isVisible);
          toggleBtn.innerHTML = `⭐ Favorites ${isVisible ? 'Show' : 'Hide'}`;
          toggleBtn.setAttribute('aria-label', `${isVisible ? 'Show' : 'Hide'} favorites sidebar`);
          toggleBtn.title = `Click to ${isVisible ? 'show' : 'hide'} favorites`;
        }
        
        // Save state for desktop
        localStorage.setItem(SIDEBAR_STATE_KEY, isVisible ? 'hidden' : 'visible');
      }
    }
  }

  function createToggleButton() {
    const btn = document.createElement('button');
    btn.className = 'favorites-toggle btn btn-primary';
    btn.setAttribute('aria-controls', 'favorites-sidebar');
    
    // Check if popout is active first
    const isPopoutActive = checkIfPopoutActive();
    const savedState = localStorage.getItem(SIDEBAR_STATE_KEY);
    const isMobile = window.innerWidth < 768;
    
    // DEBUG: Enhanced logging for troubleshooting
    console.group('🔘 TOGGLE BUTTON CREATION DEBUG');
    console.log('🗗 Popout active:', isPopoutActive);
    console.log('💾 Saved sidebar state:', savedState);
    console.log('📱 Is mobile:', isMobile);
    console.log('⚙️ Popout preference:', getPopoutPreference());
    console.log('🎯 User intent analysis:');
    if (isPopoutActive) {
      console.log('  - System thinks popout is active');
      console.log('  - This might prevent sidebar usage even if user wants it');
    } else {
      console.log('  - No active popout detected');
      console.log('  - Sidebar should be available for user');
    }
    
    if (isPopoutActive) {
      // CRITICAL FIX: Make button clickable for "pop back in" functionality
      console.log('🗗 POPOUT ACTIVE - Creating clickable "pop back in" button');
      console.log('🚨 POTENTIAL PROBLEM: User may want sidebar but system thinks popout is active');
      btn.disabled = false; // CHANGED: Enable the button
      btn.style.opacity = '0.8'; // CHANGED: Less opacity but still visible
      btn.title = 'Click to restore favorites sidebar (close popout)';
      
      if (isMobile) {
        // Mobile: keep clean star only
        btn.innerHTML = '⭐';
        btn.setAttribute('aria-label', 'Restore favorites sidebar');
      } else {
        // Desktop: subtle label without "(Popped Out)"
        btn.innerHTML = '⭐ Favorites';
        btn.setAttribute('aria-label', 'Restore favorites sidebar');
      }
      
      btn.setAttribute('aria-expanded', 'false');
      
      // CRITICAL FIX: Add click handler for "pop back in" functionality
      btn.addEventListener('click', () => {
        console.log('🔄 POP BACK IN - Button clicked by user');
        console.log('✅ User explicitly wants to use sidebar instead of popout');
        // NEW: Record that user chose sidebar method
        setLastUsedMethod('sidebar');
        // Force restore the sidebar
        setPopoutActiveState(false);
        restoreSidebarFromPopout();
        // Update button state
        updateToggleButtonState(btn);
      });
    } else {
      // Normal state logic
      const isInitiallyHidden = (savedState !== null && savedState !== undefined)
        ? (savedState === 'hidden')
        : (isMobile ? true : false);
      
      btn.setAttribute('aria-expanded', !isInitiallyHidden);
      
      // Set initial button content based on screen size and saved state
      if (isMobile) {
        btn.innerHTML = isInitiallyHidden ? '⭐' : '✕';
        btn.setAttribute('aria-label', isInitiallyHidden ? 'Show favorites drawer' : 'Hide favorites drawer');
        btn.title = (isInitiallyHidden ? 'Tap to show favorites' : 'Tap to hide favorites') + ' • Long-press to open popout';
      } else {
        btn.innerHTML = `⭐ Favorites ${isInitiallyHidden ? 'Show' : 'Hide'}`;
        btn.setAttribute('aria-label', `${isInitiallyHidden ? 'Show' : 'Hide'} favorites sidebar`);
        btn.title = `Click to ${isInitiallyHidden ? 'show' : 'hide'} favorites • Right-click to open popout`;
      }
      
      btn.addEventListener('click', toggleSidebar);
      // Add popout gestures: right-click (desktop) and long-press (mobile)
      // Context menu -> open popout
      btn.addEventListener('contextmenu', (e) => {
        e.preventDefault();
        try {
          setLastUsedMethod('popout');
          openFavoritesPopout();
        } catch (err) {
          console.warn('Context popout failed:', err);
          window.open('/terminology/favorites/', '_blank');
        }
      });
      // Long-press (touch) -> open popout
      let touchTimer = null;
      btn.addEventListener('touchstart', (e) => {
        if (e.touches && e.touches.length > 1) return; // ignore multi-touch
        touchTimer = setTimeout(() => {
          try {
            setLastUsedMethod('popout');
            openFavoritesPopout();
          } catch (err) {
            console.warn('Long-press popout failed:', err);
            window.open('/terminology/favorites/', '_blank');
          }
        }, 600); // 600ms long-press
      }, { passive: true });
      ['touchend','touchcancel','touchmove'].forEach(evt => {
        btn.addEventListener(evt, () => {
          if (touchTimer) { clearTimeout(touchTimer); touchTimer = null; }
        }, { passive: true });
      });
    }
    
    console.log('🔘 Button created with state:', btn.innerHTML);
    console.groupEnd();
    
    document.body.appendChild(btn);
    
    // Add loaded class to show button smoothly
    requestAnimationFrame(() => {
      btn.classList.add('loaded');
    });
    
    // Update button on window resize and handle mobile/desktop switching
    window.addEventListener('resize', () => {
      const newIsMobile = window.innerWidth < 768;
      const sidebar = document.querySelector('.favorites-sidebar');
      
      if (newIsMobile !== isMobile) {
        // Device type changed, sync states
        if (newIsMobile) {
          // Switching to mobile: move state from body to sidebar
          const wasHidden = document.body.classList.contains('favorites-hidden');
          document.body.classList.remove('favorites-hidden');
          if (wasHidden) {
            sidebar?.classList.add('is-hidden');
          } else {
            sidebar?.classList.remove('is-hidden');
          }
        } else {
          // Switching to desktop: move state from sidebar to body
          const wasHidden = sidebar?.classList.contains('is-hidden');
          sidebar?.classList.remove('is-hidden');
          if (wasHidden) {
            document.body.classList.add('favorites-hidden');
          } else {
            document.body.classList.remove('favorites-hidden');
          }
        }
      }
      
      // Update button text for current device type
      const isCurrentlyHidden = newIsMobile ?
        sidebar?.classList.contains('is-hidden') :
        document.body.classList.contains('favorites-hidden');
      
      if (newIsMobile) {
        btn.innerHTML = isCurrentlyHidden ? '⭐' : '✕';
        btn.setAttribute('aria-label', isCurrentlyHidden ? 'Show favorites drawer' : 'Hide favorites drawer');
        btn.title = (isCurrentlyHidden ? 'Tap to show favorites' : 'Tap to hide favorites') + ' • Long-press to open popout';
      } else {
        btn.innerHTML = `⭐ Favorites ${isCurrentlyHidden ? 'Show' : 'Hide'}`;
        btn.setAttribute('aria-label', `${isCurrentlyHidden ? 'Show' : 'Hide'} favorites sidebar`);
        btn.title = `Click to ${isCurrentlyHidden ? 'show' : 'hide'} favorites • Right-click to open popout`;
      }
    });
    
    return btn;
  }

  function init(els) {
    elements = els;

    // Check if popout is active FIRST to prevent flash
    const isPopoutActive = checkIfPopoutActive();
    
    // Migrate legacy keys to normalized keys
    migrateLegacyKeys();

    // DEBUG: Comprehensive logging for troubleshooting
    console.group('🔍 FAVORITES DEBUG - Init Process');
    console.log('📍 Page:', window.location.pathname);
    console.log('📱 Mobile:', window.innerWidth < 768);
    console.log('🗗 Popout Active:', isPopoutActive);
    console.log('💾 LocalStorage State:');
    console.log('  - ia_popout_active:', localStorage.getItem('ia_popout_active'));
    console.log('  - ia_popout_timestamp:', localStorage.getItem('ia_popout_timestamp'));
    console.log('  - sidebar_state:', localStorage.getItem(SIDEBAR_STATE_KEY));
    
    // Get sidebar and preferences
    const sidebar = document.querySelector('.favorites-sidebar');
    const savedState = localStorage.getItem(SIDEBAR_STATE_KEY);
    const isMobile = window.innerWidth < 768;
    
    if (!sidebar) {
      console.log('❌ No sidebar found, exiting init');
      console.groupEnd();
      return;
    }
    
    console.log('✅ Sidebar found:', sidebar);
    console.log('🎨 Current sidebar classes:', Array.from(sidebar.classList));
    console.log('📋 Current sidebar attributes:', Array.from(sidebar.attributes).map(a => `${a.name}="${a.value}"`));
    
    // If popout is active, keep sidebar completely hidden
    if (isPopoutActive) {
      console.log('🗗 POPOUT ACTIVE - Hiding sidebar');
      sidebar.setAttribute('data-hidden-for-popout', 'true');
      // Explicitly remove any existing classes that might show the sidebar
      sidebar.classList.remove('js-safe-to-show', 'js-visible');
      // Add HTML class for immediate hiding
      document.documentElement.classList.add('popout-active');
      console.log('✅ Popout hiding complete');
      console.groupEnd();
      // CRITICAL FIX: Don't return early - we still need to create the toggle button!
      // The toggle button shows the popout notification and allows restoration
    } else {
      console.log('📱 NORMAL MODE - Setting up sidebar');
      // Remove popout class if not active
      document.documentElement.classList.remove('popout-active');
      
      // Normal sidebar logic - mark as safe to show
      console.log('🎯 Setting up normal sidebar logic');
      sidebar.classList.add('js-safe-to-show');
      sidebar.setAttribute('id', 'favorites-sidebar');
      
      // Determine initial state
      const shouldBeHidden = (savedState !== null && savedState !== undefined)
        ? (savedState === 'hidden')
        : (isMobile ? true : false);
      console.log('👁️ Should be hidden:', shouldBeHidden, '(savedState:', savedState, ', isMobile:', isMobile, ')');
      
      // Set initial state based on device type
      if (isMobile) {
        if (!shouldBeHidden) {
          sidebar.classList.remove('is-hidden');
          console.log('📱 Mobile: showing sidebar');
        } else {
          sidebar.classList.add('is-hidden');
          console.log('📱 Mobile: hiding sidebar');
        }
        // Remove any body class for mobile
        document.body.classList.remove('favorites-hidden');
      } else {
        // Desktop: Handle body class
        if (shouldBeHidden) {
          document.body.classList.add('favorites-hidden');
          console.log('🖥️ Desktop: hiding sidebar via body class');
        } else {
          document.body.classList.remove('favorites-hidden');
          console.log('🖥️ Desktop: showing sidebar');
        }
      }
      
      console.log('🎨 Final sidebar classes before animation:', Array.from(sidebar.classList));
      console.log('🏗️ Body classes:', Array.from(document.body.classList));
      
      // Enable transitions and make visible after a brief delay to prevent flickering
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          console.log('✨ Enabling transitions and making visible');
          sidebar.classList.add('transitions-enabled');
          sidebar.classList.add('js-visible');
          console.log('🎨 Final sidebar classes after animation:', Array.from(sidebar.classList));
          console.groupEnd();
        });
      });
    }

    // CRITICAL FIX: Always create toggle button, regardless of popout state
    // The toggle button is essential for showing popout notifications and restoration
    console.log('🔘 Creating toggle button (popout active:', isPopoutActive, ')');
    const toggleBtn = createToggleButton();

    // Initial render
    renderList();

    // Search handler
    elements.searchEl?.addEventListener('input', () => renderList());

    // Clear handler
    elements.clearBtn?.addEventListener('click', () => {
      if (confirm('Clear all favorites? This cannot be undone.')) {
        saveFavorites([]);
        renderList([]);
      }
    });

    // Popout handler - robust event targeting (handles clicks on nested SVG/paths)
    document.addEventListener('click', (e) => {
      const btn = e.target?.closest && e.target.closest('#iaPopoutBtn');
      if (!btn) return;
      e.preventDefault();
      e.stopPropagation();
      try { IAFavorites.openFavoritesPopout(); }
      catch (error) {
        console.error('Error opening popout:', error);
        window.open('/terminology/favorites/', '_blank');
      }
    });

    // Attach early gesture handlers to maximize popup success on mobile/desktop
    const directPopoutBtn = document.getElementById('iaPopoutBtn');
    const directHandler = (e) => {
      e.preventDefault();
      e.stopPropagation();
      try { IAFavorites.openFavoritesPopout(); }
      catch (error) {
        console.error('Error opening popout:', error);
        window.open('/terminology/favorites/', '_blank');
      }
    };
    if (directPopoutBtn) {
      // Earliest possible gesture events
      directPopoutBtn.addEventListener('pointerdown', directHandler, { passive: false });
      directPopoutBtn.addEventListener('touchstart', directHandler, { passive: false });
      directPopoutBtn.addEventListener('touchend', directHandler, { passive: false });
      directPopoutBtn.addEventListener('click', directHandler);
    }

    // CAPTURE-PHASE global early handlers (in case the button is re-rendered or nested content eats the event)
    const captureHandler = (e) => {
      const btn = e.target?.closest && e.target.closest('#iaPopoutBtn');
      if (!btn) return;
      // Only act on primary pointer/touch to avoid duplicates
      if (e.type === 'pointerdown' && e.button !== 0) return;
      e.preventDefault();
      e.stopPropagation();
      try { IAFavorites.openFavoritesPopout(); }
      catch (error) {
        console.error('Error opening popout (capture):', error);
        window.open('/terminology/favorites/', '_blank');
      }
    };
    document.addEventListener('pointerdown', captureHandler, { capture: true, passive: false });
    document.addEventListener('touchstart', captureHandler, { capture: true, passive: false });

    // Cross-tab sync - Enhanced to handle popout state
    window.addEventListener('storage', (e) => {
      if (e.key === STORAGE_KEY) {
        renderList();
      } else if (e.key === SIDEBAR_STATE_KEY) {
        const isHidden = e.newValue === 'hidden';
        const isMobile = window.innerWidth < 768;
        const sidebar = document.querySelector('.favorites-sidebar');
        
        if (isMobile) {
          sidebar?.classList.toggle('is-hidden', isHidden);
        } else {
          document.body.classList.toggle('favorites-hidden', isHidden);
        }
      } else if (e.key === POPOUT_ACTIVE_KEY) {
        console.group('📡 CROSS-TAB SYNC DEBUG - Popout State Change');
        console.log('🔄 Storage event received');
        console.log('📍 Current page:', window.location.pathname);
        console.log('🔑 Key:', e.key);
        console.log('🆕 New value:', e.newValue);
        console.log('🔙 Old value:', e.oldValue);
        
        const sidebar = document.querySelector('.favorites-sidebar');
        if (!sidebar) {
          console.log('❌ No sidebar found, ignoring event');
          console.groupEnd();
          return;
        }
        
        console.log('✅ Sidebar found, processing event');
        
        if (e.newValue === 'true') {
          // Popout became active in another tab
          console.log('🗗 Popout activated in another tab - hiding sidebar');
          hideSidebarForPopout();
        } else if (e.newValue === null) {
          // Popout was closed in another tab
          console.log('❌ Popout closed in another tab - restoring sidebar');
          restoreSidebarFromPopout();
        }
        
        console.groupEnd();
      }
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
      // Toggle favorites: Ctrl/Cmd + .
      if ((e.ctrlKey || e.metaKey) && e.key === '.') {
        e.preventDefault();
        toggleSidebar();
        return;
      }
      // Open popout: Ctrl/Cmd + Shift + O
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === 'O' || e.key === 'o')) {
        e.preventDefault();
        try {
          setLastUsedMethod('popout');
          openFavoritesPopout();
        } catch (err) {
          window.open('/terminology/favorites/', '_blank');
        }
      }
    });

    // Check if user prefers popout and auto-open if enabled
    checkAutoOpenPopout();
  }

  function getPopoutPreference() {
    return localStorage.getItem(POPOUT_PREFERENCE_KEY) === 'true';
  }

  function setPopoutPreference(enabled) {
    localStorage.setItem(POPOUT_PREFERENCE_KEY, enabled.toString());
  }

  // NEW: Track what method user used last (sidebar or popout)
  function getLastUsedMethod() {
    return localStorage.getItem(LAST_USED_METHOD_KEY) || 'sidebar'; // Default to sidebar
  }

  function setLastUsedMethod(method) {
    localStorage.setItem(LAST_USED_METHOD_KEY, method);
    console.log('📝 User preference updated - last used method:', method);
  }

  function openFavoritesPopout() {
    // Open synchronously and as early as possible in the gesture to satisfy blockers
    if (openingPopout) return;
    openingPopout = true;
    const favoritesUrl = '/terminology/favorites/';
    const WINDOW_NAME = 'favorites_popout'; // constant to reuse same window across clicks
    const FEATURES = 'width=1200,height=800,scrollbars=yes,resizable=yes,toolbar=no,menubar=no,location=no,status=no';
    console.group('🗗 POPOUT DEBUG - Opening Favorites (about:blank -> navigate + anchor fallback)');
    try {
      // Reuse existing window if present
      if (window.popoutWindowRef && !window.popoutWindowRef.closed) {
        console.log('🔁 Reusing existing popout window');
        try { window.popoutWindowRef.focus(); } catch {}
        try { window.popoutWindowRef.location.href = favoritesUrl; } catch {}
        setPopoutPreference(true);
        setLastUsedMethod('popout');
        setPopoutActiveState(true);
        hideSidebarForPopout();
        monitorPopoutWindow(window.popoutWindowRef);
        return;
      }

      // Strategy A: Open about:blank first with constant name, then navigate (best for iOS/Safari)
      let win = window.open('about:blank', WINDOW_NAME, FEATURES);
      if (!win) {
        // Strategy B: direct URL open with same name (some desktop browsers)
        win = window.open(favoritesUrl, WINDOW_NAME, FEATURES);
      }
      if (!win) {
        // Strategy C: anchor element click fallback (still in gesture)
        console.log('B failed -> trying anchor fallback');
        const a = getOrCreatePopoutAnchor(favoritesUrl);
        a.click();
        // Cannot monitor tab reliably; do not hide sidebar
        setPopoutPreference(true);
        setLastUsedMethod('popout');
        console.groupEnd();
        return;
      }

      // Navigate and focus
      try { if (win.location.href === 'about:blank') win.location.href = favoritesUrl; } catch {}
      try { win.focus(); } catch {}

      // Store and mark active
      window.popoutWindowRef = win;
      setPopoutPreference(true);
      setLastUsedMethod('popout');
      setPopoutActiveState(true);

      // Hide in opener and monitor close
      hideSidebarForPopout();
      monitorPopoutWindow(win);

      if (typeof gtag === "function") {
        gtag('event', 'favorites_popout_opened', { source: 'sidebar_button' });
      }
      console.log('✅ Popout opened (constant-name + about:blank or anchor)');
    } catch (err) {
      console.error('❌ Error opening popout:', err);
      // Worst-case fallback: navigate current tab
      window.location.href = favoritesUrl;
    } finally {
      console.groupEnd();
      openingPopout = false;
    }
  }

  function hideSidebarForPopout() {
    const sidebar = document.querySelector('.favorites-sidebar');
    const body = document.body;
    const isMobile = window.innerWidth < 768;
    
    if (sidebar) {
      // Mark that sidebar is hidden due to popout and remove safe-to-show class
      sidebar.setAttribute('data-hidden-for-popout', 'true');
      sidebar.classList.remove('js-safe-to-show', 'js-visible');
      
      // Add HTML class for immediate hiding
      document.documentElement.classList.add('popout-active');
      
      // Reset body padding for desktop
      if (!isMobile) {
        body.classList.remove('favorites-hidden');
        body.style.paddingRight = '0';
      }
      
      // Update toggle button to show "Show" state but disable it
      const toggleBtn = document.querySelector('.favorites-toggle');
      if (toggleBtn) {
        // Keep the button enabled so user can "pop back in"
        toggleBtn.disabled = false;
        toggleBtn.style.opacity = '1';
        toggleBtn.title = 'Click to restore favorites sidebar';
        
        if (isMobile) {
          toggleBtn.innerHTML = '⭐';
          toggleBtn.setAttribute('aria-label', 'Restore favorites sidebar');
        } else {
          toggleBtn.innerHTML = '⭐ Favorites';
          toggleBtn.setAttribute('aria-label', 'Restore favorites sidebar');
        }
      }
    }
  }

  function restoreSidebarFromPopout() {
    console.log('🔄 RESTORE DEBUG - Starting sidebar restoration');
    const sidebar = document.querySelector('.favorites-sidebar');
    const body = document.body;
    const isMobile = window.innerWidth < 768;
    
    console.log('📍 Sidebar found:', !!sidebar);
    console.log('📱 Is mobile:', isMobile);
    console.log('🏷️ Current popout attribute:', sidebar?.getAttribute('data-hidden-for-popout'));
    
    if (sidebar) {
      // CRITICAL FIX: Always restore sidebar regardless of attribute state
      // This handles cases where the attribute might be corrupted or missing
      console.log('🧹 Removing popout flags and restoring sidebar...');
      
      // Remove the popout flag and restore safe-to-show
      sidebar.removeAttribute('data-hidden-for-popout');
      sidebar.classList.add('js-safe-to-show');
      
      // Remove HTML class for popout hiding
      document.documentElement.classList.remove('popout-active');
      
      // Restore sidebar visibility; on mobile default to hidden after popout closes
      let savedState = localStorage.getItem(SIDEBAR_STATE_KEY);
      let shouldBeHidden = savedState === 'hidden';

      if (isMobile) {
        // Force mobile drawer hidden after popout closes; user can tap star to open
        shouldBeHidden = true;
        localStorage.setItem(SIDEBAR_STATE_KEY, 'hidden');
      }

      console.log('💾 Saved state:', savedState);
      console.log('👁️ Should be hidden (after popout close):', shouldBeHidden);

      if (isMobile) {
        sidebar.classList.toggle('is-hidden', shouldBeHidden);
        console.log('📱 Mobile: Set is-hidden to', shouldBeHidden);
        // Ensure desktop class not lingering
        body.classList.remove('favorites-hidden');
      } else {
        body.classList.toggle('favorites-hidden', shouldBeHidden);
        console.log('🖥️ Desktop: Set favorites-hidden to', shouldBeHidden);
        // Ensure mobile class not lingering
        sidebar.classList.remove('is-hidden');
      }
      
      // Make visible with double requestAnimationFrame for reliability
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          sidebar.classList.add('js-visible');
          console.log('✨ Added js-visible class');
          
          // Force a style recalculation to ensure visibility
          sidebar.offsetHeight; // Trigger reflow
          
          console.log('🎨 Final sidebar classes:', Array.from(sidebar.classList));
          console.log('🏗️ Final body classes:', Array.from(body.classList));
        });
      });
      
      // Re-enable and update toggle button
      const toggleBtn = document.querySelector('.favorites-toggle');
      if (toggleBtn) {
        console.log('🔘 Updating toggle button...');
        toggleBtn.disabled = false;
        toggleBtn.style.opacity = '1';
        
        if (isMobile) {
          toggleBtn.innerHTML = shouldBeHidden ? '⭐' : '✕';
          toggleBtn.setAttribute('aria-label', shouldBeHidden ? 'Show favorites drawer' : 'Hide favorites drawer');
          toggleBtn.title = (shouldBeHidden ? 'Tap to show favorites' : 'Tap to hide favorites') + ' • Long-press to open popout';
        } else {
          toggleBtn.innerHTML = `⭐ Favorites ${shouldBeHidden ? 'Show' : 'Hide'}`;
          toggleBtn.setAttribute('aria-label', `${shouldBeHidden ? 'Show' : 'Hide'} favorites sidebar`);
          toggleBtn.title = `Click to ${shouldBeHidden ? 'show' : 'hide'} favorites • Right-click to open popout`;
        }
        console.log('🔘 Toggle button updated:', toggleBtn.innerHTML);
      } else {
        console.log('❌ No toggle button found');
      }
      
      console.log('✅ Sidebar restoration complete');
    } else {
      console.log('❌ No sidebar found for restoration');
    }
  }

  function checkIfPopoutActive() {
    // Normalized popout check with bounded timeout (2 hours)
    try {
      const popoutState = localStorage.getItem(POPOUT_ACTIVE_KEY);
      const popoutTimestamp = localStorage.getItem(POPOUT_TS_KEY);
      
      console.group('🔍 POPOUT STATE CHECK DEBUG');
      console.log('🔑 Popout state:', popoutState);
      console.log('⏰ Popout timestamp:', popoutTimestamp);
      
      if (popoutState === 'true' && popoutTimestamp) {
        const now = Date.now();
        const timestamp = parseInt(popoutTimestamp);
        const twoHours = 2 * 60 * 60 * 1000;
        const timeDiff = now - timestamp;
        const ageMinutes = Math.round(timeDiff / 1000 / 60);
        
        console.log('📊 Current time:', new Date(now).toLocaleTimeString());
        console.log('📊 Popout created:', new Date(timestamp).toLocaleTimeString());
        console.log('⏱️ Age in minutes:', ageMinutes);
        console.log('⏱️ Timeout threshold: 120 minutes (2 hours)');
        
        if (timeDiff < twoHours) {
          console.log('✅ Popout is active (age:', ageMinutes, 'minutes) - BLOCKING SIDEBAR');
          console.groupEnd();
          return true;
        } else {
          console.log('⏰ Popout expired (age:', ageMinutes, 'minutes), clearing state');
          setPopoutActiveState(false);
          console.groupEnd();
        }
      } else {
        console.log('✅ No active popout state - sidebar can be used');
        console.groupEnd();
      }
      
      return false;
    } catch (error) {
      console.warn('❌ Error checking popout state:', error);
      console.groupEnd();
      return false;
    }
  }

  function setPopoutActiveState(active) {
    if (active) {
      localStorage.setItem(POPOUT_ACTIVE_KEY, 'true');
      localStorage.setItem(POPOUT_TS_KEY, Date.now().toString());
      document.documentElement.classList.add('popout-active');
      // Natural 'storage' events will fire in other tabs due to setItem
    } else {
      localStorage.removeItem(POPOUT_ACTIVE_KEY);
      localStorage.removeItem(POPOUT_TS_KEY);
      document.documentElement.classList.remove('popout-active');
      // Natural 'storage' events will fire in other tabs due to removeItem
    }
  }

  function monitorPopoutWindow(popoutWindow) {
    console.log('👀 Setting up enhanced popout window monitoring');
    
    // CRITICAL FIX: Clear any existing monitoring first
    if (window.popoutMonitorInterval) {
      console.log('🧹 Clearing existing popout monitor interval');
      clearInterval(window.popoutMonitorInterval);
      delete window.popoutMonitorInterval;
    }
    
    // Check if the popout window is closed every 2 seconds
    const checkClosed = setInterval(() => {
      try {
        if (popoutWindow.closed) {
          console.log('🪟 Popout window detected as closed');
          clearInterval(checkClosed);
          delete window.popoutMonitorInterval;
          
          // FIXED: Always restore sidebar when popout window is closed
          // The user closed the window, so they want the sidebar back
          console.log('✅ Popout window closed - restoring sidebar');
          
          // Mark popout as inactive
          setPopoutActiveState(false);
          // Clear window reference
          delete window.popoutWindowRef;
          // Restore sidebar immediately
          restoreSidebarFromPopout();
          
          // Clean up event listeners
          if (window.popoutCleanup) {
            window.removeEventListener('beforeunload', window.popoutCleanup);
            delete window.popoutCleanup;
          }
        }
      } catch (error) {
        console.warn('❌ Error checking popout window status:', error);
        // If we can't check the window status, assume it's closed and clean up
        clearInterval(checkClosed);
        delete window.popoutMonitorInterval;
        console.log('⚠️ Assuming window closed due to error, cleaning up');
        setPopoutActiveState(false);
        delete window.popoutWindowRef;
        restoreSidebarFromPopout();
      }
    }, 2000); // Check every 2 seconds
    
    // Store the interval reference for cleanup
    window.popoutMonitorInterval = checkClosed;
    
    // Also listen for beforeunload on the main window to clean up
    const cleanup = () => {
      console.log('🧹 Cleaning up popout monitoring due to main window unload');
      if (window.popoutMonitorInterval) {
        clearInterval(window.popoutMonitorInterval);
        delete window.popoutMonitorInterval;
      }
      // Don't automatically clear popout state on main window navigation
      // The popout might still be open in another window
    };
    
    // Remove any existing beforeunload listener first
    if (window.popoutCleanup) {
      window.removeEventListener('beforeunload', window.popoutCleanup);
    }
    
    window.addEventListener('beforeunload', cleanup);
    
    // Store the cleanup function so we can call it if needed
    window.popoutCleanup = cleanup;
  }

  function checkAutoOpenPopout() {
    // Only auto-open on the main translator page, not on other pages
    const isMainPage = window.location.pathname === '/terminology/translate/' ||
                      window.location.pathname === '/';
    
    const lastUsedMethod = getLastUsedMethod();
    
    console.group('🔍 AUTO-OPEN POPOUT DEBUG');
    console.log('📍 Is main page:', isMainPage);
    console.log('⚙️ Popout preference:', getPopoutPreference());
    console.log('📊 Favorites count:', getFavorites().length);
    console.log('🗗 Popout currently active:', checkIfPopoutActive());
    console.log('🎯 Last used method:', lastUsedMethod);
    
    // FIXED: Only auto-open if user explicitly used popout in their last session
    if (isMainPage && getPopoutPreference() && lastUsedMethod === 'popout') {
      const favorites = getFavorites();
      // Only auto-open if user has favorites and no popout is currently active
      if (favorites.length > 0 && !checkIfPopoutActive()) {
        console.log('✅ AUTO-OPENING POPOUT - User last chose popout method');
        // Delay slightly to ensure page is fully loaded
        setTimeout(() => {
          console.log('⏰ Auto-popout timeout triggered - opening popout window');
          openFavoritesPopout();
        }, 1000);
      } else {
        console.log('✅ Auto-popout conditions not met - not opening');
      }
    } else {
      if (lastUsedMethod === 'sidebar') {
        console.log('✅ User last chose SIDEBAR - respecting their choice, not auto-opening popout');
      } else {
        console.log('✅ Auto-popout disabled or not on main page');
      }
    }
    console.groupEnd();
  }

  // Emergency restore function for debugging/recovery
  function emergencyRestoreSidebar() {
    console.log('🚨 EMERGENCY RESTORE - Forcing sidebar restoration');
    
    // Clear all popout state
    setPopoutActiveState(false);
    
    // Force restore sidebar
    restoreSidebarFromPopout();
    
    // Also ensure the sidebar is marked as safe to show
    const sidebar = document.querySelector('.favorites-sidebar');
    if (sidebar) {
      sidebar.classList.add('js-safe-to-show', 'js-visible');
      sidebar.removeAttribute('data-hidden-for-popout');
      document.documentElement.classList.remove('popout-active');
    }
    
    console.log('✅ Emergency restore complete');
  }

  // Update toggle button state based on current conditions
  function updateToggleButtonState(btn) {
    console.log('🔘 UPDATING TOGGLE BUTTON STATE');
    
    const isPopoutActive = checkIfPopoutActive();
    const savedState = localStorage.getItem(SIDEBAR_STATE_KEY);
    const isMobile = window.innerWidth < 768;
    
    console.log('🗗 Popout active:', isPopoutActive);
    console.log('💾 Saved state:', savedState);
    console.log('📱 Is mobile:', isMobile);
    
    if (isPopoutActive) {
      // Popout active: allow restoration with a clean, minimal label
      btn.disabled = false;
      btn.style.opacity = '1';
      btn.title = 'Click to restore favorites sidebar';
      
      if (isMobile) {
        // Mobile: star only to avoid ugly text
        btn.innerHTML = '⭐';
        btn.setAttribute('aria-label', 'Restore favorites sidebar');
      } else {
        // Desktop: subtle label without "(Popped Out)"
        btn.innerHTML = '⭐ Favorites';
        btn.setAttribute('aria-label', 'Restore favorites sidebar');
      }
      
      btn.setAttribute('aria-expanded', 'false');
    } else {
      // Normal mode - restore regular toggle functionality
      console.log('🔄 Restoring normal toggle button functionality');
      btn.disabled = false;
      btn.style.opacity = '1';
      
      const shouldBeHidden = (savedState !== null && savedState !== undefined)
        ? (savedState === 'hidden')
        : (isMobile ? true : false);
      
      btn.setAttribute('aria-expanded', !shouldBeHidden);
      
      if (isMobile) {
        btn.innerHTML = shouldBeHidden ? '⭐' : '✕';
        btn.setAttribute('aria-label', shouldBeHidden ? 'Show favorites drawer' : 'Hide favorites drawer');
        btn.title = (shouldBeHidden ? 'Tap to show favorites' : 'Tap to hide favorites') + ' • Long-press to open popout';
      } else {
        btn.innerHTML = `⭐ Favorites ${shouldBeHidden ? 'Show' : 'Hide'}`;
        btn.setAttribute('aria-label', `${shouldBeHidden ? 'Show' : 'Hide'} favorites sidebar`);
        btn.title = `Click to ${shouldBeHidden ? 'show' : 'hide'} favorites • Right-click to open popout`;
      }
      
      // Remove old event listeners and add normal toggle functionality
      const replacement = btn.cloneNode(true); // Remove all event listeners
      btn.replaceWith(replacement);
      const newBtn = document.querySelector('.favorites-toggle');
      newBtn.addEventListener('click', toggleSidebar);
      // Re-attach gesture handlers on the new button
      newBtn.addEventListener('contextmenu', (e) => {
        e.preventDefault();
        try { setLastUsedMethod('popout'); openFavoritesPopout(); } catch { window.open('/terminology/favorites/', '_blank'); }
      });
      let touchTimer2 = null;
      newBtn.addEventListener('touchstart', (e) => {
        if (e.touches && e.touches.length > 1) return;
        touchTimer2 = setTimeout(() => {
          try { setLastUsedMethod('popout'); openFavoritesPopout(); } catch { window.open('/terminology/favorites/', '_blank'); }
        }, 600);
      }, { passive: true });
      ['touchend','touchcancel','touchmove'].forEach(evt => {
        newBtn.addEventListener(evt, () => {
          if (touchTimer2) { clearTimeout(touchTimer2); touchTimer2 = null; }
        }, { passive: true });
      });
    }
  }

  return {
    init,
    add,
    removeById,
    isFav: id => getFavorites().some(f => f.id === id),
    getAll: getFavorites,
    toggleSidebar,
    openFavoritesPopout,
    getPopoutPreference,
    setPopoutPreference,
    getLastUsedMethod,        // NEW: Expose last used method getter
    setLastUsedMethod,        // NEW: Expose last used method setter
    emergencyRestoreSidebar   // Emergency function for recovery
  };
})();