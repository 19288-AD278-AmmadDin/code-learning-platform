from fastapi import FastAPI
from .routers import users, auth, courses, sections, lessons, enrollments, quizzes, quiz_attempts, course_ratings, certificates

app = FastAPI()

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