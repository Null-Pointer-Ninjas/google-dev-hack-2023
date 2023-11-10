#============
# main.py
# This is the entry point of our backend server
#============
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import Annotated, Union
import asyncio
import os
import shutil
import time
from fastapi import FastAPI, Depends, Form, UploadFile, Cookie, WebSocket, BackgroundTasks, HTTPException, WebSocketException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from scene.base import Interview, Assessment
from user.base import *
from utils.resume_io import *

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_result(self, message: str, websocket: WebSocket):
        await websocket.send_json(message)

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Union[str, None] = None

SECRET_KEY = "REDACTED"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 3000

app = FastAPI(docs_url=None, redoc_url=None)   

app.mount("/static", StaticFiles(directory="static"), name="static")
manager = ConnectionManager()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return False
        token_data = TokenData(username=username)
    except JWTError:
        return False
    user = get_user(username=token_data.username)
    if user is None:
        return False
    return user

async def aget_ws_current_user(
    websocket: WebSocket,
    access_token: Annotated[Union[str, None], Cookie()] = None,
):
    print(access_token)
    if access_token is None:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
    user = get_current_user(access_token)
    if user == False:
        raise WebSocketException(code=1101, reason="Authentication Failed")
    return user

async def aget_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    user = get_current_user(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

@app.get("/")
async def index():
    file_path = f"./static/index.html"
    return FileResponse(file_path)

@app.get("/{path:path}")
async def send_Dirs(path: str):
    file_path = f"./static/{path}"
    if os.path.isfile(file_path):
        file_res = FileResponse(file_path)
    else:
        file_path = f"./static/pages-error-404.html"
        file_res = FileResponse(file_path)
    return file_res

#Hardcore for this round
@app.post("/applicants")
async def index(user: Annotated[UserInDB, Depends(aget_current_user)]):
    data = [
    {
        "fullName": "Alice",
        "emailAddress": "alice@example.com",
        "assessmentScore": 40
    },
    {
        "fullName": "Adam Joseph",
        "emailAddress": "adam.doe@example.com",
        "assessmentScore": 60
    },
    {
        "fullName": "Richeal Tan",
        "emailAddress": "adam.doe@example.com",
        "assessmentScore": 60
    },
    {
        "fullName": "Ng Jing Jing",
        "emailAddress": "adam.doe@example.com",
        "assessmentScore": 60
    },
    {
        "fullName": "Thomas Low",
        "emailAddress": "john.doe@example.com",
        "assessmentScore": 20
    },
    {
        "fullName": "Matthiew Elliot",
        "emailAddress": "john.doe@example.com",
        "assessmentScore": 44
    },
    {
        "fullName": "Thiagarajan a/l Kumaran",
        "emailAddress": "kumaran@example.com",
        "assessmentScore": 60
    },
    {
        "fullName": "Jane Smith",
        "emailAddress": "john.doe@example.com",
        "assessmentScore": 40
    },
    {
        "fullName": "Khoo Zi Yi",
        "emailAddress": "ziyi@example.com",
        "assessmentScore": 65
    },
    {
        "fullName": "Teoh Zhen Quan",
        "emailAddress": "john.doe@example.com",
        "assessmentScore": 70
    },
]
    for i in range(90):
        data.append(
    {
        "fullName": "Joseph",
        "emailAddress": "failed@example.com",
        "assessmentScore": 10
    })
    return data
@app.post("/uploads")
async def screen_resume(user: Annotated[UserInDB, Depends(aget_current_user)],
                        file: Union[UploadFile, None] = None, ):
    
    if not file:
        print(11123)
        return {"message": "No upload file sent"}
    try:
        upload_dir = f"files/{user.username}/"  # Change this to your desired directory

        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
        file_path = os.path.join(upload_dir, file.filename)

        with open(file_path, "wb") as file_object:
            shutil.copyfileobj(file.file, file_object)
        resumeReader = ResumeReader(username=user.username, filepath=upload_dir, filename=file.filename)
       
        infos = await resumeReader.extract_info(["name", "contact no", "gender", "email", "linkedin URL", "area of study", "education", "latest CGPA", "experiences", "projects"])
        return {"message": {
            "fullName": infos[0],
            "contactNo": infos[1],
            "gender": infos[2],
            "email": infos[3],
            "linkedinUrl": infos[4],
            "areaOfStudy" : infos[5],
            "university": infos[6],
            "latestCGPA": infos[7],
            "workingExperience": infos[8],
            "projects": infos[9]
        }}
    except Exception as e:
        print(e)
        return {"message": "Error"}

@app.post("/app-form-submission")
async def submit_form(user: Annotated[UserInDB, Depends(aget_current_user)],
    name: str = Form(...),
    email: str = Form(...),
    gender: str = Form(...),
    phone: str = Form(...),
    address: str = Form(...),
    working_mode: str = Form(...),
    extra_document: Union[UploadFile, None] = None,):
    
    if not extra_document:
        print(0)
    print(name)
    return {"message": "ok"}

@app.post("/criteria-gen")
async def submit_form(
    job_title: str = Form(...),
    job_desc: str = Form(...),
    job_req: str = Form(...),):
    x = genCriteria(job_title, job_desc, job_req).split(';')
    
    return {"message": x}

@app.post("/guestlogin")
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    u_id= create_user()
    user = authenticate_user(u_id, "secret")
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/login")
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.websocket("/interview")
async def interview_websocket(websocket: WebSocket, 
                        user: Annotated[UserInDB, Depends(aget_ws_current_user)],
                        q: Union[int, None] = None):
    try:
        await manager.connect(websocket)
        print("[main] connected")
        candidate_interview = Interview(user.username)
        asyncio.create_task(candidate_interview.start_session(audio=False))
        while True:
            while True:
                print("[main] Waiting AI response..")
                response = await candidate_interview.response_queue.get()
                if response is None:
                    print("[main] This loop ended")
                    break
                elif type(response) == str and response == "ENDED":
                    print("[main] Received response from RNAI.")
                    await manager.send_result({"message": "Thank you", "ended":True}, websocket)
                elif type(response) == dict:
                    print("[main] Received response from RNAI.")
                    await manager.send_result(response, websocket)
            print("[main] waiting client response..")
            interviewee_input_text = await websocket.receive_text()
            await candidate_interview.send_interviewee_input(text=interviewee_input_text)
            print("[main] sent")
    
    except Exception as e:
        print("Error: ", e)
            
            
@app.websocket("/assessment")
async def assessment_websocket(websocket: WebSocket, 
                        user: Annotated[UserInDB, Depends(aget_ws_current_user)],
                        q: Union[int, None] = None):
    try:
        await manager.connect(websocket)
        print("[main] connected")
        recruiter_assessment = Assessment(user.username)
        asyncio.create_task(recruiter_assessment.start_session(q))
        while True:
            while True:
                print("[main] Waiting RNAI response..")
                response = await recruiter_assessment.response_queue.get()
                if response is None:
                    print("[main] This loop ended")
                    break
                else:
                    print("[main] Received response from RNAI.")
                    await manager.send_result(response, websocket)
            print("[main] waiting client response..")
            interviewee_input_text = await websocket.receive_text()
            await recruiter_assessment.send_interviewee_input(text=interviewee_input_text)
            print("[main] sent")
        # post evaluation
    except Exception as e:
        print("Error: ", e)
            