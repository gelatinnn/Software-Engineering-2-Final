import os
from flask import Flask, session, render_template, request, redirect, url_for, flash
import pickle
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)
app.secret_key = 'simple-secret-key'

# Sample log in
users = {
    "rigel": "password",
    "admin": "12345"
}

# Load model
try:
    with open('model2.obj', 'rb') as fileObj:
        model = pickle.load(fileObj)
except FileNotFoundError:
    print("Error: Model file not found!")
    model = None

# Database connection function
def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host='127.0.0.1',  
            user='root',        
            password='123123',        
            database='derma'
        )
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

# Routes
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/database')
def database():
    if 'username' not in session:
        return redirect(url_for('login'))

    try:
        conn = get_db_connection()
        if conn is None:
            return "Database connection error", 500

        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, name, age, sex, address, predicted_condition FROM patients")
        patients = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('database.html', patients=patients)
    except Exception as e:
        print(f"Database error: {e}")
        return f"Database error: {e}", 500

@app.route('/edit_patient/<int:patient_id>', methods=['POST'])
def edit_patient(patient_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    try:
        conn = get_db_connection()
        if conn is None:
            return "Database connection error", 500

        name = request.form.get('name')
        age = request.form.get('age')
        sex = request.form.get('sex')
        address = request.form.get('address')
        predicted_condition = request.form.get('predicted_condition')

        cursor = conn.cursor()
        cursor.execute("""
            UPDATE patients 
            SET name=%s, age=%s, sex=%s, address=%s, predicted_condition=%s 
            WHERE id=%s
        """, (name, age, sex, address, predicted_condition, patient_id))
        conn.commit()
        cursor.close()
        conn.close()

        flash("Patient record updated successfully!", "success")
        return redirect(url_for('database'))

    except Exception as e:
        print(f"Error updating patient: {e}")
        return f"Error updating patient: {e}", 500

@app.route('/delete_patient/<int:patient_id>', methods=['POST'])
def delete_patient(patient_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    try:
        conn = get_db_connection()
        if conn is None:
            return "Database connection error", 500

        cursor = conn.cursor()
        cursor.execute("DELETE FROM patients WHERE id=%s", (patient_id,))
        conn.commit()
        cursor.close()
        conn.close()

        flash("Patient record deleted successfully!", "success")
        return redirect(url_for('database'))

    except Exception as e:
        print(f"Error deleting patient: {e}")
        return f"Error deleting patient: {e}", 500


@app.route('/diagnosis')
def diagnosis():
    if 'username' in session:
        return render_template('diagnosis.html')
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        if conn is None:
            flash("Database connection error", "danger")
            return redirect(url_for('login'))

        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()

        cursor.close()
        conn.close()

        if user:
            if user['password'] == password:  # Assuming passwords are stored as plain text
                session['username'] = username
                flash("Login successful!", "success")
                return redirect(url_for('home'))
            else:
                flash("The password you’ve entered is incorrect. Forgot Password?")
        else:
            flash("User not found. Please register first.", "danger")

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('username', None)
    flash("You have been logged out successfully", "success")
    return redirect(url_for('login'))

@app.route('/about')
def about():
    return render_template('about.html')

@app.route("/prediction", methods=['POST', 'GET'])
def prediction():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == "POST":
        try:
            name = request.form.get('name')
            age = int(request.form.get('age'))
            sex = request.form.get('sex')
            address = request.form.get('address')

            features_list = [
                'Erythema', 'Scaling', 'definite_borders', 'itching', 'koebner_phenomenon', 
                'polygonal_papules', 'follicular_papules', 'oral_mucosal_involvement',
                'knee_and_elbow_involvement', 'scalp_involvement', 'family_history', 
                'melanin_incontinence', 'eosinophils_infiltrate', 'PNL_infiltrate',
                'fibrosis_papillary_dermis', 'exocytosis', 'acanthosis', 'hyperkeratosis', 
                'parakeratosis', 'clubbing_rete_ridges', 'elongation_rete_ridges',
                'thinning_suprapapillary_epidermis', 'spongiform_pustule', 'munro_microabcess', 
                'focal_hypergranulosis', 'disappearance_granular_layer',
                'vacuolisation_damage_basal_layer', 'spongiosis', 'saw_tooth_appearance_retes', 
                'follicular_horn_plug', 'perifollicular_parakeratosis', 
                'inflammatory_mononuclear_infiltrate', 'band_like_infiltrate'
            ]

            features = [int(request.form.get(feature)) for feature in features_list] + [age]
            derma = model.predict([features])

            conditions = {
                0: "Psoriasis",
                1: "Seborrheic Dermatitis",
                2: "Lichen Planus",
                3: "Pityriasis Rosea",
                4: "Chronic Dermatitis",
                5: "Pityriasis Rubra Pilaris"
            }

            result = conditions.get(derma[0], "Unknown condition")

            conn = get_db_connection()
            if conn is None:
                return "Database connection error", 500

            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO patients (name, age, sex, address, predicted_condition) 
                VALUES (%s, %s, %s, %s, %s)""", 
                (name, age, sex, address, result))
            conn.commit()
            cursor.close()
            conn.close()

            return render_template('diagnosis.html', derma=result, name=name, age=age, sex=sex, address=address)

        except Exception as e:
            return f"An error occurred: {e}", 500

    return render_template('prediction.html')

from werkzeug.security import generate_password_hash

from werkzeug.security import generate_password_hash
    
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db_connection()
        if conn is None:
            flash("Database connection error", "danger")
            return redirect(url_for('register'))
        
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)", 
                           (username, email, password))
            conn.commit()
            flash("Registration successful! You can now log in.", "success")
            return redirect(url_for('login'))
        except mysql.connector.Error as err:
            flash(f"Error: {err}", "danger")
        finally:
            cursor.close()
            conn.close()
    
    return render_template('register.html')

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        flash('Password reset link has been sent to your email.', 'success')
        return redirect(url_for('login'))
    return render_template('forgot_password.html')

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        username = request.form['username']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        if new_password != confirm_password:
            flash("Passwords do not match. Please try again.", "danger")
            return redirect(url_for('reset_password'))

        conn = get_db_connection()
        if conn is None:
            flash("Database connection error", "danger")
            return redirect(url_for('reset_password'))

        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()

        if not user:
            flash("User not found. Please register first.", "danger")
            return redirect(url_for('register'))

        cursor.execute("UPDATE users SET password = %s WHERE username = %s", (new_password, username))
        conn.commit()
        cursor.close()
        conn.close()

        flash("Password reset successfully! You can now log in.", "success")
        return redirect(url_for('login'))

    return render_template('reset_password.html')

if __name__ == '__main__':
    app.run(debug=True)
