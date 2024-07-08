from flask import Flask, render_template, request, redirect, session
from flask_mysqldb import MySQL
import MySQLdb.cursors
import os
import pandas as pd
from textblob import TextBlob  # TextBlob for sentiment analysis
from datetime import datetime
from dotenv import load_dotenv
from waitress import serve 

load_dotenv()

app = Flask(__name__, static_url_path='/static')
app.secret_key = os.urandom(24)

df = pd.read_csv('dataset_cities.csv', encoding='latin1')

# MySQL configurations
app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB')

mysql = MySQL(app)

# Function to add user to the database
def add_user_to_database(name, email, password, user_type):
    cursor = mysql.connection.cursor()
    cursor.execute("INSERT INTO users (name, email, password, user_type) VALUES (%s, %s, %s, %s)", (name, email, password, user_type))
    mysql.connection.commit()
    cursor.close()

# Route for handling the form submission
@app.route('/signup', methods=['POST'])
def process_signup_form():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        user_type = request.form['type']

        if password != confirm_password:
            return 'Passwords do not match'

        add_user_to_database(name, email, password, user_type)

        return redirect('/login')  

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/signup')
def signup():
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html', error=None)  # Pass None as the error initially
    
    elif request.method == 'POST':
        if 'email' in request.form and 'password' in request.form:
            username = request.form['email']
            password = request.form['password']

            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            try:
                cursor.execute('SELECT * FROM users WHERE email = %s AND password = %s', (username, password,))
                user = cursor.fetchone()

                if user:
                    session['user_id'] = user['id']  # Store user ID in session
                    session['logged_in'] = True
                    print("User ID:", user['id'])
                    return redirect('/') 
                else:
                    return render_template('login.html', error='Invalid username/password')
            except Exception as e:
                return render_template('login.html', error='An error occurred: {}'.format(str(e)))
            finally:
                cursor.close()
        else:
            return render_template('login.html', error='Missing email or password in form data')

@app.route('/logout')
def logout():
    # Clear the session when the user logs out
    session.clear()
    return redirect('/')

# Sentiment analysis function using TextBlob
def analyze_sentiment(popularity):
    blob = TextBlob(popularity)
    sentiment_score = blob.sentiment.polarity
    return sentiment_score

def preprocess_place_name(place_name):
    return place_name.split(',')[0].strip()

def recommend_locations_with_review(place_name, start_date, end_date, type_, budget, df):

    # Preprocess the place_name
    place_name = preprocess_place_name(place_name)

    # Calculate duration in days
    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    end_date = datetime.strptime(end_date, "%Y-%m-%d")
    duration = (end_date - start_date).days
    
    # Filter DataFrame based on user input
    filtered_df = df[(df['Place Name'] == place_name) & (df['Type'] == type_)]
    
    # Extract unique tourist locations, their reviews, and costs
    unique_locations = filtered_df['Tourist Location'].tolist()
    locations_reviews = filtered_df.set_index('Tourist Location')['Review'].to_dict()
    locations_popularity = filtered_df.set_index('Tourist Location')['Popularity'].to_dict()
    locations_budget = filtered_df.set_index('Tourist Location')['Budget'].to_dict()
    locations_type = filtered_df.set_index('Tourist Location')['Type'].to_dict()
    locations_state = filtered_df.set_index('Tourist Location')['State'].to_dict()
    
    # Generate recommendation with review scores for each day
    remaining_budget = budget
    recommendations = []
    no_more_locations_added = False
    no_more_budget_added = False
    day_counter = 1 

    location_added = False 

    for i in range(duration):
        if remaining_budget <= 0 and not no_more_budget_added:
            recommendations.append({"day": day_counter, "location": "No more budget for additional locations", "popularity": 0, "review": "", "sentiment_score": 0})
            no_more_budget_added = True
        
        if unique_locations:
            location_added = False
            for location in unique_locations:
                if remaining_budget >= locations_budget[location]:
                    review = locations_reviews.get(location, '')
                    sentiment_score = analyze_sentiment(locations_popularity[location]) 
                    popularity = locations_popularity.get(location, '')
                    trip_type = locations_type[location]
                    state = locations_state.get(location, 'N/A')
                    recommendation = {"day": day_counter, "state": state, "location": f"{location}", "type": f"{trip_type}", "popularity": popularity, "review": review, "sentiment_score": sentiment_score, "budget": locations_budget[location]}
                    recommendations.append(recommendation)
                    remaining_budget -= locations_budget[location]
                    unique_locations.remove(location)
                    location_added = True
                    break
            if not location_added:
                if not no_more_budget_added:
                    recommendations.append({"day": day_counter, "location": "No more locations available", "popularity": 0, "review": "", "sentiment_score": 0})
                    no_more_locations_added = True
                    break
        else:
            if not no_more_locations_added:
                recommendations.append({"day": day_counter, "location": "No more locations available", "popularity": 0, "review": "", "sentiment_score": 0})
                no_more_locations_added = True

        if location_added:
            day_counter += 1
    
    recommendations.sort(key=lambda x: x.get("sentiment_score", 0), reverse=True)

    day_counter = 1

    for recommendation in recommendations:
        recommendation["day"] = day_counter
        day_counter += 1

    return recommendations, budget - remaining_budget

# Function to save trip details for a specific user to the database
def save_trip_details(user_id, place_name, start_date, end_date, trip_type, budget):
    cursor = mysql.connection.cursor()
    cursor.execute("INSERT INTO trips (user_id, place_name, start_date, end_date, trip_type, budget) VALUES (%s, %s, %s, %s, %s, %s)", (user_id, place_name, start_date, end_date, trip_type, budget))
    mysql.connection.commit()
    cursor.close()

@app.route('/result', methods=['GET', 'POST'])
def result():
    if request.method == 'POST':

        place_name = request.form['place_name']
        start_date = request.form['startDate']
        end_date = request.form['endDate']
        trip_type = request.form['tripType']
        budget_str = request.form['budget']

        # Check if budget is a valid numerical value
        try:
            budget = float(budget_str)
            if budget < 1000:
                return 'Budget should be at least ₹1000'
        except ValueError:
            return 'Budget should be a numerical value'
        
        # Get user ID from session
        user_id = session.get('user_id')
        
        # Check if user is logged in
        if user_id:

            save_trip_details(user_id, place_name, start_date, end_date, trip_type, budget)
            
            recommendations, remaining_budget = recommend_locations_with_review(place_name, start_date, end_date, trip_type, budget, df)
            
            return render_template('recommendations.html', sorted_recommendations=recommendations, remaining_budget=remaining_budget)
        else:
            return redirect('/login')

if __name__ == '__main__':
    # Use Waitress to serve the Flask app
    serve(app, host='0.0.0.0', port=5000)
