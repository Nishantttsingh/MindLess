from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_cors import CORS
from flask_mysqldb import MySQL
from werkzeug.utils import secure_filename
import os
import groq
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv(encoding='utf-8')
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("No GROQ_API_KEY set in .env file")

client = groq.Client(api_key=GROQ_API_KEY)

# ----------------- App Initialization -----------------
app = Flask(__name__)
CORS(app)

# Secret key for sessions
app.secret_key = 'your_secret_key'

# MySQL configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '1907'
app.config['MYSQL_DB'] = 'shrawanidb'
mysql = MySQL(app)

# Upload config
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

# ----------------- AI Chat Conversation -----------------
conversation_history = [
    {"role": "system", "content":
        "You are an empathetic AI that provides motivation, hope, and emotional support. "
        "Your replies should be short but powerful, uplifting, and helpful. "
        "If the user greets you with 'hi' or 'hello', respond in a friendly and casual way, without being overly empathetic."
    }
]

# ----------------- Dummy Data -----------------
profs = [
    {"name": "Dr. Jane Doe", "specialty": "Clinical Psychologist", "rate": 100, "availability": ["10:00 AM", "2:00 PM", "4:00 PM"], "photo": "1.jpg"},
    {"name": "Dr. John Smith", "specialty": "Career Consultant", "rate": 80, "availability": ["11:00 AM", "3:00 PM", "5:00 PM"], "photo": "2.jpg"},
    {"name": "Dr. Lisa Johnson", "specialty": "Neuropsychologist", "rate": 130, "availability": ["9:00 AM", "1:00 PM", "6:00 PM"], "photo": "5.jpg"},
    {"name": "Dr. Lisa Brown", "specialty": "Depression & Anxiety Specialist", "rate": 120, "availability": ["8:00 AM", "12:00 PM", "5:00 PM"], "photo": "3.jpg"},
    {"name": "Dr. Michael Johnson", "specialty": "Life Coach", "rate": 90, "availability": ["10:00 AM", "3:00 PM", "7:00 PM"], "photo": "4.jpg"}
]

# Initialize bookings list
bookings = []

# Initialize success stories list
success_stories_list = []

# ----------------- Posts Data -----------------
posts = [
    {
        "id": 1,
        "title": "Overcoming Fear",
        "photo": "5.jpg",
        "author": "User789",
        "content": "Fear only has power if we let it control us.",
        "comments": [
            {"user": "User012", "text": "So motivational!"},
            {"user": "User456", "text": "Fear held me back for so long, but not anymore."}
        ]
    },
    {
        "id": 2,
        "title": "Journey to Self-Acceptance",
        "photo": "2.webp",
        "author": "User456",
        "content": "Learning to love myself was the best decision I ever made.",
        "comments": [
            {"user": "User789", "text": "This resonates with me!"},
            {"user": "User123", "text": "Thank you for sharing your experience."}
        ]
    },
    {
        "id": 3,
        "title": "Embracing Change",
        "photo": "3.webp",
        "author": "User567",
        "content": "Growth begins when we step out of our comfort zones.",
        "comments": [
            {"user": "User890", "text": "This is so true!"},
            {"user": "User234", "text": "I needed to hear this today."}
        ]
    },
    {
        "id": 4,
        "title": "Finding Inner Peace",
        "photo": "4.jpg",
        "author": "User678",
        "content": "Meditation and mindfulness changed my life for the better.",
        "comments": [
            {"user": "User901", "text": "Mindfulness has helped me too!"},
            {"user": "User345", "text": "Such an inspiring post."}
        ]
    },
    {
        "id": 5,
        "title": "Overcoming Anxiety",
        "photo": "1.png",
        "author": "User123",
        "content": "I struggled with anxiety for years, but mindfulness and therapy helped me take control.",
        "comments": [
            {"user": "User456", "text": "Great story! Thanks for sharing."},
            {"user": "User789", "text": "I agree, this was really inspiring."}
        ]
    }
]

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# ----------------- Routes -----------------

@app.route("/")
def home_page():
    return render_template("newhp.html")

@app.route("/home")
def index():
    return render_template("home.html", posts=posts)

@app.route("/login", methods=["GET", "POST"])
def login_page():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("SELECT id, username, password FROM user WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()

        if user and user[2] == password:
            session['email'] = email
            session['username'] = user[1]
            session['id'] = user[0]
            session['loggedin'] = True
            return redirect(url_for('home_page'))
        else:
            flash('Invalid email or password!', 'danger')

    return render_template('login.html')

@app.route("/signup", methods=["POST"])
def signup():
    name = request.form['name']
    email = request.form['email']
    password = request.form['password']

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM user WHERE email = %s", (email,))
    if cur.fetchone():
        cur.close()
        flash('Email already registered. Please log in.', 'danger')
        return render_template('login.html', show_signup=True)

    cur.execute("INSERT INTO user (username, email, password) VALUES (%s, %s, %s)", (name, email, password))
    mysql.connection.commit()
    cur.close()
    flash('Signup successful! Please log in.', 'success')
    return render_template('login.html')

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home_page"))

@app.route("/conversation")
def conversation_page():
    return render_template("conversation.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message", "").lower().strip()

    if user_message in ["hi", "hello", "hey"]:
        ai_reply = "Hey there! How's it going?"
    else:
        conversation_history.append({"role": "user", "content": data["message"]})
        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=conversation_history
        )
        ai_reply = response.choices[0].message.content
        conversation_history.append({"role": "assistant", "content": ai_reply})

    return jsonify({"reply": ai_reply})

@app.route("/profile/<username>")
def profile(username):
    if 'id' not in session:
        flash("Please log in to view profiles.", "warning")
        return redirect(url_for('login_page'))
    
    cur = mysql.connection.cursor()
    try:
        # Updated query to include profile_pic if it exists in your table
        cur.execute("""
            SELECT 
                u.id, 
                u.username, 
                u.email, 
                p.bio, 
                p.gender, 
                p.mental_health_status, 
                p.preferred_contact_method,
                p.profile_pic,
                p.created_at
            FROM user u
            LEFT JOIN user_profiles p ON u.id = p.user_id
            WHERE u.username = %s
            ORDER BY p.created_at DESC
            LIMIT 1
        """, (username,))
        
        result = cur.fetchone()

        if not result:
            flash("User not found.", "danger")
            return redirect(url_for('index'))

        # Determine profile picture path
        profile_pic = 'default.png'  # Default image
        if result[7]:  # If profile_pic exists in database
            # Check if file actually exists
            pic_path = os.path.join(app.config['UPLOAD_FOLDER'], result[7])
            if os.path.exists(pic_path):
                profile_pic = result[7]
            else:
                app.logger.warning(f"Profile picture not found: {result[7]}")

        # Create user dictionary
        user = {
            'id': result[0],
            'username': result[1],
            'email': result[2],
            'bio': result[3] if result[3] else 'No bio yet',
            'gender': result[4] if result[4] else 'Not specified',
            'mental_health_status': result[5] if result[5] else 'Not specified',
            'preferred_contact_method': result[6] if result[6] else 'Email',
            'profile_pic': profile_pic,
            'member_since': result[8].strftime('%B %Y') if result[8] else 'Recently'
        }

        # Get user's posts (from database if available, otherwise from dummy data)
        user_posts = []
        try:
            cur.execute("SELECT * FROM posts WHERE author_id = %s ORDER BY created_at DESC", (user['id'],))
            db_posts = cur.fetchall()
            if db_posts:
                user_posts = [{
                    'id': post[0],
                    'title': post[1],
                    'content': post[2],
                    'created_at': post[3]
                } for post in db_posts]
        except Exception as e:
            app.logger.error(f"Couldn't fetch posts: {str(e)}")
            # Fallback to dummy data if database fails
            user_posts = [post for post in posts if post['author'] == username]

        return render_template('profile.html', user=user, posts=user_posts)
    
    except Exception as e:
        app.logger.error(f"Profile error: {str(e)}")
        flash("An error occurred while loading the profile.", "danger")
        return redirect(url_for('index'))
    finally:
        cur.close()
from werkzeug.security import generate_password_hash, check_password_hash

@app.route("/editp", methods=["GET", "POST"])
def edit_profile():
    if 'id' not in session:
        return redirect(url_for('login_page'))
    
    if request.method == 'POST':
        # Get form data
        bio = request.form.get('bio')
        gender = request.form.get('gender')
        mental_health_status = request.form.get('mental_health_status')
        preferred_contact_method = request.form.get('preferred_contact_method')
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        try:
            cur = mysql.connection.cursor()
            
            # Handle password change if fields are filled
            if current_password or new_password:
                if not all([current_password, new_password, confirm_password]):
                    flash('All password fields are required for password change', 'danger')
                    return redirect(url_for('edit_profile'))
                
                if new_password != confirm_password:
                    flash('New passwords do not match', 'danger')
                    return redirect(url_for('edit_profile'))
                
                if len(new_password) < 8:
                    flash('Password must be at least 8 characters', 'danger')
                    return redirect(url_for('edit_profile'))
                
                # Verify current password
                cur.execute("SELECT password FROM user WHERE id = %s", (session['id'],))
                user = cur.fetchone()
                
                if not user or not check_password_hash(user[0], current_password):
                    flash('Current password is incorrect', 'danger')
                    return redirect(url_for('edit_profile'))
                
                # Update password
                hashed_password = generate_password_hash(new_password)
                cur.execute("UPDATE user SET password = %s WHERE id = %s", 
                          (hashed_password, session['id']))
                flash('Password changed successfully!', 'success')
            
            # Handle profile picture upload
            profile_pic = None
            if 'profile_pic' in request.files:
                file = request.files['profile_pic']
                if file and allowed_file(file.filename):
                    # Delete old profile picture if exists
                    cur.execute("SELECT profile_pic FROM user_profiles WHERE user_id = %s", (session['id'],))
                    old_pic = cur.fetchone()
                    if old_pic and old_pic[0]:
                        old_path = os.path.join(app.config['UPLOAD_FOLDER'], old_pic[0])
                        if os.path.exists(old_path):
                            os.remove(old_path)
                    
                    # Save new picture
                    filename = secure_filename(f"{session['id']}_{file.filename}")
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(filepath)
                    profile_pic = filename
            
            # Update profile information
            update_data = {
                'user_id': session['id'],
                'bio': bio,
                'gender': gender,
                'mental_health_status': mental_health_status,
                'preferred_contact_method': preferred_contact_method
            }
            
            if profile_pic:
                update_data['profile_pic'] = profile_pic
            
            # Build the query dynamically based on available data
            columns = []
            values = []
            update_clauses = []
            
            for key, value in update_data.items():
                if value is not None:
                    columns.append(key)
                    values.append(value)
                    update_clauses.append(f"{key}=%s")
            
            query = f"""
                INSERT INTO user_profiles 
                ({', '.join(columns)}) 
                VALUES ({', '.join(['%s']*len(columns))})
                ON DUPLICATE KEY UPDATE
                {', '.join(update_clauses)}
            """
            
            cur.execute(query, values + values)
            mysql.connection.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('profile', username=session['username']))
            
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Error updating profile: {str(e)}', 'danger')
            app.logger.error(f"Profile update error: {str(e)}")
            return redirect(url_for('edit_profile'))
        finally:
            cur.close()
    
    # GET request handling
    cur = mysql.connection.cursor()
    try:
        cur.execute("SELECT username, email FROM user WHERE id = %s", (session['id'],))
        user_data = cur.fetchone()
        
        cur.execute("""
            SELECT bio, gender, mental_health_status, preferred_contact_method, profile_pic
            FROM user_profiles 
            WHERE user_id = %s
        """, (session['id'],))
        profile_data = cur.fetchone()
        
        user = {
            'username': user_data[0],
            'email': user_data[1],
            'bio': profile_data[0] if profile_data and profile_data[0] else '',
            'gender': profile_data[1] if profile_data and profile_data[1] else '',
            'mental_health_status': profile_data[2] if profile_data and profile_data[2] else '',
            'preferred_contact_method': profile_data[3] if profile_data and profile_data[3] else 'Email',
            'profile_pic': profile_data[4] if profile_data and profile_data[4] else 'default-profile.png'
        }
        
        return render_template('editp.html', user=user)
    finally:
        cur.close()

@app.route('/professionals')
def professionals():
    return render_template('professionals.html', professionals=profs)

@app.route('/book', methods=['GET', 'POST'])
def book():
    if 'email' not in session:
        flash("Please log in to book a session.", "danger")
        return redirect(url_for('login_page'))

    if request.method == 'POST':
        selected_professional_name = request.form.get('professional')
        time_slot = request.form.get('time_slot')

        if not selected_professional_name or not time_slot:
            flash("Please select a professional and time slot.", "danger")
            return redirect(url_for('book'))

        # Get current user ID
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT id FROM user WHERE email = %s", (session['email'],))
        user = cursor.fetchone()
        if not user:
            flash("User not found.", "danger")
            cursor.close()
            return redirect(url_for('book'))
        user_id = user[0]

        # Check for existing booking
        cursor.execute("SELECT * FROM bookings WHERE doctor_name = %s AND time_slot = %s", (selected_professional_name, time_slot))
        existing = cursor.fetchone()
        if existing:
            flash("This time slot is already booked.", "danger")
            cursor.close()
            return redirect(url_for('book'))

        # Insert booking
        cursor.execute("INSERT INTO bookings (user_id, doctor_name, time_slot, booked_at) VALUES (%s, %s, %s, NOW())",
                       (user_id, selected_professional_name, time_slot))
        mysql.connection.commit()
        cursor.close()

        flash("Booking successful!", "success")
        return redirect(url_for('view_bookings'))

    selected_professional_name = request.args.get('professional')
    selected_professional = next((prof for prof in profs if prof['name'] == selected_professional_name), None)
    return render_template('book.html', professionals=profs, selected_professional=selected_professional)


@app.route('/bookings')
def view_bookings():
    if 'email' not in session:
        return redirect(url_for('login_page'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT id FROM user WHERE email = %s", (session['email'],))
    user = cursor.fetchone()
    if not user:
        flash("User not found", "danger")
        return redirect(url_for('login_page'))

    cursor.execute("SELECT doctor_name, time_slot FROM bookings WHERE user_id = %s", (user['id'],))
    user_bookings = cursor.fetchall()
    return render_template('bookings.html', bookings=user_bookings)


@app.route('/delete_comment/<int:post_id>/<int:comment_index>', methods=["POST"])
def delete_comment(post_id, comment_index):
    if 'email' not in session:
        return jsonify({"success": False, "error": "User not logged in"})

    for post in posts:
        if post['id'] == post_id and 0 <= comment_index < len(post['comments']):
            if post['comments'][comment_index]['user'] == session['email']:
                del post['comments'][comment_index]
                return jsonify({"success": True})
            return jsonify({"success": False, "error": "Unauthorized deletion"})

    return jsonify({"success": False, "error": "Comment not found"})

@app.route('/add_comment/<int:post_id>', methods=["POST"])
def add_comment(post_id):
    if 'email' not in session:
        return jsonify({"success": False, "error": "User not logged in"})

    comment_text = request.form.get('comment_text')
    if not comment_text:
        return jsonify({"success": False, "error": "Empty comment"})

    for post in posts:
        if post['id'] == post_id:
            new_comment = {"user": session['email'], "text": comment_text}
            post['comments'].append(new_comment)
            comment_index = len(post['comments']) - 1
            return jsonify({"success": True, "user": session['email'], "comment_index": comment_index})

    return jsonify({"success": False, "error": "Post not found"})

@app.route('/ss')
def success_stories():
    return render_template('ss.html', stories=success_stories_list)

@app.route('/addsts', methods=["GET", "POST"])
def addsts():
    if 'email' not in session:
        return redirect(url_for('login_page'))

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        file = request.files['photo']

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            success_stories_list.append({'name': name, 'description': description, 'photo': filename})
            flash('Success Story Added!', 'success')
        else:
            flash('Invalid file type. Please upload an image.', 'error')
            return redirect(url_for('addsts'))

        return redirect(url_for('success_stories'))

    return render_template('addsts.html')

@app.route('/zen')
def zen_game():
    return render_template('zen.html')

@app.route('/memory')
def memory_game():
    return render_template('memorygm.html')

@app.route('/breathe')
def breathe_game():
    return render_template('breathgame.html')

if __name__ == "__main__":
    app.run(debug=True, port=8000, host="0.0.0.0")