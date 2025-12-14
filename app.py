import threading
from datetime import datetime, date, timedelta
from flask import Flask, render_template, redirect, url_for
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from models import db, Task, Project, Category, User, Cycle, TaskDependency, XPHistory
from sqlalchemy import func

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///project_manager.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'dev-key-for-sessions'  # Required for Flask-Admin

db.init_app(app)

# --- FLASK ADMIN SETUP ---
# Access this at http://localhost:5000/admin
admin = Admin(app, name='Project Manager', template_mode='bootstrap3')

admin.add_view(ModelView(Task, db.session))
admin.add_view(ModelView(Project, db.session))
admin.add_view(ModelView(Category, db.session))
admin.add_view(ModelView(User, db.session))
admin.add_view(ModelView(Cycle, db.session))
admin.add_view(ModelView(TaskDependency, db.session))
admin.add_view(ModelView(XPHistory, db.session))

# --- CONFIGURATION & HARDCODED LOGIC ---

XP_LEVELS = {
    1: {"name": "Ensign", "xp": 0},
    2: {"name": "Engineering Student", "xp": 10000},
    3: {"name": "Physics Afficiando", "xp": 100000},
    4: {"name": "Engineering Assistant", "xp": 1000000},
    5: {"name": "Quantum Enthusiast", "xp": 10000000},
    6: {"name": "Black Arts Sailer", "xp": 100000000},
    7: {"name": "Embedded Diver", "xp": 1000000000},
    8: {"name": "Renaissance Student", "xp": 10000000000},
    9: {"name": "Master of the layers", "xp": 100000000000},
    10: {"name": "Captain of the Electrons", "xp": 1000000000000}
}

RECURRING_TASKS = {
    "Cooking": {"days": [1, 3, 6], "xp": 50, "desc": "Make food (Tue, Thu, Sun)"}, # 0=Mon, 6=Sun
    "Sweep House": {"days": [0], "xp": 30, "desc": "Sweep the house (Mon)"},
    "Laundry": {"days": [3], "xp": 40, "desc": "Do Laundry (Thu)"},
}

# --- HELPER FUNCTIONS ---

def get_user_level(current_xp):
    """Determines user level based on hardcoded table."""
    current_lvl = 1
    current_title = XP_LEVELS[1]["name"]
    
    for lvl, data in XP_LEVELS.items():
        if current_xp >= data["xp"]:
            current_lvl = lvl
            current_title = data["name"]
        else:
            break
    return current_lvl, current_title

def calculate_task_score(task):
    """
    Calculates priority score based on User Formula.
    Higher score = Higher priority.
    """
    if not task.deadline:
        return 0
    
    today = date.today()
    delta = (task.deadline - today).days
    xp = task.xp_award
    
    if delta > 0:
        # Due in future: (1 / days_until_due) * XP
        # Example: Due tomorrow (1 day) = 1.0 * XP
        # Example: Due in 2 days = 0.5 * XP
        score = (1 / delta) * xp
    elif delta == 0:
        # Due Today. 
        # MODIFICATION: Must be higher than tomorrow.
        # Tomorrow is (1/1) * XP = XP. 
        # So Today needs to be > XP. Let's do XP * 1.5 to bump it up.
        score = xp * 1.5
    else:
        # Overdue: Abs(days) * XP
        # Example: 1 day late = 1 * XP (Lower than Today, confusing?)
        # Let's trust the user's formula: Abs(-1) * XP = XP.
        # This implies Day 0 (Today) is actually higher priority than 1 day late
        # unless we tweak logic. Sticking to prompt formula exactly for "Else".
        score = abs(delta) * xp
        
    return score

def check_recurring_tasks():
    """
    Checks if recurring tasks for today exist. If not, creates them.
    Runs on background thread or startup.
    """
    with app.app_context():
        today = date.today()
        weekday = today.weekday() # 0=Mon, 6=Sun
        
        # 1. Standard Weekly/Daily tasks
        for name, data in RECURRING_TASKS.items():
            if weekday in data['days']:
                # Check if task already exists for today
                exists = Task.query.filter(
                    Task.name == name, 
                    Task.deadline == today,
                    Task.date_time_complete == None
                ).first()
                
                if not exists:
                    new_task = Task(
                        name=name,
                        description=data['desc'],
                        xp_award=data['xp'],
                        deadline=today,
                        estimated_cycles=1
                    )
                    db.session.add(new_task)
                    print(f"Auto-generated task: {name}")

        # 2. Bi-weekly Logic (Clean Bathroom vs Clean Floors)
        # We use ISO week number. Even weeks = Bathroom, Odd weeks = Floors
        # Trigger on Tuesday (weekday == 1)
        if weekday == 1:
            iso_week = today.isocalendar()[1]
            task_name = "Clean Bathroom" if (iso_week % 2 == 0) else "Clean Floors"
            task_desc = "Bi-weekly cleaning task"
            
            exists = Task.query.filter(
                Task.name == task_name,
                Task.deadline == today,
                Task.date_time_complete == None
            ).first()
            
            if not exists:
                new_task = Task(
                    name=task_name,
                    description=task_desc,
                    xp_award=100,
                    deadline=today,
                    estimated_cycles=2
                )
                db.session.add(new_task)
                print(f"Auto-generated task: {task_name}")

        db.session.commit()

# --- ROUTES ---

@app.route('/')
def index():
    # 1. Fetch User Stats
    user = User.query.first()
    if not user:
        # Create default user if none exists
        user = User(xp=0, level=1)
        db.session.add(user)
        db.session.commit()
    
    current_lvl, title = get_user_level(user.xp)
    
    # 2. Fetch Incomplete Tasks
    tasks = Task.query.filter(Task.date_time_complete == None).all()
    
    # 3. Calculate Scores & Sort
    # We create a list of dicts or tuples to sort
    scored_tasks = []
    for t in tasks:
        score = calculate_task_score(t)
        scored_tasks.append((t, score))
    
    # Sort by score descending (Highest priority first)
    scored_tasks.sort(key=lambda x: x[1], reverse=True)
    
    # Top 5 tasks
    top_tasks = [t[0] for t in scored_tasks[:5]]
    
    return render_template('index.html', 
                           user=user, 
                           level_title=title, 
                           tasks=top_tasks)

# --- STARTUP ---

def init_db():
    with app.app_context():
        db.create_all()

if __name__ == '__main__':
    # Initialize DB
    init_db()
    
    # Run background check for recurring tasks immediately on start
    # Using a thread so it doesn't block startup, though it's fast enough here.
    threading.Thread(target=check_recurring_tasks).start()
    
    # Run App
    app.run(host='0.0.0.0', debug=True)