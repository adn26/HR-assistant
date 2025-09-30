from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import os
from datetime import datetime

# user-defined modules
from resume_parser import parse_resume
from candidate_ranker import rank_candidates
from scheduler import schedule_interviews
from email_service import send_confirmation_emails

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# in-memory storage(gotta use db in prod)
candidates_store = []
job_description_store = ""

# request models
class JobDescriptionRequest(BaseModel):
    job_description: str

class SelectCandidatesRequest(BaseModel):
    candidate_indices: List[int]
    interview_date: str  # format: "2025-10-01"
    interview_duration: int = 60  # minutes

# response models
class CandidateResponse(BaseModel):
    id: int
    name: str
    email: str
    phone: str
    skills: List[str]
    experience_years: str
    score: float
    summary: str
    match_percentage: float

# store job description for candidate matching
@app.post("/job_description/")
async def post_job_description(request: JobDescriptionRequest):
    global job_description_store
    job_description_store = request.job_description
    return {"message": "Job description saved successfully", "jd": job_description_store}

# retrieve current job description
@app.get("/job_description/")
async def get_job_description():
    return {"job_description": job_description_store}

    
# batch upload resumes, parse them, and store candidate information 
@app.post("/upload_resumes/")
async def upload_resumes(files: List[UploadFile] = File(...)):
    global candidates_store
    
    if not job_description_store:
        raise HTTPException(status_code=400, detail="Please post a job description first")
    
    parsed_candidates = []
    
    for idx, file in enumerate(files):
        if not file.filename.endswith('.pdf'):
            continue
            
        # save temporarily
        file_location = f"temp_{idx}_{file.filename}"
        try:
            with open(file_location, "wb") as f:
                f.write(await file.read())
            
            # parse resume
            candidate_info = await parse_resume(file_location, job_description_store)
            
            # clean up temp file
            os.remove(file_location)
            
            if "error" not in candidate_info:
                parsed_candidates.append(candidate_info)
                
        except Exception as e:
            print(f"Error processing {file.filename}: {e}")
            if os.path.exists(file_location):
                os.remove(file_location)
            continue
    
    if not parsed_candidates:
        raise HTTPException(status_code=400, detail="No valid resumes processed")
    
    # rank candidates against job description
    ranked_candidates = await rank_candidates(parsed_candidates, job_description_store)
    
    # store candidates with IDs
    candidates_store = []
    for idx, candidate in enumerate(ranked_candidates):
        candidate['id'] = idx
        candidates_store.append(candidate)
    
    return {
        "message": f"Successfully processed {len(ranked_candidates)} resumes",
        "candidates": candidates_store
    }

# retrieve all ranked candidates
@app.get("/candidates/")
async def get_candidates():
    return {"candidates": candidates_store}

@app.post("/select_candidates/")
async def select_candidates(request: SelectCandidatesRequest):
    """
    Autonomous agent workflow:
    1. Select top candidates
    2. Schedule interviews on Google Calendar
    3. Send confirmation emails
    """
    if not candidates_store:
        raise HTTPException(status_code=400, detail="No candidates available")
    
    # validate indices
    selected = []
    for idx in request.candidate_indices:
        if idx >= len(candidates_store):
            raise HTTPException(status_code=400, detail=f"Invalid candidate index: {idx}")
        selected.append(candidates_store[idx])
    
    if not selected:
        raise HTTPException(status_code=400, detail="No candidates selected")
    
    # parse interview date
    try:
        interview_date = datetime.fromisoformat(request.interview_date)
    except:
        raise HTTPException(status_code=400, detail="Invalid date format. Use ISO format: YYYY-MM-DD")
    
    # AGENT WORKFLOW BEGINS
    
    # schedule interviews on Google Calendar
    try:
        scheduled_interviews = await schedule_interviews(
            candidates=selected,
            start_date=interview_date,
            duration_minutes=request.interview_duration
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scheduling failed: {str(e)}")
    
    # send confirmation emails
    try:
        email_results = await send_confirmation_emails(
            scheduled_interviews=scheduled_interviews,
            job_description=job_description_store
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email sending failed: {str(e)}")
    
    return {
        "message": f"Successfully scheduled {len(scheduled_interviews)} interviews",
        "scheduled_interviews": scheduled_interviews,
        "email_status": email_results
    }


@app.get("/health/")
async def health_check():
    return {"status": "healthy", "candidates_count": len(candidates_store)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)