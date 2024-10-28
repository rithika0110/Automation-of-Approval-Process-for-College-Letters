from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
import MySQLdb.cursors
from datetime import datetime
import hashlib

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Necessary for session management

# Configure MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'sqlpassword@1234'  # Change this to your MySQL password
app.config['MYSQL_DB'] = 'letter_approval'

mysql = MySQL(app)


# Utility function to hash passwords
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = hash_password(request.form['password'])

        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("SELECT * FROM user WHERE username = %s AND password = %s", (username, password))
        user = cur.fetchone()
        cur.close()

        if user:
            session['loggedin'] = True
            session['id'] = user['id']
            session['username'] = user['username']
            session['position'] = user['position']

            flash('Login successful!', 'success')
            if user['position'] == 'student':
                return redirect(url_for('student_dashboard'))
            elif user['position'] == 'faculty':
                return redirect(url_for('faculty_dashboard'))
            elif user['position'] == 'hod':
                return redirect(url_for('hod_dashboard'))
            elif user['position'] == 'admin':
                return redirect(url_for('admin_dashboard'))
        else:
            flash('Incorrect username or password!', 'danger')

    return render_template('login.html')


# Logout route
@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    session.pop('position', None)
    flash('You have successfully logged out.', 'success')
    return redirect(url_for('login'))


# Student Dashboard
@app.route('/student')
def student_dashboard():
    if 'loggedin' in session and session['position'] == 'student':
        # Fetch student's letters and leave requests
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("SELECT * FROM letter WHERE student_id = %s", [session['id']])
        letters = cur.fetchall()
        cur.execute("SELECT * FROM leave_request WHERE student_id = %s", [session['id']])
        leave_requests = cur.fetchall()
        cur.close()
        return render_template('student.html', letters=letters, leave_requests=leave_requests)
    return redirect(url_for('login'))


# Faculty Dashboard
@app.route('/faculty')
def faculty_dashboard():
    if 'loggedin' in session and session['position'] == 'faculty':
        # Fetch faculty's leave requests
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("SELECT * FROM leave_request WHERE student_id = %s", [session['id']])
        leave_requests = cur.fetchall()
        cur.close()
        return render_template('faculty.html', leave_requests=leave_requests)
    return redirect(url_for('login'))


# HOD Dashboard
@app.route('/hod')
def hod_dashboard():
    if 'loggedin' in session and session['position'] == 'hod':
        # Fetch pending leave requests
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("SELECT * FROM leave_request WHERE status = 'Pending'")
        leave_requests = cur.fetchall()
        cur.close()
        return render_template('hod.html', leave_requests=leave_requests)
    return redirect(url_for('login'))


# Admin Dashboard
@app.route('/admin')
def admin_dashboard():
    if 'loggedin' in session and session['position'] == 'admin':
        # Fetch pending letters
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("SELECT * FROM letter WHERE status = 'Pending'")
        letters = cur.fetchall()
        cur.close()
        return render_template('admin.html', letters=letters)
    return redirect(url_for('login'))


# Index route
@app.route('/')
def index():
    if 'loggedin' in session:
        return redirect(url_for(f"{session['position']}_dashboard"))
    return redirect(url_for('login'))


# Route to submit a new letter (for students)
@app.route('/submit_letter', methods=['GET', 'POST'])
def submit_letter():
    if 'loggedin' in session and session['position'] == 'student':
        if request.method == 'POST':
            letter_type = request.form['type']
            content = request.form['content']

            cur = mysql.connection.cursor()
            cur.execute("INSERT INTO letter (student_id, type, content) VALUES (%s, %s, %s)",
                        (session['id'], letter_type, content))
            mysql.connection.commit()
            cur.close()

            flash('Letter submitted successfully!', 'success')
            return redirect(url_for('student_dashboard'))
        return render_template('submit_letter.html')
    return redirect(url_for('login'))


# Route to view and approve/reject a letter (for admin)
@app.route('/letter_detail/<int:letter_id>', methods=['GET', 'POST'])
def letter_detail(letter_id):
    if 'loggedin' in session and session['position'] == 'admin':
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        if request.method == 'POST':
            status = request.form['status']
            cur.execute("UPDATE letter SET status = %s WHERE id = %s", (status, letter_id))
            mysql.connection.commit()
            flash(f'Letter {status.lower()} successfully!', 'success')
            return redirect(url_for('admin_dashboard'))

        cur.execute("SELECT * FROM letter WHERE id = %s", [letter_id])
        letter = cur.fetchone()
        cur.close()
        return render_template('letter_detail.html', letter=letter)
    return redirect(url_for('login'))


# Route to submit a new leave request (for students and faculty)
@app.route('/submit_leave', methods=['GET', 'POST'])
def submit_leave():
    if 'loggedin' in session and session['position'] in ['student', 'faculty']:
        if request.method == 'POST':
            leave_type = request.form['leave_type']
            start_date = request.form['start_date']
            end_date = request.form['end_date']
            reason = request.form['reason']

            cur = mysql.connection.cursor()
            cur.execute(
                "INSERT INTO leave_request (student_id, leave_type, start_date, end_date, reason) VALUES (%s, %s, %s, %s, %s)",
                (session['id'], leave_type, start_date, end_date, reason))
            mysql.connection.commit()
            cur.close()

            flash('Leave request submitted successfully!', 'success')
            return redirect(url_for(f"{session['position']}_dashboard"))
        return render_template('submit_leave.html')
    return redirect(url_for('login'))


# Route to view and approve/reject a leave request (for HOD)
@app.route('/leave_detail/<int:leave_id>', methods=['GET', 'POST'])
def leave_detail(leave_id):
    if 'loggedin' in session and session['position'] == 'hod':
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        if request.method == 'POST':
            status = request.form['status']
            comments = request.form['comments']
            cur.execute("UPDATE leave_request SET status = %s WHERE id = %s", (status, leave_id))
            mysql.connection.commit()
            flash(f'Leave request {status.lower()} successfully!', 'success')
            return redirect(url_for('hod_dashboard'))

        cur.execute("SELECT * FROM leave_request WHERE id = %s", [leave_id])
        leave = cur.fetchone()
        cur.close()
        return render_template('leave_detail.html', leave=leave)
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)

