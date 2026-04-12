from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from app.deps import get_db, get_current_user
from app.models import User, FollowRequest

router = APIRouter(prefix="/network", tags=["Network"])


# --- SCHEMAS ---
class FollowResponse(BaseModel):
    status: str
    message: str


class UserNetworkDto(BaseModel):
    request_id: int
    user_id: int
    username: str


# --- 1. SEND FOLLOW REQUEST ---
@router.post("/follow/{target_username}", response_model=FollowResponse)
def send_follow_request(target_username: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    target = db.query(User).filter(User.username == target_username, User.status == "ACTIVE").first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found.")

    if target.id == user.id:
        raise HTTPException(status_code=400, detail="You cannot follow yourself.")

    # Check if a request already exists
    existing = db.query(FollowRequest).filter(
        FollowRequest.follower_id == user.id,
        FollowRequest.target_id == target.id
    ).first()

    if existing:
        return {"status": "info", "message": f"Request already {existing.status.lower()}."}

    new_request = FollowRequest(follower_id=user.id, target_id=target.id, status="PENDING")
    db.add(new_request)
    db.commit()

    return {"status": "success", "message": f"Follow request sent to {target.username}."}


# --- 2. GET PENDING REQUESTS (People who want to follow me) ---
@router.get("/requests/pending")
def get_pending_requests(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    pending = db.query(FollowRequest, User).join(User, FollowRequest.follower_id == User.id) \
        .filter(FollowRequest.target_id == user.id, FollowRequest.status == "PENDING").all()

    # FIX: r and u are already the raw objects, no need to call .FollowRequest or .User
    return [{"request_id": r.id, "user_id": u.id, "username": u.username} for r, u in pending]


# --- 3. ACCEPT / REJECT REQUEST ---
@router.post("/requests/{request_id}/{action}", response_model=FollowResponse)
def resolve_request(request_id: int, action: str, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    if action not in ["accept", "reject"]:
        raise HTTPException(status_code=400, detail="Invalid action. Use 'accept' or 'reject'.")

    req = db.query(FollowRequest).filter(FollowRequest.id == request_id, FollowRequest.target_id == user.id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Follow request not found.")

    if action == "accept":
        req.status = "ACCEPTED"
        msg = "Request accepted."
    else:
        db.delete(req)  # If rejected, we just delete it so they can try again later if needed
        msg = "Request rejected."

    db.commit()
    return {"status": "success", "message": msg}


# --- 4. GET MY APPROVED NETWORK (People I can share with) ---
@router.get("/connections")
def get_approved_connections(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Returns users that the current user is following OR who are following the current user."""

    # 1. People I sent a request to (who accepted)
    following = db.query(User).join(FollowRequest, FollowRequest.target_id == User.id) \
        .filter(FollowRequest.follower_id == user.id, FollowRequest.status == "ACCEPTED").all()

    # 2. People who sent a request to me (that I accepted)
    followers = db.query(User).join(FollowRequest, FollowRequest.follower_id == User.id) \
        .filter(FollowRequest.target_id == user.id, FollowRequest.status == "ACCEPTED").all()

    # Combine both lists and remove any duplicates automatically using a dictionary
    unique_connections = {u.id: u.username for u in (following + followers)}

    return [{"user_id": uid, "username": uname} for uid, uname in unique_connections.items()]