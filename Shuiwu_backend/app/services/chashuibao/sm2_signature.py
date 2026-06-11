"""
查税宝 SM2 签名工具
与 Java demo 实现保持一致

支持两种私钥格式：
1. 十六进制字符串（64字符）
2. PKCS8 PEM 格式（Base64编码，与Java demo一致）
"""
import urllib.parse
import base64
from typing import Dict, Any, Optional
from gmssl import sm2, func
import re


class ChashuibaoSignature:
    """查税宝 SM2 签名工具类"""

    # SM2 私钥（需要从配置或环境变量获取）
    _private_key: Optional[str] = None

    @classmethod
    def set_private_key(cls, private_key: str):
        """设置 SM2 私钥

        Args:
            private_key: SM2 私钥，支持两种格式：
                        - 十六进制字符串（64字符）
                        - PKCS8 PEM 格式（Base64编码，与Java demo一致）
        """
        # 自动检测私钥格式
        key = private_key.strip()

        # 检查是否是十六进制格式（只有十六进制字符）
        if re.match(r'^[0-9a-fA-F]+$', key):
            # 十六进制格式，直接使用
            cls._private_key = key
        else:
            # 尝试解析为 PKCS8 PEM 格式（与 Java demo 一致）
            cls._private_key = cls._parse_pkcs8_private_key(key)

    @classmethod
    def _parse_pkcs8_private_key(cls, private_key_pem: str) -> str:
        """解析 PKCS8 PEM 格式的私钥，提取十六进制私钥

        与 Java demo 的 PrivateKey generatePrivateKey 方法对应

        Args:
            private_key_pem: PEM 格式或 Base64 编码的私钥

        Returns:
            十六进制格式的私钥（64字符）
        """
        # 清理 PEM 格式
        pem_clean = private_key_pem.strip()
        pem_clean = re.sub(r'-----BEGIN[^-]+-----', '', pem_clean)
        pem_clean = re.sub(r'-----END[^-]+-----', '', pem_clean)
        pem_clean = pem_clean.replace('\n', '').replace('\r', '').strip()

        try:
            # Base64 解码
            der_bytes = base64.b64decode(pem_clean)
            der_hex = der_bytes.hex()

            # PKCS8 私钥结构:
            # SEQUENCE {
            #   INTEGER 0 (version)
            #   SEQUENCE {  # AlgorithmIdentifier
            #     OBJECT IDENTIFIER ecPublicKey
            #     OBJECT IDENTIFIER SM2/prime256v1
            #   }
            #   OCTET STRING {  # EC 私钥
            #     SEQUENCE {
            #       INTEGER 1
            #       OCTET STRING {  # 32字节私钥 (64个十六进制字符)
            #         ...
            #       }
            #       [1] { ... }  # 可选的公钥
            #     }
            #   }
            # }

            # 查找 04 20 模式（OCTET STRING with 32 bytes）
            # 这是 SM2/ECDSA 私钥的标准格式
            octet_string_pos = der_hex.find('0420')
            if octet_string_pos != -1:
                # 找到 04 20，提取后面的 64 个十六进制字符（32 字节）
                private_key_hex = der_hex[octet_string_pos + 4:octet_string_pos + 4 + 64]
                return private_key_hex

            # 查找 04 81 20 模式（OCTET STRING with long form length, 32 bytes）
            octet_string_pos = der_hex.find('048120')
            if octet_string_pos != -1:
                private_key_hex = der_hex[octet_string_pos + 6:octet_string_pos + 6 + 64]
                return private_key_hex

            # 查找 04 82 00 20 模式（OCTET STRING with very long form length, 32 bytes）
            octet_string_pos = der_hex.find('04820020')
            if octet_string_pos != -1:
                private_key_hex = der_hex[octet_string_pos + 8:octet_string_pos + 8 + 64]
                return private_key_hex

            # 如果都没找到，尝试从头开始查找 AlgorithmIdentifier 后的第一个 OCTET STRING
            # PKCS8 私钥的 AlgorithmIdentifier 通常以 30 13 或 30 12 开头
            # 查找 AlgorithmIdentifier SEQUENCE 后面紧跟的 OCTET STRING

            # 跳过 SEQUENCE header
            pos = 0
            if der_hex.startswith('3082'):
                pos = 4  # 30 82 [2字节长度]
            elif der_hex.startswith('3081'):
                pos = 3  # 30 81 [1字节长度]
            elif der_hex.startswith('30'):
                pos = 2  # 30 [1字节长度]
            else:
                raise ValueError("无效的 PKCS8 格式：不是 SEQUENCE")

            # 跳过 version (INTEGER 0)
            if der_hex[pos:pos+2] == '02':
                pos += 2
                version_length = int(der_hex[pos:pos+2], 16)
                pos += 2 + version_length * 2

            # 跳过 AlgorithmIdentifier SEQUENCE
            if der_hex[pos:pos+2] == '30':
                pos += 2
                alg_id_length = int(der_hex[pos:pos+2], 16)
                pos += 2
                # 跳过 AlgorithmIdentifier 内容
                pos += alg_id_length * 2

            # 现在应该指向 OCTET STRING
            if der_hex[pos:pos+2] == '04':
                pos += 2
                # 读取长度
                length_byte = int(der_hex[pos:pos+2], 16)
                pos += 2

                if length_byte == 0x20:
                    # 32 字节 = 64 个十六进制字符
                    private_key_hex = der_hex[pos:pos+64]
                    return private_key_hex
                else:
                    # 尝试读取
                    return der_hex[pos:pos + length_byte * 2]

            raise ValueError("无法在 PKCS8 中找到私钥 OCTET STRING")

        except Exception as e:
            raise ValueError(f"无法解析 PKCS8 私钥: {e}")

    @classmethod
    def get_private_key(cls) -> str:
        """获取 SM2 私钥

        Returns:
            SM2 私钥

        Raises:
            ValueError: 私钥未设置
        """
        if cls._private_key is None:
            # 尝试从环境变量获取
            import os
            cls._private_key = os.getenv('CHASHUIBAO_PRIVATE_KEY')
            if not cls._private_key:
                raise ValueError(
                    "SM2 私钥未设置。请通过 set_private_key() 设置 "
                    "或配置环境变量 CHASHUIBAO_PRIVATE_KEY"
                )
        return cls._private_key

    @classmethod
    def build_sign_string(cls, params: Dict[str, Any], exclude_fields: list = None) -> str:
        """构建待签名字符串（与 Java demo 的 getSignCheckContent 逻辑一致）

        Args:
            params: 参数字典
            exclude_fields: 排除的字段列表（默认排除 sign 和 sign_type）

        Returns:
            待签名字符串
        """
        if exclude_fields is None:
            exclude_fields = ['sign', 'sign_type']  # 与 Java demo 一致

        # 过滤排除的字段（不过滤空值，与 Java demo 一致）
        filtered_params = {
            k: v for k, v in params.items()
            if k not in exclude_fields
        }

        # 按键名的字母顺序排序（与 Java demo 的 Collections.sort(keys) 一致）
        sorted_params = sorted(filtered_params.items(), key=lambda x: x[0])

        # 组合成 参数=参数值 的格式，用 & 连接
        # 与 Java demo: content.append((i == 0 ? "" : "&") + key + "=" + value)
        param_pairs = [f"{k}={v}" for k, v in sorted_params]
        sign_string = '&'.join(param_pairs)

        return sign_string

    @classmethod
    def sign(cls, params: Dict[str, Any], exclude_fields: list = None) -> str:
        """使用 SM2 对参数进行签名（与 Java demo 的 sign1 方法逻辑一致）

        Args:
            params: 参数字典
            exclude_fields: 排除的字段列表

        Returns:
            签名结果（Base64 编码，与 Java demo 一致）
        """
        # 构建待签名字符串
        sign_string = cls.build_sign_string(params, exclude_fields)

        # 获取私钥
        private_key = cls.get_private_key()

        # 创建 SM2 对象
        # mode=0 表示 C1C2C3 模式（默认）
        sm2_crypt = sm2.CryptSM2(
            private_key=private_key,
            public_key='',  # 签名只需要私钥
            mode=0  # 0=C1C2C3, 1=C1C3C2
        )

        # 进行签名
        # 随机数用于签名的 k 值
        import random
        random_hex = bytes([random.randint(1, 255) for _ in range(32)]).hex()
        # sign() 方法返回十六进制字符串
        signature_hex = sm2_crypt.sign(sign_string.encode('utf-8'), random_hex)

        # 转换为 Base64 编码（与 Java demo 的 Base64Utils.encode 一致）
        signature_bytes = bytes.fromhex(signature_hex)
        signature_base64 = base64.b64encode(signature_bytes).decode('utf-8')

        return signature_base64

    @classmethod
    def verify(cls, params: Dict[str, Any], signature: str, public_key: str) -> bool:
        """使用 SM2 公钥验签

        Args:
            params: 参数字典
            signature: 签名（Base64 编码）
            public_key: SM2 公钥

        Returns:
            验签是否成功
        """
        # 构建待签名字符串
        sign_string = cls.build_sign_string(params, ['sign', 'sign_type'])

        # 创建 SM2 对象
        sm2_crypt = sm2.CryptSM2(
            private_key='',  # 验签只需要公钥
            public_key=public_key,
            mode=0  # 0=C1C2C3, 1=C1C3C2
        )

        # 将 Base64 签名转换为十六进制字符串
        signature_bytes = base64.b64decode(signature)
        signature_hex = signature_bytes.hex()

        # 进行验签 (verify 方法参数顺序: Sign, data)
        result = sm2_crypt.verify(signature_hex, sign_string.encode('utf-8'))

        return result

    @classmethod
    def encrypt_field(cls, plaintext: str, public_key: str) -> str:
        """使用 SM2 公钥加密字段

        Args:
            plaintext: 明文
            public_key: SM2 公钥（支持 PEM 格式或十六进制格式）

        Returns:
            密文（Base64 编码）
        """
        # 自动检测公钥格式并转换
        public_key_hex = cls._parse_public_key(public_key)

        # 创建 SM2 对象
        sm2_crypt = sm2.CryptSM2(
            private_key='',
            public_key=public_key_hex,
            mode=0  # 0=C1C2C3, 1=C1C3C2
        )

        # 加密 (需要 bytes 类型)
        ciphertext = sm2_crypt.encrypt(plaintext.encode('utf-8'))

        # Base64 编码
        return base64.b64encode(ciphertext).decode('utf-8')

    @classmethod
    def _parse_public_key(cls, public_key: str) -> str:
        """解析公钥，支持 PEM 格式和十六进制格式

        Args:
            public_key: 公钥（PEM 格式或十六进制格式）

        Returns:
            十六进制格式的公钥（包含 04 前缀）
        """
        key = public_key.strip()

        # 检查是否是十六进制格式
        if re.match(r'^[0-9a-fA-F]+$', key):
            # 十六进制格式，添加 04 前缀（如果需要）
            if not key.startswith('04'):
                return '04' + key
            return key
        else:
            # PEM 格式，需要转换为十六进制
            return cls._parse_pem_public_key(key)

    @classmethod
    def _parse_pem_public_key(cls, public_key_pem: str) -> str:
        """解析 PEM 格式的公钥，提取十六进制公钥

        Args:
            public_key_pem: PEM 格式或 Base64 编码的公钥

        Returns:
            十六进制格式的公钥（包含 04 前缀）
        """
        # 清理 PEM 格式
        pem_clean = public_key_pem.strip()
        pem_clean = re.sub(r'-----BEGIN[^-]+-----', '', pem_clean)
        pem_clean = re.sub(r'-----END[^-]+-----', '', pem_clean)
        pem_clean = pem_clean.replace('\n', '').replace('\r', '').strip()

        try:
            # Base64 解码
            der_bytes = base64.b64decode(pem_clean)

            # 直接在字节中查找 BIT STRING (tag 0x03)
            # SM2 公钥通常在 BIT STRING 中，格式为 04 + X(32字节) + Y(32字节)
            for i in range(len(der_bytes) - 1):
                if der_bytes[i] == 0x03:  # BIT STRING tag
                    length = der_bytes[i + 1]
                    # 跳过 unused bits (1 字节)
                    content_start = i + 3
                    if content_start + 65 <= len(der_bytes):
                        bit_string_content = der_bytes[content_start:content_start + 65]
                        if bit_string_content[0] == 0x04:  # 未压缩格式标记
                            # 返回完整的 04 + X + Y 格式
                            return bit_string_content.hex()

            raise ValueError("无法在 PEM 中找到 SM2 公钥")

        except Exception as e:
            raise ValueError(f"无法解析 PEM 公钥: {e}")

    @classmethod
    def decrypt_field(cls, ciphertext: str) -> str:
        """使用 SM2 私钥解密字段

        Args:
            ciphertext: 密文（Base64 编码）

        Returns:
            明文
        """
        # 获取私钥
        private_key = cls.get_private_key()

        # 创建 SM2 对象
        sm2_crypt = sm2.CryptSM2(
            private_key=private_key,
            public_key='',
            mode=0  # 0=C1C2C3, 1=C1C3C2
        )

        # Base64 解码
        ciphertext_bytes = base64.b64decode(ciphertext)

        # 解密
        plaintext = sm2_crypt.decrypt(ciphertext_bytes)

        return plaintext

    @classmethod
    def build_url_with_signature(cls, base_url: str, params: Dict[str, Any]) -> str:
        """构建带签名的 URL（用于 GET 请求）

        Args:
            base_url: 基础 URL
            params: 参数字典

        Returns:
            完整的 URL（包含签名）
        """
        # 生成签名
        signature = cls.sign(params)

        # 添加 sign 参数
        params_with_sign = {**params, 'sign': signature}

        # 构建 URL 查询字符串
        query_string = '&'.join([f"{k}={urllib.parse.quote(str(v))}" for k, v in params_with_sign.items()])

        return f"{base_url}?{query_string}"
