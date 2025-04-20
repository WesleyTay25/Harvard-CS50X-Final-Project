import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, timedelta
import pytz
import calendar

from helpers import login_required

# Configure application
app = Flask(__name__)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///data.db")

if __name__ == "__main__":
    app.run(debug=True)

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

#Home page
@app.route('/')
@login_required
def index():

    userID = session.get("user_id")
    name = db.execute("SELECT username FROM users WHERE id = ?", userID)
    name = name[0]["username"]

    profile = db.execute("SELECT * FROM profile WHERE userid = ?", userID)
    if not profile:
        flash("Please enter particulars first")
        return redirect("/profile")

    weight = profile[0]["weight"]
    height = profile[0]["height"]
    age = profile[0]["age"]
    gender = profile[0]["gender"]
    goal = profile[0]["goal"]

    #BMR Calculator:
    BMR = 0
    if gender == 'M':
        BMR = 88.362 + (13.397 * weight) + (4.799 * height) - (5.677 * age)
    elif gender == 'F':
        BMR = 447.593 + (9.247 * weight) + (3.098 * height) - (5.677 * age)

    BMR = round(BMR, 2)

    #daily calorie limit:
    calorie = db.execute("SELECT calorie from calorielimit WHERE userid = ?", userID)
    if not calorie:
        calorie = 0
        if weight > goal:
            calorie = round((BMR - 200),2)
        elif weight == goal:
            calorie = round(BMR,2)
        else:
            calorie = round((BMR + 200),2)
    else:
        calorie = calorie[0]["calorie"]

    #protein intake:
    protein = db.execute("SELECT protein from calorielimit WHERE userid = ?", userID)
    if not protein:
        protein = 0
        protein = round((weight * 2.205),2)
    else:
        protein = protein[0]["protein"]


    existing = db.execute("SELECT * from calorielimit WHERE userid = ?", userID)
    if not existing:
        db.execute("INSERT INTO calorielimit (BMR, calorie, protein, userid) VALUES (?,?,?,?)", BMR, calorie, protein, userID)
    else:
        db.execute("UPDATE calorielimit SET BMR = ?, calorie = ?, protein = ? WHERE userid = ?", BMR, calorie, protein, userID)

    return render_template("home.html", name=name, profile=profile, BMR=BMR, calorie=calorie, protein=protein)

#Register Page
@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        if not username:
            flash("Enter username")
            return redirect('/register')

        email = request.form.get("email")
        if not email:
            flash("Enter email")
            return redirect('/register')

        existing_emails = db.execute("SELECT email FROM users WHERE email = ?", email)
        if existing_emails:
            flash("Enter unique email")
            return redirect('/register')

        password = request.form.get("password")
        if not password:
            flash("Enter password")
            return redirect('/register')

        confirmation = request.form.get("confirmation")
        if not confirmation:
            flash("Confirm Password")
            return redirect('/register')

        if confirmation != password:
            flash("passwords dont match")
            return redirect('/register')
        
        try:
           passwordhash = generate_password_hash(password)
           db.execute("INSERT INTO users (username, email, password) VALUES (?,?,?)", username, email, passwordhash)
        except ValueError:
            flash("Please enter unique email")
            return redirect('/register')
        
        return redirect("/")

    return render_template("register.html")

#login page
@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return redirect('/login')

        # Ensure password was submitted
        elif not request.form.get("password"):
            return redirect('/login')

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["password"], request.form.get("password")
        ):
            return redirect('/login')

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

#Log Out
@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

#Profile Page
@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    userID = session.get("user_id")
    if request.method == "POST":
        weight = request.form.get("weight")
        if not weight:
            flash("Enter Weight!")
            return redirect("/profile")
        try:
            weight = float(weight)
            if weight < 0:
                flash("Weight must not be below 0!")
                return redirect("/profile")
        except ValueError:
            flash("Weight must be a number!")
            return redirect("/profile")

        goal = request.form.get("goal")
        if not goal:
            flash("Enter Goal weight!")
            return redirect("/profile")
        try:
            goal = float(goal)
            if goal < 0:
                flash("Goal weight must not be below 0!")
                return redirect("/profile")
        except ValueError:
            flash("Goal weight must be a number!")
            return redirect("/profile")

        height = request.form.get("height")

        if not height:
            flash("Enter Height!")
            return redirect("/profile")
        try:
            height = int(height)
            if height < 0:
                flash("Height must be above 0!")
                return redirect("/profile")
        except ValueError:
            flash("Height must be a number!")
            return redirect("/profile")

        age = request.form.get("age")
        if not age:
            flash("Enter age!")
            return redirect("/profile")
        try:
            age = int(age)
            if age < 0:
                flash("Age must be above 0!")
                return redirect("/profile")
        except ValueError:
            flash("Age must be a number!")
            return redirect("/profile")

        gender = request.form.get("gender")
        if not gender:
            flash("Enter gender!")
            return redirect("/profile")
        if gender != 'F' and gender != 'M':
            flash("Male or Female Only!")
            return redirect("/profile")

        sg_timezone = datetime.now(pytz.timezone("Asia/Singapore"))

        existing_profile = db.execute("SELECT * from profile WHERE userid = ?", userID)
        if existing_profile:
            db.execute("UPDATE profile SET weight = ?, height = ?, age = ?, gender = ?, goal = ? WHERE userid = ?", weight, height, age, gender, goal, userID)
        else:
            db.execute("INSERT INTO profile (weight, height, age, gender, goal, userid) VALUES (?,?,?,?,?,?)",weight,height,age,gender, goal, userID)
        db.execute("INSERT INTO weight (weight, userid, date) VALUES (?,?,?)", weight, userID, sg_timezone)
        return redirect("/")

    return render_template("profile.html")

#Weight Tracker
@app.route("/weight", methods=["POST", "GET"])
@login_required
def weight():
    userID = session.get("user_id")
    weight = db.execute("SELECT weight from profile WHERE userid = ?", userID)
    goal = db.execute("SELECT goal from profile WHERE userid = ?", userID)
    weight = weight[0]["weight"]
    goal = goal[0]["goal"]
    if request.method == "POST":
        weight = request.form.get("weight")
        if not weight:
            flash("Enter Weight!")
            return redirect("/weight")
        try:
            weight = float(weight)
            if weight < 0:
                flash("Weight must not be below 0!")
                return redirect("/weight")
        except ValueError:
            flash("Weight must be a number!")
            return redirect("/weight")

        weight_goal = request.form.get("goal")
        if weight_goal:
            try:
                weight_goal = float(weight_goal)
                if weight_goal < 0:
                    flash("Goal weight must not be below 0!")
                    return redirect("/weight")
            except ValueError:
                flash("Goal weight must be a number!")
                return redirect("/weight")


        calorie = request.form.get("calorie")
        if calorie:
            try:
                calorie = int(calorie)
                if calorie < 0:
                    flash("Calorie limit must not be below 0!")
                    return redirect("/weight")
            except ValueError:
                flash("Calorie limit must be a number!")
                return redirect("/weight")


        protein = request.form.get("protein")
        if protein:
            try:
                protein = int(protein)
                if goal < 0:
                    flash("Protein intake must not be below 0!")
                    return redirect("/weight")
            except ValueError:
                flash("Protein intake must be a number!")
                return redirect("/weight")

        sg_timezone = datetime.now(pytz.timezone("Asia/Singapore"))

        db.execute("INSERT INTO weight (weight, userid, date) VALUES (?,?,?)", weight, userID, sg_timezone)
        db.execute("UPDATE profile SET weight = ? WHERE userid = ?", weight, userID)


        if calorie and protein:
            db.execute("UPDATE calorielimit SET calorie = ?, protein = ? WHERE userid = ?", calorie, protein, userID)
        elif calorie and not protein:
            db.execute("UPDATE calorielimit SET calorie = ? WHERE userid = ?", calorie, userID)
        elif protein and not calorie:
            db.execute("UPDATE calorielimit SET protein = ? WHERE userid = ?", protein, userID)

        if weight_goal:
            db.execute("UPDATE profile SET goal = ? WHERE userid = ?", weight_goal, userID)

        return redirect("/weight")

    return render_template("weight.html", weight=weight, goal=goal)

#Nutrient Tracker
@app.route("/food", methods=["POST", "GET"])
@login_required
def food():
    userID = session.get("user_id")
    Nutrient_required = db.execute("SELECT * from calorielimit WHERE userid = ?", userID)

    calorielimit = Nutrient_required[0]["calorie"]
    proteinlimit = Nutrient_required[0]["protein"]


    sg = pytz.timezone("Asia/Singapore")
    now = datetime.now(sg)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start.replace(day=today_start.day + 1)
    print(today_start)
    print(today_end)

    nutrients = db.execute("SELECT calorie, protein, date FROM calorietracker WHERE userid = ? AND date >= ? AND date < ?", userID, today_start, today_end)
    caloriesum = 0
    proteinsum = 0
    for calorie in nutrients:
        caloriesum += calorie["calorie"]

    for protein in nutrients:
        proteinsum += protein["protein"]

    calorieleft = round((calorielimit - caloriesum),2)
    proteinleft = round((proteinlimit - proteinsum),2)

    calorie_burned = db.execute("SELECT calorie FROM workout WHERE userid = ? AND date >= ? AND date < ?", userID, today_start, today_end)
    if calorie_burned:
        calorie_burned = calorie_burned[0]["calorie"]
    else:
        calorie_burned = 0

    #Calorie intake
    if request.method == "POST":
        calorie = request.form.get("calorie")
        if not calorie:
            flash("Enter calories!")
            return redirect("/food")
        try:
            calorie = int(calorie)
            if calorie < 0:
                flash("calories cannot be below 0!")
                return redirect("/food")
        except ValueError:
            flash("Calories must be a number!")
            return redirect("/food")

        #Protein intake
        protein = request.form.get("protein")
        if not protein:
            flash("Enter protein!")
            return redirect("/food")
        try:
            protein = float(protein)
            if calorie < 0:
                flash("protein cannot be below 0!")
                return redirect("/food")
        except ValueError:
            flash("Protein intake must be a number!")
            return redirect("/food")

        sg_timezone = datetime.now(pytz.timezone("Asia/Singapore"))
        db.execute("INSERT INTO calorietracker (calorie, userid, protein, date) VALUES (?,?,?,?)", calorie, userID, protein, sg_timezone)
        return redirect("/food")

    return render_template("food.html", calorielimit=calorielimit, calorieleft=calorieleft, proteinleft=proteinleft, nutrients=nutrients, calorie_burned=calorie_burned)

#Workout Tracker
@app.route("/workout", methods=["POST", "GET"])
@login_required
def workout():
    userID = session.get("user_id")
    workouts = db.execute("SELECT * from workout WHERE userid = ?", userID)
    if request.method == "POST":
        calorie = request.form.get("calorie")
        if not calorie:
            flash("Enter Calorie Burned!")
            return redirect("/workout")
        try:
            calorie = float(calorie)
            if calorie < 0:
                flash("Calorie burned must not be below 0!")
                return redirect("/workout")
        except ValueError:
            flash("Calories burned must be a number!")
            return redirect("/workout")

        workout = request.form.get("workout")
        if not workout:
            flash("Enter Workout type!")
            return redirect("/workout")
        if workout != 'Strength' and workout != 'Cardio':
            flash("Invalid Input!")
            return redirect("/workout")

        sg_timezone = datetime.now(pytz.timezone("Asia/Singapore"))
        db.execute("INSERT INTO workout (calorie, userid, type, date) VALUES (?,?,?,?)", calorie, userID, workout, sg_timezone)
        return redirect("/workout")

    return render_template("workout.html", workouts=workouts)

#Dashboard
@app.route("/dashboard", methods=["POST", "GET"])
@login_required
def dashboard():
    userID = session.get("user_id")
    ''' 1. Chart to show calorie/protein intake for the week/month/year
        2. show line graph for weight loss
        3. show graph for no. of workouts done so far'''

    today = datetime.now(pytz.timezone("Asia/Singapore"))

    #Monday
    start_of_week = today - timedelta(days=today.weekday())
    calories_total = []
    days_labels = []

    for i in range(7):
        day = start_of_week + timedelta(days=i)
        next_day = day + timedelta(days=1)
        result = db.execute("SELECT SUM(calorie) as total FROM calorietracker WHERE date >= ? AND date < ? AND userid = ?", day, next_day, userID)

        calories = result[0]["total"] or 0
        calories_total.append(calories)
        days_labels.append(day.strftime("%A"))

    limit = db.execute("SELECT calorie FROM calorielimit WHERE userid = ?", userID)[0]["calorie"]

#---------------------WEIGHT-------------------------------------------
    first_day = today.replace(day=1)
    last_day = today.replace(day=calendar.monthrange(today.year, today.month)[1])

    days = [first_day + timedelta(days=i) for i in range((last_day - first_day).days + 1)]
    labels = [d.strftime("%d %B").lstrip("0").replace(" 0", " ") for d in days]

    date_list = [(first_day + timedelta(days=i)).strftime("%Y-%m-%d") for i in range((last_day - first_day).days + 1)]

    # Get weights logged per day
    rows = db.execute("SELECT Date(date) as date, weight FROM weight WHERE userid = ? AND date BETWEEN ? AND ?", userID, first_day.strftime("%Y-%m-%d"), last_day.strftime("%Y-%m-%d"))

    # Map weights to date
    weight_map = {row["date"]: row["weight"] for row in rows}
    weights = [weight_map.get(date, None) for date in date_list]
    labels = [datetime.strptime(date, "%Y-%m-%d").strftime("%d %B").lstrip("0").replace(" 0", " ") for date in date_list]

    goal = db.execute("SELECT goal FROM profile WHERE userid = ?", userID)[0]["goal"]

    return render_template("dashboard.html", days_label=days_labels, labels=labels, calories_total = calories_total, calorielimit=limit, weights=weights, goal=goal)

#Change password
@app.route("/forget", methods=["POST", "GET"])
def change_password():
    userID = session.get("user_id")
    if request.method == "POST":
        email = request.form.get("email")
        if not email:
            flash("Enter email!")
            return redirect("/forget")
        
        exist_email = db.execute("SELECT email, id from users WHERE email = ?", email)
        if not exist_email:
            flash("You are not registered")
            return redirect("/register")
        id = exist_email[0]["id"]

        password = request.form.get("password")
        if not password:
            flash("Enter Password")
            return redirect("/forget")
        
        confirmation = request.form.get("confirmation")
        if not confirmation:
            flash("Confirm Password")
            return redirect("/forget")
        
        if confirmation != password:
            flash("Passwords do not match")
            return redirect("/forget")
        
        try:
           passwordhash = generate_password_hash(password)
           db.execute("UPDATE users SET password = ? WHERE id = ?", passwordhash, id)
        except ValueError:
            flash("Error")
            return redirect('/forget')

        flash("password successfully changed")
        return redirect("/login")
    
    return render_template("changepassword.html")