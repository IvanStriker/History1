var catSearchEl  = document.getElementById('cat-search');
var catNoResults = document.getElementById('cat-no-results');

if (catSearchEl) {
  catSearchEl.addEventListener('input', function () {
    var q = this.value.toLowerCase().trim();
    var items = document.querySelectorAll('.category-card');
    var anyVisible = false;
    items.forEach(function (item) {
      var name = (item.dataset.name        || '').toLowerCase();
      var desc = (item.dataset.description || '').toLowerCase();
      var match = !q || name.includes(q) || desc.includes(q);
      item.style.display = match ? '' : 'none';
      if (match) anyVisible = true;
    });
    if (catNoResults) catNoResults.hidden = anyVisible;
  });
}

document.addEventListener('click', function (e) {
  var btn = e.target.closest('.category-delete-btn');
  if (!btn) return;
  var id = btn.dataset.id;
  showConfirm('Удалить подборку #' + id + '?', function () {
    fetch('/categories/delete', {
      method: 'DELETE',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({id: parseInt(id, 10)})
    })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      if (data.ok) {
        var card = document.getElementById('category-' + id);
        if (card) card.remove();
      }
    });
  });
});
