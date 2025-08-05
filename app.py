from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime, timedelta
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'meeting-room-app-2025'

# Database setup
def init_db():
    conn = sqlite3.connect('meeting_room.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS bookings
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  agenda TEXT NOT NULL,
                  date TEXT NOT NULL,
                  start_time TEXT NOT NULL,
                  end_time TEXT NOT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

# Helper functions
def get_time_slots():
    """Generate 30-minute time slots from 8:00 AM to 4:30 PM"""
    slots = []
    start_time = datetime.strptime("08:00", "%H:%M")
    end_time = datetime.strptime("16:30", "%H:%M")
    
    while start_time <= end_time:
        slots.append(start_time.strftime("%H:%M"))
        start_time += timedelta(minutes=30)
    
    return slots

def get_week_dates(week_offset=0):
    """Get week's dates (Monday to Friday) with optional offset"""
    today = datetime.now()
    # Find Monday of current week
    monday = today - timedelta(days=today.weekday())
    # Apply week offset
    monday = monday + timedelta(weeks=week_offset)
    
    week_dates = []
    for i in range(5):  # Monday to Friday
        date = monday + timedelta(days=i)
        week_dates.append({
            'date': date.strftime("%Y-%m-%d"),
            'display': date.strftime("%a %m/%d"),
            'full_display': date.strftime("%A, %B %d, %Y")
        })
    
    return week_dates

def get_bookings_for_week(week_offset=0):
    """Get all bookings for the specified week"""
    conn = sqlite3.connect('meeting_room.db')
    c = conn.cursor()
    
    week_dates = get_week_dates(week_offset)
    start_date = week_dates[0]['date']
    end_date = week_dates[-1]['date']
    
    c.execute('''SELECT name, agenda, date, start_time, end_time 
                 FROM bookings 
                 WHERE date BETWEEN ? AND ?
                 ORDER BY date, start_time''', (start_date, end_date))
    
    bookings = c.fetchall()
    conn.close()
    
    return bookings

def is_slot_booked(date, time, bookings):
    """Check if a specific time slot is booked"""
    for booking in bookings:
        booking_date, start_time, end_time, name = booking[2], booking[3], booking[4], booking[0]
        if booking_date == date:
            start = datetime.strptime(start_time, "%H:%M")
            end = datetime.strptime(end_time, "%H:%M")
            slot_time = datetime.strptime(time, "%H:%M")
            
            if start <= slot_time < end:
                return name
    return None

def get_week_info(week_offset=0):
    """Get week information including navigation details"""
    week_dates = get_week_dates(week_offset)
    start_date = datetime.strptime(week_dates[0]['date'], "%Y-%m-%d")
    end_date = datetime.strptime(week_dates[-1]['date'], "%Y-%m-%d")
    
    week_info = {
        'start_date': start_date,
        'end_date': end_date,
        'week_display': f"{start_date.strftime('%B %d')} - {end_date.strftime('%B %d, %Y')}",
        'is_current_week': week_offset == 0,
        'is_past_week': week_offset < 0
    }
    
    return week_info

@app.route('/')
def index(week_offset=0):
    """Main booking view - shows the weekly schedule with navigation"""
    # Get week_offset from URL parameters if provided
    week_offset = request.args.get('week_offset', 0, type=int)
    
    time_slots = get_time_slots()
    week_dates = get_week_dates(week_offset)
    bookings = get_bookings_for_week(week_offset)
    week_info = get_week_info(week_offset)
    
    # Create a schedule grid
    schedule = {}
    for date_info in week_dates:
        date = date_info['date']
        schedule[date] = {}
        for time_slot in time_slots:
            booked_by = is_slot_booked(date, time_slot, bookings)
            schedule[date][time_slot] = booked_by
    
    return render_template('index.html', 
                         time_slots=time_slots, 
                         week_dates=week_dates, 
                         schedule=schedule,
                         week_offset=week_offset,
                         week_info=week_info)

@app.route('/book', methods=['GET', 'POST'])
def book():
    """Book a meeting room with week navigation"""
    week_offset = request.args.get('week_offset', 0, type=int)
    
    if request.method == 'POST':
        name = request.form['name']
        agenda = request.form['agenda']
        date = request.form['date']
        start_time = request.form['start_time']
        end_time = request.form['end_time']
        week_offset = int(request.form.get('week_offset', 0))
        
        # Validate booking
        if not all([name, agenda, date, start_time, end_time]):
            flash('All fields are required!')
            return redirect(url_for('book', week_offset=week_offset))
        
        # Validate that end time is after start time
        start_dt = datetime.strptime(start_time, "%H:%M")
        end_dt = datetime.strptime(end_time, "%H:%M")
        if end_dt <= start_dt:
            flash('End time must be after start time!')
            return redirect(url_for('book', week_offset=week_offset))
        
        # Check for conflicts
        conn = sqlite3.connect('meeting_room.db')
        c = conn.cursor()
        c.execute('''SELECT * FROM bookings 
                     WHERE date = ? AND (
                         (start_time < ? AND end_time > ?) OR
                         (start_time < ? AND end_time > ?) OR
                         (start_time >= ? AND start_time < ?)
                     )''', (date, end_time, start_time, start_time, start_time, start_time, end_time))
        
        if c.fetchone():
            flash('Time slot conflicts with existing booking!')
            conn.close()
            return redirect(url_for('book', week_offset=week_offset))
        
        # Create booking
        c.execute('INSERT INTO bookings (name, agenda, date, start_time, end_time) VALUES (?, ?, ?, ?, ?)',
                  (name, agenda, date, start_time, end_time))
        conn.commit()
        conn.close()
        
        flash(f'Meeting room booked for {name} on {date} from {start_time} to {end_time}!')
        return redirect(url_for('index', week_offset=week_offset))
    
    # GET request - show booking form
    week_dates = get_week_dates(week_offset)
    time_slots = get_time_slots()
    week_info = get_week_info(week_offset)
    
    # Handle pre-filled values from quick booking
    prefill_date = request.args.get('date', '')
    prefill_start_time = request.args.get('time', '')
    prefill_end_time = ''
    
    # Calculate default end time (1 hour after start time)
    if prefill_start_time:
        try:
            start_dt = datetime.strptime(prefill_start_time, "%H:%M")
            end_dt = start_dt + timedelta(hours=1)
            prefill_end_time = end_dt.strftime("%H:%M")
        except:
            prefill_end_time = ''
    
    return render_template('book.html', 
                         week_dates=week_dates, 
                         time_slots=time_slots,
                         week_offset=week_offset,
                         week_info=week_info,
                         prefill_date=prefill_date,
                         prefill_start_time=prefill_start_time,
                         prefill_end_time=prefill_end_time)

@app.route('/bookings')
def view_bookings():
    """View all current and future bookings"""
    conn = sqlite3.connect('meeting_room.db')
    c = conn.cursor()
    
    # Get current date
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Show all future bookings (including today)
    c.execute('''SELECT id, name, agenda, date, start_time, end_time, created_at 
                 FROM bookings 
                 WHERE date >= ?
                 ORDER BY date, start_time''', (today,))
    upcoming_bookings = c.fetchall()
    
    # Show past bookings
    c.execute('''SELECT id, name, agenda, date, start_time, end_time, created_at 
                 FROM bookings 
                 WHERE date < ?
                 ORDER BY date DESC, start_time DESC''', (today,))
    past_bookings = c.fetchall()
    
    conn.close()
    
    return render_template('bookings.html', 
                         upcoming_bookings=upcoming_bookings,
                         past_bookings=past_bookings)

@app.route('/delete/<int:booking_id>')
def delete_booking(booking_id):
    """Delete a booking"""
    conn = sqlite3.connect('meeting_room.db')
    c = conn.cursor()
    
    # Get booking details before deleting (for confirmation message)
    c.execute('SELECT name, agenda, date, start_time, end_time FROM bookings WHERE id = ?', (booking_id,))
    booking_details = c.fetchone()
    
    if booking_details:
        c.execute('DELETE FROM bookings WHERE id = ?', (booking_id,))
        conn.commit()
        name, agenda, date, start, end = booking_details
        flash(f'Booking deleted: {name} on {date} from {start} to {end}')
    else:
        flash('Booking not found!')
    
    conn.close()
    
    # Redirect back to where we came from
    return redirect(request.referrer or url_for('view_bookings'))

@app.route('/quick_book')
def quick_book():
    """Quick booking from schedule grid"""
    date = request.args.get('date')
    time = request.args.get('time')
    week_offset = int(request.args.get('week_offset', 0))
    
    if date and time:
        # Redirect to booking form with pre-filled date and time
        return redirect(url_for('book', date=date, time=time, week_offset=week_offset))
    
    return redirect(url_for('book', week_offset=week_offset))

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)