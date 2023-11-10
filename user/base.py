from pydantic import BaseModel
from typing import Union
from passlib.context import CryptContext
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
from firebase_admin import firestore
import time
import random
default_app = firebase_admin.initialize_app()

db = firestore.client()
users_ref = db.collection("users")

class User(BaseModel):
    username: str
    email: Union[str, None] = None
    full_name: Union[str, None] = None
    disabled: Union[bool, None] = None
    
class UserInDB(User):
    hashed_password: str
    hard_skills: Union[list[str], None] = None
    soft_skills: Union[list[str], None] = None

def get_user(username: str):
    docs = users_ref.stream()
    for doc in docs:
        print(f"{doc.id} => {doc.to_dict()}")
        if (doc.id == username):
            user_dict = doc.to_dict()
            print("get user")
            return UserInDB(**user_dict)


def create_user():
    u_id = "guest"+ str(time.time()).replace('.','') + str(random.randrange(1000,9999))
    doc_ref = users_ref.document(u_id)
    doc_ref.set({"disabled": False, 
             "email": "guest@example.com", 
             "full_name": "Guest", 
             "hashed_password": "NA", 
             "username": u_id})
    return u_id


def authenticate_user(username: str, password: str):
    user = get_user(username)
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    if not user or not pwd_context.verify(password, user.hashed_password):
        return False
    return user