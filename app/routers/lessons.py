# ── Lesson ──────────────────────────────────────────────────────────────
# class LessonCreate(BaseModel):
#     title: str = Field(..., min_length=3)
#     content_type: str
#     content: str = Field(..., alias="content_text")
#     order_index: int = 0
#     duration_minutes: int = 20
#     section_id: int
#
# class LessonResponse(BaseModel):
#     id: int
#     title: str
#     content_type: str
#     content: str = Field(..., alias="content_text")
#     order_index: int
#     duration_minutes: int
#     section_id: int
#     has_quiz: bool = False
#     model_config = ConfigDict(from_attributes=True, populate_by_name=True)

