# author: Lan_zhijiang
# date: 2024/06/04
# desc: Label(Tag) Schema
# issues:
#   #21
# references: 
#   https://app.apifox.com/link/project/4406548/apis/schema-98704908

# typing
from typing import Any, Union, List, Callable
from pydantic import RootModel, field
from app.schemas import BaseSchema


class Label(BaseSchema):
    
    id: Union[str, None] = field(default=None, alias="_id", serialization_alias="_id")
    content: Union[str, None] = None
    color: Union[str, None] = None

    def serialize(self) -> str:
        return "%s" % (self.content)
    
    @classmethod
    def from_schema(cls, schema: 'LabelRef') -> 'Label':
        return cls.from_id(schema)
    
    @classmethod
    def from_id(cls, label_id: str) -> 'Label':
        from app.managers.label import LabelManager
        return LabelManager.fetch_data_by_id(label_id)

class LabelRef(RootModel):
    root: str

    def deref(self) -> 'Label':
        return Label.from_id(self.root)

class Labels(RootModel):

    root: List[
        # order as weight
        LabelRef  
    ]

    def deref(self) -> 'LabelsDetail':
        
        return [Label.from_id(label_ref.root) for label_ref in self.root]

# class Labels(list):

#     def __init__(self, value: LabelsType):
#         self.value = value

#     @classmethod
#     def __get_pydantic_core_schema__(cls, source_type: Any, handler: Any) -> CoreSchema:
#         def validate(value: Any) -> 'Labels':
#             if isinstance(value, Labels):
#                 return value
#             if not isinstance(value, list) or not all(isinstance(item, LabelRef) for item in value):
#                 raise ValueError("Value must be a list of LabelRef(str)")
#             return Labels(value)
        
#         return core_schema.no_info_after_validator_function(
#             function=validate,
#             schema=handler(LabelsType),
#             serialization=core_schema.plain_serializer_function_ser_schema(
#                 lambda labels: labels.value
#             )
#         )

#     def __iter__(self):
#         return iter(self.value)

#     def __repr__(self):
#         return repr(self.value)

#     def __eq__(self, other):
#         if isinstance(other, Labels):
#             return self.value == other.value
#         return self.value == other 

LabelsDefault = []

class LabelsDetail(RootModel):
    root: List [
        Label
    ]

    @classmethod
    def from_schema(cls, schema: Labels) -> 'LabelsDetail':
        from app.managers.label import LabelManager
        return cls(root=[LabelManager(label_id=label_ref).schema for label_ref in schema.root])

LabelsDetailDefault = []
