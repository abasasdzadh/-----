const UI = {
  showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
  },

  updateStepper(status) {
    const stepIds = [
      'step_downloading',
      'step_extracting_audio',
      'step_transcribing',
      'step_translating',
      'step_generating_voice',
      'step_rendering'
    ];

    const statusMap = {
      'downloading': 0,
      'extracting_audio': 1,
      'transcribing': 2,
      'translating': 3,
      'generating_voice': 4,
      'rendering': 5,
      'completed': 6
    };

    const activeIndex = statusMap[status] !== undefined ? statusMap[status] : -1;

    stepIds.forEach((id, idx) => {
      const el = document.getElementById(id);
      if (!el) return;
      el.classList.remove('active', 'completed');
      if (idx < activeIndex) {
        el.classList.add('completed');
      } else if (idx === activeIndex) {
        el.classList.add('active');
      }
    });
  },

  renderTranscriptTable(transcription, translation) {
    const tbody = document.getElementById('transcriptTbody');
    tbody.innerHTML = '';
    
    const transMap = {};
    if (translation && translation.segments) {
      translation.segments.forEach(s => { transMap[s.id] = s.translated_text; });
    }

    if (!transcription || !transcription.segments) return;

    transcription.segments.forEach(seg => {
      const tr = document.createElement('tr');
      const startMin = Math.floor(seg.start / 60);
      const startSec = Math.floor(seg.start % 60);
      const timeFmt = `${startMin.toString().padStart(2, '0')}:${startSec.toString().padStart(2, '0')}`;

      tr.innerHTML = `
        <td><code>${timeFmt}</code></td>
        <td>${seg.text}</td>
        <td><strong>${transMap[seg.id] || '-'}</strong></td>
      `;
      tbody.appendChild(tr);
    });
  }
};