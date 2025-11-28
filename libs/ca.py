"""
author: Lan_zhijiang
date: 2024-08-16
desc: Certificate Authority library
issues: 
    #48
references: 

"""

# typing
from typing import Optional, Tuple

# logger
from app.libs.logs import top_logger as logging
logger = logging.getChild('CA')

# cryptography
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from asn1crypto import keys, x509 as asn1_x509

# utils
from datetime import datetime, timezone, timedelta
import time
import base64

# setting
from app.libs.settings import settings

# supabase
from app.libs.postgresql import supabase_serv_db


class CA:

    """
    @other
    统一采用DER编码, PCKS8格式，与pyhanko的要求一致
    """

    def __init__(
            self, pub_key_b: bytes, pri_key_b: bytes,
            name_oid: dict, paraphrase: Optional[str] = None,
            schema: str = "ca", table: str = "certificate"
        ) -> None:
        
        """
        @param cert_pem: 根证书
        @param key_pem: 根证书密钥
        @param name_oid: 
        @param schema: 数据库schema
        @param table: 数据库表名
        """
        # self.cert = x509.load_pem_x509_certificate(pub_key_b)
        self._pub_key_b = pub_key_b
        self.cert = x509.load_der_x509_certificate(pub_key_b)
        self._pri_key_b = pri_key_b
        # self._pri_key = serialization.load_pem_private_key(pri_key_b, paraphrase)
        self._pri_key = serialization.load_der_private_key(pri_key_b, paraphrase)
        
        self.name_oid = name_oid
        
        self._schema = schema
        self._table = table

    @property
    def pub_key(self) -> bytes:
        return self.cert.public_key()
    
    @property
    def pri_key(self) -> bytes:
        return self._pri_key
    
    @property
    def pub_key_b(self) -> bytes:
        return self._pub_key_b
    
    @property
    def pri_key_b(self) -> bytes:
        return self._pri_key_b
    
    @classmethod
    def load_certificate_from_fs(self, pub_key_path: str, pri_key_path: str):

        """
        从文件系统加载证书

        Returns
        -------
        pub_key, pri_key: Tuple[bytes, bytes]
        """
        logger.info(f"Loading certificate from {pub_key_path} and {pri_key_path}")

        try:
            with open(pub_key_path, 'rb') as cert_file:
                cert_pem = cert_file.read()
            
            with open(pri_key_path, 'rb') as key_file:
                key_pem = key_file.read()
            
            # Load the certificate to get its serial number
            # cert = x509.load_pem_x509_certificate(cert_pem)
            # self.issued_certs[cert.serial_number] = cert
            
            return cert_pem, key_pem
        except FileNotFoundError:
            logger.error(f"Certificate or key not found")
            return None, None
        
    @classmethod
    def load_certificate_from_bytes(
        cls, pub_key_b: bytes, pri_key_b: bytes, paraphrase: Optional[str] = None
    ) -> Tuple[asn1_x509.Certificate, keys.PrivateKeyInfo]:

        """
        从二进制加载证书公钥、私钥
        匹配pyhanko对公钥、私钥的格式要求

        Parameters
        ----------
        pub_key_b : bytes
            公钥，必须是PEM格式
        pri_key_b : bytes
            私钥，必须是PEM格式

        Returns
        -------
        pub_key, pri_key : Tuple[asn1_x509.Certificate, asn1_x509.keys.PrivateKeyInfo]
        """

        logger.info(f"Loading certificate from bytes")


        pri_key = keys.PrivateKeyInfo.load(pri_key_b,
            # serialization.load_der_private_key(pri_key_b, paraphrase).private_bytes(
            #     encoding=serialization.Encoding.DER,
            #     format=serialization.PrivateFormat.PKCS8,
            #     encryption_algorithm=serialization.NoEncryption()
            # )
        )
        pub_key = asn1_x509.Certificate.load(pub_key_b,
            # serialization.load_der_public_key(pub_key_b).public_bytes(
            #     encoding=serialization.Encoding.DER,
            #     format=serialization.PublicFormat.SubjectPublicKeyInfo
            # )
        )
        # pem_info = pem.unarmor(pub_key_b)
        # if pem_info[0] is None or pem_info[0].lower() == 'certificate':
        #     
        # else:
        #     pass

        return pub_key, pri_key
    
    def load_certificate_from_db(self, account_id: str) -> Tuple[bytes, bytes, float, float, bool]:

        """
        从数据库中获取（用户）证书

        Docs
        ----
        https://git.hadream.ltd/anana/backend/main/-/wikis/Design/Database#schemaca

        Returns
        -------
        pub_key, pri_key, issued_at, expired_at, revoked : Tuple[bytes, bytes, float, float, bool]
        """
        logger.info(f"Load account {account_id}'s certificate from db")

        # get from db
        res = supabase_serv_db.fetch(
            self._table, filters=(('eq', ('_id', account_id)),), 
            logger=logger, schema=self._schema
        )[0]

        return \
            base64.b64decode(res["public_key"].encode("utf-8")), \
            base64.b64decode(res["private_key"].encode("utf-8")), \
            res["issued_at"], res["expired_at"], res["revoked"]

    def store_certificate_to_db(
            self, account_id: str, 
            pub_key_b: bytes, pri_key_b: bytes,
            issued_at: float, expired_at: float
        ) -> dict:

        """
        存储（用户）证书到数据库

        Implementation
        --------------
        使用base64编码存储

        Usage
        -----
        Issue, renew an account's certificate

        Parameters
        ----------
        issued_at : float
            发行时间，暂不支持通过pub,pri计算得到
        expired_at : float
            过期时间，暂不支持通过pub,pri计算得到

        Docs
        ----
        https://git.hadream.ltd/anana/backend/main/-/wikis/Design/Database#schemaca

        Returns
        -------
        存储结果 : dict
        """
        logger.info(f"Store account {account_id}'s certificate to db")

        # prepare data
        to_upsert = {
            "_id": account_id,
            "private_key": base64.b64encode(pri_key_b).decode('utf-8'),
            "public_key": base64.b64encode(pub_key_b).decode('utf-8'),
            "revoked": False,
            "issued_at": issued_at,  
            "expired_at": expired_at
        }

        # upsert to db
        return supabase_serv_db.upsert(self._table, to_upsert, logger=logger, schema=self._schema)[0]

    
    def issue_certificate(
            self,
            common_name: str, email: str,
            days_valid=30,
            key_size=2048, public_exponent=65537
        ) -> Tuple[bytes, bytes, float, float]:

        """
        签发证书

        使用UTC+0时区

        Returns
        -------
        cert_pem, key_pem, issued_at, expired_at : Tuple[bytes, bytes, float, float]
        """
        logger.info(f"Issuing certificate for {common_name}")

        pri_key = rsa.generate_private_key(
            public_exponent=public_exponent,
            key_size=key_size
        )

        subject = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, self.name_oid["country_name"]),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, self.name_oid["state_or_province_name"]),
            x509.NameAttribute(NameOID.LOCALITY_NAME, self.name_oid["locality_name"]),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, self.name_oid["organization_name"]),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
            x509.NameAttribute(NameOID.EMAIL_ADDRESS, email),
        ])

        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            self.cert.subject
        ).public_key(
            pri_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.now(timezone.utc)
        ).not_valid_after(
            datetime.now(timezone.utc) + timedelta(days=days_valid)
        ).add_extension(
            x509.BasicConstraints(ca=False, path_length=None), critical=True
        ).sign(self._pri_key, hashes.SHA256())

        pub_key_b = cert.public_bytes(serialization.Encoding.DER)
        pri_key_b = pri_key.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        return pub_key_b, pri_key_b, time.time(), time.time() + days_valid * 24 * 60 * 60

    def revoke_certificate(self, account_id: str):

        """
        吊销证书

        目前暂不支持通过serial_number吊销证书

        Implementation
        --------------
        设置表中的revoked为True

        Returns
        -------
        table:certificate's row : dict
        """
        logger.info(f"Revoke account {account_id}'s certificate")

        # prepare data
        to_update = {
            "revoked": True
        }

        return supabase_serv_db.update(
            self._table, to_update, filters=(('eq', ('_id', account_id)),), logger=logger, schema=self._schema
        )[0]

    def is_certificate_valid(self, account_id: str) -> Tuple[bool, bool, bytes, bytes]:
        
        """
        检查证书是否有效

        Returns
        -------
        expired, revoked, pub_key, pri_key : Tuple[bool, bool, bytes, bytes]
        """
        logger.info(f"Check account {account_id}'s certificate validity")

        pub_key, pri_key, _, expired_at, revoked = self.load_certificate_from_db(account_id)

        return time.time() > expired_at, revoked, pub_key, pri_key


root_pub_key, root_pri_key = CA.load_certificate_from_fs(
    settings.contract["ca"]["root_pub_key_fp"],
    settings.contract["ca"]["root_pri_key_fp"]
)
ca_root = CA(
    name_oid=settings.contract["ca"]["name_oid"],
    pub_key_b=root_pub_key, pri_key_b=root_pri_key
)
