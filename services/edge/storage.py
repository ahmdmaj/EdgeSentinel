import json
import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///./outbox.db"

# Create SQLAlchemy engine for SQLite
# check_same_thread=False is needed in SQLite to allow multiple threads to use the same connection if required
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String, unique=True, index=True, nullable=False)
    payload = Column(Text, nullable=False)  # JSON string
    status = Column(String, default="PENDING", nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

# Initialize the database (creates tables if they don't exist)
Base.metadata.create_all(bind=engine)

def save_event_to_outbox(event_id: str, payload: dict):
    """
    Save an event to the local SQLite outbox database.
    """
    session = SessionLocal()
    try:
        payload_str = json.dumps(payload)
        new_event = OutboxEvent(
            event_id=event_id,
            payload=payload_str,
            status="PENDING"
        )
        session.add(new_event)
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"Error saving to outbox: {e}")
    finally:
        session.close()
