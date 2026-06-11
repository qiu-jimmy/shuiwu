// pages/file/component/addKnowledge/addKnowledge.js
import { API_BASE_URL } from '../../../../utils/config';
Component({

  /**
   * 组件的属性列表
   */
  properties: {
    show: {
      type: Boolean,
      value: false
    }
  },

  /**
   * 组件的初始数据
   */
  data: {
    formData: {
      name: '',
      description: '',
      type_id: null,
      chunking_rule: '',
      chunk_size: 500,
      chunk_overlap: 50
    },
    // 知识库分类列表（从本地storage获取）
    categoryList: [],
    categoryIndex: -1,
    selectedCategory: '',
    // 切分规则列表（基础数据）
    chunkingRuleList: [
      { label: '快速', value: 'fixed_size' },
      { label: '普通', value: 'semantic' },
      { label: '专业', value: 'recursive' }
    ],
    chunkingRuleIndex: -1,
    selectedChunkingRule: '',
    // 切分规则弹窗用的选项（复用自定义弹窗组件结构）
    chunkRuleOptions: [],
    showChunkRulePicker: false,
    // 分片长度列表
    chunkSizeList: ['500', '800', '1000'],
    chunkSizeIndex: -1,
    selectedChunkSize: '',
    // 分片长度弹窗用的选项（复用自定义弹窗组件结构）
    chunkSizeOptions: [],
    showChunkSizePicker: false,
    canSubmit: false
  },

  /**
   * 组件生命周期
   */
  lifetimes: {
    attached() {
      this.loadCategoryList();
      this.initChunkRuleOptions();
      this.initChunkSizeOptions();
    }
  },

  /**
   * 组件的方法列表
   */
  methods: {
    /**
     * 从本地storage加载知识库分类
     */
    loadCategoryList() {
      try {
        const categoryList = wx.getStorageSync('categoryList') || [];
        this.setData({
          categoryList: categoryList
        });
      } catch (e) {
        console.error('加载分类列表失败：', e);
      }
    },

    /**
     * 初始化切分规则选项（用于自定义弹出框）
     */
    initChunkRuleOptions() {
      const options = this.data.chunkingRuleList.map(item => ({
        type_id: item.value,
        type_name: item.label
      }));
      this.setData({
        chunkRuleOptions: options
      });
    },

    /**
     * 初始化分片长度选项（用于自定义弹出框）
     */
    initChunkSizeOptions() {
      const options = this.data.chunkSizeList.map(size => ({
        type_id: size,
        type_name: size
      }));
      this.setData({
        chunkSizeOptions: options
      });
    },

    /**
     * 阻止事件冒泡
     */
    stopPropagation() {},

    /**
     * 点击遮罩层
     */
    onMaskTap() {
      this.onClose();
    },

    /**
     * 关闭弹窗
     */
    onClose() {
      this.triggerEvent('close');
      this.resetForm();
    },

    /**
     * 重置表单
     */
    resetForm() {
      this.setData({
        formData: {
          name: '',
          description: '',
          type_id: null,
          chunking_rule: '',
          chunk_size: 500,
          chunk_overlap: 50
        },
        categoryIndex: -1,
        selectedCategory: '',
        chunkingRuleIndex: -1,
        selectedChunkingRule: '',
        chunkSizeIndex: -1,
        selectedChunkSize: '',
        canSubmit: false
      });
    },

    /**
     * 知识库名字输入
     */
    onNameInput(e) {
      this.setData({
        'formData.name': e.detail.value
      });
      this.updateSubmitStatus();
    },

    /**
     * 知识库描述输入
     */
    onDescriptionInput(e) {
      this.setData({
        'formData.description': e.detail.value
      });
      this.updateSubmitStatus();
    },

    /**
     * 知识库分类改变
     */
    onCategoryChange(e) {
      const index = parseInt(e.detail.value);
      const category = this.data.categoryList[index];
      this.setData({
        categoryIndex: index,
        selectedCategory: category.type_name,
        'formData.type_id': category.type_id || null
      });
      this.updateSubmitStatus();
    },

    /**
     * 使用 categorySelector 组件时的分类改变
     */
    onCategorySelectorChange(e) {
      const { value, item } = e.detail;
      this.setData({
        selectedCategory: value,
        'formData.type_id': item.type_id || null
      });
      this.updateSubmitStatus();
    },

    /**
     * 切分规则改变（系统 picker 使用）
     */
    onChunkingRuleChange(e) {
      const index = parseInt(e.detail.value);
      const rule = this.data.chunkingRuleList[index];
      this.setData({
        chunkingRuleIndex: index,
        selectedChunkingRule: rule.label,
        'formData.chunking_rule': rule.value
      });
      this.updateSubmitStatus();
    },

    /**
     * 打开切分规则自定义弹出框
     */
    onChunkRuleTriggerTap() {
      this.setData({
        showChunkRulePicker: true
      });
    },

    /**
     * 关闭切分规则自定义弹出框
     */
    onChunkRulePickerClose() {
      this.setData({
        showChunkRulePicker: false
      });
    },

    /**
     * 自定义弹出框中选择切分规则
     */
    onChunkRulePickerSelect(e) {
      const { item, value } = e.detail;
      this.setData({
        selectedChunkingRule: value,
        'formData.chunking_rule': item.type_id || '',
        showChunkRulePicker: false
      });
      this.updateSubmitStatus();
    },

    /**
     * 分片长度改变（系统 picker 使用，已废弃）
     */
    onChunkSizeChange(e) {
      const index = parseInt(e.detail.value);
      const size = this.data.chunkSizeList[index];
      this.setData({
        chunkSizeIndex: index,
        selectedChunkSize: size,
        'formData.chunk_size': parseInt(size)
      });
      this.updateSubmitStatus();
    },

    /**
     * 打开分片长度自定义弹出框
     */
    onChunkSizeTriggerTap() {
      this.setData({
        showChunkSizePicker: true
      });
    },

    /**
     * 关闭分片长度弹出框
     */
    onChunkSizePickerClose() {
      this.setData({
        showChunkSizePicker: false
      });
    },

    /**
     * 选择分片长度
     */
    onChunkSizePickerSelect(e) {
      const { value, item } = e.detail;
      this.setData({
        selectedChunkSize: value,
        'formData.chunk_size': parseInt(item.type_id),
        showChunkSizePicker: false
      });
      this.updateSubmitStatus();
    },

    /**
     * 更新提交按钮状态
     */
    updateSubmitStatus() {
      const { formData } = this.data;
      const canSubmit = formData.name && 
                       formData.description && 
                       formData.chunking_rule && 
                       formData.chunk_size > 0;
      this.setData({
        canSubmit: canSubmit
      });
    },

    /**
     * 提交创建知识库
     */
    onSubmit() {
      if (!this.data.canSubmit) {
        return;
      }

      const { formData } = this.data;
      
      // 获取 access_token（从 storage 获取）
      const accessToken = wx.getStorageSync('access_token');

      if (!accessToken) {
        wx.showToast({
          title: '请先登录',
          icon: 'none'
        });
        return;
      }

      // 从 user_info 中获取 user_id
      const userInfo = wx.getStorageSync('user_info');
      let userId = null;
      
      if (userInfo && typeof userInfo === 'object') {
        userId = userInfo.user_id || userInfo.id || userInfo.userId || null;
      }
      
      // 如果从 user_info 中获取不到，尝试直接从 user_id key 获取
      if (!userId) {
        userId = wx.getStorageSync('user_id');
      }

      if (!userId) {
        wx.showToast({
          title: '用户信息缺失',
          icon: 'none'
        });
        return;
      }

      // 准备请求数据
      const requestData = {
        name: formData.name,
        description: formData.description,
        user_id: userId,
        chunking_rule: formData.chunking_rule,
        chunk_size: formData.chunk_size,
        chunk_overlap: formData.chunk_overlap,
        embedder_model: 'text-embedding-3-small',
        type_id: formData.type_id,
        is_system: false
      };

      wx.showLoading({
        title: '创建中...',
        mask: true
      });

      // 发送创建请求
      wx.request({
        url: `${API_BASE_URL}/api/knowledge-base/create`,
        method: 'POST',
        header: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`
        },
        data: requestData,
        success: (res) => {
          wx.hideLoading();
          if (res.statusCode === 200 && res.data.code === 1) {
            wx.showToast({
              title: '创建成功',
              icon: 'success'
            });
            // 触发创建成功事件
            this.triggerEvent('success', res.data.data);
            this.onClose();
          } else {
            wx.showToast({
              title: res.data.message || '创建失败',
              icon: 'none'
            });
          }
        },
        fail: (err) => {
          wx.hideLoading();
          console.error('创建知识库失败：', err);
          wx.showToast({
            title: '网络错误，请重试',
            icon: 'none'
          });
        }
      });
    }
  }
})
