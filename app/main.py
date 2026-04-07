from flask import Flask,render_template,request,session,redirect,url_for,flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash,check_password_hash
from flask_login import login_user,logout_user,login_manager,LoginManager
from flask_login import login_required,current_user 
from sqlalchemy import inspect, text
from werkzeug.middleware.proxy_fix import ProxyFix
import json
import os
import time
import pymysql
from types import SimpleNamespace

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
app.secret_key=os.getenv("FLASK_SECRET_KEY", "kusumachandashwini")
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)


# this is for getting unique user access
login_manager=LoginManager(app)
login_manager.login_view='login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))



# app.config['SQLALCHEMY_DATABASE_URL']='mysql://username:password@localhost/databas_table_name'
database_url = os.getenv("DATABASE_URL")
if database_url:
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    db_user = os.getenv("DB_USER", "root")
    db_password = os.getenv("DB_PASSWORD", "")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "3306")
    db_name = os.getenv("DB_NAME", "students")
    app.config['SQLALCHEMY_DATABASE_URI'] = (
        f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
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
    sem=db.Column(db.Integer())
    branch=db.Column(db.String(50))
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
    rollno=db.Column(db.String(50), nullable=False)
    sname=db.Column(db.String(50), nullable=False)
    sem=db.Column(db.Integer, nullable=False)
    gender=db.Column(db.String(50), nullable=False)
    branch=db.Column(db.String(50), nullable=False)
    email=db.Column(db.String(50), nullable=False)
    number=db.Column(db.String(12), nullable=False)
    address=db.Column(db.String(100), nullable=False)
    __table_args__ = (
        db.UniqueConstraint('rollno', 'sem', 'branch', name='uq_student_roll_sem_branch'),
    )


def get_attendence_columns():
    inspector = inspect(db.engine)
    return {column["name"] for column in inspector.get_columns("attendence")}


def get_attendence_where_clause(rollno, sem=None, branch=None):
    columns = get_attendence_columns()
    clauses = ["rollno = :rollno"]
    params = {"rollno": rollno}
    if "sem" in columns and sem is not None:
        clauses.append("sem = :sem")
        params["sem"] = sem
    if "branch" in columns and branch is not None:
        clauses.append("branch = :branch")
        params["branch"] = branch
    return " AND ".join(clauses), params


def save_attendence_record(rollno, attendance, sem=None, branch=None):
    columns = get_attendence_columns()
    where_clause, where_params = get_attendence_where_clause(rollno, sem=sem, branch=branch)

    existing = db.session.execute(
        text(f"SELECT aid FROM attendence WHERE {where_clause} ORDER BY aid DESC LIMIT 1"),
        where_params,
    ).mappings().first()

    payload = {"attendance": attendance}
    if "sem" in columns and sem is not None:
        payload["sem"] = sem
    if "branch" in columns and branch is not None:
        payload["branch"] = branch

    if existing:
        set_clause = ", ".join(f"{key} = :{key}" for key in payload.keys())
        payload["aid"] = existing["aid"]
        db.session.execute(
            text(f"UPDATE attendence SET {set_clause} WHERE aid = :aid"),
            payload,
        )
        return

    payload["rollno"] = rollno
    column_names = ", ".join(payload.keys())
    value_names = ", ".join(f":{key}" for key in payload.keys())
    db.session.execute(
        text(f"INSERT INTO attendence ({column_names}) VALUES ({value_names})"),
        payload,
    )


def fetch_attendence_record(rollno, sem=None, branch=None):
    where_clause, params = get_attendence_where_clause(rollno, sem=sem, branch=branch)
    row = db.session.execute(
        text(f"SELECT * FROM attendence WHERE {where_clause} ORDER BY aid DESC LIMIT 1"),
        params,
    ).mappings().first()
    if not row:
        return None
    return SimpleNamespace(**row)


@app.route('/')
def index(): 
    student_count = Student.query.count()
    department_count = Department.query.count()
    trigger_count = Trig.query.count()
    attendance_count = db.session.execute(
        text("SELECT COUNT(*) AS count FROM attendence")
    ).scalar() or 0
    return render_template(
        'index.html',
        student_count=student_count,
        department_count=department_count,
        trigger_count=trigger_count,
        attendance_count=attendance_count,
    )


@app.route('/health')
def health():
    try:
        db.session.execute(text("SELECT 1"))
        return {"status": "ok"}, 200
    except Exception:
        return {"status": "error"}, 503

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
        dept=request.form.get('dept')
        if not dept or not dept.strip():
            flash("Please enter department name","danger")
            return redirect('/department')
        query=Department.query.filter_by(branch=dept.strip()).first()
        if query:
            flash("Department already exists","warning")
            return redirect('/department')
        dep=Department(branch=dept.strip())
        db.session.add(dep)
        db.session.commit()
        flash("Department added","success")
    return render_template('department.html')

@app.route('/addattendance',methods=['POST','GET'])
def addattendance():
    query=Student.query.all()
    sem_options=sorted({student.sem for student in query})
    branch_options=sorted({student.branch for student in query})

    if request.method=="POST":
        rollno=request.form.get('rollno')
        sem=request.form.get('sem')
        branch=request.form.get('branch')
        attend=request.form.get('attend')

        if not rollno or not rollno.strip() or rollno == 'Select RollNo':
            flash("Please select the roll number","danger")
            return redirect('/addattendance')
        if not sem or not sem.strip():
            flash("Please select semester","danger")
            return redirect('/addattendance')
        if not branch or branch == 'Select Branch':
            flash("Please select branch","danger")
            return redirect('/addattendance')
        if not attend or not attend.strip():
            flash("Please enter attendance percentage","danger")
            return redirect('/addattendance')

        try:
            sem_val = int(sem)
            if sem_val <= 0:
                raise ValueError
        except ValueError:
            flash("Please enter a valid semester","danger")
            return redirect('/addattendance')

        try:
            attend_val=int(attend)
            if attend_val < 0 or attend_val > 100:
                raise ValueError
        except ValueError:
            flash("Please enter a valid attendance number between 0 and 100","danger")
            return redirect('/addattendance')

        student=Student.query.filter_by(rollno=rollno.strip(), sem=sem_val, branch=branch.strip()).first()
        if not student:
            flash("No student found for the given roll, semester, and branch","warning")
            return redirect('/addattendance')

        save_attendence_record(
            rollno=rollno.strip(),
            sem=sem_val,
            branch=branch.strip(),
            attendance=attend_val,
        )
        db.session.commit()
        flash("Attendance saved","success")

    return render_template('attendance.html', query=query, sem_options=sem_options, branch_options=branch_options)

@app.route('/search',methods=['POST','GET'])
def search():
    dept = Department.query.all()
    bio = None
    attend = None
    if request.method=="POST":
        rollno=request.form.get('roll')
        sem=request.form.get('sem')
        branch=request.form.get('branch')

        if not rollno or not rollno.strip():
            flash("Please enter roll number","danger")
            return render_template('search.html', dept=dept)
        if not sem or not sem.strip():
            flash("Please enter semester","danger")
            return render_template('search.html', dept=dept)
        if not branch or branch == "Select Branch":
            flash("Please select branch","danger")
            return render_template('search.html', dept=dept)

        try:
            sem_val = int(sem)
            if sem_val <= 0:
                raise ValueError
        except ValueError:
            flash("Please enter a valid semester number","danger")
            return render_template('search.html', dept=dept)

        bio=Student.query.filter_by(rollno=rollno.strip(), sem=sem_val, branch=branch.strip()).first()
        if not bio:
            flash("No student found with given roll, semester and branch","warning")
            return render_template('search.html', dept=dept)

        attend=fetch_attendence_record(bio.rollno, sem=bio.sem, branch=bio.branch)

    return render_template('search.html', bio=bio, attend=attend, dept=dept)

@app.route("/delete/<string:id>",methods=['POST','GET'])
@login_required
def delete(id):
    post=Student.query.filter_by(id=id).first()
    if not post:
        flash("Student not found","warning")
        return redirect('/studentdetails')

    where_clause, params = get_attendence_where_clause(
        post.rollno,
        sem=post.sem,
        branch=post.branch,
    )
    db.session.execute(
        text(f"DELETE FROM attendence WHERE {where_clause}"),
        params,
    )
    db.session.delete(post)
    db.session.commit()
    # db.engine.execute(f"DELETE FROM `student` WHERE `student`.`id`={id}")
    flash("Slot Deleted Successfully","danger")
    return redirect('/studentdetails')


@app.route("/edit/<string:id>",methods=['POST','GET'])
@login_required
def edit(id):
    # dept=db.engine.execute("SELECT * FROM `department`")
    dept=Department.query.all()
    post=Student.query.filter_by(id=id).first()
    if not post:
        flash("Student not found","warning")
        return redirect('/studentdetails')

    if request.method=="POST":
        rollno=request.form.get('rollno')
        sname=request.form.get('sname')
        sem=request.form.get('sem')
        gender=request.form.get('gender')
        branch=request.form.get('branch')
        email=request.form.get('email')
        num=request.form.get('num')
        address=request.form.get('address')

        if not rollno or not rollno.strip():
            flash("Please enter roll number", "danger")
            return render_template('edit.html',posts=post,dept=dept)
        if not sname or not sname.strip():
            flash("Please enter student name", "danger")
            return render_template('edit.html',posts=post,dept=dept)
        if not sem or not sem.strip():
            flash("Please enter semester", "danger")
            return render_template('edit.html',posts=post,dept=dept)
        if not gender or gender == "Select Gender":
            flash("Please select gender", "danger")
            return render_template('edit.html',posts=post,dept=dept)
        if not branch or branch == "Select Branch":
            flash("Please select branch", "danger")
            return render_template('edit.html',posts=post,dept=dept)
        if not email or not email.strip():
            flash("Please enter email", "danger")
            return render_template('edit.html',posts=post,dept=dept)
        if not num or not num.strip():
            flash("Please enter mobile number", "danger")
            return render_template('edit.html',posts=post,dept=dept)
        if not address or not address.strip():
            flash("Please enter address", "danger")
            return render_template('edit.html',posts=post,dept=dept)

        try:
            sem_val = int(sem)
            if sem_val <= 0:
                raise ValueError
        except ValueError:
            flash("Please enter a valid semester", "danger")
            return render_template('edit.html',posts=post,dept=dept)

        rollno_val = rollno.strip()
        sname_val = sname.strip()
        gender_val = gender.strip()
        branch_val = branch.strip()
        email_val = email.strip()
        num_val = num.strip()
        address_val = address.strip()

        if len(rollno_val) > 20:
            flash("Roll number must be 20 characters or fewer", "danger")
            return render_template('edit.html',posts=post,dept=dept)

        existing = Student.query.filter_by(
            rollno=rollno_val,
            sem=sem_val,
            branch=branch_val,
        ).first()
        if existing and existing.id != post.id:
            flash("Student already exists in this semester and department with same roll number", "warning")
            return render_template('edit.html',posts=post,dept=dept)

        old_rollno = post.rollno
        old_sem = post.sem
        old_branch = post.branch

        post.rollno=rollno_val
        post.sname=sname_val
        post.sem=sem_val
        post.gender=gender_val
        post.branch=branch_val
        post.email=email_val
        post.number=num_val
        post.address=address_val

        if (
            old_rollno != rollno_val
            or old_sem != sem_val
            or old_branch != branch_val
        ):
            columns = get_attendence_columns()
            where_clause, where_params = get_attendence_where_clause(
                old_rollno,
                sem=old_sem,
                branch=old_branch,
            )
            updates = {"new_rollno": rollno_val}
            if "sem" in columns:
                updates["new_sem"] = sem_val
            if "branch" in columns:
                updates["new_branch"] = branch_val
            assignments = ["rollno = :new_rollno"]
            if "sem" in columns:
                assignments.append("sem = :new_sem")
            if "branch" in columns:
                assignments.append("branch = :new_branch")
            set_clause = ", ".join(assignments)
            updates.update(where_params)
            db.session.execute(
                text(f"UPDATE attendence SET {set_clause} WHERE {where_clause}"),
                updates,
            )

        db.session.commit()
        flash("detail has been updated successfully","success")
        return redirect('/studentdetails')
    return render_template('edit.html',posts=post,dept=dept)


@app.route('/signup',methods=['POST','GET'])
def signup():
    if request.method == "POST":
        username=request.form.get('username')
        email=request.form.get('email')
        password=request.form.get('password')
        if not username or not username.strip():
            flash("Please enter username","danger")
            return render_template('signup.html')
        if not email or not email.strip():
            flash("Please enter email","danger")
            return render_template('signup.html')
        if not password:
            flash("Please enter password","danger")
            return render_template('signup.html')
        user=User.query.filter_by(email=email.strip()).first()
        if user:
            flash("Email already exists","warning")
            return render_template('signup.html')

        newuser=User(username=username.strip(),email=email.strip(),password=password)
        db.session.add(newuser)
        db.session.commit()
        flash("Signup success. Please login","success")
        return render_template('login.html')

          

    return render_template('signup.html')

@app.route('/login',methods=['POST','GET'])
def login():
    if request.method == "POST":
        email=request.form.get('email')
        password=request.form.get('password')
        if not email or not email.strip():
            flash("Please enter email","danger")
            return render_template('login.html')
        if not password:
            flash("Please enter password","danger")
            return render_template('login.html')
        user=User.query.filter_by(email=email.strip()).first()

        if user and user.password == password:
            login_user(user)
            flash("Login Success","primary")
            return redirect(url_for('index'))
        else:
            flash("Invalid credentials","danger")
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
    dept=Department.query.all()
    if request.method=="POST":
        rollno=request.form.get('rollno')
        sname=request.form.get('sname')
        sem=request.form.get('sem')
        gender=request.form.get('gender')
        branch=request.form.get('branch')
        email=request.form.get('email')
        num=request.form.get('num')
        address=request.form.get('address')

        if not rollno or not rollno.strip():
            flash("Please enter roll number", "danger")
            return render_template('student.html',dept=dept)
        if not sname or not sname.strip():
            flash("Please enter student name", "danger")
            return render_template('student.html',dept=dept)
        if not sem or not sem.strip():
            flash("Please enter semester", "danger")
            return render_template('student.html',dept=dept)
        if not gender or gender == "Select Gender":
            flash("Please select gender", "danger")
            return render_template('student.html',dept=dept)
        if not branch or branch == "Select Branch":
            flash("Please select branch", "danger")
            return render_template('student.html',dept=dept)
        if not email or not email.strip():
            flash("Please enter email", "danger")
            return render_template('student.html',dept=dept)
        if not num or not num.strip():
            flash("Please enter mobile number", "danger")
            return render_template('student.html',dept=dept)
        if not address or not address.strip():
            flash("Please enter address", "danger")
            return render_template('student.html',dept=dept)

        existing = Student.query.filter_by(rollno=rollno.strip(), sem=sem.strip(), branch=branch.strip()).first()
        if existing:
            flash("Student already exists in this semester and department with same roll number", "warning")
            return render_template('student.html',dept=dept)

        student=Student(rollno=rollno.strip(),sname=sname.strip(),sem=int(sem),gender=gender.strip(),branch=branch.strip(),email=email.strip(),number=num.strip(),address=address.strip())
        db.session.add(student)
        db.session.commit()

        flash("Booking Confirmed","success")

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
  
