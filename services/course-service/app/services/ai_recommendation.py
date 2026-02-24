"""AI-powered course recommendations using OpenAI."""

import json
from typing import List, Optional

import httpx
from app.core.config import settings
from pydantic import BaseModel


class CourseRecommendation(BaseModel):
    """Course recommendation result."""

    course_id: int
    title: str
    reason: str
    match_score: float


class RecommendationRequest(BaseModel):
    """Request for course recommendations."""

    prompt: str
    user_interests: Optional[List[str]] = None
    max_results: int = 5


class AIRecommendationService:
    """Service for AI-powered course recommendations."""

    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.model = settings.OPENAI_MODEL
        self.api_url = "https://api.openai.com/v1/chat/completions"

    async def get_recommendations(
        self,
        prompt: str,
        available_courses: List[dict],
        user_interests: Optional[List[str]] = None,
        max_results: int = 5,
    ) -> List[CourseRecommendation]:
        """
        Get AI-powered course recommendations based on user prompt.

        Args:
            prompt: User's learning goals or interests
            available_courses: List of available courses with details
            user_interests: Optional list of user's interests
            max_results: Maximum number of recommendations

        Returns:
            List of recommended courses with reasons
        """
        if not self.api_key:
            # Fallback to simple keyword matching if no API key
            return self._fallback_recommendations(
                prompt, available_courses, max_results
            )

        # Build the system prompt
        system_prompt = self._build_system_prompt(available_courses)
        user_prompt = self._build_user_prompt(
            prompt, user_interests, max_results
        )

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        "temperature": 0.7,
                        "max_tokens": 1000,
                    },
                    timeout=30.0,
                )

                if response.status_code == 200:
                    result = response.json()
                    content = result["choices"][0]["message"]["content"]
                    return self._parse_recommendations(
                        content, available_courses
                    )
                else:
                    # Fallback on API error
                    return self._fallback_recommendations(
                        prompt, available_courses, max_results
                    )

        except Exception:
            # Fallback on any error
            return self._fallback_recommendations(
                prompt, available_courses, max_results
            )

    def _build_system_prompt(self, courses: List[dict]) -> str:
        """Build the system prompt with available courses."""
        courses_info = "\n".join(
            [
                f"- ID: {c['id']}, Title: {c['title']}, Description: {c['description'][:200]}..."
                for c in courses[:50]  # Limit to avoid token overflow
            ]
        )

        return f"""You are an AI course recommendation assistant for an online learning platform.
Your job is to recommend the most relevant courses based on the user's learning goals.

Available courses:
{courses_info}

When making recommendations:
1. Match courses to the user's stated interests and goals
2. Consider course descriptions and titles
3. Provide clear reasons for each recommendation
4. Rate each match on a scale of 0.0 to 1.0

Respond ONLY with a JSON array of recommendations in this format:
[
  {{"course_id": 1, "title": "Course Title", "reason": "Why this course matches", "match_score": 0.95}},
  ...
]
"""

    def _build_user_prompt(
        self, prompt: str, interests: Optional[List[str]], max_results: int
    ) -> str:
        """Build the user prompt."""
        interests_str = ""
        if interests:
            interests_str = f"\nMy interests: {', '.join(interests)}"

        return f"""I'm looking for courses related to: {prompt}{interests_str}

Please recommend up to {max_results} courses that best match my needs.
Respond with only the JSON array, no other text."""

    def _parse_recommendations(
        self, content: str, courses: List[dict]
    ) -> List[CourseRecommendation]:
        """Parse AI response into recommendations."""
        try:
            # Try to extract JSON from response
            content = content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]

            recommendations = json.loads(content)
            return [
                CourseRecommendation(
                    course_id=r["course_id"],
                    title=r["title"],
                    reason=r["reason"],
                    match_score=min(1.0, max(0.0, float(r["match_score"]))),
                )
                for r in recommendations
            ]
        except (json.JSONDecodeError, KeyError, ValueError):
            return []

    def _fallback_recommendations(
        self, prompt: str, courses: List[dict], max_results: int
    ) -> List[CourseRecommendation]:
        """Fallback keyword-based recommendations when AI is unavailable."""
        prompt_lower = prompt.lower()
        keywords = prompt_lower.split()

        scored_courses = []
        for course in courses:
            title_lower = course["title"].lower()
            desc_lower = course.get("description", "").lower()

            # Simple keyword matching score
            score = 0.0
            for keyword in keywords:
                if keyword in title_lower:
                    score += 0.3
                if keyword in desc_lower:
                    score += 0.1

            if score > 0:
                scored_courses.append(
                    {
                        "course": course,
                        "score": min(1.0, score),
                    }
                )

        # Sort by score and take top results
        scored_courses.sort(key=lambda x: x["score"], reverse=True)
        top_courses = scored_courses[:max_results]

        return [
            CourseRecommendation(
                course_id=c["course"]["id"],
                title=c["course"]["title"],
                reason=f"Matches your interest in: {prompt}",
                match_score=c["score"],
            )
            for c in top_courses
        ]


# Singleton instance
recommendation_service = AIRecommendationService()
