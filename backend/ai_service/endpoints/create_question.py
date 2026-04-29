from fastapi import APIRouter, HTTPException
from utils.questions_generator import generate_question

router = APIRouter()

@router.get("/create_question")
async def create_question(schema: str, complexity: str):
    try:
        res = await generate_question(schema, complexity)
        return res
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
