import requests
from bs4 import BeautifulSoup

session = requests.Session()

# Step 1: Get login page
r1 = session.get('http://localhost:8000/user/login', timeout=10)
print(f'Login page: {r1.status_code}')
soup = BeautifulSoup(r1.text, 'html.parser')
csrf_input = soup.find('input', {'name': 'csrf_token'})
csrf = csrf_input['value'] if csrf_input else ''
print(f'CSRF token: {csrf[:20]}...')

# Step 2: Submit login
r2 = session.post('http://localhost:8000/user/login', data={
    'identifier': 'testuser@example.com',
    'password': 'demo123',
    'csrf_token': csrf,
    'next': '/portal/'
}, allow_redirects=False, timeout=10)
print(f'Login POST: {r2.status_code}')
print(f'Location: {r2.headers.get("Location", "None")}')
print(f'Cookies: {list(session.cookies.keys())}')

# Step 3: Follow redirect
if r2.status_code in [301, 302, 307]:
    next_url = r2.headers['Location']
    r3 = session.get(f'http://localhost:8000{next_url}', timeout=10)
    print(f'Redirect page: {r3.status_code}')
    soup3 = BeautifulSoup(r3.text, 'html.parser')
    title = soup3.find('title')
    print(f'Page title: {title.text if title else "No title"}')
