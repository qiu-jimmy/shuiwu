// subpackage/pages/mine/point/point.js
import { API_BASE_URL } from '../../../../utils/config';

const formatPoints = (value) => {
  const amount = Number(value || 0);
  if (!Number.isFinite(amount)) {
    return '0';
  }
  return amount % 1 === 0 ? amount.toFixed(0) : amount.toFixed(2);
};

const formatDateTime = (value) => {
  if (!value) {
    return '';
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

const changeTypeMap = {
  manual_grant: { label: '手动发放', theme: 'success' },
  order_reward: { label: '订单奖励', theme: 'success' },
  invite_reward: { label: '邀请奖励', theme: 'success' },
  consume: { label: '积分消耗', theme: 'danger' },
  refund: { label: '退款扣回', theme: 'warning' },
  system_adjust: { label: '系统调整', theme: 'default' },
};

const buildRelatedLabel = (record = {}) => {
  if (record.related_order_id) {
    const amount = record.order_amount != null ? ` · 订单金额 ${formatPoints(record.order_amount)}` : '';
    return `关联订单 ${record.related_order_id}${amount}`;
  }
  if (record.related_user_nickname) {
    const userId = record.related_user_id ? ` (${record.related_user_id})` : '';
    return `关联用户 ${record.related_user_nickname}${userId}`;
  }
  if (record.related_user_id) {
    return `关联用户 ${record.related_user_id}`;
  }
  return '';
};

const normalizeRecord = (record) => {
  const pointsValue = Number(record.points || 0);
  const pointsLabel = `${pointsValue > 0 ? '+' : ''}${formatPoints(pointsValue)}`;
  const pointsClass = pointsValue > 0 ? 'points-positive' : pointsValue < 0 ? 'points-negative' : 'points-neutral';
  const change = changeTypeMap[record.change_type] || { label: record.change_type || '积分变动', theme: 'default' };
  return {
    ...record,
    title: record.change_reason || change.label || '积分变动',
    changeTypeLabel: change.label,
    tagTheme: change.theme,
    pointsLabel,
    pointsClass,
    balanceLabel: formatPoints(record.balance_after),
    createdLabel: formatDateTime(record.created_at),
    relatedLabel: buildRelatedLabel(record),
  };
};

Page({

  /**
   * 页面的初始数据
   */
  data: {
    records: [],
    total: 0,
    page: 1,
    pageSize: 20,
    hasMore: true,
    loading: false,
    refreshing: false,
    balanceLabel: '0',
    lastUpdatedLabel: '',
    hasLoaded: false,
  },

  /**
   * 生命周期函数--监听页面加载
   */
  onLoad() {
    this.fetchRecords({ refresh: true });
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
    if (!this.data.hasLoaded) {
      this.setData({ hasLoaded: true });
      return;
    }
    this.fetchRecords({ refresh: true });
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
    this.fetchRecords({
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
      this.fetchRecords({ refresh: false });
    }
  },

  /**
   * 用户点击右上角分享
   */
  onShareAppMessage() {

  },

  fetchRecords({ refresh, done } = {}) {
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

    wx.request({
      url: `${API_BASE_URL}/api/user/points/records?page=${currentPage}&page_size=${this.data.pageSize}`,
      method: 'GET',
      header: {
        Authorization: authHeader,
      },
      success: (res) => {
        const payload = res && res.data ? res.data : {};
        const ok = res.statusCode >= 200 && res.statusCode < 300;
        if (!ok) {
          wx.showToast({ title: payload.message || '获取积分记录失败', icon: 'none' });
          return;
        }

        const data = payload.code === 1 && payload.data ? payload.data : payload;
        const rawRecords = Array.isArray(data.records) ? data.records : [];
        const normalized = rawRecords.map(normalizeRecord);
        const nextRecords = refresh ? normalized : this.data.records.concat(normalized);
        const serverTotal = Number(data.total);
        const hasTotal = Number.isFinite(serverTotal) && serverTotal >= 0;
        const total = hasTotal ? serverTotal : nextRecords.length;
        const hasMore = hasTotal ? nextRecords.length < serverTotal : rawRecords.length === this.data.pageSize;
        const nextState = {
          records: nextRecords,
          total,
          page: currentPage + 1,
          hasMore,
        };

        if (refresh) {
          const latestRecord = rawRecords.reduce((latest, item) => {
            if (!latest) return item;
            const latestTime = new Date(latest.created_at).getTime();
            const itemTime = new Date(item.created_at).getTime();
            if (Number.isNaN(itemTime)) return latest;
            if (Number.isNaN(latestTime)) return item;
            return itemTime > latestTime ? item : latest;
          }, null);
          const balance = latestRecord ? formatPoints(latestRecord.balance_after) : '0';
          const lastUpdated = latestRecord ? formatDateTime(latestRecord.created_at) : '';
          nextState.balanceLabel = balance;
          nextState.lastUpdatedLabel = lastUpdated;
        }

        this.setData(nextState);
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
