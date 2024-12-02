from pymongo import MongoClient
from werkzeug.security import generate_password_hash

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["attendance_system"]

# Insert sample users into the `users` collection
users_collection = db["users"]

users_collection.insert_one({
    "name": "ashlesh",
    "email": "ashlesh@example.com",
    "password": generate_password_hash("123"),
    "role": "teacher"
})

print("Sample user inserted!")
