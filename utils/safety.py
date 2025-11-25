"""
author: Lan_zhijiang
date: 2024/06/27 
desc: 内容安全控制
issues:
    #34
"""

# logging
from app.libs.logs import top_logger
logger = top_logger.getChild('SafetyUtil')

# exceptions
from app.libs.exceptions import UnavailableForLegalReasons

# libs
from app.libs.weixin import msg_sec_check, access_token

# manager
from app.managers.account import AccountManager


def check_plain_content(content: str, account_id: str = None, weixin_openid: str = None) -> bool:

    """
    检查文本内容是否合法

    :param account_id: 账号id
    :param weixin_openid: 如果提供了account_id，可以不提供这个参数
    :param content: 文本内容 内容为空自动通过
    
    :return True合法，不合法则抛出 UnavailableForLegalReasons
    """
    logger.info("Check plain content safety")

    if not content:
        # '' or None
        return True

    # 1. 获取账号的weixin_openid
    if weixin_openid is None:
        weixin_openid = AccountManager.get_wxmp_openid(account_id)

    # 2. 调用微信的内容安全检查接口
    result = msg_sec_check(
        content, access_token=access_token, openid=weixin_openid
    )

    # 3. 校验
    if result:
        # pass
        return True
    else:
        # fail
        raise UnavailableForLegalReasons("Content is not safe, %s" % content)


def check_partner_request_content(pr_content: dict, account_id: str):

    logger.info("Check partner request content safety")

    # [title]
    check_plain_content(pr_content["title"], account_id)
    # [introduction]
    check_plain_content(pr_content["introduction"], account_id)
