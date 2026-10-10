document.addEventListener('click', async event => {
  const button = event.target.closest('[data-apply-popup]');
  if (!button) return;
  const panel = button.closest('[data-popup-settings]');
  const result = panel.querySelector('[data-popup-result]');
  const data = { version: Number(panel.dataset.popupVersion) };
  panel.querySelectorAll('[data-popup-field]').forEach(input => {
    data[input.dataset.popupField] = input.type === 'checkbox' ? input.checked : input.value;
  });
  const csrf = panel.closest('form')?.querySelector('[name=csrfmiddlewaretoken]')?.value;
  button.disabled = true;
  result.textContent = '팝업 설정을 적용하고 있습니다. 본문 입력은 현재 화면에 남습니다.';
  try {
    const response = await fetch(panel.dataset.popupSettingsUrl, {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf, 'X-Requested-With': 'XMLHttpRequest' },
      body: JSON.stringify(data),
    });
    if ([401, 403].includes(response.status)) {
      result.textContent = '적용 권한 또는 로그인 상태를 확인해 주세요. 작성 중인 본문과 설정 입력은 유지됩니다.';
      return;
    }
    const saved = await response.json();
    if (!response.ok) {
      result.textContent = Object.values(saved.errors || {}).flat().join(' ') || '적용하지 못했습니다. 로그인과 권한을 확인해 주세요. 입력은 유지됩니다.';
      return;
    }
    panel.dataset.popupVersion = saved.version;
    panel.querySelector('[data-popup-state]').textContent = `${saved.state} — ${saved.reason}`;
    result.textContent = '팝업 설정을 적용했습니다. 본문 입력과 공개본은 변경하지 않았습니다.';
  } catch {
    result.textContent = '적용 결과를 확인하지 못했습니다. 새 탭에서 저장된 설정을 확인해 주세요. 본문과 설정 입력은 유지됩니다.';
  } finally { button.disabled = false; }
});
