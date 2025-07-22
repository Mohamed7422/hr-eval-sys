# 1) Base image: small, up‑to‑date Python
FROM python:3.12-slim

# 2) Prevent Python from buffering stdout/stderr
ENV PYTHONUNBUFFERED=1

# 3) Use the PORT Vercel (or any host) gives you; default to 8000
ENV PORT=8000

# 4) Set workdir and copy dependency list
WORKDIR /app
COPY requirements.txt .

# 5) Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 6) Copy your project code
COPY . .

# 7) Collect static files (if you’ve configured STATIC_ROOT & WhiteNoise)
RUN python manage.py collectstatic --no-input

# 8) On container start: apply migrations, then run Gunicorn on $PORT
CMD python manage.py migrate --no-input \
    && gunicorn hr_evaluation.wsgi:application --bind 0.0.0.0:$PORT
