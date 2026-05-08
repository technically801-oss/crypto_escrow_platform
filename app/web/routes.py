import os
from fastapi import APIRouter, Depends, Form, Request, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.database import get_db
from app.models import Project, User, ServiceCategory

router = APIRouter()
templates = Jinja2Templates(directory='app/web/templates')
UPLOAD_DIR = 'uploads'
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.get('/', response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse('index.html', {'request': request})

@router.get('/create-project', response_class=HTMLResponse)
async def create_project_page(request: Request, db: AsyncSession = Depends(get_db)):
    services = (await db.scalars(select(ServiceCategory).where(ServiceCategory.active == True))).all()
    return templates.TemplateResponse('create_project.html', {'request': request, 'services': services})

@router.post('/create-project')
async def create_project(
    request: Request,
    client_name: str = Form(...),
    client_email: str = Form(...),
    client_telegram: str = Form(...),
    seller_telegram: str = Form(...),
    project_type: str = Form(...),
    budget: float = Form(...),
    timeline_days: int = Form(...),
    description: str = Form(...),
    attachment: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
):
    client_username = client_telegram.lstrip('@')
    client = await db.scalar(select(User).where(User.telegram_username == client_username))
    if not client:
        client = User(full_name=client_name, email=client_email, telegram_username=client_username, role='client')
        db.add(client)
        await db.flush()

    attachment_path = None
    if attachment and attachment.filename:
        attachment_path = os.path.join(UPLOAD_DIR, attachment.filename)
        with open(attachment_path, 'wb') as f:
            f.write(await attachment.read())

    project = Project(
        client_id=client.id,
        seller_telegram_username=seller_telegram.lstrip('@'),
        project_type=project_type,
        budget=budget,
        timeline_days=timeline_days,
        description=description,
        attachment_path=attachment_path,
        status='Pending Discussion',
        payment_status='Pending',
    )
    db.add(project)
    await db.commit()
    bot_url = f'https://t.me/{settings.telegram_bot_username}?start=project_{project.id}' if settings.telegram_bot_username else '#'
    seller_bot_url = bot_url
    return templates.TemplateResponse('project_success.html', {'request': request, 'project': project, 'bot_url': bot_url, 'seller_bot_url': seller_bot_url})

@router.get('/dashboard', response_class=HTMLResponse)
async def dashboard(
    request: Request,
    telegram: str = '',
    role: str = 'client',
    db: AsyncSession = Depends(get_db),
):
    projects = []

    if telegram:
        username = telegram.lstrip('@')

        user = await db.scalar(
            select(User).where(User.telegram_username == username)
        )

        if role == 'seller':
            q = (
                select(Project)
                .where(Project.seller_telegram_username == username)
                .order_by(Project.created_at.desc())
            )
        else:
            q = (
                select(Project)
                .join(User, Project.client_id == User.id)
                .where(User.telegram_username == username)
                .order_by(Project.created_at.desc())
            )

        projects = (await db.scalars(q.limit(50))).all()

    return templates.TemplateResponse(
        'dashboard.html',
        {
            'request': request,
            'projects': projects,
            'telegram': telegram,
            'role': role,
            'bot_username': settings.telegram_bot_username,
        },
    )