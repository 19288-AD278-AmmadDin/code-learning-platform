from __future__ import annotations
from datetime import datetime
from typing import List
from .database import Base
from sqlalchemy import (
    String, Boolean, ForeignKey, TIMESTAMP, text, func,
    UniqueConstraint, CheckConstraint, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )

# ----------------------------------------------------------------------------- USERS MODEL

class User(Base, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = (Index("ix_users_email", "email"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    password: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)  # student | instructor | admin
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"), nullable=False)
    courses: Mapped[List["Course"]] = relationship(back_populates="instructor", lazy="selectin")
    enrollments: Mapped[List["Enrollment"]] = relationship(back_populates="user", lazy="selectin")

# ----------------------------------------------------------------------------- COURSES MODEL

class Course(Base, TimestampMixin):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    level: Mapped[str] = mapped_column(String, nullable=False)  # beginner | intermediate | advanced
    published: Mapped[bool] = mapped_column(Boolean, server_default=text("true"), nullable=False)
    instructor_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    instructor: Mapped["User"] = relationship(back_populates="courses")
    sections: Mapped[List["Section"]] = relationship(back_populates="course", cascade="all, delete-orphan")
    enrollments: Mapped[List["Enrollment"]] = relationship(back_populates="course", lazy="selectin")

# ----------------------------------------------------------------------------- SECTION MODEL

class Section(Base, TimestampMixin):
    __tablename__ = "sections"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    order_index: Mapped[int] = mapped_column(server_default=text("0"), nullable=False)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    course: Mapped["Course"] = relationship(back_populates="sections")
    lessons: Mapped[List["Lesson"]] = relationship(back_populates="section", cascade="all, delete-orphan", order_by="Lesson.order_index")

# ----------------------------------------------------------------------------- LESSON MODEL

class Lesson(Base, TimestampMixin):
    __tablename__ = "lessons"
    __table_args__ = (Index("ix_lessons_section_order", "section_id", "order_index"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    content_type: Mapped[str] = mapped_column(String, nullable=False)  # text | video | document | quiz ...
    content_text: Mapped[str] = mapped_column(String, nullable=False)  # or JSONB later
    order_index: Mapped[int] = mapped_column(server_default=text("0"), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(server_default=text("20"), nullable=False)  # renamed for clarity
    section_id: Mapped[int] = mapped_column(ForeignKey("sections.id", ondelete="CASCADE"), nullable=False, index=True)
    section: Mapped["Section"] = relationship(back_populates="lessons")
    quiz: Mapped["Quiz | None"] = relationship(back_populates="lesson", uselist=False)

# ----------------------------------------------------------------------------- ENROLLMENT MODEL

class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (
        UniqueConstraint("user_id", "course_id", name="uq_enrollment_user_course"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    enrolled_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    user: Mapped["User"] = relationship(back_populates="enrollments")
    course: Mapped["Course"] = relationship(back_populates="enrollments")

# ----------------------------------------------------------------------------- LESSON PROGRESS MODEL

class LessonProgress(Base):
    __tablename__ = "lesson_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "lesson_id", name="uq_progress_user_lesson"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, index=True)

# ----------------------------------------------------------------------------- QUIZ MODEL

class Quiz(Base, TimestampMixin):
    __tablename__ = "quizzes"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    passing_score: Mapped[int] = mapped_column(server_default=text("0"), nullable=False)  # usually 0–100
    lesson_id: Mapped[int] = mapped_column(
        ForeignKey("lessons.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )
    lesson: Mapped["Lesson"] = relationship(back_populates="quiz")
    questions: Mapped[List["Question"]] = relationship(back_populates="quiz", cascade="all, delete-orphan")
    attempts: Mapped[List["QuizAttempt"]] = relationship(back_populates="quiz", lazy="selectin")

# ----------------------------------------------------------------------------- QUESTION MODEL

class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    question_text: Mapped[str] = mapped_column(String, nullable=False)
    question_type: Mapped[str] = mapped_column(String, nullable=False, server_default=text("'single_choice'"))  # single_choice | multiple_choice | true_false | short_answer

    quiz_id: Mapped[int] = mapped_column(ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)

    quiz: Mapped["Quiz"] = relationship(back_populates="questions")
    answers: Mapped[List["Answer"]] = relationship(back_populates="question", cascade="all, delete-orphan")

# ----------------------------------------------------------------------------- ANSWER MODEL

class Answer(Base):
    __tablename__ = "answers"

    id: Mapped[int] = mapped_column(primary_key=True)
    answer_text: Mapped[str] = mapped_column(String, nullable=False)  # renamed
    is_correct: Mapped[bool] = mapped_column(server_default=text("false"), nullable=False)

    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)

    question: Mapped["Question"] = relationship(back_populates="answers")

# ----------------------------------------------------------------------------- QUIZ ATTEMPT MODEL

class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"
    __table_args__ = (
        UniqueConstraint("user_id", "quiz_id", name="uq_attempt_user_quiz"),
        CheckConstraint("score BETWEEN 0 AND 100"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    score: Mapped[int] = mapped_column(nullable=False, server_default=text("0"))
    submitted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    quiz_id: Mapped[int] = mapped_column(ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False)

    user: Mapped["User"] = relationship()
    quiz: Mapped["Quiz"] = relationship(back_populates="attempts")

# ----------------------------------------------------------------------------- COURSE RATING MODEL

class CourseRating(Base):
    __tablename__ = "course_ratings"
    __table_args__ = (
        UniqueConstraint("user_id", "course_id", name="uq_rating_user_course"),
        CheckConstraint("rating BETWEEN 1 AND 5"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    rating: Mapped[int] = mapped_column(nullable=False)
    comment: Mapped[str | None] = mapped_column(String, server_default="", nullable=True)  # renamed

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False
    )

# ----------------------------------------------------------------------------- CERTIFICATE MODEL

class Certificate(Base):
    __tablename__ = "certificates"
    __table_args__ = (
        UniqueConstraint("user_id", "course_id", name="uq_certificate_user_course"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False
    )