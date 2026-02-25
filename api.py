import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from cover_letter import generate_cover_letter

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["POST"],
    allow_headers=["*"],
)


@app.post("/api/generate")
async def generate(
    resume: UploadFile = File(...),
    job_description: str = Form(...),
    model: str = Form(...),
):
    if resume.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=400, detail="Resume must be a PDF.")

    contents = await resume.read()
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(contents)
        tmp_path = Path(tmp.name)

    try:
        result = await generate_cover_letter(
            resume_pdf_path=tmp_path,
            job_description=job_description,
            model=model,
        )
    finally:
        tmp_path.unlink(missing_ok=True)

    return {"cover_letter": result.cover_letter, "company_name": result.company_name}
