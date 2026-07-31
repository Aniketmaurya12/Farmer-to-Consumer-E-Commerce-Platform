# Farmer-to-Consumer-E-Commerce-Platform
A Flask-based marketplace web app connecting farmers directly with buyers — farmers list fresh produce, buyers browse and purchase. Built with Flask, SQLAlchemy, and Flask-Login.
# Farm Marketplace

A Flask-based marketplace web app that connects farmers directly with buyers. Farmers can list produce for sale, and buyers can browse and purchase fresh vegetables and fruits.

## Features

- User authentication (buyers and farmers) via Flask-Login
- Farmer product listings with image uploads
- SQLite database via SQLAlchemy
- Auto-generated placeholder product images

## Tech Stack

- Flask 2.2.5
- Flask-SQLAlchemy
- Flask-Login
- SQLite
- Gunicorn (production server)

## Local Setup

1. Clone the repo:
   ```bash
   git clone https://github.com/<your-username>/farm-marketplace.git
   cd farm-marketplace
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set environment variables (recommended):
   ```bash
   export SECRET_KEY="your-random-secret-key"   # Windows: set SECRET_KEY=your-random-secret-key
   ```

5. Generate default placeholder images:
   ```bash
   python create_default_images.py
   ```

6. Run the app:
   ```bash
   python app.py
   ```

   The app will create `marketplace.db` automatically on first run.

7. Visit `http://localhost:5000` in your browser.

## Production Deployment

This project includes a `Procfile` for Gunicorn-based deployment (Heroku, Render, Railway, etc.):

```
web: gunicorn app:app
```

Make sure to set a strong `SECRET_KEY` environment variable in your hosting platform's config — do not rely on the development fallback key.

## Project Structure

```
.
├── app.py                     # Main Flask application
├── create_default_images.py   # Generates placeholder product images
├── requirements.txt           # Python dependencies
├── Procfile                   # Gunicorn start command for deployment
├── templates/                 # Jinja2 HTML templates
└── static/                    # CSS, JS, uploaded & default images
```

## Notes

- `marketplace.db` and uploaded images are excluded from version control (see `.gitignore`) since they contain runtime/user data. The database is created automatically when the app first runs.
- Max upload size is capped at 16MB.
