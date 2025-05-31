import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'

// Initialize the application
function initializeApp() {
  const root = ReactDOM.createRoot(document.getElementById('root'));

  // Remove initial loader when React takes over
  const initialLoader = document.getElementById('initialLoader');
  if (initialLoader) {
    setTimeout(() => {
      initialLoader.style.opacity = '0';
      setTimeout(() => {
        initialLoader.style.display = 'none';
      }, 300);
    }, 800); // Increased delay to ensure App has rendered
  }

  root.render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  );
}

// Wait for DOM to be ready, then initialize
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeApp);
} else {
  initializeApp();
}