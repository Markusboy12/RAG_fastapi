"""
FastAPI Backend с SSE streaming для RAG-агента
"""
import json
import uuid
from typing import Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.pipeline import get_pipeline, RAGPipeline
from backend.config import settings


# Модели данных
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    session_id: str


# Создание приложения
app = FastAPI(
    title="FastAPI RAG Agent",
    description="RAG-агент по документации FastAPI с HyDE и streaming",
    version="0.1.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Статические файлы (фронтенд)
app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.on_event("startup")
async def startup_event():
    """Инициализация пайплайна при старте"""
    pipeline = await get_pipeline()
    print("RAG Pipeline инициализирован")


@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Отдача фронтенда"""
    with open("frontend/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "0.1.0"}


async def generate_sse_stream(
    pipeline: RAGPipeline,
    query: str,
    session_id: str
):
    """
    Генератор SSE событий для потоковой передачи
    
    Формат SSE:
    event: token
    data: {"token": "..."}
    
    event: done
    data: {"session_id": "..."}
    """
    full_response = ""
    
    try:
        async for token in pipeline.chat_stream(query, session_id):
            full_response += token
            # Форматирование SSE события
            sse_data = json.dumps({"token": token}, ensure_ascii=False)
            yield f"data: {sse_data}\n\n"
        
        # Сохранение ответа в историю
        await pipeline.save_message(session_id, "assistant", full_response)
        
        # Событие завершения
        yield f"data: {json.dumps({'done': True, 'session_id': session_id})}\n\n"
        
    except Exception as e:
        # Ошибка в стриме
        error_data = json.dumps({"error": str(e)}, ensure_ascii=False)
        yield f"data: {error_data}\n\n"


@app.post("/chat")
async def chat_streaming(request: ChatRequest):
    """
    Чат с SSE streaming
    
    Возвращает StreamingResponse с токенами в реальном времени
    """
    # Генерация session_id если не предоставлен
    session_id = request.session_id or str(uuid.uuid4())
    
    try:
        pipeline = await get_pipeline()
        
        return StreamingResponse(
            generate_sse_stream(pipeline, request.message, session_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # Отключение буферизации nginx
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/sync", response_model=ChatResponse)
async def chat_sync(request: ChatRequest):
    """
    Синхронный чат (fallback для клиентов без SSE)
    
    Возвращает полный ответ JSON
    """
    session_id = request.session_id or str(uuid.uuid4())
    
    try:
        pipeline = await get_pipeline()
        response = await pipeline.chat_sync(request.message, session_id)
        
        # Сохранение ответа
        await pipeline.save_message(session_id, "assistant", response)
        
        return ChatResponse(response=response, session_id=session_id)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sessions/{session_id}/history")
async def get_history(session_id: str):
    """Получение истории сессии"""
    try:
        pipeline = await get_pipeline()
        
        if pipeline.redis_memory:
            history = await pipeline.redis_memory.aget(session_id=session_id)
            return {"session_id": session_id, "history": history}
        
        return {"session_id": session_id, "history": []}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """Удаление сессии"""
    try:
        pipeline = await get_pipeline()
        
        if pipeline.redis_memory:
            await pipeline.redis_memory.adelete(session_id=session_id)
        
        return {"status": "deleted", "session_id": session_id}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "backend.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=True,
        log_level=settings.log_level.lower()
    )
