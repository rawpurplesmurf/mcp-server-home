#!/bin/bash

# MySQL Setup Script for MCP Chat
# This script helps configure MySQL for the feedback system

set -e

echo "🗄️  MCP Chat - MySQL Setup"
echo "=========================="
echo ""

# Check if MySQL is installed
if ! command -v mysql &> /dev/null; then
    echo "❌ MySQL is not installed."
    echo ""
    echo "Please install MySQL first:"
    echo "  macOS:  brew install mysql && brew services start mysql"
    echo "  Linux:  sudo apt-get install mysql-server"
    exit 1
fi

echo "✅ MySQL is installed"
echo ""

# Prompt for root password
echo "Please enter your MySQL root password:"
read -s MYSQL_ROOT_PASSWORD
echo ""

# Test root connection
if ! mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "SELECT 1;" &> /dev/null; then
    echo "❌ Failed to connect to MySQL with root credentials"
    exit 1
fi

echo "✅ Connected to MySQL successfully"
echo ""

# Prompt for new user details
echo "Enter the database name [default: mcp_chat]:"
read DB_NAME
DB_NAME=${DB_NAME:-mcp_chat}

echo "Enter the username for the application [default: mcp_user]:"
read DB_USER
DB_USER=${DB_USER:-mcp_user}

echo "Enter the password for user '$DB_USER':"
read -s DB_PASSWORD

if [ -z "$DB_PASSWORD" ]; then
    echo "❌ Password cannot be empty"
    exit 1
fi
echo ""

# Create database and user
echo "Creating database and user..."
mysql -u root -p"$MYSQL_ROOT_PASSWORD" << EOF
CREATE DATABASE IF NOT EXISTS $DB_NAME CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '$DB_USER'@'localhost' IDENTIFIED BY '$DB_PASSWORD';
GRANT ALL PRIVILEGES ON $DB_NAME.* TO '$DB_USER'@'localhost';
FLUSH PRIVILEGES;
EOF

echo "✅ Database '$DB_NAME' created"
echo "✅ User '$DB_USER' created with privileges"
echo ""

# Load schema
echo "Loading database schema..."
if [ -f "schema.sql" ]; then
    mysql -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" < schema.sql
    echo "✅ Schema loaded successfully"
else
    echo "⚠️  schema.sql not found - you'll need to load it manually"
fi
echo ""

# Update .env file
echo "Updating .env file..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✅ Created .env from .env.example"
    else
        echo "⚠️  No .env or .env.example file found"
    fi
fi

if [ -f ".env" ]; then
    # Update MySQL settings in .env
    sed -i.bak "s/^MYSQL_DATABASE=.*/MYSQL_DATABASE=$DB_NAME/" .env
    sed -i.bak "s/^MYSQL_USER=.*/MYSQL_USER=$DB_USER/" .env
    sed -i.bak "s/^MYSQL_PASSWORD=.*/MYSQL_PASSWORD=$DB_PASSWORD/" .env
    rm .env.bak 2>/dev/null || true
    echo "✅ Updated .env with MySQL credentials"
else
    echo ""
    echo "⚠️  No .env file to update. Please create .env with:"
    echo "MYSQL_HOST=localhost"
    echo "MYSQL_PORT=3306"
    echo "MYSQL_DATABASE=$DB_NAME"
    echo "MYSQL_USER=$DB_USER"
    echo "MYSQL_PASSWORD=$DB_PASSWORD"
    echo "MYSQL_POOL_SIZE=5"
fi
echo ""

# Install Python dependencies
echo "Installing Python dependencies..."
if [ -f "requirements.txt" ]; then
    if [ -d ".venv" ]; then
        source .venv/bin/activate
        pip install -q aiomysql
        echo "✅ Installed aiomysql Python package"
    else
        echo "⚠️  Virtual environment not found. Run: pip install aiomysql"
    fi
else
    echo "⚠️  requirements.txt not found"
fi
echo ""

# Test connection
echo "Testing database connection..."
python3 << EOF
try:
    import pymysql
    connection = pymysql.connect(
        host='localhost',
        user='$DB_USER',
        password='$DB_PASSWORD',
        database='$DB_NAME'
    )
    cursor = connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM interactions")
    connection.close()
    print("✅ Successfully connected to database")
    print("✅ Schema tables are accessible")
except ImportError:
    print("⚠️  pymysql not installed (optional - aiomysql is used by the app)")
except Exception as e:
    print(f"❌ Connection test failed: {e}")
EOF
echo ""

echo "✅ MySQL setup complete!"
echo ""
echo "Next steps:"
echo "1. Restart the MCP client to connect to MySQL"
echo "2. Check logs for: 'MySQL connection pool initialized'"
echo "3. Test the feedback system in the UI (👍 👎 buttons)"
echo ""
echo "View your interactions:"
echo "  mysql -u $DB_USER -p $DB_NAME -e 'SELECT * FROM interactions LIMIT 5;'"
echo ""
