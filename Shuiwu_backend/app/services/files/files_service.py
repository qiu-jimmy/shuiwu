"""
文件管理业务逻辑层（Service）
处理文件上传、下载、管理等业务逻辑
"""
import os
import mimetypes
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import alibabacloud_oss_v2 as oss

from app.services.files.files_repository import files_repository
from app.infra.oss_client import oss_client_manager


class FilesService:
    """文件管理业务逻辑层"""

    def __init__(self):
        self.repository = files_repository
        self.oss_manager = oss_client_manager

    def _get_file_category(self, file_type: str, mime_type: Optional[str] = None) -> str:
        """根据文件类型判断分类"""
        # 图片类型
        image_types = ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'svg', 'ico']
        if file_type.lower() in image_types or (mime_type and mime_type.startswith('image/')):
            return 'image'

        # 文档类型
        doc_types = ['pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'txt', 'rtf', 'odt', 'md', 'markdown']
        if file_type.lower() in doc_types or (mime_type and mime_type.startswith('application/')):
            return 'document'

        # 视频类型
        video_types = ['mp4', 'avi', 'mov', 'wmv', 'flv', 'mkv', 'webm']
        if file_type.lower() in video_types or (mime_type and mime_type.startswith('video/')):
            return 'video'

        # 音频类型
        audio_types = ['mp3', 'wav', 'flac', 'aac', 'ogg', 'wma']
        if file_type.lower() in audio_types or (mime_type and mime_type.startswith('audio/')):
            return 'audio'

        # 压缩文件
        archive_types = ['zip', 'rar', '7z', 'tar', 'gz']
        if file_type.lower() in archive_types:
            return 'archive'

        return 'other'

    def _guess_mime_type(self, filename: str) -> Optional[str]:
        """猜测文件的MIME类型"""
        mime_type, _ = mimetypes.guess_type(filename)
        return mime_type

    def _generate_oss_key(self, user_id: str, filename: str, folder_path: Optional[str] = None) -> str:
        """生成OSS存储路径"""
        # 按日期组织文件：user_files/{user_id}/{year}/{month}/{filename}
        now = datetime.now()
        date_path = f"{now.year}/{now.month:02d}"

        base_path = f"user_files/{user_id}/{date_path}"

        if folder_path:
            # 如果指定了文件夹，添加到路径中
            safe_folder = folder_path.strip('/')
            base_path = f"{base_path}/{safe_folder}"

        # 生成唯一文件名（保留原始扩展名）
        name, ext = os.path.splitext(filename)
        unique_filename = f"{name}_{uuid.uuid4().hex[:8]}{ext}"

        return f"{base_path}/{unique_filename}"

    def upload_file(
        self,
        user_id: str,
        file_content: bytes,
        filename: str,
        folder_path: Optional[str] = None,
        kb_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """上传文件到OSS并保存记录"""
        import traceback
        try:
            print(f"[DEBUG] upload_file: user_id={user_id}, filename={filename}")
            # 确保OSS客户端已初始化（会从环境变量或数据库读取配置）
            if not self.oss_manager.is_initialized():
                print("[DEBUG] OSS客户端未初始化，尝试从环境变量或数据库加载配置...")
                if not self.oss_manager.initialize_from_db():
                    raise Exception("OSS客户端未初始化，请先配置OSS环境变量或通过API配置")

            # 获取文件信息
            file_size = len(file_content)
            file_ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
            mime_type = self._guess_mime_type(filename)
            category = self._get_file_category(file_ext, mime_type)

            # 生成OSS存储路径
            oss_key = self._generate_oss_key(user_id, filename, folder_path)

            # 上传到OSS
            client = self.oss_manager.client
            bucket = self.oss_manager.bucket

            result = client.put_object(oss.PutObjectRequest(
                bucket=bucket,
                key=oss_key,
                body=file_content,
            ))

            if result.status_code != 200:
                raise Exception(f"OSS上传失败，状态码: {result.status_code}")

            # 构建文件URL（使用OSS默认域名）
            # 标准格式：https://{bucket}.oss-{region}.aliyuncs.com/{key}
            region = self.oss_manager._config.get('region', 'cn-hangzhou')
            endpoint = self.oss_manager._config.get('endpoint')

            if endpoint and endpoint.strip():
                # 使用自定义endpoint（去除协议前缀）
                endpoint_clean = endpoint.replace('https://', '').replace('http://', '').strip()
                file_url = f"https://{bucket}.{endpoint_clean}/{oss_key}"
            else:
                # 使用标准endpoint格式：bucket.oss-region.aliyuncs.com
                file_url = f"https://{bucket}.oss-{region}.aliyuncs.com/{oss_key}"
            # 保存文件记录到数据库
            file_data = {
                'user_id': user_id,
                'file_name': filename,
                'file_type': file_ext,
                'file_size': file_size,
                'file_path': oss_key,
                'file_url': file_url,
                'mime_type': mime_type,
                'category': category,
                'folder_path': folder_path,
                'kb_name': kb_name,
                'status': 'active'
            }

            print(f"[DEBUG] Calling repository.create_file with file_data: {file_data}")
            file_record = self.repository.create_file(file_data)
            print(f"[DEBUG] repository.create_file returned: {file_record}, type: {type(file_record)}")

            if file_record:
                return file_record

            return None

        except Exception as e:
            print(f"上传文件失败: {e}")
            traceback.print_exc()
            raise Exception(f"上传文件失败: {str(e)}")

    def batch_upload_files(
        self,
        user_id: str,
        files: List[tuple],  # List of (filename, file_content) tuples
        folder_path: Optional[str] = None,
        kb_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        批量上传文件

        Args:
            user_id: 用户ID
            files: 文件列表，每个元素为 (filename, file_content) 元组
            folder_path: 文件夹路径（可选）
            kb_name: 关联知识库名称（可选）

        Returns:
            Dict: {
                'total': 总文件数,
                'success': 成功上传数,
                'failed': 失败数,
                'files': 成功上传的文件列表,
                'errors': 失败文件的错误信息 {filename: error_message}
            }
        """
        import traceback

        result = {
            'total': len(files),
            'success': 0,
            'failed': 0,
            'files': [],
            'errors': {}
        }

        for filename, file_content in files:
            try:
                file_record = self.upload_file(
                    user_id=user_id,
                    file_content=file_content,
                    filename=filename,
                    folder_path=folder_path,
                    kb_name=kb_name
                )

                if file_record:
                    result['files'].append(file_record)
                    result['success'] += 1
                else:
                    result['errors'][filename] = '上传失败，未知原因'
                    result['failed'] += 1

            except Exception as e:
                error_msg = f"上传失败: {str(e)}"
                result['errors'][filename] = error_msg
                result['failed'] += 1
                print(f"批量上传文件 '{filename}' 失败: {e}")
                traceback.print_exc()

        return result

    def upload_file_from_path(
        self,
        user_id: str,
        file_path: str,
        folder_path: Optional[str] = None,
        kb_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """从本地路径上传文件"""
        try:
            # 读取文件内容
            with open(file_path, 'rb') as f:
                file_content = f.read()

            filename = os.path.basename(file_path)

            return self.upload_file(
                user_id=user_id,
                file_content=file_content,
                filename=filename,
                folder_path=folder_path,
                kb_name=kb_name
            )

        except Exception as e:
            print(f"从路径上传文件失败: {e}")
            raise Exception(f"从路径上传文件失败: {str(e)}")

    def get_file_info(self, file_id: str, user_id: Optional[str] = None, is_admin: bool = False) -> Optional[Dict[str, Any]]:
        """获取文件信息"""
        file_info = self.repository.get_file_by_id(file_id)

        if not file_info:
            return None

        # 如果指定了user_id且不是管理员，验证文件所有者
        if user_id and not is_admin and file_info['user_id'] != user_id:
            return None

        return file_info

    def list_files(
        self,
        user_id: str,
        is_admin: bool = False,
        file_type: Optional[str] = None,
        category: Optional[str] = None,
        folder_path: Optional[str] = None,
        kb_name: Optional[str] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """查询文件列表（管理员可查看所有文件）"""
        filters = {
            'file_type': file_type,
            'category': category,
            'folder_path': folder_path,
            'kb_name': kb_name,
            'keyword': keyword,
            'page': page,
            'page_size': page_size
        }

        # 只有非管理员才过滤 user_id
        if not is_admin:
            filters['user_id'] = user_id

        return self.repository.list_files(filters)

    def update_file(
        self,
        file_id: str,
        user_id: str,
        file_name: Optional[str] = None,
        folder_path: Optional[str] = None,
        kb_name: Optional[str] = None,
        is_admin: bool = False
    ) -> bool:
        """更新文件信息"""
        # 验证文件所有者（管理员可跳过）
        file_info = self.repository.get_file_by_id(file_id)
        if not file_info or (not is_admin and file_info['user_id'] != user_id):
            return False

        update_data = {}
        if file_name is not None:
            update_data['file_name'] = file_name
        if folder_path is not None:
            update_data['folder_path'] = folder_path
        if kb_name is not None:
            update_data['kb_name'] = kb_name

        if not update_data:
            return False

        return self.repository.update_file(file_id, update_data)

    def delete_file(
        self,
        file_id: str,
        user_id: str,
        permanent: bool = False,
        is_admin: bool = False
    ) -> bool:
        """删除文件"""
        # 验证文件所有者（管理员可跳过）
        file_info = self.repository.get_file_by_id(file_id)
        if not file_info or (not is_admin and file_info['user_id'] != user_id):
            return False

        # 如果是永久删除，同时删除OSS文件
        if permanent:
            try:
                client = self.oss_manager.client
                bucket = self.oss_manager.bucket

                client.delete_object(oss.DeleteObjectRequest(
                    bucket=bucket,
                    key=file_info['file_path']
                ))
            except Exception as e:
                print(f"删除OSS文件失败: {e}")

        return self.repository.delete_file(file_id, permanent)

    def batch_delete_files(
        self,
        file_ids: List[str],
        user_id: str,
        permanent: bool = False,
        is_admin: bool = False
    ) -> int:
        """批量删除文件"""
        # 验证所有文件的所有者（管理员可跳过）
        valid_file_ids = []
        for file_id in file_ids:
            file_info = self.repository.get_file_by_id(file_id)
            if file_info and (is_admin or file_info['user_id'] == user_id):
                valid_file_ids.append(file_id)

                # 如果是永久删除，删除OSS文件
                if permanent:
                    try:
                        client = self.oss_manager.client
                        bucket = self.oss_manager.bucket

                        client.delete_object(oss.DeleteObjectRequest(
                            bucket=bucket,
                            key=file_info['file_path']
                        ))
                    except Exception as e:
                        print(f"删除OSS文件失败: {e}")

        return self.repository.batch_delete_files(valid_file_ids, permanent)

    def get_download_url(self, file_id: str, user_id: str, is_admin: bool = False) -> Optional[str]:
        """获取文件下载URL"""
        file_info = self.get_file_info(file_id, user_id, is_admin)
        if not file_info:
            return None

        # 增加下载计数
        self.repository.increment_download_count(file_id)

        # 直接返回OSS URL
        return file_info['file_url']

    def get_file_stats(self, user_id: str, is_admin: bool = False) -> Dict[str, Any]:
        """获取文件统计信息（管理员可查看全局统计）"""
        return self.repository.get_file_stats(user_id, is_admin)

    def batch_update_files(
        self,
        file_ids: List[str],
        user_id: str,
        folder_path: Optional[str] = None,
        kb_name: Optional[str] = None,
        is_admin: bool = False
    ) -> int:
        """批量更新文件"""
        updated_count = 0
        for file_id in file_ids:
            # 验证文件所有者（管理员可跳过）
            file_info = self.repository.get_file_by_id(file_id)
            if not file_info or (not is_admin and file_info['user_id'] != user_id):
                continue

            # 构建更新数据
            update_data = {}
            if folder_path is not None:
                update_data['folder_path'] = folder_path
            if kb_name is not None:
                update_data['kb_name'] = kb_name

            if not update_data:
                continue

            if self.repository.update_file(file_id, update_data):
                updated_count += 1
        return updated_count

    def create_folder(self, user_id: str, folder_path: str) -> bool:
        """创建文件夹（记录路径，不实际创建）"""
        # 这里可以选择是否记录文件夹信息
        # 当前实现中，文件夹只是一个路径标记
        return True

    def list_folders(self, user_id: str) -> List[str]:
        """列出用户的所有文件夹"""
        result = self.repository.list_files({
            'user_id': user_id,
            'page': 1,
            'page_size': 1000
        })

        folders = set()
        files_list = result.get('files', [])

        for file in files_list:
            # 确保 file 是字典类型
            if not isinstance(file, dict):
                print(f"Warning: file 不是字典类型，而是 {type(file)}: {file}")
                continue

            if file.get('folder_path'):
                folders.add(file['folder_path'])

        return sorted(list(folders))


# 全局Service实例
files_service = FilesService()
