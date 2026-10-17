(() => {
  const select = document.getElementById('history-week-select');
  if (select) select.addEventListener('change', () => {
    if (select.value) window.location.assign(select.value);
  });
})();
