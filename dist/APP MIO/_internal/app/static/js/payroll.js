// ── Register payroll ───────────────────────────────────────────────────────
const payrollForm = document.getElementById('payrollForm');
if (payrollForm) {
  payrollForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const personId = payrollForm.dataset.personId;
    const formData = new FormData(payrollForm);
    const payload = {
      amount:         Number(formData.get('amount')),
      effective_date: formData.get('effective_date'),
      notes:          formData.get('notes') || null,
    };
    const btn = payrollForm.querySelector('button[type="submit"]');
    btn.disabled = true;
    btn.textContent = 'Guardando…';
    const response = await fetch(`/api/people/${personId}/payrolls`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    btn.disabled = false;
    btn.textContent = 'Registrar';
    if (!response.ok) {
      showToast('No se pudo registrar la nómina', 'error');
      return;
    }
    const payroll = await response.json();
    // Add row dynamically
    const list = document.getElementById('payrollList') || (() => {
      const ul = document.createElement('ul');
      ul.className = 'item-list';
      ul.id = 'payrollList';
      const empty = document.getElementById('payrollEmpty');
      if (empty) empty.remove();
      payrollForm.insertAdjacentElement('afterend', ul);
      return ul;
    })();
    const li = document.createElement('li');
    li.id = `payroll-${payroll.id}`;
    li.innerHTML = `
      <div class="item-list-main">
        <span style="font-weight:600;">${payroll.amount} €</span>
        &nbsp;<span class="item-list-sub">${payroll.effective_date}</span>
        ${payroll.notes ? `&nbsp;·&nbsp;<span class="item-list-sub">${payroll.notes}</span>` : ''}
      </div>
      <button class="button btn-sm btn-danger" onclick="deletePayroll(${personId}, ${payroll.id})">Eliminar</button>`;
    list.insertBefore(li, list.firstChild);
    payrollForm.reset();
    showToast('Nómina registrada');
  });
}

// ── Delete payroll ─────────────────────────────────────────────────────────
async function deletePayroll(personId, payrollId) {
  const ok = await confirmDialog('¿Eliminar esta entrada de nómina?');
  if (!ok) return;
  const r = await fetch(`/api/people/${personId}/payrolls/${payrollId}`, { method: 'DELETE' });
  if (r.ok) {
    const el = document.getElementById(`payroll-${payrollId}`);
    if (el) el.remove();
    const list = document.getElementById('payrollList');
    if (list && list.children.length === 0) {
      list.remove();
      const p = document.createElement('p');
      p.className = 'empty-state';
      p.id = 'payrollEmpty';
      p.textContent = 'Sin historial de nóminas';
      payrollForm.insertAdjacentElement('afterend', p);
    }
    showToast('Nómina eliminada');
  } else {
    showToast('No se pudo eliminar la nómina', 'error');
  }
}
