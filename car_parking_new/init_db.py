import sqlite3

# Connect to SQLite database (creates the file if it doesn't exist)
conn = sqlite3.connect("parking.db")
cur = conn.cursor()

# Create a table for storing user accounts
cur.execute('''
    CREATE TABLE IF NOT EXISTS customer (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL
    )
''')

# Create a table for storing parking bookings
cur.execute('''
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        slot TEXT NOT NULL,
        registration_number TEXT NOT NULL,
        start_time DATETIME NOT NULL,
        end_time DATETIME NOT NULL
    )
''')

# Commit changes and close connection
conn.commit()
conn.close()

print("Database and tables created successfully.")
