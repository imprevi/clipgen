from fastapi import FastAPI

app = FastAPI(title="StreamClip AI")

@app.get("/")
async def root():
    return {"message": "StreamClip AI - Day 1 Setup Complete"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 