from sqlalchemy import Column, Integer, String, Text, ForeignKey, Table
from sqlalchemy.orm import relationship
from ..database import Base

# Association table for scene-characters many-to-many relationship
scene_characters = Table(
    'scene_characters',
    Base.metadata,
    Column('scene_id', Integer, ForeignKey('scenes.id')),
    Column('character_id', Integer, ForeignKey('characters.id'))
)

class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    author = Column(String)
    chapters = relationship("Chapter", back_populates="book")

class Chapter(Base):
    __tablename__ = "chapters"

    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, ForeignKey("books.id"))
    title = Column(String, index=True)
    chapter_no = Column(Integer)
    content = Column(Text)
    book = relationship("Book", back_populates="chapters")
    scenes = relationship("Scene", back_populates="chapter")

class Character(Base):
    __tablename__ = "characters"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(Text)
    book_id = Column(Integer, ForeignKey("books.id"))
    scenes = relationship("Scene", secondary=scene_characters, back_populates="characters")

class Scene(Base):
    __tablename__ = "scenes"

    id = Column(Integer, primary_key=True, index=True)
    scene_number = Column(Integer)
    title = Column(String, index=True)
    chapter_id = Column(Integer, ForeignKey("chapters.id"))
    content = Column(Text)
    chapter = relationship("Chapter", back_populates="scenes")
    characters = relationship("Character", secondary=scene_characters, back_populates="scenes") 