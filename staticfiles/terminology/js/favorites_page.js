/**
 * Enhanced Favorites Page JavaScript
 * Handles the standalone favorites page functionality
 */

const FavoritesPage = (() => {
  const STORAGE_KEY = 'ia_favorites_v1';
  const POPOUT_PREFERENCE_KEY = 'ia_favorites_popout_preference';
  const VIEW_PREFERENCE_KEY = 'ia_favorites_view_preference';
  
  let currentView = 'grid';
  let currentSort = 'newest';
  let currentFilter = '';
  let searchTerm = '';
  let selectedItems = new Set();
  let favorites = [];

  // DOM elements
  let elements = {};

  function initElements() {
    elements = {
      favoritesCount: document.getElementById('favoritesCount'),
      favoritesSearch: document.getElementById('favoritesSearch'),
      domainFilter: document.getElementById('domainFilter'),
      sortBy: document.getElementById('sortBy'),
      favoritesGrid: document.getElementById('favoritesGrid'),
      emptyState: document.getElementById('emptyState'),
      bulkActions: document.getElementById('bulkActions'),
      selectedCount: document.getElementById('selectedCount'),
      selectAllBtn: document.getElementById('selectAllBtn'),
      deselectAllBtn: document.getElementById('deselectAllBtn'),
      deleteSelectedBtn: document.getElementById('deleteSelectedBtn'),
      listViewBtn: document.getElementById('listViewBtn'),
      gridViewBtn: document.getElementById('gridViewBtn'),
      autoOpenToggle: document.getElementById('autoOpenToggle'),
      exportJsonBtn: document.getElementById('exportJsonBtn'),
      exportCsvBtn: document.getElementById('exportCsvBtn'),
      statisticsSection: document.getElementById('statisticsSection'),
      totalFavorites: document.getElementById('totalFavorites'),
      mostUsedDomain: document.getElementById('mostUsedDomain'),
      recentlyAdded: document.getElementById('recentlyAdded'),
      averagePerDay: document.getElementById('averagePerDay')
    };
  }

  function getFavorites() {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
    } catch {
      return [];
    }
  }

  function saveFavorites(favs) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(favs));
      // Notify other tabs
      window.dispatchEvent(new StorageEvent('storage', {
        key: STORAGE_KEY
      }));
      return true;
    } catch {
      console.error('Failed to save favorites');
      return false;
    }
  }

  function getPopoutPreference() {
    return localStorage.getItem(POPOUT_PREFERENCE_KEY) === 'true';
  }

  function setPopoutPreference(enabled) {
    localStorage.setItem(POPOUT_PREFERENCE_KEY, enabled.toString());
  }

  function getViewPreference() {
    return localStorage.getItem(VIEW_PREFERENCE_KEY) || 'grid';
  }

  function setViewPreference(view) {
    localStorage.setItem(VIEW_PREFERENCE_KEY, view);
  }

  function formatDate(timestamp) {
    if (!timestamp) return 'Unknown';
    const date = new Date(timestamp);
    const now = new Date();
    const diffTime = Math.abs(now - date);
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays === 1) return '1 day ago';
    if (diffDays < 7) return `${diffDays} days ago`;
    if (diffDays < 30) return `${Math.ceil(diffDays / 7)} weeks ago`;
    return date.toLocaleDateString();
  }

  function getDomainIcon(domain) {
    const icons = {
      medical: '🏥',
      diagnosis: '🏥',
      mesh: '🏥',
      medication: '💊',
      legal: '⚖️',
      financial: '💰',
      immigration: '🛂',
      government_agency: '🏛️',
      government: '🏛️',
      medicare: '🩺',
      l2: '📚',
      l3: '📖',
      llm: '📝',
      general: '📝'
    };
    return icons[domain] || '📝';
  }

  function getDomainColor(domain) {
    const colors = {
      medical: '#dc3545',
      diagnosis: '#dc3545',
      mesh: '#dc3545',
      medication: '#dc3545',
      legal: '#6f42c1',
      financial: '#fd7e14',
      immigration: '#20c997',
      government_agency: '#0d6efd',
      government: '#0d6efd',
      medicare: '#198754',
      l2: '#6c757d',
      l3: '#495057',
      llm: '#6c757d',
      general: '#6c757d'
    };
    return colors[domain] || '#6c757d';
  }

  function getDomainDisplayName(domain) {
    const displayNames = {
      medical: 'Medical',
      diagnosis: 'Medical',
      mesh: 'Medical',
      medication: 'Medical',
      legal: 'Legal',
      financial: 'Financial',
      immigration: 'Immigration',
      government_agency: 'Government',
      government: 'Government',
      medicare: 'Medicare',
      l2: 'Interpreter Basics 1',
      l3: 'Interpreter Basics 2',
      llm: 'General',
      general: 'General'
    };
    return displayNames[domain] || 'General';
  }

  function createFavoriteItem(favorite) {
    const isSelected = selectedItems.has(favorite.id);
    const domainIcon = getDomainIcon(favorite.domain);
    const domainColor = getDomainColor(favorite.domain);
    
    return `
      <div class="favorite-item-enhanced ${isSelected ? 'selected' : ''}" data-id="${favorite.id}">
        <div class="favorite-content">
          <div class="favorite-source">${favorite.src}</div>
          <div class="d-flex align-items-center">
            <span class="favorite-arrow">→</span>
            <div class="favorite-target">${favorite.tgt}</div>
          </div>
        </div>
        
        <div class="favorite-meta">
          <span class="favorite-domain" style="background-color: ${domainColor}">
            ${domainIcon} ${getDomainDisplayName(favorite.domain)}
          </span>
          <span class="favorite-date">${formatDate(favorite.timestamp)}</span>
        </div>
        
        <div class="favorite-actions">
          <div class="form-check favorite-checkbox">
            <input class="form-check-input" type="checkbox" id="fav-${favorite.id}" 
                   ${isSelected ? 'checked' : ''} onchange="FavoritesPage.toggleSelection('${favorite.id}')">
            <label class="form-check-label" for="fav-${favorite.id}">
              Select
            </label>
          </div>
          <button class="favorite-remove" onclick="FavoritesPage.removeFavorite('${favorite.id}')" 
                  title="Remove from favorites" aria-label="Remove ${favorite.src} from favorites">
            ✕
          </button>
        </div>
      </div>
    `;
  }

  function filterAndSortFavorites() {
    let filtered = [...favorites];

    // Apply search filter
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(fav => 
        fav.src.toLowerCase().includes(term) ||
        fav.tgt.toLowerCase().includes(term) ||
        (fav.domain || '').toLowerCase().includes(term)
      );
    }

    // Apply domain filter
    if (currentFilter) {
      filtered = filtered.filter(fav => 
        (fav.domain || '').toLowerCase() === currentFilter.toLowerCase()
      );
    }

    // Apply sorting
    switch (currentSort) {
      case 'newest':
        filtered.sort((a, b) => (b.timestamp || 0) - (a.timestamp || 0));
        break;
      case 'oldest':
        filtered.sort((a, b) => (a.timestamp || 0) - (b.timestamp || 0));
        break;
      case 'alphabetical':
        filtered.sort((a, b) => a.src.localeCompare(b.src));
        break;
      case 'usage':
        // For now, sort by timestamp as usage data isn't tracked yet
        filtered.sort((a, b) => (b.timestamp || 0) - (a.timestamp || 0));
        break;
    }

    return filtered;
  }

  function renderFavorites() {
    const filtered = filterAndSortFavorites();
    
    if (filtered.length === 0) {
      elements.emptyState.style.display = 'block';
      elements.favoritesGrid.style.display = 'none';
      elements.statisticsSection.style.display = 'none';
    } else {
      elements.emptyState.style.display = 'none';
      elements.favoritesGrid.style.display = 'block';
      elements.statisticsSection.style.display = 'block';
      
      elements.favoritesGrid.innerHTML = filtered.map(createFavoriteItem).join('');
      elements.favoritesGrid.className = `favorites-grid ${currentView === 'list' ? 'list-view' : ''}`;
    }

    updateCounts();
    updateStatistics();
  }

  function updateCounts() {
    const total = favorites.length;
    const selected = selectedItems.size;
    
    if (elements.favoritesCount) {
      elements.favoritesCount.textContent = total;
    }
    
    if (elements.selectedCount) {
      elements.selectedCount.textContent = selected;
    }
    
    if (elements.bulkActions) {
      elements.bulkActions.style.display = selected > 0 ? 'block' : 'none';
    }
  }

  function updateStatistics() {
    const total = favorites.length;
    
    // Calculate domain usage
    const domainCounts = {};
    favorites.forEach(fav => {
      const domain = getDomainDisplayName(fav.domain);
      domainCounts[domain] = (domainCounts[domain] || 0) + 1;
    });
    
    const mostUsed = Object.keys(domainCounts).reduce((a, b) =>
      domainCounts[a] > domainCounts[b] ? a : b, 'None'
    );
    
    // Calculate recent additions (last 7 days)
    const weekAgo = Date.now() - (7 * 24 * 60 * 60 * 1000);
    const recentCount = favorites.filter(fav => 
      (fav.timestamp || 0) > weekAgo
    ).length;
    
    // Calculate average per day (rough estimate)
    const oldestTimestamp = Math.min(...favorites.map(fav => fav.timestamp || Date.now()));
    const daysSinceFirst = Math.max(1, Math.ceil((Date.now() - oldestTimestamp) / (24 * 60 * 60 * 1000)));
    const avgPerDay = total > 0 ? (total / daysSinceFirst).toFixed(1) : 0;
    
    // Update statistics display
    if (elements.totalFavorites) elements.totalFavorites.textContent = total;
    if (elements.mostUsedDomain) elements.mostUsedDomain.textContent = mostUsed;
    if (elements.recentlyAdded) elements.recentlyAdded.textContent = recentCount;
    if (elements.averagePerDay) elements.averagePerDay.textContent = avgPerDay;
  }

  function toggleSelection(id) {
    if (selectedItems.has(id)) {
      selectedItems.delete(id);
    } else {
      selectedItems.add(id);
    }
    renderFavorites();
  }

  function selectAll() {
    const filtered = filterAndSortFavorites();
    filtered.forEach(fav => selectedItems.add(fav.id));
    renderFavorites();
  }

  function deselectAll() {
    selectedItems.clear();
    renderFavorites();
  }

  function deleteSelected() {
    if (selectedItems.size === 0) return;
    
    const message = `Delete ${selectedItems.size} selected favorite${selectedItems.size > 1 ? 's' : ''}? This cannot be undone.`;
    if (!confirm(message)) return;
    
    favorites = favorites.filter(fav => !selectedItems.has(fav.id));
    selectedItems.clear();
    
    if (saveFavorites(favorites)) {
      renderFavorites();
    }
  }

  function removeFavorite(id) {
    if (!confirm('Remove this favorite? This cannot be undone.')) return;
    
    favorites = favorites.filter(fav => fav.id !== id);
    selectedItems.delete(id);
    
    if (saveFavorites(favorites)) {
      renderFavorites();
    }
  }

  function setView(view) {
    currentView = view;
    setViewPreference(view);
    
    // Update button states
    elements.listViewBtn.classList.toggle('active', view === 'list');
    elements.gridViewBtn.classList.toggle('active', view === 'grid');
    
    renderFavorites();
  }

  function exportFavorites(format) {
    if (favorites.length === 0) {
      alert('No favorites to export.');
      return;
    }

    const data = {
      favorites: favorites,
      format: format,
      timestamp: new Date().toISOString()
    };

    fetch('/terminology/api/favorites/export/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data)
    })
    .then(response => {
      if (response.ok) {
        return response.blob();
      }
      throw new Error('Export failed');
    })
    .then(blob => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `interpascend_favorites.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    })
    .catch(error => {
      console.error('Export error:', error);
      alert('Export failed. Please try again.');
    });
  }

  function setupEventListeners() {
    // Search
    if (elements.favoritesSearch) {
      elements.favoritesSearch.addEventListener('input', (e) => {
        searchTerm = e.target.value;
        renderFavorites();
      });
    }

    // Filters
    if (elements.domainFilter) {
      elements.domainFilter.addEventListener('change', (e) => {
        currentFilter = e.target.value;
        renderFavorites();
      });
    }

    if (elements.sortBy) {
      elements.sortBy.addEventListener('change', (e) => {
        currentSort = e.target.value;
        renderFavorites();
      });
    }

    // View toggles
    if (elements.listViewBtn) {
      elements.listViewBtn.addEventListener('click', () => setView('list'));
    }
    if (elements.gridViewBtn) {
      elements.gridViewBtn.addEventListener('click', () => setView('grid'));
    }

    // Bulk actions
    if (elements.selectAllBtn) {
      elements.selectAllBtn.addEventListener('click', selectAll);
    }
    if (elements.deselectAllBtn) {
      elements.deselectAllBtn.addEventListener('click', deselectAll);
    }
    if (elements.deleteSelectedBtn) {
      elements.deleteSelectedBtn.addEventListener('click', deleteSelected);
    }

    // Auto-open toggle
    if (elements.autoOpenToggle) {
      elements.autoOpenToggle.checked = getPopoutPreference();
      elements.autoOpenToggle.addEventListener('change', (e) => {
        setPopoutPreference(e.target.checked);
      });
    }

    // Export buttons
    if (elements.exportJsonBtn) {
      elements.exportJsonBtn.addEventListener('click', (e) => {
        e.preventDefault();
        exportFavorites('json');
      });
    }
    if (elements.exportCsvBtn) {
      elements.exportCsvBtn.addEventListener('click', (e) => {
        e.preventDefault();
        exportFavorites('csv');
      });
    }

    // Cross-tab synchronization
    window.addEventListener('storage', (e) => {
      if (e.key === STORAGE_KEY) {
        favorites = getFavorites();
        renderFavorites();
      }
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
      if (e.ctrlKey || e.metaKey) {
        switch (e.key) {
          case 'f':
            e.preventDefault();
            elements.favoritesSearch?.focus();
            break;
          case 'a':
            if (e.shiftKey) {
              e.preventDefault();
              selectAll();
            }
            break;
          case 'Delete':
          case 'Backspace':
            if (selectedItems.size > 0) {
              e.preventDefault();
              deleteSelected();
            }
            break;
        }
      }
    });
  }

  function init() {
    initElements();
    favorites = getFavorites();
    currentView = getViewPreference();
    
    // Set initial view state
    setView(currentView);
    
    setupEventListeners();
    renderFavorites();
    
    // Remove loading class
    document.body.classList.remove('loading');
  }

  // Public API
  return {
    init,
    toggleSelection,
    removeFavorite,
    selectAll,
    deselectAll,
    deleteSelected,
    setView,
    exportFavorites
  };
})();

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', FavoritesPage.init);
} else {
  FavoritesPage.init();
}