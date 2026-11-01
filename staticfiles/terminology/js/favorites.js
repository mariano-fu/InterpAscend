const IAFavorites = (() => {
  const STORAGE_KEY = 'ia_favorites_v1';
  const SIDEBAR_STATE_KEY = 'ia_sidebar_state';
  const POPOUT_PREFERENCE_KEY = 'ia_favorites_popout_preference';
  let elements = {};
  
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
        // Notify other tabs
        window.dispatchEvent(new StorageEvent('storage', {
          key: STORAGE_KEY
        }));
      }
    }
  }

  function removeById(id) {
    const favorites = getFavorites().filter(f => f.id !== id);
    if (saveFavorites(favorites)) {
      renderList(favorites);
      window.dispatchEvent(new StorageEvent('storage', {
        key: STORAGE_KEY
      }));
    }
  }

  function toggleSidebar() {
    const sidebar = document.querySelector('.favorites-sidebar');
    const toggleBtn = document.querySelector('.favorites-toggle');
    const body = document.body;
    
    if (sidebar) {
      const isMobile = window.innerWidth < 768;
      
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
    
    if (isPopoutActive) {
      // Popout is active, show disabled state
      btn.disabled = true;
      btn.style.opacity = '0.5';
      btn.title = 'Favorites are open in a separate window';
      
      if (isMobile) {
        btn.innerHTML = '⭐';
        btn.setAttribute('aria-label', 'Favorites open in separate window');
      } else {
        btn.innerHTML = '⭐ Favorites (Popped Out)';
        btn.setAttribute('aria-label', 'Favorites are open in separate window');
      }
      
      btn.setAttribute('aria-expanded', 'false');
    } else {
      // Normal state logic
      const isInitiallyHidden = savedState === 'hidden' || (savedState === null && isMobile);
      
      btn.setAttribute('aria-expanded', !isInitiallyHidden);
      
      // Set initial button content based on screen size and saved state
      if (isMobile) {
        btn.innerHTML = isInitiallyHidden ? '⭐' : '✕';
        btn.setAttribute('aria-label', isInitiallyHidden ? 'Show favorites drawer' : 'Hide favorites drawer');
        btn.title = isInitiallyHidden ? 'Tap to show favorites' : 'Tap to hide favorites';
      } else {
        btn.innerHTML = `⭐ Favorites ${isInitiallyHidden ? 'Show' : 'Hide'}`;
        btn.setAttribute('aria-label', `${isInitiallyHidden ? 'Show' : 'Hide'} favorites sidebar`);
        btn.title = `Click to ${isInitiallyHidden ? 'show' : 'hide'} favorites`;
      }
      
      btn.addEventListener('click', toggleSidebar);
    }
    
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
        btn.title = isCurrentlyHidden ? 'Tap to show favorites' : 'Tap to hide favorites';
      } else {
        btn.innerHTML = `⭐ Favorites ${isCurrentlyHidden ? 'Show' : 'Hide'}`;
        btn.setAttribute('aria-label', `${isCurrentlyHidden ? 'Show' : 'Hide'} favorites sidebar`);
        btn.title = `Click to ${isCurrentlyHidden ? 'show' : 'hide'} favorites`;
      }
    });
    
    return btn;
  }

  function init(els) {
    elements = els;

    // Check if popout is active FIRST to prevent flash
    const isPopoutActive = checkIfPopoutActive();
    
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
      // Don't add js-safe-to-show class - keep it hidden
      return;
    } else {
      console.log('📱 NORMAL MODE - Setting up sidebar');
      // Remove popout class if not active
      document.documentElement.classList.remove('popout-active');
    }
    
    // Normal sidebar logic - mark as safe to show
    console.log('🎯 Setting up normal sidebar logic');
    sidebar.classList.add('js-safe-to-show');
    sidebar.setAttribute('id', 'favorites-sidebar');
    
    // Determine initial state
    const shouldBeHidden = savedState === 'hidden' || (savedState === null && isMobile);
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

    // Create toggle button with correct initial state
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

    // Popout handler - use event delegation to handle dynamically added buttons
    document.addEventListener('click', (e) => {
      if (e.target && e.target.id === 'iaPopoutBtn') {
        e.preventDefault();
        e.stopPropagation();
        
        try {
          openFavoritesPopout();
        } catch (error) {
          console.error('Error opening popout:', error);
          // Fallback: direct navigation
          window.open('/terminology/favorites/', '_blank');
        }
      }
    });

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
      } else if (e.key === 'ia_popout_active') {
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

    // Keyboard shortcut
    document.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === '.') {
        e.preventDefault();
        toggleSidebar();
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

  function openFavoritesPopout() {
    const favoritesUrl = '/terminology/favorites/';
    
    console.group('🗗 POPOUT DEBUG - Opening Favorites Popout');
    console.log('🌐 URL:', favoritesUrl);
    console.log('📍 Current page:', window.location.pathname);
    
    try {
      // Try popup window first
      console.log('🚀 Attempting to open popup window...');
      const popoutWindow = window.open(
        favoritesUrl,
        'interpascend_favorites',
        'width=1200,height=800,scrollbars=yes,resizable=yes,toolbar=no,menubar=no,location=no,status=no'
      );
      
      console.log('🪟 Popup result:', popoutWindow);
      console.log('🔍 Is valid window?', popoutWindow && popoutWindow !== window);
      
      if (popoutWindow && popoutWindow !== window) {
        console.log('✅ Popup opened successfully');
        
        // Store reference to the popout window
        window.popoutWindowRef = popoutWindow;
        console.log('📝 Stored window reference');
        
        // Set preference that user likes popout
        setPopoutPreference(true);
        console.log('⚙️ Set popout preference to true');
        
        // Mark popout as active IMMEDIATELY
        console.log('🔄 Setting popout state to active...');
        setPopoutActiveState(true);
        
        // Hide the sidebar in the main window since it's now popped out
        console.log('👁️ Hiding sidebar for popout...');
        hideSidebarForPopout();
        
        // Monitor when the popout window is closed to restore the sidebar
        console.log('👀 Starting popout window monitoring...');
        monitorPopoutWindow(popoutWindow);
        
        // Focus the new window
        popoutWindow.focus();
        console.log('🎯 Focused popout window');
        
        // Fire analytics event if available
        if (typeof gtag === "function") {
          gtag('event', 'favorites_popout_opened', {
            source: 'sidebar_button'
          });
          console.log('📊 Analytics event fired');
        }
        
        console.log('✅ Popout setup complete');
      } else {
        console.log('❌ Popup blocked or failed, trying new tab...');
        // Fallback if popup blocked - open in new tab
        const newTab = window.open(favoritesUrl, '_blank');
        if (newTab) {
          newTab.focus();
          setPopoutPreference(true);
          console.log('✅ Opened in new tab instead');
          // For new tabs, we can't reliably detect when they close, so keep sidebar visible
        } else {
          console.log('❌ All popup methods failed');
          alert('Please allow popups for this site to use the favorites popout feature.');
        }
      }
    } catch (error) {
      console.error('❌ Error in openFavoritesPopout:', error);
      // Last resort fallback
      window.location.href = favoritesUrl;
    }
    
    console.groupEnd();
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
        toggleBtn.disabled = true;
        toggleBtn.style.opacity = '0.5';
        toggleBtn.title = 'Favorites are open in a separate window';
        
        if (isMobile) {
          toggleBtn.innerHTML = '⭐';
          toggleBtn.setAttribute('aria-label', 'Favorites open in separate window');
        } else {
          toggleBtn.innerHTML = '⭐ Favorites (Popped Out)';
          toggleBtn.setAttribute('aria-label', 'Favorites are open in separate window');
        }
      }
    }
  }

  function restoreSidebarFromPopout() {
    const sidebar = document.querySelector('.favorites-sidebar');
    const body = document.body;
    const isMobile = window.innerWidth < 768;
    
    if (sidebar && sidebar.getAttribute('data-hidden-for-popout') === 'true') {
      // Remove the popout flag and restore safe-to-show
      sidebar.removeAttribute('data-hidden-for-popout');
      sidebar.classList.add('js-safe-to-show');
      
      // Remove HTML class for popout hiding
      document.documentElement.classList.remove('popout-active');
      
      // Restore sidebar visibility based on user's previous preference
      const savedState = localStorage.getItem(SIDEBAR_STATE_KEY);
      const shouldBeHidden = savedState === 'hidden';
      
      if (isMobile) {
        sidebar.classList.toggle('is-hidden', shouldBeHidden);
      } else {
        body.classList.toggle('favorites-hidden', shouldBeHidden);
      }
      
      // Make visible
      requestAnimationFrame(() => {
        sidebar.classList.add('js-visible');
      });
      
      // Re-enable and update toggle button
      const toggleBtn = document.querySelector('.favorites-toggle');
      if (toggleBtn) {
        toggleBtn.disabled = false;
        toggleBtn.style.opacity = '1';
        
        if (isMobile) {
          toggleBtn.innerHTML = shouldBeHidden ? '⭐' : '✕';
          toggleBtn.setAttribute('aria-label', shouldBeHidden ? 'Show favorites drawer' : 'Hide favorites drawer');
          toggleBtn.title = shouldBeHidden ? 'Tap to show favorites' : 'Tap to hide favorites';
        } else {
          toggleBtn.innerHTML = `⭐ Favorites ${shouldBeHidden ? 'Show' : 'Hide'}`;
          toggleBtn.setAttribute('aria-label', `${shouldBeHidden ? 'Show' : 'Hide'} favorites sidebar`);
          toggleBtn.title = `Click to ${shouldBeHidden ? 'show' : 'hide'} favorites`;
        }
      }
    }
  }

  function checkIfPopoutActive() {
    // Enhanced popout check with better timeout handling
    try {
      const popoutState = localStorage.getItem('ia_popout_active');
      const popoutTimestamp = localStorage.getItem('ia_popout_timestamp');
      
      if (popoutState === 'true' && popoutTimestamp) {
        // Check if the popout was created recently (within last 4 hours)
        // Extended timeout to handle navigation and browser quirks
        const now = Date.now();
        const timestamp = parseInt(popoutTimestamp);
        const fourHours = 4 * 60 * 60 * 1000;
        const timeDiff = now - timestamp;
        
        if (timeDiff < fourHours) {
          console.log('✅ Popout is active (age:', Math.round(timeDiff / 1000 / 60), 'minutes)');
          return true;
        } else {
          // Popout is too old, clear the state
          console.log('⏰ Popout expired (age:', Math.round(timeDiff / 1000 / 60), 'minutes), clearing state');
          setPopoutActiveState(false);
        }
      }
      
      return false;
    } catch (error) {
      console.warn('❌ Error checking popout state:', error);
      return false;
    }
  }

  function setPopoutActiveState(active) {
    if (active) {
      localStorage.setItem('ia_popout_active', 'true');
      localStorage.setItem('ia_popout_timestamp', Date.now().toString());
      
      // Also set the HTML class immediately for all current pages
      document.documentElement.classList.add('popout-active');
      
      // Broadcast to other tabs/windows that popout is active
      try {
        window.dispatchEvent(new StorageEvent('storage', {
          key: 'ia_popout_active',
          newValue: 'true',
          oldValue: null
        }));
      } catch (e) {
        console.warn('Could not broadcast popout storage event:', e);
      }
    } else {
      localStorage.removeItem('ia_popout_active');
      localStorage.removeItem('ia_popout_timestamp');
      
      // Remove the HTML class
      document.documentElement.classList.remove('popout-active');
      
      // Broadcast to other tabs/windows that popout is inactive
      try {
        window.dispatchEvent(new StorageEvent('storage', {
          key: 'ia_popout_active',
          newValue: null,
          oldValue: 'true'
        }));
      } catch (e) {
        console.warn('Could not broadcast popout storage event:', e);
      }
    }
  }

  function monitorPopoutWindow(popoutWindow) {
    console.log('👀 Setting up enhanced popout window monitoring');
    
    // Check if the popout window is closed every 2 seconds
    const checkClosed = setInterval(() => {
      try {
        if (popoutWindow.closed) {
          console.log('🪟 Popout window detected as closed');
          clearInterval(checkClosed);
          
          // Only clear popout state if user explicitly closed the window
          // Don't clear if it was closed due to navigation or browser behavior
          const timeSincePopout = Date.now() - parseInt(localStorage.getItem('ia_popout_timestamp') || '0');
          const fiveMinutes = 5 * 60 * 1000;
          
          if (timeSincePopout > fiveMinutes) {
            console.log('⏰ Popout was open for more than 5 minutes, assuming user closed it');
            // Mark popout as inactive
            setPopoutActiveState(false);
            // Clear window reference
            delete window.popoutWindowRef;
            // Restore sidebar
            restoreSidebarFromPopout();
          } else {
            console.log('⚡ Popout closed quickly, likely due to navigation - keeping state active');
            // Keep the popout state active for a longer period
            // This handles cases where the popup closes due to browser navigation
          }
        }
      } catch (error) {
        console.warn('❌ Error checking popout window status:', error);
        // If we can't check the window status, assume it's still open
      }
    }, 2000); // Check every 2 seconds instead of 1 second
    
    // Also listen for beforeunload on the main window to clean up
    const cleanup = () => {
      console.log('🧹 Cleaning up popout monitoring due to main window unload');
      clearInterval(checkClosed);
      // Don't automatically clear popout state on main window navigation
      // The popout might still be open in another window
    };
    
    window.addEventListener('beforeunload', cleanup);
    
    // Store the cleanup function so we can call it if needed
    window.popoutCleanup = cleanup;
  }

  function checkAutoOpenPopout() {
    // Only auto-open on the main translator page, not on other pages
    const isMainPage = window.location.pathname === '/terminology/translate/' ||
                      window.location.pathname === '/';
    
    if (isMainPage && getPopoutPreference()) {
      const favorites = getFavorites();
      // Only auto-open if user has favorites and no popout is currently active
      if (favorites.length > 0 && !checkIfPopoutActive()) {
        // Delay slightly to ensure page is fully loaded
        setTimeout(() => {
          openFavoritesPopout();
        }, 1000);
      }
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
    setPopoutPreference
  };
})();