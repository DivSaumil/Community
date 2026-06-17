import pytest
import uuid
from decimal import Decimal
from datetime import datetime, date, timedelta, timezone
from sqlalchemy import select
from app.models.users import User, Flat
from app.models.finance import Invoice, Payment
from app.models.notices import Notice, PollOption, PollVote
from app.models.visitors import VisitorPass, VisitorLog


# Helpers
async def get_auth_headers(client, email: str, otp: str = "123456"):
    response = await client.post(
        "/api/v1/auth/otp/verify", 
        json={"email": email, "otp": otp}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_otp_flow(client):
    # 1. Request OTP
    response = await client.post(
        "/api/v1/auth/otp/request", 
        json={"email": "new_resident@cohabitat.com"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "otp" in data
    assert data["otp"] == "sent"  # OTP is never exposed in the response
    
    # 2. Verify OTP (use the master mock OTP '123456' for development/test environment)
    response_verify = await client.post(
        "/api/v1/auth/otp/verify", 
        json={"email": "new_resident@cohabitat.com", "otp": "123456"}
    )
    assert response_verify.status_code == 200
    token_data = response_verify.json()
    assert "access_token" in token_data
    assert "refresh_token" in token_data
    assert token_data["role"] == "resident"  # default auto-registered role


@pytest.mark.asyncio
async def test_refresh_token_flow(client):
    response_verify = await client.post(
        "/api/v1/auth/otp/verify", 
        json={"email": "resident@cohabitat.com", "otp": "123456"}
    )
    assert response_verify.status_code == 200
    token_data = response_verify.json()
    refresh_token = token_data["refresh_token"]
    
    response_refresh = await client.post(
        f"/api/v1/auth/refresh?refresh_token={refresh_token}"
    )
    assert response_refresh.status_code == 200
    new_token_data = response_refresh.json()
    assert "access_token" in new_token_data
    assert "refresh_token" in new_token_data


@pytest.mark.asyncio
async def test_read_profile(client):
    headers = await get_auth_headers(client, "resident@cohabitat.com")  # Amit Kumar
    response = await client.get("/api/v1/users/me", headers=headers)
    assert response.status_code == 200
    profile = response.json()
    assert profile["name"] == "Amit Kumar"
    assert profile["role"] == "resident"


@pytest.mark.asyncio
async def test_admin_rbac_protection(client):
    # A resident should not be allowed to register a flat
    resident_headers = await get_auth_headers(client, "resident@cohabitat.com")
    response = await client.post(
        "/api/v1/users/flats", 
        headers=resident_headers, 
        json={"block": "C", "flat_number": "909"}
    )
    assert response.status_code == 403
    
    # Admin should be allowed
    admin_headers = await get_auth_headers(client, "admin@cohabitat.com")
    response_admin = await client.post(
        "/api/v1/users/flats", 
        headers=admin_headers, 
        json={"block": "C", "flat_number": "909"}
    )
    assert response_admin.status_code == 200
    assert response_admin.json()["flat_number"] == "909"


@pytest.mark.asyncio
async def test_billing_and_payment_flow(client, db_session):
    admin_headers = await get_auth_headers(client, "admin@cohabitat.com")
    resident_headers = await get_auth_headers(client, "resident@cohabitat.com")
    
    # 1. Fetch Amit's Flat ID
    res = await db_session.execute(select(Flat).where(Flat.block == "A", Flat.flat_number == "101"))
    flat_a101 = res.scalar_one()
    
    # 2. Admin creates an invoice
    due_date = (date.today() + timedelta(days=10)).isoformat()
    response_invoice = await client.post(
        "/api/v1/finance/invoices",
        headers=admin_headers,
        json={
            "flat_id": str(flat_a101.id),
            "title": "Clubhouse Pool Repair Contribution",
            "amount": 1000.00,
            "due_date": due_date
        }
    )
    assert response_invoice.status_code == 200
    invoice = response_invoice.json()
    assert invoice["status"] == "unpaid"
    invoice_id = invoice["id"]
    
    # 3. Resident views their invoices
    response_my_invoices = await client.get("/api/v1/finance/my-invoices", headers=resident_headers)
    assert response_my_invoices.status_code == 200
    my_invoices = response_my_invoices.json()
    assert any(inv["id"] == invoice_id for inv in my_invoices)
    
    # 4. Resident pays the invoice
    response_pay = await client.post(
        "/api/v1/finance/pay",
        headers=resident_headers,
        json={
            "invoice_id": invoice_id,
            "amount": 1000.00,
            "payment_method": "UPI",
            "transaction_id": "TXN_TEST1234"
        }
    )
    assert response_pay.status_code == 200
    payment = response_pay.json()
    assert payment["status"] == "completed"
    
    # Verify invoice status transitioned to 'paid'
    res_inv = await db_session.execute(select(Invoice).where(Invoice.id == uuid.UUID(invoice_id)))
    db_invoice = res_inv.scalar_one()
    assert db_invoice.status == "paid"


@pytest.mark.asyncio
async def test_notices_and_polling_flow(client, db_session):
    admin_headers = await get_auth_headers(client, "admin@cohabitat.com")
    resident_headers = await get_auth_headers(client, "resident@cohabitat.com")
    
    # 1. Admin creates a poll notice
    response_poll = await client.post(
        "/api/v1/notices",
        headers=admin_headers,
        json={
            "title": "Which day for Society Fest?",
            "content": "Vote on the most preferred day for our annual celebration.",
            "type": "poll",
            "poll_options": ["Saturday June 6", "Sunday June 7"]
        }
    )
    assert response_poll.status_code == 201
    poll = response_poll.json()
    assert len(poll["poll_options"]) == 2
    notice_id = poll["id"]
    opt1_id = poll["poll_options"][0]["id"]
    opt2_id = poll["poll_options"][1]["id"]
    
    # 2. Resident votes on option 1
    response_vote = await client.post(
        f"/api/v1/notices/{notice_id}/vote",
        headers=resident_headers,
        json={"option_id": opt1_id}
    )
    assert response_vote.status_code == 200
    
    # 3. Resident tries to vote again on the same poll
    response_double_vote = await client.post(
        f"/api/v1/notices/{notice_id}/vote",
        headers=resident_headers,
        json={"option_id": opt2_id}
    )
    assert response_double_vote.status_code == 400
    assert "already voted" in response_double_vote.json()["detail"]
    
    # 4. View poll details to verify counts
    response_detail = await client.get(f"/api/v1/notices/{notice_id}", headers=resident_headers)
    assert response_detail.status_code == 200
    updated_poll = response_detail.json()
    opt1 = next(o for o in updated_poll["poll_options"] if o["id"] == opt1_id)
    assert opt1["vote_count"] == 1
 
 
@pytest.mark.asyncio
async def test_visitor_pass_and_gate_flow(client, db_session):
    resident_headers = await get_auth_headers(client, "resident@cohabitat.com")
    guard_headers = await get_auth_headers(client, "guard@cohabitat.com")
    
    # 1. Fetch Amit's Flat ID
    res = await db_session.execute(select(Flat).where(Flat.block == "A", Flat.flat_number == "101"))
    flat_a101 = res.scalar_one()
    
    # 2. Resident pre-approves visitor
    expected_arrival = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    response_pass = await client.post(
        "/api/v1/visitors/pre-approve",
        headers=resident_headers,
        json={
            "flat_id": str(flat_a101.id),
            "name": "Courier Boy",
            "phone": "+919999000000",
            "visitor_type": "delivery",
            "expected_arrival": expected_arrival
        }
    )
    assert response_pass.status_code == 200
    v_pass = response_pass.json()
    pass_code = v_pass["pass_code"]
    
    # 3. Guard logs check-in at the gate using the passcode
    response_checkin = await client.post(
        "/api/v1/visitors/gate/check-in",
        headers=guard_headers,
        json={"pass_code": pass_code, "vehicle_number": "DL-1S-BB-2222"}
    )
    assert response_checkin.status_code == 200
    log = response_checkin.json()
    assert log["name"] == "Courier Boy"
    assert log["visitor_type"] == "delivery"
    assert log["vehicle_number"] == "DL-1S-BB-2222"
    log_id = log["id"]
    
    # Verify visitor pass status updated to used
    res_pass = await db_session.execute(select(VisitorPass).where(VisitorPass.pass_code == pass_code))
    db_pass = res_pass.scalar_one()
    assert db_pass.status == "used"
    
    # 4. Guard logs departure/check-out
    response_checkout = await client.post(
        f"/api/v1/visitors/gate/check-out/{log_id}",
        headers=guard_headers
    )
    assert response_checkout.status_code == 200
    assert response_checkout.json()["exit_time"] is not None


@pytest.mark.asyncio
async def test_user_signup_flow(client):
    # 1. Request OTP for unregistered email
    response_req = await client.post(
        "/api/v1/auth/otp/request", 
        json={"email": "johndoe@example.com"}
    )
    assert response_req.status_code == 200
    
    # 2. Verify OTP (should fail with 404 since it's not a cohabitat email and not registered)
    response_verify = await client.post(
        "/api/v1/auth/otp/verify",
        json={"email": "johndoe@example.com", "otp": "123456"}
    )
    assert response_verify.status_code == 404
    assert response_verify.json()["detail"] == "EMAIL_NOT_REGISTERED"
    
    # 3. Register user using /auth/register
    response_reg = await client.post(
        "/api/v1/auth/register",
        json={
            "name": "John Doe",
            "email": "johndoe@example.com",
            "role": "resident",
            "block": "X",
            "flat_number": "999",
            "vehicle_number": "KA-05-AA-1234",
            "otp": "123456"
        }
    )
    assert response_reg.status_code == 200
    token_data = response_reg.json()
    assert "access_token" in token_data
    assert token_data["role"] == "resident"
    
    # 4. Read profile to ensure it has flat X-999
    headers = {"Authorization": f"Bearer {token_data['access_token']}"}
    response_me = await client.get("/api/v1/users/me", headers=headers)
    assert response_me.status_code == 200
    profile = response_me.json()
    assert profile["name"] == "John Doe"
    assert "X-999" in profile["flats"]


@pytest.mark.asyncio
async def test_daily_help_resident_flow(client):
    resident_headers = await get_auth_headers(client, "resident@cohabitat.com")
    
    # 1. Resident registers a new daily helper
    response_reg = await client.post(
        "/api/v1/visitors/daily-help/register-by-resident",
        headers=resident_headers,
        json={
            "name": "Kamla Bai",
            "phone": "+919876543210",
            "role": "Maid"
        }
    )
    assert response_reg.status_code == 200
    helper = response_reg.json()
    assert helper["name"] == "Kamla Bai"
    assert helper["role"] == "Maid"
    assert "A-101" in helper["flats"]  # resident@cohabitat.com is resident of A-101
    
    helper_id = helper["id"]
    
    # 2. Unlink helper from flat
    response_unlink = await client.post(
        f"/api/v1/visitors/daily-help/{helper_id}/unlink",
        headers=resident_headers
    )
    assert response_unlink.status_code == 200
    unlinked_helper = response_unlink.json()
    assert "A-101" not in unlinked_helper["flats"]
    
    # 3. Link helper back to flat
    response_link = await client.post(
        f"/api/v1/visitors/daily-help/{helper_id}/link",
        headers=resident_headers
    )
    assert response_link.status_code == 200
    linked_helper = response_link.json()
    assert "A-101" in linked_helper["flats"]


@pytest.mark.asyncio
async def test_admin_user_management_flow(client):
    admin_headers = await get_auth_headers(client, "admin@cohabitat.com")
    resident_headers = await get_auth_headers(client, "resident@cohabitat.com")
    
    # 1. Non-admin tries to list all users (should fail with 403)
    response_list_fail = await client.get("/api/v1/users", headers=resident_headers)
    assert response_list_fail.status_code == 403
    
    # 2. Admin lists all users
    response_list = await client.get("/api/v1/users", headers=admin_headers)
    assert response_list.status_code == 200
    users = response_list.json()
    assert len(users) > 0
    
    # Find Amit Kumar (resident@cohabitat.com)
    resident_user = next(u for u in users if u["email"] == "resident@cohabitat.com")
    resident_id = resident_user["id"]
    
    # 3. Admin updates Amit's role to admin
    response_update = await client.put(
        f"/api/v1/users/{resident_id}",
        headers=admin_headers,
        json={"role": "admin"}
    )
    assert response_update.status_code == 200
    updated_user = response_update.json()
    assert updated_user["role"] == "admin"


@pytest.mark.asyncio
async def test_notices_crud_flow(client):
    admin_headers = await get_auth_headers(client, "admin@cohabitat.com")
    resident_headers = await get_auth_headers(client, "resident@cohabitat.com")
    
    # 1. Create a notice
    response_create = await client.post(
        "/api/v1/notices",
        headers=admin_headers,
        json={
            "title": "Initial Notice",
            "content": "This is the content",
            "type": "general"
        }
    )
    assert response_create.status_code == 201
    notice = response_create.json()
    notice_id = notice["id"]
    
    # 2. Resident tries to edit notice (should fail 403)
    response_edit_fail = await client.put(
        f"/api/v1/notices/{notice_id}",
        headers=resident_headers,
        json={"title": "Resident Edit"}
    )
    assert response_edit_fail.status_code == 403
    
    # 3. Admin edits notice
    response_edit = await client.put(
        f"/api/v1/notices/{notice_id}",
        headers=admin_headers,
        json={"title": "Updated Notice Title", "content": "Updated content"}
    )
    assert response_edit.status_code == 200
    updated = response_edit.json()
    assert updated["title"] == "Updated Notice Title"
    
    # 4. Resident tries to delete (should fail 403)
    response_delete_fail = await client.delete(
        f"/api/v1/notices/{notice_id}",
        headers=resident_headers
    )
    assert response_delete_fail.status_code == 403
    
    # 5. Admin deletes notice
    response_delete = await client.delete(
        f"/api/v1/notices/{notice_id}",
        headers=admin_headers
    )
    assert response_delete.status_code == 204
    
    # 6. Fetching it should fail 404
    response_get = await client.get(f"/api/v1/notices/{notice_id}", headers=admin_headers)
    assert response_get.status_code == 404


@pytest.mark.asyncio
async def test_family_member_flow(client):
    resident_headers = await get_auth_headers(client, "resident@cohabitat.com")
    
    # 1. List family members (should be empty initially)
    response_list = await client.get("/api/v1/users/me/family", headers=resident_headers)
    assert response_list.status_code == 200
    assert len(response_list.json()) == 0
    
    # 2. Add family member
    response_add = await client.post(
        "/api/v1/users/me/family",
        headers=resident_headers,
        json={
            "name": "Wife Jane",
            "relation": "Spouse",
            "phone": "+91 99999 88888"
        }
    )
    assert response_add.status_code == 201
    member = response_add.json()
    assert member["name"] == "Wife Jane"
    assert member["relation"] == "Spouse"
    member_id = member["id"]
    
    # 3. List family members again (should have 1 item)
    response_list2 = await client.get("/api/v1/users/me/family", headers=resident_headers)
    assert response_list2.status_code == 200
    assert len(response_list2.json()) == 1
    assert response_list2.json()[0]["name"] == "Wife Jane"
    
    # 4. Update family member details
    response_update = await client.put(
        f"/api/v1/users/me/family/{member_id}",
        headers=resident_headers,
        json={
            "name": "Jane Doe",
            "relation": "Spouse",
            "phone": "+91 99999 77777"
        }
    )
    assert response_update.status_code == 200
    assert response_update.json()["name"] == "Jane Doe"
    assert response_update.json()["phone"] == "+91 99999 77777"
    
    # 5. Delete family member
    response_delete = await client.delete(
        f"/api/v1/users/me/family/{member_id}",
        headers=resident_headers
    )
    assert response_delete.status_code == 204
    
    # 6. List family members should be empty again
    response_list3 = await client.get("/api/v1/users/me/family", headers=resident_headers)
    assert response_list3.status_code == 200
    assert len(response_list3.json()) == 0


