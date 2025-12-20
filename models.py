from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey
from datetime import datetime, date

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    xp = db.Column(db.Integer, default=0)
    level = db.Column(db.Integer, default=1)

class Category(db.Model):
    __tablename__ = 'category'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(25), nullable=False)
    description = db.Column(db.String(280))

    # Relationships
    projects = db.relationship('Project', backref='category', lazy=True)

    def __str__(self):
        return self.name

class Project(db.Model):
    __tablename__ = 'projects'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(25), nullable=False)
    description = db.Column(db.String(280))
    deadline = db.Column(db.Date)
    percent_complete = db.Column(db.Integer, default=0)
    ongoing = db.Column(db.Boolean, default=False)
    
    # Foreign Keys
    category_id = db.Column(db.Integer, ForeignKey('category.id'))
    parent_project_id = db.Column(db.Integer, ForeignKey('projects.id'), nullable=True)

    # Relationships
    tasks = db.relationship('Task', backref='project', lazy=True)
    subprojects = db.relationship('Project', backref=db.backref('parent', remote_side=[id]), lazy=True)

    def __str__(self):
        return self.name

class Task(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(25), nullable=False)
    description = db.Column(db.String(140))
    estimated_cycles = db.Column(db.Integer, default=1)
    cycles_used = db.Column(db.Integer, default=0)
    xp_award = db.Column(db.Integer, default=0)
    deadline = db.Column(db.Date)
    
    # "Status" is determined by completion date
    date_time_complete = db.Column(db.DateTime, nullable=True)

    # Foreign Keys
    project_id = db.Column(db.Integer, ForeignKey('projects.id'), nullable=True)

    # Relationships
    cycles = db.relationship('Cycle', backref='task', lazy=True)

    @property
    def is_complete(self):
        return self.date_time_complete is not None
    
    def __str__(self):
        return self.name

class TaskDependency(db.Model):
    __tablename__ = 'task_dependency'
    id = db.Column(db.Integer, primary_key=True)
    dependant_task_id = db.Column(db.Integer, ForeignKey('tasks.id'), nullable=False)
    prerequisite_task_id = db.Column(db.Integer, ForeignKey('tasks.id'), nullable=False)

class Cycle(db.Model):
    __tablename__ = 'cycles'
    id = db.Column(db.Integer, primary_key=True)
    datetime = db.Column(db.DateTime, default=datetime.utcnow)
    deep_cycle = db.Column(db.Boolean, default=False)
    
    # Foreign Keys
    task_id = db.Column(db.Integer, ForeignKey('tasks.id'))

class XPHistory(db.Model):
    __tablename__ = 'xp_history'
    id = db.Column(db.Integer, primary_key=True)
    xp = db.Column(db.Integer, default=0)
    week_start_date = db.Column(db.Date) # Monday of the week
    
    # Foreign Keys
    user_id = db.Column(db.Integer, ForeignKey('user.id'))