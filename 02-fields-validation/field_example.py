from pydantic import BaseModel # typ: ignore
from typing import Optional, Dict, List

class Cart(BaseModel):
    user_id: int
    itmes: List[str] = []
    quantities: Dict[str, int]

class BlogPost(BaseModel):
    title: str
    content: str
    image_url: Optional[str] = None
