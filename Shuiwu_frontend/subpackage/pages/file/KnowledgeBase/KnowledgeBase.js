// pages/file/KnowledgeBase/KnowledgeBase.js
Page({

  /**
   * 页面的初始数据
   */
  data: {
    // 选中的分类
    selectedCategory: '全部',
    categoryCount: 0,
    // 是否显示添加知识库弹窗
    showAddKnowledgeModal: false,
    // 是否显示添加按钮（默认false，因为默认显示系统知识库）
    showAddButton: false,
    // 当前显示的知识库类型：'system' 系统知识库，'my' 我的知识库（默认显示系统知识库）
    currentKnowledgeType: 'system'
  },

  /**
   * 系统知识库卡片点击事件
   */
  onSystemCardTap() {
    console.log('点击系统知识库');
    // 切换到系统知识库
    this.setData({
      showAddButton: false,
      currentKnowledgeType: 'system'
    }, () => {
      // 更新数量统计
      this.updateFileCounts();
    });
  },

  /**
   * 我的知识库卡片点击事件
   */
  onMyCardTap() {
    console.log('点击我的知识库');
    // 切换到我的知识库
    this.setData({
      showAddButton: true,
      currentKnowledgeType: 'my'
    }, () => {
      // 更新数量统计
      this.updateFileCounts();
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
    this.filterKnowledgeBaseByCategory(item);
    
    // 如果当前显示系统知识库，通知组件筛选
    if (this.data.currentKnowledgeType === 'system') {
      const sysKnowledgeComponent = this.selectComponent('sys-knowledge');
      if (sysKnowledgeComponent) {
        sysKnowledgeComponent.filterByCategory(item);
      }
    }
  },

  /**
   * 根据分类筛选知识库列表
   */
  filterKnowledgeBaseByCategory(categoryData) {
    console.log('筛选分类：', categoryData);

    // 更新知识库数量统计
    if (this.data.currentKnowledgeType === 'system') {
      const sysKnowledgeComponent = this.selectComponent('sys-knowledge');
      if (sysKnowledgeComponent) {
        const count = sysKnowledgeComponent.getFilteredCount();
        this.setData({
          categoryCount: count
        });
      }
    } else {
      // 我的知识库的筛选逻辑
      const myKnowledgeComponent = this.selectComponent('my-knowledge');
      if (myKnowledgeComponent) {
        myKnowledgeComponent.filterByCategory(categoryData);
      }
    }
  },

  /**
   * 系统知识库数量变化事件
   */
  onSysKnowledgeCountChange(e) {
    const { count } = e.detail;
    this.setData({
      categoryCount: count
    });
  },

  /**
   * 我的知识库数量变化事件
   */
  onMyKnowledgeCountChange(e) {
    const { count } = e.detail;
    this.setData({
      categoryCount: count
    });
  },

  /**
   * 我的知识库卡片点击事件
   */
  onKnowledgeCardTap(e) {
    const { index, item } = e.detail;
    console.log('点击我的知识库卡片:', index, item);
  },

  /**
   * 添加按钮点击事件
   */
  onAddTap() {
    console.log('点击添加按钮');
    this.setData({
      showAddKnowledgeModal: true
    });
  },

  /**
   * 关闭添加知识库弹窗
   */
  onCloseAddKnowledge() {
    this.setData({
      showAddKnowledgeModal: false
    });
  },

  /**
   * 添加知识库成功回调
   */
  onAddKnowledgeSuccess(e) {
    console.log('知识库创建成功：', e.detail);
    
    // 如果当前显示的是系统知识库，自动切换到我的知识库
    if (this.data.currentKnowledgeType === 'system') {
      this.setData({
        showAddButton: true,
        currentKnowledgeType: 'my'
      }, () => {
        // 等待视图更新后，再刷新组件
        this.refreshMyKnowledge();
      });
    } else {
      // 如果已经是我的知识库，直接刷新
      this.refreshMyKnowledge();
    }
  },

  /**
   * 刷新我的知识库组件
   */
  refreshMyKnowledge() {
    // 使用 setTimeout 确保组件已经渲染
    setTimeout(() => {
      // 使用 id 选择器确保能找到组件
      const myKnowledgeComponent = this.selectComponent('#my-knowledge');
      if (myKnowledgeComponent) {
        console.log('找到 my-knowledge 组件，开始刷新');
        // 强制刷新，清除缓存并重新加载
        myKnowledgeComponent.refresh(true);
        // 延迟更新文件数量统计，确保数据已加载
        setTimeout(() => {
          this.updateFileCounts();
        }, 1000);
      } else {
        console.warn('未找到 my-knowledge 组件，尝试延迟刷新');
        // 如果找不到组件，可能是视图还没更新，再延迟一下
        setTimeout(() => {
          const retryComponent = this.selectComponent('#my-knowledge');
          if (retryComponent) {
            retryComponent.refresh(true);
            setTimeout(() => {
              this.updateFileCounts();
            }, 1000);
          }
        }, 300);
      }
    }, 100);
  },

  /**
   * 加载知识库列表
   */
  loadKnowledgeBaseList() {
    // 刷新我的知识库组件
    if (this.data.currentKnowledgeType === 'my') {
      const myKnowledgeComponent = this.selectComponent('my-knowledge');
      if (myKnowledgeComponent) {
        myKnowledgeComponent.refresh();
      }
    }
  },


  /**
   * 生命周期函数--监听页面加载
   */
  onLoad(options) {
    // 初始化时加载我的知识库列表
    this.loadMyKnowledgeList();
    // 初始化文件数量统计
    this.updateFileCounts();
  },

  /**
   * 加载我的知识库列表（参考 file.js 的逻辑）
   */
  loadMyKnowledgeList() {
    const myKnowledgeComponent = this.selectComponent('my-knowledge');
    if (myKnowledgeComponent) {
      // 调用组件的 refresh 方法，会自动查询列表
      myKnowledgeComponent.refresh(false);
    }
  },

  /**
   * 更新文件数量统计
   */
  updateFileCounts() {
    if (this.data.currentKnowledgeType === 'system') {
      const sysKnowledgeComponent = this.selectComponent('sys-knowledge');
      if (sysKnowledgeComponent) {
        const count = sysKnowledgeComponent.getFilteredCount();
        this.setData({
          categoryCount: count
        });
      }
    } else {
      const myKnowledgeComponent = this.selectComponent('my-knowledge');
      if (myKnowledgeComponent) {
        const count = myKnowledgeComponent.getFilteredCount();
        this.setData({
          categoryCount: count
        });
      }
    }
  },

  /**
   * 生命周期函数--监听页面初次渲染完成
   */
  onReady() {

  },

  /**
   * 生命周期函数--监听页面显示
   * 参考 file.js 的逻辑：每次页面显示时自动查询列表
   */
  onShow() {
    // 每次页面显示时，自动查询我的知识库列表（无论当前显示的是哪个类型）
    this.loadMyKnowledgeList();
    // 更新文件数量统计
    this.updateFileCounts();
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
   * 参考 file.js 的逻辑：下拉刷新时重新查询列表
   */
  onPullDownRefresh() {
    // 下拉刷新时重新查询知识库类型并缓存
    // 通过选择器组件的方法刷新
    const categorySelector = this.selectComponent('.category-selector');
    if (categorySelector) {
      categorySelector.refreshCategoryList();
    }
    
    // 刷新我的知识库列表（无论当前显示的是哪个类型，都刷新）
    const myKnowledgeComponent = this.selectComponent('my-knowledge');
    if (myKnowledgeComponent) {
      myKnowledgeComponent.refresh(true);
    }
    
    // 刷新当前显示的知识库列表
    if (this.data.currentKnowledgeType === 'system') {
      const sysKnowledgeComponent = this.selectComponent('sys-knowledge');
      if (sysKnowledgeComponent && sysKnowledgeComponent.refresh) {
        sysKnowledgeComponent.refresh();
      }
    }
    
    // 延迟更新数量统计，确保数据已加载
    setTimeout(() => {
      this.updateFileCounts();
      // 停止下拉刷新动画
      wx.stopPullDownRefresh();
    }, 500);
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