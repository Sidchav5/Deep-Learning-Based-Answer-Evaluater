import React, { useEffect } from 'react';
import '../Toast.css';

function Toast({ message, type = 'info', duration = 6000, onClose }) {
  useEffect(() => {
    if (!message) return;

    let timer = null;
    
    // Progress messages don't auto-dismiss, others do
    if (type !== 'progress') {
      timer = setTimeout(() => {
        onClose();
      }, duration);
    }

    return () => {
      if (timer) clearTimeout(timer);
    };
  }, [message, type, duration, onClose]);

  const handleClose = () => {
    onClose();
  };

  if (!message) return null;

  return (
    <div 
      className={`toast toast-${type}`} 
      role="alert"
      aria-live={type === 'progress' ? 'polite' : 'assertive'}
    >
      <span className="toast-icon" aria-hidden="true">
        {type === 'success' && '✓'}
        {type === 'error' && '✕'}
        {type === 'info' && 'ℹ'}
        {type === 'progress' && '⟳'}
      </span>
      <span className="toast-message">{message}</span>
      {type !== 'progress' && (
        <button 
          className="toast-close"
          onClick={handleClose}
          aria-label="Close notification"
          style={{
            background: 'none',
            border: 'none',
            color: 'inherit',
            cursor: 'pointer',
            fontSize: '20px',
            padding: '0 4px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}
        >
          ✕
        </button>
      )}
    </div>
  );
}

export default Toast;
