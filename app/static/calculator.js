(function () {
  function getExpression() {
    return document.getElementById('expression');
  }

  function appendToExpr(val) {
    const input = getExpression();
    if (!input) return;
    input.value += val;
    input.focus();
  }

  function deleteLastChar() {
    const input = getExpression();
    if (!input || !input.value) return;
    input.value = input.value.slice(0, -1);
    input.focus();
  }

  function clearAll() {
    const input = getExpression();
    const result = document.getElementById('result');
    if (input) input.value = '';
    if (result) result.textContent = '';
  }

  function bindButtons() {
    document.querySelectorAll('button[data-append]').forEach((btn) => {
      btn.addEventListener('click', () => appendToExpr(btn.dataset.append));
    });
    document.querySelectorAll('button[data-action="clear"]').forEach((btn) => {
      btn.addEventListener('click', clearAll);
    });
    document.querySelectorAll('button[data-action="delete"]').forEach((btn) => {
      btn.addEventListener('click', deleteLastChar);
    });
  }

  function adjustFractionBars(root) {
    const scope = root || document;
    const stacks = scope.querySelectorAll('.fraction .stack');
    stacks.forEach((stack) => {
      const den = stack.querySelector('.den');
      const bar = stack.querySelector('.bar');
      if (!den || !bar) return;
      const width = Math.ceil(den.getBoundingClientRect().width);
      bar.style.width = width > 0 ? width + 'px' : '';
    });
  }

  function fitButtonText(btn, maxPx, minPx) {
    let low = minPx;
    let high = maxPx;
    let best = minPx;
    while (low <= high) {
      const mid = Math.floor((low + high) / 2);
      btn.style.fontSize = mid + 'px';
      if (btn.scrollWidth <= btn.clientWidth) {
        best = mid;
        low = mid + 1;
      } else {
        high = mid - 1;
      }
    }
    btn.style.fontSize = best + 'px';
  }

  function adjustAllButtons() {
    const btns = document.querySelectorAll('.buttons button');
    const rootStyle = getComputedStyle(document.documentElement);
    const maxPx = parseInt(rootStyle.getPropertyValue('--btn-max-font-px')) || 24;
    const minPx = parseInt(rootStyle.getPropertyValue('--btn-min-font-px')) || 10;
    btns.forEach((b) => fitButtonText(b, maxPx, minPx));
  }

  function init() {
    bindButtons();
    adjustAllButtons();
    adjustFractionBars(document);

    window.addEventListener('resize', () => {
      window.requestAnimationFrame(() => {
        adjustAllButtons();
        adjustFractionBars(document);
      });
    });

    const btnContainer = document.querySelector('.buttons');
    if (btnContainer && window.MutationObserver) {
      const mo = new MutationObserver(() => adjustAllButtons());
      mo.observe(btnContainer, { childList: true, subtree: true, characterData: true });
    }

    document.body.addEventListener('htmx:afterSwap', (event) => {
      window.requestAnimationFrame(() => adjustFractionBars(event.target || document));
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
