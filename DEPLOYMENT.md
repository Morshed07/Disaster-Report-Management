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

### Step 4: Configure Production Environment File (`.env.production`)
Copy the provided template:
```bash
cp .env.production.example .env.production
```

Edit `.env.production` if you need to update any passwords or API keys:
```bash
nano .env.production
```

---

### Step 5: Build and Launch Containers
Run Docker Compose in detached mode using `docker-compose.prod.yml`:
```bash
docker compose -f docker-compose.prod.yml up -d --build
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
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

---

## 🌐 Verifying Deployment

Once deployed, your application is live at:

* **Google Reviews API**: `http://191.218.162.194/api/v1/reviews/google/`
* **Google Write Review Link**: `http://191.218.162.194/api/v1/reviews/google/write-url/`
* **Damage Reports API**: `http://191.218.162.194/api/v1/reports/`
* **ActiveCampaign Webhook**: `http://191.218.162.194/api/v1/webhooks/activecampaign/?secret=bevingshulpnoord-webhook-secret-2026`
* **Django Admin**: `http://191.218.162.194/admin/`

---

## 🛠️ Management Commands

### Check Container Status
```bash
docker compose -f docker-compose.prod.yml ps
```

### View Application & Task Logs
```bash
# View all logs in real-time
docker compose -f docker-compose.prod.yml logs -f

# View web container logs
docker compose -f docker-compose.prod.yml logs -f web

# View Celery worker logs
docker compose -f docker-compose.prod.yml logs -f celery_worker
```

### Restart Services
```bash
docker compose -f docker-compose.prod.yml restart
```

---

## 🔐 Optional: SSL/HTTPS Setup with Certbot (When domain is added)

If you connect a domain name (e.g. `api.bevingshulpnoord.nl`) to IP `191.218.162.194`:

1. Install Certbot on VPS:
   ```bash
   apt-get install -y certbot python3-certbot-nginx
   ```
2. Obtain SSL certificate:
   ```bash
   certbot --nginx -d api.bevingshulpnoord.nl
   ```
