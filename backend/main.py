from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Backend is running"}
@app.post("/predict")
def predict():
    return {"status": "Food is Fresh"}
