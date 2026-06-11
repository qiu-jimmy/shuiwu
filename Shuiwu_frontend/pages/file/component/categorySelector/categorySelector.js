// pages/file/component/categorySelector/categorySelector.js
import { API_BASE_URL } from '../../../../utils/config';

Component({

  /**
   * 组件的属性列表
   */
  properties: {
    // 标签文字
    label: {
      type: String,
      value: '分类：'
    },
    // 占位符
    placeholder: {
      type: String,
      value: '请选择分类'
    },
    // 选中的值
    value: {
      type: String,
      value: ''
    },
    // 是否排除"全部"选项
    excludeAll: {
      type: Boolean,
      value: false
    }
  },

  /**
   * 组件的初始数据
   */
  data: {
    // 是否显示选择器
    showPicker: false,
    // 分类列表
    categoryList: [],
    // 当前选中的值
    selectedValue: ''
  },

  /**
   * 组件生命周期
   */
  lifetimes: {
    attached() {
      // 初始化分类数据
      this.initCategoryList();
      // 设置初始值
      this.setData({
        selectedValue: this.properties.value || ''
      });
    }
  },

  /**
   * 监听属性变化
   */
  observers: {
    'value'(newVal) {
      this.setData({
        selectedValue: newVal || ''
      });
    }
  },

  /**
   * 组件的方法列表
   */
  methods: {
    /**
     * 过滤分类列表（排除"全部"选项）
     */
    filterCategoryList(list) {
      if (!this.properties.excludeAll || !list || list.length === 0) {
        return list;
      }
      // 过滤掉第一个 type_name 为"全部"的项
      return list.filter((item, index) => {
        // 如果是第一个且 type_name 为"全部"，则过滤掉
        if (index === 0 && item.type_name === '全部') {
          return false;
        }
        return true;
      });
    },

    /**
     * 初始化分类数据（页面加载时调用）
     */
    initCategoryList() {
      try {
        const cachedList = wx.getStorageSync('categoryList');
        if (cachedList && cachedList.length > 0) {
          // 有缓存，直接使用（根据 excludeAll 属性过滤）
          const filteredList = this.filterCategoryList(cachedList);
          this.setData({
            categoryList: filteredList
          });
          return;
        }
      } catch (e) {
        console.error('读取分类缓存失败：', e);
      }

      // 没有缓存，发送网络请求
      this.fetchCategoryList(false);
    },

    /**
     * 获取知识库类型列表
     * @param {Boolean} showPicker - 是否显示选择器
     */
    fetchCategoryList(showPicker = false) {
      wx.showLoading({
        title: '加载中...',
        mask: true
      });

      wx.request({
        url: `${API_BASE_URL}/api/knowledge-types/list?status=active&is_system=true`,
        method: 'GET',
        success: (res) => {
          wx.hideLoading();
          if (res.statusCode === 200 && res.data.code === 1) {
            const categoryData = res.data.data || [];
            
            // 提取 type_id 和 type_name 字段，并添加"全部"选项
            const categoryList = [
              { type_id: 'all', type_name: '全部' },
              ...categoryData.map(item => ({
                type_id: item.type_id,
                type_name: item.type_name
              }))
            ];

            // 缓存到本地
            try {
              wx.setStorageSync('categoryList', categoryList);
            } catch (e) {
              console.error('缓存分类列表失败：', e);
            }

            // 根据 excludeAll 属性过滤列表
            const filteredList = this.filterCategoryList(categoryList);

            this.setData({
              categoryList: filteredList
            }, () => {
              // 如果是点击选择框触发的，显示选择器
              if (showPicker) {
                this.setData({
                  showPicker: true
                });
              }
            });
          } else {
            wx.showToast({
              title: res.data.message || '获取分类列表失败',
              icon: 'none'
            });
          }
        },
        fail: (err) => {
          wx.hideLoading();
          console.error('获取分类列表失败：', err);
          wx.showToast({
            title: '网络错误，请重试',
            icon: 'none'
          });
        }
      });
    },

    /**
     * 点击选择框
     */
    onTriggerTap() {
      // 先从本地缓存读取
      try {
        const cachedList = wx.getStorageSync('categoryList');
        if (cachedList && cachedList.length > 0) {
          // 有缓存，根据 excludeAll 属性过滤后使用并显示选择器
          const filteredList = this.filterCategoryList(cachedList);
          this.setData({
            categoryList: filteredList,
            showPicker: true
          });
        } else {
          // 没有缓存，查询并显示选择器
          this.fetchCategoryList(true);
        }
      } catch (e) {
        console.error('读取分类缓存失败：', e);
        wx.showToast({
          title: '读取分类失败',
          icon: 'none'
        });
      }
    },

    /**
     * 选择器关闭事件
     */
    onPickerClose() {
      this.setData({
        showPicker: false
      });
    },

    /**
     * 选择器选择事件
     */
    onPickerSelect(e) {
      const { item } = e.detail;
      const selectedValue = item.type_name;
      
      this.setData({
        selectedValue: selectedValue,
        showPicker: false
      });

      // 触发选择事件，传递选中的值
      this.triggerEvent('change', {
        value: selectedValue,
        item: item
      });
    },

    /**
     * 刷新分类列表（下拉刷新时调用）
     */
    refreshCategoryList() {
      this.fetchCategoryList(false);
    }
  }
})
