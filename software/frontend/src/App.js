import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [printerStatus, setPrinterStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);

  const fetchPrinterStatus = async () => {
    try {
      setLoading(true);
      const response = await axios.get('/api/printer/status');
      if (response.data.success) {
        setPrinterStatus(response.data.data);
        setLastUpdated(new Date().toLocaleTimeString());
        setError(null);
      } else {
        setError('Failed to fetch printer status');
      }
    } catch (err) {
      setError('Error connecting to backend: ' + err.message);
      console.error('Error fetching printer status:', err);
    } finally {
      setLoading(false);
    }
  };

  const startPrinter = async () => {
    try {
      setActionLoading(true);
      const response = await axios.post('/api/printer/start');
      if (response.data.success) {
        setPrinterStatus(response.data.data);
        setError(null);
      } else {
        setError('Failed to start printer monitoring');
      }
    } catch (err) {
      setError('Error starting printer: ' + err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const stopPrinter = async () => {
    try {
      setActionLoading(true);
      const response = await axios.post('/api/printer/stop');
      if (response.data.success) {
        setPrinterStatus(response.data.data);
        setError(null);
      } else {
        setError('Failed to stop printer monitoring');
      }
    } catch (err) {
      setError('Error stopping printer: ' + err.message);
    } finally {
      setActionLoading(false);
    }
  };

  useEffect(() => {
    fetchPrinterStatus();
    // Auto-refresh every 3 seconds
    const interval = setInterval(fetchPrinterStatus, 3000);
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (isRunning, failureDetected) => {
    if (failureDetected) return '#F44336'; // Red for failure
    if (isRunning) return '#4CAF50'; // Green for running
    return '#9E9E9E'; // Gray for stopped
  };

  const getStatusText = (isRunning, failureDetected) => {
    if (failureDetected) return 'FAILURE DETECTED';
    if (isRunning) return 'MONITORING';
    return 'STOPPED';
  };

  const getPrintStatusColor = (printStatus) => {
    switch (printStatus) {
      case 'printing': return '#2196F3'; // Blue
      case 'paused': return '#FF9800'; // Orange
      case 'completed': return '#4CAF50'; // Green
      case 'failed': return '#F44336'; // Red
      default: return '#9E9E9E'; // Gray for idle
    }
  };

  const getPrintStatusText = (printStatus) => {
    switch (printStatus) {
      case 'printing': return 'PRINTING';
      case 'paused': return 'PAUSED';
      case 'completed': return 'COMPLETED';
      case 'failed': return 'FAILED';
      default: return 'IDLE';
    }
  };

  const formatTime = (minutes) => {
    if (!minutes || minutes === 0) return '0m';
    const hours = Math.floor(minutes / 60);
    const mins = Math.floor(minutes % 60);
    return hours > 0 ? `${hours}h ${mins}m` : `${mins}m`;
  };

  if (loading && !printerStatus) {
    return (
      <div className="app">
        <div className="loading">
          <h2>Loading...</h2>
          <p>Connecting to 3D Printer Monitoring System...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="app">
      {/* Animated Snow Background */}
      <div className="snow-container">
        <div className="snowflake"></div>
        <div className="snowflake"></div>
        <div className="snowflake"></div>
        <div className="snowflake"></div>
        <div className="snowflake"></div>
        <div className="snowflake"></div>
        <div className="snowflake"></div>
        <div className="snowflake"></div>
        <div className="snowflake"></div>
        <div className="snowflake"></div>
        <div className="snowflake"></div>
        <div className="snowflake"></div>
        <div className="snowflake"></div>
        <div className="snowflake"></div>
        <div className="snowflake"></div>
        <div className="snowflake"></div>
        <div className="snowflake"></div>
        <div className="snowflake"></div>
        <div className="snowflake"></div>
        <div className="snowflake"></div>
        <div className="snowflake"></div>
        <div className="snowflake"></div>
        <div className="snowflake"></div>
        <div className="snowflake"></div>
        <div className="snowflake"></div>
        <div className="snowflake"></div>
        <div className="snowflake"></div>
        <div className="snowflake"></div>
        <div className="snowflake"></div>
        <div className="snowflake"></div>
        <div className="snowflake"></div>
        <div className="snowflake"></div>
        <div className="snowflake"></div>
        <div className="snowflake"></div>
        <div className="snowflake"></div>
        <div className="snowflake"></div>
        <div className="snowflake"></div>
        <div className="snowflake"></div>
        <div className="snowflake"></div>
        <div className="snowflake"></div>
        <div className="snowflake"></div>
        <div className="snowflake"></div>
      </div>
      
      <header className="app-header">
        <h1>3D Printer Monitoring System</h1>
        <div className="status-indicator">
          <div 
            className="status-dot" 
            style={{ backgroundColor: getStatusColor(printerStatus?.is_running, printerStatus?.failure_detected) }}
          ></div>
          <span>Status: {getStatusText(printerStatus?.is_running, printerStatus?.failure_detected)}</span>
        </div>
        {lastUpdated && (
          <p className="last-updated">Last updated: {lastUpdated}</p>
        )}
      </header>

      {error && (
        <div className="error-message">
          <h3>Error</h3>
          <p>{error}</p>
          <button onClick={fetchPrinterStatus} className="retry-button">
            Retry
          </button>
        </div>
      )}

      <main className="dashboard">
        <div className="main-grid">
          {/* Video Stream */}
          <div className="video-card">
            <h2>Live Camera Feed</h2>
            <div className="video-container">
              {printerStatus?.is_running ? (
                <img 
                  src="/video_feed" 
                  alt="3D Printer Camera Feed"
                  className="video-stream"
                />
              ) : (
                <div className="video-placeholder">
                  <p>Camera feed will appear when monitoring starts</p>
                </div>
              )}
            </div>
          </div>

          {/* Print Status */}
          <div className="print-status-card">
            <h2>Print Status</h2>
            <div className="print-status-content">
              <div className="print-status-indicator">
                <div 
                  className="print-status-dot" 
                  style={{ backgroundColor: getPrintStatusColor(printerStatus?.print_status) }}
                ></div>
                <span className="print-status-text">
                  {getPrintStatusText(printerStatus?.print_status)}
                </span>
              </div>
              
              {printerStatus?.print_status === 'printing' && (
                <div className="print-progress-section">
                  <div className="progress-info">
                    <span className="progress-label">Progress</span>
                    <span className="progress-percentage">{printerStatus?.print_progress || 0}%</span>
                  </div>
                  <div className="progress-bar-container">
                    <div 
                      className="progress-bar-fill" 
                      style={{ width: `${printerStatus?.print_progress || 0}%` }}
                    ></div>
                  </div>
                  <div className="time-info">
                    <div className="time-item">
                      <span className="time-label">Elapsed:</span>
                      <span className="time-value">{formatTime(printerStatus?.print_time_elapsed)}</span>
                    </div>
                    <div className="time-item">
                      <span className="time-label">Remaining:</span>
                      <span className="time-value">{formatTime(printerStatus?.print_time_remaining)}</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Defect Detection Control */}
          <div className="control-card">
            <h2>Defect Detection</h2>
            <div className="control-buttons">
              <button 
                className={`control-btn start-btn ${printerStatus?.is_running ? 'disabled' : ''}`}
                onClick={startPrinter}
                disabled={printerStatus?.is_running || actionLoading}
              >
                {actionLoading ? 'Starting...' : 'Start Monitoring'}
              </button>
              <button 
                className={`control-btn stop-btn ${!printerStatus?.is_running ? 'disabled' : ''}`}
                onClick={stopPrinter}
                disabled={!printerStatus?.is_running || actionLoading}
              >
                {actionLoading ? 'Stopping...' : 'Stop Monitoring'}
              </button>
            </div>
            
            {/* Failure Alert */}
            {printerStatus?.failure_detected && (
              <div className="failure-alert">
                <h3>⚠️ PRINT FAILURE DETECTED</h3>
                <p>Last failure: {printerStatus.last_failure_time ? new Date(printerStatus.last_failure_time).toLocaleString() : 'Unknown'}</p>
              </div>
            )}
          </div>
        </div>

        {/* Status Information */}
        <div className="status-info">
          <div className="status-item">
            <span className="status-label">Monitoring:</span>
            <span className={`status-value ${printerStatus?.is_monitoring ? 'active' : 'inactive'}`}>
              {printerStatus?.is_monitoring ? 'Active' : 'Inactive'}
            </span>
          </div>
          <div className="status-item">
            <span className="status-label">Video Stream:</span>
            <span className={`status-value ${printerStatus?.video_stream_active ? 'active' : 'inactive'}`}>
              {printerStatus?.video_stream_active ? 'Active' : 'Inactive'}
            </span>
          </div>
          <div className="status-item">
            <span className="status-label">System Time:</span>
            <span className="status-value">
              {printerStatus?.timestamp ? new Date(printerStatus.timestamp).toLocaleString() : 'Unknown'}
            </span>
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
