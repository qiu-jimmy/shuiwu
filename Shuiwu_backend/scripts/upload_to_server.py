"""
使用SCP上传文件到远程服务器
"""
import os
import sys
from pathlib import Path

try:
    import paramiko
    from scp import SCPClient
except ImportError:
    print("正在安装必要的库...")
    os.system(f"{sys.executable} -m pip install paramiko scp -q")
    import paramiko
    from scp import SCPClient

# 配置信息
LOCAL_FILE = r"D:\zhulong_code\Shuiwu\Shuiwu_backend\Shuiwu_backend\Shuiwu_backend\docs\数据集\shuixiaotong_finetune_800_with_reasoning.jsonl"
REMOTE_HOST = "117.50.217.66"
REMOTE_USER = "ubuntu"
REMOTE_PASSWORD = "7EmLb0952gf136pF"
REMOTE_PATH = "/home/ubuntu/models/shuixiaotong_finetune_800_with_reasoning.jsonl"

def upload_file():
    """上传文件到远程服务器"""
    print("=" * 60)
    print("文件上传工具")
    print("=" * 60)
    
    # 检查本地文件
    print(f"\n[1/4] 检查本地文件...")
    if not os.path.exists(LOCAL_FILE):
        print(f"错误: 本地文件不存在: {LOCAL_FILE}")
        return False
    
    file_size = os.path.getsize(LOCAL_FILE)
    print(f"本地文件: {LOCAL_FILE}")
    print(f"文件大小: {file_size / 1024:.2f} KB")
    
    # 连接服务器
    print(f"\n[2/4] 连接远程服务器...")
    print(f"服务器: {REMOTE_USER}@{REMOTE_HOST}")
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(REMOTE_HOST, username=REMOTE_USER, password=REMOTE_PASSWORD)
        print("SSH连接成功")
        
        # 创建远程目录（如果不存在）
        print(f"\n[3/4] 检查远程目录...")
        remote_dir = os.path.dirname(REMOTE_PATH)
        stdin, stdout, stderr = ssh.exec_command(f"mkdir -p {remote_dir}")
        stdout.read()  # 等待命令执行完成
        print(f"远程目录: {remote_dir}")
        
        # 上传文件
        print(f"\n[4/4] 上传文件...")
        with SCPClient(ssh.get_transport()) as scp:
            scp.put(LOCAL_FILE, REMOTE_PATH)
        
        print(f"文件上传成功: {REMOTE_PATH}")
        
        # 验证上传
        print(f"\n[验证] 检查远程文件...")
        stdin, stdout, stderr = ssh.exec_command(f"ls -lh {REMOTE_PATH}")
        result = stdout.read().decode('utf-8')
        print(result)
        
        ssh.close()
        print("\n" + "=" * 60)
        print("上传完成！")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n错误: {str(e)}")
        return False

if __name__ == "__main__":
    upload_file()
