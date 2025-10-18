from fastapi import FastAPI
from pydantic import BaseModel
from utils import GeminiClient
import os

app = FastAPI()
gemini = GeminiClient(api_key=os.environ.get("GEMINI_API_KEY"))

class SummReq(BaseModel):
    text: str

@app.post("/summarize")
def summarize(req: SummReq):
    summary = gemini.summarize(req.text)
    return {"summary": summary}
