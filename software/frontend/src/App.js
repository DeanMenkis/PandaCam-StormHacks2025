import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [printerStatus, setPrinterStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [aiStatus, setAiStatus] = useState(null);

  const fetchPrinterStatus = async (retryCount = 0) => {
    try {
      setLoading(true);
      const response = await axios.get('/api/printer/status', { timeout: 10000 });
      if (response.data.success) {
        const newStatus = response.data.data;
        
        // Debug logging for status changes
        if (printerStatus && (
          printerStatus.print_status !== newStatus.print_status ||
          printerStatus.is_running !== newStatus.is_running ||
          printerStatus.failure_detected !== newStatus.failure_detected
        )) {
          console.log('📊 Status Change Detected:', {
            old_print_status: printerStatus.print_status,
            new_print_status: newStatus.print_status,
            old_is_running: printerStatus.is_running,
            new_is_running: newStatus.is_running,
            old_failure: printerStatus.failure_detected,
            new_failure: newStatus.failure_detected,
            timestamp: new Date().toLocaleTimeString()
          });
        }
        
        setPrinterStatus(newStatus);
        setLastUpdated(new Date().toLocaleTimeString());
        setError(null);
      } else {
        setError('Failed to fetch printer status');
      }
    } catch (err) {
      console.error('Error fetching printer status:', err);
      
      // Retry logic for network issues and timeouts
      if (retryCount < 2 && (err.code === 'ECONNABORTED' || err.code === 'NETWORK_ERROR' || err.message.includes('timeout'))) {
        console.log(`🔄 Retrying printer status fetch (attempt ${retryCount + 1}) - ${err.message}`);
        setTimeout(() => fetchPrinterStatus(retryCount + 1), 2000);
        return;
      }
      
      // More user-friendly error messages
      if (err.message.includes('timeout')) {
        setError('Backend is slow to respond - retrying...');
      } else {
        setError('Error connecting to backend: ' + err.message);
      }
    } finally {
      setLoading(false);
    }
  };

  const fetchAiStatus = async (retryCount = 0) => {
    try {
      const response = await axios.get('/api/ai/status', { timeout: 10000 });
      if (response.data.success) {
        const newAiStatus = response.data.data;
        
        // Debug logging to track AI status updates
        if (aiStatus && newAiStatus.last_ai_analysis !== aiStatus.last_ai_analysis) {
          console.log('🔄 AI Status Updated:', {
            old_response: aiStatus.ai_response,
            new_response: newAiStatus.ai_response,
            old_timestamp: aiStatus.last_ai_analysis,
            new_timestamp: newAiStatus.last_ai_analysis,
            binary_status: newAiStatus.ai_binary_status
          });
        }
        
        setAiStatus(newAiStatus);
      }
    } catch (err) {
      console.error('Error fetching AI status:', err);
      
      // Retry logic for network issues and timeouts
      if (retryCount < 2 && (err.code === 'ECONNABORTED' || err.code === 'NETWORK_ERROR' || err.message.includes('timeout'))) {
        console.log(`🔄 Retrying AI status fetch (attempt ${retryCount + 1}) - ${err.message}`);
        setTimeout(() => fetchAiStatus(retryCount + 1), 2000);
        return;
      }
    }
  };

  const startAiMonitoring = async () => {
    try {
      setActionLoading(true);
      const response = await axios.post('/api/ai/start');
      if (response.data.success) {
        setAiStatus(response.data.data);
        setError(null);
      } else {
        setError('Failed to start AI monitoring');
      }
    } catch (err) {
      setError('Error starting AI monitoring: ' + err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const stopAiMonitoring = async () => {
    try {
      setActionLoading(true);
      const response = await axios.post('/api/ai/stop');
      if (response.data.success) {
        setAiStatus(response.data.data);
        setError(null);
      } else {
        setError('Failed to stop AI monitoring');
      }
    } catch (err) {
      setError('Error stopping AI monitoring: ' + err.message);
    } finally {
      setActionLoading(false);
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
    fetchAiStatus();
    // Auto-refresh every 3 seconds to balance responsiveness and performance
    const interval = setInterval(() => {
      fetchPrinterStatus();
      fetchAiStatus();
    }, 3000);
    return () => clearInterval(interval);
  // eslint-disable-next-line react-hooks/exhaustive-deps
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
                {/* AI Binary Status Indicator */}
                {aiStatus?.ai_monitoring_active && aiStatus?.ai_binary_status !== undefined && (
                  <div className="ai-binary-indicator">
                    <span className="ai-binary-label">AI Assessment:</span>
                    <span className={`ai-binary-value ${aiStatus.ai_binary_status === 1 ? 'good' : 'bad'}`}>
                      {aiStatus.ai_binary_status === 1 ? '✅ GOOD' : '❌ BAD'}
                    </span>
                  </div>
                )}
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

          {/* Camera Control */}
          <div className="control-card">
            <h2>Camera Control</h2>
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
            
          </div>
        </div>

        {/* AI Monitoring Section */}
        <div className="ai-monitoring-section">
          <div className="ai-status-card">
            <h2>🤖 AI Monitoring</h2>
            <div className="ai-status-content">
              <div className="ai-status-indicator">
                <div 
                  className="ai-status-dot" 
                  style={{ backgroundColor: aiStatus?.ai_monitoring_active ? '#4CAF50' : '#9E9E9E' }}
                ></div>
                <span className="ai-status-text">
                  {aiStatus?.ai_monitoring_active ? 'Active' : 'Inactive'}
                </span>
              </div>
              
              <div className="ai-controls">
                <button 
                  className={`control-btn start-btn ${aiStatus?.ai_monitoring_active ? 'disabled' : ''}`}
                  onClick={startAiMonitoring}
                  disabled={aiStatus?.ai_monitoring_active || actionLoading}
                >
                  {actionLoading ? 'Starting...' : 'Start AI Monitoring'}
                </button>
                <button 
                  className={`control-btn stop-btn ${!aiStatus?.ai_monitoring_active ? 'disabled' : ''}`}
                  onClick={stopAiMonitoring}
                  disabled={!aiStatus?.ai_monitoring_active || actionLoading}
                >
                  {actionLoading ? 'Stopping...' : 'Stop AI Monitoring'}
                </button>
              </div>

              {/* AI Analysis Results */}
              {aiStatus?.ai_response && (
                <div className="ai-analysis-card">
                  <h3>Latest AI Analysis 
                    {aiStatus.last_ai_analysis && (
                      <span className="update-indicator">
                        • Updated {new Date(aiStatus.last_ai_analysis).toLocaleTimeString()}
                      </span>
                    )}
                  </h3>
                  <div className="ai-response">
                    <p>{aiStatus.ai_response}</p>
                  </div>
                  <div className="ai-metadata">
                    <span className="ai-binary-status">
                      Binary Status: {aiStatus.ai_binary_status === 1 ? '✅ 1 (Good)' : '❌ 0 (Bad)'}
                    </span>
                    <span className="ai-confidence">
                      Confidence: {Math.round((aiStatus.ai_confidence || 0) * 100)}%
                    </span>
                    {aiStatus.last_ai_analysis && (
                      <span className="ai-timestamp">
                        {new Date(aiStatus.last_ai_analysis).toLocaleString()}
                      </span>
                    )}
                  </div>
                </div>
              )}

              </div>
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
