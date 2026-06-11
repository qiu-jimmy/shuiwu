// pages/file/component/PreviewFile/PreviewFile.js
import { API_BASE_URL } from '../../../../utils/config';

Component({
  /**
   * 组件的属性列表
   */
  properties: {
    // 文件ID
    fileId: {
      type: String,
      value: ''
    },
    // 是否显示预览弹窗
    show: {
      type: Boolean,
      value: false
    }
  },

  /**
   * 组件的初始数据
   */
  data: {
    fileInfo: null,
    loading: false
  },

  /**
   * 组件的方法列表
   */
  methods: {
    /**
     * 预览文件信息
     */
    previewFile(fileId) {
      if (!fileId) {
        return;
      }

      // 检查登录状态
      const accessToken = wx.getStorageSync('access_token');
      if (!accessToken) {
        wx.showToast({
          title: '请先登录',
          icon: 'none'
        });
        return;
      }

      // 显示加载提示
      this.setData({ loading: true });
      wx.showLoading({
        title: '加载中...',
        mask: true
      });

      // 发送 GET 请求获取文件详情
      wx.request({
        url: `${API_BASE_URL}/api/files/${fileId}`,
        method: 'GET',
        header: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`
        },
        success: (res) => {
          wx.hideLoading();
          this.setData({ loading: false });
          
          // 检查响应状态
          if (res.statusCode >= 200 && res.statusCode < 300) {
            const payload = res.data || {};
            
            // 如果获取成功
            if (payload.code === 1 && payload.data) {
              const fileData = payload.data;
              this.setData({
                fileInfo: fileData
              });
              // 直接打开文件预览（不显示弹窗）
              this.openFilePreview(fileData);
            } else {
              wx.showToast({
                title: payload.message || '获取文件信息失败',
                icon: 'none'
              });
            }
          } else {
            console.error('获取文件信息失败：', res);
            wx.showToast({
              title: '获取文件信息失败',
              icon: 'none'
            });
          }
        },
        fail: (err) => {
          wx.hideLoading();
          this.setData({ loading: false });
          console.error('网络请求失败：', err);
          wx.showToast({
            title: '网络错误，请重试',
            icon: 'none'
          });
        }
      });
    },

    /**
     * 打开文件预览
     */
    openFilePreview(fileData) {
      if (!fileData.file_id) {
        wx.showToast({
          title: '文件ID不存在',
          icon: 'none'
        });
        return;
      }

      const fileId = fileData.file_id;
      const fileType = this.normalizeFileType(fileData.file_type);
      const accessToken = wx.getStorageSync('access_token');
      
      // 显示加载提示
      wx.showLoading({
        title: '准备预览...',
        mask: true
      });

      // 先获取下载链接
      wx.request({
        url: `${API_BASE_URL}/api/files/${fileId}/download`,
        method: 'GET',
        header: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`
        },
        success: (res) => {
          if (res.statusCode >= 200 && res.statusCode < 300) {
            const payload = res.data || {};
            
            // 获取下载链接
            let downloadUrl = '';
            if (payload.code === 1 && payload.data) {
              // 如果返回的是对象，可能包含 download_url 字段
              downloadUrl = payload.data.download_url || payload.data.url || payload.data;
            } else if (typeof payload === 'string') {
              downloadUrl = payload;
            } else if (payload.url) {
              downloadUrl = payload.url;
            }
            
            if (!downloadUrl) {
              wx.hideLoading();
              wx.showToast({
                title: '获取下载链接失败',
                icon: 'none'
              });
              return;
            }

            // 使用微信原生API下载文件
            wx.downloadFile({
              url: downloadUrl,
              header: {
                'Authorization': `Bearer ${accessToken}`
              },
              success: (downloadRes) => {
                wx.hideLoading();
                
                if (downloadRes.statusCode === 200 && downloadRes.tempFilePath) {
                  const filePath = downloadRes.tempFilePath;
                  
                  // 使用 wx.openDocument 打开文件，添加 showMenu 字段
                  wx.openDocument({
                    filePath: filePath,
                    fileType: fileType.toLowerCase(),
                    showMenu: true, // 显示菜单，允许用户分享、保存等操作
                    success: () => {
                      console.log('文件打开成功');
                    },
                    fail: (err) => {
                      console.error('打开文件失败：', err);
                      wx.showToast({
                        title: err.errMsg || '无法预览此文件类型',
                        icon: 'none',
                        duration: 2000
                      });
                    }
                  });
                } else {
                  wx.showToast({
                    title: '下载文件失败',
                    icon: 'none'
                  });
                }
              },
              fail: (err) => {
                wx.hideLoading();
                console.error('下载文件失败：', err);
                wx.showToast({
                  title: err.errMsg || '下载文件失败，请重试',
                  icon: 'none',
                  duration: 2000
                });
              }
            });
          } else {
            wx.hideLoading();
            wx.showToast({
              title: '获取下载链接失败',
              icon: 'none'
            });
          }
        },
        fail: (err) => {
          wx.hideLoading();
          console.error('获取下载链接失败：', err);
          wx.showToast({
            title: err.errMsg || '获取下载链接失败，请重试',
            icon: 'none',
            duration: 2000
          });
        }
      });
    },

    /**
     * 下载文件（供外部调用）
     */
    downloadFile(fileId) {
      // 如果传入了 fileId，直接使用；否则使用当前 fileInfo 中的 file_id
      const targetFileId = fileId || (this.data.fileInfo && this.data.fileInfo.file_id);
      
      if (!targetFileId) {
        wx.showToast({
          title: '文件ID不存在',
          icon: 'none'
        });
        return;
      }

      const accessToken = wx.getStorageSync('access_token');
      if (!accessToken) {
        wx.showToast({
          title: '请先登录',
          icon: 'none'
        });
        return;
      }

      wx.showLoading({
        title: '下载中...',
        mask: true
      });

      // 先获取下载链接
      wx.request({
        url: `${API_BASE_URL}/api/files/${targetFileId}/download`,
        method: 'GET',
        header: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`
        },
        success: (res) => {
          if (res.statusCode >= 200 && res.statusCode < 300) {
            const payload = res.data || {};
            
            // 获取下载链接
            let downloadUrl = '';
            if (payload.code === 1 && payload.data) {
              // 如果返回的是对象，可能包含 download_url 字段
              downloadUrl = payload.data.download_url || payload.data.url || payload.data;
            } else if (typeof payload === 'string') {
              downloadUrl = payload;
            } else if (payload.url) {
              downloadUrl = payload.url;
            }
            
            if (!downloadUrl) {
              wx.hideLoading();
              wx.showToast({
                title: '获取下载链接失败',
                icon: 'none'
              });
              return;
            }

            // 使用微信原生API下载文件
            wx.downloadFile({
              url: downloadUrl,
              header: {
                'Authorization': `Bearer ${accessToken}`
              },
              success: (downloadRes) => {
                wx.hideLoading();
                
                if (downloadRes.statusCode === 200 && downloadRes.tempFilePath) {
                  const tempFilePath = downloadRes.tempFilePath;
                  
                  // 保存文件到本地
                  wx.saveFile({
                    tempFilePath: tempFilePath,
                    success: (saveRes) => {
                      wx.showToast({
                        title: '下载成功',
                        icon: 'success',
                        duration: 2000
                      });
                      console.log('文件保存路径：', saveRes.savedFilePath);
                      
                      // 下载成功后自动打开文件
                      const currentFileInfo = this.data.fileInfo;
                      if (currentFileInfo && currentFileInfo.file_type) {
                        const fileType = this.normalizeFileType(currentFileInfo.file_type);
                        wx.openDocument({
                          filePath: saveRes.savedFilePath,
                          fileType: fileType.toLowerCase(),
                          showMenu: true, // 显示菜单，允许用户分享、保存等操作
                          success: () => {
                            console.log('文件打开成功');
                          },
                          fail: (err) => {
                            console.error('打开文件失败：', err);
                          }
                        });
                      }
                    },
                    fail: (err) => {
                      console.error('保存文件失败：', err);
                      wx.showToast({
                        title: err.errMsg || '保存文件失败',
                        icon: 'none',
                        duration: 2000
                      });
                    }
                  });
                } else {
                  wx.showToast({
                    title: '下载失败',
                    icon: 'none'
                  });
                }
              },
              fail: (err) => {
                wx.hideLoading();
                console.error('下载文件失败：', err);
                wx.showToast({
                  title: err.errMsg || '下载失败，请重试',
                  icon: 'none',
                  duration: 2000
                });
              }
            });
          } else {
            wx.hideLoading();
            wx.showToast({
              title: '获取下载链接失败',
              icon: 'none'
            });
          }
        },
        fail: (err) => {
          wx.hideLoading();
          console.error('获取下载链接失败：', err);
          wx.showToast({
            title: err.errMsg || '获取下载链接失败，请重试',
            icon: 'none',
            duration: 2000
          });
        }
      });
    },

    /**
     * 标准化文件类型：如果不是PDF或DOCX，则返回"其他"
     */
    normalizeFileType(type) {
      const upperType = (type || '').toUpperCase();
      if (upperType === 'PDF') {
        return 'PDF';
      } else if (upperType === 'DOCX' || upperType === 'DOC') {
        return 'DOCX';
      } else {
        return '其他';
      }
    },

    /**
     * 格式化文件大小
     */
    formatFileSize(bytes) {
      if (!bytes || bytes === 0) return '0 B';
      const k = 1024;
      const sizes = ['B', 'KB', 'MB', 'GB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    },

    /**
     * 格式化日期时间
     */
    formatDateTime(dateString) {
      if (!dateString) return '';
      
      try {
        const date = new Date(dateString);
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        
        // 格式：2026-01-15 11:53
        return `${year}-${month}-${day} ${hours}:${minutes}`;
      } catch (e) {
        console.error('格式化日期失败：', e);
        return dateString;
      }
    }
  }
});
