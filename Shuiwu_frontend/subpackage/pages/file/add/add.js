// pages/file/add/add.js
import { API_BASE_URL, OSS_URL } from '../../../../utils/config';
Page({

  /**
   * 页面的初始数据
   */
  data: {
    // OSS图片地址前缀
    ossUrl: OSS_URL,
    // 已上传的文件列表
    fileList: [],
    // 是否可以提交
    canSubmit: false
  },

  /**
   * 生命周期函数--监听页面加载
   */
  onLoad(options) {

  },

  /**
   * 选择文件
   */
  onChooseFile() {
    const that = this;
    const currentFileCount = this.data.fileList.length;
    const maxFiles = 3; // 最多只能上传3个文件
    
    // 检查是否已达到最大文件数
    if (currentFileCount >= maxFiles) {
      wx.showToast({
        title: `最多只能上传${maxFiles}个文件`,
        icon: 'none'
      });
      return;
    }

    // 计算还可以选择的文件数量
    const remainingCount = maxFiles - currentFileCount;
    
    wx.chooseMessageFile({
      count: remainingCount, // 最多可以选择剩余数量的文件
      type: 'file',
      success(res) {
        const tempFiles = res.tempFiles;
        const newFiles = tempFiles.map(file => {
          // 保存原始文件名（未处理），避免出现乱码
          const original_filename = file.name || '';
          
          // 获取文件名并确保不是乱码（用于显示）
          let fileName = original_filename;
          // 用于列表展示的截断文件名（限制为 12 个字符）
          let displayName = '';
          
          // 处理文件名编码问题
          // 小程序返回的文件名通常是 UTF-8 编码的，但需要确保正确处理
          try {
            // 如果文件名是字符串，直接使用
            if (typeof fileName === 'string') {
              // 清理文件名中的非法字符，但保留中文和常见字符
              // 移除或替换可能导致问题的字符
              fileName = fileName.trim();
              
              // 如果文件名为空或无效，使用默认名称
              if (!fileName || fileName.length === 0) {
                const timestamp = Date.now();
                fileName = `文件_${timestamp}`;
              }
            } else {
              // 如果文件名不是字符串，尝试转换或使用默认名称
              fileName = String(fileName) || `文件_${Date.now()}`;
            }
          } catch (e) {
            console.error('解析文件名失败：', e);
            // 如果解析失败，使用时间戳作为文件名
            fileName = `文件_${Date.now()}`;
          }

          // 生成用于展示的文件名：超过 12 个字符时截断并加省略号
          const maxNameLength = 12;
          if (typeof fileName === 'string' && fileName.length > maxNameLength) {
            displayName = fileName.slice(0, maxNameLength) + '...';
          } else {
            displayName = fileName;
          }
          
          // 获取文件扩展名
          const lastDotIndex = fileName.lastIndexOf('.');
          let ext = '';
          if (lastDotIndex !== -1 && lastDotIndex < fileName.length - 1) {
            ext = fileName.substring(lastDotIndex + 1).toUpperCase();
          }
          
          let type = 'OTHER';
          if (ext === 'PDF') {
            type = 'PDF';
          } else if (ext === 'DOCX' || ext === 'DOC') {
            type = 'DOCX';
          }

          // 格式化文件大小
          const size = that.formatFileSize(file.size);

          return {
            name: fileName, // 完整文件名
            displayName, // 截断后的文件名（用于列表展示）
            original_filename: original_filename || fileName, // 保存原始文件名，避免出现乱码
            path: file.path,
            size: size,
            type: type,
            originalSize: file.size, // 保存原始大小用于上传
            uploading: false, // 上传状态
            uploadSuccess: false, // 上传成功状态
            uploadError: null // 上传错误信息
          };
        });

        that.setData({
          fileList: [...that.data.fileList, ...newFiles]
        });
        that.updateSubmitStatus();
      },
      fail(err) {
        console.error('选择文件失败：', err);
        wx.showToast({
          title: '选择文件失败',
          icon: 'none'
        });
      }
    });
  },

  /**
   * 删除文件
   */
  onDeleteFile(e) {
    const index = e.currentTarget.dataset.index;
    const fileList = this.data.fileList;
    fileList.splice(index, 1);
    this.setData({
      fileList: fileList
    });
    this.updateSubmitStatus();
  },

  /**
   * 格式化文件大小
   */
  formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  },

  /**
   * 更新提交按钮状态
   */
  updateSubmitStatus() {
    const canSubmit = this.data.fileList.length > 0;
    this.setData({
      canSubmit: canSubmit
    });
  },

  /**
   * 提交表单
   */
  onSubmit() {
    if (!this.data.canSubmit) {
      return;
    }

    if (this.data.fileList.length === 0) {
      wx.showToast({
        title: '请至少上传一个文件',
        icon: 'none'
      });
      return;
    }

    // 检查登录状态
    const accessToken = wx.getStorageSync('access_token');
    if (!accessToken) {
      wx.showToast({
        title: '请先登录',
        icon: 'none'
      });
      setTimeout(() => {
        wx.navigateTo({
          url: '/pages/mine/login/login'
        });
      }, 1500);
      return;
    }

    // 检查文件数量限制
    if (this.data.fileList.length > 3) {
      wx.showToast({
        title: '最多只能上传3个文件',
        icon: 'none'
      });
      return;
    }

    // 开始上传文件
    this.uploadFiles();
  },

  /**
   * 上传文件
   */
  uploadFiles() {
    const fileList = this.data.fileList;
    const accessToken = wx.getStorageSync('access_token');
    
    if (fileList.length === 0) {
      return;
    }

    // 显示加载提示
    wx.showLoading({
      title: '上传中...',
      mask: true
    });

    // 更新文件状态为上传中
    const updatedFileList = fileList.map(file => ({
      ...file,
      uploading: true,
      uploadSuccess: false,
      uploadError: null
    }));
    this.setData({ fileList: updatedFileList });

    // 如果是单个文件，直接上传
    if (fileList.length === 1) {
      this.uploadSingleFile(fileList[0], accessToken, 0);
    } else {
      // 多个文件，循环上传
      this.uploadFilesSequentially(fileList, accessToken, 0);
    }
  },

  /**
   * 上传单个文件
   */
  uploadSingleFile(file, accessToken, index) {
    const that = this;
    
    wx.uploadFile({
      url: `${API_BASE_URL}/api/files/upload`,
      filePath: file.path,
      name: 'file',
      formData: {
        'original_filename': file.original_filename || file.name // 使用原始文件名，避免出现乱码
      },
      header: {
        'Authorization': `Bearer ${accessToken}`
      },
      success(res) {
        wx.hideLoading();
        
        try {
          const data = typeof res.data === 'string' ? JSON.parse(res.data) : res.data;
          
          if (res.statusCode >= 200 && res.statusCode < 300 && data.code === 1) {
            // 上传成功
            const fileList = that.data.fileList;
            fileList[index] = {
              ...fileList[index],
              uploading: false,
              uploadSuccess: true
            };
            that.setData({ fileList });
            
            wx.showToast({
              title: '上传成功',
              icon: 'success'
            });
            
            // 延迟返回上一页
            setTimeout(() => {
              wx.navigateBack();
            }, 1500);
          } else {
            // 上传失败
            that.handleUploadError(index, data.message || '上传失败');
          }
        } catch (e) {
          console.error('解析响应失败：', e);
          that.handleUploadError(index, '上传失败，请重试');
        }
      },
      fail(err) {
        wx.hideLoading();
        console.error('上传文件失败：', err);
        that.handleUploadError(index, err.errMsg || '网络错误，请重试');
      }
    });
  },

  /**
   * 顺序上传多个文件
   */
  uploadFilesSequentially(fileList, accessToken, currentIndex) {
    const that = this;
    
    if (currentIndex >= fileList.length) {
      // 所有文件上传完成
      wx.hideLoading();
      
      // 检查是否有失败的文件
      const hasError = fileList.some(file => file.uploadError);
      const successCount = fileList.filter(file => file.uploadSuccess).length;
      
      if (hasError) {
        wx.showToast({
          title: `${successCount}/${fileList.length} 个文件上传成功`,
          icon: 'none',
          duration: 2000
        });
      } else {
        wx.showToast({
          title: '全部上传成功',
          icon: 'success'
        });
        
        // 延迟返回上一页
        setTimeout(() => {
          wx.navigateBack();
        }, 1500);
      }
      return;
    }

    const file = fileList[currentIndex];
    
    wx.uploadFile({
      url: `${API_BASE_URL}/api/files/upload`,
      filePath: file.path,
      name: 'file',
      formData: {
        'original_filename': file.original_filename || file.name // 使用原始文件名，避免出现乱码
      },
      header: {
        'Authorization': `Bearer ${accessToken}`
      },
      success(res) {
        try {
          const data = typeof res.data === 'string' ? JSON.parse(res.data) : res.data;
          
          if (res.statusCode >= 200 && res.statusCode < 300 && data.code === 1) {
            // 当前文件上传成功
            const updatedFileList = that.data.fileList;
            updatedFileList[currentIndex] = {
              ...updatedFileList[currentIndex],
              uploading: false,
              uploadSuccess: true
            };
            that.setData({ fileList: updatedFileList });
            
            // 继续上传下一个文件
            that.uploadFilesSequentially(fileList, accessToken, currentIndex + 1);
          } else {
            // 当前文件上传失败
            that.handleUploadError(currentIndex, data.message || '上传失败');
            // 继续上传下一个文件
            that.uploadFilesSequentially(fileList, accessToken, currentIndex + 1);
          }
        } catch (e) {
          console.error('解析响应失败：', e);
          that.handleUploadError(currentIndex, '上传失败，请重试');
          // 继续上传下一个文件
          that.uploadFilesSequentially(fileList, accessToken, currentIndex + 1);
        }
      },
      fail(err) {
        console.error(`上传文件 ${currentIndex + 1} 失败：`, err);
        that.handleUploadError(currentIndex, err.errMsg || '网络错误，请重试');
        // 继续上传下一个文件
        that.uploadFilesSequentially(fileList, accessToken, currentIndex + 1);
      }
    });
  },

  /**
   * 处理上传错误
   */
  handleUploadError(index, errorMessage) {
    const fileList = this.data.fileList;
    fileList[index] = {
      ...fileList[index],
      uploading: false,
      uploadSuccess: false,
      uploadError: errorMessage
    };
    this.setData({ fileList });
  },

  /**
   * 生命周期函数--监听页面初次渲染完成
   */
  onReady() {

  },

  /**
   * 生命周期函数--监听页面显示
   */
  onShow() {

  },

  /**
   * 生命周期函数--监听页面隐藏
   */
  onHide() {

  },

  /**
   * 生命周期函数--监听页面卸载
   */
  onUnload() {

  },

  /**
   * 页面相关事件处理函数--监听用户下拉动作
   */
  onPullDownRefresh() {

  },

  /**
   * 页面上拉触底事件的处理函数
   */
  onReachBottom() {

  },

  /**
   * 用户点击右上角分享
   */
  onShareAppMessage() {

  }
})
