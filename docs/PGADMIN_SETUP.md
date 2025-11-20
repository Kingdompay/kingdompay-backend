# PgAdmin Setup Guide

## Accessing PgAdmin

PgAdmin is already configured in `docker-compose.yml` and can be started easily.

### 1. Start PgAdmin

```bash
cd kingdompay-backend
docker-compose --profile tools up -d pgadmin
```

### 2. Access PgAdmin Web Interface

Open your browser and go to:
```
http://localhost:5050
```

### 3. Login Credentials

- **Email:** `admin@kingdompay.com`
- **Password:** `admin123`

### 4. Connect to PostgreSQL Database

Once logged into pgAdmin:

1. **Right-click** on "Servers" in the left sidebar
2. Select **"Register" → "Server"**

3. Fill in the **General** tab:
   - **Name:** `KingdomPay Database` (or any name you prefer)

4. Fill in the **Connection** tab:
   - **Host name/address:** `postgres` (container name) or `localhost` if connecting from host
   - **Port:** `5432`
   - **Maintenance database:** `kingdompay`
   - **Username:** `admin`
   - **Password:** `admin123`
   - ☑ **Save password** (optional, for convenience)

5. Click **"Save"**

### 5. View Tables

Once connected:

1. Expand **Servers** → **KingdomPay Database** → **Databases** → **kingdompay** → **Schemas** → **public** → **Tables**
2. You'll see all 23 tables listed
3. Right-click on any table to:
   - **View/Edit Data** → **All Rows** - View table contents
   - **Properties** - View table structure, columns, indexes
   - **Scripts** → **CREATE Script** - View table creation SQL

## Quick Reference

### Start PgAdmin
```bash
docker-compose --profile tools up -d pgadmin
```

### Stop PgAdmin
```bash
docker-compose --profile tools stop pgadmin
```

### View PgAdmin Logs
```bash
docker-compose --profile tools logs pgadmin
```

### Access URL
- **PgAdmin:** http://localhost:5050
- **PostgreSQL (direct):** localhost:5433

### Database Connection Info
- **Host:** `postgres` (from inside Docker) or `localhost` (from host)
- **Port:** `5432` (container) or `5433` (host)
- **Database:** `kingdompay`
- **User:** `admin`
- **Password:** `admin123`

## Troubleshooting

### PgAdmin won't start
```bash
# Check if port 5050 is already in use
lsof -i :5050

# View logs
docker-compose --profile tools logs pgadmin
```

### Can't connect to database
- Make sure PostgreSQL container is running: `docker-compose ps postgres`
- If connecting from host machine, use `localhost` as host and port `5433`
- If connecting from pgAdmin container, use `postgres` as host and port `5432`

### Forgot password
- PgAdmin login: `admin@kingdompay.com` / `admin123`
- These are set in `docker-compose.yml` under `PGADMIN_DEFAULT_EMAIL` and `PGADMIN_DEFAULT_PASSWORD`

## Viewing Tables in PgAdmin

### Method 1: View Data (Recommended)
1. Navigate to the table (e.g., `users`)
2. Right-click → **View/Edit Data** → **All Rows**
3. You'll see a spreadsheet-like view of all data

### Method 2: Query Tool
1. Right-click on database `kingdompay`
2. Select **Query Tool**
3. Type: `SELECT * FROM users LIMIT 10;`
4. Press F5 or click Execute (▶)

### Method 3: Properties View
1. Right-click on table → **Properties**
2. View **Columns** tab for structure
3. View **Indexes** tab for indexes
4. View **Constraints** tab for foreign keys

## Common SQL Queries in PgAdmin

### List all tables
```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public'
ORDER BY table_name;
```

### View table structure
```sql
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'users'
ORDER BY ordinal_position;
```

### Count rows in all tables
```sql
SELECT 
    schemaname,
    tablename,
    n_tup_ins - n_tup_del as row_count
FROM pg_stat_user_tables
ORDER BY tablename;
```

