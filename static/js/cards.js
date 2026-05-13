var cardsSearchEl  = document.getElementById('cards-search');
var cardsNoResults = document.getElementById('cards-no-results');

if (cardsSearchEl) {
  cardsSearchEl.addEventListener('input', function () {
    var q = this.value.toLowerCase().trim();
    var rows = document.querySelectorAll('.card-row');
    var anyVisible = false;
    rows.forEach(function (row) {
      var front  = (row.dataset.front  || '').toLowerCase();
      var back   = (row.dataset.back   || '').toLowerCase();
      var answer = (row.dataset.answer || '').toLowerCase();
      var match  = !q || front.includes(q) || back.includes(q) || answer.includes(q);
      row.style.display = match ? '' : 'none';
      if (match) anyVisible = true;
    });
    if (cardsNoResults) cardsNoResults.hidden = anyVisible;
  });
}

document.addEventListener('click', function (e) {
  var btn = e.target.closest('.card-delete-btn');
  if (!btn) return;
  var id = btn.dataset.id;
  showConfirm('Удалить карточку #' + id + '?', function () {
    fetch('/cards/delete', {
      method: 'DELETE',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({id: parseInt(id, 10)})
    })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      if (data.ok) {
        var row = document.getElementById('card-' + id);
        if (row) row.remove();
      }
    });
  });
});
