import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      const response = await axios.get('/api/data');
      if (response.data.success) {
        setData(response.data.data);
        setLastUpdated(new Date().toLocaleTimeString());
        setError(null);
      } else {
        setError('Failed to fetch data');
      }
    } catch (err) {
      setError('Error connecting to backend: ' + err.message);
      console.error('Error fetching data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    // Auto-refresh every 5 seconds
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status) => {
    switch (status) {
      case 'running': return '#4CAF50';
      case 'warning': return '#FF9800';
      case 'error': return '#F44336';
      default: return '#9E9E9E';
    }
  };

  if (loading && !data) {
    return (
      <div className="app">
        <div className="loading">
          <h2>Loading...</h2>
          <p>Connecting to Raspberry Pi...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>Circuit Breakers Dashboard</h1>
        <div className="status-indicator">
          <div 
            className="status-dot" 
            style={{ backgroundColor: getStatusColor(data?.status) }}
          ></div>
          <span>Status: {data?.status || 'Unknown'}</span>
        </div>
        {lastUpdated && (
          <p className="last-updated">Last updated: {lastUpdated}</p>
        )}
      </header>

      {error && (
        <div className="error-message">
          <h3>Error</h3>
          <p>{error}</p>
          <button onClick={fetchData} className="retry-button">
            Retry
          </button>
        </div>
      )}

      {data && (
        <main className="dashboard">
          <div className="cards-grid">
            {/* Sensors Card */}
            <div className="card">
              <h2>Sensor Data</h2>
              <div className="sensor-grid">
                <div className="sensor-item">
                  <span className="sensor-label">Temperature</span>
                  <span className="sensor-value">{data.sensors?.temperature}°C</span>
                </div>
                <div className="sensor-item">
                  <span className="sensor-label">Humidity</span>
                  <span className="sensor-value">{data.sensors?.humidity}%</span>
                </div>
                <div className="sensor-item">
                  <span className="sensor-label">Pressure</span>
                  <span className="sensor-value">{data.sensors?.pressure} hPa</span>
                </div>
              </div>
            </div>

            {/* System Info Card */}
            <div className="card">
              <h2>System Information</h2>
              <div className="system-grid">
                <div className="system-item">
                  <span className="system-label">CPU Usage</span>
                  <div className="progress-bar">
                    <div 
                      className="progress-fill" 
                      style={{ width: `${data.system_info?.cpu_usage}%` }}
                    ></div>
                  </div>
                  <span className="system-value">{data.system_info?.cpu_usage}%</span>
                </div>
                <div className="system-item">
                  <span className="system-label">Memory Usage</span>
                  <div className="progress-bar">
                    <div 
                      className="progress-fill" 
                      style={{ width: `${data.system_info?.memory_usage}%` }}
                    ></div>
                  </div>
                  <span className="system-value">{data.system_info?.memory_usage}%</span>
                </div>
                <div className="system-item">
                  <span className="system-label">Disk Usage</span>
                  <div className="progress-bar">
                    <div 
                      className="progress-fill" 
                      style={{ width: `${data.system_info?.disk_usage}%` }}
                    ></div>
                  </div>
                  <span className="system-value">{data.system_info?.disk_usage}%</span>
                </div>
              </div>
            </div>
          </div>

          <div className="timestamp">
            <p>Data timestamp: {new Date(data.timestamp).toLocaleString()}</p>
          </div>
        </main>
      )}
    </div>
  );
}

export default App;
