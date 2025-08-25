from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from datetime import datetime, timedelta
import sqlite3
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = 'office-resource-booking-2025'
app.config['SESSION_TYPE'] = 'filesystem'

# Database setup
def init_db():
    conn = sqlite3.connect('office_resources.db')
    c = conn.cursor()
    
    # Meeting room bookings table
    c.execute('''CREATE TABLE IF NOT EXISTS room_bookings
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  agenda TEXT NOT NULL,
                  date TEXT NOT NULL,
                  start_time TEXT NOT NULL,
                  end_time TEXT NOT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Car bookings table
    c.execute('''CREATE TABLE IF NOT EXISTS car_bookings
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

def get_bookings_for_week(table_name, week_offset=0):
    """Get all bookings for the specified week and resource type"""
    conn = sqlite3.connect('office_resources.db')
    c = conn.cursor()
    
    week_dates = get_week_dates(week_offset)
    start_date = week_dates[0]['date']
    end_date = week_dates[-1]['date']
    
    c.execute(f'''SELECT name, agenda, date, start_time, end_time 
                 FROM {table_name} 
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

def get_booking_stats():
    """Get booking statistics for the dashboard"""
    conn = sqlite3.connect('office_resources.db')
    c = conn.cursor()
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Room stats
    c.execute('SELECT COUNT(*) FROM room_bookings WHERE date >= ?', (today,))
    room_upcoming = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM room_bookings WHERE date = ?', (today,))
    room_today = c.fetchone()[0]
    
    # Car stats
    c.execute('SELECT COUNT(*) FROM car_bookings WHERE date >= ?', (today,))
    car_upcoming = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM car_bookings WHERE date = ?', (today,))
    car_today = c.fetchone()[0]
    
    conn.close()
    
    return {
        'room_stats': {'upcoming': room_upcoming, 'today': room_today},
        'car_stats': {'upcoming': car_upcoming, 'today': car_today}
    }

def login_required(f):
    """Decorator to enforce login requirement for certain routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    """Main landing page - choose between room and car booking"""
    stats = get_booking_stats()
    return render_template('index.html', 
                         room_stats=stats['room_stats'],
                         car_stats=stats['car_stats'])

# MEETING ROOM ROUTES
@app.route('/room')
@login_required
def room_index():
    """Meeting room schedule view - TEMPORARY using car template"""
    week_offset = request.args.get('week_offset', 0, type=int)
    
    time_slots = get_time_slots()
    week_dates = get_week_dates(week_offset)
    bookings = get_bookings_for_week('room_bookings', week_offset)
    week_info = get_week_info(week_offset)
    
    # Create a schedule grid
    schedule = {}
    for date_info in week_dates:
        date = date_info['date']
        schedule[date] = {}
        for time_slot in time_slots:
            booked_by = is_slot_booked(date, time_slot, bookings)
            schedule[date][time_slot] = booked_by

    # TEMPORARY: Use room_index.html template to test
    return render_template('room_index.html', 
                         time_slots=time_slots, 
                         week_dates=week_dates, 
                         schedule=schedule,
                         week_offset=week_offset,
                         week_info=week_info)

@app.route('/room/book', methods=['GET', 'POST'])
@login_required
def room_book():
    """Book a meeting room"""
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
            return redirect(url_for('room_book', week_offset=week_offset))
        
        # Validate that end time is after start time
        start_dt = datetime.strptime(start_time, "%H:%M")
        end_dt = datetime.strptime(end_time, "%H:%M")
        if end_dt <= start_dt:
            flash('End time must be after start time!')
            return redirect(url_for('room_book', week_offset=week_offset))
        
        # Check for conflicts
        conn = sqlite3.connect('office_resources.db')
        c = conn.cursor()
        c.execute('''SELECT * FROM room_bookings 
                     WHERE date = ? AND (
                         (start_time < ? AND end_time > ?) OR
                         (start_time < ? AND end_time > ?) OR
                         (start_time >= ? AND start_time < ?)
                     )''', (date, end_time, start_time, start_time, start_time, start_time, end_time))
        
        if c.fetchone():
            flash('Time slot conflicts with existing room booking!')
            conn.close()
            return redirect(url_for('room_book', week_offset=week_offset))
        
        # Create booking
        c.execute('INSERT INTO room_bookings (name, agenda, date, start_time, end_time) VALUES (?, ?, ?, ?, ?)',
                  (name, agenda, date, start_time, end_time))
        conn.commit()
        conn.close()
        
        flash(f'Meeting room booked for {name} on {date} from {start_time} to {end_time}!')
        return redirect(url_for('room_index', week_offset=week_offset))
    
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
                         booking_type='room',
                         week_dates=week_dates, 
                         time_slots=time_slots,
                         week_offset=week_offset,
                         week_info=week_info,
                         prefill_date=prefill_date,
                         prefill_start_time=prefill_start_time,
                         prefill_end_time=prefill_end_time)

@app.route('/room/bookings')
@login_required
def room_bookings():
    """View all room bookings"""
    conn = sqlite3.connect('office_resources.db')
    c = conn.cursor()
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Get upcoming bookings
    c.execute('''SELECT id, name, agenda, date, start_time, end_time, created_at 
                 FROM room_bookings 
                 WHERE date >= ?
                 ORDER BY date, start_time''', (today,))
    upcoming_bookings = c.fetchall()
    
    # Get past bookings
    c.execute('''SELECT id, name, agenda, date, start_time, end_time, created_at 
                 FROM room_bookings 
                 WHERE date < ?
                 ORDER BY date DESC, start_time DESC''', (today,))
    past_bookings = c.fetchall()
    
    conn.close()
    
    return render_template('bookings.html', 
                         booking_type='room',
                         upcoming_bookings=upcoming_bookings,
                         past_bookings=past_bookings)

@app.route('/room/delete/<int:booking_id>')
@login_required
def delete_room_booking(booking_id):
    if session.get('user') != 'admin':
        flash('Only admin can delete bookings!')
        return redirect(url_for('room_bookings'))
    
    """Delete a room booking"""
    conn = sqlite3.connect('office_resources.db')
    c = conn.cursor()
    
    # Get booking details before deleting
    c.execute('SELECT name, agenda, date, start_time, end_time FROM room_bookings WHERE id = ?', (booking_id,))
    booking_details = c.fetchone()
    
    if booking_details:
        c.execute('DELETE FROM room_bookings WHERE id = ?', (booking_id,))
        conn.commit()
        name, agenda, date, start, end = booking_details
        flash(f'Room booking deleted: {name} on {date} from {start} to {end}')
    else:
        flash('Booking not found!')
    
    conn.close()
    
    return redirect(request.referrer or url_for('room_bookings'))

@app.route('/room/quick_book')
@login_required
def room_quick_book():
    """Quick booking from room schedule grid"""
    date = request.args.get('date')
    time = request.args.get('time')
    week_offset = int(request.args.get('week_offset', 0))
    
    if date and time:
        return redirect(url_for('room_book', date=date, time=time, week_offset=week_offset))
    
    return redirect(url_for('room_book', week_offset=week_offset))

# COMPANY CAR ROUTES
@app.route('/car')
@login_required
def car_index():
    """Company car schedule view"""
    week_offset = request.args.get('week_offset', 0, type=int)
    
    time_slots = get_time_slots()
    week_dates = get_week_dates(week_offset)
    bookings = get_bookings_for_week('car_bookings', week_offset)
    week_info = get_week_info(week_offset)
    
    # Create a schedule grid
    schedule = {}
    for date_info in week_dates:
        date = date_info['date']
        schedule[date] = {}
        for time_slot in time_slots:
            booked_by = is_slot_booked(date, time_slot, bookings)
            schedule[date][time_slot] = booked_by
    
    return render_template('car_index.html', 
                         time_slots=time_slots, 
                         week_dates=week_dates, 
                         schedule=schedule,
                         week_offset=week_offset,
                         week_info=week_info)

@app.route('/car/book', methods=['GET', 'POST'])
@login_required
def car_book():
    """Book the company car"""
    week_offset = request.args.get('week_offset', 0, type=int)
    
    if request.method == 'POST':
        name = request.form['name']
        agenda = request.form['agenda']  # This will be "purpose" for car bookings
        date = request.form['date']
        start_time = request.form['start_time']
        end_time = request.form['end_time']
        week_offset = int(request.form.get('week_offset', 0))
        
        # Validate booking
        if not all([name, agenda, date, start_time, end_time]):
            flash('All fields are required!')
            return redirect(url_for('car_book', week_offset=week_offset))
        
        # Validate that end time is after start time
        start_dt = datetime.strptime(start_time, "%H:%M")
        end_dt = datetime.strptime(end_time, "%H:%M")
        if end_dt <= start_dt:
            flash('End time must be after start time!')
            return redirect(url_for('car_book', week_offset=week_offset))
        
        # Check for conflicts (car can only be booked by one person at a time)
        conn = sqlite3.connect('office_resources.db')
        c = conn.cursor()
        c.execute('''SELECT * FROM car_bookings 
                     WHERE date = ? AND (
                         (start_time < ? AND end_time > ?) OR
                         (start_time < ? AND end_time > ?) OR
                         (start_time >= ? AND start_time < ?)
                     )''', (date, end_time, start_time, start_time, start_time, start_time, end_time))
        
        if c.fetchone():
            flash('Car is already booked for that time slot!')
            conn.close()
            return redirect(url_for('car_book', week_offset=week_offset))
        
        # Create booking
        c.execute('INSERT INTO car_bookings (name, agenda, date, start_time, end_time) VALUES (?, ?, ?, ?, ?)',
                  (name, agenda, date, start_time, end_time))
        conn.commit()
        conn.close()
        
        flash(f'Company car booked for {name} on {date} from {start_time} to {end_time}!')
        return redirect(url_for('car_index', week_offset=week_offset))
    
    # GET request - show booking form
    week_dates = get_week_dates(week_offset)
    time_slots = get_time_slots()
    week_info = get_week_info(week_offset)
    
    # Handle pre-filled values from quick booking
    prefill_date = request.args.get('date', '')
    prefill_start_time = request.args.get('time', '')
    prefill_end_time = ''
    
    # Calculate default end time (2 hours for car bookings)
    if prefill_start_time:
        try:
            start_dt = datetime.strptime(prefill_start_time, "%H:%M")
            end_dt = start_dt + timedelta(hours=2)  # Default 2 hours for car trips
            prefill_end_time = end_dt.strftime("%H:%M")
        except:
            prefill_end_time = ''
    
    return render_template('book.html', 
                         booking_type='car',
                         week_dates=week_dates, 
                         time_slots=time_slots,
                         week_offset=week_offset,
                         week_info=week_info,
                         prefill_date=prefill_date,
                         prefill_start_time=prefill_start_time,
                         prefill_end_time=prefill_end_time)

@app.route('/car/bookings')
@login_required
def car_bookings():
    """View all car bookings"""
    conn = sqlite3.connect('office_resources.db')
    c = conn.cursor()
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Get upcoming bookings
    c.execute('''SELECT id, name, agenda, date, start_time, end_time, created_at 
                 FROM car_bookings 
                 WHERE date >= ?
                 ORDER BY date, start_time''', (today,))
    upcoming_bookings = c.fetchall()
    
    # Get past bookings
    c.execute('''SELECT id, name, agenda, date, start_time, end_time, created_at 
                 FROM car_bookings 
                 WHERE date < ?
                 ORDER BY date DESC, start_time DESC''', (today,))
    past_bookings = c.fetchall()
    
    conn.close()
    
    return render_template('bookings.html', 
                         booking_type='car',
                         upcoming_bookings=upcoming_bookings,
                         past_bookings=past_bookings)

@app.route('/car/delete/<int:booking_id>')
@login_required
def delete_car_booking(booking_id):
    if session.get('user') != 'admin':
        flash('Only admin can delete bookings!')
        return redirect(url_for('car_bookings'))
    
    """Delete a car booking"""
    conn = sqlite3.connect('office_resources.db')
    c = conn.cursor()
    
    # Get booking details before deleting
    c.execute('SELECT name, agenda, date, start_time, end_time FROM car_bookings WHERE id = ?', (booking_id,))
    booking_details = c.fetchone()
    
    if booking_details:
        c.execute('DELETE FROM car_bookings WHERE id = ?', (booking_id,))
        conn.commit()
        name, agenda, date, start, end = booking_details
        flash(f'Car booking deleted: {name} on {date} from {start} to {end}')
    else:
        flash('Booking not found!')
    
    conn.close()
    
    return redirect(request.referrer or url_for('car_bookings'))

@app.route('/car/quick_book')
@login_required
def car_quick_book():
    """Quick booking from car schedule grid"""
    date = request.args.get('date')
    time = request.args.get('time')
    week_offset = int(request.args.get('week_offset', 0))
    
    if date and time:
        return redirect(url_for('car_book', date=date, time=time, week_offset=week_offset))
    
    return redirect(url_for('car_book', week_offset=week_offset))

# COMBINED VIEWS
@app.route('/bookings')
@login_required
def all_bookings():
    """View all bookings (both room and car)"""
    conn = sqlite3.connect('office_resources.db')
    c = conn.cursor()
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Get all upcoming bookings
    c.execute('''
        SELECT id, name, agenda, date, start_time, end_time, 'room' as type, created_at 
        FROM room_bookings WHERE date >= ?
        UNION ALL
        SELECT id, name, agenda, date, start_time, end_time, 'car' as type, created_at 
        FROM car_bookings WHERE date >= ?
        ORDER BY date, start_time
    ''', (today, today))
    upcoming_bookings = c.fetchall()
    
    # Get all past bookings
    c.execute('''
        SELECT id, name, agenda, date, start_time, end_time, 'room' as type, created_at 
        FROM room_bookings WHERE date < ?
        UNION ALL
        SELECT id, name, agenda, date, start_time, end_time, 'car' as type, created_at 
        FROM car_bookings WHERE date < ?
        ORDER BY date DESC, start_time DESC
    ''', (today, today))
    past_bookings = c.fetchall()
    
    conn.close()
    
    return render_template('bookings.html', 
                         upcoming_bookings=upcoming_bookings,
                         past_bookings=past_bookings)

# API ROUTES
@app.route('/api/todays-bookings')
@login_required
def todays_bookings_api():
    """API endpoint for today's bookings"""
    conn = sqlite3.connect('office_resources.db')
    c = conn.cursor()
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Get today's room bookings
    c.execute('''SELECT name, agenda, start_time, end_time 
                 FROM room_bookings 
                 WHERE date = ?
                 ORDER BY start_time''', (today,))
    room_bookings = [{'name': row[0], 'agenda': row[1], 'start_time': row[2], 'end_time': row[3]} 
                     for row in c.fetchall()]
    
    # Get today's car bookings
    c.execute('''SELECT name, agenda, start_time, end_time 
                 FROM car_bookings 
                 WHERE date = ?
                 ORDER BY start_time''', (today,))
    car_bookings = [{'name': row[0], 'agenda': row[1], 'start_time': row[2], 'end_time': row[3]} 
                    for row in c.fetchall()]
    
    conn.close()
    
    return jsonify({
        'room_bookings': room_bookings,
        'car_bookings': car_bookings
    })

# LEGACY ROUTES (for backward compatibility)
@app.route('/book')
def legacy_book():
    """Redirect legacy book route to room booking"""
    return redirect(url_for('room_book'))

@app.route('/bookings_old')
def legacy_bookings():
    """Redirect legacy bookings route"""
    return redirect(url_for('room_bookings'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'EquipAdmin' and password == 'equipgroupadmin2025':
            session['user'] = 'admin'
            return redirect(url_for('index'))
        elif username == 'EquipGroup' and password == 'equip2025':
            session['user'] = 'workmate'
            return redirect(url_for('index'))
        else:
            error = 'Invalid username or password'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
