"""AURA Date proof-of-concept API. Not cleared for public launch."""
import hashlib
import hmac
import os
from collections.abc import Generator
from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator
from sqlalchemy import and_, create_engine, event, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from .models import Base, Block, Conversation, Introduction, Message, Report, User
from .security import decode_token, hash_password, issue_token, password_matches, signing_secret


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    display_name: str = Field(min_length=2, max_length=70)
    age: int = Field(ge=18, le=120)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class ProfileIn(BaseModel):
    display_name: str = Field(min_length=2, max_length=70)
    bio: str = Field(default="", max_length=500)
    values: list[str] = Field(min_length=1, max_length=10)
    min_age: int = Field(ge=18, le=120)
    max_age: int = Field(ge=18, le=120)
    ready: bool = False

    @field_validator("values")
    @classmethod
    def clean_values(cls, values: list[str]) -> list[str]:
        normalized = [v.strip().lower() for v in values]
        if any(not 2 <= len(v) <= 40 for v in normalized) or len(set(normalized)) != len(normalized):
            raise ValueError("Values must be unique and each 2-40 characters")
        return normalized

    @model_validator(mode="after")
    def check_ages(self) -> "ProfileIn":
        if self.min_age > self.max_age:
            raise ValueError("min_age cannot exceed max_age")
        return self


class MessageIn(BaseModel):
    content: str = Field(min_length=1, max_length=2000)

    @field_validator("content")
    @classmethod
    def nonblank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message cannot be blank")
        return value


class ReportIn(BaseModel):
    subject_id: str
    reason: str = Field(pattern="^(harassment|spam|impersonation|safety|other)$")
    details: str = Field(default="", max_length=500)


class PublicUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    display_name: str
    age: int
    bio: str
    values: list[str]


def view_user(user: User) -> dict:
    return PublicUser.model_validate(user).model_dump()


def view_intro(intro: Introduction, other: User) -> dict:
    return {
        "id": intro.id, "day": intro.day.isoformat(), "person": view_user(other),
        "owner_accepted": intro.owner_accepts, "candidate_accepted": intro.candidate_accepts,
        "declined": intro.declined,
    }


def create_app(database_url: str | None = None) -> FastAPI:
    signing_secret()  # fail closed on insecure production configuration
    url = database_url or os.getenv("AURA_DATABASE_URL", "sqlite:///./aura-local.db")
    engine = create_engine(
        url, pool_pre_ping=True,
        connect_args={"check_same_thread": False} if url.startswith("sqlite") else {},
    )
    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def enable_foreign_keys(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    Base.metadata.create_all(bind=engine)  # local bootstrap only; migrations required before production
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    app = FastAPI(title="AURA Date API", version="0.1.0")
    app.state.engine = engine

    def database() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session

    Db = Annotated[Session, Depends(database)]

    def current_user(authorization: Annotated[str | None, Header()] = None,
                     db: Session = Depends(database)) -> User:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Authentication required")
        user_id = decode_token(authorization[7:])
        user = db.get(User, user_id) if user_id else None
        if user is None:
            raise HTTPException(status_code=401, detail="Invalid session")
        return user

    Auth = Annotated[User, Depends(current_user)]

    def permitted_intro(db: Session, intro_id: str, person: User) -> Introduction:
        intro = db.get(Introduction, intro_id)
        if intro is None or person.id not in (intro.owner_id, intro.candidate_id):
            raise HTTPException(status_code=404, detail="Introduction not found")
        return intro

    def permitted_conversation(db: Session, conv_id: str, person: User) -> tuple[Conversation, Introduction]:
        conv = db.get(Conversation, conv_id)
        intro = db.get(Introduction, conv.introduction_id) if conv else None
        if intro is None or person.id not in (intro.owner_id, intro.candidate_id):
            raise HTTPException(status_code=404, detail="Conversation not found")
        return conv, intro

    def blocked(db: Session, left: str, right: str) -> bool:
        return db.scalar(select(Block).where(or_(
            and_(Block.blocker_id == left, Block.blocked_id == right),
            and_(Block.blocker_id == right, Block.blocked_id == left),
        )).limit(1)) is not None

    def active_count(db: Session, user_id: str) -> int:
        return db.scalar(
            select(func.count()).select_from(Conversation)
            .join(Introduction, Introduction.id == Conversation.introduction_id)
            .where(Conversation.closed.is_(False),
                   or_(Introduction.owner_id == user_id, Introduction.candidate_id == user_id))
        ) or 0

    @app.get("/health/live")
    def liveness() -> dict:
        return {"status": "ok"}

    @app.post("/api/v1/auth/register", status_code=201)
    def register(data: RegisterIn, db: Db) -> dict:
        email = str(data.email).lower()
        if db.scalar(select(User.id).where(User.email == email)) is not None:
            raise HTTPException(status_code=409, detail="Email already in use")
        user = User(email=email, password_hash=hash_password(data.password),
                    display_name=data.display_name.strip(), age=data.age)
        db.add(user)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=409, detail="Email already in use")
        db.refresh(user)
        return {"access_token": issue_token(user.id), "token_type": "bearer"}

    @app.post("/api/v1/auth/token")
    def login(data: LoginIn, db: Db) -> dict:
        person = db.scalar(select(User).where(User.email == str(data.email).lower()))
        if person is None or not password_matches(data.password, person.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return {"access_token": issue_token(person.id), "token_type": "bearer"}

    @app.get("/api/v1/me")
    def me(person: Auth) -> dict:
        return {**view_user(person), "email": person.email, "ready": person.ready,
                "min_age": person.min_age, "max_age": person.max_age}

    @app.put("/api/v1/me")
    def update_profile(data: ProfileIn, person: Auth, db: Db) -> dict:
        person.display_name = data.display_name.strip()
        person.bio = data.bio
        person.values = data.values
        person.min_age = data.min_age
        person.max_age = data.max_age
        person.ready = data.ready
        db.commit()
        return {**view_user(person), "ready": person.ready}

    @app.get("/api/v1/introductions/today")
    def today(person: Auth, db: Db) -> dict:
        if not person.ready:
            raise HTTPException(status_code=409, detail="Complete your profile first")
        day = datetime.now(timezone.utc).date()
        existing = db.scalar(select(Introduction).where(
            Introduction.owner_id == person.id, Introduction.day == day))
        if existing:
            return view_intro(existing, db.get(User, existing.candidate_id))

        candidates = db.scalars(select(User).where(
            User.id != person.id, User.ready.is_(True),
            User.age >= person.min_age, User.age <= person.max_age,
            User.min_age <= person.age, User.max_age >= person.age,
        )).all()
        excluded_pairs = db.scalars(select(Introduction).where(or_(
            Introduction.owner_id == person.id, Introduction.candidate_id == person.id
        ))).all()
        seen = {i.candidate_id if i.owner_id == person.id else i.owner_id for i in excluded_pairs}
        candidates = [c for c in candidates if c.id not in seen and not blocked(db, person.id, c.id)]
        if not candidates:
            return {"id": None, "day": day.isoformat(), "person": None}

        secret = signing_secret().encode("utf-8")
        def ranking(candidate: User) -> tuple[int, str]:
            shared = len(set(person.values).intersection(candidate.values))
            tie = hmac.new(secret, f"{day}:{person.id}:{candidate.id}".encode(), hashlib.sha256).hexdigest()
            return (-shared, tie)
        best = min(candidates, key=ranking)
        intro = Introduction(owner_id=person.id, candidate_id=best.id, day=day)
        db.add(intro)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            existing = db.scalar(select(Introduction).where(
                Introduction.owner_id == person.id, Introduction.day == day))
            if existing is None:
                raise
            return view_intro(existing, db.get(User, existing.candidate_id))
        db.refresh(intro)
        return view_intro(intro, best)

    @app.get("/api/v1/introductions/inbox")
    def inbox(person: Auth, db: Db) -> list[dict]:
        items = db.scalars(select(Introduction).where(
            Introduction.candidate_id == person.id, Introduction.declined.is_(False)
        ).order_by(Introduction.day.desc()).limit(50)).all()
        return [view_intro(i, db.get(User, i.owner_id)) for i in items
                if not blocked(db, person.id, i.owner_id)]

    @app.post("/api/v1/introductions/{intro_id}/accept")
    def accept(intro_id: str, person: Auth, db: Db) -> dict:
        intro = permitted_intro(db, intro_id, person)
        other_id = intro.candidate_id if person.id == intro.owner_id else intro.owner_id
        if intro.declined or blocked(db, person.id, other_id):
            raise HTTPException(status_code=409, detail="Introduction unavailable")
        if person.id == intro.owner_id:
            intro.owner_accepts = True
        else:
            intro.candidate_accepts = True
        conversation = db.scalar(select(Conversation).where(Conversation.introduction_id == intro.id))
        if intro.owner_accepts and intro.candidate_accepts and conversation is None:
            if active_count(db, intro.owner_id) >= 3 or active_count(db, intro.candidate_id) >= 3:
                db.rollback()
                raise HTTPException(status_code=409, detail="Three active conversations maximum")
            conversation = Conversation(introduction_id=intro.id)
            db.add(conversation)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=409, detail="Concurrent update; retry")
        return {"mutual": intro.owner_accepts and intro.candidate_accepts,
                "conversation_id": conversation.id if conversation else None}

    @app.post("/api/v1/introductions/{intro_id}/decline")
    def decline(intro_id: str, person: Auth, db: Db) -> dict:
        intro = permitted_intro(db, intro_id, person)
        intro.declined = True
        conversation = db.scalar(select(Conversation).where(Conversation.introduction_id == intro.id))
        if conversation:
            conversation.closed = True
        db.commit()
        return {"declined": True}

    @app.get("/api/v1/conversations")
    def conversations(person: Auth, db: Db) -> list[dict]:
        records = db.execute(
            select(Conversation, Introduction)
            .join(Introduction, Conversation.introduction_id == Introduction.id)
            .where(Conversation.closed.is_(False), Introduction.declined.is_(False),
                   or_(Introduction.owner_id == person.id, Introduction.candidate_id == person.id))
            .order_by(Conversation.created_at.desc())
        ).all()
        return [{"id": c.id, "person": view_user(db.get(User, i.candidate_id if i.owner_id == person.id else i.owner_id))}
                for c, i in records if not blocked(db, i.owner_id, i.candidate_id)]

    @app.get("/api/v1/conversations/{conv_id}/messages")
    def messages(conv_id: str, person: Auth, db: Db) -> dict:
        conv, intro = permitted_conversation(db, conv_id, person)
        if conv.closed or intro.declined or blocked(db, intro.owner_id, intro.candidate_id):
            raise HTTPException(status_code=409, detail="Conversation closed")
        items = db.scalars(select(Message).where(Message.conversation_id == conv.id)
                           .order_by(Message.created_at, Message.id).limit(200)).all()
        meaningful = db.scalar(select(func.count()).select_from(Message).where(
            Message.conversation_id == conv.id, func.length(Message.content) >= 20)) or 0
        return {"reveal_stage": "unlocked" if meaningful >= 20 else "hidden",
                "meaningful_messages": meaningful,
                "items": [{"id": m.id, "author_id": m.author_id, "content": m.content,
                           "created_at": m.created_at.isoformat()} for m in items]}

    @app.post("/api/v1/conversations/{conv_id}/messages", status_code=201)
    def send(conv_id: str, data: MessageIn, person: Auth, db: Db) -> dict:
        conv, intro = permitted_conversation(db, conv_id, person)
        if conv.closed or intro.declined or blocked(db, intro.owner_id, intro.candidate_id):
            raise HTTPException(status_code=409, detail="Conversation closed")
        msg = Message(conversation_id=conv.id, author_id=person.id, content=data.content)
        db.add(msg)
        db.commit()
        db.refresh(msg)
        return {"id": msg.id, "content": msg.content}

    @app.post("/api/v1/conversations/{conv_id}/close")
    def close(conv_id: str, person: Auth, db: Db) -> dict:
        conv, _ = permitted_conversation(db, conv_id, person)
        conv.closed = True
        db.commit()
        return {"closed": True}

    @app.post("/api/v1/safety/blocks/{user_id}")
    def block(user_id: str, person: Auth, db: Db) -> dict:
        if person.id == user_id or db.get(User, user_id) is None:
            raise HTTPException(status_code=400, detail="Invalid target")
        if db.get(Block, (person.id, user_id)) is None:
            db.add(Block(blocker_id=person.id, blocked_id=user_id))
        introductions = db.scalars(select(Introduction).where(or_(
            and_(Introduction.owner_id == person.id, Introduction.candidate_id == user_id),
            and_(Introduction.owner_id == user_id, Introduction.candidate_id == person.id)
        ))).all()
        for intro in introductions:
            intro.declined = True
            conv = db.scalar(select(Conversation).where(Conversation.introduction_id == intro.id))
            if conv:
                conv.closed = True
        db.commit()
        return {"blocked": True}

    @app.post("/api/v1/safety/reports", status_code=201)
    def report(data: ReportIn, person: Auth, db: Db) -> dict:
        if data.subject_id == person.id or db.get(User, data.subject_id) is None:
            raise HTTPException(status_code=400, detail="Invalid target")
        db.add(Report(reporter_id=person.id, subject_id=data.subject_id,
                      reason=data.reason, details=data.details))
        db.commit()
        return {"submitted": True}

    @app.delete("/api/v1/me", status_code=204)
    def delete_account(person: Auth, db: Db) -> None:
        introductions = db.scalars(select(Introduction).where(or_(
            Introduction.owner_id == person.id, Introduction.candidate_id == person.id))).all()
        ids = [intro.id for intro in introductions]
        for intro_id in ids:
            conv = db.scalar(select(Conversation).where(Conversation.introduction_id == intro_id))
            if conv:
                # DB foreign-key ON DELETE CASCADE erases messages exactly once.
                db.delete(conv)
        for intro in introductions:
            db.delete(intro)
        for block_row in db.scalars(select(Block).where(or_(
            Block.blocker_id == person.id, Block.blocked_id == person.id))).all():
            db.delete(block_row)
        for item in db.scalars(select(Report).where(or_(
            Report.reporter_id == person.id, Report.subject_id == person.id))).all():
            db.delete(item)
        db.delete(person)
        db.commit()

    return app


app = create_app()
