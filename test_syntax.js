const dropZone = document.getElementById('dropZone');

['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, preventDefaults, false);
});

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

function showLoading() {
    document.getElementById('loaderOverlay').style.display = 'flex';
}

document.getElementById('uploadForm').addEventListener('submit', function() {
    showLoading();
});

dropZone.addEventListener('drop', (e) => {
    const dt = e.dataTransfer;
    const files = dt.files;
    if(files.length) {
        document.getElementById('pdfFile').files = files;
        showLoading();
        document.getElementById('uploadForm').submit();
    }
});
