// subpackage/pages/mine/tax-cooperate/tax-cooperate.js
import { API_BASE_URL } from '../../../../utils/config';

const getAuthContext = () => {
  const userInfo = wx.getStorageSync('user_info');
  const userId = userInfo && userInfo.user_id ? userInfo.user_id : '';
  const token = wx.getStorageSync('access_token');
  if (!userId || !token) return null;
  const tokenType = String(wx.getStorageSync('token_type') || 'bearer');
  const normalizedType = tokenType.toLowerCase() === 'bearer' ? 'Bearer' : tokenType;
  return { userId, token, tokenType: normalizedType };
};

Page({
  data: {
    loading: false,
    errorText: '',
    // 接口原始数据
    application: null,
    // 计算后的展示字段
    view: {
      title: '',
      badgeText: '',
      badgeType: 'info', // info | success | warn | error
      description: '',
      showRejectReason: false,
      rejectReason: '',
      createdAt: '',
      applicationId: '',
    },
  },

  onLoad() {
    this.ensureLoginAndFetch();
  },

  onShow() {
    // 返回页面时刷新一次（例如刚提交完申请）
    this.ensureLoginAndFetch();
  },

  onPullDownRefresh() {
    this.ensureLoginAndFetch(true);
  },

  ensureLoginAndFetch(fromPullDown = false) {
    const auth = getAuthContext();
    if (!auth) {
      if (fromPullDown) wx.stopPullDownRefresh();
      wx.showModal({
        title: '请先登录',
        content: '查看税务师申请状态需要登录，是否前往登录？',
        confirmText: '去登录',
        cancelText: '取消',
        success: (res) => {
          if (res.confirm) {
            wx.navigateTo({
              url: '/pages/mine/login/login',
              fail: () => wx.reLaunch({ url: '/pages/mine/login/login' }),
            });
          } else {
            wx.navigateBack();
          }
        },
      });
      return;
    }
    this.fetchMyApplication(auth.token, fromPullDown);
  },

  fetchMyApplication(accessToken, fromPullDown = false) {
    if (!fromPullDown) {
      wx.showLoading({ title: '加载中...', mask: true });
    }
    this.setData({ loading: true, errorText: '' });

    wx.request({
      url: `${API_BASE_URL}/api/tax_accountant/my-application`,
      method: 'GET',
      header: {
        Authorization: `Bearer ${accessToken}`,
      },
      success: (res) => {
        const data = res.data || {};
        if (res.statusCode >= 200 && res.statusCode < 300 && data.code === 1) {
          const application = data.data || null;
          this.setData({
            application,
            view: this.buildView(application),
          });
        } else {
          this.setData({
            application: null,
            view: this.buildView(null),
            errorText: data.message || '获取失败，请稍后重试',
          });
        }
      },
      fail: (err) => {
        this.setData({
          application: null,
          view: this.buildView(null),
          errorText: err.errMsg || '网络错误，请稍后重试',
        });
      },
      complete: () => {
        wx.hideLoading();
        if (fromPullDown) wx.stopPullDownRefresh();
        this.setData({ loading: false });
      },
    });
  },

  buildView(application) {
    const hasApplied = !!(application && application.has_applied);
    const status = application ? application.status : null;
    const applicationId = application && application.application_id ? application.application_id : '';
    const createdAt = application && application.created_at ? application.created_at : '';
    const rejectReason = application && application.reject_reason ? application.reject_reason : '';

    if (!hasApplied) {
      return {
        title: '未提交申请',
        badgeText: '未申请',
        badgeType: 'info',
        description: '您当前还没有提交税务师入驻申请。',
        showRejectReason: false,
        rejectReason: '',
        createdAt: '',
        applicationId: '',
      };
    }

    if (status === 'pending') {
      return {
        title: '申请审核中',
        badgeText: '待审核',
        badgeType: 'warn',
        description: '您的申请已提交，正在审核中，请耐心等待。',
        showRejectReason: false,
        rejectReason: '',
        createdAt,
        applicationId,
      };
    }

    if (status === 'approved') {
      return {
        title: '审核通过',
        badgeText: '已通过',
        badgeType: 'success',
        description: '恭喜，您的税务师入驻申请已通过审核。',
        showRejectReason: false,
        rejectReason: '',
        createdAt,
        applicationId,
      };
    }

    if (status === 'rejected') {
      return {
        title: '审核未通过',
        badgeText: '已拒绝',
        badgeType: 'error',
        description: '您的申请未通过审核，可根据原因修改后重新提交。',
        showRejectReason: true,
        rejectReason: rejectReason || '（未提供拒绝原因）',
        createdAt,
        applicationId,
      };
    }

    return {
      title: '申请状态',
      badgeText: status || '未知',
      badgeType: 'info',
      description: '当前申请状态未知，请稍后重试。',
      showRejectReason: false,
      rejectReason: '',
      createdAt,
      applicationId,
    };
  },

  onGoApply() {
    wx.navigateTo({
      url: '/subpackage/pages/index/TaxConsultantInput/TaxConsultantInput',
    });
  },

  onRetry() {
    this.ensureLoginAndFetch();
  },
});