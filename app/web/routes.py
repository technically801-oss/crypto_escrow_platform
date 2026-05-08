import os

from fastapi import APIRouter, Depends, Form, Request, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import Project, User, ServiceCategory


router = APIRouter()
templates = Jinja2Templates(directory="app/web/templates")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def clean_username(username: str) -> str:
    return username.strip().lstrip("@").lower()


async def current_user(request: Request, db: AsyncSession):
    user_id = request.session.get("user_id")

    if not user_id:
        return None

    user = await db.get(User, user_id)

    if not user:
        request.session.clear()
        return None

    return user


def require_login(request: Request):
    if not request.session.get("user_id"):
        return RedirectResponse("/login", status_code=303)
    return None


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request},
    )


@router.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    return templates.TemplateResponse(
        "signup.html",
        {"request": request, "error": None},
    )


@router.post("/signup")
async def signup(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    telegram_username: str = Form(...),
    role: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    telegram_username = clean_username(telegram_username)
    email = email.strip().lower()

    existing = await db.scalar(
        select(User).where(
            or_(
                User.email == email,
                User.telegram_username == telegram_username,
            )
        )
    )

    if existing:
        return templates.TemplateResponse(
            "signup.html",
            {
                "request": request,
                "error": "Email or Telegram username already exists.",
            },
        )

    user = User(
        full_name=full_name,
        email=email,
        telegram_username=telegram_username,
        role=role,
        password=password,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    request.session["user_id"] = user.id
    request.session["role"] = user.role

    return RedirectResponse("/dashboard", status_code=303)


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": None},
    )


@router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    email = email.strip().lower()

    user = await db.scalar(select(User).where(User.email == email))

    if not user or user.password != password:
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error": "Invalid email or password.",
            },
        )

    request.session["user_id"] = user.id
    request.session["role"] = user.role

    return RedirectResponse("/dashboard", status_code=303)


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)


@router.get("/create-project", response_class=HTMLResponse)
async def create_project_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    login_redirect = require_login(request)

    if login_redirect:
        return login_redirect

    user = await current_user(request, db)

    if not user:
        request.session.clear()
        return RedirectResponse("/login", status_code=303)

    if user.role != "client":
        return templates.TemplateResponse(
            "create_project.html",
            {
                "request": request,
                "services": [],
                "error": "Only clients can create project offers.",
                "user": user,
            },
        )

    services = (
        await db.scalars(
            select(ServiceCategory).where(ServiceCategory.active == True)
        )
    ).all()

    return templates.TemplateResponse(
        "create_project.html",
        {
            "request": request,
            "services": services,
            "error": None,
            "user": user,
        },
    )


@router.post("/create-project")
async def create_project(
    request: Request,
    seller_telegram: str = Form(...),
    project_type: str = Form(...),
    budget: float = Form(...),
    timeline_days: int = Form(...),
    description: str = Form(...),
    attachment: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
):
    login_redirect = require_login(request)

    if login_redirect:
        return login_redirect

    user = await current_user(request, db)

    if not user:
        request.session.clear()
        return RedirectResponse("/login", status_code=303)

    if user.role != "client":
        return RedirectResponse("/dashboard", status_code=303)

    attachment_path = None

    if attachment and attachment.filename:
        safe_name = f"{user.id}_{attachment.filename}"
        attachment_path = os.path.join(UPLOAD_DIR, safe_name)

        with open(attachment_path, "wb") as f:
            f.write(await attachment.read())

    seller_username = clean_username(seller_telegram)

    seller = await db.scalar(
        select(User).where(User.telegram_username == seller_username)
    )

    project = Project(
        client_id=user.id,
        seller_id=seller.id if seller and seller.role == "seller" else None,
        seller_telegram_username=seller_username,
        project_type=project_type,
        budget=budget,
        timeline_days=timeline_days,
        description=description,
        attachment_path=attachment_path,
        status="Pending Discussion",
        payment_status="Pending",
    )

    db.add(project)
    await db.commit()
    await db.refresh(project)

    bot_url = (
        f"https://t.me/{settings.telegram_bot_username}?start=project_{project.id}"
        if settings.telegram_bot_username
        else "#"
    )

    seller_bot_url = (
        f"https://t.me/{settings.telegram_bot_username}?start=seller"
        if settings.telegram_bot_username
        else "#"
    )

    return templates.TemplateResponse(
        "project_success.html",
        {
            "request": request,
            "project": project,
            "bot_url": bot_url,
            "seller_bot_url": seller_bot_url,
            "user": user,
        },
    )


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    login_redirect = require_login(request)

    if login_redirect:
        return login_redirect

    user = await current_user(request, db)

    if not user:
        request.session.clear()
        return RedirectResponse("/login", status_code=303)

    if user.role == "seller":
        q = (
            select(Project)
            .where(
                or_(
                    Project.seller_id == user.id,
                    Project.seller_telegram_username == user.telegram_username,
                )
            )
            .order_by(Project.created_at.desc())
        )
    else:
        q = (
            select(Project)
            .where(Project.client_id == user.id)
            .order_by(Project.created_at.desc())
        )

    projects = (await db.scalars(q.limit(50))).all()

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "projects": projects,
            "user": user,
            "bot_username": settings.telegram_bot_username,
        },
    )

@router.get("/profile", response_class=HTMLResponse)
async def profile(request: Request, db: AsyncSession = Depends(get_db)):
    login_redirect = require_login(request)
    if login_redirect:
        return login_redirect

    user = await current_user(request, db)

    if not user:
        request.session.clear()
        return RedirectResponse("/login", status_code=303)

    return templates.TemplateResponse(
        "profile.html",
        {
            "request": request,
            "user": user,
            "bot_username": settings.telegram_bot_username,
        },
    )