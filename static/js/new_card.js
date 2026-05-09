(function () {
  function bindSide(radioName, textareaId, uploadId, fileId, previewId) {
    var radios   = document.querySelectorAll('input[name="' + radioName + '"]');
    var textarea = document.getElementById(textareaId);
    var upload   = document.getElementById(uploadId);
    var fileIn   = document.getElementById(fileId);
    var preview  = document.getElementById(previewId);

    function applyType(val) {
      if (val === 'image') {
        textarea.style.display  = 'none';
        textarea.removeAttribute('required');
        textarea.value          = '';
        upload.style.display    = 'flex';
        fileIn.required         = true;
      } else {
        upload.style.display    = 'none';
        fileIn.required         = false;
        preview.style.display   = 'none';
        preview.src             = '';
        textarea.style.display  = '';
        textarea.setAttribute('required', '');
      }
    }

    radios.forEach(function (r) {
      r.addEventListener('change', function () { applyType(r.value); });
    });

    fileIn.addEventListener('change', function () {
      if (this.files && this.files[0]) {
        var reader = new FileReader();
        reader.onload = function (e) {
          preview.src           = e.target.result;
          preview.style.display = 'block';
        };
        reader.readAsDataURL(this.files[0]);
      } else {
        preview.src           = '';
        preview.style.display = 'none';
      }
    });

    var initial = document.querySelector('input[name="' + radioName + '"]:checked');
    if (initial) applyType(initial.value);
  }

  bindSide('front_type', 'front_content', 'front_upload', 'front_file', 'front_preview');
  bindSide('back_type',  'back_content',  'back_upload',  'back_file',  'back_preview');
})();
