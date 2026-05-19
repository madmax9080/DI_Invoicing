import warnings
from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from app.routers import auth, dynamic_reference
from app.routers import reference, invoices, clients, dashboard, reports, buyers
    
warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    module="openpyxl"
)
@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
app = FastAPI(
    title="FBR Digital Invoicing Backend",
    lifespan=lifespan,
    redirect_slashes=False
)
app.router.redirect_slashes = True
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "http://localhost:3000",
    "http://localhost",
    ],
    allow_credentials=True,
    allow_methods=["*"],    
    allow_headers=["*"],
)
# Base.metadata.create_all(bind=engine)
app.include_router(reference.router)
app.include_router(invoices.router)
app.include_router(clients.router)
app.include_router(dynamic_reference.router)
app.include_router(dashboard.router)
app.include_router(reports.router)
app.include_router(buyers.router)
app.include_router(auth.router)
BASE_DIR = Path(__file__).resolve().parent
app.mount("/static",StaticFiles(directory=BASE_DIR / "static"),name="static")