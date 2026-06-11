// pages/mine/vip-order/vip-order.js
import { API_BASE_URL } from '../../../../utils/config';

const formatAmount = (value) => {
  const amount = Number(value || 0);
  if (Number.isNaN(amount)) {
    return '0';
  }
  return amount % 1 === 0 ? amount.toFixed(0) : amount.toFixed(1);
};

const formatDateTime = (value) => {
  if (!value) {
    return '—';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  const pad = (num) => (num < 10 ? `0${num}` : `${num}`);
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(
    date.getHours()
  )}:${pad(date.getMinutes())}`;
};

const getAuthHeader = () => {
  const token = wx.getStorageSync('access_token');
  if (!token) {
    return '';
  }
  const tokenType = String(wx.getStorageSync('token_type') || 'bearer');
  const normalizedType = tokenType.toLowerCase() === 'bearer' ? 'Bearer' : tokenType;
  return `${normalizedType} ${token}`;
};

const normalizeOrder = (order) => {
  const paymentStatusMap = {
    paid: { label: '已支付', theme: 'success' },
    pending: { label: '待支付', theme: 'warning' },
    failed: { label: '支付失败', theme: 'danger' },
    refunded: { label: '已退款', theme: 'default' },
  };
  const payment = paymentStatusMap[order.payment_status] || { label: order.payment_status || '未知', theme: 'default' };
  const expireAt = order.new_expire_at || order.original_expire_at;
  return {
    ...order,
    paymentLabel: payment.label,
    paymentTheme: payment.theme,
    amountLabel: formatAmount(order.actual_amount != null ? order.actual_amount : order.amount),
    createdLabel: formatDateTime(order.created_at),
    paidLabel: order.payment_time ? formatDateTime(order.payment_time) : '—',
    expireLabel: expireAt ? formatDateTime(expireAt) : order.duration_days ? `${order.duration_days}天` : '—',
  };
};

Page({

  /**
   * 页面的初始数据
   */
  data: {
    activeFilter: 'all',
    orders: [],
    total: 0,
    page: 1,
    pageSize: 10,
    hasMore: true,
    loading: false,
    refreshing: false,
  },

  /**
   * 生命周期函数--监听页面加载
   */
  onLoad(options) {
    this.fetchOrders({ refresh: true });
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
    this.fetchOrders({ refresh: true });
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
    this.fetchOrders({
      refresh: true,
      done: () => {
        wx.stopPullDownRefresh();
      },
    });
  },

  /**
   * 页面上拉触底事件的处理函数
   */
  onReachBottom() {
    if (this.data.hasMore && !this.data.loading) {
      this.fetchOrders({ refresh: false });
    }
  },

  /**
   * 用户点击右上角分享
   */
  onShareAppMessage() {

  },

  onFilterChange(e) {
    const value = e.detail && e.detail.value ? e.detail.value : 'all';
    this.setData({
      activeFilter: value,
      orders: [],
      page: 1,
      hasMore: true,
    });
    this.fetchOrders({ refresh: true });
  },

  onBuyTap() {
    wx.navigateTo({ url: '/subpackage/pages/mine/vip-buy/vip-buy' });
  },

  fetchOrders({ refresh, done } = {}) {
    const authHeader = getAuthHeader();
    if (!authHeader) {
      wx.showToast({ title: '请先登录', icon: 'none' });
      if (typeof done === 'function') done();
      return;
    }

    const currentPage = refresh ? 1 : this.data.page;
    if (this.data.loading) {
      if (typeof done === 'function') done();
      return;
    }

    this.setData({ loading: true, refreshing: !!refresh });

    const query = [];
    if (this.data.activeFilter === 'paid') {
      query.push('payment_status=paid');
    } else if (this.data.activeFilter === 'pending') {
      query.push('payment_status=pending');
    }
    query.push(`page=${currentPage}`);
    query.push(`page_size=${this.data.pageSize}`);

    wx.request({
      url: `${API_BASE_URL}/api/member/orders?${query.join('&')}`,
      method: 'GET',
      header: {
        Authorization: authHeader,
      },
      success: (res) => {
        const payload = res && res.data ? res.data : {};
        const ok = res.statusCode >= 200 && res.statusCode < 300 && payload.code === 1 && payload.data;
        if (ok) {
          const orders = (payload.data.orders || []).map(normalizeOrder);
          const nextOrders = refresh ? orders : this.data.orders.concat(orders);
          const total = payload.data.total || nextOrders.length;
          const hasMore = nextOrders.length < total;
          this.setData({
            orders: nextOrders,
            total,
            page: currentPage + 1,
            hasMore,
          });
          return;
        }
        wx.showToast({ title: payload.message || '获取订单失败', icon: 'none' });
      },
      fail: () => {
        wx.showToast({ title: '网络异常，请稍后重试', icon: 'none' });
      },
      complete: () => {
        this.setData({ loading: false, refreshing: false });
        if (typeof done === 'function') done();
      },
    });
  },
})
