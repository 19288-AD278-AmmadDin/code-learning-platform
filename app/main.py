from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import users, auth, courses, sections, lessons, enrollments, quizzes, quiz_attempts, course_ratings, certificates

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(auth.router)
app.include_router(courses.router)
app.include_router(sections.router)
app.include_router(lessons.router)
app.include_router(enrollments.router)
app.include_router(quizzes.router)
app.include_router(quiz_attempts.router)
app.include_router(course_ratings.router)
app.include_router(certificates.router)