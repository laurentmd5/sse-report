with open('app/templates/team_leader/dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('onchange="document.getElementById(\'uploadForm\').submit()"', 'onchange="showLoading(); document.getElementById(\'uploadForm\').submit()"')

with open('app/templates/team_leader/dashboard.html', 'w', encoding='utf-8') as f:
    f.write(content)
