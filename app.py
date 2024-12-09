from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import mysql.connector
import logging
import datetime
from tkinter import *
import tkinter.messagebox 
from flask import render_template
from datetime import datetime
from sqlalchemy import func, extract
from flask import jsonify, request
from datetime import datetime

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
    user_id = session.get('user')["user_id"]
    if not user_id:
        return redirect(url_for('signin'))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        # Fetch user details
        cursor.execute("SELECT email, phone_number, bank_account FROM Users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()

        # Fetch bank balance
        cursor.execute("SELECT bank_balance FROM Bank WHERE user_id = %s", (user_id,))
        bank = cursor.fetchone()

        user["bank_balance"] = bank["bank_balance"] if bank else 0.00

        return render_template("profile.html", user=user)
    finally:
        cursor.close()
        connection.close()


@app.route('/get_monthly_data', methods=['GET'])
def get_monthly_data():
    if 'user' not in session or not session.get('user').get("user_id"):
        return jsonify({"error": "User not logged in"}), 401
    user_id = session.get('user')["user_id"]
    current_month = datetime.now().strftime('%Y-%m')  # Format as "YYYY-MM"
    app.logger.info("get_monthly_data route called.")

    # Establish database connection
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor(dictionary=True)

        # Fetch total money sent and received by aggregating all rows for the user in the current month
        statement_query = """
            SELECT 
                COALESCE(SUM(CASE WHEN total_sent > 0 THEN total_sent ELSE 0 END), 0) AS total_sent,
                COALESCE(SUM(CASE WHEN total_received > 0 THEN total_received ELSE 0 END), 0) AS total_received
            FROM Statements
            WHERE user_id = %s AND month = %s
        """
        cursor.execute(statement_query, (user_id, current_month))
        statement_row = cursor.fetchone()

        sent = statement_row['total_sent']
        received = statement_row['total_received']

        # Fetch the email of the user who received the most money
        favorite_user_query = """
            SELECT U.email, SUM(T.amount) AS total_amount
            FROM Transactions T
            JOIN Users U ON U.user_id = T.receiver_id
            WHERE T.sender_id = %s
            GROUP BY U.email
            ORDER BY total_amount DESC
            LIMIT 1
        """
        cursor.execute(favorite_user_query, (user_id,))
        favorite_user_row = cursor.fetchone()
        favorite_user = favorite_user_row['email'] if favorite_user_row else "No transactions"

        # Fetch the highest transaction amounts for each month
        highest_transactions_query = """
            SELECT DATE_FORMAT(transaction_date, '%Y-%m') AS month, MAX(amount) AS max_amount
            FROM Transactions
            WHERE sender_id = %s
            GROUP BY DATE_FORMAT(transaction_date, '%Y-%m')
        """
        cursor.execute(highest_transactions_query, (user_id,))
        highest_transactions_rows = cursor.fetchall()
        highest_transactions = {
            row['month']: row['max_amount'] for row in highest_transactions_rows
        }

        return jsonify({
            "sent": sent,
            "received": received,
            "favorite_user": favorite_user,
            "highest_transactions": highest_transactions
        })
    except Exception as e:
        logging.error(f"Error while fetching data: {e}")
        return jsonify({"error": "Failed to fetch data"}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/request_money', methods=['GET', 'POST'])
def request_money():
    if request.method == 'GET':
        # Render the request money page for GET requests
        return render_template('request_money.html')

    if request.method == 'POST':
        try:
            user_id = session.get('user')["user_id"]
            app.logger.info(f"Request method: {request.method}")
            app.logger.info(f"Form data: {request.form}")

            # Retrieve form data
            requestee_email = request.form['email']
            amount = float(request.form['amount'])

            # Validate requestee exists
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT user_id FROM Users WHERE email = %s", (requestee_email,))
            requestee = cursor.fetchone()

            if not requestee:
                flash("Recipient email not found.", "error")
                return redirect(url_for('request_money'))

            requestee_id = requestee['user_id']

            # Insert into MoneyRequests table
            cursor.execute("""
                INSERT INTO MoneyRequests (requester_id, requestee_id, amount)
                VALUES (%s, %s, %s)
            """, (user_id, requestee_id, amount))
            connection.commit()

            flash("Money request sent successfully.", "success")
            return redirect(url_for('main_menu'))
        except Exception as e:
            app.logger.error(f"Error processing money request: {e}")
            flash("An error occurred while processing your request.", "error")
            return redirect(url_for('request_money'))
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()



@app.route('/get_money_requests', methods=['GET'])
def get_money_requests():
    try:
        user_id = session.get('user')["user_id"]  # Get logged-in user's ID
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Fetch pending requests where the logged-in user is the requestee
        cursor.execute("""
            SELECT mr.request_id, u.email AS requester_email, mr.amount 
            FROM MoneyRequests mr
            JOIN Users u ON u.user_id = mr.requester_id
            WHERE mr.requestee_id = %s AND mr.status = 'pending'
        """, (user_id,))
        pending_requests = cursor.fetchall()

        return jsonify(pending_requests)

    except mysql.connector.Error as err:
        app.logger.error(f"Database error: {err}")
        return jsonify({"error": "Failed to fetch requests"}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/update_money_request', methods=['POST'])
def update_money_request():
    try:
        data = request.get_json()
        app.logger.info(f"Update request received: {data}")

        request_id = data['request_id']
        action = data['action']  # 'accept' or 'reject'

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Fetch request details
        cursor.execute("SELECT * FROM MoneyRequests WHERE request_id = %s", (request_id,))
        money_request = cursor.fetchone()

        if not money_request:
            return jsonify({"error": "Request not found"}), 404

        sender_id = money_request['requestee_id']  # Person who is accepting the request
        receiver_id = money_request['requester_id']  # Person who made the request
        amount = money_request['amount']

        if action == 'accept':
            # Fetch sender's bank balance
            cursor.execute("SELECT bank_balance FROM Bank WHERE user_id = %s", (sender_id,))
            sender_balance = cursor.fetchone()["bank_balance"]

            if sender_balance < amount:
                return jsonify({"error": "Insufficient balance to accept the request."}), 400

            # Deduct from sender's balance and add to receiver's balance
            cursor.execute("UPDATE Bank SET bank_balance = bank_balance - %s WHERE user_id = %s", (amount, sender_id))
            cursor.execute("UPDATE Bank SET bank_balance = bank_balance + %s WHERE user_id = %s", (amount, receiver_id))

            # Insert transaction record
            cursor.execute("""
                INSERT INTO Transactions (sender_id, receiver_id, amount, transaction_type, transaction_date)
                VALUES (%s, %s, %s, 'send', NOW())
            """, (sender_id, receiver_id, amount))

        # Update the request status
        cursor.execute("""
            UPDATE MoneyRequests SET status = %s WHERE request_id = %s
        """, ('accepted' if action == 'accept' else 'rejected', request_id))

        connection.commit()
        app.logger.info("Money request updated successfully.")
        return jsonify({"success": True})
    except Exception as e:
        app.logger.error(f"Error in update_money_request: {e}")
        return jsonify({"error": "Failed to process the request"}), 500
    finally:
        cursor.close()
        connection.close()


# @app.route('/request_money', methods=['GET', 'POST'])
# def request_money():
#     user = get_user_info()

#     if request.method == 'POST':
#         user_id = user[user_id]
#         recipient_email = request.form['email']
#         amount = request.form['amount']

#         # Validate input
#         if not recipient_email or not amount:
#             flash('Both email and amount are required.', 'error')
#             return redirect(url_for('request_money'))

#         try:
#             amount = float(amount)
#             if amount <= 0:
#                 flash('Amount must be greater than 0.', 'error')
#                 return redirect(url_for('request_money'))

#             # Database connection
#             connection = get_db_connection()
#             cursor = connection.cursor()

#             # Check if recipient exists
#             cursor.execute('SELECT user_id FROM Users WHERE email = %s', (recipient_email,))
#             recipient = cursor.fetchone()

#             if not recipient:
#                 flash('Recipient not found.', 'error')
#                 return redirect(url_for('request_money'))

#             recipient_id = recipient[0]

#             # Log the request in the database (sender_id is current user, receiver_id is the recipient)
#             cursor.execute('''INSERT INTO Transactions (sender_id, receiver_id, amount, date, status)
#                                VALUES (%s, %s, %s, NOW(), 'requested')''',
#                            (user_id, recipient_id, amount))

#             connection.commit()
#             flash(f'Successfully requested {amount} from {recipient_email}.', 'success')
#             return redirect(url_for('main_menu'))

#         except ValueError:
#             flash('Invalid amount entered.', 'error')
#             return redirect(url_for('request_money'))
#         except mysql.connector.Error as err:
#             flash(f'Database error: {err}', 'error')
#             return redirect(url_for('request_money'))
#         finally:
#             cursor.close()
#             connection.close()

#     # If GET request, render the request form
#     return render_template('request_money.html')
       

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

            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)

            # Fetch sender's bank balance
            cursor.execute("SELECT bank_balance FROM Bank WHERE user_id = %s", (sender_id,))
            sender_balance = cursor.fetchone()["bank_balance"]

            if sender_balance < amount:
                flash("Insufficient balance to complete the transaction.", "error")
                return redirect(url_for('send_money'))

            # Check if recipient exists
            cursor.execute('SELECT user_id FROM Users WHERE email = %s', (recipient_email,))
            recipient = cursor.fetchone()

            if not recipient:
                flash('Recipient not found.', 'error')
                return redirect(url_for('send_money'))

            recipient_id = recipient["user_id"]

            # Deduct amount from sender and add to recipient
            cursor.execute("UPDATE Bank SET bank_balance = bank_balance - %s WHERE user_id = %s", (amount, sender_id))
            cursor.execute("UPDATE Bank SET bank_balance = bank_balance + %s WHERE user_id = %s", (amount, recipient_id))

            # Record the transaction
            cursor.execute("""
                INSERT INTO Transactions (sender_id, receiver_id, amount, transaction_type, transaction_date)
                VALUES (%s, %s, %s, 'send', NOW())
            """, (sender_id, recipient_id, amount))

            connection.commit()
            app.logger.info("Transaction successfully inserted and committed.")

            return jsonify({'success': f'Successfully sent {amount} to {recipient_email}.'})

        except ValueError:
            app.logger.error("Invalid amount entered.")
            return jsonify({'error': 'Invalid amount entered.'})
        except mysql.connector.Error as err:
            app.logger.error(f"Database error: {err}")
            return jsonify({'error': f'Database error: {err}'})
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()


@app.route('/statements', methods=['GET'])
def statements():
    user_id = session.get('user')["user_id"]
    if not user_id:
        return redirect(url_for('signin'))
    
    # Get filter values from the query parameters
    filters = {
        "transaction_id": request.args.get('transaction_id', '').strip(),
        "person": request.args.get('person', '').strip(),
        "transaction_type": request.args.get('transaction_type', '').strip(),
        "amount": request.args.get('amount', '').strip(),
        "date": request.args.get('date', '').strip()
    }

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        # Base query
        query = '''
            SELECT 
                t.transaction_id,
                CASE 
                    WHEN t.sender_id = %s THEN u2.email
                    WHEN t.receiver_id = %s THEN u1.email
                END AS person,
                CASE 
                    WHEN t.sender_id = %s THEN 'sent'
                    WHEN t.receiver_id = %s THEN 'received'
                END AS transaction_type,
                t.amount,
                t.transaction_date
            FROM Transactions t
            LEFT JOIN Users u1 ON t.sender_id = u1.user_id
            LEFT JOIN Users u2 ON t.receiver_id = u2.user_id
            WHERE (t.sender_id = %s OR t.receiver_id = %s)
        '''
        params = [user_id, user_id, user_id, user_id, user_id, user_id]

        # Add filters dynamically
        if filters["transaction_id"]:
            query += " AND t.transaction_id = %s"
            params.append(filters["transaction_id"])
        if filters["person"]:
            query += " AND (u1.email LIKE %s OR u2.email LIKE %s)"
            params.extend([f"%{filters['person']}%", f"%{filters['person']}%"])
        if filters["transaction_type"]:
            if filters["transaction_type"].lower() == 'sent':
                query += " AND t.sender_id = %s"
                params.append(user_id)
            elif filters["transaction_type"].lower() == 'received':
                query += " AND t.receiver_id = %s"
                params.append(user_id)
        if filters["amount"]:
            query += " AND t.amount = %s"
            params.append(filters["amount"])
        if filters["date"]:
            query += " AND DATE(t.transaction_date) = %s"
            params.append(filters["date"])

        query += " ORDER BY t.transaction_date DESC"

        cursor.execute(query, tuple(params))
        transactions = cursor.fetchall()

        return render_template('statements.html', transactions=transactions, filters=filters)

    except mysql.connector.Error as err:
        app.logger.error(f"Error fetching statements: {err}")
        flash('Failed to fetch statements.', 'error')
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
