from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict


# ── User ────────────────────────────────────────────────────────────────
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: str = Field(..., pattern="^(student|instructor|admin)$")

class UserBasic(BaseModel):
    id: int
    email: EmailStr
    role: str

    model_config = ConfigDict(from_attributes=True)

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    role: str
    is_active: bool
    created_at: datetime
    courses: List[CourseBasic] = []
    enrollments: List["EnrollmentResponse"] = []
    model_config = ConfigDict(from_attributes=True)


# ── Course ──────────────────────────────────────────────────────────────
class CourseCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=10)
    level: str = Field(..., pattern="^(beginner|intermediate|advanced)$")
    published: bool = True

class CourseBasic(BaseModel):
    id: int
    title: str
    level: str
    published: bool
    model_config = ConfigDict(from_attributes=True)

class CourseResponse(BaseModel):
    id: int
    title: str
    description: str
    level: str
    published: bool
    created_at: datetime
    instructor_id: int
    sections: List["SectionResponse"] = []
    enrollments_count: int
    model_config = ConfigDict(from_attributes=True)


# ── Section ─────────────────────────────────────────────────────────────
class SectionCreate(BaseModel):
    title: str = Field(..., min_length=3)
    order_index: int = 0

class SectionResponse(BaseModel):
    id: int
    title: str
    order_index: int
    course_id: int
    lessons: List["LessonResponse"] = []
    model_config = ConfigDict(from_attributes=True)

# ── Lesson ──────────────────────────────────────────────────────────────
class LessonCreate(BaseModel):
    title: str = Field(..., min_length=3)
    content_type: str
    content: str = Field(..., alias="content_text")  # rename in schema if desired
    order_index: int = 0
    duration_minutes: int = 20
    section_id: Optional[int]

class LessonResponse(BaseModel):
    id: int
    title: str
    content_type: str
    content: str = Field(..., alias="content_text")
    order_index: int
    duration_minutes: int
    section_id: int
    has_quiz: bool = False
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

# ── Quiz ────────────────────────────────────────────────────────────────
class QuizCreate(BaseModel):
    title: str
    passing_score: int = 70

class QuizResponse(BaseModel):
    id: int
    title: str
    passing_score: int
    lesson_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ── Question ─────────────────────────────────────────────────────────────
class QuestionCreate(BaseModel):
    text: str = Field(..., min_length=10, max_length=2000, alias="question_text")
    question_type: str = Field("single_choice", pattern="^(single_choice|multiple_choice)$")
    model_config = ConfigDict(populate_by_name=True)

class QuestionResponse(QuestionCreate):
    id: int
    quiz_id: int
    answers: List["AnswerResponse"] = []
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

# ── Answer ───────────────────────────────────────────────────────────────
class AnswerCreate(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000, alias="answer_text")
    is_correct: bool = False
    model_config = ConfigDict(populate_by_name=True)

class AnswerResponse(AnswerCreate):
    id: int
    question_id: int
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class AnswerStudentResponse(BaseModel):
    """Student-facing answer: hides is_correct. For single_choice (fill-in-blank) answer_text is also hidden."""
    id: int
    answer_text: str = ""
    question_id: int
    model_config = ConfigDict(from_attributes=True)


# ── Student-facing question / quiz schemas ──────────────────────────────
class QuestionStudentResponse(BaseModel):
    id: int
    question_text: str = Field(..., alias="question_text")
    question_type: str
    quiz_id: int
    # answers: List[AnswerStudentResponse] = []
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class QuizDetailStudentResponse(QuizResponse):
    """Quiz detail returned to students – no is_correct, no fill-in-blank answer text."""
    questions: List[QuestionStudentResponse] = []
    attempts_count: int = 0


# ── Quiz Attempt ─────────────────────────────────────────────────────────
class QuizAttemptSubmit(BaseModel):
    selected_answer_ids: List[int] = []
    text_answers: Optional[dict[int, str]] = None  # question_id -> typed text for fill-in-blank

class QuizAttemptResponse(BaseModel):
    id: int
    quiz_id: int
    user_id: int
    score: int
    passed: bool = False
    submitted_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)

class QuizDetailResponse(QuizResponse):
    questions: List[QuestionResponse] = []
    attempts_count: int = 0
    my_attempt: Optional["QuizAttemptResponse"] = None

# ── Enrollment ────────────────────────────────────────────────────────────────
class EnrollmentResponse(BaseModel):
    id: int
    course_id: int
    user_id: int
    enrolled_at: datetime
    completed_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

# ── Course Rating ────────────────────────────────────────────────────────────────
class CourseRatingCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: str = ""

class CourseRatingResponse(CourseRatingCreate):
    id: int
    user_id: int
    course_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ── Certificate ──────────────────────────────────────────────────────────────
class CertificateResponse(BaseModel):
    id: int
    user_id: int
    course_id: int
    issued_at: datetime
    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    id: Optional[str] | int = None