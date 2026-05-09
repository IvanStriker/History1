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
