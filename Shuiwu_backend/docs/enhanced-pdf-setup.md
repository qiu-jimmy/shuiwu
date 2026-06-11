# 增强型PDF处理器 - 安装和使用指南

## 概述

系统现在使用增强型PDF处理器，支持多种PDF处理库的自动回退机制，能够处理：

- ✅ 复杂排版的PDF（多栏、图文混排）
- ✅ 包含表格的PDF
- ✅ 加密的PDF文件
- ✅ 损坏或格式异常的PDF
- ✅ 扫描版PDF（需要OCR支持）

## 处理优先级

系统按以下顺序尝试读取PDF：

1. **PyMuPDF (fitz)** - 快速且功能强大
2. **pdfplumber** - 专注表格和复杂布局
3. **pypdf** - 当前方案（兜底）
4. **OCR (Tesseract)** - 处理扫描版PDF（可选）

## 安装步骤

### 基础安装（必需）

安装核心PDF处理库：

```bash
pip install PyMuPDF>=1.23.0 pdfplumber>=0.10.0
```

### OCR支持（可选）

如果需要处理扫描版PDF，需要安装OCR相关依赖：

#### Python包安装

```bash
pip install pytesseract>=0.3.10 pdf2image>=1.16.0 Pillow>=10.0.0
```

#### Tesseract引擎安装

**Windows:**

1. 下载安装程序：https://github.com/UB-Mannheim/tesseract/wiki
2. 安装到默认路径（通常 `C:\Program Files\Tesseract-OCR`）
3. 下载中文语言包：`chi_sim.traineddata`

**macOS:**

```bash
brew install tesseract tesseract-lang
```

**Linux (Ubuntu/Debian):**

```bash
sudo apt-get install tesseract-ocr tesseract-ocr-chi-sim poppler-utils
```

### 完整安装命令

一次性安装所有推荐库：

```bash
# 核心库
pip install PyMuPDF>=1.23.0 pdfplumber>=0.10.0

# OCR支持（可选）
pip install pytesseract>=0.3.10 pdf2image>=1.16.0 Pillow>=10.0.0
```

## 使用方式

### API使用

增强型PDF处理器已集成到知识库上传接口中，无需额外配置。

### 代码示例

```python
from app.utils.enhanced_pdf_reader import EnhancedPDFReader

# 创建读取器实例
reader = EnhancedPDFReader(
    enable_ocr=True,           # 启用OCR
    ocr_lang="chi_sim+eng",    # 中英文识别
    fallback_on_error=True     # 出错时回退到下一个库
)

# 读取PDF文件
documents = reader.read(
    pdf="path/to/file.pdf",
    name="document.pdf",
    password=None  # 如果有密码
)

# 处理文档
for doc in documents:
    print(f"页面: {doc.meta_data['page']}")
    print(f"内容: {doc.content[:100]}...")
```

## 配置选项

### 环境变量

在 `.env` 文件中添加：

```env
# OCR配置
PDF_ENABLE_OCR=true           # 是否启用OCR（默认true）
PDF_OCR_LANG=chi_sim+eng      # OCR语言（默认中英文）
PDF_TESSERACT_PATH=/usr/bin/tesseract  # Tesseract路径（可选）
```

### 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|-----|------|--------|------|
| `enable_ocr` | bool | True | 是否启用OCR处理扫描版PDF |
| `ocr_lang` | str | "chi_sim+eng" | OCR识别语言 |
| `fallback_on_error` | bool | True | 是否在出错时回退到下一个库 |

## 性能对比

| 库 | 速度 | 复杂PDF | 表格提取 | 扫描版PDF |
|----|------|---------|----------|-----------|
| PyMuPDF | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ❌ |
| pdfplumber | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ❌ |
| pypdf | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ❌ |
| OCR | ⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |

## 故障排除

### 问题1：PyMuPDF安装失败

```bash
# 尝试使用pip安装
pip install pymupdf

# 或者使用conda
conda install -c conda-forge pymupdf
```

### 问题2：OCR识别失败

1. 确认Tesseract已正确安装：
   ```bash
   tesseract --version
   ```

2. 检查语言包是否安装：
   ```bash
   tesseract --list-langs
   ```

3. 如果需要指定Tesseract路径：
   ```python
   import pytesseract
   pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
   ```

### 问题3：pdf2image需要poppler

**macOS:**
```bash
brew install poppler
```

**Linux:**
```bash
sudo apt-get install poppler-utils
```

**Windows:**
下载并添加到PATH：http://blog.alivate.com.au/poppler-windows/

### 问题4：内存不足

处理大文件时可能出现内存问题，可以：

1. 减小分块大小
2. 逐页处理而不是一次性读取
3. 增加系统内存限制

## 测试

测试增强型PDF处理器：

```python
import sys
sys.path.insert(0, 'D:/download/taxation/Shuiwu_backend')

from app.utils.enhanced_pdf_reader import EnhancedPDFReader

# 测试读取
reader = EnhancedPDFReader()
docs = reader.read("test.pdf")

print(f"成功读取 {len(docs)} 个文档块")
for i, doc in enumerate(docs[:3]):
    print(f"\n文档块 {i+1}:")
    print(f"  页面: {doc.meta_data.get('page')}")
    print(f"  内容预览: {doc.content[:100]}...")
```

## 更新日志

### v1.0.0 (2024-01-19)

- ✅ 添加PyMuPDF支持（快速PDF处理）
- ✅ 添加pdfplumber支持（表格提取）
- ✅ 添加OCR支持（扫描版PDF）
- ✅ 实现自动回退机制
- ✅ 支持加密PDF
- ✅ 改进错误处理和日志
