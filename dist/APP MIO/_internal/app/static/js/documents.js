// ── Upload document ────────────────────────────────────────────────────────
const documentForm = document.getElementById('documentForm');
if (documentForm) {
  documentForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const personId = documentForm.dataset.personId;
    const formData = new FormData(documentForm);
    const btn = documentForm.querySelector('button[type="submit"]');
    btn.disabled = true;
    btn.textContent = 'Subiendo…';
    const response = await fetch(`/api/people/${personId}/documents`, {
      method: 'POST',
      body: formData,
    });
    btn.disabled = false;
    btn.textContent = 'Subir PDF';
    if (!response.ok) {
      showToast('No se pudo subir el PDF', 'error');
      return;
    }
    const doc = await response.json();
    // Add row dynamically
    const list = document.getElementById('documentList') || (() => {
      const ul = document.createElement('ul');
      ul.className = 'item-list';
      ul.id = 'documentList';
      const empty = document.getElementById('docEmpty');
      if (empty) empty.remove();
      documentForm.insertAdjacentElement('afterend', ul);
      return ul;
    })();
    const li = document.createElement('li');
    li.id = `doc-${doc.id}`;
    li.innerHTML = `
      <div class="item-list-main">
        <a href="/api/documents/${doc.id}/file" target="_blank" style="font-weight:600;">${doc.original_filename}</a>
        ${doc.category ? `<div class="item-list-sub">${doc.category}</div>` : ''}
        ${doc.description ? `<div class="item-list-sub">${doc.description}</div>` : ''}
      </div>
      <button class="button btn-sm btn-danger" onclick="deleteDocument(${doc.id}, '${doc.original_filename.replace(/'/g,"\\'")}')">Eliminar</button>`;
    list.appendChild(li);
    documentForm.reset();
    showToast('PDF subido correctamente');
  });
}

// ── Delete document ────────────────────────────────────────────────────────
async function deleteDocument(docId, filename) {
  const ok = await confirmDialog(`¿Eliminar el documento <strong>${filename}</strong>?`);
  if (!ok) return;
  const r = await fetch(`/api/documents/${docId}`, { method: 'DELETE' });
  if (r.ok) {
    const el = document.getElementById(`doc-${docId}`);
    if (el) el.remove();
    const list = document.getElementById('documentList');
    if (list && list.children.length === 0) {
      list.remove();
      const card = document.querySelector('#documentList')?.closest('.card');
      // Show empty state
      const p = document.createElement('p');
      p.className = 'empty-state';
      p.id = 'docEmpty';
      p.textContent = 'Sin documentos';
      documentForm.insertAdjacentElement('afterend', p);
    }
    showToast('Documento eliminado');
  } else {
    showToast('No se pudo eliminar el documento', 'error');
  }
}
