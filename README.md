# Farmer-to-Consumer-E-Commerce-Platform
A Flask-based marketplace web app connecting farmers directly with buyers — farmers list fresh produce, buyers browse and purchase. Built with Flask, SQLAlchemy, and Flask-Login.
# Farm Marketplace

A Flask-based marketplace web app that connects farmers directly with buyers. Farmers can list produce for sale, and buyers can browse and purchase fresh vegetables and fruits.

## Features

- User authentication (buyers and farmers) via Flask-Login
- Farmer product listings with image uploads
- **My Products** page where a farmer can edit or delete any of their own listings
- Unlimited listings per category
- Product photos stored in the database, so they survive on read-only serverless hosts
- Seasonal vegetable and fruit cards, each with its own picture
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

6. (Optional) Regenerate the seasonal home-page pictures:
   ```bash
   python create_seasonal_images.py
   ```
   They are already committed under `static/images/seasonal/`. To use a **real
   photograph** instead of the drawing, drop a file named after the item into that
   folder, e.g. `static/images/seasonal/tomatoes.jpg` or `mangoes.png` - the app
   prefers a real photo over the drawing automatically, no code change needed.

7. Run the app:
   ```bash
   python app.py
   ```

   The app will create `marketplace.db` automatically on first run.

8. Visit `http://localhost:5000` in your browser.

## Deploying to Vercel

Vercel serves the deployment from a **read-only filesystem**. That has two
consequences, and both bite the moment a farmer tries to add, edit or delete a
product:

1. **SQLite will not work there.** Writing to the bundled `marketplace.db`
   fails with `attempt to write a readonly database`, so registration, listing
   a product, editing it, deleting it and placing an order all fail. You must
   point the app at a hosted Postgres database.
2. **Uploaded photos cannot be written to `static/uploads/`.** Product photos
   are therefore stored **in the database** instead: `ProductImage` holds the
   bytes and `/product_image/<id>` serves them. Uploads are re-encoded to a
   max 1200 px JPEG first, so a phone photo lands at a couple of hundred KB
   rather than several MB. No object storage or extra service is needed, and
   it behaves identically on your own machine.

### Steps

1. `vercel.json` in this repo already tells Vercel how to build the Flask app,
   so importing the GitHub repo at <https://vercel.com/new> is enough - pick
   the repo and deploy. Every later `git push origin main` redeploys it.

2. Create a free Postgres database (Neon, Supabase and Vercel Postgres all have
   a free tier) and copy its connection string.

3. In Vercel: **Project → Settings → Environment Variables**, add

   | Name           | Value                                              |
   | -------------- | -------------------------------------------------- |
   | `DATABASE_URL` | the Postgres connection string from step 2         |
   | `SECRET_KEY`   | any long random string                             |

   `postgres://` connection strings are converted to `postgresql://`
   automatically, so either form works.

4. Redeploy (**Deployments → ⋯ → Redeploy**). Tables are created on the first
   request, so the first page load may take a second longer than usual.

Without step 3 the site still loads and browses, but every write fails - which
is exactly what "I can't edit or delete my product" looks like from a farmer's
side.

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
├── create_seasonal_images.py  # Draws a picture for every seasonal item
├── requirements.txt           # Python dependencies
├── Procfile                   # Gunicorn start command for deployment
├── vercel.json                # Vercel build + routing config
├── templates/                 # Jinja2 HTML templates
└── static/                    # CSS, JS, uploaded & default images
```

## Notes

- `marketplace.db` and uploaded images are excluded from version control (see `.gitignore`) since they contain runtime/user data. The database is created automatically when the app first runs.
- Max upload size is capped at 16MB.
