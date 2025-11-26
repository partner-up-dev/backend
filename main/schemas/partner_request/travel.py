"""旅游搭子请求数据模型"""

from pydantic import BaseModel


class TravelPRContent(BaseModel):
    """旅游搭子请求特有内容"""
    id: int


class TravelPartnerRequest(TravelPRContent):
    """旅游搭子请求"""
    type: str = "travel"
