# Online Bookstore - Deploy-ready package

This package is configured for deployment (Railway recommended).

## Quick start (local/test)

1. Copy `.env.example` to `.env` and fill values (especially DATABASE_URL and Gmail app password).
2. Create virtualenv and install requirements:
   ```bash
   pip install -r requirements.txt
   ```
3. Run app:
   ```bash
   python app.py
   ```

## Default admin

- email: admin@bookstore.com
- password: admin123

