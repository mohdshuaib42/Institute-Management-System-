from flask import Flask,render_template,request,session,redirect,url_for,flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash,check_password_hash
from flask_login import login_user,logout_user,login_manager,LoginManager
from flask_login import login_required,current_user 
import json
import os
import time
import pymysql

def wait_for_db():
    while True:
        try:
            conn = pymysql.connect(
                host=os.getenv("DB_HOST"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                database=os.getenv("DB_NAME")
            )
            conn.close()
            print("✅ Database is ready")
            break
        except Exception as e:
            print("⏳ Waiting for database...")
            time.sleep(3)


# MY db connection
local_server= True
app = Flask(__name__)
app.secret_key='kusumachandashwini'


# this is for getting unique user access
login_manager=LoginManager(app)
login_manager.login_view='login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))



# app.config['SQLALCHEMY_DATABASE_URL']='mysql://username:password@localhost/databas_table_name'
app.config['SQLALCHEMY_DATABASE_URI'] = (
    f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

wait_for_db()

db=SQLAlchemy(app)



# here we will create db models that is tables
class Test(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    name=db.Column(db.String(100))
    email=db.Column(db.String(100))

class Department(db.Model):
    cid=db.Column(db.Integer,primary_key=True)
    branch=db.Column(db.String(100))

class Attendence(db.Model):
    aid=db.Column(db.Integer,primary_key=True)
    rollno=db.Column(db.String(100))
    attendance=db.Column(db.Integer())

class Trig(db.Model):
    tid=db.Column(db.Integer,primary_key=True)
    rollno=db.Column(db.String(100))
    action=db.Column(db.String(100))
    timestamp=db.Column(db.String(100))


class User(UserMixin,db.Model):
    id=db.Column(db.Integer,primary_key=True)
    username=db.Column(db.String(50))
    email=db.Column(db.String(50),unique=True)
    password=db.Column(db.String(1000))





class Student(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    rollno=db.Column(db.String(50))
    sname=db.Column(db.String(50))
    sem=db.Column(db.Integer)
    gender=db.Column(db.String(50))
    branch=db.Column(db.String(50))
    email=db.Column(db.String(50))
    number=db.Column(db.String(12))
    address=db.Column(db.String(100))


def get_required_form_data(field_labels):
    cleaned_data = {}
    missing_fields = []

    for field_name, field_label in field_labels.items():
        value = (request.form.get(field_name) or "").strip()
        cleaned_data[field_name] = value

        if not value or value.lower().startswith("select "):
            missing_fields.append(field_label)

    return cleaned_data, missing_fields


def flash_missing_fields(missing_fields):
    flash(f"Please fill the {', '.join(missing_fields)}.", "warning")
    

@app.route('/')
def index(): 
    return render_template('index.html')

@app.route('/studentdetails')
def studentdetails():
    # query=db.engine.execute(f"SELECT * FROM `student`") 
    query=Student.query.all() 
    return render_template('studentdetails.html',query=query)

@app.route('/triggers')
def triggers():
    # query=db.engine.execute(f"SELECT * FROM `trig`") 
    query=Trig.query.all()
    return render_template('triggers.html',query=query)

@app.route('/department',methods=['POST','GET'])
def department():
    if request.method=="POST":
        form_data, missing_fields = get_required_form_data({
            'dept': 'department'
        })
        if missing_fields:
            flash_missing_fields(missing_fields)
            return render_template('department.html')

        dept = form_data['dept']
        query=Department.query.filter_by(branch=dept).first()
        if query:
            flash("Department Already Exist","warning")
            return redirect('/department')
        dep=Department(branch=dept)
        db.session.add(dep)
        db.session.commit()
        flash("Department Addes","success")
    return render_template('department.html')

@app.route('/addattendance',methods=['POST','GET'])
def addattendance():
    # query=db.engine.execute(f"SELECT * FROM `student`") 
    query=Student.query.all()
    if request.method=="POST":
        form_data, missing_fields = get_required_form_data({
            'rollno': 'roll number',
            'attend': 'attendance percentage'
        })
        if missing_fields:
            flash_missing_fields(missing_fields)
            return render_template('attendance.html',query=query)

        rollno = form_data['rollno']
        attend = form_data['attend']
        print(attend,rollno)
        atte=Attendence(rollno=rollno,attendance=attend)
        db.session.add(atte)
        db.session.commit()
        flash("Attendance added","warning")

        
    return render_template('attendance.html',query=query)

@app.route('/search',methods=['POST','GET'])
def search():
    if request.method=="POST":
        form_data, missing_fields = get_required_form_data({
            'roll': 'roll number'
        })
        if missing_fields:
            flash_missing_fields(missing_fields)
            return render_template('search.html', searched=False)

        rollno = form_data['roll']
        bio=Student.query.filter_by(rollno=rollno).first()
        attend=Attendence.query.filter_by(rollno=rollno).first()
        return render_template('search.html',bio=bio,attend=attend, searched=True)
        
    return render_template('search.html', searched=False)

@app.route("/delete/<string:id>",methods=['POST','GET'])
@login_required
def delete(id):
    post=Student.query.filter_by(id=id).first()
    db.session.delete(post)
    db.session.commit()
    # db.engine.execute(f"DELETE FROM `student` WHERE `student`.`id`={id}")
    flash("Slot Deleted Successful","danger")
    return redirect('/studentdetails')


@app.route("/edit/<string:id>",methods=['POST','GET'])
@login_required
def edit(id):
    # dept=db.engine.execute("SELECT * FROM `department`")    
    if request.method=="POST":
        form_data, missing_fields = get_required_form_data({
            'rollno': 'roll number',
            'sname': 'student name',
            'sem': 'semester',
            'gender': 'gender',
            'branch': 'branch',
            'email': 'email',
            'num': 'phone number',
            'address': 'address'
        })
        post=Student.query.filter_by(id=id).first()
        dept=Department.query.all()
        if missing_fields:
            flash_missing_fields(missing_fields)
            return render_template('edit.html',posts=post,dept=dept)

        rollno = form_data['rollno']
        sname = form_data['sname']
        sem = form_data['sem']
        gender = form_data['gender']
        branch = form_data['branch']
        email = form_data['email']
        num = form_data['num']
        address = form_data['address']
        duplicate_student = Student.query.filter(
            Student.rollno == rollno,
            Student.id != id
        ).first()
        if duplicate_student:
            flash("Roll number already exists", "warning")
            return render_template('edit.html',posts=post,dept=dept)
        # query=db.engine.execute(f"UPDATE `student` SET `rollno`='{rollno}',`sname`='{sname}',`sem`='{sem}',`gender`='{gender}',`branch`='{branch}',`email`='{email}',`number`='{num}',`address`='{address}'")
        post.rollno=rollno
        post.sname=sname
        post.sem=sem
        post.gender=gender
        post.branch=branch
        post.email=email
        post.number=num
        post.address=address
        db.session.commit()
        flash("Slot is Updates","success")
        return redirect('/studentdetails')
    dept=Department.query.all()
    posts=Student.query.filter_by(id=id).first()
    return render_template('edit.html',posts=posts,dept=dept)


@app.route('/signup',methods=['POST','GET'])
def signup():
    if request.method == "POST":
        form_data, missing_fields = get_required_form_data({
            'username': 'username',
            'email': 'email',
            'password': 'password'
        })
        if missing_fields:
            flash_missing_fields(missing_fields)
            return render_template('signup.html')

        username = form_data['username']
        email = form_data['email']
        password = form_data['password']
        user=User.query.filter_by(email=email).first()
        if user:
            flash("Email Already Exist","warning")
            return render_template('signup.html')
        # encpassword=generate_password_hash(password)

        # new_user=db.engine.execute(f"INSERT INTO `user` (`username`,`email`,`password`) VALUES ('{username}','{email}','{encpassword}')")

        # this is method 2 to save data in db
        newuser=User(username=username,email=email,password=password)
        db.session.add(newuser)
        db.session.commit()
        flash("Signup Succes Please Login","success")
        return render_template('login.html')

          

    return render_template('signup.html')

@app.route('/login',methods=['POST','GET'])
def login():
    if request.method == "POST":
        form_data, missing_fields = get_required_form_data({
            'email': 'email',
            'password': 'password'
        })
        if missing_fields:
            flash_missing_fields(missing_fields)
            return render_template('login.html')

        email = form_data['email']
        password = form_data['password']
        user=User.query.filter_by(email=email).first()

        # if user and check_password_hash(user.password,password):
        if user and user.password == password:
            login_user(user)
            flash("Login Success","primary")
            return redirect(url_for('index'))
        else:
            flash("invalid credentials","danger")
            return render_template('login.html')    

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logout SuccessFul","warning")
    return redirect(url_for('login'))



@app.route('/addstudent',methods=['POST','GET'])
@login_required
def addstudent():
    # dept=db.engine.execute("SELECT * FROM `department`")
    dept=Department.query.all()
    if request.method=="POST":
        form_data, missing_fields = get_required_form_data({
            'rollno': 'roll number',
            'sname': 'student name',
            'sem': 'semester',
            'gender': 'gender',
            'branch': 'branch',
            'email': 'email',
            'num': 'phone number',
            'address': 'address'
        })
        if missing_fields:
            flash_missing_fields(missing_fields)
            return render_template('student.html',dept=dept)

        rollno = form_data['rollno']
        sname = form_data['sname']
        sem = form_data['sem']
        gender = form_data['gender']
        branch = form_data['branch']
        email = form_data['email']
        num = form_data['num']
        address = form_data['address']
        existing_student = Student.query.filter_by(rollno=rollno).first()
        if existing_student:
            flash("Roll number already exists", "warning")
            return render_template('student.html',dept=dept)
        # query=db.engine.execute(f"INSERT INTO `student` (`rollno`,`sname`,`sem`,`gender`,`branch`,`email`,`number`,`address`) VALUES ('{rollno}','{sname}','{sem}','{gender}','{branch}','{email}','{num}','{address}')")
        query=Student(rollno=rollno,sname=sname,sem=sem,gender=gender,branch=branch,email=email,number=num,address=address)
        db.session.add(query)
        db.session.commit()

        flash("Booking Confirmed","info")


    return render_template('student.html',dept=dept)
@app.route('/test')
def test():
    try:
        Test.query.all()
        return 'My database is Connected'
    except:
        return 'My db is not Connected'


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
  
