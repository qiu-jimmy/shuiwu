"""
微信支付签名和验签工具
"""
import hashlib
import json
from typing import Dict, Any
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
import base64


class WechatPaySignature:
    """微信支付签名工具类"""

    @staticmethod
    def private_key_sign(
        message: str,
        private_key_path: str
    ) -> str:
        """
        使用商户私钥对消息进行签名

        Args:
            message: 待签名的消息
            private_key_path: 商户私钥文件路径

        Returns:
            Base64编码的签名
        """
        try:
            # 读取私钥
            with open(private_key_path, 'rb') as f:
                private_key = serialization.load_pem_private_key(
                    f.read(),
                    password=None,
                    backend=default_backend()
                )

            # 对消息进行SHA256哈希
            message_hash = hashlib.sha256(message.encode('utf-8')).digest()

            # 使用私钥签名
            signature = private_key.sign(
                message_hash,
                padding.PKCS1v15(),
                hashes.SHA256()
            )

            # 返回Base64编码的签名
            return base64.b64encode(signature).decode('utf-8')
        except Exception as e:
            raise Exception(f"签名失败: {str(e)}")

    @staticmethod
    def public_key_encrypt(
        plaintext: str,
        public_key_path: str
    ) -> str:
        """
        使用微信支付公钥加密敏感字段（用于上送敏感信息）

        Args:
            plaintext: 待加密的明文（如手机号、银行卡号等）
            public_key_path: 微信支付公钥文件路径

        Returns:
            Base64编码的密文

        Raises:
            Exception: 加密失败时抛出异常

        Note:
            微信支付 API v3 要求使用 RSA OAEP with SHA-1AndMGF1Padding
            加密后的数据长度不能超过 344 字节（Base64编码后）
            因此明文长度不能超过 214 字节（RSA 2048 位密钥）
        """
        try:
            from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
            from cryptography.hazmat.primitives import hashes

            # 读取公钥
            with open(public_key_path, 'rb') as f:
                public_key = serialization.load_pem_public_key(
                    f.read(),
                    backend=default_backend()
                )

            # 检查明文长度（RSA 2048位密钥使用OAEP加密，明文最大214字节）
            if len(plaintext.encode('utf-8')) > 214:
                raise ValueError(f"明文长度超过限制（214字节），当前: {len(plaintext.encode('utf-8'))}字节")

            # 使用 RSA OAEP with SHA-1AndMGF1Padding 加密
            # 对应微信支付官方文档的加密要求
            ciphertext = public_key.encrypt(
                plaintext.encode('utf-8'),
                asym_padding.OAEP(
                    mgf=asym_padding.MGF1(algorithm=hashes.SHA1()),
                    algorithm=hashes.SHA1(),
                    label=None
                )
            )

            # 返回Base64编码的密文
            return base64.b64encode(ciphertext).decode('utf-8')

        except FileNotFoundError:
            raise Exception(f"公钥文件不存在: {public_key_path}")
        except ValueError as e:
            raise Exception(f"加密参数错误: {str(e)}")
        except Exception as e:
            raise Exception(f"加密失败: {str(e)}")

    @staticmethod
    def public_key_verify(
        message: str,
        signature: str,
        public_key_path: str
    ) -> bool:
        """
        使用微信支付平台证书验签（支持 X.509 证书和纯公钥格式）

        Args:
            message: 原始消息
            signature: Base64编码的签名
            public_key_path: 微信支付平台证书路径

        Returns:
            验签是否成功
        """
        try:
            # 读取证书/公钥文件
            with open(public_key_path, 'rb') as f:
                cert_data = f.read()

            # 尝试加载为 X.509 证书（微信支付平台证书格式）
            public_key = None
            try:
                from cryptography import x509
                cert = x509.load_pem_x509_certificate(cert_data, default_backend())
                public_key = cert.public_key()
                print(f"[DEBUG] 成功加载 X.509 证书，序列号: {format(cert.serial_number, 'X')}")
            except Exception:
                # 如果不是证书，尝试直接加载公钥
                public_key = serialization.load_pem_public_key(cert_data, backend=default_backend())
                print(f"[DEBUG] 加载纯公钥格式")

            # 解码签名
            signature_bytes = base64.b64decode(signature)

            # 使用公钥验签（微信支付 API v3 使用 RSA/SHA256/RSASSA-PKCS1-v1_5）
            public_key.verify(
                signature_bytes,
                message.encode('utf-8'),
                padding.PKCS1v15(),
                hashes.SHA256()
            )

            return True
        except FileNotFoundError:
            print(f"验签失败: 证书/公钥文件不存在 - {public_key_path}")
        except ValueError as e:
            print(f"验签失败: 签名/证书格式错误 - {str(e)}")
        except Exception as e:
            print(f"验签失败: {str(e)}")
        return False

    @staticmethod
    def build_signature_message(
        http_method: str,
        url: str,
        timestamp: str,
        nonce_str: str,
        body: str = ""
    ) -> str:
        """
        构建待签名的消息

        Args:
            http_method: HTTP请求方法（GET/POST）
            url: 请求URL（不包含域名）
            timestamp: 时间戳
            nonce_str: 随机字符串
            body: 请求体（GET请求为空）

        Returns:
            待签名的消息字符串
        """
        # 拼接规则：请求方法 + \n + URL + \n + 时间戳 + \n + 随机串 + \n + 请求体
        message = f"{http_method}\n{url}\n{timestamp}\n{nonce_str}\n{body}\n"
        return message

    @staticmethod
    def build_param_signature(params: Dict[str, Any]) -> str:
        """
        构建参数签名字符串（用于回调验签）

        Args:
            params: 参数字典

        Returns:
            按照规则拼接的字符串
        """
        # 过滤空值并按参数名ASCII码从小到大排序
        filtered_params = {k: v for k, v in params.items() if v is not None and v != ''}
        sorted_params = sorted(filtered_params.items())

        # 拼接成键值对字符串
        param_str = '&'.join([f"{k}={v}" for k, v in sorted_params])
        return param_str

    @staticmethod
    def get_cert_serial_no(private_key_path: str) -> str:
        """
        从商户私钥证书中提取序列号

        Args:
            private_key_path: 商户私钥文件路径

        Returns:
            证书序列号
        """
        try:
            from cryptography import x509

            with open(private_key_path, 'rb') as f:
                cert = x509.load_pem_x509_certificate(f.read(), default_backend())

            # 获取证书序列号并转为16进制大写
            serial_no = format(cert.serial_number, 'X')
            return serial_no
        except Exception as e:
            # 如果私钥文件不包含证书，返回配置中的序列号
            import os
            return os.getenv('WECHAT_PAY_CERT_SERIAL_NO', '')

    @staticmethod
    def hmac_sha256_sign(message: str, key: str) -> str:
        """
        HMAC-SHA256签名（用于API v3之前的版本）

        Args:
            message: 待签名消息
            key: 密钥

        Returns:
            HMAC-SHA256签名（16进制）
        """
        import hmac
        signature = hmac.new(
            key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).digest()
        return signature.hex()

    @staticmethod
    def verify_wechat_pay_notify(
        timestamp: str,
        nonce: str,
        body: str,
        signature: str,
        public_key_path: str
    ) -> bool:
        """
        验证微信支付回调通知的签名

        Args:
            timestamp: 时间戳
            nonce: 随机字符串
            body: 回调通知body
            signature: 微信支付返回的签名
            public_key_path: 平台公钥路径

        Returns:
            验签是否成功
        """
        # 验证参数不为空
        if not all([timestamp, nonce, body, signature]):
            print("验签失败: 缺少必要参数")
            return False

        # 构建待签名串
        message = f"{timestamp}\n{nonce}\n{body}\n"

        # 调试日志：输出验签信息
        print(f"[DEBUG] 验签消息长度: {len(message)}")
        print(f"[DEBUG] 验签消息前200字符: {repr(message[:200])}")
        print(f"[DEBUG] 签名长度: {len(signature)}")
        print(f"[DEBUG] 公钥路径: {public_key_path}")

        # 使用公钥验签
        result = WechatPaySignature.public_key_verify(
            message=message,
            signature=signature,
            public_key_path=public_key_path
        )
        print(f"[DEBUG] 验签结果: {result}")
        return result

    @staticmethod
    def decrypt_callback_resource(
        ciphertext: str,
        associated_data: str,
        nonce: str,
        api_v3_key: str
    ) -> str:
        """
        解密回调通知中的加密数据

        Args:
            ciphertext: Base64编码的密文
            associated_data: 附加数据
            nonce: 加密使用的随机串
            api_v3_key: API v3密钥

        Returns:
            解密后的明文
        """
        import cryptography.hazmat.primitives.ciphers.algorithms as algorithms
        from cryptography.hazmat.primitives.ciphers import Cipher, modes
        from cryptography.hazmat.backends import default_backend

        try:
            # Base64解码
            ciphertext_bytes = base64.b64decode(ciphertext)

            # 密钥处理
            key = api_v3_key.encode('utf-8')

            # 构建AES-GCM解密器
            cipher = Cipher(
                algorithms.AES(key),
                modes.GCM(nonce.encode('utf-8'), tag=None),
                backend=default_backend()
            )

            decryptor = cipher.decryptor()

            # 解密
            plaintext_bytes = decryptor.update(ciphertext_bytes) + decryptor.finalize()

            # 去除附加数据（前16字节是associated_data的长度和数据）
            # 微信支付的AES-GCM实现中，associated_data在明文前面
            # 格式：associated_data + ciphertext
            # 所以解密后需要去除associated_data部分
            if associated_data:
                # 找到JSON开始的位置
                plaintext_str = plaintext_bytes.decode('utf-8')
                # 去除前面的associated_data
                if plaintext_str.startswith(associated_data):
                    plaintext_str = plaintext_str[len(associated_data):]
                return plaintext_str
            else:
                return plaintext_bytes.decode('utf-8')

        except Exception as e:
            # 尝试另一种解密方式
            try:
                from cryptography.hazmat.primitives.ciphers.aead import AESGCM
                aesgcm = AESGCM(key)

                # 微信支付的解密方式：密文需要去除末尾16位的tag
                # 但在某些实现中，tag已经包含在密文中
                decrypted = aesgcm.decrypt(
                    nonce.encode('utf-8'),
                    ciphertext_bytes,
                    associated_data.encode('utf-8') if associated_data else b''
                )
                return decrypted.decode('utf-8')
            except Exception as e2:
                raise Exception(f"解密失败: {str(e2)}")
