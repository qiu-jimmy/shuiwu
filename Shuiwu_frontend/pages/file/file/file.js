// pages/file/file/file.js
import { API_BASE_URL, OSS_URL } from '../../../utils/config';

Page({

  /**
   * 页面的初始数据
   */
  data: {
    // OSS图片地址前缀
    ossUrl: OSS_URL,
    // 选中的分类
    selectedCategory: '全部',
    categoryCount: 0,
    // 选中的文件类型
    selectedFileType: '全部',
    fileTypeCount: 0,
    // 文件类型选项
    fileTypeOptions: ['全部', 'PDF', 'DOCX', '其他'],
    // 原始文件列表（用于筛选）
    originalFileList: [],
    // 显示的文件列表（筛选后）
    fileList: [],
    // 当前用户ID（用于检测用户切换）
    currentUserId: null,
    // 分页相关
    currentPage: 1,      // 当前页码
    pageSize: 10,        // 每页条数
    hasMore: true,       // 是否还有更多数据
    isLoadingMore: false // 是否正在加载更多
  },

  /**
   * 检查会员等级是否为免费版
   * @returns {boolean} 如果是免费版返回true，否则返回false
   */
  checkIsFreeMember() {
    try {
      const userInfo = wx.getStorageSync('user_info');
      if (!userInfo || typeof userInfo !== 'object') {
        // 如果没有用户信息，默认允许访问（可能是未登录状态，由其他逻辑处理）
        return false;
      }
      const memberLevel = userInfo.member_level || '';
      // 检查是否为免费版
      return String(memberLevel).toLowerCase() === 'free';
    } catch (e) {
      console.error('检查会员等级失败：', e);
      // 出错时默认允许访问
      return false;
    }
  },

  /**
   * 显示会员升级提示弹窗
   */
  showVipUpgradeModal() {
    wx.showModal({
      title: '会员功能',
      content: '您还不是会员，建议充值开通会员以使用更多功能',
      confirmText: '开通会员',
      cancelText: '取消',
      success: (res) => {
        if (res.confirm) {
          // 用户点击了"开通会员"按钮，跳转到会员购买页面
          wx.navigateTo({
            url: '/subpackage/pages/mine/vip-buy/vip-buy'
          });
        }
      }
    });
  },

  /**
   * 知识库卡片点击事件
   */
  onKnowledgeBaseTap() {
    // 检查会员等级
    if (this.checkIsFreeMember()) {
      // 如果是免费版，显示升级提示
      this.showVipUpgradeModal();
      return;
    }
    // 非免费版，允许进入
    wx.navigateTo({
      url: '/subpackage/pages/file/KnowledgeBase/KnowledgeBase'
    });
  },

  /**
   * 分类选择改变事件
   */
  onCategoryChange(e) {
    const { value, item } = e.detail;
    this.setData({
      selectedCategory: value
    });
    
    // 根据选中的分类筛选文件列表
    this.filterFileListByCategory(item);
  },


  /**
   * 根据分类筛选文件列表
   */
  filterFileListByCategory(categoryData) {
    // 更新选中的分类
    this.setData({
      selectedCategory: categoryData.type_name || '全部',
      selectedCategoryId: categoryData.type_id
    });
    
    // 调用统一的筛选方法
    this.filterFileList();
  },

  /**
   * 文件类型选择点击事件
   */
  onFileTypeTap() {
    const that = this;
    wx.showActionSheet({
      itemList: this.data.fileTypeOptions,
      success(res) {
        const selectedType = that.data.fileTypeOptions[res.tapIndex];
        that.setData({
          selectedFileType: selectedType
        });
        // 筛选文件列表
        that.filterFileList();
      },
      fail(res) {
        console.log(res.errMsg);
      }
    });
  },

  /**
   * 根据文件类型和分类筛选文件列表
   */
  filterFileList() {
    const { originalFileList, selectedFileType, selectedCategory } = this.data;
    let filteredList = originalFileList;

    // 先按文件类型筛选
    if (selectedFileType !== '全部') {
      filteredList = filteredList.filter(file => {
        // file.type 已经是标准化的类型（PDF、DOCX、其他）
        return file.type === selectedFileType;
      });
    }
    // 再按分类筛选（如果分类选择器返回了分类信息）
    // 文件的 category 字段存储的是 kb_name，需要与选中的分类名称匹配
    // 如果 selectedCategory 是 "全部"，则不过滤分类
    if (selectedCategory && selectedCategory !== '全部') {
      filteredList = filteredList.filter(file => {
        // 通过 category 或 kb_name 字段匹配选中的分类名称
        // category 字段在数据映射时已经设置为 kb_name
        return file.category === selectedCategory;
      });
    }

    // 确保每个文件都有 translateX 属性
    filteredList = filteredList.map(file => ({
      ...file,
      translateX: file.translateX || 0
    }));

    this.setData({
      fileList: filteredList
    });
    this.updateFileCounts();
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
  },

  /**
   * 添加按钮点击事件
   */
  onAddTap() {
    // 检查会员等级
    if (this.checkIsFreeMember()) {
      // 如果是免费版，显示升级提示
      this.showVipUpgradeModal();
      return;
    }
    // 非免费版，允许进入
    wx.navigateTo({
      url: '/subpackage/pages/file/add/add'
    });
  },

  /**
   * 文件列表变化事件（来自组件）
   */
  onFileListChange(e) {
    const { fileList } = e.detail;
    this.setData({
      fileList: fileList
    });
  },

  /**
   * 文件卡片点击事件（预览文件信息）
   */
  onFileTap(e) {
    const { fileId } = e.detail;
    
    // 调用预览文件组件的方法
    const previewFileComponent = this.selectComponent('#preview-file');
    if (previewFileComponent) {
      previewFileComponent.previewFile(fileId);
    }
  },

  /**
   * 删除文件
   */
  onDeleteFile(e) {
    const { fileId } = e.detail;
    const that = this;
    
    wx.showModal({
      title: '提示',
      content: '确定要删除这个文件吗？',
      success(res) {
        if (res.confirm) {
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
          wx.showLoading({
            title: '删除中...',
            mask: true
          });

          // 发送 DELETE 请求到后端
          wx.request({
            url: `${API_BASE_URL}/api/files/${fileId}?permanent=true`,
            method: 'DELETE',
            header: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${accessToken}`
            },
            success(res) {
              wx.hideLoading();
              
              // 检查响应状态
              if (res.statusCode >= 200 && res.statusCode < 300) {
                const payload = res.data || {};
                
                // 如果删除成功
                if (payload.code === 1) {
                  // 从原始列表中删除
                  const originalFileList = that.data.originalFileList.filter(file => file.id !== fileId);
                  
                  // 更新原始列表和显示列表
                  that.setData({
                    originalFileList: originalFileList,
                    hasFiles: originalFileList.length > 0
                  });
                  
                  // 更新缓存
                  try {
                    if (originalFileList.length > 0) {
                      wx.setStorageSync('fileList', originalFileList);
                    } else {
                      wx.removeStorageSync('fileList');
                    }
                  } catch (e) {
                    console.error('更新文件列表缓存失败：', e);
                  }
                  
                  // 重新筛选文件列表
                  that.filterFileList();
                  
                  wx.showToast({
                    title: '删除成功',
                    icon: 'success'
                  });
                } else {
                  // 删除失败
                  wx.showToast({
                    title: payload.message || '删除失败',
                    icon: 'none'
                  });
                }
              } else {
                // HTTP 状态码错误
                console.error('删除文件失败：', res);
                wx.showToast({
                  title: '删除失败，请重试',
                  icon: 'none'
                });
              }
            },
            fail(err) {
              wx.hideLoading();
              console.error('删除文件请求失败：', err);
              wx.showToast({
                title: '网络错误，请重试',
                icon: 'none'
              });
            }
          });
        }
      }
    });
  },

  /**
   * 检查用户登录状态
   */
  checkLoginStatus() {
    try {
      const accessToken = wx.getStorageSync('access_token');
      const isLoggedIn = !!accessToken;
      
      this.setData({
        isLoggedIn: isLoggedIn
      });
      
      if (isLoggedIn) {
        // 用户已登录，查询文件列表
        this.fetchUserFiles();
      } else {
        // 用户未登录
        this.setData({
          hasFiles: false,
          originalFileList: [],
          fileList: [],
          categoryCount: 0
        });
      }
    } catch (e) {
      console.error('检查登录状态失败：', e);
      this.setData({
        isLoggedIn: false,
        hasFiles: false,
        originalFileList: [],
        fileList: [],
        categoryCount: 0
      });
    }
  },

  /**
   * 查询用户上传的文件
   * @param {boolean} append 是否在列表尾部追加（用于分页）
   */
  fetchUserFiles(append = false) {
    const accessToken = wx.getStorageSync('access_token');
    
    if (!accessToken) {
      // 如果没有 access_token，设置未登录状态
      this.setData({
        isLoggedIn: false,
        hasFiles: false,
        originalFileList: [],
        fileList: [],
        categoryCount: 0
      });
      return;
    }

    // 获取当前用户ID
    const currentUserId = wx.getStorageSync('user_id') || null;
    const previousUserId = this.data.currentUserId;
    
    // 如果用户切换了，清空缓存
    if (previousUserId !== null && previousUserId !== currentUserId) {
      try {
        wx.removeStorageSync('fileList');
      } catch (e) {
        console.error('清空文件列表缓存失败：', e);
      }
    }
    
    // 更新当前用户ID
    this.setData({
      currentUserId: currentUserId
    });
    
    // 仅在首次加载或刷新时尝试从缓存恢复；分页追加时不重置已有列表
    if (!append) {
      try {
        const cachedFileList = wx.getStorageSync('fileList');
        if (cachedFileList && Array.isArray(cachedFileList) && cachedFileList.length > 0) {
          this.setData({
            hasFiles: true,
            originalFileList: cachedFileList
          });
          // 应用当前的筛选条件
          this.filterFileList();
        } else {
          // 如果缓存为空，确保数量为0
          this.setData({
            categoryCount: 0
          });
        }
      } catch (e) {
        console.error('读取文件列表缓存失败：', e);
      }
    }

    // 显示加载提示或“正在加载更多”状态
    if (append) {
      this.setData({ isLoadingMore: true });
    } else {
      wx.showLoading({
        title: '加载中...',
        mask: true
      });
    }

    // 计算要请求的页码
    const nextPage = append ? (this.data.currentPage + 1) : 1;

    // 调用 API 查询文件列表（支持分页）
    wx.request({
      url: `${API_BASE_URL}/api/files/list?page=${nextPage}&page_size=${this.data.pageSize}`,
      method: 'GET',
      header: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`
      },
      success: (res) => {
        if (!append) {
          wx.hideLoading();
        }
        
        // 检查响应状态
        if (res.statusCode >= 200 && res.statusCode < 300) {
          const payload = res.data || {};
          
          const pageFiles = payload.data && Array.isArray(payload.data.files)
            ? payload.data.files
            : [];

          // 如果返回成功且有数据（数据结构：data { files { 数据 } }）
          if (payload.code === 1 && pageFiles.length > 0) {
            // 将后端数据映射为前端格式
            const normalizedList = pageFiles.map(file => {
              return {
                id: file.file_id,
                name: file.file_name,
                type: this.normalizeFileType(file.file_type),
                size: this.formatFileSize(file.file_size),
                time: this.formatDateTime(file.created_at),
                category: file.kb_name || '暂无分类',
                file_url: file.file_url,
                file_path: file.file_path,
                download_count: file.download_count || 0,
                status: file.status,
                translateX: 0,
                // 保存 user_id 字段，用于过滤
                user_id: file.user_id || null,
                // 保留原始数据以便后续使用
                raw: file
              };
            });
            
            // 合并到现有列表（分页追加）
            const mergedList = append
              ? (this.data.originalFileList || []).concat(normalizedList)
              : normalizedList;

            // 缓存到本地 storage（保存完整列表）
            try {
              wx.setStorageSync('fileList', mergedList);
            } catch (e) {
              console.error('保存文件列表缓存失败：', e);
            }
            
            // 渲染数据
            this.setData({
              hasFiles: true,
              originalFileList: mergedList,
              currentPage: nextPage,
              hasMore: normalizedList.length >= this.data.pageSize,
              isLoadingMore: false
            });
            
            // 应用当前的筛选条件
            this.filterFileList();
          } else {
            // 当前页无数据
            if (append) {
              // 加载更多时无新数据，只标记没有更多
              this.setData({
                hasMore: false,
                isLoadingMore: false
              });
            } else {
              // 首次加载无数据，清除缓存并显示空状态
              try {
                wx.removeStorageSync('fileList');
              } catch (e) {
                console.error('清除文件列表缓存失败：', e);
              }
              this.setData({
                hasFiles: false,
                originalFileList: [],
                fileList: [],
                categoryCount: 0,
                currentPage: 1,
                hasMore: false,
                isLoadingMore: false
              });
            }
          }
        } else {
          // API 请求失败
          console.error('获取文件列表失败：', res);
          // 请求失败时保留缓存数据，不重置为空
          const update = { isLoadingMore: false };
          if (!this.data.hasFiles) {
            Object.assign(update, {
              hasFiles: false,
              originalFileList: [],
              fileList: [],
              categoryCount: 0
            });
          }
          this.setData(update);
        }
      },
      fail: (err) => {
        if (!append) {
          wx.hideLoading();
        }
        console.error('网络请求失败：', err);
        // 网络失败时保留缓存数据，不重置为空
        const update = { isLoadingMore: false };
        if (!this.data.hasFiles) {
          Object.assign(update, {
            hasFiles: false,
            originalFileList: [],
            fileList: [],
            categoryCount: 0
          });
        }
        this.setData(update);
      }
    });
  },

  /**
   * 跳转到登录页面
   */
  navigateToLogin() {
    wx.navigateTo({
      url: '/pages/mine/login/login'
    });
  },

  /**
   * 生命周期函数--监听页面加载
   */
  onLoad(options) {
    // 检查用户登录状态
    this.checkLoginStatus();
    
    // 初始化分类数据（通过组件调用）
    const categorySelector = this.selectComponent('.category-selector');
    if (categorySelector) {
      categorySelector.initCategoryList();
    }
  },

  /**
   * 更新文件数量统计
   */
  updateFileCounts() {
    this.setData({
      categoryCount: this.data.fileList.length,
      fileTypeCount: this.data.fileList.length
    });
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
    // 检查用户是否切换了
    const currentUserId = wx.getStorageSync('user_id') || null;
    const previousUserId = this.data.currentUserId;
    
    // 如果用户切换了，清空缓存和数量
    if (previousUserId !== null && previousUserId !== currentUserId) {
      try {
        wx.removeStorageSync('fileList');
      } catch (e) {
        console.error('清空文件列表缓存失败：', e);
      }
      this.setData({
        originalFileList: [],
        fileList: [],
        categoryCount: 0,
        currentUserId: currentUserId
      });
    }
    
    // 页面显示时重新检查登录状态（可能用户在其他页面登录了）
    this.checkLoginStatus();
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
    // 下拉刷新时重新查询知识库类型并缓存
    // 通过选择器组件的方法刷新
    const categorySelector = this.selectComponent('.category-selector');
    if (categorySelector) {
      categorySelector.refreshCategoryList();
    }
    
    // 停止下拉刷新动画
    wx.stopPullDownRefresh();
  },

  /**
   * 页面上拉触底事件的处理函数
   */
  onReachBottom() {
    // 如果没有更多数据或正在加载中，直接返回
    if (!this.data.hasMore || this.data.isLoadingMore) {
      return;
    }

    // 触底时加载下一页文件列表
    this.fetchUserFiles(true);
  },

  /**
   * 用户点击右上角分享
   */
  onShareAppMessage() {

  }
})