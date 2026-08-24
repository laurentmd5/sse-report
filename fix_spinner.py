import re

with open('app/templates/team_leader/dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('class="dropzone" id="dropZone" onclick="', 'class="dropzone" id="dropZone" style="position: relative;" onclick="')

overlay_html = '''
        <div id="loaderOverlay" style="display:none; position:absolute; top:0; left:0; right:0; bottom:0; background:rgba(255,255,255,0.9); flex-direction:column; align-items:center; justify-content:center; z-index:10; border-radius:12px;">
            <div class="loader"></div>
            <div class="main-txt" style="color:var(--signal); font-weight:600; margin-top:10px;">Analyse en cours...</div>
        </div>
'''
content = content.replace('<div class="ico">', overlay_html + '        <div class="ico">')

js_script = '''
    function showLoading() {
        document.getElementById('loaderOverlay').style.display = 'flex';
    }
    
    document.getElementById('uploadForm').addEventListener('submit', function() {
        showLoading();
    });
'''
content = content.replace("dropZone.addEventListener('drop', (e) => {", js_script + "\n    dropZone.addEventListener('drop', (e) => {")

with open('app/templates/team_leader/dashboard.html', 'w', encoding='utf-8') as f:
    f.write(content)
