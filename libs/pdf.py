"""
author: Lan_zhijiang
date: 2024-08-16
desc: PDF related operations
issues: 
    #48
references: 
    https://www.lsbin.com/9244.html
    https://blog.51cto.com/u_16213450/9064259
    https://stackoverflow.com/questions/74555322/how-make-digital-sign-in-a-pdf-with-python
    https://docs.reportlab.com/reportlab/userguide/ch5_platypus/
    https://pyhanko.readthedocs.io/en/latest/lib-guide/sig-fields.html
    https://pyhanko.readthedocs.io/en/latest/lib-guide/signing.html

docs:

"""

# typing
from typing import List, Optional, Tuple

# logging
from app.libs.logs import top_logger as logging
logger = logging.getChild('PDF')

import io

# cryptography
from asn1crypto import x509, keys

# reportlab
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

# pyhanko
from pyhanko import stamp as pdf_stamp
from pyhanko.sign import fields as signable_fields, signers as pdf_signers
from pyhanko.pdf_utils import incremental_writer, text 
from pyhanko.pdf_utils.font import opentype
from pyhanko_certvalidator.registry import SimpleCertificateStore
CHINESE_FONT_PATH = 'app/data/fonts/SourceHanSansSC-VF.ttf'
CHINESE_FONT_TEXT_BOX_STYLE = text.TextBoxStyle(
    font=opentype.GlyphAccumulatorFactory(CHINESE_FONT_PATH)
)

# supabase
from app.libs.oss import supabase_serv_storage, BucketName, ContentType

def generate_from_list(
        content: List[str],
        variables: dict,
        doc_options: dict = {
            "pagesize": A4, 
            "rightMargin": 72, "leftMargin": 72, 
            "topMargin": 72, "bottomMargin": 18
        }
) -> bytes:
    
    """
    从字符串列表生成PDF

    Parameters
    ----------
    content : 字符串列表，使用`{}`包住变量，会被替换为variables中的值
    variables : 变量字典
    doc_options : 文档选项，参考 https://docs.reportlab.com/reportlab/userguide/ch5_platypus/#the-basedoctemplate-class

    Returns
    -------
    bytes : PDF二进制数据
    """

    output = io.BytesIO()

    doc = SimpleDocTemplate(output, )
    story = []

    for item in content:
        if isinstance(item, str):
            text = item.format(**variables)
            story.append(Paragraph(text, self.styles['Normal']))
        elif isinstance(item, dict) and item.get('type') == 'spacer':
            story.append(Spacer(1, item.get('height', 12)))

    doc.build(story)
    return output.getvalue()

async def sign_pdf(
        pdf_content: bytes, 
        signature_field_name: str,
        pub_key: x509.Certificate, pri_key: keys.PrivateKeyInfo,
        pdf_url: Optional[str]
    ) -> bytes:

    """
    数字签名PDF
    1. 盖章 (添加signature field)
    2. 签名文档

    务必在调用本函数之前，创建对应的签名域

    印章内容：QR + `Signed by: %(signer)s \nTime: %(ts)s`
    印章位置：signature_field指定

    Parameters
    ----------
    pdf_content : bytes
        PDF二进制数据
    signature_field_name : str
        签名域名称
    pub_key : x509.Certificate
        公钥
    pri_key : keys.PrivateKeyInfo
        私钥
    pdf_url : str, optional
        可下载该PDF的地址，生成为印章中的二维码

    """
    logger.info("Signing PDF to field %s" % signature_field_name)

    signer = pdf_signers.SimpleSigner(pub_key, pri_key, SimpleCertificateStore())
    meta = pdf_signers.PdfSignatureMetadata(field_name=signature_field_name)
    pdf_signer = pdf_signers.PdfSigner(
        meta, signer=signer, 
        stamp_style=pdf_stamp.QRStampStyle(
            stamp_text='Signed by: %(signer)s \nTime: %(ts)s',
            text_box_style=CHINESE_FONT_TEXT_BOX_STYLE
        )
    )

    raw = incremental_writer.IncrementalPdfFileWriter(io.BytesIO(pdf_content))
    output = io.BytesIO()
    await pdf_signer.async_sign_pdf(
        pdf_out=raw, output=output,
        appearance_text_params={'url': pdf_url}
    )
    return output.getvalue()

def add_signature_field(
        pdf_content: bytes, 
        field_name: str, 
        box: tuple = (200, 600, 400, 660),
        on_page: int = -1
    ) -> bytes:

    """
    添加签名域

    Parameters
    ----------
    pdf_content : bytes
        PDF二进制数据
    field_name : str
        签名域名称
    box : tuple, optional
        签名域位置，笛卡尔坐标系，从左下角开始
    on_page : int, optional
        签名域所在页码

    Returns
    -------
    bytes : PDF二进制数据
    """
    logger.info("Add signature field %s at page %s, %s", field_name, on_page, box)

    raw = incremental_writer.IncrementalPdfFileWriter(io.BytesIO(pdf_content))
    signable_fields.append_signature_field(
        raw, signable_fields.SigFieldSpec(
            field_name, 
            on_page=on_page,
            box=box
        )
    )

    output = io.BytesIO()
    raw.write(output)
    return output.getvalue()

def add_signature_fields(
        pdf_content: bytes, 
        field_names: List[str], on_page: int = -1,
        field_size: Tuple[int, int] = (240, 80)
    ) -> bytes:

    """
    添加多个签名域
    签名域的位置将会被自动计算

    尽可能确保所在页面是空白的

    Parameters
    ----------
    pdf_content : bytes
        PDF二进制数据
    fields : List[str]
        签名域名称列表

    Implementations
    ------------
    1. 计算签名域的位置：默认基于A4
        2列的table，从左到右，从下往上填充；
        column之间间距20
        每一个签名域的大小可以被指定，默认240(w)*80(h) 


    Returns
    -------
    bytes : PDF二进制数据
    """
    logger.info("Add signature fields %s to page %s", field_names, on_page)
    rectangle_width, rectangle_height = field_size
    rl_margin, tb_margin = 50, 50
    column_margin = 20

    for i, field_name in enumerate(field_names):
        # 计算行号和列号
        row = (i+1 - 1) // 2
        col = (i+1 - 1) % 2

        # 计算坐标
        x1 = rl_margin + col * (rectangle_width + column_margin)
        y1 = tb_margin + row * rectangle_height
        x2 = x1 + rectangle_width
        y2 = y1 + rectangle_height
        pdf_content = add_signature_field(
            pdf_content, field_name, (x1, y1, x2, y2), on_page
        )

    return pdf_content
    
def store_pdf_to_oss(pdf_content: bytes, path: str) -> str:

    """
    存储PDF到Supabase Storage

    Parameters
    ----------
    pdf_content : bytes
        PDF二进制数据
    path : str
        存储路径；会覆盖同名文件

    Returns
    -------
    str : key （包括存储桶）
    """
    logger.info("Store PDF %s to oss", path)

    return supabase_serv_storage.upload(
        BucketName.PDF,
        path, pdf_content, 
        [ContentType.PDF],
        True
    )["Key"]

def load_pdf_from_oss(path: str) -> bytes:

    """
    从Supabase Storage加载PDF

    Parameters
    ----------
    path : str
        存储路径

    Returns
    -------
    bytes : PDF二进制数据
    """
    logger.info("Load PDF %s from oss", path)

    return supabase_serv_storage.download(BucketName.PDF, path)

def delete_pdf_from_oss(path: str) -> dict:

    """
    从Supabase Storage删除PDF

    Parameters
    ----------
    path : str
        存储路径
    """
    logger.info("Delete PDF %s from oss", path)

    return supabase_serv_storage.delete(BucketName.PDF, path)
