from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import mysql.connector
import logging
import datetime
from tkinter import *
import tkinter.messagebox 
root = tkinter.Tk() 


# Set up logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__, static_folder='static')  # Ensure static folder is correctly linked
app.secret_key = 'your_secret_key'  # Needed for session management

# Database connection
def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='root',  # Your MySQL username
            password='',  # Your MySQL password (empty in this case, adjust as needed)
            database='wallet_db'  # Your database name
        )
        if connection.is_connected():
            app.logger.info('Successfully connected to the database.')
        return connection
    except mysql.connector.Error as err:
        logging.error(f"Error connecting to database: {err}")
        return None

# Main Menu Route (after sign-in)
@app.route('/')
def main_menu():
    if 'user' not in session:
        return redirect(url_for('signin'))  # Redirect to Sign In if not logged in
    return render_template('main_menu.html')

# Sign In Route
@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        email = request.form['email']  # Only take email input, no phone number
        password = request.form['password']

        try:
            connection = get_db_connection()
            if connection is None:
                flash('Unable to connect to the database. Please try again later.', 'error')
                return redirect(url_for('signin'))

            cursor = connection.cursor()
            # Modify SQL query to only check for the email
            cursor.execute("SELECT user_id, email, password, bank_account, phone_number FROM Users WHERE email = %s", 
                           (email,))
            user = cursor.fetchone()

            if user and (user[2] == password):  # Compare password directly

                user_dict = {}
                user_dict["user_id"] = user[0]
                user_dict["email"] = user[1]
                user_dict["password"] = user[2]
                user_dict["bank_account"] = user[3]
                user_dict["phone_number"] = user[4]
                session['user'] = user_dict
                app.logger.info(user)
                return redirect(url_for('main_menu'))
            else:
                flash('Invalid credentials. Please try again.', 'error')
        except mysql.connector.Error as err:
            flash(f'Error: {err}', 'error')
        finally:
            cursor.close()
            connection.close()

    return render_template('signin.html')

# Sign Up Route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        phone_number = request.form['phone_number']
        password = request.form['password']
        bank_account = request.form['bank_account']

        # Basic input validation
        if not email or not phone_number or not password or not bank_account:
            flash('All fields are required.', 'error')
            return redirect(url_for('signup'))

        try:
            # Connect to the database
            connection = get_db_connection()
            if connection is None:
                flash('Unable to connect to the database. Please try again later.', 'error')
                return redirect(url_for('signup'))

            cursor = connection.cursor()

            # Check if email already exists
            cursor.execute("SELECT * FROM Users WHERE email = %s", (email,))
            existing_user = cursor.fetchone()

            if existing_user:
                flash('Email already in use. Please try again.', 'error')
            else:
                # Insert new user into the database
                cursor.execute("INSERT INTO Users (email, phone_number, password, bank_account) VALUES (%s, %s, %s, %s)", 
                               (email, phone_number, password, bank_account))  
                connection.commit()
                flash('Account created successfully! Please sign in.', 'success')
                return redirect(url_for('signin'))
        except mysql.connector.Error as err:
            flash(f'Error: {err}', 'error')
        finally:
            cursor.close()
            connection.close()

    return render_template('signup.html')

@app.route('/update_profile', methods=['POST'])
def update_profile():
    user_id = session.get('user')["user_id"]
    if not user_id:
        return jsonify({'success': False, 'message': 'You need to log in first.'})

    field = request.form['field']
    new_value = request.form['value']

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        if field == 'email':
            cursor.execute("UPDATE Users SET email = %s WHERE user_id = %s", (new_value, user_id))
            session["user"]["email"] = new_value
        elif field == 'phone_number':
            cursor.execute("UPDATE Users SET phone_number = %s WHERE user_id = %s", (new_value, user_id))
            session["user"]["phone_number"] = new_value
        elif field == 'bank_account':
            cursor.execute("UPDATE Users SET bank_account = %s WHERE user_id = %s", (new_value, user_id))
            session["user"]["bank_account"] = new_value

        connection.commit()

        

        return jsonify({'success': True})

    except mysql.connector.Error as err:
        return jsonify({'success': False, 'message': str(err)})

    finally:
        if connection:
            connection.close()

@app.route('/account_info', methods=["GET"])
def account_info():
    user = get_user_info()  
    app.logger.info(user)
    return render_template('profile.html', user=user)


@app.route('/request_money', methods=['GET', 'POST'])
def request_money():
    user = get_user_info()
    app.logger.info(user)

    if request.method == 'POST':
        user_id = user[user_id]
        recipient_email = request.form['email']
        amount = request.form['amount']

        # Validate input
        if not recipient_email or not amount:
            flash('Both email and amount are required.', 'error')
            return redirect(url_for('request_money'))

        try:
            amount = float(amount)
            if amount <= 0:
                flash('Amount must be greater than 0.', 'error')
                return redirect(url_for('request_money'))

            # Database connection
            connection = get_db_connection()
            cursor = connection.cursor()

            # Check if recipient exists
            cursor.execute('SELECT user_id FROM Users WHERE email = %s', (recipient_email,))
            recipient = cursor.fetchone()

            if not recipient:
                flash('Recipient not found.', 'error')
                return redirect(url_for('request_money'))

            recipient_id = recipient[0]

            # Log the request in the database (sender_id is current user, receiver_id is the recipient)
            cursor.execute('''INSERT INTO Transactions (sender_id, receiver_id, amount, date, status)
                               VALUES (%s, %s, %s, NOW(), 'requested')''',
                           (user_id, recipient_id, amount))

            connection.commit()
            flash(f'Successfully requested {amount} from {recipient_email}.', 'success')
            return redirect(url_for('main_menu'))

        except ValueError:
            flash('Invalid amount entered.', 'error')
            return redirect(url_for('request_money'))
        except mysql.connector.Error as err:
            flash(f'Database error: {err}', 'error')
            return redirect(url_for('request_money'))
        finally:
            cursor.close()
            connection.close()

    # If GET request, render the request form
    return render_template('request_money.html')


@app.route('/send_money', methods=['GET', 'POST'])
def send_money():
    if request.method == 'POST':
        sender_id = session.get('user')["user_id"]
        if not sender_id:
            flash('Please log in first.', 'error')
            return redirect(url_for('signin'))

        recipient_email = request.form['recipient']
        amount = request.form['amount']

        if not recipient_email or not amount:
            flash('Please provide both recipient email and amount.', 'error')
            return redirect(url_for('send_money'))

        try:
            amount = float(amount)
            if amount <= 0:
                flash('Amount must be greater than 0.', 'error')
                return redirect(url_for('send_money'))

            # Establish DB connection
            connection = get_db_connection()
            cursor = connection.cursor()

            # Check if recipient exists
            cursor.execute('SELECT user_id FROM Users WHERE email = %s', (recipient_email,))
            recipient = cursor.fetchone()

            if not recipient:
                flash('Recipient not found.', 'error')
                return redirect(url_for('send_money'))

            recipient_id = recipient[0]

            # Record the transaction (no balance check needed)
            cursor.execute('''INSERT INTO Transactions (sender_id, transaction_type, receiver_id, amount, transaction_date)
                               VALUES (%s,%s, %s, %s, %s)''', 
                           (sender_id, "send", recipient_id,  amount, datetime.datetime.now()))

            connection.commit()
            flash(f'Successfully sent {amount} to {recipient_email}.', 'success')
            return redirect(url_for('main_menu'))

        except ValueError:
            flash('Invalid amount entered.', 'error')
            return redirect(url_for('send_money'))
        except mysql.connector.Error as err:
            flash(f'Database error: {err}', 'error')
            return redirect(url_for('send_money'))
        finally:
            cursor.close()
            connection.close()

    return render_template('send_money.html')

@app.route('/statements')
def statements():
    user_id = session.get('user')["user_id"]
    if not user_id:
        return redirect(url_for('signin'))

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute('''SELECT t.id, u1.email AS sender_email, u2.email AS receiver_email, t.amount, t.date
                           FROM Transactions t
                           LEFT JOIN Users u1 ON t.sender_id = u1.user_id
                           LEFT JOIN Users u2 ON t.receiver_id = u2.user_id
                           WHERE t.sender_id = %s OR t.receiver_id = %s
                           ORDER BY t.date DESC''', (user_id, user_id))

        transactions = cursor.fetchall()

        return render_template('statements.html', transactions=transactions)

    except mysql.connector.Error as err:
        flash(f'Error: {err}', 'error')
        return redirect(url_for('main_menu'))
    finally:
        cursor.close()
        connection.close()


# Logout Route
@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('signin'))

def get_user_info():
    # Example: Fetch user data from a session or database
    user = session.get('user')  # If using Flask sessions
    app.logger.info(user)
    if not user:
        #raise Exception("User not logged in")
        flash('Please log in first.', 'error')
        return redirect(url_for('signin'))
    return user


if __name__ == '__main__':
    app.run(debug=True)
