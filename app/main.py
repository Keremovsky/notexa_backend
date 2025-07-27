from fastapi import FastAPI
from api import routes_user, routes_chat, routes_workspace
from db.session import Base, engine

# create DB tables
Base.metadata.create_all(bind=engine)

app = FastAPI()

# include routers
app.include_router(routes_user.router, prefix="/api/users", tags=["Users"])
app.include_router(routes_chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(routes_workspace.router, prefix="/api/workspace", tags=["Workspace"])
