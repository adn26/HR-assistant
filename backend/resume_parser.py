import re, os, json
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from google import genai
import asyncio

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

def get_client():
    api_key = os.getenv("AI_API_KEY")
    if not api_key:
        raise ValueError("AI_API_KEY not set in environment")
    return genai.Client(api_key=api_key)

# load pdf resume and divide into chunks
def load_pdf(file_path):
    loader = PyPDFLoader(file_path)
    pages = loader.load()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100,
        separators=["\n\n", "\n", " "]
    )
    return splitter.split_documents(pages)

# semantic embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")

# generate embeddings for document chunks
def embed_chunks(docs):
    texts = [doc.page_content for doc in docs]
    embedded_texts = model.encode(texts, convert_to_numpy=True)
    return embedded_texts

# semantic retrieval of most relevant chunks
def retrieve_chunks(query, docs, embeddings, top_k=5):
    query_emb = model.encode([query], convert_to_numpy=True)
    sim = cosine_similarity(query_emb, embeddings)[0]
    top_idx = sim.argsort()[-top_k:][::-1]
    return [docs[i] for i in top_idx]

# extract json from AI response
def extract_json(text):
    
    # try to find json block
    match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
    if match:
        json_str = match.group(1)
    else:
        match = re.search(r'(\{.*\})', text, re.DOTALL)
        if not match:
            raise ValueError("JSON not found in AI response")
        json_str = match.group(0)
    
    # clean up the json string
    json_str = re.sub(r',\s*}', '}', json_str)
    json_str = re.sub(r',\s*]', ']', json_str)
    
    return json.loads(json_str)

# extract candidate information using LLM with job desc that HR inputs
async def generate_candidate_info(text, job_description=""):
    client = get_client()
    
    jd_context = ""  # initialize the job desc context

    # if jd exists then add to the variable
    if job_description:
        jd_context = f"\nJob Description Context:\n{job_description}\n"
    
    prompt = f"""
You are an expert HR Assistant analyzing resumes.

{jd_context}
Extract the candidate's information from the resume text below.
Provide a brief assessment of how well they match the job requirements if provided.

Return ONLY valid JSON in this exact format:
{{
    "name": "Full Name",
    "email": "email@example.com",
    "phone": "+1234567890",
    "skills": ["skill1", "skill2", "skill3"],
    "experience_years": "5",
    "key_achievements": ["achievement1", "achievement2"],
    "education": "Highest degree and institution",
    "relevant_experience": "Brief summary of most relevant experience"
}}

Resume text:
{text}
"""
    
    try:
        resp = await asyncio.to_thread(
            lambda: client.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=prompt
            )
        )
        ai_text = resp.text
        return extract_json(ai_text)
    except Exception as e:
        print(f"Gemini AI error: {e}")
        return {"error": f"Failed to parse resume: {str(e)}"}
    
    
# this is the main function to parse resume and extract candidate information
async def parse_resume(file_location, job_description=""):
    try:
        # load and process pdf
        docs = load_pdf(file_location)
        embeddings = embed_chunks(docs)
        
        # retrieve relevant chunks by semantic retrieval
        chunks = retrieve_chunks("Extract candidate information", docs, embeddings, top_k=5)
        combined_text = "\n".join([chunk.page_content for chunk in chunks])
        
        # generate candidate info
        candidate = await generate_candidate_info(combined_text, job_description)
        
        if "error" in candidate:
            return candidate
        
        # add preliminary score (will be refined by the ranker function)
        num_skills = len(candidate.get("skills", []))
        candidate['preliminary_score'] = min(num_skills * 10, 100) # formula for calculating a simple score.
        
        return candidate
        
    except Exception as e:
        print(f"Error parsing resume: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    # test usage
    async def test():
        candidate_json = await parse_resume("resume.pdf")
        print(json.dumps(candidate_json, indent=2))
    
    asyncio.run(test())