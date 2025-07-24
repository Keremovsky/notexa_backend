from fastapi import FastAPI
from api import routes_user
from db.session import Base, engine

# Create DB tables
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Include routers
app.include_router(routes_user.router, prefix="/api/users", tags=["Users"])
