// terminology/static/terminology/js/background_updater.js

function updateBackground() {
  // Determine local hour
  const hour = new Date().getHours();
  let timeClass;

  if (hour >= 5 && hour < 12) {
    timeClass = 'morning';
  } else if (hour >= 12 && hour < 17) {
    timeClass = 'afternoon';
  } else if (hour >= 17 && hour < 20) {
    timeClass = 'evening';
  } else {
    timeClass = 'night';
  }

  // Only update body class if it's different to prevent unnecessary changes
  const currentTimeClasses = ['morning', 'afternoon', 'evening', 'night'];
  const hasCorrectClass = document.body.classList.contains(timeClass);
  
  if (!hasCorrectClass) {
    document.body.classList.remove(...currentTimeClasses);
    document.body.classList.add(timeClass);
  }

  // ✅ Define icon map BEFORE using it
  const iconMap = {
    morning:   '/static/terminology/images/home-light.svg',
    afternoon: '/static/terminology/images/home-light.svg',
    evening:   '/static/terminology/images/home-light.svg',
    night:     '/static/terminology/images/home-dark.svg'
  };

  // ✅ Update SVG icon if present
  const logoImg = document.getElementById('day-icon');
  if (logoImg && iconMap[timeClass]) {
    logoImg.src = iconMap[timeClass];
  }

  // ✅ Update PNG-based home button icon
  const homeButtonIcon = document.getElementById('home-button-icon');
  if (homeButtonIcon) {
    if (timeClass === 'afternoon' || timeClass === 'evening') {
      homeButtonIcon.src = '/static/terminology/images/home-dark_transparent.png';
    } else {
      homeButtonIcon.src = '/static/terminology/images/home-light_transparent.png';
    }
  }

  console.log('Background and icon updated. Current timeClass:', timeClass);
}

// Run on page load
document.addEventListener('DOMContentLoaded', updateBackground);

// Refresh every 15 minutes
setInterval(updateBackground, 15 * 60 * 1000);
