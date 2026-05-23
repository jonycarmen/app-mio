function addPublicBankAccount() {
  const container = document.getElementById('publicBankAccounts');
  if (!container) return;
  const block = document.createElement('div');
  block.className = 'repeatable bank-account';
  block.innerHTML = `
    <input type="text" name="bank_name" placeholder="Banco">
    <input type="text" name="iban" placeholder="IBAN">
    <input type="text" name="account_number" placeholder="Numero de cuenta">
    <input type="text" name="notes" placeholder="Notas">
    <button type="button" class="btn-remove-row" onclick="removeRow(this)" title="Eliminar fila">×</button>
  `;
  container.appendChild(block);
}

function addPublicWallet() {
  const container = document.getElementById('publicWallets');
  if (!container) return;
  const block = document.createElement('div');
  block.className = 'repeatable wallet';
  block.innerHTML = `
    <input type="text" name="network" placeholder="Red">
    <input type="text" name="address" placeholder="Direccion">
    <input type="text" name="label" placeholder="Etiqueta">
    <input type="text" name="wallet_notes" placeholder="Notas">
    <button type="button" class="btn-remove-row" onclick="removeRow(this)" title="Eliminar fila">×</button>
  `;
  container.appendChild(block);
}

function documentQuery(selector) {
  return window.document.querySelector(selector);
}

function renderPublicDocument(doc, token) {
  const li = window.document.createElement('li');
  li.id = `public-doc-${doc.id}`;
  li.innerHTML = `
    <div class="item-list-main">
      <a href="/form/${token}/documents/${doc.id}/file" target="_blank" rel="noopener">${doc.original_filename}</a>
      ${doc.category ? `<div class="item-list-sub">${doc.category}</div>` : ''}
      ${doc.description ? `<div class="item-list-sub">${doc.description}</div>` : ''}
    </div>
  `;
  return li;
}

/* ── Drag & drop + mobile tap for public file upload ─────────── */
(function initPublicDropzone() {
  const dropzone = document.getElementById('publicDropzone');
  const input    = document.getElementById('publicFileInput');
  if (!dropzone || !input) return;

  // Update label when a file is chosen
  function updateLabel() {
    const file = input.files && input.files[0];
    const hint = dropzone.querySelector('.drop-hint');
    const para = dropzone.querySelector('p');
    if (file) {
      if (para) para.textContent = '✅ ' + file.name;
      if (hint) hint.textContent = 'Toca de nuevo para cambiar el archivo';
    } else {
      if (para) para.textContent = '📎 Toca para seleccionar un archivo';
      if (hint) hint.textContent = 'También puedes arrastrar y soltar aquí';
    }
  }
  input.addEventListener('change', updateLabel);

  // Desktop drag-and-drop
  ['dragenter','dragover','dragleave','drop'].forEach(function(evt) {
    dropzone.addEventListener(evt, function(e) {
      e.preventDefault();
      e.stopPropagation();
    }, false);
  });
  ['dragenter','dragover'].forEach(function(evt) {
    dropzone.addEventListener(evt, function() { dropzone.classList.add('dragover'); }, false);
  });
  ['dragleave','drop'].forEach(function(evt) {
    dropzone.addEventListener(evt, function() { dropzone.classList.remove('dragover'); }, false);
  });
  dropzone.addEventListener('drop', function(e) {
    const dt = e.dataTransfer;
    if (dt && dt.files && dt.files.length) {
      input.files = dt.files;
      updateLabel();
    }
  }, false);

  // Keyboard accessibility (Enter / Space opens file picker)
  dropzone.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      input.click();
    }
  });

  // Reset label when the parent form is reset
  const form = dropzone.closest('form');
  if (form) {
    form.addEventListener('reset', function() {
      // Timeout needed because reset() hasn't applied yet at this moment
      setTimeout(updateLabel, 0);
    });
  }
})();

const publicPersonForm = document.getElementById('publicPersonForm');
if (publicPersonForm) {
  publicPersonForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const token = publicPersonForm.dataset.token;
    const formData = new FormData(publicPersonForm);
    const payload = {
      dni: formData.get('dni') || null,
      passport: formData.get('passport') || null,
      bank_accounts: collectRepeatable('.bank-account', (row) => ({
        bank_name: row.querySelector('[name="bank_name"]')?.value || null,
        iban: row.querySelector('[name="iban"]')?.value || null,
        account_number: row.querySelector('[name="account_number"]')?.value || null,
        notes: row.querySelector('[name="notes"]')?.value || null,
      })),
      wallet_addresses: collectRepeatable('.wallet', (row) => ({
        network: row.querySelector('[name="network"]')?.value || null,
        address: row.querySelector('[name="address"]')?.value || '',
        label: row.querySelector('[name="label"]')?.value || null,
        notes: row.querySelector('[name="wallet_notes"]')?.value || null,
      })),
    };

    const button = publicPersonForm.querySelector('button[type="submit"]');
    button.disabled = true;
    button.textContent = 'Guardando...';

    const response = await fetch(`/form/${token}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    button.disabled = false;
    button.textContent = 'Guardar mis datos';

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      showToast(error.detail || 'No se pudieron guardar tus datos', 'error');
      return;
    }

    showToast('Tus datos se han guardado correctamente');
  });
}

const publicDocumentForm = document.getElementById('publicDocumentForm');
if (publicDocumentForm) {
  publicDocumentForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const token = publicDocumentForm.dataset.token;
    const formData = new FormData(publicDocumentForm);
    const button = publicDocumentForm.querySelector('button[type="submit"]');
    button.disabled = true;
    button.textContent = 'Subiendo...';

    const response = await fetch(`/form/${token}/documents`, {
      method: 'POST',
      body: formData,
    });

    button.disabled = false;
    button.textContent = 'Subir archivo';

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      showToast(error.detail || 'No se pudo subir el archivo', 'error');
      return;
    }

    const doc = await response.json();
    const list = documentQuery('#publicDocumentsList');
    const empty = documentQuery('#publicDocumentsEmpty');
    if (empty) empty.style.display = 'none';
    if (list) list.prepend(renderPublicDocument(doc, token));
    publicDocumentForm.reset();
    showToast('Archivo subido correctamente');
  });
}