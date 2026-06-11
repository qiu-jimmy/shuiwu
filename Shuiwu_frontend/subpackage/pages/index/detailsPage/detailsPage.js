// pages/index/detailsPage/detailsPage.js
import { API_BASE_URL } from '../../../../utils/config.js';

Page({

  /**
   * 页面的初始数据
   */
  data: {
    detail: null,
    dataType: 'cases' // cases、laws、knowledge 或 ticket
  },

  /**
   * 生命周期函数--监听页面加载
   */
  onLoad(options) {
    const type = options.type || 'cases';
    const id = options.id || options.caseId; // 兼容旧的 caseId 参数
    
    this.setData({
      dataType: type
    });
    
    if (type === 'laws') {
      this.loadLawDetail(id);
    } else if (type === 'knowledge') {
      this.loadKnowledgeDetail(id);
    } else if (type === 'ticket') {
      this.loadTicketDetail(id);
    } else {
      this.loadCaseDetail(id);
    }
  },

  /**
   * 加载案例详情（已移除本地数据，仅保留占位）
   */
  loadCaseDetail() {
    this.setData({ detail: null });
    wx.showToast({ title: '暂无数据', icon: 'none' });
  },

  /**
   * 加载法律知识详情（已移除本地数据，仅保留占位）
   */
  loadLawDetail() {
    this.setData({ detail: null });
    wx.showToast({ title: '暂无数据', icon: 'none' });
  },

  /**
   * 加载税务知识详情（从接口 GET /api/tax-knowledge/frontend/detail/{doc_id}）
   */
  loadKnowledgeDetail(docId) {
    if (!docId) {
      wx.showToast({ title: '缺少文档ID', icon: 'none' });
      return;
    }
    wx.showLoading({ title: '加载中...' });
    wx.request({
      url: `${API_BASE_URL}/api/tax-knowledge/frontend/detail/${docId}`,
      method: 'GET',
      success: (res) => {
        wx.hideLoading();
        if (res.data && res.data.code === 1 && res.data.data) {
          const raw = res.data.data;
          const detail = raw.jsonContent || raw;
          this.setData({ detail });
          const title = detail.lawName || detail.noticeName || detail.caseTitle || '税务知识';
          wx.setNavigationBarTitle({ title });
        } else {
          wx.showToast({ title: res.data?.msg || '加载失败', icon: 'none' });
        }
      },
      fail: (err) => {
        wx.hideLoading();
        wx.showToast({ title: '网络错误', icon: 'none' });
        console.error('详情请求失败', err);
      }
    });
  },

  /**
   * 加载票务知识详情（已移除本地数据，仅保留占位）
   */
  loadTicketDetail() {
    this.setData({ detail: null });
    wx.showToast({ title: '暂无数据', icon: 'none' });
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