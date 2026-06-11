"""文件名编码处理工具函数

用于处理从 HTTP multipart/form-data 上传的文件名编码问题。
中文文件名在上传时可能被浏览器/客户端编码，需要解码后存储。
"""
import urllib.parse
from typing import Optional
from email.message import Message
from email import message_from_string


def decode_filename(filename: Optional[str]) -> Optional[str]:
    """解码可能被编码的文件名

    支持以下编码格式：
    1. URL 编码（Percent encoding）: %E4%B8%AD%E6%96%87.docx
    2. RFC 2231 编码: utf-8''%E4%B8%AD%E6%96%87.docx
    3. RFC 2047 编码: =?utf-8?B?5Lit5paHLmRvY3g=?=

    Args:
        filename: 原始文件名字符串

    Returns:
        解码后的文件名，如果无法解码则返回原文件名
    """
    if not filename:
        return filename

    try:
        # 尝试 URL 解码（处理 %E4%B8%AD%E6%96%87 这样的编码）
        if '%' in filename:
            decoded = urllib.parse.unquote(filename)
            if decoded != filename:
                # 验证解码结果是否包含有效字符
                try:
                    decoded.encode('utf-8').decode('utf-8')
                    return decoded
                except (UnicodeEncodeError, UnicodeDecodeError):
                    pass

        # 尝试 RFC 2231 解码（处理 utf-8''%E4%B8%AD%E6%96%87 这样的编码）
        if "''" in filename:
            try:
                # 格式: charset''url-encoded-text
                parts = filename.split("''", 1)
                if len(parts) == 2:
                    charset = parts[0]
                    encoded_text = parts[1]
                    # URL 解码
                    decoded = urllib.parse.unquote(encoded_text)
                    # 尝试使用指定的字符集解码
                    decoded.encode('iso-8859-1').decode(charset)
                    return decoded
            except (UnicodeDecodeError, LookupError):
                pass

        # 尝试 RFC 2047 解码（处理 =?utf-8?B?...?= 这样的编码）
        if filename.startswith('=?') and filename.endswith('?='):
            try:
                # 构造一个简单的邮件消息来解析
                msg = message_from_string(f'Content-Disposition: attachment; filename="{filename}"')
                decoded = msg.get_filename()
                if decoded and decoded != filename:
                    return decoded
            except Exception:
                pass

    except Exception:
        # 如果所有解码方法都失败，返回原始文件名
        pass

    return filename


def safe_filename(filename: Optional[str]) -> Optional[str]:
    """获取安全的文件名

    对文件名进行解码，并确保其合法性。

    Args:
        filename: 原始文件名

    Returns:
        解码后的安全文件名
    """
    if not filename:
        return filename

    # 解码文件名
    decoded = decode_filename(filename)

    # 可以在此添加其他安全性检查
    # 例如：移除危险字符、限制长度等

    return decoded
