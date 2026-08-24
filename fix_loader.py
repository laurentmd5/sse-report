import re

with open('app/templates/team_leader/dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

loader_html = '''
  <div id="loaderZone" style="display:none; flex-direction:column; align-items:center; justify-content:center; gap:15px; padding: 20px 0; border: 2px dashed var(--signal); border-radius: 12px; background: rgba(0, 51, 102, 0.05); margin-bottom: 2rem;">
      <div class="loader"></div>
      <div class="main-txt" style="color:var(--signal); font-weight:600;">Analyse du fichier en cours...</div>
      <div class="sub-txt">Veuillez patienter, cela peut prendre quelques instants.</div>
  </div>
'''

content = content.replace('<form action="{{ url_for(\'main.upload\') }}"', loader_html + '<form action="{{ url_for(\'main.upload\') }}"')

js_script = '''
    const uploadForm = document.getElementById('uploadForm');
    function showLoading() {
        uploadForm.style.display = 'none';
        document.getElementById('loaderZone').style.display = 'flex';
    }
    
    uploadForm.addEventListener('submit', function() {
        showLoading();
    });
    
    document.getElementById('pdfFile').addEventListener('change', function() {
        if(this.files.length) {
            showLoading();
            uploadForm.submit();
        }
    });
</script>
'''

content = content.replace("document.getElementById('pdfFile').files = files;\n            document.getElementById('uploadForm').submit();", "document.getElementById('pdfFile').files = files;\n            showLoading();\n            document.getElementById('uploadForm').submit();")

content = content.replace("</script>", js_script)

with open('app/templates/team_leader/dashboard.html', 'w', encoding='utf-8') as f:
    f.write(content)
