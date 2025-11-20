# PgAdmin Connection Fix Guide

## The Issue

PgAdmin connection is failing even though PostgreSQL is running. This is typically because:

1. Network configuration differences
2. PostgreSQL authentication settings
3. Using wrong connection parameters

## Solution: Use Correct Connection Parameters

Since pgAdmin is accessed via browser (localhost:5050), the connection is made from **your host machine**, not from within Docker.

### Correct Connection Settings in PgAdmin:

1. **Right-click** "Servers" → **Register** → **Server**

2. **General Tab:**

   - Name: `KingdomPay Database`

3. **Connection Tab:**

   ```
   Host name/address: 127.0.0.1    ← Use 127.0.0.1 (IPv4) not localhost
   Port: 5433                       ← Important: Port 5433 (not 5432)
   Maintenance database: kingdompay
   Username: admin
   Password: admin123
   ```

   - ✅ Check **"Save password"**

4. Click **"Save"**

### Why These Settings Work:

- **Host:** `127.0.0.1` uses IPv4 explicitly (avoids IPv6 issues)
- **Port:** `5433` is the Docker-mapped port (container uses 5432, host uses 5433)
- **Database:** `kingdompay` is the database name

## Alternative: Connect Using Container Network

If you want pgAdmin to connect via Docker network (internal):

1. **Host name/address:** `host.docker.internal` (Mac/Windows) or `172.17.0.1` (Linux)
2. **Port:** `5433`
3. Rest of settings same as above

## Verify Connection from Command Line

Test that connection works:

```bash
# Test PostgreSQL is accessible
nc -zv 127.0.0.1 5433

# Test connection with psql (if installed)
psql -h 127.0.0.1 -p 5433 -U admin -d kingdompay
# Password: admin123
```

## If Still Not Working

### Option 1: Use Docker Network Connection

Edit `docker-compose.yml` to ensure pgAdmin and PostgreSQL are on the same network:

```yaml
pgadmin:
  # ... existing config ...
  networks:
    - default # Same network as postgres
```

Then in pgAdmin, use:

- **Host:** `postgres` (container name)
- **Port:** `5432` (internal container port)

### Option 2: Check PostgreSQL Logs

```bash
docker logs kingdompay_postgres | tail -50
```

Look for connection refused errors or authentication issues.

### Option 3: Test Direct Connection

```bash
# From host machine
docker exec kingdompay_postgres psql -U admin -d kingdompay -c "SELECT 1;"

# Should work - this connects from inside container
```

### Option 4: Restart PostgreSQL

```bash
docker-compose restart postgres
# Wait a few seconds
docker-compose ps postgres  # Verify it's healthy
```

## Quick Reference

### From Browser (PgAdmin UI):

- **Host:** `127.0.0.1`
- **Port:** `5433`
- **Database:** `kingdompay`
- **User:** `admin`
- **Password:** `admin123`

### From Host Command Line:

```bash
psql -h 127.0.0.1 -p 5433 -U admin -d kingdompay
```

### From Inside Docker:

```bash
docker exec -it kingdompay_postgres psql -U admin -d kingdompay
```
