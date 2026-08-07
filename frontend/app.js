const input = document.querySelector('#file-input');
const form = document.querySelector('#upload-form');
const browse = document.querySelector('#browse-button');
const verify = document.querySelector('#verify-button');
const fileName = document.querySelector('#file-name');
const result = document.querySelector('#result');
// Use the same FastAPI server when it serves /app (regardless of its port).
// A VS Code Live Server preview still falls back to the normal local API port.
const API_BASE = window.location.pathname.startsWith('/app') ? '' : 'http://127.0.0.1:8000';

const setFile = (file) => {
  if (!file) return;
  if (file.size > 10 * 1024 * 1024) return showError('Please choose a file smaller than 10 MB.');
  input.files = createFileList(file);
  fileName.textContent = file.name;
  verify.disabled = false;
  result.classList.add('hidden');
};
const createFileList = (file) => { const data = new DataTransfer(); data.items.add(file); return data.files; };
browse.addEventListener('click', () => input.click());
input.addEventListener('change', () => setFile(input.files[0]));
['dragenter', 'dragover'].forEach((event) => form.addEventListener(event, (e) => { e.preventDefault(); form.classList.add('dragging'); }));
['dragleave', 'drop'].forEach((event) => form.addEventListener(event, (e) => { e.preventDefault(); form.classList.remove('dragging'); }));
form.addEventListener('drop', (e) => setFile(e.dataTransfer.files[0]));
form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const file = input.files[0]; if (!file) return;
  verify.disabled = true; verify.textContent = 'Reading document…';
  const body = new FormData(); body.append('file', file);
  try {
    const response = await fetch(`${API_BASE}/verify-document`, { method:'POST', body });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Verification could not be completed.');
    showResult(data);
  } catch (error) {
    const message = error instanceof TypeError
      ? 'Cannot reach the verification server. Start FastAPI at http://127.0.0.1:8000, then try again.'
      : error.message;
    showError(message);
  }
  finally { verify.disabled = false; verify.innerHTML = 'Verify document <span>→</span>'; }
});
function showResult(data) {
  const f = data.fields; const validation = data.validation;
  const rows = [['Document type',f.document_type],['Name',f.name],['Aadhaar number',f.aadhaar_number],['Date of birth',f.dob],['Gender',f.gender],['PIN code',f.pin_code]];
  result.innerHTML = `<div class="result-heading"><h2>Extraction result</h2><span class="badge ${validation.valid ? 'ok' : 'bad'}">${validation.valid ? 'VALIDATED' : 'NEEDS REVIEW'}</span></div><div class="field-grid">${rows.map(([label,value]) => `<div class="field"><label>${escapeHtml(label)}</label><strong>${escapeHtml(value || 'Not detected')}</strong></div>`).join('')}</div>${validation.errors.length ? `<div class="errors">${validation.errors.map(escapeHtml).join('<br>')}</div>` : ''}`;
  result.classList.remove('hidden'); result.scrollIntoView({ behavior:'smooth', block:'nearest' });
}
function showError(message) { result.innerHTML = `<div class="errors">${escapeHtml(message)}</div>`; result.classList.remove('hidden'); }
function escapeHtml(value) { return String(value).replace(/[&<>'"]/g, (character) => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', "'":'&#39;', '"':'&quot;' })[character]); }
