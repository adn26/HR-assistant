import os
import json
import asyncio
from dotenv import load_dotenv
from google import genai
from typing import List, Dict

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

def get_client():
    api_key = os.getenv("AI_API_KEY")
    if not api_key:
        raise ValueError("AI_API_KEY not set in environment")
    return genai.Client(api_key=api_key)

# evaluate the candidate using AI from the provided candidate info and job desc.
async def evaluate_candidate(candidate: Dict, job_description: str) -> Dict:
    client = get_client()
    
    candidate_summary = f"""
Name: {candidate.get('name', 'Unknown')}
Skills: {', '.join(candidate.get('skills', []))}
Experience: {candidate.get('experience_years', 'Unknown')} years
Education: {candidate.get('education', 'Not specified')}
Relevant Experience: {candidate.get('relevant_experience', 'Not specified')}
Key Achievements: {', '.join(candidate.get('key_achievements', []))}
"""
    
    prompt = f"""
You are an expert technical recruiter. Evaluate this candidate against the job description.

Job Description:
{job_description}

Candidate Profile:
{candidate_summary}

Provide your assessment in JSON format:
{{
    "score": <0-100>,
    "match_percentage": <0-100>,
    "summary": "2-3 sentence overview of candidate fit",
    "strengths": ["strength1", "strength2", "strength3"],
    "gaps": ["gap1", "gap2"],
    "recommendation": "strong_fit | good_fit | moderate_fit | weak_fit"
}}

Be objective and thorough. Score based on:
- Skills match (40%)
- Experience relevance (30%)
- Education fit (15%)
- Achievements (15%)
"""
    
    try:
        resp = await asyncio.to_thread(
            lambda: client.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=prompt
            )
        )
        
        ai_text = resp.text
        
        # Extract JSON
        import re
        match = re.search(r'```json\s*(\{.*?\})\s*```', ai_text, re.DOTALL)
        if match:
            json_str = match.group(1)
        else:
            match = re.search(r'(\{.*\})', ai_text, re.DOTALL)
            if not match:
                raise ValueError("JSON not found")
            json_str = match.group(0)
        
        evaluation = json.loads(json_str)
        
        # merge evaluation with candidate data
        enhanced_candidate = {**candidate, **evaluation}
        return enhanced_candidate
        
    except Exception as e:
        print(f"Error evaluating candidate {candidate.get('name', 'Unknown')}: {e}")
        # Fallback scoring
        return {
            **candidate,
            "score": candidate.get('preliminary_score', 50),
            "match_percentage": 50,
            "summary": "Unable to generate detailed assessment",
            "strengths": ["Evaluation pending"],
            "gaps": [],
            "recommendation": "moderate_fit"
        }
    

# ranks and sorts the highest performing candidates from the given resumes
async def rank_candidates(candidates: List[Dict], job_description: str) -> List[Dict]:
    if not candidates:
        return []
    
    # evaluate all candidates concurrently
    evaluation_tasks = [
        evaluate_candidate(candidate, job_description)
        for candidate in candidates
    ]
    
    evaluated_candidates = await asyncio.gather(*evaluation_tasks)
    
    # sort by score (descending)
    ranked_candidates = sorted(
        evaluated_candidates,
        key=lambda x: x.get('score', 0),
        reverse=True
    )
    
    return ranked_candidates

if __name__ == "__main__":
    # test
    async def test():
        test_candidates = [
            {
                "name": "John Doe",
                "email": "john@example.com",
                "phone": "+1234567890",
                "skills": ["Python", "FastAPI", "Machine Learning"],
                "experience_years": "5",
                "education": "MS Computer Science",
                "relevant_experience": "5 years in AI development",
                "key_achievements": ["Built ML pipeline", "Led team of 3"]
            }
        ]
        
        test_jd = """
        We are looking for a Senior Python Developer with experience in FastAPI
        and machine learning. Must have 3+ years of experience.
        """
        
        ranked = await rank_candidates(test_candidates, test_jd)
        print(json.dumps(ranked, indent=2))
    
    asyncio.run(test())