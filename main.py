import time, uuid, bcrypt, logging, uvicorn
from typing import Optional, List
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

# --- SETUP ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RehobothCore")

# Database Connection (Supabase)
DATABASE_URL = "postgresql://postgres.kiavrhphfxinpuaudafe:MugenyiTitus2026@aws-0-eu-west-1.pooler.supabase.com:6543/postgres?sslmode=require"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

app = FastAPI(title="Rehoboth Health | Core Node")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# --- MODELS ---
class AuthRequest(BaseModel):
    username: str
    email: Optional[str] = None
    pin: str

class PatientProfile(BaseModel):
    username: str
    full_name: str
    dob: str
    age: int
    gender: str
    location: str
    phone: str
    emergency_contact: str
    next_of_kin_name: str
    next_of_kin_phone: str
    past_illnesses: str
    previous_surgeries: str
    chronic_conditions: str
    known_allergies: str
    blood_pressure: str
    hypertension_status: str
    smoking_status: str
    exercise_frequency: str

class ClinicalEntry(BaseModel):
    username: str
    note_type: str
    content: str
    doctor_name: str
    doctor_phone: str
    doctor_email: str
    hospital_name: str
    hospital_phone: str
    hospital_email: str

# --- INITIALIZATION ---
def initialize_db():
    with engine.connect() as conn:
        conn.execute(text('''CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY, hashed_pin TEXT, patient_id TEXT UNIQUE,
            email TEXT, full_name TEXT, dob TEXT, age INTEGER, gender TEXT, 
            location TEXT, phone TEXT, emergency_contact TEXT, next_of_kin_name TEXT, 
            next_of_kin_phone TEXT, past_illnesses TEXT, previous_surgeries TEXT, 
            chronic_conditions TEXT, known_allergies TEXT, blood_pressure TEXT, 
            hypertension_status TEXT, smoking_status TEXT, exercise_frequency TEXT)'''))
        
        conn.execute(text('''CREATE TABLE IF NOT EXISTS clinical_logs (
            log_id SERIAL PRIMARY KEY, username TEXT, note_type TEXT, content TEXT, 
            doctor_name TEXT, doctor_phone TEXT, doctor_email TEXT, hospital_name TEXT, 
            hospital_phone TEXT, hospital_email TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)'''))
        conn.commit()
        logger.info("Core Node: Database and Tables verified.")

initialize_db()

# --- ENDPOINTS ---
@app.post("/register")
async def register(request: AuthRequest, db: Session = Depends(get_db)):
    p_id = str(uuid.uuid4())
    hashed = bcrypt.hashpw(request.pin.encode()[:72], bcrypt.gensalt()).decode()
    db.execute(text("INSERT INTO users (username, hashed_pin, patient_id, email) VALUES (:u, :h, :id, :e)"),
               {"u": request.username.lower(), "h": hashed, "id": p_id, "e": request.email})
    db.commit()
    return {"status": "success", "patient_id": p_id}

@app.post("/sync_profile")
async def sync_profile(p: PatientProfile, db: Session = Depends(get_db)):
    db.execute(text("""UPDATE users SET full_name=:fn, dob=:dob, age=:age, gender=:gender, location=:loc, 
    phone=:ph, emergency_contact=:ec, next_of_kin_name=:nokn, next_of_kin_phone=:nokp, past_illnesses=:pi, 
    previous_surgeries=:ps, chronic_conditions=:cc, known_allergies=:ka, blood_pressure=:bp, 
    hypertension_status=:hs, smoking_status=:ss, exercise_frequency=:ef WHERE username=:u"""), p.dict())
    db.commit()
    return {"status": "success"}

@app.post("/add_clinical_entry")
async def add_clinical_entry(e: ClinicalEntry, db: Session = Depends(get_db)):
    db.execute(text("""INSERT INTO clinical_logs (username, note_type, content, doctor_name, doctor_phone, 
    doctor_email, hospital_name, hospital_phone, hospital_email) VALUES (:u, :nt, :c, :dn, :dp, :de, :hn, :hp, :he)"""), e.dict())
    db.commit()
    return {"status": "success"}

@app.get("/patient/full_record/{username}")
async def get_full_patient_record(username: str, db: Session = Depends(get_db)):
    user = db.execute(text("SELECT * FROM users WHERE username = :u"), {"u": username.lower()}).fetchone()
    if not user:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    logs = db.execute(text("SELECT * FROM clinical_logs WHERE username = :u ORDER BY created_at DESC"), 
                      {"u": username.lower()}).fetchall()
    
    return {
        "profile": dict(zip(user.keys(), user)),
        "clinical_history": [dict(zip(log.keys(), log)) for log in logs]
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)