import psycopg2

# Connect to your PostgreSQL database
conn = psycopg2.connect(
    dbname="homeservice", 
    user="myuser", 
    password="mypassword", 
    host="localhost", 
    port="5432"
)
cur = conn.cursor()

# Grant privileges
cur.execute("GRANT ALL PRIVILEGES ON SCHEMA public TO myuser;")
cur.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO myuser;")

# Commit and close connection
conn.commit()
cur.close()
conn.close()
