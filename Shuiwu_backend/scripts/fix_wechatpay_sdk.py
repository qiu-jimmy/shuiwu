"""
修复 wechatpayv3 SDK 的 PUB_KEY_ID 格式问题

运行此脚本会自动修复 wechatpayv3 SDK 的源码，
使其能够正确处理微信支付平台公钥ID格式 (PUB_KEY_ID_...)

使用方法：
    python scripts/fix_wechatpay_sdk.py
"""
import os
import shutil


def fix_sdk():
    """修复 wechatpayv3 SDK 源码"""

    # 找到 wechatpayv3 的安装路径
    import wechatpayv3
    sdk_path = os.path.dirname(wechatpayv3.__file__)
    core_file = os.path.join(sdk_path, "core.py")

    print(f"找到 wechatpayv3 SDK 路径: {sdk_path}")
    print(f"需要修复的文件: {core_file}")

    # 备份原文件
    backup_file = core_file + ".bak"
    if not os.path.exists(backup_file):
        shutil.copy2(core_file, backup_file)
        print(f"已备份原文件到: {backup_file}")
    else:
        print(f"备份文件已存在: {backup_file}")

    # 读取文件内容
    with open(core_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 检查是否已经修复过
    if 'serial_no_for_compare' in content:
        print("SDK 已经修复过了，无需重复修复。")
        return True

    # 查找需要修复的代码块
    old_code = """        if serial_no == self._public_key_id:
            public_key = self._public_key
        else:
            cert_found = False
            for cert in self._certificates:
                if int('0x' + serial_no, 16) == cert.serial_number:
                    cert_found = True
                    certificate = cert
                    break
            if not cert_found:
                self._update_certificates()
                for cert in self._certificates:
                    if int('0x' + serial_no, 16) == cert.serial_number:
                        cert_found = True
                        certificate = cert
                        break"""

    new_code = """        if serial_no == self._public_key_id:
            public_key = self._public_key
        else:
            cert_found = False
            # 处理平台公钥ID格式 (PUB_KEY_ID_...)
            serial_no_for_compare = serial_no
            if serial_no.startswith('PUB_KEY_ID_'):
                serial_no_for_compare = serial_no.replace('PUB_KEY_ID_', '')
            for cert in self._certificates:
                if int('0x' + serial_no_for_compare, 16) == cert.serial_number:
                    cert_found = True
                    certificate = cert
                    break
            if not cert_found:
                self._update_certificates()
                for cert in self._certificates:
                    if int('0x' + serial_no_for_compare, 16) == cert.serial_number:
                        cert_found = True
                        certificate = cert
                        break"""

    if old_code not in content:
        print("警告: 未找到需要修复的代码块，可能 SDK 版本不同。")
        return False

    # 替换代码
    new_content = content.replace(old_code, new_code)

    # 写入文件
    with open(core_file, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print("✅ SDK 修复成功！")
    return True


if __name__ == "__main__":
    print("=" * 50)
    print("修复 wechatpayv3 SDK PUB_KEY_ID 格式问题")
    print("=" * 50)

    try:
        if fix_sdk():
            print("\n请重启应用以使修复生效。")
        else:
            print("\n修复失败，请检查 SDK 版本。")
    except Exception as e:
        print(f"\n❌ 修复失败: {e}")
        import traceback
        traceback.print_exc()
