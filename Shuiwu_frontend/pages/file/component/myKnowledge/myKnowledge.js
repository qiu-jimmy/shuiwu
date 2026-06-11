// pages/file/component/myKnowledge/myKnowledge.js
import { API_BASE_URL, OSS_URL } from '../../../../utils/config';

Component({

  /**
   * 组件的属性列表
   */
  properties: {
    // 选中的分类
    selectedCategory: {
      type: String,
      value: '全部',
      observer: function(newVal, oldVal) {
        // 当分类改变时，触发筛选
        if (newVal !== oldVal && this.data.originalList.length > 0) {
          this.filterByCategoryValue(newVal);
        }
      }
    }
  },

  /**
   * 组件的初始数据
   */
  data: {
    // OSS图片地址前缀
    ossUrl: OSS_URL,
    // 是否已登录
    isLoggedIn: false,
    // 是否有数据
    hasData: false,
    // 我的知识库原始列表（未筛选）
    originalList: [],
    // 我的知识库列表（筛选后）
    fileList: [],
    // 触摸相关
    touchStartX: 0,
    touchStartY: 0,
    currentIndex: -1,
    isSwipeAction: false, // 标记是否发生了滑动操作
    // 屏幕信息（用于单位转换）
    screenWidth: 375,
    // 添加文件弹窗相关
    showAddFileModal: false,
    currentKbInfo: {}, // 当前选中的知识库信息
    fileListForSelect: [], // 用于选择的文件列表
    selectedFileCount: 0, // 选中的文件数量
    isAllSelected: false, // 是否全选
    // 文档列表弹窗相关
    showDocModal: false, // 是否显示文档列表弹窗
    currentKbName: '', // 当前选中的知识库名称
    totalDocuments: 0, // 文档总数
    documentList: [], // 文档列表
    // 筛选相关
    categoryCount: 0 // 知识库数量
  },

  /**
   * 组件生命周期函数--组件实例刚刚被创建
   */
  lifetimes: {
    attached() {
      // 获取屏幕宽度
      const systemInfo = wx.getSystemInfoSync();
      this.setData({
        screenWidth: systemInfo.windowWidth
      });
      // 组件挂载时加载我的知识库列表
      this.loadMyKnowledgeList();
    }
  },

  /**
   * 组件的方法列表
   */
  methods: {
    /**
     * 从缓存中提取 token
     * @returns {string} token 字符串
     */
    getTokenFromStorage() {
      const accessTokenData = wx.getStorageSync('access_token');
      // 从 access_token 中提取 token（可能是字符串或对象）
      if (typeof accessTokenData === 'string') {
        return accessTokenData;
      } else if (accessTokenData && typeof accessTokenData === 'object') {
        // 如果是对象，尝试提取 token 字段
        return accessTokenData.token || accessTokenData.access_token || accessTokenData.value || '';
      }
      return '';
    },

    /**
     * 从缓存中获取 user_id
     * @returns {string} user_id 字符串
     */
    getUserIdFromStorage() {
      // 方式1: 直接从 user_id key 获取
      let userId = wx.getStorageSync('user_id');
      if (userId) {
        return userId;
      }
      
      // 方式2: 从 user_info 对象中获取
      const userInfo = wx.getStorageSync('user_info');
      if (userInfo && typeof userInfo === 'object') {
        userId = userInfo.user_id || userInfo.id || userInfo.userId || '';
        if (userId) {
          return userId;
        }
      }
      
      return '';
    },

    /**
     * 加载我的知识库列表
     * @param {Boolean} forceRefresh - 是否强制刷新（跳过缓存）
     */
    loadMyKnowledgeList(forceRefresh = false) {
      // 1. 检查是否有 access_token
      const accessToken = this.getTokenFromStorage();
      
      if (!accessToken) {
        // 未登录，显示提示
        this.setData({
          isLoggedIn: false,
          hasData: false,
          originalList: [],
          fileList: [],
          categoryCount: 0
        }, () => {
          // 通知父组件更新数量
          this.triggerEvent('countchange', {
            count: 0
          });
        });
        return;
      }

      // 已登录，设置登录状态
      this.setData({
        isLoggedIn: true
      });

      // 2. 如果不是强制刷新，先尝试从缓存加载并显示（参考 file.js 的逻辑）
      if (!forceRefresh) {
        try {
          const cachedList = wx.getStorageSync('myKnowledgeList');
          if (cachedList && Array.isArray(cachedList) && cachedList.length > 0) {
            // 从缓存中读取 categoryList 并补充缺失的 type_name
            const categoryList = wx.getStorageSync('categoryList') || [];
            const typeMap = {};
            categoryList.forEach(category => {
              if (category.type_id && category.type_name) {
                typeMap[category.type_id] = category.type_name;
              }
            });
            
            // 确保每个 item 都有 translateX: 0 和 type_name
            const listWithTranslateX = cachedList.map(item => {
              const baseItem = { ...item, translateX: 0 };
              // 如果 item 没有 type_name 但 type_id 存在，从 categoryList 中查找
              if (!baseItem.type_name && baseItem.type_id && typeMap[baseItem.type_id]) {
                baseItem.type_name = typeMap[baseItem.type_id];
              }
              return baseItem;
            });
            
            this.setData({
              hasData: true,
              originalList: listWithTranslateX,
              fileList: listWithTranslateX,
              categoryCount: listWithTranslateX.length
            }, () => {
              // 如果有选中的分类，进行筛选
              if (this.properties.selectedCategory && this.properties.selectedCategory !== '全部') {
                this.filterByCategoryValue(this.properties.selectedCategory);
              } else {
                // 通知父组件更新数量
                this.triggerEvent('countchange', {
                  count: this.data.fileList.length
                });
              }
            });
          }
        } catch (e) {
          console.error('读取知识库列表缓存失败：', e);
        }
      } else {
        // 强制刷新时，不清空显示状态，保留现有数据直到新数据加载完成
        // 这样用户不会看到列表突然消失
      }

      // 3. 发送 GET 请求查询我的知识库列表（无论是否有缓存都请求最新数据）
      wx.request({
        url: `${API_BASE_URL}/api/knowledge-base/list/user`,
        method: 'GET',
        header: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`
        },
        timeout: 30000, // 设置30秒超时
        success: (res) => {
          // 检查并显示后端返回的 message 信息
          if (res.data && res.data.results && res.data.results.message) {
            wx.showToast({
              title: res.data.results.message,
              icon: 'none',
              duration: 2000
            });
          }

          // 检查响应状态
          if (res.statusCode >= 200 && res.statusCode < 300) {
            const responseData = res.data;
            // 根据实际返回的数据结构处理
            let knowledgeList = [];
            if (responseData.code === 1 && responseData.data) {
              // 如果返回的是数组
              if (Array.isArray(responseData.data)) {
                knowledgeList = responseData.data;
              } else if (Array.isArray(responseData.data.list)) {
                knowledgeList = responseData.data.list;
              } else if (Array.isArray(responseData.data.items)) {
                knowledgeList = responseData.data.items;
              }
            } else if (Array.isArray(responseData)) {
              // 如果直接返回数组
              knowledgeList = responseData;
            }

            // 4. 如果有知识库列表，查询每个知识库的类型信息
            if (knowledgeList.length > 0) {
              this.loadKnowledgeTypes(knowledgeList, accessToken);
            } else {
              // 没有数据，清除缓存并显示空状态
              try {
                wx.removeStorageSync('myKnowledgeList');
              } catch (e) {
                console.error('清除知识库列表缓存失败：', e);
              }
              this.setData({
                hasData: false,
                originalList: [],
                fileList: [],
                categoryCount: 0
              }, () => {
                // 通知父组件更新数量
                this.triggerEvent('countchange', {
                  count: 0
                });
              });
            }
          } else {
            // API 请求失败
            console.error('获取我的知识库列表失败:', res);
            // 请求失败时保留缓存数据，不重置为空（参考 file.js 的逻辑）
            if (!this.data.hasData) {
              this.setData({
                hasData: false,
                originalList: [],
                fileList: [],
                categoryCount: 0
              });
            }
          }
        },
        fail: (err) => {
          console.error('请求我的知识库列表失败:', err);
          // 网络失败时保留缓存数据，不重置为空（参考 file.js 的逻辑）
          if (!this.data.hasData) {
            this.setData({
              hasData: false,
              originalList: [],
              fileList: [],
              categoryCount: 0
            });
          }
        }
      });
    },

    /**
     * 加载知识库类型信息并更新列表
     */
    loadKnowledgeTypes(knowledgeList, accessToken) {
      // 收集所有需要查询的 type_id（去重）
      const typeIds = [...new Set(knowledgeList.map(item => item.type_id).filter(Boolean))];
      
      if (typeIds.length === 0) {
        // 如果没有 type_id，直接更新数据，确保每个 item 都有 translateX: 0
        const listWithTranslateX = knowledgeList.map(item => ({ ...item, translateX: 0 }));
        wx.setStorageSync('myKnowledgeList', knowledgeList);
        this.setData({
          hasData: listWithTranslateX.length > 0,
          originalList: listWithTranslateX,
          fileList: listWithTranslateX,
          categoryCount: listWithTranslateX.length
        }, () => {
          // 如果有选中的分类，进行筛选
          if (this.properties.selectedCategory && this.properties.selectedCategory !== '全部') {
            this.filterByCategoryValue(this.properties.selectedCategory);
          } else {
            // 通知父组件更新数量
            this.triggerEvent('countchange', {
              count: this.data.fileList.length
            });
          }
        });
        return;
      }

      // 先从缓存中读取 categoryList 创建类型映射
      const categoryList = wx.getStorageSync('categoryList') || [];
      const typeMap = {};
      
      // 从 categoryList 中创建 type_id 到 type_name 的映射
      categoryList.forEach(category => {
        if (category.type_id && category.type_name) {
          typeMap[category.type_id] = category.type_name;
        }
      });

      // 找出缓存中没有的类型ID（需要从API获取）
      const missingTypeIds = typeIds.filter(typeId => !typeMap[typeId]);
      
      // 如果缓存中有所有类型信息，直接使用缓存数据
      if (missingTypeIds.length === 0) {
        // 将 type_name 添加到每个知识库对象中，并确保 translateX: 0
        const updatedList = knowledgeList.map(item => {
          const baseItem = item.type_id && typeMap[item.type_id] 
            ? { ...item, type_name: typeMap[item.type_id] }
            : item;
          return { ...baseItem, translateX: 0 };
        });

        // 更新缓存和渲染
        wx.setStorageSync('myKnowledgeList', updatedList);
        const listWithTranslateX = updatedList.map(item => ({ ...item, translateX: 0 }));
        this.setData({
          hasData: listWithTranslateX.length > 0,
          originalList: listWithTranslateX,
          fileList: listWithTranslateX,
          categoryCount: listWithTranslateX.length
        }, () => {
          // 如果有选中的分类，进行筛选
          if (this.properties.selectedCategory && this.properties.selectedCategory !== '全部') {
            this.filterByCategoryValue(this.properties.selectedCategory);
          } else {
            // 通知父组件更新数量
            this.triggerEvent('countchange', {
              count: this.data.fileList.length
            });
          }
        });
        return;
      }

      // 如果有缺失的类型，从API获取（作为后备方案）
      let completedCount = 0;
      const totalCount = missingTypeIds.length;

      missingTypeIds.forEach(typeId => {
        wx.request({
          url: `${API_BASE_URL}/api/knowledge-types/${typeId}`,
          method: 'GET',
          header: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${accessToken}`
          },
          timeout: 10000, // 设置10秒超时
          success: (res) => {
            completedCount++;
            
            if (res.statusCode === 200) {
              const typeData = res.data;
              // 处理不同的响应结构
              let typeInfo = null;
              if (typeData.code === 1 && typeData.data) {
                typeInfo = typeData.data;
              } else if (typeData.type_name) {
                typeInfo = typeData;
              } else if (typeData.data) {
                typeInfo = typeData.data;
              }
              
              if (typeInfo && typeInfo.type_name) {
                typeMap[typeId] = typeInfo.type_name;
              }
            }

            // 当所有请求完成后，更新知识库列表
            if (completedCount === totalCount) {
              // 将 type_name 添加到每个知识库对象中，并确保 translateX: 0
              const updatedList = knowledgeList.map(item => {
                const baseItem = item.type_id && typeMap[item.type_id] 
                  ? { ...item, type_name: typeMap[item.type_id] }
                  : item;
                return { ...baseItem, translateX: 0 };
              });

              // 更新缓存和渲染
              wx.setStorageSync('myKnowledgeList', updatedList);
              const listWithTranslateX = updatedList.map(item => ({ ...item, translateX: 0 }));
              this.setData({
                hasData: listWithTranslateX.length > 0,
                originalList: listWithTranslateX,
                fileList: listWithTranslateX,
                categoryCount: listWithTranslateX.length
              }, () => {
                // 如果有选中的分类，进行筛选
                if (this.properties.selectedCategory && this.properties.selectedCategory !== '全部') {
                  this.filterByCategoryValue(this.properties.selectedCategory);
                } else {
                  // 通知父组件更新数量
                  this.triggerEvent('countchange', {
                    count: this.data.fileList.length
                  });
                }
              });
            }
          },
          fail: (err) => {
            completedCount++;
            console.error(`获取类型信息失败 type_id: ${typeId}`, err);
            
            // 即使失败也要继续处理
            if (completedCount === totalCount) {
              const updatedList = knowledgeList.map(item => {
                const baseItem = item.type_id && typeMap[item.type_id]
                  ? { ...item, type_name: typeMap[item.type_id] }
                  : item;
                return { ...baseItem, translateX: 0 };
              });

              wx.setStorageSync('myKnowledgeList', updatedList);
              const listWithTranslateX = updatedList.map(item => ({ ...item, translateX: 0 }));
              this.setData({
                hasData: listWithTranslateX.length > 0,
                originalList: listWithTranslateX,
                fileList: listWithTranslateX,
                categoryCount: listWithTranslateX.length
              }, () => {
                // 如果有选中的分类，进行筛选
                if (this.properties.selectedCategory && this.properties.selectedCategory !== '全部') {
                  this.filterByCategoryValue(this.properties.selectedCategory);
                } else {
                  // 通知父组件更新数量
                  this.triggerEvent('countchange', {
                    count: this.data.fileList.length
                  });
                }
              });
            }
          }
        });
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
      
      // 根据选中的分类筛选知识库列表
      this.filterByCategory(item);
    },

    /**
     * 根据分类筛选知识库列表
     * @param {Object} categoryData - 分类数据对象，包含 type_id 和 type_name
     */
    filterByCategory(categoryData) {
      if (!categoryData || !categoryData.type_id || categoryData.type_id === 'all') {
        // 显示全部，重置 translateX
        const resetList = this.data.originalList.map(item => ({ ...item, translateX: 0 }));
        this.setData({
          fileList: resetList,
          categoryCount: resetList.length
        }, () => {
          // 通知父组件更新数量
          this.triggerEvent('countchange', {
            count: this.data.fileList.length
          });
        });
      } else {
        // 根据 type_id 筛选，重置 translateX
        const filteredList = this.data.originalList.filter(item => {
          return item.type_id === categoryData.type_id;
        }).map(item => ({ ...item, translateX: 0 }));
        this.setData({
          fileList: filteredList,
          categoryCount: filteredList.length
        }, () => {
          // 通知父组件更新数量
          this.triggerEvent('countchange', {
            count: this.data.fileList.length
          });
        });
      }
    },

    /**
     * 根据分类值筛选知识库列表
     * @param {String} categoryValue - 分类名称（如"全部"、"增值税"等）
     */
    filterByCategoryValue(categoryValue) {
      if (!categoryValue || categoryValue === '全部') {
        // 显示全部，重置 translateX
        const resetList = this.data.originalList.map(item => ({ ...item, translateX: 0 }));
        this.setData({
          fileList: resetList,
          categoryCount: resetList.length
        }, () => {
          // 通知父组件更新数量
          this.triggerEvent('countchange', {
            count: this.data.fileList.length
          });
        });
      } else {
        // 根据 type_name 筛选，重置 translateX
        const filteredList = this.data.originalList.filter(item => {
          return item.type_name === categoryValue;
        }).map(item => ({ ...item, translateX: 0 }));
        this.setData({
          fileList: filteredList,
          categoryCount: filteredList.length
        }, () => {
          // 通知父组件更新数量
          this.triggerEvent('countchange', {
            count: this.data.fileList.length
          });
        });
      }
    },

    /**
     * 知识库卡片点击事件
     */
    onKnowledgeCardTap(e) {
      // 如果发生了滑动操作，不触发点击事件
      if (this.data.isSwipeAction) {
        return;
      }
      
      const index = e.currentTarget.dataset.index;
      let kbName = e.currentTarget.dataset.kbName;
      let knowledgeItem = null;
      
      // 如果从 dataset 获取不到，尝试从列表数据中获取
      if (!kbName && index !== undefined && index !== null) {
        knowledgeItem = this.data.fileList[index];
        if (knowledgeItem && knowledgeItem.kb_name) {
          kbName = knowledgeItem.kb_name;
        }
      } else if (kbName) {
        // 如果已有 kbName，从列表中查找对应的项
        knowledgeItem = this.data.fileList.find(item => item.kb_name === kbName);
      }
      
      if (!kbName) {
        console.error('无法获取知识库名称，index:', index, 'list:', this.data.fileList);
        wx.showToast({
          title: '获取知识库信息失败',
          icon: 'none'
        });
        return;
      }
      
      // 显示弹窗并加载文档列表
      this.setData({
        showDocModal: true,
        currentKbName: kbName,
        documentList: []
      });
      
      // 加载文档列表，传递知识库项
      this.loadDocumentList(kbName, knowledgeItem);
    },

    /**
     * 获取筛选后的知识库数量
     */
    getFilteredCount() {
      return this.data.fileList.length;
    },

    /**
     * 刷新知识库列表（供父组件调用）
     * 参考 file.js 的逻辑：先尝试从缓存加载并显示，然后请求最新数据
     * @param {Boolean} forceRefresh - 是否强制刷新（清除缓存后重新加载）
     */
    refresh(forceRefresh = true) {
      // 如果强制刷新，清除缓存以确保获取最新数据
      if (forceRefresh) {
        try {
          wx.removeStorageSync('myKnowledgeList');
        } catch (e) {
          console.error('清除知识库列表缓存失败：', e);
        }
        // 强制刷新时，直接请求最新数据，不先加载缓存
        this.loadMyKnowledgeList(true);
      } else {
        // 非强制刷新时，先尝试从缓存加载并显示，然后请求最新数据
        this.loadMyKnowledgeList(false);
      }
    },

    /**
     * 触摸开始事件
     */
    onTouchStart(e) {
      const touch = e.touches[0];
      const index = e.currentTarget.dataset.index;
      
      this.setData({
        touchStartX: touch.clientX,
        touchStartY: touch.clientY,
        currentIndex: index,
        isSwipeAction: false // 重置滑动标记
      });
    },

    /**
     * 触摸移动事件
     */
    onTouchMove(e) {
      const touch = e.touches[0];
      const index = e.currentTarget.dataset.index;
      const deltaX = touch.clientX - this.data.touchStartX;
      const deltaY = Math.abs(touch.clientY - this.data.touchStartY);
      
      // 如果垂直滑动距离大于水平滑动距离，则不处理
      if (deltaY > Math.abs(deltaX)) {
        return;
      }
      
      // 标记发生了滑动操作
      if (Math.abs(deltaX) > 10) {
        this.setData({
          isSwipeAction: true
        });
      }
      
      // 将像素转换为rpx (750rpx = screenWidth px)
      const pxToRpx = 750 / this.data.screenWidth;
      const deltaXRpx = deltaX * pxToRpx;
      
      // 限制滑动范围：只能左滑，最大滑动距离为160rpx
      let translateX = deltaXRpx;
      if (translateX > 0) {
        translateX = 0;
      } else if (translateX < -160) {
        translateX = -160;
      }
      
      // 更新当前项的 translateX
      const fileList = this.data.fileList;
      const updatedList = fileList.map((item, idx) => {
        if (idx === index) {
          return { ...item, translateX };
        }
        // 其他项恢复原位
        return { ...item, translateX: 0 };
      });
      
      this.setData({
        fileList: updatedList
      });
    },

    /**
     * 触摸结束事件
     */
    onTouchEnd(e) {
      const index = e.currentTarget.dataset.index;
      const fileList = this.data.fileList;
      const currentItem = fileList[index];
      
      if (!currentItem) return;
      
      // 如果左滑超过80rpx，则显示删除按钮，否则恢复原位
      if (currentItem.translateX < -80) {
        const updatedList = fileList.map((item, idx) => {
          if (idx === index) {
            return { ...item, translateX: -160 };
          }
          return { ...item, translateX: 0 };
        });
        this.setData({
          fileList: updatedList
        });
      } else {
        const updatedList = fileList.map((item, idx) => {
          if (idx === index) {
            return { ...item, translateX: 0 };
          }
          return item;
        });
        this.setData({
          fileList: updatedList
        });
      }
      
      // 重置滑动标记
      this.setData({
        isSwipeAction: false
      });
    },

    /**
     * 删除知识库
     * 优化：先删除缓存和更新UI，再发送网络请求，实现即时响应
     */
    onDeleteKnowledge(e) {
      const kbName = e.currentTarget.dataset.kbName;
      const index = e.currentTarget.dataset.index;
      const that = this;
      
      if (!kbName) {
        wx.showToast({
          title: '知识库名称缺失',
          icon: 'none'
        });
        return;
      }
      
      wx.showModal({
        title: '提示',
        content: '确定要删除这个知识库吗？',
        success(res) {
          if (res.confirm) {
            // 获取 token
            const accessToken = wx.getStorageSync('access_token');
            
            if (!accessToken) {
              wx.showToast({
                title: '请先登录',
                icon: 'none'
              });
              return;
            }

            // 保存当前数据作为备份（用于失败时回滚）
            const backupOriginalList = [...that.data.originalList];
            const backupFileList = [...that.data.fileList];
            const backupHasData = that.data.hasData;
            const backupCategoryCount = that.data.categoryCount;

            // 1. 先立即从列表中删除（乐观更新）
            const updatedOriginalList = that.data.originalList.filter(item => item.kb_name !== kbName);
            const updatedFileList = that.data.fileList.filter(item => item.kb_name !== kbName);
            
            // 2. 立即更新UI数据（包括categoryCount）
            that.setData({
              originalList: updatedOriginalList,
              fileList: updatedFileList,
              hasData: updatedOriginalList.length > 0,
              categoryCount: updatedFileList.length
            });
            
            // 3. 立即更新缓存
            try {
              if (updatedOriginalList.length > 0) {
                wx.setStorageSync('myKnowledgeList', updatedOriginalList);
              } else {
                wx.removeStorageSync('myKnowledgeList');
              }
            } catch (e) {
              console.error('更新知识库列表缓存失败：', e);
            }
            
            // 4. 立即通知父组件更新数量
            that.triggerEvent('countchange', {
              count: updatedFileList.length
            });

            // 5. 然后发送 DELETE 请求
            wx.request({
              url: `${API_BASE_URL}/api/knowledge-base/${kbName}`,
              method: 'DELETE',
              header: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${accessToken}`
              },
              data: {
                kb_name: kbName
              },
              success(res) {
                // 检查并显示后端返回的 message 信息
                if (res.data && res.data.results && res.data.results.message) {
                  wx.showToast({
                    title: res.data.results.message,
                    icon: 'none',
                    duration: 2000
                  });
                }
                
                // 检查响应状态
                if (res.statusCode >= 200 && res.statusCode < 300) {
                  const payload = res.data || {};
                  
                  // 如果删除成功
                  if (payload.code === 1 || res.statusCode === 200) {
                    // 删除成功，显示提示（UI已经更新过了）
                    wx.showToast({
                      title: '删除成功',
                      icon: 'success'
                    });
                  } else {
                    // 删除失败，回滚数据
                    that.setData({
                      originalList: backupOriginalList,
                      fileList: backupFileList,
                      hasData: backupHasData,
                      categoryCount: backupCategoryCount
                    });
                    
                    // 回滚缓存
                    try {
                      if (backupOriginalList.length > 0) {
                        wx.setStorageSync('myKnowledgeList', backupOriginalList);
                      } else {
                        wx.removeStorageSync('myKnowledgeList');
                      }
                    } catch (e) {
                      console.error('回滚知识库列表缓存失败：', e);
                    }
                    
                    // 回滚父组件数量
                    that.triggerEvent('countchange', {
                      count: backupFileList.length
                    });
                    
                    wx.showToast({
                      title: payload.message || '删除失败',
                      icon: 'none'
                    });
                  }
                } else {
                  // HTTP 状态码错误，回滚数据
                  console.error('删除知识库失败：', res);
                  
                  that.setData({
                    originalList: backupOriginalList,
                    fileList: backupFileList,
                    hasData: backupHasData,
                    categoryCount: backupCategoryCount
                  });
                  
                  // 回滚缓存
                  try {
                    if (backupOriginalList.length > 0) {
                      wx.setStorageSync('myKnowledgeList', backupOriginalList);
                    } else {
                      wx.removeStorageSync('myKnowledgeList');
                    }
                  } catch (e) {
                    console.error('回滚知识库列表缓存失败：', e);
                  }
                  
                  // 回滚父组件数量
                  that.triggerEvent('countchange', {
                    count: backupFileList.length
                  });
                  
                  wx.showToast({
                    title: '删除失败，请重试',
                    icon: 'none'
                  });
                }
              },
              fail(err) {
                console.error('删除知识库请求失败：', err);
                
                // 网络请求失败，回滚数据
                that.setData({
                  originalList: backupOriginalList,
                  fileList: backupFileList,
                  hasData: backupHasData,
                  categoryCount: backupCategoryCount
                });
                
                // 回滚缓存
                try {
                  if (backupOriginalList.length > 0) {
                    wx.setStorageSync('myKnowledgeList', backupOriginalList);
                  } else {
                    wx.removeStorageSync('myKnowledgeList');
                  }
                } catch (e) {
                  console.error('回滚知识库列表缓存失败：', e);
                }
                
                // 回滚父组件数量
                that.triggerEvent('countchange', {
                  count: backupFileList.length
                });
                
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
     * 阻止事件冒泡
     */
    stopPropagation() {},

    /**
     * 添加按钮点击事件
     */
    onAddTap(e) {
      console.log('onAddTap 被调用', e);
      const kbName = e.currentTarget.dataset.kbName;
      const index = e.currentTarget.dataset.index;
      const item = this.data.fileList[index];
      
      console.log('知识库名称:', kbName, '索引:', index, '项目:', item);
      
      // 从缓存中获取知识库完整信息
      const myKnowledgeList = wx.getStorageSync('myKnowledgeList') || [];
      const kbInfo = myKnowledgeList.find(kb => kb.kb_name === kbName) || item;
      
      console.log('知识库信息:', kbInfo);
      
      // 从缓存中加载文件列表，只显示 .doc, .docx, .pdf 文件
      const cachedFileList = wx.getStorageSync('fileList') || [];
      
      // 过滤文件：只保留 .doc, .docx, .pdf 文件
      const allowedTypes = ['PDF', 'DOCX'];
      const allowedExtensions = ['.doc', '.docx', '.pdf'];
      
      const filteredFileList = cachedFileList.filter(file => {
        // 检查 type 字段
        if (file.type && allowedTypes.includes(file.type)) {
          return true;
        }
        
        // 如果 type 字段不符合，检查文件名后缀
        const fileName = file.name || '';
        const lowerFileName = fileName.toLowerCase();
        return allowedExtensions.some(ext => lowerFileName.endsWith(ext));
      });
      
      const fileListForSelect = filteredFileList.map(file => {
        // 限制文件名长度，超过10个字符显示省略号
        let displayName = file.name || '';
        if (displayName.length > 10) {
          displayName = displayName.substring(0, 10) + '...';
        }
        return {
          ...file,
          name: displayName,
          selected: false
        };
      });
      
      console.log('文件列表:', fileListForSelect);
      
      this.setData({
        showAddFileModal: true,
        currentKbInfo: kbInfo,
        fileListForSelect: fileListForSelect,
        selectedFileCount: 0,
        isAllSelected: false
      }, () => {
        console.log('弹窗状态已更新，showAddFileModal:', this.data.showAddFileModal);
      });
    },

    /**
     * 上传新文件按钮点击事件
     */
    onUploadNewFile() {
      const that = this;
      
      wx.chooseMessageFile({
        count: 3,
        type: 'file',
        success(res) {
          const tempFiles = res.tempFiles;
          if (tempFiles.length === 0) {
            wx.showToast({ title: '未选择文件', icon: 'none' });
            return;
          }
          
          that.uploadNewFiles(tempFiles);
        },
        fail(err) {
          console.error('选择文件失败：', err);
          wx.showToast({ title: '选择文件失败', icon: 'none' });
        }
      });
    },

    /**
     * 上传新选择的文件到服务器
     */
    uploadNewFiles(tempFiles) {
      const that = this;
      const accessToken = wx.getStorageSync('access_token');
      
      if (!accessToken) {
        wx.showToast({ title: '请先登录', icon: 'none' });
        return;
      }

      wx.showLoading({ title: '上传中...', mask: true });

      let uploadedCount = 0;
      const newFiles = [];
      const totalFiles = tempFiles.length;

      tempFiles.forEach((tempFile, index) => {
        const original_filename = tempFile.name || `文件_${Date.now()}`;
        
        wx.uploadFile({
          url: `${API_BASE_URL}/api/files/upload`,
          filePath: tempFile.path,
          name: 'file',
          formData: { original_filename },
          header: { 'Authorization': `Bearer ${accessToken}` },
          success(uploadRes) {
            try {
              const rawData = uploadRes.data;
              console.log(`📤 文件 ${index + 1} 原始响应:`, typeof rawData, rawData);
              
              let data = typeof rawData === 'string' ? JSON.parse(rawData) : rawData;
              console.log(`📤 文件 ${index + 1} 解析后数据:`, data);
              
              // 兼容多种后端响应格式
              const isSuccess = (
                (uploadRes.statusCode >= 200 && uploadRes.statusCode < 300) &&
                (
                  data.code === 1 ||           // 格式1: code = 1
                  data.code === 0 ||           // 格式2: code = 0  
                  data.code === 200 ||         // 格式3: HTTP状态码
                  data.success === true ||     // 格式4: success字段
                  data.success === 'true' ||   // 格式5: 字符串true
                  data.status === 'success' || // 格式6: status字段
                  data.id ||                   // 格式7: 有ID即成功
                  data.file_id ||              // 格式8: 有file_id即成功
                  data.data ||                 // 格式9: 有data对象
                  !data.code ||                // 格式10: 无code字段且HTTP成功
                  Object.keys(data).length > 0 // 格式11: 有任何数据
                )
              );
              
              console.log(`📤 文件 ${index + 1} 判断结果:`, isSuccess, 
                         '| statusCode:', uploadRes.statusCode,
                         '| code:', data.code,
                         '| keys:', Object.keys(data));
              
              if (isSuccess) {
                // 提取文件数据 - 兼容多种结构
                const fileData = data.data || data.results?.data || data;
                
                console.log(`✅ 文件 ${index + 1} 上传成功！fileData:`, fileData);
                
                let displayName = original_filename;
                if (displayName.length > 10) {
                  displayName = displayName.substring(0, 10) + '...';
                }
                
                const lastDotIndex = original_filename.lastIndexOf('.');
                let ext = '';
                let type = 'OTHER';
                if (lastDotIndex !== -1 && lastDotIndex < original_filename.length - 1) {
                  ext = original_filename.substring(lastDotIndex + 1).toUpperCase();
                  if (ext === 'PDF') type = 'PDF';
                  else if (ext === 'DOCX' || ext === 'DOC') type = 'DOCX';
                }
                
                const size = that.formatFileSize(tempFile.size);
                
                // 兼容多种 ID 字段
                const fileId = fileData.id || 
                              fileData.file_id || 
                              data.id || 
                              data.file_id ||
                              `temp_${Date.now()}_${index}`;
                
                console.log(`📝 文件 ${index + 1} 提取的ID:`, fileId);
                
                newFiles.push({
                  id: fileId,
                  file_id: fileId,
                  name: displayName,
                  original_name: original_filename,
                  size: size,
                  type: type,
                  category: '新上传',
                  selected: true,
                  isNewUpload: true
                });
              } else {
                console.error(`❌ 文件 ${index + 1} 上传失败！`, {
                  statusCode: uploadRes.statusCode,
                  code: data.code,
                  message: data.message || data.msg,
                  fullResponse: data
                });
              }
            } catch (e) {
              console.error(`解析文件 ${index + 1} 响应失败：`, e);
            }
          },
          fail(err) {
            console.error(`文件 ${index + 1} 上传请求失败：`, err);
          },
          complete() {
            uploadedCount++;
            
            if (uploadedCount === totalFiles) {
              wx.hideLoading();
              
              if (newFiles.length > 0) {
                const currentList = that.data.fileListForSelect || [];
                const mergedList = [...newFiles, ...currentList];
                const selectedCount = mergedList.filter(f => f.selected).length;
                const isAllSelected = selectedCount > 0 && selectedCount === mergedList.length;
                
                that.setData({
                  fileListForSelect: mergedList,
                  selectedFileCount: selectedCount,
                  isAllSelected: isAllSelected
                });
                
                wx.showToast({
                  title: `${newFiles.length}/${totalFiles} 个文件上传成功`,
                  icon: 'success'
                });
              } else {
                wx.showToast({
                  title: '文件上传失败，请重试',
                  icon: 'none'
                });
              }
            }
          }
        });
      });
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
     * 关闭添加文件弹窗
     */
    onCloseAddFileModal() {
      this.setData({
        showAddFileModal: false,
        currentKbInfo: {},
        fileListForSelect: [],
        selectedFileCount: 0,
        isAllSelected: false
      });
    },

    /**
     * 点击遮罩层关闭弹窗
     */
    onMaskTap() {
      this.onCloseAddFileModal();
    },

    /**
     * 切换文件选择状态
     */
    onToggleFileSelect(e) {
      const index = e.currentTarget.dataset.index;
      const fileListForSelect = [...this.data.fileListForSelect];
      const file = fileListForSelect[index];
      
      if (file) {
        file.selected = !file.selected;
        const selectedFileCount = fileListForSelect.filter(f => f.selected).length;
        const isAllSelected = selectedFileCount === fileListForSelect.length && fileListForSelect.length > 0;
        
        this.setData({
          fileListForSelect: fileListForSelect,
          selectedFileCount: selectedFileCount,
          isAllSelected: isAllSelected
        });
      }
    },

    /**
     * 全选/取消全选
     */
    onToggleSelectAll() {
      const fileListForSelect = [...this.data.fileListForSelect];
      const isAllSelected = !this.data.isAllSelected;
      
      // 更新所有文件的选择状态
      fileListForSelect.forEach(file => {
        file.selected = isAllSelected;
      });
      
      const selectedFileCount = isAllSelected ? fileListForSelect.length : 0;
      
      this.setData({
        fileListForSelect: fileListForSelect,
        selectedFileCount: selectedFileCount,
        isAllSelected: isAllSelected
      });
    },

    /**
     * 提交添加文件
     */
    onSubmitAddFile() {
      const { currentKbInfo, fileListForSelect } = this.data;
      const selectedFiles = fileListForSelect.filter(file => file.selected);
      
      if (selectedFiles.length === 0) {
        wx.showToast({
          title: '请选择至少一个文件',
          icon: 'none'
        });
        return;
      }

      // 获取 token
      const accessToken = wx.getStorageSync('access_token');
      if (!accessToken) {
        wx.showToast({
          title: '请先登录',
          icon: 'none'
        });
        return;
      }

      // 准备请求参数 - 批量收集选中的文件ID到file_ids数组中
      const fileIds = selectedFiles.map(file => {
        // 优先使用id，如果没有则使用file_id
        return file.id || file.file_id;
      }).filter(Boolean); // 过滤掉空值
      
      console.log('批量选择的文件ID列表:', fileIds);
      
      if (fileIds.length === 0) {
        wx.showToast({
          title: '文件ID缺失',
          icon: 'none'
        });
        return;
      }

      const requestData = {
        kb_name: currentKbInfo.kb_name,
        user_id: currentKbInfo.user_id,
        file_ids: fileIds, // 批量上传的文件ID数组
        chunking_rule: currentKbInfo.chunking_rule,
        chunk_size: currentKbInfo.chunk_size,
        chunk_overlap: currentKbInfo.chunk_overlap
      };
      
      console.log('提交的请求数据:', requestData);

      wx.showLoading({
        title: '上传中...',
        mask: true
      });

      // 发送 POST 请求
      wx.request({
        url: `${API_BASE_URL}/api/knowledge-base/import-files`,
        method: 'POST',
        header: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`
        },
        data: requestData,
        timeout: 300000, // 设置120秒超时（文件导入可能需要较长时间，特别是批量上传时）
        success: (res) => {
          wx.hideLoading();
          
          // 检查并显示后端返回的 message 信息
          if (res.data && res.data.results && res.data.results.message) {
            wx.showToast({
              title: res.data.results.message,
              icon: 'none',
              duration: 2000
            });
          }
          
          if (res.statusCode >= 200 && res.statusCode < 300) {
            const payload = res.data || {};
            
            if (payload.code === 1 || res.statusCode === 200) {
              wx.showToast({
                title: '添加成功',
                icon: 'success',
                duration: 1500
              });
              
              // 关闭弹窗
              this.onCloseAddFileModal();
              
              // 延迟刷新知识库列表，给后端一些处理时间
              setTimeout(() => {
                // 使用非强制刷新，保留现有数据，等新数据加载完成后再更新
                this.refresh(false);
              }, 1000);
              
              // 通知父组件
              this.triggerEvent('fileadded', {
                kbName: currentKbInfo.kb_name,
                fileCount: fileIds.length
              });
            } else {
              wx.showToast({
                title: payload.message || '添加失败',
                icon: 'none'
              });
            }
          } else {
            console.error('添加文件失败：', res);
            wx.showToast({
              title: '添加失败，请重试',
              icon: 'none'
            });
          }
        },
        fail: (err) => {
          wx.hideLoading();
          console.error('添加文件请求失败：', err);
          let errorMsg = '网络错误，请重试';
          if (err.errMsg && err.errMsg.includes('timeout')) {
            errorMsg = '请求超时，文件可能正在处理中，请稍后刷新查看';
          }
          wx.showToast({
            title: errorMsg,
            icon: 'none',
            duration: 3000
          });
        }
      });
    },

    /**
     * 加载知识库文档列表
     * @param {string} kbName - 知识库名称
     * @param {Object} knowledgeItem - 知识库项（可选，如果未提供则从列表中查找）
     */
    loadDocumentList(kbName, knowledgeItem = null) {
      // 从本地缓存获取 token
      const token = this.getTokenFromStorage();
      
      // 从 fileList / originalList 中获取 user_id、type_name、table_name
      let userId = null;
      let typeName = null;
      let tableName = null;
      
      // 如果传入了 knowledgeItem，直接使用
      if (knowledgeItem) {
        if (knowledgeItem.user_id) {
          userId = knowledgeItem.user_id;
        }
        if (knowledgeItem.type_name) {
          typeName = knowledgeItem.type_name;
        }
        if (knowledgeItem.table_name) {
          tableName = knowledgeItem.table_name;
        }
      } else {
        // 否则从 fileList 中查找对应的知识库项
        const foundItem = this.data.fileList.find(item => item.kb_name === kbName);
        if (foundItem) {
          if (foundItem.user_id) {
            userId = foundItem.user_id;
          }
          if (foundItem.type_name) {
            typeName = foundItem.type_name;
          }
          if (foundItem.table_name) {
            tableName = foundItem.table_name;
          }
        } else {
          // 如果当前列表中没有，尝试从 originalList 中查找
          const foundInOriginal = this.data.originalList.find(item => item.kb_name === kbName);
          if (foundInOriginal) {
            if (foundInOriginal.user_id) {
              userId = foundInOriginal.user_id;
            }
            if (foundInOriginal.type_name) {
              typeName = foundInOriginal.type_name;
            }
            if (foundInOriginal.table_name) {
              tableName = foundInOriginal.table_name;
            }
          }
        }

        // 如果还是找不到 userId，尝试从缓存中获取
        if (!userId) {
          userId = this.getUserIdFromStorage();
        }
      }
      
      // 详细的调试信息
      console.log('登录信息检查:', {
        hasToken: !!token,
        tokenLength: token ? token.length : 0,
        hasUserId: !!userId,
        userId: userId,
        hasTypeName: !!typeName,
        typeName: typeName,
        hasTableName: !!tableName,
        tableName: tableName,
        kbName: kbName,
        knowledgeItem: knowledgeItem
      });
      
      // 优先检查 token，如果 token 存在但 user_id 不存在，仍然尝试请求（后端可能会从 token 中解析）
      if (!token) {
        console.log('Token 不存在');
        wx.showToast({
          title: '请先登录',
          icon: 'none'
        });
        this.setData({
          showDocModal: false
        });
        return;
      }
      
      // 如果 user_id 不存在，给出警告但继续尝试（某些 API 可能只需要 token）
      if (!userId) {
        console.warn('User ID 不存在，但 token 存在，继续尝试请求');
      }

      // 如果 table_name 不存在，尝试用已有信息兜底
      if (!tableName) {
        // 优先使用 type_name 作为表名兜底，其次使用 kbName
        tableName = typeName || kbName || null;
        console.warn('table_name 不存在，使用兜底值:', tableName);
      }

      // 显示加载提示
      wx.showLoading({
        title: '加载中...',
        mask: true
      });

      // 发送 GET 请求获取文档列表
      wx.request({
        url: `${API_BASE_URL}/api/knowledge-base/documents`,
        method: 'GET',
        header: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        data: {
          // 后端现在要求 table_name，同时带上 type_name 便于区分
          type_name: typeName,
          table_name: tableName,
          user_id: userId
        },
        success: (res) => {
          wx.hideLoading();
          
          if (res.statusCode === 200) {
            const responseData = res.data;
            let documentsData = null;
            
            // 处理不同的响应结构
            if (responseData.code === 1 && responseData.data) {
              documentsData = responseData.data;
            } else if (responseData.data) {
              documentsData = responseData.data;
            } else if (responseData.kb_name) {
              documentsData = responseData;
            }
            
            if (documentsData) {
              // 缓存数据
              wx.setStorageSync(`documents_${kbName}`, documentsData);
              
              // 转换数据格式为 fileList 组件需要的格式
              const documentList = this.formatDocumentList(documentsData);
              
              this.setData({
                totalDocuments: documentsData.total_documents || 0,
                documentList: documentList
              });
            } else {
              wx.showToast({
                title: '暂无文档',
                icon: 'none'
              });
              this.setData({
                documentList: []
              });
            }
          } else {
            console.error('获取文档列表失败:', res);
            wx.showToast({
              title: '加载失败',
              icon: 'none'
            });
            this.setData({
              documentList: []
            });
          }
        },
        fail: (err) => {
          wx.hideLoading();
          console.error('请求文档列表失败:', err);
          wx.showToast({
            title: '网络错误',
            icon: 'none'
          });
          this.setData({
            documentList: []
          });
        }
      });
    },

    /**
     * 格式化文档列表数据为 fileList 组件需要的格式
     */
    formatDocumentList(documentsData) {
      if (!documentsData || !documentsData.documents || !Array.isArray(documentsData.documents)) {
        return [];
      }

      const kbName = documentsData.kb_name || '';
      
      return documentsData.documents.map((doc, index) => {
        // 从文件名中提取名称和类型
        const filename = doc.filename || '';
        const lastDotIndex = filename.lastIndexOf('.');
        const name = lastDotIndex > 0 ? filename.substring(0, lastDotIndex) : filename;
        const type = lastDotIndex > 0 ? filename.substring(lastDotIndex + 1).toUpperCase() : 'OTHER';
        
        // 格式化时间
        const createdAt = doc.created_at || '';
        let formattedTime = '';
        if (createdAt) {
          try {
            const date = new Date(createdAt);
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            const hours = String(date.getHours()).padStart(2, '0');
            const minutes = String(date.getMinutes()).padStart(2, '0');
            formattedTime = `${year}-${month}-${day} ${hours}:${minutes}`;
          } catch (e) {
            formattedTime = createdAt;
          }
        }
        
        // parse_status 放在 size 位置
        const parseStatus = doc.parse_status || '';
        
        return {
          id: doc.id || index,
          name: name,
          category: kbName,
          size: parseStatus,
          time: formattedTime,
          type: type,
          translateX: 0
        };
      });
    },

    /**
     * 关闭文档列表弹窗
     */
    onCloseDocModal() {
      this.setData({
        showDocModal: false,
        currentKbName: '',
        totalDocuments: 0,
        documentList: []
      });
    },

    /**
     * 文档点击事件
     */
    onDocumentTap(e) {
      const fileId = e.detail.fileId;
      const index = e.detail.index;
      console.log('点击文档:', fileId, index);
      // 这里可以添加文档预览或其他操作
    },

    /**
     * 文档列表变化事件（滑动删除等）
     */
    onDocumentListChange(e) {
      this.setData({
        documentList: e.detail.fileList
      });
    }
  }
})
