import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';
import History from './History';
import ErrorBoundary from './ErrorBoundary';

function App() {
  const [printerStatus, setPrinterStatus] = useState(null);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [aiStatus, setAiStatus] = useState(null);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [countdown, setCountdown] = useState(0);
  const [interval, setInterval] = useState(15); // Default 15 seconds
  
  // White balance controls
  const [whiteBalance, setWhiteBalance] = useState({
    red: 1.8,
    blue: 1.0,
    auto: true
  });

  // Use countdown from backend (already calculated and synced)
  const getCountdown = (aiStatus) => {
    if (!aiStatus || !aiStatus.ai_monitoring_active) {
      return 0;
    }
    return aiStatus.ai_countdown || 0;
  };

  // Smooth countdown timer
  useEffect(() => {
    if (!aiStatus || !aiStatus.ai_monitoring_active) {
      setCountdown(0);
      return;
    }

    // Always use the backend countdown value directly
    const backendCountdown = getCountdown(aiStatus);
    setCountdown(backendCountdown);

    // Run smooth countdown that syncs with backend
    const countdownInterval = setInterval(() => {
      setCountdown(prev => {
        // Get fresh countdown from backend
        const freshCountdown = getCountdown(aiStatus);
        
        // If backend countdown is different, use it
        if (freshCountdown !== prev) {
          return freshCountdown;
        }
        
        // Otherwise, count down normally
        return Math.max(0, prev - 1);
      });
    }, 1000);

    return () => clearInterval(countdownInterval);
  }, [aiStatus?.ai_monitoring_active, aiStatus?.ai_countdown, aiStatus]);

  const setAiInterval = async (intervalSeconds) => {
    try {
      setActionLoading(true);
      const response = await axios.post('/api/ai/interval', { interval: intervalSeconds }, { timeout: 10000 });
      if (response.data.success) {
        setInterval(intervalSeconds);
        setError(null);
        // Refresh printer status to get updated data
        fetchPrinterStatus();
      } else {
        setError('Failed to set interval: ' + (response.data.error || 'Unknown error'));
      }
    } catch (err) {
      setError('Error setting interval: ' + err.message);
    } finally {
      setActionLoading(false);
    }
  };


  const pauseAiMonitoring = async () => {
    try {
      setActionLoading(true);
      const response = await axios.post('/api/ai/pause', {}, { timeout: 10000 });
      if (response.data.success) {
        setError(null);
      } else {
        setError('Failed to pause AI monitoring: ' + (response.data.error || 'Unknown error'));
      }
    } catch (err) {
      setError('Error pausing AI monitoring: ' + err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const resumeAiMonitoring = async () => {
    try {
      setActionLoading(true);
      const response = await axios.post('/api/ai/resume', {}, { timeout: 10000 });
      if (response.data.success) {
        setError(null);
      } else {
        setError('Failed to resume AI monitoring: ' + (response.data.error || 'Unknown error'));
      }
    } catch (err) {
      setError('Error resuming AI monitoring: ' + err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const fetchPrinterStatus = async () => {
    try {
      console.log('📡 Fetching printer status...');
      const response = await axios.get('/api/printer/status', { timeout: 5000 });
      
      if (response.data.success) {
        const newStatus = response.data.data;
        console.log('📊 Received status:', {
          print_status: newStatus.print_status,
          ai_binary_status: newStatus.ai_binary_status,
          is_running: newStatus.is_running
        });
        
        setPrinterStatus(newStatus);
        setLastUpdated(new Date().toLocaleTimeString());
        setError(null);
      }
    } catch (err) {
      console.error('❌ Error fetching status:', err.message);
      setError('Failed to fetch status: ' + err.message);
    }
  };

  // Removed fetchAiStatus - we get all data from printer status endpoint


  const startAiMonitoring = async () => {
    try {
      setActionLoading(true);
      const response = await axios.post('/api/ai/start', {}, { timeout: 30000 }); // 30s timeout for AI start
      if (response.data.success) {
        setAiStatus(response.data.data);
        setError(null);
      } else {
        setError('Failed to start AI monitoring: ' + (response.data.error || 'Unknown error'));
      }
    } catch (err) {
      if (err.code === 'ECONNABORTED' || err.message.includes('timeout')) {
        setError('AI monitoring start timed out - the system may be busy. Please try again.');
      } else {
        setError('Error starting AI monitoring: ' + err.message);
      }
    } finally {
      setActionLoading(false);
    }
  };

  const stopAiMonitoring = async () => {
    try {
      setActionLoading(true);
      const response = await axios.post('/api/ai/stop', {}, { timeout: 15000 }); // 15s timeout for AI stop
      if (response.data.success) {
        setAiStatus(response.data.data);
        setError(null);
      } else {
        setError('Failed to stop AI monitoring: ' + (response.data.error || 'Unknown error'));
      }
    } catch (err) {
      if (err.code === 'ECONNABORTED' || err.message.includes('timeout')) {
        setError('AI monitoring stop timed out - the system may be busy. Please try again.');
      } else {
        setError('Error stopping AI monitoring: ' + err.message);
      }
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
    // Initial fetch
    fetchPrinterStatus();
    
    // Use recursive setTimeout instead of setInterval (more reliable during video streaming)
    let isActive = true;
    
    const scheduleNext = () => {
      if (isActive) {
        setTimeout(() => {
          if (isActive) {
            console.log('📡 Auto polling - fetching printer status');
            fetchPrinterStatus();
            scheduleNext(); // Schedule the next call
          }
        }, 5000);
      }
    };
    
    // Start the polling cycle
    scheduleNext();
    
    return () => {
      isActive = false; // Stop the polling when component unmounts
    };
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

  const getPrintStatusColor = (printStatus, aiBinaryStatus) => {
    // Convert to number to handle string values
    const binaryStatus = Number(aiBinaryStatus);
    
    console.log(`🎨 Color calc: status=${printStatus}, ai=${binaryStatus}`);
    
    // If AI says it's good (binary_status === 1), show green regardless of print status
    if (binaryStatus === 1) {
      console.log('🎨 → GREEN (AI good)');
      return '#4CAF50'; // Green for good AI assessment
    }
    
    // Otherwise, use the normal color logic
    let color;
    switch (printStatus) {
      case 'printing': color = '#2196F3'; break; // Blue
      case 'paused': color = '#FF9800'; break; // Orange
      case 'completed': color = '#4CAF50'; break; // Green
      case 'failed': color = '#F44336'; break; // Red
      case 'warning': color = '#FF9800'; break; // Orange for warnings
      default: color = '#9E9E9E'; break; // Gray for idle
    }
    
    console.log(`🎨 → ${color} (${printStatus})`);
    return color;
  };

  const getPrintStatusText = (printStatus, aiBinaryStatus) => {
    // Convert to number to handle string values
    const binaryStatus = Number(aiBinaryStatus);
    
    // If AI says it's good, show a positive status
    if (binaryStatus === 1) {
      switch (printStatus) {
        case 'printing': return 'PRINTING ✅';
        case 'idle': return 'IDLE ✅';
        default: return 'GOOD ✅';
      }
    }
    
    // Otherwise, use the normal text logic
    switch (printStatus) {
      case 'printing': return 'PRINTING';
      case 'paused': return 'PAUSED';
      case 'completed': return 'COMPLETED';
      case 'failed': return 'FAILED';
      case 'warning': return 'WARNING';
      default: return 'IDLE';
    }
  };

  if (!printerStatus) {
    return (
      <div className="app">
        <div className="loading">
          <h2>Loading...</h2>
          <p>Connecting to 3D Printer Monitoring System...</p>
        </div>
      </div>
    );
  }

  // Show History component if History tab is active
  if (activeTab === 'history') {
    return (
      <div className="app">
        <div className="tab-navigation">
          <button 
            className={`tab-btn ${activeTab === 'dashboard' ? 'active' : ''}`}
            onClick={() => setActiveTab('dashboard')}
          >
            🏠 Dashboard
          </button>
          <button 
            className={`tab-btn ${activeTab === 'history' ? 'active' : ''}`}
            onClick={() => setActiveTab('history')}
          >
            📸 History
          </button>
        </div>
        <ErrorBoundary>
          <History />
        </ErrorBoundary>
      </div>
    );
  }

  // White balance functions
  const updateWhiteBalance = async (red, blue) => {
    try {
      await axios.post('/api/camera/wb', { red, blue });
      setWhiteBalance(prev => ({ ...prev, red, blue, auto: false }));
      console.log(`White balance updated: R=${red}, B=${blue}`);
    } catch (error) {
      console.error('Error updating white balance:', error);
    }
  };

  const resetWhiteBalance = async () => {
    try {
      await axios.post('/api/camera/wb/reset');
      setWhiteBalance(prev => ({ ...prev, auto: true }));
      console.log('White balance reset to auto');
    } catch (error) {
      console.error('Error resetting white balance:', error);
    }
  };

  return (
    <ErrorBoundary>
      <div className="app">
        {/* Tab Navigation */}
        <div className="tab-navigation">
          <button 
            className={`tab-btn ${activeTab === 'dashboard' ? 'active' : ''}`}
            onClick={() => setActiveTab('dashboard')}
          >
            🏠 Dashboard
          </button>
          <button 
            className={`tab-btn ${activeTab === 'history' ? 'active' : ''}`}
            onClick={() => setActiveTab('history')}
          >
            📸 History
          </button>
        </div>

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
          <p className="last-updated">
            Last updated: {lastUpdated}
            <button 
              onClick={fetchPrinterStatus} 
              style={{marginLeft: '10px', padding: '2px 8px', fontSize: '12px'}}
            >
              🔄 Test Update
            </button>
          </p>
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
        {/* Row 1: Print Status and Camera Controls */}
        <div className="top-row">
          {/* Print Status */}
          <div className="print-status-card">
            <h2>Print Status</h2>
            <div className="print-status-content">
              <div className="print-status-indicator">
                <div 
                  className="print-status-dot" 
                  style={{ backgroundColor: getPrintStatusColor(printerStatus?.print_status, printerStatus?.ai_binary_status) }}
                ></div>
                <span className="print-status-text">
                  {getPrintStatusText(printerStatus?.print_status, printerStatus?.ai_binary_status)}
                </span>
                {/* AI Binary Status Indicator */}
                {printerStatus?.ai_binary_status !== undefined && printerStatus?.ai_response && printerStatus.ai_response !== "No analysis yet." && (
                  <div className="ai-binary-indicator">
                    <span className="ai-binary-label">AI Assessment:</span>
                    <span className={`ai-binary-value ${printerStatus.ai_binary_status === 1 ? 'good' : 'bad'}`}>
                      {printerStatus.ai_binary_status === 1 ? '✅ GOOD' : '❌ BAD'}
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

        {/* Row 2: Live Camera Feed */}
        <div className="video-card">
          <h2>Live Camera Feed</h2>
          
          {/* Compact White Balance Controls */}
          <div className="white-balance-controls">
            <div className="wb-control-group">
              <label>Red: {whiteBalance.red.toFixed(1)}</label>
              <input
                type="range"
                min="0.5"
                max="3.0"
                step="0.1"
                value={whiteBalance.red}
                onChange={(e) => updateWhiteBalance(parseFloat(e.target.value), whiteBalance.blue)}
                className="wb-slider red-slider"
              />
            </div>
            <div className="wb-control-group">
              <label>Blue: {whiteBalance.blue.toFixed(1)}</label>
              <input
                type="range"
                min="0.5"
                max="3.0"
                step="0.1"
                value={whiteBalance.blue}
                onChange={(e) => updateWhiteBalance(whiteBalance.red, parseFloat(e.target.value))}
                className="wb-slider blue-slider"
              />
            </div>
            <button
              onClick={resetWhiteBalance}
              className={`wb-reset-btn ${whiteBalance.auto ? 'active' : ''}`}
              title="Reset to Auto White Balance"
            >
              {whiteBalance.auto ? '🎨 Auto' : '🔄 Reset'}
            </button>
          </div>
          
          <div className="video-container">
            {printerStatus?.is_running ? (
              <>
                <video 
                  src="/h264_stream" 
                  autoPlay 
                  muted 
                  playsInline
                  className="video-stream"
                  style={{display: 'block'}}
                  onError={(e) => {
                    e.target.style.display = 'none';
                    e.target.nextSibling.style.display = 'block';
                  }}
                />
                <img 
                  src="/video_feed" 
                  alt="3D Printer Camera Feed"
                  className="video-stream"
                  style={{display: 'none'}}
                  onError={(e) => {
                    e.target.style.display = 'none';
                    e.target.nextSibling.style.display = 'block';
                  }}
                />
              </>
            ) : (
              <div className="video-placeholder">
                <p>Camera feed will appear when monitoring starts</p>
              </div>
            )}
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
                {aiStatus?.ai_monitoring_active && (
                  <div className="ai-countdown">
                    <span className="countdown-label">
                      {aiStatus.ai_monitoring_paused ? 'PAUSED' : 
                       aiStatus.ai_process_status === 'analyzing' ? 'Analyzing now...' :
                       countdown > 0 ? 'Next analysis in:' : 'Ready...'}
                    </span>
                    <span className={`countdown-timer ${aiStatus.ai_monitoring_paused ? 'paused' : aiStatus.ai_process_status === 'analyzing' ? 'analyzing' : ''}`}>
                      {aiStatus.ai_monitoring_paused ? '⏸️' : 
                       aiStatus.ai_process_status === 'analyzing' ? '⏳' :
                       countdown > 0 ? `${countdown}s` : '✓'}
                    </span>
                  </div>
                )}
              </div>
              
              {/* AI Process Status */}
              {aiStatus?.ai_monitoring_active && (
                <div className="ai-process-status">
                  <div className="process-status-item">
                    <span className="process-label">Status:</span>
                    <span className={`process-value ${aiStatus.ai_process_status || 'idle'}`}>
                      {(aiStatus.ai_process_status || 'idle').replace('_', ' ').toUpperCase()}
                    </span>
                  </div>
                  <div className="process-status-item">
                    <span className="process-label">Analyses:</span>
                    <span className="process-value">{aiStatus.ai_analysis_count || 0}</span>
                  </div>
                  <div className="process-status-item">
                    <span className="process-label">Success Rate:</span>
                    <span className="process-value">
                      {Math.round((aiStatus.ai_success_rate || 0) * 100)}%
                    </span>
                  </div>
                </div>
              )}
              
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
                {aiStatus?.ai_monitoring_active && (
                  <>
                    <button 
                      className={`control-btn pause-btn ${aiStatus?.ai_monitoring_paused ? 'disabled' : ''}`}
                      onClick={pauseAiMonitoring}
                      disabled={aiStatus?.ai_monitoring_paused || actionLoading}
                    >
                      {actionLoading ? 'Pausing...' : '⏸️ Pause'}
                    </button>
                    <button 
                      className={`control-btn resume-btn ${!aiStatus?.ai_monitoring_paused ? 'disabled' : ''}`}
                      onClick={resumeAiMonitoring}
                      disabled={!aiStatus?.ai_monitoring_paused || actionLoading}
                    >
                      {actionLoading ? 'Resuming...' : '▶️ Resume'}
                    </button>
                    <div className="interval-dropdown">
                      <select
                        value={interval}
                        onChange={(e) => setAiInterval(parseInt(e.target.value))}
                        disabled={!aiStatus?.ai_monitoring_paused || actionLoading}
                        className="interval-select"
                      >
                        <option value={5}>5s</option>
                        <option value={10}>10s</option>
                        <option value={15}>15s</option>
                        <option value={25}>25s</option>
                        <option value={30}>30s</option>
                        <option value={45}>45s</option>
                        <option value={60}>60s</option>
                      </select>
                    </div>
                  </>
                )}
              </div>

              {/* AI Analysis Results */}
              {(() => {
                const shouldShow = aiStatus?.ai_response && aiStatus.ai_response !== "No analysis yet.";
                console.log('🔍 AI Analysis Display Check:', {
                  has_aiStatus: !!aiStatus,
                  has_response: !!aiStatus?.ai_response,
                  response_value: aiStatus?.ai_response,
                  is_not_default: aiStatus?.ai_response !== "No analysis yet.",
                  should_show: shouldShow
                });
                return shouldShow;
              })() && (
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

              {/* AI Response Display */}
              {(() => {
                const shouldShow = aiStatus?.ai_response && aiStatus.ai_response !== "No analysis yet.";
                console.log('🔍 AI Response Display Check:', {
                  has_aiStatus: !!aiStatus,
                  has_response: !!aiStatus?.ai_response,
                  response_value: aiStatus?.ai_response,
                  is_not_default: aiStatus?.ai_response !== "No analysis yet.",
                  should_show: shouldShow
                });
                return shouldShow;
              })() && (
                <div className="ai-prompt-card">
                  <h3>🤖 Gemini AI Response</h3>
                  <div className="ai-prompt-content">
                    <pre>{aiStatus.ai_response}</pre>
                  </div>
                </div>
              )}

              </div>
            </div>
          </div>

      </main>
      </div>


    </ErrorBoundary>
  );
}

export default App;
