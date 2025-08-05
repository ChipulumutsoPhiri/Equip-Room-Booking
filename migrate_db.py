import sqlite3
import os

def migrate_database():
    """Migrate the database from team_name to name + agenda structure"""
    
    # Connect to the database
    conn = sqlite3.connect('meeting_room.db')
    c = conn.cursor()
    
    try:
        # Check if the old structure exists
        c.execute("PRAGMA table_info(bookings)")
        columns = [column[1] for column in c.fetchall()]
        
        if 'team_name' in columns and 'name' not in columns:
            print("Migrating database from old structure to new structure...")
            
            # Create new table with updated structure
            c.execute('''CREATE TABLE bookings_new
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          name TEXT NOT NULL,
                          agenda TEXT NOT NULL,
                          date TEXT NOT NULL,
                          start_time TEXT NOT NULL,
                          end_time TEXT NOT NULL,
                          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            
            # Copy existing data (team_name becomes name, agenda gets default value)
            c.execute('''INSERT INTO bookings_new (id, name, agenda, date, start_time, end_time, created_at)
                         SELECT id, team_name, 'Migrated booking', date, start_time, end_time, created_at
                         FROM bookings''')
            
            # Drop old table and rename new table
            c.execute('DROP TABLE bookings')
            c.execute('ALTER TABLE bookings_new RENAME TO bookings')
            
            print("Migration completed successfully!")
            print("Note: Existing bookings have 'Migrated booking' as their agenda.")
            
        elif 'name' in columns and 'agenda' in columns:
            print("Database is already using the new structure. No migration needed.")
            
        else:
            print("Creating fresh database with new structure...")
            # Create the table with new structure
            c.execute('DROP TABLE IF EXISTS bookings')
            c.execute('''CREATE TABLE bookings
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          name TEXT NOT NULL,
                          agenda TEXT NOT NULL,
                          date TEXT NOT NULL,
                          start_time TEXT NOT NULL,
                          end_time TEXT NOT NULL,
                          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            print("Fresh database created!")
        
        conn.commit()
        
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    
    finally:
        conn.close()

if __name__ == '__main__':
    migrate_database()
    print("\nMigration complete! You can now run your Flask app.")