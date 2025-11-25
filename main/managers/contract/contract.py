"""
author: Lan_zhijiang
date: 2024/06/10
desc: Module Contract's Manager
issues:
    #22 #47
"""

# typing
from copy import deepcopy
from app.managers import BaseManager
from typing import Dict, List, Literal

# logging
from app.libs.logs import top_logger as logging
from app.schemas.partner_request.common import PartnerRequest
logger = logging.getChild("ContractManager")

# schemas
from app.schemas.contract.display import ContractSimpleDisplay
from app.schemas.contract import Contract, ContractMetadata, ContractContent, ContractStatus
from app.schemas.contract.clause import Clause
from app.schemas.partner_request import PartnerRequestType, PartnerRequestContentId

# manager
from app.managers.clause import ClauseManager
from app.managers.account import AccountManager

# exceptions
from app.libs.exceptions import NotFound, Forbidden, ServerException, DuplicateOrConflict

# db
from app.libs.postgresql import supabase_serv_db

# setting
from app.libs.settings import settings
contract_py_settings = settings.contract_py

# libs
from app.libs.ca import ca_root
from app.libs import pdf


class ContractManager(BaseManager):

    _table = "contract"

    def __init__(self, contract_id: int | None = None, **data) -> None:

        if contract_id:
            data = self.fetch_data_by_id(contract_id)

        self._schema = Contract(**data)
        self._simple_display = ContractSimpleDisplay(
            _id=self._schema.id, status=self._schema.status
        )

        self._parties: List[str] | None = None
        self._file_key: str = "contract/%s.pdf" % self._schema.id
        self._partner_request_primary_type: PartnerRequestType | None = None

    @property
    def simple_display(self) -> ContractSimpleDisplay:
        return self._simple_display
    
    @property
    def schema(self) -> Contract:
        return self._schema
    
    @property
    def _id(self) -> int:
        return self.schema.id
    
    @property
    def status(self) -> ContractStatus:
        return self.schema.status
    
    @property
    def parties(self) -> List[str]:
        """
        契约当事人列表

        即搭子请求的搭子列表
        """

        if self._parties:
            return self._parties

        from app.managers.partner_request.base import BasePRManager
        parties = BasePRManager.fetch_data_by_id(
            self.schema.partner_request, "partners"
        )["partners"]
        return parties
    
    @property
    def partner_request_primary_type(self) -> PartnerRequestType:
        """
        搭子请求主类型
        """
        if self._partner_request_primary_type:
            return self._partner_request_primary_type
        
        from app.managers.partner_request.base import BasePRManager
        primary_type = PartnerRequestType(BasePRManager.fetch_data_by_id(
            self.schema.partner_request, "type"
        )["type"][0])
        return primary_type
    
    @property
    def file_key(self) -> str:
        """
        契约书面文件 的 OSS Key
        """
        return self._file_key
    
    @file_key.setter
    def file_key(self, new_key: str) -> None:
        self._file_key = new_key

    def is_signed(self, account_id: str) -> bool:
        """
        是否已经签名
        """
        return account_id in self.schema.signature_state
    
    @property
    def signed(self) -> bool:
        """
        是否已经(完全)签署
        """
        return self.schema.status == ContractStatus.SIGNED

    @classmethod
    def fetch_data_by_id(cls, contract_id: int, *fields) -> dict:

        logger.info("Fetch contract's %s by _id %s", fields, contract_id)

        fetch_result = supabase_serv_db.fetch(cls._table, columns=fields, filters=[("eq", ("_id", contract_id))], logger=logger)
        return fetch_result[0]
    
    @classmethod
    def get_simple_display_by_id(cls, contract_id: int) -> ContractSimpleDisplay:

        """
        Get ContractSimpleDisplay by _id
        """
        logger.info("Get contract simple display by _id %s", contract_id)
        fetch_result = cls.fetch_data_by_id(contract_id, "_id", "status")
        
        contract_data = fetch_result[0]
        return ContractSimpleDisplay(**contract_data)
    
    @classmethod
    def create(cls, partner_request: PartnerRequest) -> 'ContractManager':

        """
        创建契约

        Usage
        -----
        一般用于搭子请求发布时
        
        Parameters
        ----------
        partner_request
            传入PartnerRequest获得搭子请求id, type以创建契约

        Description
        -----------
        不包含创建契约合同文件

        :return ContractManager
        """
        logger.info("Create contract for partner_request %s", partner_request.id)

        # construct schema
        contract = Contract(
            _id=0, partner_request=partner_request.id,
            clauses=cls.create_content(partner_request).clauses
        )
        contract_data = contract.json(exclude_fields=["id"])

        # insert to db
        insert_result = supabase_serv_db.insert(cls._table, contract_data, logger=logger)

        contract_manager = cls(**insert_result)

        # update inner state
        contract_manager._partner_request_primary_type = partner_request.pri_type

        # create manager
        return contract_manager

    @classmethod
    def create_content(cls, partner_request: PartnerRequest) -> ContractContent:

        """
        创建契约内容

        :desc
            根据搭子请求主类型获得条款预设模板列表
            分别调用ClauseManager.create创建条款

        :param partner_request

        :return ContractContent
        """
        pr_pri_type = partner_request.pri_type
        logger.info("Create contract content of pr_type %s", pr_pri_type)

        # [clauses]
        try:
            clauses_preset: Dict[PartnerRequestContentId, Clause] = contract_py_settings["preset"]["clauses"][pr_pri_type](partner_request)
        except KeyError:
            e = NotFound("No contract content preset found for type %s" % pr_pri_type)
            logger.fatal(e, exc_info=True)
            raise e
        else:
            # insert to db
            clauses: Dict[PartnerRequestContentId, int] = {}
            for content_id, clause in clauses_preset.items():
                clause_manager = ClauseManager.create(clause)
                clauses[content_id] = clause_manager.schema.id

        # return content
        return ContractContent(clauses=clauses)

    def update_signature_state(self, account_id: str | None, reset: bool = False) -> None:

        """
        更新签名状态
        会引起契约状态的变化

        Implementation
        --------------
        0. 校验
            0.1 是否已经签名，是则直接返回
        1. 更新数据
            1.1 更新signature_state
            1.2 更新status
        2. 更新到数据库
        """
        if reset:
            logger.info("Reset signature state of contract %s", self.id)
        else:
            logger.info("Update signature state of contract %s, account %s", self.id, account_id)

        if not reset:
            # 0. validate
            # 0.1 is duplicated
            if self.is_signed(account_id):
                logger.warning("Account %s has signed contract %s", account_id, self.id)
                return

            # 1. update local
            self.schema.signature_state.append(account_id)
            self.schema.status = ContractStatus.SIGNING  # 嗯？怎么这里开始是动态推导了？是Annotated导致的吗？
            if len(self.schema.signature_state) == len(self.parties):
                self.schema.status = ContractStatus.SIGNED
        else:
            self.schema.signature_state = []
            self.schema.status = ContractStatus.PENDING

        # 2. update to db
        to_update = {
            "signature_state": self.schema.signature_state,
            "status": self.schema.status.value
        }
        try:
            supabase_serv_db.update(
                self._table, to_update, filters=[("eq", ("_id", self.id))], logger=logger
            )
        except Exception:
            # rollback
            self.schema.signature_state.remove(account_id)
            if len(self.schema.signature_state) == 0:
                self.schema.status = ContractStatus.PENDING
            if self.schema.status == ContractStatus.SIGNED:
                self.schema.status = ContractStatus.SIGNING
            
            raise ServerException("Failed to update signature state of contract %s" % self.id, logger=logger)

    async def export_legal_document(self) -> str:

        """
        导出法律书面文件到OSS

        异步
        """
        logger.info("Export legal document for contract %s to OSS", self.id)

        legal_document_pdf = await self.generate_legal_document()
        return pdf.store_pdf_to_oss(legal_document_pdf, self.file_key)

    async def generate_legal_document(self) -> bytes:

        """
        生成法律书面文件（PDF）

        Implementation
        --------------
        1 通过生成器生成基础PDF
        2 添加签名域（"root"固定为根证书签名域）

        Returns
        -------
        bytes : PDF Binary Content
        """
        logger.info("Generate legal document for contract %s", self.id)

        # 1
        parties: List[Dict[Literal["uuid", "name", "id", "contact"], str]] = []
        for party in self.parties:
            account_info = AccountManager.fetch_data_by_id(party, "_id", "nickname", "email")
            parties.append({
                "uuid": account_info["_id"],
                "name": account_info["nickname"],
                "contact": account_info["email"],
                "id": None
            })

        legal_document_pdf: bytes = contract_py_settings["pdf_template"]["contract"][
            self.partner_request_primary_type
        ](
            contract=self.schema,
            parties=parties
        )

        # 2
        legal_document_pdf = pdf.add_signature_fields(legal_document_pdf, [*self.parties, "root"])

        return legal_document_pdf

    async def sign(
            self, 
            account_id: str, 
            realname: str,
            email: str,
            update_signature_state: bool = True
        ) -> str:

        """
        契约签名

        Metadata
        --------
        :issues: #48
        :docs: https://git.hadream.ltd/anana/gitlab-profile/-/wikis/Design/Contract#%E7%AD%BE%E5%90%8D
        
        Parameters
        ----------
        account_id : str
            签名用户的ID
        realname : str
            签名用户的真实姓名
        email : str
            签名用户的邮箱
            未来可能用作传送签名后的书面文件
        update_signature_state : bool
            是否更新signature_state

        Implementation
        --------------
        0. 校验
            0.1 状态为pending, singing
            0.2 是否为契约当事人
            0.3 是否已经签名
        1. 调取证书
            1.1 如果没有/过期，则签发
            1.2 如果被吊销，则抛出错误
        2. 从对象存储中获取上一份签名过的文件（PDF）
            2.1 如果没有，则生成新的
                2.1.1 通过生成器生成
                2.1.2 添加签名域（"root"固定为根证书签名域）
        3. 使用证书为文件（PDF）签名
            3.1 签名
            3.2 存储到对象存储中
        4. 更新signature_state (如果需要)

        Exceptions
        ----------
        Forbidden
            证书被吊销；不是契约当事人

        Returns
        -------
        签名后的文件OSS Key (With Bucket)
        """
        logger.info("Sign contract %s by account %s", self.id, account_id)

        # 0.
        # 0.1
        if self.status not in [ContractStatus.PENDING, ContractStatus.SIGNING]:
            raise DuplicateOrConflict('contract signature', self.id, "status is %s" % self.status, logger=logger)
        # 0.2
        if account_id not in self.parties:
            logger.error("Account %s is not contract %s's party", account_id, self.id)
            raise Forbidden("You are not the party of contract %s" % self.id)
        # 0.3
        if self.is_signed(account_id):
            logger.warning("Account %s has signed contract %s", account_id, self.id)
            return self.file_key

        # 1. 
        try:
            expired, revoked, pub_key_b, pri_key_b = ca_root.is_certificate_valid(account_id)
            if revoked:
                # 1.2
                raise Forbidden("Certificate of account %s is revoked" % account_id, logger=logger)
            if expired:
                raise NotFound("Certificate of account %s is expired" % account_id, logger=logger)
        except NotFound:
            # 1.1
            pub_key_b, pri_key_b, issued_at, expired_at = ca_root.issue_certificate(
                common_name=realname, email=email
            )
            ca_root.store_certificate_to_db(account_id, pub_key_b, pri_key_b, issued_at, expired_at)

        # 2.
        try:
            last_pdf: bytes = pdf.load_pdf_from_oss(self.file_key)
        except NotFound:
            last_pdf: bytes = await self.generate_legal_document()
        
        # 3.
        # TODO 替换 self.file_key 为确实可以下载的URL（这个其实很难，因为URL是动态的）
        # 但可以通过给一个webpage wrapper来实现
        cert, key = ca_root.load_certificate_from_bytes(pub_key_b, pri_key_b)
        signed_pdf: bytes = await pdf.sign_pdf(
            last_pdf, account_id, 
            cert, key, 
            pdf_url=self.file_key
        )
        file_key_with_bucket = pdf.store_pdf_to_oss(signed_pdf, self.file_key)

        # 4.
        if update_signature_state:
            self.update_signature_state(account_id)

        return file_key_with_bucket

    async def sign_by_root_certificate(self) -> str:

        """
        使用根证书进行签署

        Returns
        -------
        签名后的文件OSS Key (With Bucket)
        """
        logger.info("Sign root certificate to contract %s", self.id)

        # 1. get root certificate
        root_pub_key_b, root_pri_key_b = ca_root.pub_key_b, ca_root.pri_key_b
        
        # 2. get last pdf
        last_pdf: bytes = pdf.load_pdf_from_oss(self.file_key)

        # 3. sign
        cert, key = ca_root.load_certificate_from_bytes(root_pub_key_b, root_pri_key_b)
        signed_pdf: bytes = await pdf.sign_pdf(
            last_pdf, "root", cert, key, pdf_url=self.file_key
        )

        # 3. store
        return pdf.store_pdf_to_oss(signed_pdf, self.file_key)
    
    def abrogate_and_resign(self) -> None:

        """
        毁约重签

        Usage
        -----
        通过搭子请求修改（搭子加入/退出、搭子请求修正案、直接编辑等）的钩子触发
        该钩子应该在后端启动时挂载

        Implementation
        --------------
        1. 销毁导出的文件
        2. 重置signature_state, 重置status
        3. 迁移原有签名（如果配置许可）
        4. 重新导出法律文件

        Docs
        ----
        https://git.hadream.ltd/anana/backend/main/-/work_items/49

        """
        logger.info("Abrogate and resign contract %s due to content's change", self.id)

        # 1.
        pdf.delete_pdf_from_oss(self.file_key)

        # 2.
        original_signature_state = deepcopy(self.schema.signature_state)
        self.update_signature_state(None, reset=True)

        # 3.
        # for account_id in original_signature_state:
        #     self.sign(account_id, None, None)

        # 4.
        self.export_legal_document()


