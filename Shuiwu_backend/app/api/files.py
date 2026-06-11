"""
文件管理API路由
提供文件上传、下载、管理等功能
"""
import asyncio
from typing import Optional, List

from fastapi import APIRouter, UploadFile, File, Form, Query, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.schemas.file import (
    FileUploadFromUrlRequest,
    FileUpdateRequest,
    FileResponse,
    FileDeleteRequest,
    FileBatchUpdateRequest,
    OSSConfigRequest,
    OSSConfigResponse,
    FileStorageStatsResponse,
)
from app.services.files.files_service import files_service
from app.infra.oss_client import oss_client_manager
from app.utils.response import response
from app.utils.dependencies import require_current_user, get_current_user_with_roles
from app.utils.filename_utils import safe_filename
from app.middleware.member_permission import require_member_quota

router = APIRouter(prefix="/api/files", tags=["文件管理"])


async def _run_sync(func, *args, **kwargs):
    """在线程池中执行同步函数"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: func(*args, **kwargs))


# ============================================================================
# OSS配置管理
# ============================================================================

@router.post(
    "/config/oss",
    summary="配置OSS",
    description="""
配置阿里云OSS存储服务。

**功能特性：**
- 配置OSS访问凭证和连接信息
- 支持自定义endpoint
- 配置保存到数据库加密存储

**所需参数：**
- access_key_id: 阿里云AccessKey ID
- access_key_secret: 阿里云AccessKey Secret
- region: OSS区域（默认cn-hangzhou）
- bucket: Bucket名称
- endpoint: 自定义endpoint（可选）
""",
    responses={
        200: {
            "description": "配置成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "OSS配置成功",
                        "data": {
                            "bucket": "my-bucket",
                            "region": "cn-hangzhou"
                        }
                    }
                }
            }
        },
        400: {
            "description": "配置失败",
            "content": {
                "application/json": {
                    "examples": {
                        "save_failed": {
                            "summary": "保存配置失败",
                            "value": {
                                "code": 0,
                                "message": "保存OSS配置失败",
                                "data": None
                            }
                        },
                        "init_failed": {
                            "summary": "初始化客户端失败",
                            "value": {
                                "code": 0,
                                "message": "OSS客户端初始化失败",
                                "data": None
                            }
                        }
                    }
                }
            }
        }
    }
)
async def configure_oss(request: OSSConfigRequest):
    """配置阿里云OSS"""
    try:
        # 保存配置到数据库
        success = await _run_sync(
            oss_client_manager.save_config_to_db,
            request.access_key_id,
            request.access_key_secret,
            request.region,
            request.bucket,
            request.endpoint
        )

        if not success:
            return response.fail(message="保存OSS配置失败")

        # 重新初始化OSS客户端
        init_success = await _run_sync(
            oss_client_manager.initialize_direct,
            request.access_key_id,
            request.access_key_secret,
            request.region,
            request.bucket,
            request.endpoint
        )

        if not init_success:
            return response.fail(message="OSS客户端初始化失败")

        return response.success(
            data={
                "bucket": request.bucket,
                "region": request.region
            },
            message="OSS配置成功"
        )

    except Exception as e:
        return response.fail(message=f"配置OSS失败: {str(e)}")


@router.get(
    "/config/oss",
    summary="获取OSS配置状态",
    description="""
获取当前OSS配置状态。

**返回信息：**
- configured: 是否已配置
- bucket: Bucket名称
- region: OSS区域
""",
    responses={
        200: {
            "description": "获取成功",
            "content": {
                "application/json": {
                    "examples": {
                        "configured": {
                            "summary": "OSS已配置",
                            "value": {
                                "code": 1,
                                "message": "OSS已配置",
                                "data": {
                                    "configured": True,
                                    "bucket": "my-bucket",
                                    "region": "cn-hangzhou",
                                    "message": "OSS已配置"
                                }
                            }
                        },
                        "not_configured": {
                            "summary": "OSS未配置",
                            "value": {
                                "code": 1,
                                "message": "OSS未配置",
                                "data": {
                                    "configured": False,
                                    "message": "OSS未配置"
                                }
                            }
                        }
                    }
                }
            }
        }
    }
)
async def get_oss_config():
    """获取OSS配置状态"""
    try:
        # 尝试初始化（会从环境变量或数据库读取配置）
        await _run_sync(oss_client_manager.initialize_from_db)

        is_configured = await _run_sync(oss_client_manager.is_initialized)

        if is_configured:
            return response.success(
                data=OSSConfigResponse(
                    configured=True,
                    bucket=oss_client_manager.bucket,
                    region=oss_client_manager._config.get('region'),
                    message="OSS已配置"
                ).model_dump(),
                message="OSS已配置"
            )
        else:
            return response.success(
                data=OSSConfigResponse(
                    configured=False,
                    message="OSS未配置"
                ).model_dump(),
                message="OSS未配置"
            )

    except Exception as e:
        return response.fail(message=f"获取OSS配置失败: {str(e)}")


# ============================================================================
# 文件上传
# ============================================================================

@router.post(
    "/upload",
    summary="上传文件",
    description="""
上传文件到OSS并保存记录。

**功能特性：**
- 支持多种文件格式（PDF、DOCX、PPTX、图片等）
- 自动识别文件类型和分类
- 支持文件夹分类管理
- 可关联知识库
- 支持原始文件名传递（解决微信小程序文件名编码问题）

**请求参数：**
- file: 要上传的文件（multipart/form-data）
- folder_path: 文件夹路径（可选）
- kb_name: 关联知识库名称（可选）
- original_filename: 原始文件名（可选，建议微信小程序上传时传递，解决文件名被临时路径替换的问题）

**微信小程序上传示例：**
```javascript
wx.chooseMessageFile({
  count: 1,
  type: 'file',
  success(res) {
    const tempFile = res.tempFiles[0];
    wx.uploadFile({
      url: 'https://your-domain.com/api/files/upload',
      filePath: tempFile.path,
      name: 'file',
      formData: {
        original_filename: tempFile.name,  // 传递原始文件名
        folder_path: 'documents'
      },
      header: {
        'Authorization': 'Bearer ' + token
      }
    });
  }
});
```

**认证要求：** 需要在请求头中提供有效的 Bearer Token
""",
    responses={
        200: {
            "description": "上传成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "文件 'example.pdf' 上传成功",
                        "data": {
                            "file_id": "file_1234567890abcdef",
                            "file_name": "example.pdf",
                            "file_type": "pdf",
                            "file_size": 1048576,
                            "file_url": "https://my-bucket.oss-cn-hangzhou.aliyuncs.com/files/file_1234567890abcdef.pdf",
                            "mime_type": "application/pdf",
                            "category": "document",
                            "folder_path": "documents/tax",
                            "kb_name": "knowledge_base_1",
                            "status": "active",
                            "created_at": "2024-01-13T15:30:00"
                        }
                    }
                }
            }
        },
        400: {
            "description": "上传失败",
            "content": {
                "application/json": {
                    "examples": {
                        "empty_file": {
                            "summary": "文件内容为空",
                            "value": {
                                "code": 0,
                                "message": "文件内容为空",
                                "data": None
                            }
                        },
                        "upload_failed": {
                            "summary": "上传失败",
                            "value": {
                                "code": 0,
                                "message": "文件上传失败",
                                "data": None
                            }
                        }
                    }
                }
            }
        },
        401: {
            "description": "未授权",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "未提供认证token",
                        "data": None
                    }
                }
            }
        }
    }
)
@require_member_quota("file_storage_mb", consume=10)
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    folder_path: Optional[str] = Form(None),
    kb_name: Optional[str] = Form(None),
    original_filename: Optional[str] = Form(None),  # 新增：支持传入原始文件名
    current_user: str = Depends(require_current_user)
):
    """上传文件 - 需要文件存储配额（默认10MB）"""
    try:
        # 读取文件内容
        file_content = await file.read()

        if not file_content:
            return response.fail(message="文件内容为空")

        # 优先使用传入的原始文件名，否则使用上传的文件名并解码
        # 解决微信小程序上传时文件名被临时路径替换的问题
        if original_filename and original_filename.strip():
            final_filename = original_filename.strip()
        else:
            final_filename = safe_filename(file.filename)

        # 上传文件
        file_record = await _run_sync(
            files_service.upload_file,
            current_user,  # current_user 已经是 user_id 字符串
            file_content,
            final_filename,
            folder_path,
            kb_name
        )

        if not file_record:
            return response.fail(message="文件上传失败")

        return response.success(
            data=file_record,
            message=f"文件 '{final_filename}' 上传成功"
        )

    except Exception as e:
        return response.fail(message=f"上传文件失败: {str(e)}")


@router.post(
    "/upload/batch",
    summary="批量上传文件",
    description="""
批量上传多个文件到OSS并保存记录。

**功能特性：**
- 支持一次上传多个文件
- 自动识别文件类型和分类
- 支持文件夹分类管理
- 可关联知识库
- 部分失败不影响其他文件上传
- 支持原始文件名传递（解决微信小程序文件名编码问题）

**请求参数：**
- files: 要上传的多个文件（multipart/form-data，支持多个文件字段）
- folder_path: 文件夹路径（可选）
- kb_name: 关联知识库名称（可选）
- original_filenames: 原始文件名列表，逗号分隔（可选，建议微信小程序上传时传递）
  - 例如: "document1.pdf,document2.docx,税务文档.xlsx"

**微信小程序批量上传示例：**
```javascript
wx.chooseMessageFile({
  count: 10,
  type: 'file',
  success(res) {
    const tempFiles = res.tempFiles;
    // 提取所有原始文件名，用逗号连接
    const originalNames = tempFiles.map(f => f.name).join(',');

    // 注意：微信小程序的 wx.uploadFile 只支持单文件上传
    // 批量上传需要循环调用单个文件上传接口
    tempFiles.forEach((tempFile, index) => {
      wx.uploadFile({
        url: 'https://your-domain.com/api/files/upload',
        filePath: tempFile.path,
        name: 'file',
        formData: {
          original_filename: tempFile.name,
          folder_path: 'documents'
        },
        header: {
          'Authorization': 'Bearer ' + token
        }
      });
    });
  }
});
```

**认证要求：** 需要在请求头中提供有效的 Bearer Token

**返回信息：**
- total: 总文件数
- success: 成功上传数
- failed: 失败数
- files: 成功上传的文件列表
- errors: 失败文件的错误信息 {filename: error_message}
""",
    responses={
        200: {
            "description": "批量上传完成",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "批量上传完成，成功 3 个，失败 1 个",
                        "data": {
                            "total": 4,
                            "success": 3,
                            "failed": 1,
                            "files": [
                                {
                                    "file_id": "file_1234567890abcdef",
                                    "file_name": "document1.pdf",
                                    "file_type": "pdf",
                                    "file_size": 1048576,
                                    "file_url": "https://my-bucket.oss-cn-hangzhou.aliyuncs.com/user_files/user_123/2024/01/document1_abc123.pdf",
                                    "mime_type": "application/pdf",
                                    "category": "document",
                                    "folder_path": "documents",
                                    "kb_name": "knowledge_base_1",
                                    "status": "active",
                                    "created_at": "2024-01-13T15:30:00"
                                },
                                {
                                    "file_id": "file_2345678901bcdef",
                                    "file_name": "document2.docx",
                                    "file_type": "docx",
                                    "file_size": 524288,
                                    "file_url": "https://my-bucket.oss-cn-hangzhou.aliyuncs.com/user_files/user_123/2024/01/document2_def456.docx",
                                    "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                    "category": "document",
                                    "folder_path": "documents",
                                    "kb_name": "knowledge_base_1",
                                    "status": "active",
                                    "created_at": "2024-01-13T15:30:01"
                                }
                            ],
                            "errors": {
                                "invalid_file.txt": "上传失败: 文件内容为空"
                            }
                        }
                    }
                }
            }
        },
        400: {
            "description": "请求错误",
            "content": {
                "application/json": {
                    "examples": {
                        "no_files": {
                            "summary": "未提供文件",
                            "value": {
                                "code": 0,
                                "message": "未提供要上传的文件",
                                "data": None
                            }
                        },
                        "all_failed": {
                            "summary": "所有文件上传失败",
                            "value": {
                                "code": 0,
                                "message": "批量上传完成，成功 0 个，失败 3 个",
                                "data": {
                                    "total": 3,
                                    "success": 0,
                                    "failed": 3,
                                    "files": [],
                                    "errors": {
                                        "file1.pdf": "上传失败: OSS客户端未初始化",
                                        "file2.pdf": "上传失败: 文件过大",
                                        "file3.pdf": "上传失败: 不支持的文件类型"
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        401: {
            "description": "未授权",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "未提供认证token",
                        "data": None
                    }
                }
            }
        }
    }
)
@require_member_quota("file_storage_mb", consume=50)
async def batch_upload_files(
    request: Request,
    files: List[UploadFile] = File(...),
    folder_path: Optional[str] = Form(None),
    kb_name: Optional[str] = Form(None),
    original_filenames: Optional[str] = Form(None),  # 新增：支持传入原始文件名列表（逗号分隔）
    current_user: str = Depends(require_current_user)
):
    """批量上传文件 - 需要文件存储配额（默认50MB）"""
    try:
        if not files or len(files) == 0:
            return response.fail(message="未提供要上传的文件")

        # 解析原始文件名列表（如果提供）
        original_filename_list = None
        if original_filenames and original_filenames.strip():
            original_filename_list = [f.strip() for f in original_filenames.split(',') if f.strip()]

        # 读取所有文件内容
        files_data = []
        for i, file in enumerate(files):
            file_content = await file.read()
            if file_content:
                # 优先使用传入的原始文件名，否则使用上传的文件名并解码
                if original_filename_list and i < len(original_filename_list):
                    final_filename = original_filename_list[i]
                else:
                    final_filename = safe_filename(file.filename)
                files_data.append((final_filename, file_content))

        if not files_data:
            return response.fail(message="所有文件内容为空")

        # 批量上传
        result = await _run_sync(
            files_service.batch_upload_files,
            current_user,
            files_data,
            folder_path,
            kb_name
        )

        # 根据上传结果返回消息
        if result['success'] == 0:
            return response.fail(
                data=result,
                message=f"批量上传完成，成功 0 个，失败 {result['failed']} 个"
            )
        elif result['failed'] == 0:
            return response.success(
                data=result,
                message=f"批量上传成功，共上传 {result['success']} 个文件"
            )
        else:
            return response.success(
                data=result,
                message=f"批量上传完成，成功 {result['success']} 个，失败 {result['failed']} 个"
            )

    except Exception as e:
        return response.fail(message=f"批量上传失败: {str(e)}")


@router.post(
    "/upload/from-url",
    summary="从URL创建文件记录",
    description="""
对于已经上传到OSS的文件，创建记录到数据库。
适用于直接通过OSS SDK或其他方式上传的文件。

**认证要求：** 需要在请求头中提供有效的 Bearer Token
""",
    responses={
        200: {
            "description": "创建成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "文件记录创建成功",
                        "data": {
                            "file_id": "file_1234567890abcdef",
                            "file_name": "example.pdf",
                            "file_type": "pdf",
                            "file_size": 1048576,
                            "file_path": "files/example.pdf",
                            "file_url": "https://my-bucket.oss-cn-hangzhou.aliyuncs.com/files/example.pdf",
                            "mime_type": "application/pdf",
                            "category": "document",
                            "folder_path": "documents",
                            "kb_name": None,
                            "status": "active",
                            "created_at": "2024-01-13T15:30:00"
                        }
                    }
                }
            }
        },
        400: {
            "description": "创建失败",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "创建文件记录失败",
                        "data": None
                    }
                }
            }
        },
        401: {
            "description": "未授权",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "未提供认证token",
                        "data": None
                    }
                }
            }
        }
    }
)
@require_member_quota("file_storage_mb", consume=10)
async def create_file_from_url(
    request: Request,
    url_request: FileUploadFromUrlRequest,
    current_user: str = Depends(require_current_user)
):
    """从URL创建文件记录 - 需要文件存储配额（默认10MB）"""
    try:
        from app.services.files.files_repository import files_repository

        file_data = {
            'user_id': current_user,
            'file_name': url_request.file_name,
            'file_type': url_request.file_type,
            'file_size': url_request.file_size,
            'file_path': url_request.file_path,
            'file_url': url_request.file_url,
            'mime_type': url_request.mime_type,
            'category': url_request.category,
            'folder_path': url_request.folder_path,
            'kb_name': url_request.kb_name,
            'status': 'active'
        }

        file_record = await _run_sync(files_repository.create_file, file_data)

        if not file_record:
            return response.fail(message="创建文件记录失败")

        return response.success(
            data=file_record,
            message="文件记录创建成功"
        )

    except Exception as e:
        return response.fail(message=f"创建文件记录失败: {str(e)}")


# ============================================================================
# 文件查询
# ============================================================================

@router.get(
    "/list",
    summary="查询文件列表",
    description="""
查询用户的文件列表，支持多种过滤条件和分页。

**查询参数：**
- file_type: 文件类型过滤（如pdf、docx）
- category: 分类过滤（document、image、video、audio、other）
- folder_path: 文件夹路径过滤
- kb_name: 知识库名称过滤
- keyword: 文件名关键词搜索
- page: 页码（默认1）
- page_size: 每页数量（默认20）

**认证要求：** 需要在请求头中提供有效的 Bearer Token
""",
    responses={
        200: {
            "description": "查询成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "查询成功",
                        "data": {
                            "files": [
                                {
                                    "file_id": "file_1234567890abcdef",
                                    "file_name": "example.pdf",
                                    "file_type": "pdf",
                                    "file_size": 1048576,
                                    "file_url": "https://my-bucket.oss-cn-hangzhou.aliyuncs.com/files/example.pdf",
                                    "mime_type": "application/pdf",
                                    "category": "document",
                                    "folder_path": "documents",
                                    "kb_name": "knowledge_base_1",
                                    "download_count": 5,
                                    "status": "active",
                                    "created_at": "2024-01-13T15:30:00"
                                }
                            ],
                            "total": 50,
                            "page": 1,
                            "page_size": 20
                        }
                    }
                }
            }
        },
        401: {
            "description": "未授权",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "未提供认证token",
                        "data": None
                    }
                }
            }
        }
    }
)
async def list_files(
    file_type: Optional[str] = Query(None, description="文件类型"),
    category: Optional[str] = Query(None, description="文件分类"),
    folder_path: Optional[str] = Query(None, description="文件夹路径"),
    kb_name: Optional[str] = Query(None, description="知识库名称"),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: dict = Depends(get_current_user_with_roles)
):
    """查询文件列表（管理员可查看所有文件）"""
    try:
        result = await _run_sync(
            files_service.list_files,
            current_user["user_id"],
            current_user.get("is_admin", False),
            file_type,
            category,
            folder_path,
            kb_name,
            keyword,
            page,
            page_size
        )

        return response.success(
            data=result,
            message="查询成功"
        )

    except Exception as e:
        return response.fail(message=f"查询文件列表失败: {str(e)}")


@router.get(
    "/folders",
    summary="获取文件夹列表",
    description="""
获取用户所有的文件夹路径列表。

**认证要求：** 需要在请求头中提供有效的 Bearer Token
""",
    responses={
        200: {
            "description": "查询成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "查询文件夹列表成功",
                        "data": {
                            "folders": [
                                "documents",
                                "documents/tax",
                                "documents/finance",
                                "images",
                                "videos"
                            ]
                        }
                    }
                }
            }
        },
        401: {
            "description": "未授权",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "未提供认证token",
                        "data": None
                    }
                }
            }
        }
    }
)
async def list_folders(
    current_user: str = Depends(require_current_user)
):
    """获取文件夹列表"""
    try:
        folders = await _run_sync(
            files_service.list_folders,
            current_user
        )

        return response.success(
            data={"folders": folders},
            message="查询文件夹列表成功"
        )

    except Exception as e:
        return response.fail(message=f"获取文件夹列表失败: {str(e)}")


@router.get(
    "/{file_id}",
    summary="获取文件信息",
    description="""
根据文件ID获取文件的详细信息。

**认证要求：** 需要在请求头中提供有效的 Bearer Token
""",
    responses={
        200: {
            "description": "获取成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "查询成功",
                        "data": {
                            "file_id": "file_1234567890abcdef",
                            "file_name": "example.pdf",
                            "file_type": "pdf",
                            "file_size": 1048576,
                            "file_path": "files/example.pdf",
                            "file_url": "https://my-bucket.oss-cn-hangzhou.aliyuncs.com/files/example.pdf",
                            "mime_type": "application/pdf",
                            "category": "document",
                            "folder_path": "documents",
                            "kb_name": "knowledge_base_1",
                            "download_count": 5,
                            "status": "active",
                            "created_at": "2024-01-13T15:30:00",
                            "updated_at": "2024-01-13T15:30:00"
                        }
                    }
                }
            }
        },
        400: {
            "description": "获取失败",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "文件不存在或无权访问",
                        "data": None
                    }
                }
            }
        },
        401: {
            "description": "未授权",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "未提供认证token",
                        "data": None
                    }
                }
            }
        }
    }
)
async def get_file_info(
    file_id: str,
    current_user: str = Depends(require_current_user)
):
    """获取文件信息"""
    try:
        file_info = await _run_sync(
            files_service.get_file_info,
            file_id,
            current_user
        )

        if not file_info:
            return response.fail(message="文件不存在或无权访问")

        return response.success(
            data=file_info,
            message="查询成功"
        )

    except Exception as e:
        return response.fail(message=f"获取文件信息失败: {str(e)}")


@router.get(
    "/{file_id}/download",
    summary="获取文件下载链接",
    description="""
获取文件的下载URL。每次调用会增加文件的下载计数。

**认证要求：** 需要在请求头中提供有效的 Bearer Token

**注意事项：**
- 返回的下载URL具有时效性
- 每次调用会更新文件的下载计数
""",
    responses={
        200: {
            "description": "获取成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "获取下载链接成功",
                        "data": {
                            "download_url": "https://my-bucket.oss-cn-hangzhou.aliyuncs.com/files/example.pdf?expires=3600&signature=xxx",
                            "file_id": "file_1234567890abcdef"
                        }
                    }
                }
            }
        },
        400: {
            "description": "获取失败",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "文件不存在或无权访问",
                        "data": None
                    }
                }
            }
        },
        401: {
            "description": "未授权",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "未提供认证token",
                        "data": None
                    }
                }
            }
        }
    }
)
async def get_download_url(
    file_id: str,
    current_user: dict = Depends(get_current_user_with_roles)
):
    """获取文件下载URL"""
    try:
        download_url = await _run_sync(
            files_service.get_download_url,
            file_id,
            current_user["user_id"],
            current_user.get("is_admin", False)
        )

        if not download_url:
            return response.fail(message="文件不存在或无权访问")

        return response.success(
            data={"download_url": download_url, "file_id": file_id},
            message="获取下载链接成功"
        )

    except Exception as e:
        return response.fail(message=f"获取下载链接失败: {str(e)}")


# ============================================================================
# 文件更新
# ============================================================================

@router.put(
    "/batch",
    summary="批量更新文件",
    description="""
批量更新文件的文件夹路径或关联知识库。

**认证要求：** 需要在请求头中提供有效的 Bearer Token
""",
    responses={
        200: {
            "description": "更新成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "成功更新 3 个文件",
                        "data": {
                            "updated_count": 3
                        }
                    }
                }
            }
        },
        401: {
            "description": "未授权",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "未提供认证token",
                        "data": None
                    }
                }
            }
        }
    }
)
async def batch_update_files(
    request: FileBatchUpdateRequest,
    current_user: dict = Depends(get_current_user_with_roles)
):
    """批量更新文件"""
    try:
        updated_count = await _run_sync(
            files_service.batch_update_files,
            request.file_ids,
            current_user["user_id"],
            request.folder_path,
            request.kb_name,
            current_user.get("is_admin", False)
        )

        return response.success(
            data={"updated_count": updated_count},
            message=f"成功更新 {updated_count} 个文件"
        )

    except Exception as e:
        return response.fail(message=f"批量更新失败: {str(e)}")


@router.put(
    "/{file_id}",
    summary="更新文件信息",
    description="""
更新文件的名称、文件夹路径或关联知识库。

**认证要求：** 需要在请求头中提供有效的 Bearer Token
""",
    responses={
        200: {
            "description": "更新成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "文件信息更新成功",
                        "data": {
                            "file_id": "file_1234567890abcdef"
                        }
                    }
                }
            }
        },
        400: {
            "description": "更新失败",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "更新失败，文件不存在或无权访问",
                        "data": None
                    }
                }
            }
        },
        401: {
            "description": "未授权",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "未提供认证token",
                        "data": None
                    }
                }
            }
        }
    }
)
async def update_file(
    file_id: str,
    request: FileUpdateRequest,
    current_user: dict = Depends(get_current_user_with_roles)
):
    """更新文件信息"""
    try:
        success = await _run_sync(
            files_service.update_file,
            file_id,
            current_user["user_id"],
            request.file_name,
            request.folder_path,
            request.kb_name,
            current_user.get("is_admin", False)
        )

        if not success:
            return response.fail(message="更新失败，文件不存在或无权访问")

        return response.success(
            data={"file_id": file_id},
            message="文件信息更新成功"
        )

    except Exception as e:
        return response.fail(message=f"更新文件信息失败: {str(e)}")


# ============================================================================
# 文件删除
# ============================================================================

@router.delete(
    "/batch",
    summary="批量删除文件",
    description="""
批量删除多个文件。

**请求参数：**
- file_ids: 文件ID列表
- permanent: 是否永久删除（默认false）

**认证要求：** 需要在请求头中提供有效的 Bearer Token

**删除说明：**
- 软删除（permanent=false）：将文件标记为deleted状态，可以从回收站恢复
- 永久删除（permanent=true）：彻底删除文件，无法恢复
""",
    responses={
        200: {
            "description": "删除成功",
            "content": {
                "application/json": {
                    "examples": {
                        "soft_delete": {
                            "summary": "软删除",
                            "value": {
                                "code": 1,
                                "message": "成功删除 3 个文件",
                                "data": {
                                    "deleted_count": 3
                                }
                            }
                        },
                        "permanent_delete": {
                            "summary": "永久删除",
                            "value": {
                                "code": 1,
                                "message": "成功永久删除 3 个文件",
                                "data": {
                                    "deleted_count": 3
                                }
                            }
                        }
                    }
                }
            }
        },
        401: {
            "description": "未授权",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "未提供认证token",
                        "data": None
                    }
                }
            }
        }
    }
)
async def batch_delete_files(
    request: FileDeleteRequest,
    current_user: dict = Depends(get_current_user_with_roles)
):
    """批量删除文件（管理员永久删除）"""
    try:
        # 管理员默认执行永久删除
        is_admin = current_user.get("is_admin", False)
        actual_permanent = request.permanent or is_admin

        deleted_count = await _run_sync(
            files_service.batch_delete_files,
            request.file_ids,
            current_user["user_id"],
            actual_permanent,
            is_admin
        )

        action = "永久删除" if actual_permanent else "删除"
        return response.success(
            data={"deleted_count": deleted_count},
            message=f"成功{action} {deleted_count} 个文件"
        )

    except Exception as e:
        return response.fail(message=f"批量删除失败: {str(e)}")


@router.delete(
    "/{file_id}",
    summary="删除文件",
    description="""
删除指定的文件。

**参数说明：**
- permanent: 是否永久删除（默认false，仅软删除）

**认证要求：** 需要在请求头中提供有效的 Bearer Token

**删除说明：**
- 软删除（permanent=false）：将文件标记为deleted状态，可以从回收站恢复
- 永久删除（permanent=true）：彻底删除文件，无法恢复
""",
    responses={
        200: {
            "description": "删除成功",
            "content": {
                "application/json": {
                    "examples": {
                        "soft_delete": {
                            "summary": "软删除",
                            "value": {
                                "code": 1,
                                "message": "文件删除成功",
                                "data": {
                                    "file_id": "file_1234567890abcdef"
                                }
                            }
                        },
                        "permanent_delete": {
                            "summary": "永久删除",
                            "value": {
                                "code": 1,
                                "message": "文件永久删除成功",
                                "data": {
                                    "file_id": "file_1234567890abcdef"
                                }
                            }
                        }
                    }
                }
            }
        },
        400: {
            "description": "删除失败",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "删除失败，文件不存在或无权访问",
                        "data": None
                    }
                }
            }
        },
        401: {
            "description": "未授权",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "未提供认证token",
                        "data": None
                    }
                }
            }
        }
    }
)
async def delete_file(
    file_id: str,
    permanent: bool = Query(False, description="是否永久删除"),
    current_user: dict = Depends(get_current_user_with_roles)
):
    """删除文件（管理员永久删除）"""
    try:
        # 管理员默认执行永久删除
        is_admin = current_user.get("is_admin", False)
        actual_permanent = permanent or is_admin

        success = await _run_sync(
            files_service.delete_file,
            file_id,
            current_user["user_id"],
            actual_permanent,
            is_admin
        )

        if not success:
            return response.fail(message="删除失败，文件不存在或无权访问")

        action = "永久删除" if actual_permanent else "删除"
        return response.success(
            data={"file_id": file_id},
            message=f"文件{action}成功"
        )

    except Exception as e:
        return response.fail(message=f"删除文件失败: {str(e)}")


# ============================================================================
# 文件统计
# ============================================================================

@router.get(
    "/stats/my",
    summary="获取我的文件统计",
    description="""
获取当前用户的文件统计信息。

**统计内容包括：**
- 总文件数
- 总存储大小（MB）
- 按文件类型统计
- 按分类统计
- 今日上传数
- 本月上传数

**认证要求：** 需要在请求头中提供有效的 Bearer Token
""",
    responses={
        200: {
            "description": "获取成功",
            "content": {
                "application/json": {
                    "example": {
                        "code": 1,
                        "message": "查询统计信息成功",
                        "data": {
                            "total_files": 150,
                            "total_size_mb": 1024.5,
                            "by_type": {
                                "pdf": 50,
                                "docx": 30,
                                "pptx": 20,
                                "image": 30,
                                "video": 10,
                                "audio": 10
                            },
                            "by_category": {
                                "document": 100,
                                "image": 30,
                                "video": 10,
                                "audio": 10
                            },
                            "today_uploads": 5,
                            "month_uploads": 45
                        }
                    }
                }
            }
        },
        401: {
            "description": "未授权",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "未提供认证token",
                        "data": None
                    }
                }
            }
        }
    }
)
async def get_my_file_stats(
    current_user: dict = Depends(get_current_user_with_roles)
):
    """获取文件统计（管理员可查看全局统计）"""
    try:
        stats = await _run_sync(
            files_service.get_file_stats,
            current_user["user_id"],
            current_user.get("is_admin", False)
        )

        return response.success(
            data=stats,
            message="查询统计信息成功"
        )

    except Exception as e:
        return response.fail(message=f"获取统计信息失败: {str(e)}")
