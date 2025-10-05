import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './History.css';

function History() {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedEntry, setSelectedEntry] = useState(null);
  const [showModal, setShowModal] = useState(false);

  const fetchHistory = async () => {
    try {
      setLoading(true);
      const response = await axios.get('/api/history', { timeout: 10000 });
      if (response.data.success) {
        setHistory([...response.data.data.entries].reverse()); // Show newest first
        setError(null);
      } else {
        setError('Failed to fetch history');
      }
    } catch (err) {
      console.error('Error fetching history:', err);
      setError('Error loading history: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const clearHistory = async () => {
    if (window.confirm('Are you sure you want to clear all history? This action cannot be undone.')) {
      try {
        const response = await axios.post('/api/history/clear');
        if (response.data.success) {
          setHistory([]);
          setError(null);
        } else {
          setError('Failed to clear history');
        }
      } catch (err) {
        console.error('Error clearing history:', err);
        setError('Error clearing history: ' + err.message);
      }
    }
  };

  const openModal = (entry) => {
    setSelectedEntry(entry);
    setShowModal(true);
  };

  const closeModal = () => {
    setShowModal(false);
    setSelectedEntry(null);
  };

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleString();
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'printing': return '#4CAF50';
      case 'warning': return '#FF9800';
      case 'failed': return '#F44336';
      case 'idle': return '#9E9E9E';
      default: return '#9E9E9E';
    }
  };

  const getStatusEmoji = (binaryStatus) => {
    return binaryStatus === 1 ? '✅' : '❌';
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  if (loading) {
    return (
      <div className="history-container">
        <div className="loading">
          <h2>Loading History...</h2>
          <p>Fetching AI analysis history...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="history-container">
      <div className="history-header">
        <h1>📸 AI Analysis History</h1>
        <div className="history-controls">
          <button onClick={fetchHistory} className="refresh-btn">
            🔄 Refresh
          </button>
          <button onClick={clearHistory} className="clear-btn" disabled={history.length === 0}>
            🗑️ Clear History
          </button>
        </div>
      </div>

      {error && (
        <div className="error-message">
          <h3>Error</h3>
          <p>{error}</p>
          <button onClick={fetchHistory} className="retry-button">
            Retry
          </button>
        </div>
      )}

      {history.length === 0 ? (
        <div className="empty-history">
          <h2>📷 No History Yet</h2>
          <p>Start AI monitoring to see analysis history here.</p>
          <p>Each photo sent to Gemini will be saved with its response.</p>
        </div>
      ) : (
        <div className="history-grid">
          {history.map((entry) => (
            <div key={entry.id} className="history-card" onClick={() => openModal(entry)}>
              <div className="history-image">
                <img 
                  src={`/api/history/image/${entry.id}`}
                  alt={`Analysis ${entry.id}`}
                  loading="lazy"
                  onError={(e) => {
                    e.target.style.display = 'none';
                    e.target.nextSibling.style.display = 'flex';
                  }}
                />
                <div className="image-error" style={{ display: 'none' }}>
                  <span>📷 Image not available</span>
                </div>
                <div className="image-overlay">
                  <div className="status-badge" style={{ backgroundColor: getStatusColor(entry.print_status) }}>
                    {getStatusEmoji(entry.binary_status)} {entry.print_status.toUpperCase()}
                  </div>
                </div>
              </div>
              <div className="history-info">
                <div className="history-timestamp">
                  {formatTimestamp(entry.timestamp)}
                </div>
                <div className="history-stats">
                  <span className="confidence">Confidence: {Math.round(entry.confidence * 100)}%</span>
                  <span className="success">{entry.success ? '✅ Success' : '❌ Failed'}</span>
                </div>
                <div className="history-preview">
                  {entry.gemini_response ? entry.gemini_response.substring(0, 100) + '...' : 'No response'}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal for detailed view */}
      {showModal && selectedEntry && (
        <div className="modal-overlay" onClick={closeModal}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Analysis Details</h2>
              <button className="close-btn" onClick={closeModal}>×</button>
            </div>
            <div className="modal-body">
              <div className="modal-image">
                <img 
                  src={`/api/history/image/${selectedEntry.id}`}
                  alt={`Analysis ${selectedEntry.id}`}
                  onError={(e) => {
                    e.target.style.display = 'none';
                    e.target.nextSibling.style.display = 'flex';
                  }}
                />
                <div className="modal-image-error" style={{ display: 'none' }}>
                  <span>📷 Image not available</span>
                </div>
              </div>
              <div className="modal-info">
                <div className="info-section">
                  <h3>📅 Timestamp</h3>
                  <p>{formatTimestamp(selectedEntry.timestamp)}</p>
                </div>
                <div className="info-section">
                  <h3>📊 Analysis Results</h3>
                  <div className="analysis-results">
                    <div className="result-item">
                      <span className="label">Status:</span>
                      <span className="value" style={{ color: getStatusColor(selectedEntry.print_status) }}>
                        {getStatusEmoji(selectedEntry.binary_status)} {selectedEntry.print_status.toUpperCase()}
                      </span>
                    </div>
                    <div className="result-item">
                      <span className="label">Confidence:</span>
                      <span className="value">{Math.round(selectedEntry.confidence * 100)}%</span>
                    </div>
                    <div className="result-item">
                      <span className="label">Binary Status:</span>
                      <span className="value">{selectedEntry.binary_status === 1 ? '✅ Good' : '❌ Bad'}</span>
                    </div>
                    <div className="result-item">
                      <span className="label">Success:</span>
                      <span className="value">{selectedEntry.success ? '✅ Yes' : '❌ No'}</span>
                    </div>
                  </div>
                </div>
                <div className="info-section">
                  <h3>🤖 Gemini Response</h3>
                  <div className="gemini-response">
                    {selectedEntry.gemini_response || 'No response available'}
                  </div>
                </div>
                <div className="info-section">
                  <h3>📷 Image Info</h3>
                  <div className="image-info">
                    <div className="info-item">
                      <span className="label">Size:</span>
                      <span className="value">{(selectedEntry.image_size / 1024).toFixed(1)} KB</span>
                    </div>
                    <div className="info-item">
                      <span className="label">Filename:</span>
                      <span className="value">{selectedEntry.image_filename}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default History;
