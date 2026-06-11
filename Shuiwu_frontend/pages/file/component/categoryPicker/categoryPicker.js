// pages/file/component/categoryPicker/categoryPicker.js
Component({

  /**
   * 组件的属性列表
   */
  properties: {
    show: {
      type: Boolean,
      value: false
    },
    options: {
      type: Array,
      value: []
    },
    selectedValue: {
      type: String,
      value: ''
    }
  },

  /**
   * 组件的初始数据
   */
  data: {
    selectedIndex: -1
  },

  /**
   * 组件的方法列表
   */
  methods: {
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
     * 关闭选择器
     */
    onClose() {
      this.triggerEvent('close');
    },

    /**
     * 选择选项
     */
    onSelect(e) {
      const index = e.currentTarget.dataset.index;
      const selectedItem = this.properties.options[index];
      
      this.setData({
        selectedIndex: index
      });

      // 触发选择事件
      this.triggerEvent('select', {
        index: index,
        item: selectedItem,
        value: selectedItem.type_name
      });

      // 延迟关闭，让用户看到选中效果
      setTimeout(() => {
        this.onClose();
      }, 200);
    }
  },

  /**
   * 监听属性变化
   */
  observers: {
    'show, options, selectedValue'(show, options, selectedValue) {
      if (show && options.length > 0) {
        // 根据 selectedValue 找到对应的索引
        const index = options.findIndex(item => item.type_name === selectedValue);
        this.setData({
          selectedIndex: index >= 0 ? index : -1
        });
      }
    }
  }
})
