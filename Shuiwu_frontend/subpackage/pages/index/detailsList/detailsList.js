// pages/index/detailsList/detailsList.js
import { API_BASE_URL } from '../../../../utils/config.js';

Page({

  /**
   * 页面的初始数据
   */
  data: {
    list: [],
    dataType: 'knowledge', // 从接口获取税务知识数据
    page: 1,
    pageSize: 7,
    total: 0,
    loading: false,
    hasMore: true
  },

  /**
   * 生命周期函数--监听页面加载
   */
  onLoad() {
    // 动态设置页面标题
    wx.setNavigationBarTitle({
      title: '税务知识'
    });
    this.loadKnowledgeList();
  },

  /**
   * 加载税务知识列表数据
   * @param {boolean} isLoadMore 是否为加载更多
   */
  loadKnowledgeList(isLoadMore = false) {
    if (this.data.loading || (!this.data.hasMore && isLoadMore)) {
      return;
    }

    this.setData({ loading: true });

    if (!isLoadMore) {
      wx.showLoading({ title: '加载中...' });
    }

    // 加载更多时用下一页请求，避免 setData 异步导致 page 未更新
    const { pageSize } = this.data;
    const page = isLoadMore ? this.data.page + 1 : 1;

    wx.request({
      url: `${API_BASE_URL}/api/tax-knowledge/list`,
      method: 'GET',
      data: { page, pageSize },
      success: (res) => {
        wx.hideLoading();
        if (res.data.code === 1 && res.data.data) {
          const items = res.data.data.items || [];
          const total = res.data.data.total || 0;

          // 后端返回扁平结构：id, docId, docType, lawId, lawName, remark, createdAt, updatedAt 等
          const newList = items.map(item => ({
            id: item.id,
            docId: item.docId || String(item.id),
            title: item.lawName || item.caseTitle || '无标题',
            type: item.docType || item.caseType || '',
            summary: item.remark || '暂无摘要'
          }));

          const hasMore = page * pageSize < total;

          this.setData({
            list: isLoadMore ? [...this.data.list, ...newList] : newList,
            page: page,
            total: total,
            hasMore: hasMore,
            loading: false
          });
        } else {
          this.setData({ loading: false });
          wx.showToast({
            title: '数据加载失败',
            icon: 'none'
          });
        }
      },
      fail: (err) => {
        wx.hideLoading();
        this.setData({ loading: false });
        wx.showToast({
          title: '网络错误',
          icon: 'none'
        });
        console.error('请求失败:', err);
      }
    });
  },

  /**
   * 点击卡片跳转到详情页
   */
  onItemTap(e) {
    const index = e.currentTarget.dataset.index;
    const item = this.data.list[index];
    const docId = item.docId || String(item.id);
    wx.navigateTo({
      url: `/subpackage/pages/index/detailsPage/detailsPage?id=${encodeURIComponent(docId)}&type=knowledge`
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
    this.setData({
      page: 1,
      hasMore: true
    });
    this.loadKnowledgeList(false);
    wx.stopPullDownRefresh();
  },

  /**
   * 页面上拉触底事件的处理函数
   */
  onReachBottom() {
    if (this.data.hasMore && !this.data.loading) {
      this.loadKnowledgeList(true);
    }
  },

  /**
   * 用户点击右上角分享
   */
  onShareAppMessage() {

  }
})