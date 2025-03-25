from sqlalchemy import Column, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True)
    title = Column(Text, nullable=False)
    author = Column(Text, nullable=False)
    chapters = relationship("Chapter", back_populates="book")

class Chapter(Base):
    __tablename__ = "chapters"

    id = Column(Integer, primary_key=True)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    title = Column(Text, nullable=False)
    chapter_no = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    book = relationship("Book", back_populates="chapters") 