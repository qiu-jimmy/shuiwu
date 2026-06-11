// pages/file/component/fileList/fileList.js
import { OSS_URL } from '../../../../utils/config';

Component({

  /**
   * 组件的属性列表
   */
  properties: {
    // 文件列表
    fileList: {
      type: Array,
      value: [],
      observer: function(newVal, oldVal) {
        // 当文件列表变化时，过滤出当前用户的文件
        this.filterByUserId(newVal);
      }
    },
    // 是否允许左滑删除
    allowSwipeDelete: {
      type: Boolean,
      value: true
    }
  },

  /**
   * 组件的初始数据
   */
  data: {
    // OSS图片地址前缀
    ossUrl: OSS_URL,
    // 触摸相关
    touchStartX: 0,
    touchStartY: 0,
    currentIndex: -1,
    isSwipeAction: false, // 标记是否发生了滑动操作
    // 屏幕信息（用于单位转换）
    screenWidth: 375,
    // 过滤后的文件列表（只显示当前用户的文件）
    filteredFileList: []
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
      // 初始化时过滤文件列表
      this.filterByUserId(this.properties.fileList);
    }
  },

  /**
   * 组件的方法列表
   */
  methods: {
    /**
     * 根据当前用户的 user_id 过滤文件列表
     * 只显示与缓存中 user_id 匹配的文件
     */
    filterByUserId(fileList) {
      if (!fileList || !Array.isArray(fileList) || fileList.length === 0) {
        this.setData({
          filteredFileList: []
        });
        return;
      }

      // 从缓存中获取当前用户的 user_id
      let currentUserId = null;
      try {
        currentUserId = wx.getStorageSync('user_id');
        // 如果直接获取不到，尝试从 user_info 中获取
        if (!currentUserId) {
          const userInfo = wx.getStorageSync('user_info');
          if (userInfo && typeof userInfo === 'object') {
            currentUserId = userInfo.user_id || userInfo.id || userInfo.userId || null;
          }
        }
      } catch (e) {
        console.error('获取用户ID失败：', e);
      }

      // 如果没有 user_id，显示所有文件（向后兼容）
      if (!currentUserId) {
        this.setData({
          filteredFileList: fileList
        });
        return;
      }

      // 过滤文件列表，只保留 user_id 匹配的文件
      const filteredList = fileList.filter(file => {
        // 从文件的 raw 数据中获取 user_id
        let fileUserId = null;
        if (file.raw && file.raw.user_id) {
          fileUserId = file.raw.user_id;
        } else if (file.user_id) {
          fileUserId = file.user_id;
        }

        // 如果文件没有 user_id，默认显示（向后兼容）
        if (!fileUserId) {
          return true;
        }

        // 比较 user_id（转换为字符串进行比较，避免类型不一致）
        return String(fileUserId) === String(currentUserId);
      });

      this.setData({
        filteredFileList: filteredList
      });
    },
    /**
     * 触摸开始事件
     */
    onTouchStart(e) {
      // 如果不允许左滑删除，直接返回
      if (!this.properties.allowSwipeDelete) {
        return;
      }
      
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
      // 如果不允许左滑删除，直接返回
      if (!this.properties.allowSwipeDelete) {
        return;
      }
      
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
      const fileList = this.data.filteredFileList;
      const updatedList = fileList.map((item, idx) => {
        if (idx === index) {
          return { ...item, translateX };
        }
        // 其他项恢复原位
        return { ...item, translateX: 0 };
      });
      
      // 通知父组件更新列表
      this.triggerEvent('listchange', {
        fileList: updatedList
      });
    },

    /**
     * 触摸结束事件
     */
    onTouchEnd(e) {
      // 如果不允许左滑删除，直接返回
      if (!this.properties.allowSwipeDelete) {
        return;
      }
      
      const index = e.currentTarget.dataset.index;
      const fileList = this.data.filteredFileList;
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
        this.triggerEvent('listchange', {
          fileList: updatedList
        });
      } else {
        const updatedList = fileList.map((item, idx) => {
          if (idx === index) {
            return { ...item, translateX: 0 };
          }
          return item;
        });
        this.triggerEvent('listchange', {
          fileList: updatedList
        });
      }
      
      // 重置滑动标记
      this.setData({
        isSwipeAction: false
      });
    },

    /**
     * 文件点击事件
     */
    onFileTap(e) {
      const fileId = e.currentTarget.dataset.id;
      const index = e.currentTarget.dataset.index;
      
      // 如果发生了滑动操作，不触发预览
      if (this.data.isSwipeAction) {
        return;
      }
      
      // 如果文件正在滑动（translateX不为0），不触发预览
      const fileList = this.data.filteredFileList;
      const currentItem = fileList[index];
      if (currentItem && Math.abs(currentItem.translateX || 0) > 10) {
        return;
      }
      
      // 触发文件点击事件
      this.triggerEvent('filetap', {
        fileId: fileId,
        index: index
      });
    },

    /**
     * 删除文件事件
     */
    onDeleteFile(e) {
      const fileId = e.currentTarget.dataset.id;
      
      // 触发删除事件
      this.triggerEvent('delete', {
        fileId: fileId
      });
    }
  }
})
