# Docker Compose Deployment

## Services

- `app`: Flask + Gunicorn application container
- `db`: MySQL 8.4 database container
- `nginx`: reverse proxy in front of the app

## 1. Create your environment file

Copy the example file:

```bash
cp .env.example .env
```

Update these values in `.env` before production use:

- `APP_IMAGE`
- `MYSQL_USER`
- `MYSQL_PASSWORD`
- `MYSQL_ROOT_PASSWORD`
- `FLASK_SECRET_KEY`
- `NGINX_PORT`

## 2. Start the full stack

From the project root:

```bash
docker compose up --build -d
```

Then open:

```text
http://localhost
```

Or if you changed `NGINX_PORT`, use that port instead.

## 3. Stop the stack

```bash
docker compose down
```

To also remove the database volume:

```bash
docker compose down -v
```

## 4. Database initialization

The file `db/students.sql` is mounted into MySQL init scripts.

Important:

- It runs only when the MySQL data volume is empty.
- If you already started MySQL once, changes to `db/students.sql` will not re-import automatically.
- To reinitialize from scratch, run `docker compose down -v` and start again.

## 5. Build and push the app image to Docker Hub

Login first:

```bash
docker login
```

Build the image:

```bash
docker compose build app
```

Push using the image name from `.env`:

```bash
docker compose push app
```

You can also build and push manually:

```bash
docker build -t yourdockerhubusername/institute-management-system:latest ./app
docker push yourdockerhubusername/institute-management-system:latest
```

## 6. Useful checks

See running containers:

```bash
docker compose ps
```

See logs:

```bash
docker compose logs -f app
docker compose logs -f db
docker compose logs -f nginx
```
