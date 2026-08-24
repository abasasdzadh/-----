const API = {
  async inspectVideo(url) {
    const res = await fetch('/api/video/inspect', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'خطا در بررسی ویدیو');
    }
    return await res.json();
  },

  async getVoices(targetLanguage = 'fa') {
    const res = await fetch(`/api/video/voices?target_language=${targetLanguage}`);
    return await res.json();
  },

  async createJob(payload) {
    const res = await fetch('/api/jobs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'خطا در ایجاد فرآیند دوبله');
    }
    return await res.json();
  },

  async cancelJob(jobId) {
    const res = await fetch(`/api/jobs/${jobId}/cancel`, { method: 'POST' });
    return await res.json();
  },

  async getTranscript(jobId) {
    const res = await fetch(`/api/jobs/${jobId}/transcript`);
    return await res.json();
  },

  async getTranslation(jobId) {
    const res = await fetch(`/api/jobs/${jobId}/translation`);
    return await res.json();
  },

  async getSettings() {
    const res = await fetch('/api/settings');
    return await res.json();
  },

  async saveApiKey(key) {
    const res = await fetch('/api/settings/gemini-key', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ gemini_api_key: key })
    });
    return await res.json();
  }
};