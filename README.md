# *FUNDAAZ* – Student–Teacher Dashboard  (v2)

A full-stack academic performance management system — **Flask + SQLite + Chart.js**

---

## 🆕 What's New in v2

- **Student Progress Search** — Admin can search any student by Login ID or Name and view their full profile, test history, subject breakdown with grades (A+/A/B/C/D/F), summary stats, and interactive charts
- **📈 Progress button** on every student row — one click opens their full progress report
- **All Results** in the Marks tab now shows complete history (not just 10 recent)
- **Security hardening** — SESSION_COOKIE_HTTPONLY, SESSION_COOKIE_SECURE, env-based secret key
- **Deployment-ready** — Procfile, .gitignore, .env.example, gunicorn, flask-limiter, flask-talisman included
- **Better form validation** — maxlength, pattern, minlength attributes on all inputs

---

## 📁 Project Structure

```
fundaaz/
├── app.py                    # Flask app — all routes & logic
├── requirements.txt          # Dependencies
├── Procfile                  # For Railway/Heroku deployment
├── .env.example              # Copy to .env and fill values
├── .gitignore                # Prevents secrets from going to GitHub
├── database/
│   ├── db.py                 # SQLite init, connections, seed data
│   ├── __init__.py
│   └── fundaaz.db            # Auto-created on first run
├── templates/
│   ├── index.html            # Landing page
│   ├── admin.html            # Admin dashboard (7 tabs including Progress Search)
│   └── student.html          # Student portal
└── static/
    ├── css/
    │   ├── main.css          # Global styles
    │   └── dashboard.css     # Dashboard layout + progress tab styles
    └── js/
        ├── dashboard.js      # Tab switching, modals, quickProgress()
        ├── charts.js         # Student portal charts
        └── admin_charts.js   # Admin progress tab charts
```

---

## 🚀 Run Locally (VS Code)

```bash
# 1. Open the fundaaz/ folder in VS Code
# 2. Open terminal (Ctrl + `)

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy env file and set your secret key
cp .env.example .env
# Edit .env — replace SECRET_KEY with output of:
python -c "import secrets; print(secrets.token_hex(32))"

# 5. Run
python app.py

# 6. Open browser
# http://127.0.0.1:5000
```

---

## 🔐 Default Credentials

| Role    | Login ID  | Password   |
|---------|-----------|------------|
| Admin   | `admin`   | `admin@321` |
| Student | `aarav01` | `pass123`  |
| Student | `priya01` | `pass123`  |
| Student | `rajan01` | `pass123`  |

**Change the admin password immediately after first login.**

---

## 🌐 Deploy to Render (with Custom Domain)

1. Push your code to GitHub (`.env` and `fundaaz.db` are in `.gitignore` — safe)

2. Go to https://render.com → New → Web Service → Connect your GitHub repository

3. Configure your service:
   - Environment: Python
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app` (or your main file)

4. Add environment variables in Render Dashboard:
   - `SECRET_KEY` = your generated key
   - `FLASK_ENV` = `production`

5. Add a Persistent Disk:
   - Go to Settings → Disks
   - Mount Path: `/app/database`

6. Deploy the service (Render will automatically build and deploy your app)

7. Add Custom Domain:
   - Go to Settings → Custom Domains
   - Add your domain name

8. Update your domain registrar DNS:
   - Add the required records (CNAME or A record as provided by Render)

9. Render automatically provisions SSL — your site will run on HTTPS

---

## 🔒 Security Features

| Feature | Status |
|---------|--------|
| SHA-256 password hashing | ✅ |
| Session-based auth with signed cookies | ✅ |
| HTTPOnly + SameSite cookie flags | ✅ |
| Secure cookie flag (HTTPS only in prod) | ✅ |
| Server-side role enforcement on every route | ✅ |
| Parameterized SQL queries (no injection) | ✅ |
| Secret key via environment variable | ✅ |
| Debug mode off in production | ✅ |
| Rate limiting (flask-limiter) | ✅ install included |
| HTTPS enforcement (flask-talisman) | ✅ install included |
| .gitignore protects .env and database | ✅ |
