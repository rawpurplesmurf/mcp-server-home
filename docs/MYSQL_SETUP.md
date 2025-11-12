# MySQL Setup for MCP Chat Feedback

This document explains how to set up MySQL for permanent storage of thumbs-up interactions.

## Overview

The feedback system uses a two-tier storage approach:

1. **Redis** (short-term, fast cache):
   - All interactions stored for 24 hours by default
   - Thumbs-up: stored permanently (no TTL)
   - Thumbs-down: deleted immediately

2. **MySQL** (long-term, permanent storage):
   - Thumbs-up interactions stored forever
   - Thumbs-down feedback stored for analysis
   - Provides analytics and search capabilities

## Prerequisites

- MySQL 5.7+ or MariaDB 10.2+
- Python package `aiomysql` (included in requirements.txt)

## Installation Steps

### 1. Install MySQL (if not already installed)

**macOS** (using Homebrew):
```bash
brew install mysql
brew services start mysql
```

**Linux** (Ubuntu/Debian):
```bash
sudo apt-get update
sudo apt-get install mysql-server
sudo systemctl start mysql
```

### 2. Secure MySQL Installation

```bash
sudo mysql_secure_installation
```

Follow the prompts to set a root password and secure your installation.

### 3. Create Database and User

Login to MySQL as root:
```bash
mysql -u root -p
```

Create the database and user:
```sql
CREATE DATABASE mcp_chat CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'mcp_user'@'localhost' IDENTIFIED BY 'your_secure_password_here';
GRANT ALL PRIVILEGES ON mcp_chat.* TO 'mcp_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### 4. Load the Schema

Load the schema from the provided SQL file:
```bash
mysql -u mcp_user -p mcp_chat < schema.sql
```

Enter the password you set in step 3 when prompted.

### 5. Configure Environment Variables

Copy `.env.example` if you haven't already:
```bash
cp .env.example .env
```

Edit `.env` and add your MySQL credentials:
```bash
# MySQL Configuration
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=mcp_chat
MYSQL_USER=mcp_user
MYSQL_PASSWORD=your_secure_password_here
MYSQL_POOL_SIZE=5
```

### 6. Install Python Dependencies

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

This will install `aiomysql` and its dependencies.

### 7. Restart the Client

```bash
# If using npm start
npm start

# Or manually restart the client
.venv/bin/uvicorn client:app --reload --port 8001
```

Check the logs for successful MySQL connection:
```
INFO:__main__:MySQL connection pool initialized: mcp_user@localhost:3306/mcp_chat
```

## Database Schema

### Tables

#### `interactions`
Stores all thumbs-up approved interactions permanently.

**Key columns**:
- `interaction_id`: Unique identifier for the interaction
- `session_id`: User session identifier
- `user_message`: The user's original question
- `final_response`: The assistant's response
- `routing_type`: How the request was handled (direct_shortcut, llm_with_tools, llm_only)
- `tools_used`: JSON array of tools that were called
- `tool_results`: JSON object with tool execution results
- `llm_payload`: JSON object with the prompt sent to LLM
- `llm_response`: Raw response from LLM
- `feedback`: Always 'thumbs_up' for this table
- `created_at`, `updated_at`: Timestamps

**Indexes**:
- Primary key on `id`
- Unique index on `interaction_id`
- Indexes on `session_id`, `routing_type`, `created_at`, `feedback`
- Full-text indexes on `user_message` and `final_response`

#### `negative_feedback`
Stores thumbs-down feedback for analysis.

**Key columns**:
- `interaction_id`: Unique identifier
- `session_id`: User session
- `user_message`, `final_response`: What failed
- `routing_type`: How it was processed
- `reason`: Why it was marked down
- `created_at`: When feedback was given

#### `feedback_stats`
Daily aggregated statistics (can be populated via scheduled job).

**Columns**:
- `date`: Date of statistics
- `total_interactions`: Total count for the day
- `thumbs_up_count`, `thumbs_down_count`: Feedback counts
- `direct_shortcut_count`, `llm_with_tools_count`, `llm_only_count`: Routing type counts

### Views

#### `feedback_summary`
Aggregated view showing interaction counts by routing type and date.

```sql
SELECT * FROM feedback_summary 
WHERE date >= DATE_SUB(CURRENT_DATE, INTERVAL 7 DAY)
ORDER BY date DESC;
```

#### `tool_usage_stats`
Shows which tools are used most frequently.

```sql
SELECT tool_name, SUM(usage_count) as total_usage
FROM tool_usage_stats
GROUP BY tool_name
ORDER BY total_usage DESC;
```

## Usage Examples

### Query Successful Interactions

```sql
-- Find all thumbs-up interactions from the last 7 days
SELECT 
    interaction_id,
    user_message,
    routing_type,
    tools_used,
    created_at
FROM interactions
WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
ORDER BY created_at DESC;
```

### Analyze Failed Interactions

```sql
-- See what types of requests get thumbs-down
SELECT 
    routing_type,
    COUNT(*) as failure_count,
    AVG(CHAR_LENGTH(user_message)) as avg_message_length
FROM negative_feedback
GROUP BY routing_type
ORDER BY failure_count DESC;
```

### Search by Content

```sql
-- Full-text search for specific topics
SELECT 
    user_message,
    final_response,
    routing_type,
    created_at
FROM interactions
WHERE MATCH(user_message) AGAINST('temperature sensors' IN NATURAL LANGUAGE MODE)
ORDER BY created_at DESC
LIMIT 10;
```

### Tool Performance

```sql
-- Which tools are in successful interactions?
SELECT 
    tool_name,
    COUNT(*) as success_count
FROM (
    SELECT JSON_UNQUOTE(JSON_EXTRACT(tools_used, CONCAT('$[', numbers.n, ']'))) as tool_name
    FROM interactions
    CROSS JOIN (
        SELECT 0 as n UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4
    ) as numbers
    WHERE JSON_LENGTH(tools_used) > numbers.n
) as tool_list
WHERE tool_name IS NOT NULL
GROUP BY tool_name
ORDER BY success_count DESC;
```

## Maintenance

### Backup Database

```bash
mysqldump -u mcp_user -p mcp_chat > mcp_chat_backup_$(date +%Y%m%d).sql
```

### Restore Database

```bash
mysql -u mcp_user -p mcp_chat < mcp_chat_backup_YYYYMMDD.sql
```

### Clean Old Negative Feedback

Negative feedback is kept for analysis but you may want to archive old entries:

```sql
-- Archive negative feedback older than 90 days
DELETE FROM negative_feedback 
WHERE created_at < DATE_SUB(NOW(), INTERVAL 90 DAY);
```

### Optimize Tables

Run periodically to optimize indexes:

```sql
OPTIMIZE TABLE interactions;
OPTIMIZE TABLE negative_feedback;
```

## Troubleshooting

### Connection Errors

**Error**: `Can't connect to MySQL server`
- Check MySQL is running: `brew services list` (macOS) or `systemctl status mysql` (Linux)
- Verify credentials in `.env` file
- Check firewall settings if MySQL is on a remote host

**Error**: `Access denied for user 'mcp_user'@'localhost'`
- Verify password in `.env` matches what you set in MySQL
- Re-grant privileges: `GRANT ALL PRIVILEGES ON mcp_chat.* TO 'mcp_user'@'localhost';`

### Missing Tables

If tables don't exist, reload the schema:
```bash
mysql -u mcp_user -p mcp_chat < schema.sql
```

### Performance Issues

If queries are slow:
1. Check indexes: `SHOW INDEX FROM interactions;`
2. Analyze query performance: `EXPLAIN SELECT ...;`
3. Increase connection pool size in `.env`: `MYSQL_POOL_SIZE=10`

## Optional: External MySQL Server

To use a remote MySQL server:

1. Update `.env`:
```bash
MYSQL_HOST=your-mysql-server.com
MYSQL_PORT=3306
MYSQL_USER=mcp_user
MYSQL_PASSWORD=your_password
```

2. On the MySQL server, allow remote connections:
```sql
CREATE USER 'mcp_user'@'%' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON mcp_chat.* TO 'mcp_user'@'%';
FLUSH PRIVILEGES;
```

3. Update MySQL configuration (`/etc/mysql/my.cnf`):
```ini
[mysqld]
bind-address = 0.0.0.0
```

4. Restart MySQL and ensure firewall allows port 3306.

## Security Best Practices

1. **Use strong passwords** for MySQL users
2. **Limit privileges** - don't use root for the application
3. **Use SSL** for remote connections
4. **Regular backups** - schedule daily backups
5. **Monitor access** - review MySQL logs regularly
6. **Keep updated** - apply security patches to MySQL

## Next Steps

Once MySQL is set up:
1. Test the feedback system in the UI (👍 👎 buttons)
2. Check MySQL to see interactions being stored: `SELECT COUNT(*) FROM interactions;`
3. Set up scheduled backups
4. Create dashboards for analytics (optional)
