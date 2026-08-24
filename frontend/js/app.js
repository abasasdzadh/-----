let currentJobId = null;
let eventSource = null;
let currentInspectedUrl = null;

document.addEventListener('DOMContentLoaded', async () => {
  // 1. Initial System Check & Voices load
  await checkSystemHealth();
  await loadVoices('fa');

  // 2. Event Listeners
  document.getElementById('inspectForm').addEventListener('submit', handleInspectVideo);
  document.getElementById('targetLang').addEventListener('change', (e) => loadVoices(e.target.value));
  document.getElementById('btnStartDubbing').addEventListener('click', handleStartDubbing);
  document.getElementById('btnCancelJob').addEventListener('click', handleCancelJob);
  document.getElementById('btnSettingsModal').addEventListener('click', () => {
    document.getElementById('settingsModal').classList.remove('hidden');
  });
  document.getElementById('btnCloseModal').addEventListener('click', () => {
    document.getElementById('settingsModal').classList.add('hidden');
  });
  document.getElementById('btnSaveKey').addEventListener('click', handleSaveApiKey);
  
  // Background volume toggle
  const keepBg = document.getElementById('keepOriginalAudio');
  keepBg.addEventListener('change', (e) => {
    document.getElementById('bgVolumeControl').classList.toggle('hidden', !e.target.checked);
  });
  document.getElementById('bgVolume').addEventListener('input', (e) => {
    document.getElementById('bgVolVal').textContent = `${e.target.value}%`;
  });
});

async function checkSystemHealth() {
  try {
    const s = await API.getSettings();
    const h = s.hardware;
    const txt = `${h.cpu_cores} Cores | RAM: ${h.available_ram_gb}GB | ${h.cuda_available ? 'GPU: ' + h.gpu_name : 'CPU Mode'}`;
    document.querySelector('.health-text').textContent = txt;

    if (!s.gemini_api_key_configured) {
      UI.showToast('لطفاً ابتدا کلید Gemini API را در بخش تنظیمات وارد کنید.', 'warning');
      document.getElementById('settingsModal').classList.remove('hidden');
    }
  } catch (e) {
    document.querySelector('.health-text').textContent = 'خطا در ارتباط با سرور';
  }
}

async function loadVoices(lang) {
  try {
    const data = await API.getVoices(lang);
    const select = document.getElementById('voiceSelect');
    select.innerHTML = '';
    data.voices.forEach(v => {
      const opt = document.createElement('option');
      opt.value = v.id;
      opt.textContent = `${v.name} [${v.locale}]`;
      select.appendChild(opt);
    });
  } catch (e) {
    UI.showToast('خطا در دریافت لیست صداهای TTS', 'error');
  }
}

async function handleInspectVideo(e) {
  e.preventDefault();
  const url = document.getElementById('youtubeUrl').value.trim();
  const btn = document.getElementById('btnInspect');
  const spinner = btn.querySelector('.spinner');
  
  btn.disabled = true;
  if (spinner) spinner.classList.remove('hidden');

  try {
    const data = await API.inspectVideo(url);
    currentInspectedUrl = data.url;

    // Show metadata card
    document.getElementById('metaTitle').textContent = data.title;
    document.getElementById('metaThumb').src = data.thumbnail;
    document.getElementById('metaDuration').textContent = data.duration_formatted;
    document.getElementById('metaUploader').textContent = data.uploader;
    document.getElementById('metaQuality').textContent = data.available_qualities[0] || '720p';

    document.getElementById('videoMetaCard').classList.remove('hidden');
    document.getElementById('configSection').classList.remove('disabled-card');
    UI.showToast('اطلاعات ویدیو دریافت شد.', 'success');
  } catch (err) {
    UI.showToast(err.message, 'error');
  } finally {
    btn.disabled = false;
    if (spinner) spinner.classList.add('hidden');
  }
}

async function handleStartDubbing() {
  if (!currentInspectedUrl) {
    UI.showToast('ابتدا ویدیوی مورد نظر را بررسی کنید.', 'error');
    return;
  }

  const payload = {
    url: currentInspectedUrl,
    source_language: document.getElementById('sourceLang').value,
    target_language: document.getElementById('targetLang').value,
    voice_id: document.getElementById('voiceSelect').value,
    keep_original_audio: document.getElementById('keepOriginalAudio').checked,
    original_audio_volume: parseFloat(document.getElementById('bgVolume').value) / 100.0
  };

  try {
    const job = await API.createJob(payload);
    currentJobId = job.job_id;

    // Show Processing Card
    document.getElementById('processingSection').classList.remove('hidden');
    document.getElementById('resultSection').classList.add('hidden');
    document.getElementById('configSection').classList.add('disabled-card');
    
    // Subscribe to SSE
    listenToJobEvents(currentJobId);
  } catch (err) {
    UI.showToast(err.message, 'error');
  }
}

function listenToJobEvents(jobId) {
  if (eventSource) eventSource.close();

  eventSource = new EventSource(`/api/jobs/${jobId}/events`);
  
  eventSource.onmessage = async (event) => {
    const data = JSON.parse(event.data);
    
    // Update Stepper & Progress
    UI.updateStepper(data.status);
    document.getElementById('progressBarFill').style.width = `${data.progress}%`;
    document.getElementById('stepPercentText').textContent = `${Math.round(data.progress)}%`;
    document.getElementById('stepStatusText').textContent = data.current_step || '';

    if (data.status === 'completed') {
      eventSource.close();
      UI.showToast('عملیات دوبله کامل شد!', 'success');
      await displayFinalResult(jobId);
    } else if (data.status === 'failed') {
      eventSource.close();
      UI.showToast(`خطا در پردازش: ${data.error_message}`, 'error');
      document.getElementById('configSection').classList.remove('disabled-card');
    } else if (data.status === 'cancelled') {
      eventSource.close();
      UI.showToast('پردازش توسط کاربر لغو شد.', 'info');
      document.getElementById('configSection').classList.remove('disabled-card');
    }
  };

  eventSource.onerror = () => {
    eventSource.close();
  };
}

async function handleCancelJob() {
  if (!currentJobId) return;
  try {
    await API.cancelJob(currentJobId);
  } catch (err) {
    UI.showToast(err.message, 'error');
  }
}

async function displayFinalResult(jobId) {
  const resultSec = document.getElementById('resultSection');
  resultSec.classList.remove('hidden');

  // Setup Player & Download
  const videoUrl = `/api/jobs/${jobId}/video`;
  const player = document.getElementById('finalVideoPlayer');
  player.src = videoUrl;
  document.getElementById('btnDownloadVideo').href = videoUrl;

  // Load Transcript and Translation
  try {
    const transcript = await API.getTranscript(jobId);
    const translation = await API.getTranslation(jobId);
    UI.renderTranscriptTable(transcript, translation);
    document.getElementById('jsonPreviewContent').textContent = JSON.stringify({ transcript, translation }, null, 2);
  } catch (e) {
    console.error(e);
  }
}

async function handleSaveApiKey() {
  const key = document.getElementById('geminiApiKeyInput').value.trim();
  if (!key) {
    UI.showToast('لطفاً یک کلید معتبر وارد کنید.', 'error');
    return;
  }
  try {
    await API.saveApiKey(key);
    UI.showToast('کلید با موفقیت ذخیره شد.', 'success');
    document.getElementById('settingsModal').classList.add('hidden');
    await checkSystemHealth();
  } catch (e) {
    UI.showToast('خطا در ذخیره کلید', 'error');
  }
}