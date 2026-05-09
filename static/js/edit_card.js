(function () {
  ['front', 'back'].forEach(function (side) {
    var keep    = document.getElementById(side + '_keep');
    var fileIn  = document.getElementById(side + '_file');
    var preview = document.getElementById(side + '_preview');
    if (!keep || !fileIn) return;
    fileIn.required = false;
    if (keep.value && preview) {
      preview.src           = '/static/' + keep.value;
      preview.style.display = 'block';
    }
  });
})();
