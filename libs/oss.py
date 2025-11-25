"""
author: Lan_zhijiang
date: 2024-08-18
desc: Object Storage Service related
issues: 
    #55
references: 

todos:
    1. 进一步处理更加具体的错误类型，转化为系统内部的错误类型
"""

# typing
from enum import Enum
from typing import List, Optional
from supabase import Client as SupabaseSyncClient
from storage3.utils import StorageException

# logger
from app.libs.logs import top_logger as logging
logger = logging.getChild('ObjectStorageService')

# supabase
from app.libs.supabase import supabase_serv

# exceptions
from app.libs.exceptions import NotFound, ServerException

# json
import json


''' Schemas and Defintions '''
class BucketName(Enum):
    def __str__(self) -> str:
        return self._value_

    PDF = "pdf"
    IMAGE = "image"

class ContentType(Enum):
    def __str__(self) -> str:
        return self._value_

    PDF = "application/pdf"
    PNG = "image/png"
    JPEG = "image/jpeg"


''' Supabase Storage Service '''
class SupabaseStorage:

    def __init__(self, supabase_client: SupabaseSyncClient):
        self.supabase = supabase_client

    def upload(
            self, bucket: BucketName | str, key: str, content: bytes, 
            content_type: List[ContentType | str], upsert: bool = False
        ) -> dict:

        """
        上传文件到 Supabase 存储
        
        :param bucket: 存储桶名称
        :param key: 文件在存储中的路径，如 "images/1.jpg"
        :param content: 文件内容 
        :param content_type: 文件类型，MIME TYPES \n
            https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/MIME_types/Common_types
        :param upsert: 覆盖同名文件，supabaseClient会转为x-upsert

        :return: dict 'Id'： 文件id, 'Key'：文件路径（包括桶）
        """
        logger.info(f"Upload file to {bucket} with key {key}")

        try:
            res = self.supabase.storage.from_(str(bucket)).upload(
                path=key,
                file=content,
                file_options={
                    "content-type": ",".join([str(i) for i in content_type]),
                    "upsert": str(upsert).lower()
                }
            )
        except Exception as e:
            raise ServerException(500, f"Failed to upload to Supabase Storage {e}", logger=logger)
        else:
            return res.json()

    def download(self, bucket: BucketName, key: str) -> bytes:

        """
        从 Supabase 存储下载文件
        
        :param bucket: 存储桶名称
        :param key: 文件在存储中的路径

        :return: 文件内容（字节）
        """
        logger.info(f"Download file {key} from {bucket}")

        try:
            result = self.supabase.storage.from_(str(bucket)).download(key)
        except StorageException as e:
            if e.args[0]["error"] == "not_found":
                raise NotFound("supabase storage file", (("eq", (bucket, key))), logger=logger)
            raise
        except Exception as e:
            raise ServerException(500, f"Failed to download {key} from Supabase Storage {e}", logger=logger)
        else:
            return result

    def delete(self, bucket: BucketName, *keys: List[str]) -> dict:

        """
        从 Supabase 存储中删除文件
        
        :param bucket: 存储桶名称
        :param keys: 文件在存储中的路径

        :return: dict
        """
        logger.info(f"Delete files {keys} from {bucket}")

        try:
            result = self.supabase.storage.from_(str(bucket)).remove(keys)
        except Exception as e:
            raise ServerException(500, f"Failed to delete {keys} from Supabase Storage {e}", logger=logger)
        else:
            return result.json()


supabase_serv_storage = SupabaseStorage(supabase_serv)
