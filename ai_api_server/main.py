from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/items/{item_id}")
def read_item(item_id: int, q: str = None):
    return {"item_id": item_id, "q": q}

def run_prod():
    uvicorn.run("ai_api_server.main:app", host="0.0.0.0", port=8000, log_level="info")

def run_dev():
    uvicorn.run("ai_api_server.main:app", host="0.0.0.0", port=8000, log_level="debug", reload=True,)

if __name__ == "__main__":
    run_dev()

