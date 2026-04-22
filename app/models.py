from sqlalchemy import (
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Resource(Base):
    __tablename__ = "resources"

    sha256 = Column(String(64), primary_key=True)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    base_path = Column(Text, nullable=False)
    ext = Column(Text, nullable=False)
    mime_type = Column(Text, nullable=False)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    bytes = Column(Integer, nullable=False)
    is_deleted = Column(Integer, nullable=False, default=0)

    metadata_entries = relationship("Metadata", back_populates="resource")


class Metadata(Base):
    __tablename__ = "metadata"
    __table_args__ = (
        UniqueConstraint("mkt", "date", name="uq_mkt_date"),
        Index("ix_metadata_mkt_date_hsh", "mkt", "date", "hsh"),
        Index("ix_metadata_date", "date"),
    )

    mkt = Column(Text, primary_key=True)
    date = Column(String, primary_key=True)
    sha256 = Column(
        String(64), ForeignKey("resources.sha256"), nullable=False
    )
    hsh = Column(String, nullable=False)
    title = Column(Text, nullable=True)
    copyright = Column(Text, nullable=True)
    copyrightlink = Column(Text, nullable=True)
    is_deleted = Column(Integer, nullable=False, default=0)

    resource = relationship("Resource", back_populates="metadata_entries")


class CrawlRun(Base):
    __tablename__ = "crawl_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_date = Column(Text, nullable=False, index=True)
    started_at = Column(Text, nullable=False)
    finished_at = Column(Text, nullable=True)
    status = Column(Text, nullable=False)
    success_count = Column(Integer, default=0)
    fail_count = Column(Integer, default=0)
    message = Column(Text, nullable=True)


class CrawlState(Base):
    __tablename__ = "crawl_state"

    mkt = Column(Text, primary_key=True)
    last_success_date = Column(Text, nullable=True)
    last_attempt_at = Column(Text, nullable=True)
    consecutive_failures = Column(Integer, default=0)
