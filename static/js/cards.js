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
