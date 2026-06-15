from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import ForeignKey
import click

class Base(DeclarativeBase):
  pass

#---set up stuff for flash n database, based on example code--
app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///catering.db'

app.secret_key = "gimmeA+please" #please :D

#---------models------------------
#based from: https://flask-sqlalchemy.palletsprojects.com/en/stable/models/
db = SQLAlchemy(model_class=Base)
db.init_app(app)

class User(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    role: Mapped[str] = mapped_column()
    username: Mapped[str] = mapped_column(unique=True)
    password: Mapped[str] = mapped_column()
    
class Event(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[str] = mapped_column()
    customerId: Mapped[int] = mapped_column(ForeignKey("user.id"))
    
class Staff(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    staffId: Mapped[str] = mapped_column(ForeignKey("user.id"))
    eventId: Mapped[int] = mapped_column(ForeignKey("event.id"))


#initalize database
@app.cli.command("initdb")
def initdb():
    db.drop_all()
    db.create_all()
    owner = User(role="owner", username="owner", password="pass")
    db.session.add(owner)
    db.session.commit()
    click.echo("DATABASE. INITILIAZED. BEEP. BOP.")


#--------------------------------------
#-----------ROUTES---------------------
#--------------------------------------
@app.route('/')
def default():
    return redirect(url_for('login'))


#-------------LOG IN---------------------------
#based on example code from the class GitHub
@app.route('/login', methods=['GET', 'POST'])
def login():
    
    # first check if the user is already logged in
    if 'username' in session:
        flash("Already logged in.")
        if session['role'] == 'owner':
            return redirect(url_for('owner_dashboard'))
        elif session['role'] == 'staff':
            return redirect(url_for('staff_dashboard'))
        else:
            return redirect(url_for('customer_dashboard'))
    
    #if not, check if user is logging in
    elif request.method == "POST":
        username = request.form['user']
        password = request.form['pass']
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            session['username'] = user.username
            session['role'] = user.role
            if user.role == 'owner':
                return redirect(url_for('owner_dashboard'))
            elif user.role == 'staff':
                return redirect(url_for('staff_dashboard'))
            else:
                return redirect(url_for('customer_dashboard'))
        else:
            flash('Oopsie, error logging you in!')
            
    return render_template('loginPage.html')


#---------LOG OUT----------------------------
#based on example code from the classGitHub
@app.route("/logout/")
def logout():
    # if logged in, log out, otherwise offer to log in
    if "username" in session:
        session.clear()
        flash("Successfully logged out!")
        return redirect(url_for("login"))
    else:
        flash("Not currently logged in.")
        return redirect(url_for("login"))
    
#-----------------REGISTRATION---------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['user']
        password = request.form['pass']
        
        #check to ensure username is unique
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists!')
            return render_template('register.html')
        #then add new user to db
        new_user = User(username=username, password=password, role='customer')
        db.session.add(new_user)
        db.session.commit()
        flash('Successfully registered!')
        return redirect(url_for('login'))
    
    return render_template('register.html') 

#-----------------STAFF REGISTRATION---------------------------
@app.route('/register_staff', methods=['GET', 'POST'])
def register_staff():
    #check its the owneer doing it
    if 'username' not in session or session['role'] != 'owner':
        flash("Must be the owner to access this page.")
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        username = request.form['user']
        password = request.form['pass']
        
        #check to ensure username is unique
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists!')
            return render_template('register_staff.html')
        #then add new user to db
        new_user = User(username=username, password=password, role='staff')
        db.session.add(new_user)
        db.session.commit()
        flash('Successfully registered!')
        return redirect(url_for('owner_dashboard'))
    
    return render_template('register_staff.html') 

#----------CANCEL EVENT----------------------------
@app.route('/cancel_event/<int:event_id>')
def cancel_event(event_id):
    
    #make sure its the customer who owns the event doing it
    if 'username' not in session or session['role'] != 'customer':
        flash("Must be a customer to access this page.")
        return redirect(url_for('login'))

    user = User.query.filter_by(username=session['username']).first()
    event = Event.query.filter_by(id=event_id, customerId=user.id).first()

    #handle the removing of events
    if event:
        db.session.delete(event)
        db.session.commit()
        flash('Event canceled!')
    else:
        flash('Event not found, or you are not the owner of this event.')

    return redirect(url_for('customer_dashboard'))

#-------------STAFF SIGN UP FOR EVENT----------------------------
@app.route('/sign_up/<int:event_id>')
def sign_up(event_id):
    
    #make sure its a staff member doing it
    if 'username' not in session or session['role'] != 'staff':
        flash("Must be a staff member to access this page.")
        return redirect(url_for('login'))

    user = User.query.filter_by(username=session['username']).first()
    event = Event.query.filter_by(id=event_id).first()

    if event:
        staff_count = Staff.query.filter_by(eventId=event_id).count()
        if staff_count < 3:
            existing_signup = Staff.query.filter_by(staffId=user.id, eventId=event_id).first()
            if existing_signup:
                flash('You have already signed up for this event!')
            else:
                new_signup = Staff(staffId=user.id, eventId=event_id)
                db.session.add(new_signup)
                db.session.commit()
                flash('Successfully signed up for the event!')
        else:
            flash('This event already has 3 staff members!')
    else:
        flash('Event not found!')

    return redirect(url_for('staff_dashboard'))

#-----------------DASHBOARDS---------------------------
#--------------owner-------------
@app.route('/owner')
def owner_dashboard():
    
    #make sure its the owner doing it
    if 'username' not in session or session['role'] != 'owner':
        flash("Must be the owner to access this page.")
        return redirect(url_for('login'))
    
    #show all the events and the staff
    else:
        events = Event.query.all()
        staff = {}
        for event in events:
            staff[event.id] = []
            for s in Staff.query.filter_by(eventId=event.id).all():
                user = User.query.filter_by(id=s.staffId).first()
                staff[event.id].append(user)
                
        return render_template('owner.html', events=events, staff=staff)
    
    
#--------------customer-------------  
@app.route('/customer', methods=['GET', 'POST'])
def customer_dashboard():
    
    #make sure its the customer doing it
    if 'username' not in session or session['role'] != 'customer':
        flash("Must be a customer to access this page.")
        return redirect(url_for('login'))
    
    user = User.query.filter_by(username=session['username']).first()
    events = Event.query.filter_by(customerId=user.id).all()
    
    #handle new event creation
    if request.method == 'POST':
        date=request.form['date']
        existing_event = Event.query.filter_by(date=date).first()
        if existing_event:
            flash('Event already scheduled on that date.')
            return render_template('customer.html', events=events)
        else:
            new_event = Event(date=date, customerId=user.id)
            db.session.add(new_event)
            db.session.commit()
            flash('Event successfully created!')
            events = Event.query.filter_by(customerId=user.id).all()
            
    return render_template('customer.html', events=events)
        
        
    
#--------------staff-------------
@app.route('/staff_dashboard')
def staff_dashboard():
    
    #make sure its the staff doing it
    if 'username' not in session or session['role'] != 'staff':
        flash("Must be a staff member to access this page.")
        return redirect(url_for('login'))
    
    user = User.query.filter_by(username=session['username']).first()
    
    #events this staff member is working
    my_shifts = Staff.query.filter_by(staffId=user.id).all()
    my_event_ids = [s.eventId for s in my_shifts]
    my_events = Event.query.filter(Event.id.in_(my_event_ids)).all()
    
    #events staff can sign up for, AND DONT SHOW MORE THAN 3 ONES
    all_events = Event.query.all()
    available_events = []
    for event in all_events:
        if event.id not in my_event_ids:
            staff_count = Staff.query.filter_by(eventId=event.id).count()
            if staff_count < 3:
                available_events.append(event)
    
    return render_template('staff.html', my_events=my_events, available_events=available_events)