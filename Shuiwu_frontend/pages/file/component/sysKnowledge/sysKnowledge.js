// pages/file/component/sysKnowledge/sysKnowledge.js
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
    // 系统知识库原始列表（未筛选）
    originalList: [],
    // 系统知识库列表（筛选后）
    sysKnowledgeList: [],
    // 文档列表弹窗相关
    showDocModal: false, // 是否显示文档列表弹窗
    currentKbName: '', // 当前选中的知识库名称
    totalDocuments: 0, // 文档总数
    documentList: [], // 文档列表（完整）
    visibleDocumentList: [], // 仅用于展示的前 N 条文档
    hasMoreDocuments: false, // 是否还有更多被隐藏的文档
    // 筛选相关
    categoryCount: 0 // 知识库数量
  },

  /**
   * 组件生命周期函数--组件实例刚刚被创建
   */
  lifetimes: {
    attached() {
      // 组件挂载时加载系统知识库列表
      this.loadSystemKnowledgeList();
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
     * 加载系统知识库列表
     */
    loadSystemKnowledgeList() {
      // 1. 检查是否有 access_token
      const accessToken = this.getTokenFromStorage();
      
      if (!accessToken) {
        console.log('未找到 access_token，无法加载系统知识库列表');
        wx.showToast({
          title: '请先登录',
          icon: 'none'
        });
        return;
      }

      // 2. 先检查缓存
      const cachedList = wx.getStorageSync('sysKnowledgeList');
      if (cachedList && cachedList.length > 0) {
        // 从缓存中读取 categoryList 并补充缺失的 type_name
        const categoryList = wx.getStorageSync('categoryList') || [];
        const typeMap = {};
        categoryList.forEach(category => {
          if (category.type_id && category.type_name) {
            typeMap[category.type_id] = category.type_name;
          }
        });
        
        // 确保每个 item 都有 type_name
        const updatedCachedList = cachedList.map(item => {
          // 如果 item 没有 type_name 但 type_id 存在，从 categoryList 中查找
          if (!item.type_name && item.type_id && typeMap[item.type_id]) {
            return { ...item, type_name: typeMap[item.type_id] };
          }
          return item;
        });
        
        this.setData({
          originalList: updatedCachedList,
          sysKnowledgeList: updatedCachedList,
          categoryCount: updatedCachedList.length
        });
        // 如果有选中的分类，进行筛选
        if (this.properties.selectedCategory && this.properties.selectedCategory !== '全部') {
          this.filterByCategoryValue(this.properties.selectedCategory);
        }
      }

      // 3. 发送 GET 请求查询系统知识库列表
      wx.request({
        url: `${API_BASE_URL}/api/knowledge-base/list/system?is_system=true`,
        method: 'GET',
        header: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`
        },
        success: (res) => {
          if (res.statusCode === 200) {
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
            }
          } else {
            console.error('获取系统知识库列表失败:', res);
            wx.showToast({
              title: '加载失败',
              icon: 'none'
            });
          }
        },
        fail: (err) => {
          console.error('请求系统知识库列表失败:', err);
          wx.showToast({
            title: '网络错误',
            icon: 'none'
          });
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
        // 如果没有 type_id，直接更新数据
        wx.setStorageSync('sysKnowledgeList', knowledgeList);
        this.setData({
          sysKnowledgeList: knowledgeList
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
        // 将 type_name 添加到每个知识库对象中
        const updatedList = knowledgeList.map(item => {
          if (item.type_id && typeMap[item.type_id]) {
            return {
              ...item,
              type_name: typeMap[item.type_id]
            };
          }
          return item;
        });

        // 更新缓存和渲染
        wx.setStorageSync('sysKnowledgeList', updatedList);
        this.setData({
          originalList: updatedList,
          sysKnowledgeList: updatedList
        }, () => {
          // 如果有选中的分类，进行筛选
          if (this.properties.selectedCategory && this.properties.selectedCategory !== '全部') {
            this.filterByCategoryValue(this.properties.selectedCategory);
          }
          // 更新知识库数量
          this.setData({
            categoryCount: this.data.sysKnowledgeList.length
          });
          // 通知父组件更新数量
          this.triggerEvent('countchange', {
            count: this.data.sysKnowledgeList.length
          });
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
              // 将 type_name 添加到每个知识库对象中
              const updatedList = knowledgeList.map(item => {
                if (item.type_id && typeMap[item.type_id]) {
                  return {
                    ...item,
                    type_name: typeMap[item.type_id]
                  };
                }
                return item;
              });

              // 更新缓存和渲染
              wx.setStorageSync('sysKnowledgeList', updatedList);
              this.setData({
                originalList: updatedList,
                sysKnowledgeList: updatedList
              }, () => {
                // 如果有选中的分类，进行筛选
                if (this.properties.selectedCategory && this.properties.selectedCategory !== '全部') {
                  this.filterByCategoryValue(this.properties.selectedCategory);
                }
                // 更新知识库数量
                this.setData({
                  categoryCount: this.data.sysKnowledgeList.length
                });
                // 通知父组件更新数量
                this.triggerEvent('countchange', {
                  count: this.data.sysKnowledgeList.length
                });
              });
            }
          },
          fail: (err) => {
            completedCount++;
            console.error(`获取类型信息失败 type_id: ${typeId}`, err);
            
            // 即使失败也要继续处理
            if (completedCount === totalCount) {
              const updatedList = knowledgeList.map(item => {
                if (item.type_id && typeMap[item.type_id]) {
                  return {
                    ...item,
                    type_name: typeMap[item.type_id]
                  };
                }
                return item;
              });

              wx.setStorageSync('sysKnowledgeList', updatedList);
              this.setData({
                originalList: updatedList,
                sysKnowledgeList: updatedList
              }, () => {
                // 如果有选中的分类，进行筛选
                if (this.properties.selectedCategory && this.properties.selectedCategory !== '全部') {
                  this.filterByCategoryValue(this.properties.selectedCategory);
                }
                // 更新知识库数量
                this.setData({
                  categoryCount: this.data.sysKnowledgeList.length
                });
                // 通知父组件更新数量
                this.triggerEvent('countchange', {
                  count: this.data.sysKnowledgeList.length
                });
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
        // 显示全部
        this.setData({
          sysKnowledgeList: this.data.originalList,
          categoryCount: this.data.originalList.length
        }, () => {
          // 通知父组件更新数量
          this.triggerEvent('countchange', {
            count: this.data.sysKnowledgeList.length
          });
        });
      } else {
        // 根据 type_id 筛选
        const filteredList = this.data.originalList.filter(item => {
          return item.type_id === categoryData.type_id;
        });
        this.setData({
          sysKnowledgeList: filteredList,
          categoryCount: filteredList.length
        }, () => {
          // 通知父组件更新数量
          this.triggerEvent('countchange', {
            count: this.data.sysKnowledgeList.length
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
        // 显示全部
        this.setData({
          sysKnowledgeList: this.data.originalList,
          categoryCount: this.data.originalList.length
        }, () => {
          // 通知父组件更新数量
          this.triggerEvent('countchange', {
            count: this.data.sysKnowledgeList.length
          });
        });
      } else {
        // 根据 type_name 筛选
        const filteredList = this.data.originalList.filter(item => {
          return item.type_name === categoryValue;
        });
        this.setData({
          sysKnowledgeList: filteredList,
          categoryCount: filteredList.length
        }, () => {
          // 通知父组件更新数量
          this.triggerEvent('countchange', {
            count: this.data.sysKnowledgeList.length
          });
        });
      }
    },

    /**
     * 获取筛选后的知识库数量
     */
    getFilteredCount() {
      return this.data.sysKnowledgeList.length;
    },

    /**
     * 知识库卡片点击事件
     */
    onKnowledgeCardTap(e) {
      console.log('点击知识库卡片', e);
      console.log('dataset:', e.currentTarget.dataset);
      
      const index = e.currentTarget.dataset.index;
      let kbName = e.currentTarget.dataset.kbName;
      let knowledgeItem = null;
      
      // 如果从 dataset 获取不到，尝试从列表数据中获取
      if (!kbName && index !== undefined && index !== null) {
        knowledgeItem = this.data.sysKnowledgeList[index];
        console.log('从列表获取项:', knowledgeItem);
        if (knowledgeItem && knowledgeItem.kb_name) {
          kbName = knowledgeItem.kb_name;
        }
      } else if (kbName) {
        // 如果已有 kbName，从列表中查找对应的项
        knowledgeItem = this.data.sysKnowledgeList.find(item => item.kb_name === kbName);
      }
      
      console.log('最终获取到的知识库名称:', kbName);
      console.log('知识库项:', knowledgeItem);
      console.log('当前 showDocModal 状态:', this.data.showDocModal);
      
      if (!kbName) {
        console.error('无法获取知识库名称，index:', index, 'list:', this.data.sysKnowledgeList);
        wx.showToast({
          title: '获取知识库信息失败',
          icon: 'none'
        });
        // 即使获取不到名称，也先显示弹窗用于调试
        this.setData({
          showDocModal: true,
          currentKbName: '未知知识库',
          documentList: []
        });
        return;
      }
      
      // 显示弹窗并加载文档列表
      this.setData({
        showDocModal: true,
        currentKbName: kbName,
        documentList: [],
        visibleDocumentList: [],
        hasMoreDocuments: false
      }, () => {
        console.log('设置弹窗显示状态后:', this.data.showDocModal);
      });
      
      // 加载文档列表，传递知识库项
      this.loadDocumentList(kbName, knowledgeItem);
    },

    /**
     * 加载知识库文档列表
     * @param {string} kbName - 知识库名称
     * @param {Object} knowledgeItem - 知识库项（可选，如果未提供则从列表中查找）
     */
    loadDocumentList(kbName, knowledgeItem = null) {
      // 从本地缓存获取 token
      const token = this.getTokenFromStorage();
      
      // 从 sysKnowledgeList 中获取 user_id、type_name 和 table_name
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
        // 否则从 sysKnowledgeList 中查找对应的知识库项
        const foundItem = this.data.sysKnowledgeList.find(item => item.kb_name === kbName);
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

      // 如果 type_name 不存在，也给出警告（新接口按 type_name 查询）
      if (!typeName) {
        console.warn('type_name 不存在，将无法按类型查询文档列表', {
          kbName,
          knowledgeItem
        });
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
          // 按类型名称和表名查询文档列表（后端现在要求 table_name）
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
              
              const total = documentsData.total_documents || documentList.length || 0;
              const visible = documentList.slice(0, 5);
              const hasMore = total > visible.length;

              this.setData({
                totalDocuments: total,
                documentList: documentList,
                visibleDocumentList: visible,
                hasMoreDocuments: hasMore
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
     * 阻止事件冒泡
     */
    stopPropagation() {
      // 空函数，用于阻止事件冒泡
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