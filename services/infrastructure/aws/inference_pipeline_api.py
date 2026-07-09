import opik
from opik import opik_context

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

import os
from typing import Optional
from datetime import datetime, timedelta, timezone
import asyncpg
import asyncio
import traceback
from jose import JWTError, jwt
from passlib.context import CryptContext

from services.settings import settings
from services.application.rag.retriever import ContextRetriever
from services.application.utils import misc
from services.domain.embedded_chunks import EmbeddedChunk
from services.infrastructure.opik_config.opik_utils import configure_opik
from services.model.inference import InferenceExcuter, LLMInferenceSagemakerEndpoint

configure_opik()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

POSTGRES_DSN = settings.POSTGRES_DSN
JWT_SECRET = os.environ.get("JWT_SECRET", "change-me-in-production-please")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24 * 7  # 7 days

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)

_pool: Optional[asyncpg.Pool] = None


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(POSTGRES_DSN)
        await _pool.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                username TEXT NOT NULL,
                hashed_password TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        await _pool.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        await _pool.execute("""
            ALTER TABLE chat_messages
            ADD COLUMN IF NOT EXISTS user_id INTEGER
        """)
    return _pool


@app.on_event("startup")
async def startup():
    await get_pool()


@app.on_event("shutdown")
async def shutdown():
    global _pool
    if _pool:
        await _pool.close()


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------


def hash_password(password: str) -> str:
    return pwd_ctx.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_ctx.verify(plain, hashed)


def create_token(user_id: int, email: str, username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS)
    return jwt.encode(
        {"sub": str(user_id), "email": email, "username": username, "exp": expire},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


async def current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> dict:
    if not creds:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return decode_token(creds.credentials)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class RegisterRequest(BaseModel):
    email: str
    username: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    token: str
    user_id: int
    email: str
    username: str


class QueryRequest(BaseModel):
    query: str
    session_id: str = "default"


class QueryResponse(BaseModel):
    answer: str


class ChatMessage(BaseModel):
    role: str
    content: str
    created_at: Optional[str] = None


class HistoryResponse(BaseModel):
    messages: list[ChatMessage]


class DashboardStats(BaseModel):
    total_messages: int
    total_sessions: int
    user_messages: int
    ai_messages: int
    member_since: str
    recent_messages: list[ChatMessage]


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------


@app.post("/auth/register", response_model=AuthResponse)
async def register(req: RegisterRequest):
    pool = await get_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT id FROM users WHERE email = $1", req.email
        )
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
        row = await conn.fetchrow(
            "INSERT INTO users (email, username, hashed_password) VALUES ($1, $2, $3) RETURNING id, created_at",
            req.email,
            req.username,
            hash_password(req.password),
        )
    token = create_token(row["id"], req.email, req.username)
    return AuthResponse(
        token=token, user_id=row["id"], email=req.email, username=req.username
    )


@app.post("/auth/login", response_model=AuthResponse)
async def login(req: LoginRequest):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, username, hashed_password FROM users WHERE email = $1",
            req.email,
        )
    if not row or not verify_password(req.password, row["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_token(row["id"], req.email, row["username"])
    return AuthResponse(
        token=token, user_id=row["id"], email=req.email, username=row["username"]
    )


@app.get("/auth/me")
async def me(user: dict = Depends(current_user)):
    return {
        "user_id": int(user["sub"]),
        "email": user["email"],
        "username": user["username"],
    }


# ---------------------------------------------------------------------------
# Dashboard endpoint
# ---------------------------------------------------------------------------


@app.get("/dashboard/stats", response_model=DashboardStats)
async def dashboard_stats(user: dict = Depends(current_user)):
    user_id = int(user["sub"])
    pool = await get_pool()
    async with pool.acquire() as conn:
        total = await conn.fetchval(
            "SELECT COUNT(*) FROM chat_messages WHERE user_id = $1", user_id
        )
        sessions = await conn.fetchval(
            "SELECT COUNT(DISTINCT session_id) FROM chat_messages WHERE user_id = $1",
            user_id,
        )
        user_msgs = await conn.fetchval(
            "SELECT COUNT(*) FROM chat_messages WHERE user_id = $1 AND role = 'user'",
            user_id,
        )
        ai_msgs = await conn.fetchval(
            "SELECT COUNT(*) FROM chat_messages WHERE user_id = $1 AND role = 'assistant'",
            user_id,
        )
        member_row = await conn.fetchrow(
            "SELECT created_at FROM users WHERE id = $1", user_id
        )
        recent = await conn.fetch(
            "SELECT role, content, created_at FROM chat_messages WHERE user_id = $1 ORDER BY id DESC LIMIT 6",
            user_id,
        )
    return DashboardStats(
        total_messages=total or 0,
        total_sessions=sessions or 0,
        user_messages=user_msgs or 0,
        ai_messages=ai_msgs or 0,
        member_since=member_row["created_at"].strftime("%B %Y") if member_row else "—",
        recent_messages=[
            ChatMessage(
                role=r["role"],
                content=r["content"],
                created_at=r["created_at"].isoformat(),
            )
            for r in recent
        ],
    )


# ---------------------------------------------------------------------------
# RAG endpoints (auth required)
# ---------------------------------------------------------------------------


@opik.track
def call_llm_service(query: str, context: str | None) -> str:
    llm = LLMInferenceSagemakerEndpoint(
        endpoint_name=settings.SAGEMAKER_ENDPOINT_INFERENCE,
        inference_component_name=None,
    )
    return InferenceExcuter(llm, query, context).execute()


@opik.track
def rag(query: str) -> str:
    retriever = ContextRetriever(mock=False)
    documents = retriever.search(query, k=4)
    context = EmbeddedChunk.to_context(documents)
    answer = call_llm_service(query, context)
    opik_context.update_current_trace(
        tags=["rag"],
        metadata={
            "model_id": settings.HF_MODEL_ID,
            "embedding_model_id": settings.TEXT_EMBEDDING_MODEL_ID,
            "temperature": settings.TEMPERATURE_INFERENCE,
            "query_tokens": misc.compute_num_tokens(query),
            "context_tokens": misc.compute_num_tokens(context),
            "answer_tokens": misc.compute_num_tokens(answer),
        },
    )
    return answer


@app.post("/rag", response_model=QueryResponse)
async def rag_endpoint(request: QueryRequest, user: dict = Depends(current_user)):
    try:
        answer = rag(query=request.query)
        user_id = int(user["sub"])
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO chat_messages (user_id, session_id, role, content) VALUES ($1, $2, $3, $4)",
                user_id,
                request.session_id,
                "user",
                request.query,
            )
            await conn.execute(
                "INSERT INTO chat_messages (user_id, session_id, role, content) VALUES ($1, $2, $3, $4)",
                user_id,
                request.session_id,
                "assistant",
                answer,
            )
        return QueryResponse(answer=answer)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}") from e


@app.post("/rag/stream")
async def rag_stream_endpoint(
    request: QueryRequest, user: dict = Depends(current_user)
):
    try:
        answer = await asyncio.get_event_loop().run_in_executor(
            None, rag, request.query
        )
    except Exception as e:
        traceback.print_exc()
        error_message = f"[ERROR] {type(e).__name__}: {e}"

        async def error_stream():
            yield f"data: {error_message}\n\n"

        return StreamingResponse(
            error_stream(),
            media_type="text/event-stream",
        )

    user_id = int(user["sub"])

    async def _save():
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO chat_messages (user_id, session_id, role, content) VALUES ($1, $2, $3, $4)",
                    user_id,
                    request.session_id,
                    "user",
                    request.query,
                )
                await conn.execute(
                    "INSERT INTO chat_messages (user_id, session_id, role, content) VALUES ($1, $2, $3, $4)",
                    user_id,
                    request.session_id,
                    "assistant",
                    answer,
                )
        except Exception:
            traceback.print_exc()

    asyncio.create_task(_save())

    async def token_stream():
        words = answer.split(" ")
        for i, word in enumerate(words):
            chunk = word if i == 0 else " " + word
            yield f"data: {chunk}\n\n"
            await asyncio.sleep(0.03)
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        token_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/chat/history", response_model=HistoryResponse)
async def get_history(session_id: str = "default", user: dict = Depends(current_user)):
    user_id = int(user["sub"])
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT role, content, created_at FROM chat_messages WHERE user_id = $1 AND session_id = $2 ORDER BY id ASC",
                user_id,
                session_id,
            )
        return HistoryResponse(
            messages=[
                ChatMessage(
                    role=r["role"],
                    content=r["content"],
                    created_at=r["created_at"].isoformat(),
                )
                for r in rows
            ]
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}") from e


@app.delete("/chat/history")
async def clear_history(
    session_id: str = "default", user: dict = Depends(current_user)
):
    user_id = int(user["sub"])
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM chat_messages WHERE user_id = $1 AND session_id = $2",
                user_id,
                session_id,
            )
        return {"status": "cleared"}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}") from e


# uv run --active uvicorn services.infrastructure.aws.inference_pipeline_api:app --reload
