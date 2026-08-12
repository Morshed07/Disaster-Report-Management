# Production Deployment Guide — VPS (191.218.162.194)

This guide provides step-by-step instructions to deploy the **Bevingshulp Noord** Django application on your VPS (`191.218.162.194`) using **Docker Compose, Nginx, Gunicorn, PostgreSQL, Redis, and Celery**.

---

## 🚀 Quick Start Deployment Steps

### Step 1: Connect to your VPS via SSH
```bash
ssh root@191.218.162.194
```

---

### Step 2: Install Docker & Docker Compose (if not already installed)
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
docker --version
docker compose version
```

---

### Step 3: Clone or Copy the Repository onto VPS
```bash
git clone <YOUR_GIT_REPOSITORY_URL> /var/www/disaster_management
cd /var/www/disaster_management
```

---

### Step 4: Configure Environment File (`.env`)
Edit `.env` if you need to update any passwords or API keys:
```bash
nano .env
```

---

### Step 5: Build and Launch Containers
Run Docker Compose in detached mode using `docker-compose.prod.yml`:
```bash
docker compose up -d --build
```

This will automatically start:
1. `db`: PostgreSQL 16
2. `redis`: Redis 7
3. `web`: Django Gunicorn application (runs `migrate` & `collectstatic` automatically)
4. `celery_worker`: Celery background task worker
5. `celery_beat`: Celery scheduled task beat
6. `nginx`: Nginx reverse proxy listening on port 80

---

### Step 6: Create Admin Superuser
Create an admin user for Django admin panel:
```bash
docker compose exec web python manage.py createsuperuser
```

---

## 🌐 Verifying Deployment

Once deployed, your application is live at:

* **Frontend Web App**: `http://bevingshulpnoord.com/` (or `http://www.bevingshulpnoord.com/`)
* **Backend API Base**: `http://backend.bevingshulpnoord.com/`
* **Google Reviews API**: `http://backend.bevingshulpnoord.com/api/v1/reviews/google/`
* **Google Write Review Link**: `http://backend.bevingshulpnoord.com/api/v1/reviews/google/write-url/`
* **Damage Reports API**: `http://backend.bevingshulpnoord.com/api/v1/reports/`
* **ActiveCampaign Webhook**: `http://backend.bevingshulpnoord.com/api/v1/webhooks/activecampaign/?secret=bevingshulpnoord-webhook-secret-2026`
* **Django Admin**: `http://backend.bevingshulpnoord.com/admin/`

---

## 🛠️ Management Commands

### Check Container Status
```bash
docker compose ps
```

### View Application & Task Logs
```bash
# View all logs in real-time
docker compose logs -f

# View web container logs
docker compose logs -f web

# View Celery worker logs
docker compose logs -f celery_worker
```

### Restart Services
```bash
docker compose restart
```

---

## 🔐 SSL/HTTPS Setup with Certbot (Dockerized)

Once DNS `A` record for `backend.bevingshulpnoord.com` points to IP `191.218.162.194`:

### Step 1: Issue Initial SSL Certificate via Certbot Container
Run the following Docker Compose command on your VPS to request the SSL certificate:
```bash
docker compose run --rm certbot certonly --webroot --webroot-path=/var/www/certbot -d backend.bevingshulpnoord.com --email info@bevingshulpnoord.nl --agree-tos --no-eff-email
```

### Step 2: Enable HTTPS Block in Nginx
Open `nginx/conf.d/app.conf`:
```bash
nano nginx/conf.d/app.conf
```
Uncomment the HTTPS `server` block (lines 40 to 80), then save and exit.

### Step 3: Reload Nginx Container
Reload Nginx to apply HTTPS:
```bash
docker compose exec nginx nginx -s reload
```

### Step 4: Automatic Renewal
The `certbot` service in `docker-compose.yml` automatically checks and renews certificates every 12 hours.
To test renewal manually:
```bash
docker compose run --rm certbot renew --dry-run
```




