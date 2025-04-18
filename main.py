from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_cors import CORS
from flask_mysqldb import MySQL
from werkzeug.utils import secure_filename
import os
import groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
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

# ----------------- Posts Data -----------------
posts = [
    # Each post is a dictionary with title, author, content, and a list of comments
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
    if 'user_id' not in session and 'id' not in session:
        flash("You need to log in to view profiles.", "warning")
        return redirect(url_for('login_page'))

    cur = mysql.connection.cursor()
    cur.execute("SELECT id, email, username FROM user WHERE username = %s", (username,))
    user_data = cur.fetchone()

    if not user_data:
        flash("User not found.", "danger")
        cur.close()
        return redirect(url_for('index'))

    user_id = user_data[0]
    user = {'id': user_id, 'email': user_data[1], 'username': user_data[2]}

    cur.execute("SELECT bio, profile_pic, gender, mental_health_status, preferred_contact_method FROM user_profiles WHERE user_id = %s", (user_id,))
    profile_data = cur.fetchone()
    cur.close()

    if profile_data:
        user.update({
            'bio': profile_data[0],
            'profile_pic': profile_data[1] or 'default.png',
            'gender': profile_data[2],
            'mental_health_status': profile_data[3],
            'preferred_contact_method': profile_data[4]
        })
    else:
        user.update({'bio': None, 'profile_pic': 'default.png', 'gender': None, 'mental_health_status': None, 'preferred_contact_method': None})

    user_posts = [post for post in posts if post['author'] == username]
    return render_template('profile.html', user=user, posts=user_posts)

@app.route("/edit-profile", methods=["GET", "POST"])
def edit_profile():
   def profile(username):
    if 'user_id' not in session and 'id' not in session:
        flash("You need to log in to view profiles.", "warning")
        return redirect(url_for('login_page'))

    cur = mysql.connection.cursor()
    cur.execute("SELECT id, email, username FROM user WHERE username = %s", (username,))
    user_data = cur.fetchone()

    if not user_data:
        flash("User not found.", "danger")
        cur.close()
        return redirect(url_for('index'))

    user_id = user_data[0]
    user = {'id': user_id, 'email': user_data[1], 'username': user_data[2]}

    cur.execute("SELECT bio, profile_pic, gender, mental_health_status, preferred_contact_method FROM user_profiles WHERE user_id = %s", (user_id,))
    profile_data = cur.fetchone()
    cur.close()

    if profile_data:
        user.update({
            'bio': profile_data[0],
            'profile_pic': profile_data[1] or 'default.png',
            'gender': profile_data[2],
            'mental_health_status': profile_data[3],
            'preferred_contact_method': profile_data[4]
        })
    else:
        user.update({'bio': None, 'profile_pic': 'default.png', 'gender': None, 'mental_health_status': None, 'preferred_contact_method': None})

    user_posts = [post for post in posts if post['author'] == username]
    return render_template('profile.html', user=user, posts=user_posts)


#  --------------------------Professionals page --------------------------
@app.route('/professionals')
def professionals():
    return render_template('professionals.html', professionals=profs)

#  --------------------------Book appointment route --------------------------
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

        for booking in bookings:
            if booking['professional'] == selected_professional_name and booking['time_slot'] == time_slot:
                flash("This time slot is already booked.", "danger")
                return redirect(url_for('book'))

        bookings.append({"user": session['email'], "professional": selected_professional_name, "time_slot": time_slot})
        flash("Booking successful!", "success")
        return redirect(url_for('view_bookings'))

    selected_professional_name = request.args.get('professional')
    selected_professional = next((prof for prof in profs if prof['name'] == selected_professional_name), None)
    return render_template('book.html', professionals=profs, selected_professional=selected_professional)

#  --------------------------View all bookings for a user --------------------------
@app.route('/bookings')
def view_bookings():
    user_bookings = [b for b in bookings if b['user'] == session.get('email')]
    return render_template('bookings.html', bookings=user_bookings)

# ---------------------Delete comment from a post---------------------------
@app.route('/delete_comment/<int:post_id>/<int:comment_index>', methods=['POST'])
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

#  --------------------------Add a comment to a post --------------------------
@app.route('/add_comment/<int:post_id>', methods=['POST'])
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

#  --------------------------Show all success stories --------------------------
@app.route('/ss')
def success_stories():
    return render_template('ss.html', stories=success_stories_list)

#  --------------------------Add a success story --------------------------
@app.route('/addsts', methods=['GET', 'POST'])
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


#----------------------------games-------------------->
#------------------------------bubble------------------------>
@app.route('/bubble')
def bubble_game():
    return render_template('bubble.html')

#-------------------------------memory------------------------->
@app.route('/memory')
def memory_game():
    return render_template('memorygm.html')

#-------------------------------breath------------------------->
@app.route('/breathe')
def breathe_game():
    return render_template('breathgame.html')

# ----------------- Main -----------------
if __name__ == "__main__":
    app.run(debug=True, port=8000, host="0.0.0.0")
