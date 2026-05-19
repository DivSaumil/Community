import asyncio
from decimal import Decimal
from datetime import datetime, date, timedelta, timezone
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.main import app
from app.core.database import get_db, Base
from app.core.config import settings

# Import models to ensure they are registered on Base.metadata
from app.models.users import User, Flat
from app.models.finance import Invoice, Payment, Expense, Budget
from app.models.complaints import Complaint, ComplaintComment
from app.models.notices import Notice, PollOption, PollVote
from app.models.visitors import VisitorPass, VisitorLog, DailyHelp, DailyHelpFlat

# Define separate test database URL
TEST_DATABASE_URL = settings.DATABASE_URL.replace("/rwa_management", "/rwa_management_test")

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


async def setup_test_db():
    # Connect to default postgres DB to create/drop the test DB
    admin_url = settings.DATABASE_URL.replace("/rwa_management", "/postgres")
    admin_engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
    async with admin_engine.connect() as conn:
        # Drop test db if exists
        await conn.execute(text("DROP DATABASE IF EXISTS rwa_management_test"))
        # Create test db
        await conn.execute(text("CREATE DATABASE rwa_management_test"))
    await admin_engine.dispose()
    
    # Now connect to test db and create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def seed_test_db(session):
    # Clear tables
    for table in [
        "poll_votes",
        "poll_options",
        "notices",
        "complaint_comments",
        "complaints",
        "payments",
        "invoices",
        "daily_help_flats",
        "daily_helps",
        "visitor_logs",
        "visitor_passes",
        "flats",
        "users",
        "expenses",
        "budgets",
    ]:
        await session.execute(text(f"DELETE FROM {table}"))
    await session.commit()
    
    # Seed core seed data required by tests
    admin = User(phone="+919999999999", name="RWA President", role="admin")
    resident_user = User(phone="+918888888888", name="Amit Kumar", role="resident")
    tenant_user = User(phone="+917777777777", name="Suresh Patel", role="tenant")
    security_guard = User(phone="+916666666666", name="Ram Singh", role="security")
    staff_user = User(phone="+915555555555", name="Ravi Electrician", role="staff")
    
    session.add_all([admin, resident_user, tenant_user, security_guard, staff_user])
    await session.flush()

    # Seed flats
    flats = []
    for num in ["101", "102"]:
        flat = Flat(block="A", flat_number=num)
        if num == "101":
            flat.owner_id = resident_user.id
        elif num == "102":
            flat.owner_id = admin.id
            flat.tenant_id = tenant_user.id
        flats.append(flat)
    session.add_all(flats)
    await session.commit()


@pytest.fixture(scope="session", autouse=True)
def manage_db(event_loop):
    """Initializes the database schema for the test database."""
    event_loop.run_until_complete(setup_test_db())
    yield
    # Cleanup connection pool
    event_loop.run_until_complete(test_engine.dispose())


@pytest_asyncio.fixture
async def db_session():
    """
    Yields an AsyncSession.
    Seeds the test database before each test.
    """
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    SessionMaker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with SessionMaker() as session:
        await seed_test_db(session)
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session):
    """
    FastAPI HTTPX AsyncClient fixture.
    Overrides the get_db dependency with the test database session.
    """
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
