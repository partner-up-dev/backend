"""
author: Lan_zhijiang
date: 2024-10-28
desc: 曹操出行开放平台 基础数据模型
issues: 
    #2
references: 

"""

from enum import IntEnum

class OnOff(IntEnum):

    """
    0：不可用 / 关闭 \n
    1：可用 / 开启
    """
    OFF = 0
    ON = 1

    @classmethod
    def from_bool(cls, value: bool) -> 'OnOff':
        return cls.ON if value else cls.OFF
    
    def __bool__(self) -> bool:
        return self == self.ON
