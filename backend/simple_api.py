"""
Simple FastAPI app for testing
"""

from fastapi import FastAPI
from datetime import datetime

app = FastAPI(title="Long Article Writer - Simple Test")


@app.get("/")
def root():
    return {"message": "Long Article Writer API", "status": "running", "time": datetime.now().isoformat()}


@app.get("/health")
def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)