// ── Row helpers ────────────────────────────────────────────────────────────
function removeRow(btn) {
  btn.closest('.repeatable').remove();
}

function addBankAccount() {
  const container = document.getElementById('bankAccounts');
  if (!container) return;
  const block = document.createElement('div');
  block.className = 'repeatable bank-account';
  block.innerHTML = `
    <input type="text" name="bank_name" placeholder="Banco">
    <input type="text" name="iban" placeholder="IBAN">
    <input type="text" name="account_number" placeholder="Número de cuenta">
    <input type="text" name="notes" placeholder="Notas">
    <button type="button" class="btn-remove-row" onclick="removeRow(this)" title="Eliminar fila">✕</button>
  `;
  container.appendChild(block);
}

function addWallet() {
  const container = document.getElementById('wallets');
  if (!container) return;
  const block = document.createElement('div');
  block.className = 'repeatable wallet';
  block.innerHTML = `
    <input type="text" name="network" placeholder="Red (ej: ETH)">
    <input type="text" name="address" placeholder="Dirección">
    <input type="text" name="label" placeholder="Etiqueta">
    <input type="text" name="wallet_notes" placeholder="Notas">
    <button type="button" class="btn-remove-row" onclick="removeRow(this)" title="Eliminar fila">✕</button>
  `;
  container.appendChild(block);
}

// ── Collect repeatable rows ────────────────────────────────────────────────
function collectRepeatable(selector, mapper) {
  return Array.from(document.querySelectorAll(selector)).map(mapper);
}

// ── Person form submit ─────────────────────────────────────────────────────
const personForm = document.getElementById('personForm');
if (personForm) {
  personForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const personId = personForm.dataset.personId;
    const formData = new FormData(personForm);
    const payload = {
      full_name: formData.get('full_name'),
      dni:       formData.get('dni')      || null,
      passport:  formData.get('passport') || null,
      bank_accounts: collectRepeatable('.bank-account', (row) => ({
        bank_name:      row.querySelector('[name="bank_name"]')?.value      || null,
        iban:           row.querySelector('[name="iban"]')?.value           || null,
        account_number: row.querySelector('[name="account_number"]')?.value || null,
        notes:          row.querySelector('[name="notes"]')?.value          || null,
      })),
      wallet_addresses: collectRepeatable('.wallet', (row) => ({
        network: row.querySelector('[name="network"]')?.value      || null,
        address: row.querySelector('[name="address"]')?.value      || '',
        label:   row.querySelector('[name="label"]')?.value        || null,
        notes:   row.querySelector('[name="wallet_notes"]')?.value || null,
      })),
    };
    const method = personId ? 'PUT' : 'POST';
    const url    = personId ? `/api/people/${personId}` : '/api/people';
    const btn = personForm.querySelector('button[type="submit"]');
    btn.disabled = true;
    btn.textContent = 'Guardando…';
    const response = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    btn.disabled = false;
    btn.textContent = 'Guardar cambios';
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      showToast(err.detail || 'No se pudo guardar la persona', 'error');
      return;
    }
    const data = await response.json();
    window.location.href = `/people/${data.id}`;
  });
}

// ── Delete person from list row ────────────────────────────────────────────
async function deletePersonRow(id, name, btn) {
  const ok = await confirmDialog(`¿Eliminar a <strong>${name}</strong> y todos sus datos?`);
  if (!ok) return;
  const r = await fetch(`/api/people/${id}`, { method: 'DELETE' });
  if (r.ok) {
    btn.closest('tr').remove();
    showToast(`${name} eliminado correctamente`);
  } else {
    showToast('No se pudo eliminar la persona', 'error');
  }
}

// ── Search ─────────────────────────────────────────────────────────────────
const searchInput = document.getElementById('searchInput');
if (searchInput) {
  searchInput.addEventListener('input', () => {
    const term = searchInput.value.toLowerCase();
    document.querySelectorAll('#peopleTable tbody tr').forEach((row) => {
      row.style.display = row.innerText.toLowerCase().includes(term) ? '' : 'none';
    });
  });
}
