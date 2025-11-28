# author: Lan_zhijiang
# date: 2024/06/04
# desc: Label(Tag) Schema
# issues:
#   #21
# references:
#   https://app.apifox.com/link/project/4406548/apis/schema-98704908

from typing import List
from pydantic import BaseModel


class Label(BaseModel):
    """Label model."""
    id: str | None = None
    content: str | None = None
    color: str | None = None

    def serialize(self) -> str:
        return "%s" % (self.content)


LabelRef = str


class Labels(BaseModel):
    """Labels collection model."""
    root: List[LabelRef]

    def __iter__(self):
        return iter(self.root)


LabelsDefault = []


class LabelsDetail(BaseModel):
    """Labels detail model."""
    root: List[Label]


LabelsDetailDefault = []
