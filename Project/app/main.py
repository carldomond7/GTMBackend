import os
from fastapi import FastAPI, HTTPException, File, UploadFile, Request
import uvicorn
from pydantic import BaseModel
import json
from. streaming_handler import StreamingHandler
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse 
import asyncio 
import redis
from typing import Dict
from uuid import uuid4

# Set up necessary environment variables
groq_api_key = os.getenv("GROQ_API_KEY")
openai_key = os.getenv("OPENAI_API_KEY")
redis_password = os.getenv("REDIS_PASSWORD")

REDIS_HOST = 'redis-16426.c263.us-east-1-2.ec2.redns.redis-cloud.com'
REDIS_PORT = 16426

#Initialize Redis Client
redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=redis_password,
    decode_responses=True
)

class UserRequest(BaseModel):
    openai_assistant_response: str

class Unique_ID(BaseModel):
    unique_id: str


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://gtmhtml.onrender.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#Returns transcripts stored in Redis
@app.post("/get_transcript"):
async def get_transcript_endpoint(UUID: Unique_ID):
  #First step is to obtain what was sent from client
  unique_id = UUID.unique_id
  print(unique_id)
  #Leverage Unique ID (stored in the unique_id variable) to obtain transcripts
  while True:
        if redis_client.exists(unique_id):
            data = redis_client.hgetall(unique_id)
            if data:
                return data["transcript"]
        await asyncio.sleep(1)  # Sleep for a short duration before checking again

#Stores OpenAI Assistant Response into Redis database
@app.post("/process_text/")
async def process_text_endpoint(request: UserRequest):
    unique_id = str(uuid4())
    # Store the text in Redis with an expiration time of 24 hours (86400 seconds)
    redis_client.hmset(unique_id, {"OpenAI_Assistant_Response": request.openai_assistant_response})
    redis_client.expire(unique_id, 86400)  # Set expiration to 24 hours
    # Return the unique ID
    return JSONResponse({"status": "Success", "message": "OpenAI assistant response received and stored", "id": unique_id})

#FUNCTION: Extracts OpenAI Assistant Response from Redis Database
async def get_OpenAI_response(unique_id: str):
    while True:
        if redis_client.exists(unique_id):
            data = redis_client.hgetall(unique_id)
            if data:
                return data["OpenAI_Assistant_Response"]
        await asyncio.sleep(1)  # Sleep for a short duration before checking again

#Returns the streamed openai assistant response that is extracted using the get_OpenAI_response function
@app.get("/stream_processed_response/{unique_id}")
async def stream_processed_text_endpoint(unique_id: str):
    text = await get_OpenAI_response(unique_id)
    if not text:
        raise HTTPException(status_code=400, detail="Text not available")
    
    streaming_handler = StreamingHandler(100)
    response_stream = streaming_handler.create_generator(text)

    async def streaming_response():
        async for chunk in response_stream:
            yield chunk.encode('utf-8')

    return StreamingResponse(streaming_response(), media_type="text/plain")


#Solely for VAPI to contact and send transcript to
@app.post("/process_transcript/")
async def process_transcript_endpoint(request: Request):
    unique_id = str(uuid4())
    data = await request.json()
    print(json.dumps(data, indent=4))
    transcript = data.get("message", {}).get("transcript")
    assistant_id = data.get("message", {}).get("call", {}).get("assistantId", {})
    print(assistant_id)
    redis_client.hmset(unique_id, {"transcript": transcript}) #Initializing Redis entry unique ID being associated with transcript
    redis_client.expire(unique_id, 86400) #Set expiration time
    make_payload = {"status": "Success", "UUID": unique_id, "Assistant_ID": assistant_id}
    make_webhook_url = "https://hook.us1.make.com/rna2u29fyv3icgzlime7gaeaahqcmqwk"
    response = requests.post(make_webhook_url, json=make_payload)
    if response.status_code == 200:
        return {"message": "Transcript UUID successfully sent to make."}
    else:
        return {
            "error": "Failed to send Transcript UUID to make.",
            "statusCode": response.status_code,
        }


