"""API endpoints for AI-powered course recommendations."""

from typing import List, Optional

from app.db.session import async_session
from app.repositories.course_repository import CourseRepository
from app.services.ai_recommendation import (
    CourseRecommendation,
    recommendation_service,
)
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


class RecommendationRequest(BaseModel):
    """Request body for getting recommendations."""

    prompt: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Describe what you want to learn",
    )
    interests: Optional[List[str]] = Field(
        None, description="List of your interests"
    )
    max_results: int = Field(
        5, ge=1, le=20, description="Maximum number of recommendations"
    )


class RecommendationResponse(BaseModel):
    """Response containing course recommendations."""

    prompt: str
    recommendations: List[CourseRecommendation]
    total: int


@router.post("/", response_model=RecommendationResponse)
async def get_recommendations(request: RecommendationRequest):
    """
    Get AI-powered course recommendations based on your learning goals.

    The AI will analyze your prompt and interests to suggest the most relevant courses.
    If OpenAI is not configured, falls back to keyword-based matching.
    """
    async with async_session() as db:
        repository = CourseRepository(db)

        # Get all published courses
        courses, _ = await repository.get_courses(
            is_published=True,
            limit=100,  # Limit for AI context
        )

        if not courses:
            raise HTTPException(
                status_code=404,
                detail="No courses available for recommendations",
            )

        # Convert to dict format for AI service
        courses_data = [
            {
                "id": course.id,
                "title": course.title,
                "description": course.description,
                "category_id": course.category_id,
                "price": float(course.price),
            }
            for course in courses
        ]

        # Get AI recommendations
        recommendations = await recommendation_service.get_recommendations(
            prompt=request.prompt,
            available_courses=courses_data,
            user_interests=request.interests,
            max_results=request.max_results,
        )

        return RecommendationResponse(
            prompt=request.prompt,
            recommendations=recommendations,
            total=len(recommendations),
        )


@router.get("/suggest", response_model=RecommendationResponse)
async def suggest_courses(
    q: str = Query(
        ...,
        min_length=3,
        max_length=500,
        description="What do you want to learn?",
    ),
    limit: int = Query(5, ge=1, le=20, description="Max recommendations"),
):
    """
    Quick course suggestions based on a search query.

    Simplified endpoint for quick suggestions without full prompt specification.
    """
    request = RecommendationRequest(prompt=q, max_results=limit)
    return await get_recommendations(request)
