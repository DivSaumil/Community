import asyncio
import os
import sys
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

# Ensure the backend directory is in the python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from app.models.users import User, Flat
from app.models.finance import Invoice, Payment, Expense, Budget
from app.models.complaints import Complaint, ComplaintComment
from app.models.notices import Notice, PollOption, PollVote
from app.models.visitors import VisitorPass, VisitorLog, DailyHelp, DailyHelpFlat


async def seed_data() -> None:
    print("Connecting to database...")
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    
    async with session_factory() as session:
        print("Clearing existing data...")
        # Clear tables in reverse dependency order
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
            "expenses",
            "users",
            "budgets",
        ]:
            await session.execute(text(f"DELETE FROM {table}"))
        
        await session.commit()
        print("Existing data cleared.")

        print("Seeding Users...")
        admin = User(email="admin@cohabitat.com", name="RWA President", role="admin")
        resident_user = User(email="resident@cohabitat.com", name="Amit Kumar", role="resident", vehicle_number="KA-03-MB-1234")
        tenant_user = User(email="tenant@cohabitat.com", name="Suresh Patel", role="tenant", vehicle_number="KA-51-PH-9876")
        security_guard = User(email="guard@cohabitat.com", name="Ram Singh", role="security")
        staff_user = User(email="staff@cohabitat.com", name="Ravi Electrician", role="staff", vehicle_number="KA-04-E-5555")
        
        session.add_all([admin, resident_user, tenant_user, security_guard, staff_user])
        await session.flush()  # Generate IDs

        print("Seeding Flats...")
        # Create a few flats
        flats = []
        for block in ["A", "B"]:
            for num in ["101", "102", "103", "104", "201", "202"]:
                flat = Flat(block=block, flat_number=num)
                # Map Amit to A-101 (owner)
                if block == "A" and num == "101":
                    flat.owner_id = resident_user.id
                # Map Suresh to A-102 (tenant, owner is admin for demo)
                elif block == "A" and num == "102":
                    flat.owner_id = admin.id
                    flat.tenant_id = tenant_user.id
                flats.append(flat)
                
        session.add_all(flats)
        await session.flush()
        
        # Get specific flats for mapping
        flat_a101 = next(f for f in flats if f.block == "A" and f.flat_number == "101")
        flat_a102 = next(f for f in flats if f.block == "A" and f.flat_number == "102")
        flat_b101 = next(f for f in flats if f.block == "B" and f.flat_number == "101")

        print("Seeding Notices...")
        notice1 = Notice(
            title="Annual General Meeting (AGM) - 2026",
            content="Dear Residents, our annual AGM is scheduled for June 5th, 2026, at 7:00 PM in the Clubhouse. Attendance is highly requested.",
            type="event",
            created_by_id=admin.id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=15),
        )
        notice2 = Notice(
            title="Water Supply Interruption",
            content="Emergency: The overhead water tanks of Block A will undergo cleaning on May 22nd, 2026. Water supply will be suspended from 10:00 AM to 2:00 PM.",
            type="emergency",
            created_by_id=admin.id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=2),
        )
        poll_notice = Notice(
            title="Poll: Clubhouse Renovations",
            content="RWA is planning to renovate the clubhouse. Please vote on the amenity we should prioritize first.",
            type="poll",
            created_by_id=admin.id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        
        session.add_all([notice1, notice2, poll_notice])
        await session.flush()

        # Add poll options
        opt1 = PollOption(notice_id=poll_notice.id, option_text="Sleek Gym Equipment")
        opt2 = PollOption(notice_id=poll_notice.id, option_text="Swimming Pool Heating System")
        opt3 = PollOption(notice_id=poll_notice.id, option_text="Kid's Indoor Play Area")
        session.add_all([opt1, opt2, opt3])
        await session.flush()

        # Add some initial votes
        vote1 = PollVote(notice_id=poll_notice.id, option_id=opt1.id, user_id=resident_user.id)
        vote2 = PollVote(notice_id=poll_notice.id, option_id=opt2.id, user_id=tenant_user.id)
        session.add_all([vote1, vote2])

        print("Seeding Invoices & Payments...")
        # Maintenance invoice for Amit (A-101) - Unpaid
        invoice1 = Invoice(
            flat_id=flat_a101.id,
            title="Monthly Maintenance Fee - May 2026",
            amount=Decimal("3500.00"),
            due_date=date.today() + timedelta(days=10),
            status="unpaid",
            created_by_id=admin.id,
        )
        # Maintenance invoice for Suresh (A-102) - Paid
        invoice2 = Invoice(
            flat_id=flat_a102.id,
            title="Monthly Maintenance Fee - May 2026",
            amount=Decimal("3500.00"),
            due_date=date.today() + timedelta(days=10),
            status="paid",
            created_by_id=admin.id,
        )
        # Overdue invoice for Amit (A-101) - Overdue
        invoice3 = Invoice(
            flat_id=flat_a101.id,
            title="Clubhouse Event Contribution",
            amount=Decimal("500.00"),
            due_date=date.today() - timedelta(days=5),
            status="overdue",
            late_fee=Decimal("50.00"),
            created_by_id=admin.id,
        )
        
        session.add_all([invoice1, invoice2, invoice3])
        await session.flush()

        # Add payment record for Invoice 2 (Suresh)
        payment = Payment(
            invoice_id=invoice2.id,
            amount=Decimal("3500.00"),
            payment_method="UPI",
            transaction_id="TXN982736152",
            status="completed",
            paid_by_id=tenant_user.id,
            paid_at=datetime.now(timezone.utc) - timedelta(days=1),
            receipt_number="REC-20260519-1092",
        )
        session.add(payment)

        print("Seeding Expenses & Budgets...")
        budget1 = Budget(
            category="Housekeeping",
            allocated_amount=Decimal("40000.00"),
            start_date=date.today() - timedelta(days=20),
            end_date=date.today() + timedelta(days=10),
        )
        expense1 = Expense(
            title="May Housekeeping Vendor Payment",
            category="Housekeeping",
            amount=Decimal("35000.00"),
            spent_date=date.today() - timedelta(days=5),
            spent_by_id=admin.id,
            description="Paid monthly cleaning contract fee to CleanSpace India.",
        )
        session.add_all([budget1, expense1])

        print("Seeding Complaints...")
        # Open complaint from Amit (A-101)
        complaint1 = Complaint(
            flat_id=flat_a101.id,
            raised_by_id=resident_user.id,
            title="Kitchen Drain Clogged",
            description="The kitchen sink is draining very slowly and backing up. Needs urgent plumbing assistance.",
            category="plumbing",
            priority="high",
            status="open",
        )
        # Assigned complaint from Suresh (A-102)
        complaint2 = Complaint(
            flat_id=flat_a102.id,
            raised_by_id=tenant_user.id,
            title="Living room socket sparking",
            description="The main power plug socket in the living room sparks when plugging in the TV. Very dangerous.",
            category="electricity",
            priority="emergency",
            status="assigned",
            assigned_to_id=staff_user.id,
        )
        session.add_all([complaint1, complaint2])
        await session.flush()

        # Add comments on electricity complaint
        comment1 = ComplaintComment(
            complaint_id=complaint2.id,
            user_id=tenant_user.id,
            comment="Please send the electrician soon. I've taped the socket for safety for now.",
        )
        comment2 = ComplaintComment(
            complaint_id=complaint2.id,
            user_id=staff_user.id,
            comment="Received the ticket. I will visit your flat between 2:00 PM and 4:00 PM today.",
        )
        session.add_all([comment1, comment2])

        print("Seeding Daily Help...")
        maid = DailyHelp(
            name="Kamla Devi",
            phone="+919876543210",
            role="Maid",
            pass_code="DH8822",
            is_active=True,
        )
        session.add(maid)
        await session.flush()
        
        # Link Kamla to Flat A-101 and A-102
        link1 = DailyHelpFlat(daily_help_id=maid.id, flat_id=flat_a101.id)
        link2 = DailyHelpFlat(daily_help_id=maid.id, flat_id=flat_a102.id)
        session.add_all([link1, link2])

        print("Seeding Visitor Passes & Gate Logs...")
        v_pass = VisitorPass(
            flat_id=flat_a101.id,
            resident_id=resident_user.id,
            name="Rajesh Kumar",
            phone="+919000000000",
            visitor_type="guest",
            pass_code="527189",
            expected_arrival=datetime.now(timezone.utc) + timedelta(hours=5),
            valid_until=datetime.now(timezone.utc) + timedelta(hours=29),
            status="active",
        )
        session.add(v_pass)
        await session.flush()
        
        # Log entry for Rajesh (he entered already)
        log1 = VisitorLog(
            flat_id=flat_a102.id,
            name="Zomato Delivery",
            phone="+918000000000",
            visitor_type="delivery",
            vehicle_number="DL-3S-AA-1111",
            purpose="Food delivery",
            entry_time=datetime.now(timezone.utc) - timedelta(minutes=15),
            entered_gate_by_id=security_guard.id,
        )
        session.add(log1)

        await session.commit()
        print("Database seeded successfully with all roles and mock data!")
        
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_data())
