from fastapi import FastAPI

from routers import chat, weather, rag, map as map_router  # type: ignore

app = FastAPI(title="Kids Activity Chatbot Backend")

# Router registration (stubs)
app.include_router(chat.router, prefix="/chat", tags=["chat"])  # noqa: E402
app.include_router(weather.router, prefix="/weather", tags=["weather"])  # noqa: E402
app.include_router(rag.router, prefix="/rag", tags=["rag"])  # noqa: E402
app.include_router(map_router.router, prefix="/map", tags=["map"])  # noqa: E402


@app.get("/")
def healthcheck():
    return {"status": "ok"}
