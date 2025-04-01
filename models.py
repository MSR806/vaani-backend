from sqlalchemy import Column, Integer, Text, ForeignKey, String, Table
from sqlalchemy.orm import relationship
from database import Base

class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True)
    title = Column(Text, nullable=False)
    author = Column(Text, nullable=False)
    cover_url = Column(Text, nullable=True)  # URL to the generated book cover
    chapters = relationship("Chapter", back_populates="book")
    characters = relationship("Character", back_populates="book")

class Chapter(Base):
    __tablename__ = "chapters"

    id = Column(Integer, primary_key=True)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    title = Column(Text, nullable=False)
    chapter_no = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    book = relationship("Book", back_populates="chapters")
    scenes = relationship("Scene", back_populates="chapter")

class Character(Base):
    __tablename__ = "characters"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String)
    book_id = Column(Integer, ForeignKey("books.id"))

    book = relationship("Book", back_populates="characters")

# Association table for scene-character many-to-many relationship
scene_characters = Table(
    'scene_characters',
    Base.metadata,
    Column('scene_id', Integer, ForeignKey('scenes.id')),
    Column('character_id', Integer, ForeignKey('characters.id'))
)

class Scene(Base):
    __tablename__ = "scenes"

    id = Column(Integer, primary_key=True, index=True)
    scene_number = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=False)
    content = Column(Text, nullable=False)
    
    # Relationships
    chapter = relationship("Chapter", back_populates="scenes")
    characters = relationship("Character", secondary=scene_characters, backref="scenes") 