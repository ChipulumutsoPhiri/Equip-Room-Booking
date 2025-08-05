import sqlite3
import os

# Check if database file exists
if os.path.exists('meeting_room.db'):
    print("✅ Database file exists")
    
    # Connect and check contents
    conn = sqlite3.connect('meeting_room.db')
    c = conn.cursor()
    
    # Check if table exists
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bookings';")
    table_exists = c.fetchone()
    
    if table_exists:
        print("✅ Bookings table exists")
        
        # Count total bookings
        c.execute("SELECT COUNT(*) FROM bookings")
        count = c.fetchone()[0]
        print(f"📊 Total bookings in database: {count}")
        
        # Show all bookings
        c.execute("SELECT * FROM bookings")
        bookings = c.fetchall()
        
        if bookings:
            print("\n📋 All bookings:")
            for booking in bookings:
                print(f"  ID: {booking[0]}, Team: {booking[1]}, Date: {booking[2]}, Start: {booking[3]}, End: {booking[4]}")
        else:
            print("❌ No bookings found in database")
    else:
        print("❌ Bookings table doesn't exist")
    
    conn.close()
    
else:
    print("❌ Database file 'meeting_room.db' not found")