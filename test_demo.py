import sys
sys.path.insert(0, '.')
from securewaste import create_app

app = create_app({'TESTING': True})
print('App created')
client = app.test_client()
r = client.get('/results/demo')
print(f'Status: {r.status_code}')
html = r.get_data(as_text=True)
assert 'invoice_sample.pdf' in html
assert 'Findings: 3' in html
assert 'j••••@e•••••.com' in html
print('Demo route works!')