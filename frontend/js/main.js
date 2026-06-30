document.addEventListener('DOMContentLoaded', () => {
  // Theme management
  const themeToggle = document.getElementById('theme-toggle');
  const currentTheme = localStorage.getItem('theme') || 'dark';
  document.documentElement.setAttribute('data-theme', currentTheme);

  themeToggle.addEventListener('click', () => {
    const theme = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  });

  // UI elements
  const cpuVal = document.getElementById('cpu-val');
  const cpuBar = document.getElementById('cpu-bar');
  const ramVal = document.getElementById('ram-val');
  const ramBar = document.getElementById('ram-bar');
  
  const queueDaemonVal = document.getElementById('queue-daemon-val');
  const queueLenVal = document.getElementById('queue-len-val');
  const queueSuccessVal = document.getElementById('queue-success-val');
  const queueFailVal = document.getElementById('queue-fail-val');
  const queueActionVal = document.getElementById('queue-action-val');
  
  const dbTotalVal = document.getElementById('db-total-val');
  const dbCritVal = document.getElementById('db-crit-val');
  const dbHighVal = document.getElementById('db-high-val');
  const dbMedVal = document.getElementById('db-med-val');
  const dbLowVal = document.getElementById('db-low-val');
  
  const incidentsFeed = document.getElementById('incidents-feed');
  const refreshStreamBtn = document.getElementById('refresh-stream-btn');
  const clearDbBtn = document.getElementById('clear-db-btn');
  const textForm = document.getElementById('text-process-form');
  const reportText = document.getElementById('report-text');
  
  const dropZone = document.getElementById('drop-zone');
  const fileInput = document.getElementById('file-input');
  
  // Pipeline timeline steps
  const steps = [
    document.getElementById('step-1'),
    document.getElementById('step-2'),
    document.getElementById('step-3'),
    document.getElementById('step-4')
  ];

  // Toast Notification handler
  function showToast(message, type = 'info') {
    const holder = document.getElementById('toast-holder');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `<span>${type === 'success' ? '✅' : type === 'error' ? '❌' : 'ℹ️'}</span> <span>${message}</span>`;
    holder.appendChild(toast);
    
    // Automatically prune toast node after animation ends
    setTimeout(() => {
      toast.remove();
    }, 3000);
  }

  // Update Ingestion Pipeline timeline stages visually
  function updatePipelineStage(stage) {
    steps.forEach((step, idx) => {
      const stepNum = idx + 1;
      step.classList.remove('active', 'completed');
      
      if (stepNum < stage) {
        step.classList.add('completed');
      } else if (stepNum === stage) {
        step.classList.add('active');
      }
    });
  }

  // Fetch API status and metrics
  async function fetchStatus() {
    try {
      const res = await fetch('/status');
      if (!res.ok) throw new Error('Network status failed');
      const data = await res.json();
      
      // Update System resources
      const cpu = data.cpu_utilization || 0;
      cpuVal.textContent = `${cpu.toFixed(1)}%`;
      cpuBar.style.width = `${cpu}%`;
      if (cpu > 80) cpuBar.classList.add('high');
      else cpuBar.classList.remove('high');
      
      const ramPercent = data.ram_percent || 0;
      const ramUsed = data.ram_gb_used || 0;
      const ramTotal = data.ram_gb_total || 0;
      ramVal.textContent = `${ramUsed.toFixed(2)} / ${ramTotal.toFixed(2)} GB`;
      ramBar.style.width = `${ramPercent}%`;
      if (ramPercent > 80) ramBar.classList.add('high');
      else ramBar.classList.remove('high');

      // Update Ingest queue details
      const isRunning = data.is_running;
      queueDaemonVal.textContent = isRunning ? 'ACTIVE 🟢' : 'STOPPED 🔴';
      queueDaemonVal.className = isRunning ? 'stat-value active' : 'stat-value inactive';
      
      queueLenVal.textContent = `${data.queue_count} files`;
      queueSuccessVal.textContent = data.processed_count || 0;
      queueFailVal.textContent = data.failed_count || 0;
      
      const currentAction = data.current_status || 'Idle';
      const currentFile = data.current_file;
      queueActionVal.textContent = currentFile ? `${currentAction} (${currentFile})` : currentAction;
      
      updatePipelineStage(data.current_stage || 0);

      // Update SQLite details
      if (data.db_stats) {
        dbTotalVal.textContent = data.db_stats.total;
        dbCritVal.textContent = data.db_stats.CRITICAL;
        dbHighVal.textContent = data.db_stats.HIGH;
        dbMedVal.textContent = data.db_stats.MEDIUM;
        dbLowVal.textContent = data.db_stats.LOW;
      }
    } catch (err) {
      console.error('Error querying status:', err);
    }
  }

  // Fetch Database incident stream
  async function fetchIncidents() {
    try {
      const res = await fetch('/incidents?limit=10');
      if (!res.ok) throw new Error('Database connection failed');
      const incidents = await res.json();
      
      if (incidents.length === 0) {
        incidentsFeed.innerHTML = `
          <div style="text-align: center; padding: 2rem; color: var(--text-muted);">
            No records found. Ingest a file to see entries.
          </div>
        `;
        return;
      }

      incidentsFeed.innerHTML = incidents.map(inc => {
        const priority = inc.computed_priority_level.toLowerCase();
        const date = new Date(inc.created_at || inc.iso_timestamp).toLocaleString();
        const locations = inc.identified_entities.locations.join(', ') || 'N/A';
        const personnel = inc.identified_entities.personnel.join(', ') || 'N/A';
        
        const tasksHTML = inc.actionable_tasks.map(t => `
          <div class="task-item ${t.urgency.toLowerCase()}">
            <span class="task-desc">${t.task_desc}</span>
            <span class="task-urgency badge ${t.urgency.toLowerCase()}">${t.urgency}</span>
          </div>
        `).join('');

        return `
          <div class="incident-row" id="inc-${inc.incident_id}">
            <div class="incident-summary-bar">
              <span class="incident-id">${inc.incident_id.substring(0, 8)}...</span>
              <span class="badge ${priority}">${inc.computed_priority_level}</span>
              <span class="incident-date">${date}</span>
              <span class="incident-preview">${inc.system_summary}</span>
              <span class="incident-toggle-btn">▼</span>
            </div>
            <div class="incident-details-pane">
              <div class="details-grid">
                <div>
                  <h4 class="detail-section-title">📍 Locations</h4>
                  <div class="entities-list">
                    ${inc.identified_entities.locations.map(l => `<span class="entity-tag">${l}</span>`).join('') || '<span class="entity-tag">None</span>'}
                  </div>
                  <h4 class="detail-section-title">👥 Personnel</h4>
                  <div class="entities-list">
                    ${inc.identified_entities.personnel.map(p => `<span class="entity-tag">${p}</span>`).join('') || '<span class="entity-tag">None</span>'}
                  </div>
                </div>
                <div>
                  <h4 class="detail-section-title">📋 Actionable Tasks</h4>
                  <div class="tasks-list">
                    ${tasksHTML || '<div style="color: var(--text-muted); font-size: 0.875rem;">No tasks extracted</div>'}
                  </div>
                </div>
                <pre class="raw-json-block">${JSON.stringify(inc, null, 2)}</pre>
              </div>
            </div>
          </div>
        `;
      }).join('');

      // Setup row toggle events
      document.querySelectorAll('.incident-summary-bar').forEach(bar => {
        bar.addEventListener('click', () => {
          const row = bar.parentElement;
          const pane = row.querySelector('.incident-details-pane');
          const toggle = bar.querySelector('.incident-toggle-btn');
          
          const isOpen = pane.classList.contains('open');
          
          // Close all others first
          document.querySelectorAll('.incident-details-pane').forEach(p => p.classList.remove('open'));
          document.querySelectorAll('.incident-toggle-btn').forEach(t => t.textContent = '▼');
          
          if (!isOpen) {
            pane.classList.add('open');
            toggle.textContent = '▲';
          }
        });
      });
    } catch (err) {
      console.error('Error fetching stream:', err);
    }
  }

  // Clear Database
  clearDbBtn.addEventListener('click', async () => {
    if (!confirm('Are you sure you want to purge all database records? This action is irreversible.')) {
      return;
    }
    
    try {
      const res = await fetch('/incidents', { method: 'DELETE' });
      if (!res.ok) throw new Error('Clear operation failed');
      showToast('Database records cleared successfully.', 'success');
      fetchStatus();
      fetchIncidents();
    } catch (err) {
      showToast(err.message, 'error');
    }
  });

  // Direct Text Ingestion
  textForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const text = reportText.value.trim();
    if (!text) return;
    
    const submitBtn = document.getElementById('submit-text-btn');
    submitBtn.disabled = true;
    submitBtn.textContent = 'Extracting...';
    
    try {
      const res = await fetch('/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text })
      });
      
      if (!res.ok) throw new Error('Extraction process failed');
      
      showToast('Direct extraction completed and saved to database.', 'success');
      reportText.value = '';
      fetchStatus();
      fetchIncidents();
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = '⚡ Run Extraction';
    }
  });

  // File Upload portals
  dropZone.addEventListener('click', () => fileInput.click());
  
  dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
  });
  
  dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
  });
  
  dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      uploadFile(files[0]);
    }
  });
  
  fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0) {
      uploadFile(fileInput.files[0]);
    }
  });

  async function uploadFile(file) {
    const suffix = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    if (suffix !== '.txt' && suffix !== '.wav') {
      showToast('Unsupported format. Only .txt and .wav files are allowed.', 'error');
      return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch('/upload', {
        method: 'POST',
        body: formData
      });
      
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'File upload failed');
      }
      
      showToast(`Success: Ingested ${file.name} to background processing queue.`, 'success');
      fetchStatus();
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      fileInput.value = ''; // Reset file input
    }
  }

  // Voice Recorder variables
  const startRecordBtn = document.getElementById('start-record-btn');
  const stopRecordBtn = document.getElementById('stop-record-btn');
  const recordStatus = document.getElementById('record-status');
  const recordingResultPanel = document.getElementById('recording-result-panel');
  const recordTranscriptVal = document.getElementById('record-transcript-val');
  const recordJsonVal = document.getElementById('record-json-val');
  const recordSaveVal = document.getElementById('record-save-val');

  let mediaRecorder = null;
  let audioChunks = [];

  startRecordBtn.addEventListener('click', async () => {
    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error('Your browser does not support audio recording (MediaDevices API missing or not in secure context).');
      }

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunks = [];
      
      let mimeType = '';
      if (MediaRecorder.isTypeSupported('audio/webm')) {
        mimeType = 'audio/webm';
      } else if (MediaRecorder.isTypeSupported('audio/ogg')) {
        mimeType = 'audio/ogg';
      } else if (MediaRecorder.isTypeSupported('audio/mp4')) {
        mimeType = 'audio/mp4';
      } else if (MediaRecorder.isTypeSupported('audio/wav')) {
        mimeType = 'audio/wav';
      }

      const options = mimeType ? { mimeType } : {};
      mediaRecorder = new MediaRecorder(stream, options);

      mediaRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunks.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach(track => track.stop());

        const blobType = mimeType || 'audio/wav';
        const audioBlob = new Blob(audioChunks, { type: blobType });
        await uploadRecordedAudio(audioBlob);
      };

      mediaRecorder.start();
      
      startRecordBtn.disabled = true;
      startRecordBtn.style.cursor = 'not-allowed';
      startRecordBtn.style.backgroundColor = 'var(--text-muted)';
      
      stopRecordBtn.disabled = false;
      stopRecordBtn.style.cursor = 'pointer';
      stopRecordBtn.style.backgroundColor = 'var(--accent-red)';
      
      recordStatus.style.display = 'inline-block';
      showToast('Microphone recording started...', 'info');

    } catch (err) {
      console.error('Error starting audio recording:', err);
      showToast(`Could not start recording: ${err.message}`, 'error');
    }
  });

  stopRecordBtn.addEventListener('click', () => {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop();
    }
    
    startRecordBtn.disabled = false;
    startRecordBtn.style.cursor = 'pointer';
    startRecordBtn.style.backgroundColor = 'var(--accent-red)';
    
    stopRecordBtn.disabled = true;
    stopRecordBtn.style.cursor = 'not-allowed';
    stopRecordBtn.style.backgroundColor = 'var(--text-muted)';
    
    recordStatus.style.display = 'none';
    showToast('Recording stopped. Processing audio...', 'info');
  });

  async function uploadRecordedAudio(blob) {
    const formData = new FormData();
    formData.append('file', blob, 'recorded_mic.wav');

    try {
      const res = await fetch('/process-audio', {
        method: 'POST',
        body: formData
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.error || 'Failed to process audio recording.');
      }

      const result = await res.json();
      
      recordingResultPanel.style.display = 'block';
      recordTranscriptVal.textContent = result.transcript || '';
      recordJsonVal.textContent = JSON.stringify(result.report, null, 2);
      
      if (result.saved) {
        recordSaveVal.textContent = 'Saved to Database';
        recordSaveVal.style.color = 'var(--accent-green)';
        recordSaveVal.style.background = 'rgba(16, 185, 129, 0.1)';
        recordSaveVal.style.border = '1px solid rgba(16, 185, 129, 0.2)';
        showToast('Voice recording transcribed and saved to database.', 'success');
      } else {
        recordSaveVal.textContent = 'Failed to save to database';
        recordSaveVal.style.color = 'var(--accent-red)';
        recordSaveVal.style.background = 'rgba(239, 68, 68, 0.1)';
        recordSaveVal.style.border = '1px solid rgba(239, 68, 68, 0.2)';
        showToast('Audio transcribed but failed to save to database.', 'warning');
      }

      fetchStatus();
      fetchIncidents();

    } catch (err) {
      console.error('Error uploading audio:', err);
      showToast(`Audio processing error: ${err.message}`, 'error');
    }
  }

  // Periodic Polling setups
  fetchStatus();
  fetchIncidents();
  
  setInterval(fetchStatus, 2000);
  setInterval(fetchIncidents, 5000);
  
  refreshStreamBtn.addEventListener('click', () => {
    fetchStatus();
    fetchIncidents();
    showToast('Database stream refreshed.', 'info');
  });
});
