from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import httpx
import os

router = APIRouter(prefix="/ai", tags=["ai"])


class ChatRequest(BaseModel):
    message: str
    messages: Optional[List[dict]] = None


@router.post("/chat")
async def chat(req: ChatRequest):
    base = os.getenv("AI_MODEL_BASE_URL", "http://127.0.0.1:9010")
    url = f"{base}/api/chat"
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            payload = {"message": req.message}
            if req.messages:
                payload["messages"] = req.messages
            response = await client.post(url, json=payload)
            if response.status_code == 422 and req.messages:
                # Fallback for AI servers that don't accept chat history yet.
                response = await client.post(url, json={"message": req.message})
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI service error: {exc}")
