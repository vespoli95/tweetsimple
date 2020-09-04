import requests 
import datetime
import keys
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, logging
from passlib.hash import sha256_crypt
from flask_sqlalchemy import SQLAlchemy
app = Flask(__name__, template_folder='templates')

ENV = 'dev'

if ENV == 'prod':
    app.debug = False
    app.config['SQLALCHEMY_DATABASE_URI'] = keys.DB_STRING_PROD
else:
    app.debug = True
    app.config['SQLALCHEMY_DATABASE_URI'] = keys.DB_STRING_DEV

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

HEADERS = {"Authorization":"Bearer {}".format(keys.BEARER_TOKEN)}

class Users(db.Model):
    __tablename__ = 'users'
    PK_user_id = db.Column(db.String(200), primary_key=True)
    password = db.Column(db.String(200))
    
    def __init__(self, PK_user_id, password):
        self.PK_user_id = PK_user_id
        self.password = password

class Categories(db.Model):
    __tablename__ = 'categories'
    PK_category_id = db.Column(db.Integer, primary_key=True)
    FK_Users_user_id = db.Column(db.String(200), db.ForeignKey(Users.PK_user_id))
    name = db.Column(db.String(200))
    date_created = db.Column(db.DateTime, nullable=False)

    def __init__(self, PK_category_id, FK_Users_user_id, name, date_created):
        self.PK_category_id = PK_category_id
        self.FK_Users_user_id = FK_Users_user_id
        self.name = name
        self.date_created = date_created
    
class Timelines(db.Model):
    __tablename__ = 'timelines'
    PK_timeline_id = db.Column(db.Integer, primary_key=True)
    FK_Categories_category_id = db.Column(db.Integer, db.ForeignKey(Categories.PK_category_id))
    category_name = db.Column(db.String(200), nullable=False)
    handle = db.Column(db.String(200), nullable=False)
    date_created = db.Column(db.DateTime, nullable=False)

    def __init__(self, PK_timeline_id, FK_Categories_category_id, category_name, handle, date_created):
        self.PK_timeline_id = PK_timeline_id
        self.FK_Categories_category_id = FK_Categories_category_id
        self.category_name = category_name
        self.handle = handle
        self.date_created = date_created


@app.route('/')
@app.route('/index')
def index():
    if session.get('user') is None:
        return render_template('index.html', categories=[])
    db_categories = Categories.query.filter_by(FK_Users_user_id=session['user']).all()
    return render_template('index.html', categories=db_categories)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if session:
        session.clear()
    if request.method == 'POST':
        user_id = request.form['user_id']
        password = sha256_crypt.hash((str(request.form['password'])))
        if db.session.query(Users).filter(Users.PK_user_id == user_id).count() == 0:
            data = Users(user_id, password)
            db.session.add(data)
            db.session.commit()
            return redirect(url_for('login'))
        return render_template('register.html', error="Username already exists!")
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_id = request.form['user_id']
        password_candidate = request.form['password']
        
        db_record = Users.query.filter_by(PK_user_id=user_id).first()
        
        record_password = db_record.password
        print('rec pass: ', record_password)
        if sha256_crypt.verify(password_candidate, record_password):
            session['logged_in'] = True
            session['user'] = user_id
            return redirect(url_for('index'))
        error = "Incorrect password"
        return render_template('login.html', error=error)
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


@app.route('/categories/<string:category>', methods=['GET','POST'])
def categories(category):
    session['category'] = category
    db_categories = Categories.query.filter_by(FK_Users_user_id=session['user'], name=category).all()
    category_id = db_categories[0].PK_category_id
    db_timelines = Timelines.query.filter_by(FK_Categories_category_id=category_id).all()
    if not db_timelines:
        return render_template('categories.html', _category=category)
    timelines = {}
    for timeline in db_timelines:
        handle = timeline.handle
        url = "https://api.twitter.com/2/users/by/username/{}".format(handle)
        resp = requests.get(url, headers=HEADERS)
        id = resp.json()['data']['id']
        url_tweets = "https://api.twitter.com/1.1/statuses/user_timeline.json?screen_name={}&count=5".format(handle)
        resp_tweets = requests.get(url_tweets, headers=HEADERS)
        
        if resp_tweets.status_code == 200:
            tweets = resp_tweets.json()
            _tweets = []
            for tweet in tweets:
                url_tweet = "https://api.twitter.com/2/tweets/{}?expansions=author_id,attachments.media_keys&media.fields=url&tweet.fields=created_at,attachments".format(tweet['id'])
                resp_tweet = requests.get(url_tweet, headers=HEADERS)
                resp_tweet = resp_tweet.json()
                _tweets.append(resp_tweet)
        timelines[handle] = _tweets
    print(timelines)
    return render_template('categories.html', timelines=timelines)


@app.route('/new_timeline', methods=['POST'])
def new_timeline():
    if request.method == 'POST':
        handle = request.form['handle']
        category = request.form['category']
        user_id = session['user']
        db_categories = Categories.query.filter_by(FK_Users_user_id=session['user'], name=category).all()
        category_id = db_categories[0].PK_category_id
        db_timelines = Timelines.query.filter_by(FK_Categories_category_id=category_id, handle=handle).all()
        if not db_timelines:
            print('adding new timeline...')
            # add new timeline
            data = Timelines(None, category_id, category, handle, datetime.datetime.now())
            db.session.add(data)
            db.session.commit()
        return redirect('/categories/{}'.format(category))
       

     

@app.route('/new_category', methods=['POST'])
def new_category():
    if request.method == 'POST':
        category = request.form['category']
        user_id = session['user']
        if category != '':
            db_categories = Categories.query.filter_by(FK_Users_user_id=session['user']).all()
            for c in db_categories:
                if category == c.name:
                    return render_template('index.html', error="Category already exists!")
            data = Categories(None, user_id, category, datetime.datetime.now())
            db.session.add(data)
            db.session.commit()
            db_categories = Categories.query.filter_by(FK_Users_user_id=session['user']).all()
            return redirect(url_for('index'))

            

# @app.route('/new_timeline', methods=['POST'])
# def new_timeline():
#     if request.method == 'POST':
#         handle = request.form['handle']
#         if handle == '':
#             return render_template('index.html', message='Please enter required fields')
#         # if db.session.query(Feedback).filter(Feedback.customer == customer).count() == 0:
#         #     data = Feedback(customer, dealer, rating, comments)
#         #     db.session.add(data)
#         #     db.session.commit()
#         #     send_mail(customer, dealer, rating, comments)
#         #     return render_template('success.html')
#         else:
#             url = "https://api.twitter.com/2/users/by/username/{}".format(handle)
#             resp = requests.get(url, headers=HEADERS)
#             id = resp.json()['data']['id']
#             #url_tweets = "https://api.twitter.com/1.1/statuses/user_timeline.json?screen_name={}".format(handle)
#             url_tweets = "https://api.twitter.com/1.1/statuses/user_timeline.json?screen_name={}&count=5".format(handle)
#             resp_tweets = requests.get(url_tweets, headers=HEADERS)
#             if len(resp_tweets) != 0:
#                 tweets = resp_tweets.json()
#                 _tweets = []
#                 for tweet in tweets:
#                     url_tweet = "https://api.twitter.com/2/tweets/{}?expansions=author_id,attachments.media_keys&media.fields=url&tweet.fields=created_at,attachments".format(tweet['id'])
#                     resp_tweet = requests.get(url_tweet, headers=HEADERS)
#                     resp_tweet = resp_tweet.json()
#                     print(resp_tweet)
#                     _tweets.append(resp_tweet)
#                 return render_template('index.html', tweets=_tweets)
#             else:
#                 return render_template('index.html', error="Invalid twitter handle!")


# Check if user logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            return redirect(url_for('login'))
    return wrap

if __name__ == '__main__':
    app.secret_key = keys.SECRET_KEY
    app.run()
