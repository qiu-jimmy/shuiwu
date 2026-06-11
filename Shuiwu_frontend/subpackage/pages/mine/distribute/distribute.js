// pages/mine/distribute/distribute.js
import { API_BASE_URL } from '../../../../utils/config';
const DISTRIBUTION_ENDPOINTS = {
  code: '/api/distribution/my-code',
  bindInviteCode: '/api/distribution/bind-invite-code',
  stats: '/api/distribution/stats',
  records: '/api/distribution/records',
  withdrawApply: '/api/distribution/withdraw',
  withdrawals: '/api/distribution/withdrawals',
  miniQrcode: '/api/distribution/mini-qrcode',
};
const MIN_WITHDRAW_AMOUNT = 50;
const POSTER_TEMPLATES = [
  {
    id: 1,
    url: 'https://tax-dragonai.oss-cn-heyuan.aliyuncs.com/user_files/user_2689ea75e1114ec4/2026/02/20260202-145515_eeb21e1d.png',
  },
  {
    id: 2,
    url: 'https://tax-dragonai.oss-cn-heyuan.aliyuncs.com/user_files/user_2689ea75e1114ec4/2026/02/Gemini_Generated_Image_e57q4ee57q4ee57q (1)(1)_1d6f2b56.png',
  },
  {
    id: 3,
    url: 'https://tax-dragonai.oss-cn-heyuan.aliyuncs.com/user_files/user_2689ea75e1114ec4/2026/02/Gemini_Generated_Image_e57q4ee57q4ee57q (2)(1)_bc2790c6.png',
  },
  {
    id: 4,
    url: 'https://tax-dragonai.oss-cn-heyuan.aliyuncs.com/user_files/user_2689ea75e1114ec4/2026/02/Gemini_Generated_Image_e57q4ee57q4ee57q(1)_72cfaadb.png',
  },
];
const MINI_QRCODE_PAGE = 'pages/index/index/index';
const WITHDRAW_METHODS = [
  { value: 'wechat', label: '微信' },
  { value: 'alipay', label: '支付宝' },
  { value: 'bank', label: '银行卡' },
];
const POSTER_IMAGE = 'https://tax-dragonai.oss-cn-heyuan.aliyuncs.com/user_files/user_2689ea75e1114ec4/2026/01/税务海报_301f4635.png';

const getAuthHeader = () => {
  const token = wx.getStorageSync('access_token');
  if (!token) {
    return '';
  }
  const tokenType = String(wx.getStorageSync('token_type') || 'bearer');
  const normalizedType = tokenType.toLowerCase() === 'bearer' ? 'Bearer' : tokenType;
  return `${normalizedType} ${token}`;
};

const normalizeUserInfo = (userInfo = {}) => ({
  ...userInfo,
  is_distributor: !!userInfo.is_distributor,
  distributor_code: userInfo.distributor_code ?? null,
});

const updateStoredUserInfo = (patch) => {
  const userInfo = wx.getStorageSync('user_info') || {};
  wx.setStorageSync('user_info', { ...userInfo, ...patch });
};

const formatAmount = (value) => {
  const amount = Number(value || 0);
  if (Number.isNaN(amount)) {
    return '0.00';
  }
  return amount.toFixed(2);
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

const formatCommissionStatus = (status) => {
  const map = {
    pending: { label: '待结算', theme: 'warning' },
    available: { label: '可提现', theme: 'success' },
    settled: { label: '已结算', theme: 'default' },
  };
  return map[status] || { label: status || '未知', theme: 'default' };
};

const formatWithdrawalStatus = (status) => {
  const map = {
    pending: { label: '待处理', theme: 'warning' },
    completed: { label: '已完成', theme: 'success' },
    rejected: { label: '已拒绝', theme: 'danger' },
  };
  return map[status] || { label: status || '未知', theme: 'default' };
};

const formatWithdrawalMethod = (method) => {
  const map = {
    wechat: '微信',
    alipay: '支付宝',
    bank: '银行卡',
  };
  return map[method] || method || '-';
};

const formatCommissionType = (value) => {
  const map = {
    direct: '直推',
    indirect: '间接',
  };
  return map[value] || value || '—';
};

const buildStatsDisplay = (stats) => ({
  totalCommission: formatAmount(stats.total_commission),
  availableCommission: formatAmount(stats.available_commission),
  frozenCommission: formatAmount(stats.frozen_commission),
  totalWithdrawn: formatAmount(stats.total_withdrawn),
  totalChildren: stats.total_children_count || 0,
  totalOrders: stats.total_order_count || 0,
});

const normalizePosterDataUrl = (value) => {
  if (!value) {
    return '';
  }
  const trimmed = String(value).trim();
  if (!trimmed) {
    return '';
  }
  if (trimmed.startsWith('data:image')) {
    return trimmed;
  }
  return `data:image/png;base64,${trimmed}`;
};

const parseBase64Image = (dataUrl) => {
  if (!dataUrl) {
    return null;
  }
  const match = String(dataUrl).match(/^data:image\/\w+;base64,(.*)$/);
  if (!match) {
    return null;
  }
  return {
    ext: 'png',
    base64: match[1] || '',
  };
};

const isImageDataUrl = (value) => typeof value === 'string' && value.startsWith('data:image');


Page({

  /**
   * 页面的初始数据
   */
  data: {
    isDistributor: false,
    distributorCode: '',
    inviterCode: '',
    inviterId: '',
    inviterNickname: '',
    loading: false,
    promoLoading: false,
    statsLoading: false,
    recordsLoading: false,
    withdrawalsLoading: false,
    activeTab: 'records',
    stats: {
      total_children_count: 0,
      total_order_count: 0,
      total_commission: 0,
      available_commission: 0,
      frozen_commission: 0,
      total_withdrawn: 0,
    },
    statsDisplay: {
      totalCommission: '0.00',
      availableCommission: '0.00',
      frozenCommission: '0.00',
      totalWithdrawn: '0.00',
      totalChildren: 0,
      totalOrders: 0,
    },
    records: [],
    recordPage: 1,
    recordHasMore: true,
    withdrawals: [],
    withdrawalPage: 1,
    withdrawalHasMore: true,
    withdrawVisible: false,
    withdrawAmount: '',
    withdrawMethodIndex: 0,
    withdrawMethod: WITHDRAW_METHODS[0].value,
    withdrawMethods: WITHDRAW_METHODS,
    withdrawPickerVisible: false,
    withdrawPickerValue: [WITHDRAW_METHODS[0].value],
    withdrawAccountName: '',
    withdrawAccountNumber: '',
    withdrawBankName: '',
    withdrawBankBranch: '',
    withdrawSubmitting: false,
    inviteBindVisible: false,
    inviteCodeInput: '',
    bindSubmitting: false,
    posterVisible: false,
    posterTemplateVisible: false,
    posterTemplates: POSTER_TEMPLATES,
    selectedPosterTemplate: POSTER_TEMPLATES[0].id,
    posterImage: POSTER_IMAGE,
    posterFilePath: '',
    posterLoading: false,
    posterSaving: false,
  },

  /**
   * 生命周期函数--监听页面加载
   */
  onLoad(options) {
    this.refreshUserInfo();
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
    this.refreshUserInfo();
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
    this.refreshUserInfo(() => {
      if (this.data.isDistributor) {
        this.loadDistributorData(() => {
          wx.stopPullDownRefresh();
        });
        return;
      }
      wx.stopPullDownRefresh();
    });
  },

  /**
   * 页面上拉触底事件的处理函数
   */
  onReachBottom() {
    if (!this.data.isDistributor) {
      return;
    }
    if (this.data.activeTab === 'records' && this.data.recordHasMore && !this.data.recordsLoading) {
      this.fetchRecords({ refresh: false });
      return;
    }
    if (this.data.activeTab === 'withdrawals' && this.data.withdrawalHasMore && !this.data.withdrawalsLoading) {
      this.fetchWithdrawals({ refresh: false });
    }
  },

  refreshUserInfo(done) {
    const stored = wx.getStorageSync('user_info') || {};
    const normalized = normalizeUserInfo(stored);
    wx.setStorageSync('user_info', normalized);
    this.setData({
      isDistributor: !!normalized.is_distributor,
      distributorCode: normalized.distributor_code || '',
    });
    if (this.data.isDistributor) {
      this.loadDistributorData();
    }
    if (typeof done === 'function') {
      done();
    }
  },

  onJoinTap() {
    if (this.data.loading) {
      return;
    }
    const authHeader = getAuthHeader();
    if (!authHeader) {
      wx.showToast({ title: '请先登录', icon: 'none' });
      return;
    }
    this.setData({ loading: true });
    wx.request({
      url: `${API_BASE_URL}/api/distribution/become-distributor`,
      method: 'POST',
      header: {
        Authorization: authHeader,
      },
      success: (res) => {
        const payload = res && res.data ? res.data : {};
        const ok = res.statusCode >= 200 && res.statusCode < 300 && payload.code === 1;
        if (ok) {
          const data = payload.data || {};
          const existing = wx.getStorageSync('user_info') || {};
          const updated = {
            ...existing,
            is_distributor: true,
            distributor_code: data.distributor_code || existing.distributor_code || '',
          };
          updateStoredUserInfo(updated);
          this.setData({
            isDistributor: true,
            distributorCode: updated.distributor_code,
          });
          this.loadDistributorData();
          wx.showToast({ title: payload.message || '加入成功', icon: 'success' });
          return;
        }
        wx.showToast({ title: payload.message || '加入失败', icon: 'none' });
      },
      fail: () => {
        wx.showToast({ title: '网络异常，请稍后重试', icon: 'none' });
      },
      complete: () => {
        this.setData({ loading: false });
      },
    });
  },

  onTabChange(e) {
    const value = e.detail && e.detail.value ? e.detail.value : 'records';
    this.setData({ activeTab: value });
    if (value === 'records' && !this.data.records.length) {
      this.fetchRecords({ refresh: true });
    }
    if (value === 'withdrawals' && !this.data.withdrawals.length) {
      this.fetchWithdrawals({ refresh: true });
    }
  },

  onCopyCode() {
    const code = this.data.distributorCode;
    if (!code) {
      wx.showToast({ title: '暂无邀请码', icon: 'none' });
      return;
    }
    wx.setClipboardData({
      data: code,
      success: () => {
        wx.showToast({ title: '邀请码已复制', icon: 'success' });
      },
    });
  },

  getPoster() {
    if (this.data.posterLoading) {
      return;
    }
    const authHeader = getAuthHeader();
    if (!authHeader) {
      wx.showToast({ title: '请先登录', icon: 'none' });
      return;
    }
    this.setData({ posterTemplateVisible: true });
  },

  onPosterTemplateClose() {
    this.setData({ posterTemplateVisible: false });
  },

  onPosterTemplateSelect(e) {
    if (this.data.posterLoading) {
      return;
    }
    const templateId = Number(e.currentTarget.dataset.id || 0);
    if (!templateId) {
      return;
    }
    this.setData({
      posterTemplateVisible: false,
      selectedPosterTemplate: templateId,
    });
    this.requestPoster(templateId);
  },

  requestPoster(templateId) {
    if (this.data.posterLoading) {
      return;
    }
    const authHeader = getAuthHeader();
    if (!authHeader) {
      wx.showToast({ title: '请先登录', icon: 'none' });
      return;
    }
    const resolvedTemplateId = Number(templateId) || 1;
    this.setData({ posterLoading: true });
    wx.showLoading({ title: '海报生成中', mask: true });
    wx.request({
      url: `${API_BASE_URL}${DISTRIBUTION_ENDPOINTS.miniQrcode}`,
      method: 'POST',
      header: {
        Authorization: authHeader,
        'Content-Type': 'application/json',
      },
      data: {
        page: MINI_QRCODE_PAGE,
        img: resolvedTemplateId,
        image: resolvedTemplateId,
      },
      success: (res) => {
        const payload = res && res.data ? res.data : {};
        const ok = res.statusCode >= 200 && res.statusCode < 300 && payload.code === 1;
        if (!ok) {
          wx.showToast({ title: payload.message || '获取海报失败', icon: 'none' });
          return;
        }
        const data = payload.data || {};
        const posterDataUrl = normalizePosterDataUrl(data.data_url || data.base64);
        if (!posterDataUrl) {
          wx.showToast({ title: '获取海报失败', icon: 'none' });
          return;
        }
        this.setData({
          posterImage: posterDataUrl,
          posterFilePath: '',
          posterVisible: true,
        });
      },
      fail: () => {
        wx.showToast({ title: '网络异常，请稍后重试', icon: 'none' });
      },
      complete: () => {
        wx.hideLoading();
        this.setData({ posterLoading: false });
      },
    });
  },

  onPosterClose() {
    this.setData({ posterVisible: false });
  },

  onPosterVisibleChange(e) {
    const detail = e && e.detail ? e.detail : {};
    if (detail.visible === false) {
      this.onPosterClose();
    }
  },

  preparePosterSource(done, fail) {
    const image = this.data.posterImage || POSTER_IMAGE;
    if (!image) {
      wx.showToast({ title: '暂无海报', icon: 'none' });
      if (typeof fail === 'function') {
        fail();
      }
      return;
    }
    if (!isImageDataUrl(image)) {
      done({ src: image, isLocal: false });
      return;
    }
    if (this.data.posterFilePath) {
      done({ src: this.data.posterFilePath, isLocal: true });
      return;
    }
    const parsed = parseBase64Image(image);
    if (!parsed || !parsed.base64) {
      wx.showToast({ title: '海报加载失败', icon: 'none' });
      if (typeof fail === 'function') {
        fail();
      }
      return;
    }
    const filePath = `${wx.env.USER_DATA_PATH}/promo_poster_${Date.now()}.png`;
    wx.getFileSystemManager().writeFile({
      filePath,
      data: parsed.base64,
      encoding: 'base64',
      success: () => {
        this.setData({ posterFilePath: filePath });
        done({ src: filePath, isLocal: true });
      },
      fail: () => {
        wx.showToast({ title: '海报加载失败', icon: 'none' });
        if (typeof fail === 'function') {
          fail();
        }
      },
    });
  },

  onPosterPreview() {
    this.preparePosterSource((source) => {
      wx.previewImage({
        current: source.src,
        urls: [source.src],
      });
    });
  },

  onPosterSave() {
    if (this.data.posterSaving) {
      return;
    }

    const saveImage = (filePath) => {
      wx.saveImageToPhotosAlbum({
        filePath,
        success: () => {
          wx.showToast({ title: '保存成功', icon: 'success' });
        },
        fail: () => {
          wx.showToast({ title: '保存失败', icon: 'none' });
        },
        complete: () => {
          this.setData({ posterSaving: false });
        },
      });
    };

    const requestAuthAndSave = (filePath) => {
      wx.getSetting({
        success: (res) => {
          const hasAuth = res && res.authSetting && res.authSetting['scope.writePhotosAlbum'];
          if (hasAuth) {
            saveImage(filePath);
            return;
          }
          wx.authorize({
            scope: 'scope.writePhotosAlbum',
            success: () => saveImage(filePath),
            fail: () => {
              this.setData({ posterSaving: false });
              wx.showModal({
                title: '需要授权',
                content: '请允许保存到相册权限后再试',
                confirmText: '去设置',
                success: (modal) => {
                  if (modal.confirm) {
                    wx.openSetting();
                  }
                },
              });
            },
          });
        },
        fail: () => {
          saveImage(filePath);
        },
      });
    };

    this.setData({ posterSaving: true });
    this.preparePosterSource(
      (source) => {
        if (source.isLocal) {
          requestAuthAndSave(source.src);
          return;
        }
        wx.getImageInfo({
          src: source.src,
          success: (res) => {
            requestAuthAndSave(res.path || source.src);
          },
          fail: () => {
            this.setData({ posterSaving: false });
            wx.showToast({ title: '海报加载失败', icon: 'none' });
          },
        });
      },
      () => {
        this.setData({ posterSaving: false });
      }
    );
  },

  onInviteBindOpen() {
    if (this.data.inviterCode) {
      return;
    }
    this.setData({
      inviteBindVisible: true,
      inviteCodeInput: '',
    });
  },

  onInviteBindClose() {
    this.setData({ inviteBindVisible: false });
  },

  onInviteCodeChange(e) {
    this.setData({ inviteCodeInput: e.detail.value });
  },

  onInviteBindSubmit() {
    if (this.data.bindSubmitting) {
      return;
    }
    const inviteCode = String(this.data.inviteCodeInput || '').trim();
    if (!inviteCode) {
      wx.showToast({ title: '璇疯緭鍏ユ帹骞跨爜', icon: 'none' });
      return;
    }
    const authHeader = getAuthHeader();
    if (!authHeader) {
      wx.showToast({ title: '璇峰厛鐧诲綍', icon: 'none' });
      return;
    }
    this.setData({ bindSubmitting: true });
    wx.request({
      url: `${API_BASE_URL}${DISTRIBUTION_ENDPOINTS.bindInviteCode}`,
      method: 'POST',
      header: {
        Authorization: authHeader,
        'content-type': 'application/json',
      },
      data: {
        invite_code: inviteCode,
      },
      success: (res) => {
        const payload = res && res.data ? res.data : {};
        const ok = res.statusCode >= 200 && res.statusCode < 300 && payload.code === 1;
        if (ok) {
          const data = payload.data || {};
          this.setData({
            inviterCode: inviteCode,
            inviterId: data.inviter_id || '',
            inviterNickname: data.inviter_nickname || '',
            inviteBindVisible: false,
            inviteCodeInput: '',
          });
          wx.showToast({ title: payload.message || '缁戝畾鎴愬姛', icon: 'success' });
          return;
        }
        wx.showToast({ title: payload.message || '缁戝畾澶辫触', icon: 'none' });
      },
      fail: () => {
        wx.showToast({ title: '缃戠粶寮傚父锛岃绋嶅悗閲嶈瘯', icon: 'none' });
      },
      complete: () => {
        this.setData({ bindSubmitting: false });
      },
    });
  },

  onWithdrawOpen() {
    this.setData({
      withdrawVisible: true,
      withdrawAmount: '',
      withdrawMethodIndex: 0,
      withdrawMethod: WITHDRAW_METHODS[0].value,
      withdrawPickerVisible: false,
      withdrawPickerValue: [WITHDRAW_METHODS[0].value],
      withdrawAccountName: '',
      withdrawAccountNumber: '',
      withdrawBankName: '',
      withdrawBankBranch: '',
    });
  },

  onWithdrawClose() {
    this.setData({ withdrawVisible: false, withdrawPickerVisible: false });
  },

  onWithdrawAmountChange(e) {
    this.setData({ withdrawAmount: e.detail.value });
  },

  onWithdrawPickerOpen() {
    const value = this.data.withdrawMethod || WITHDRAW_METHODS[0].value;
    this.setData({
      withdrawPickerVisible: true,
      withdrawPickerValue: [value],
    });
  },

  onWithdrawPickerConfirm(e) {
    const detail = e && e.detail ? e.detail : {};
    const values = Array.isArray(detail.value) ? detail.value : [detail.value];
    const method = values[0] || WITHDRAW_METHODS[0].value;
    const index = WITHDRAW_METHODS.findIndex((item) => item.value === method);
    const normalizedMethod = index >= 0 ? method : WITHDRAW_METHODS[0].value;
    const nextData = {
      withdrawMethodIndex: index >= 0 ? index : 0,
      withdrawMethod: normalizedMethod,
      withdrawPickerVisible: false,
      withdrawPickerValue: [normalizedMethod],
    };
    if (normalizedMethod !== 'bank') {
      nextData.withdrawBankName = '';
      nextData.withdrawBankBranch = '';
    }
    this.setData(nextData);
  },

  onWithdrawPickerCancel() {
    this.setData({ withdrawPickerVisible: false });
  },

  onWithdrawPickerClose() {
    this.setData({ withdrawPickerVisible: false });
  },

  onWithdrawFieldChange(e) {
    const field = e.currentTarget.dataset.field;
    if (!field) {
      return;
    }
    this.setData({ [field]: e.detail.value });
  },

  onWithdrawSubmit() {
    if (this.data.withdrawSubmitting) {
      return;
    }
    const amount = Number(this.data.withdrawAmount);
    if (!amount || Number.isNaN(amount) || amount <= 0) {
      wx.showToast({ title: '请输入提现金额', icon: 'none' });
      return;
    }
    if (amount < MIN_WITHDRAW_AMOUNT) {
      wx.showToast({ title: `最低提现金额为${MIN_WITHDRAW_AMOUNT}元`, icon: 'none' });
      return;
    }
    if (amount > Number(this.data.stats.available_commission || 0)) {
      wx.showToast({ title: '超过可提现金额', icon: 'none' });
      return;
    }
    const withdrawalMethod =
      this.data.withdrawMethod ||
      (WITHDRAW_METHODS[this.data.withdrawMethodIndex]
        ? WITHDRAW_METHODS[this.data.withdrawMethodIndex].value
        : '');
    if (!withdrawalMethod) {
      wx.showToast({ title: '请选择提现方式', icon: 'none' });
      return;
    }
    const accountName = String(this.data.withdrawAccountName || '').trim();
    if (!accountName) {
      wx.showToast({ title: '请输入账户姓名', icon: 'none' });
      return;
    }
    const accountNumber = String(this.data.withdrawAccountNumber || '').trim();
    if (!accountNumber) {
      wx.showToast({ title: '请输入账户号码', icon: 'none' });
      return;
    }
    const requestData = {
      amount,
      withdrawal_method: withdrawalMethod,
      account_name: accountName,
      account_number: accountNumber,
    };
    if (withdrawalMethod === 'bank') {
      const bankName = String(this.data.withdrawBankName || '').trim();
      if (!bankName) {
        wx.showToast({ title: '请输入银行名称', icon: 'none' });
        return;
      }
      const bankBranch = String(this.data.withdrawBankBranch || '').trim();
      if (!bankBranch) {
        wx.showToast({ title: '请输入支行名称', icon: 'none' });
        return;
      }
      requestData.bank_name = bankName;
      requestData.bank_branch = bankBranch;
    }
    const authHeader = getAuthHeader();
    if (!authHeader) {
      wx.showToast({ title: '请先登录', icon: 'none' });
      return;
    }
    this.setData({ withdrawSubmitting: true });
    wx.request({
      url: `${API_BASE_URL}${DISTRIBUTION_ENDPOINTS.withdrawApply}`,
      method: 'POST',
      header: {
        Authorization: authHeader,
        'content-type': 'application/json',
      },
      data: requestData,
      success: (res) => {
        const payload = res && res.data ? res.data : {};
        const ok = res.statusCode >= 200 && res.statusCode < 300 && payload.code === 1;
        if (ok) {
          wx.showToast({ title: payload.message || '提现申请已提交', icon: 'success' });
          this.setData({ withdrawVisible: false, withdrawAmount: '' });
          this.fetchStats();
          this.fetchWithdrawals({ refresh: true });
          return;
        }
        wx.showToast({ title: payload.message || '提现申请失败', icon: 'none' });
      },
      fail: () => {
        wx.showToast({ title: '网络异常，请稍后重试', icon: 'none' });
      },
      complete: () => {
        this.setData({ withdrawSubmitting: false });
      },
    });
  },

  loadDistributorData(done) {
    this.fetchPromoCode();
    this.fetchStats();
    this.fetchRecords({ refresh: true });
    this.fetchWithdrawals({ refresh: true });
    if (typeof done === 'function') {
      done();
    }
  },

  fetchPromoCode() {
    const authHeader = getAuthHeader();
    if (!authHeader) {
      return;
    }
    if (this.data.promoLoading) {
      return;
    }
    this.setData({ promoLoading: true });
    wx.request({
      url: `${API_BASE_URL}${DISTRIBUTION_ENDPOINTS.code}`,
      method: 'GET',
      header: {
        Authorization: authHeader,
      },
      success: (res) => {
        const payload = res && res.data ? res.data : {};
        const ok = res.statusCode >= 200 && res.statusCode < 300 && payload.code === 1 && payload.data;
        if (ok) {
          const code = payload.data.distributor_code || '';
          const inviterCode = payload.data.inviter || '';
          const nextData = {
            distributorCode: code,
            inviterCode,
          };
          if (!inviterCode) {
            nextData.inviterId = '';
            nextData.inviterNickname = '';
          }
          this.setData(nextData);
          updateStoredUserInfo({ distributor_code: code, is_distributor: true });
          return;
        }
      },
      complete: () => {
        this.setData({ promoLoading: false });
      },
    });
  },

  fetchStats() {
    const authHeader = getAuthHeader();
    if (!authHeader) {
      return;
    }
    if (this.data.statsLoading) {
      return;
    }
    this.setData({ statsLoading: true });
    wx.request({
      url: `${API_BASE_URL}${DISTRIBUTION_ENDPOINTS.stats}`,
      method: 'GET',
      header: {
        Authorization: authHeader,
      },
      success: (res) => {
        const payload = res && res.data ? res.data : {};
        const ok = res.statusCode >= 200 && res.statusCode < 300 && payload.code === 1 && payload.data;
        if (ok) {
          this.setData({ stats: payload.data, statsDisplay: buildStatsDisplay(payload.data) });
          return;
        }
        wx.showToast({ title: payload.message || '获取统计失败', icon: 'none' });
      },
      fail: () => {
        wx.showToast({ title: '网络异常，请稍后重试', icon: 'none' });
      },
      complete: () => {
        this.setData({ statsLoading: false });
      },
    });
  },

  fetchRecords({ refresh } = {}) {
    const authHeader = getAuthHeader();
    if (!authHeader) {
      return;
    }
    const page = refresh ? 1 : this.data.recordPage;
    if (this.data.recordsLoading) {
      return;
    }
    this.setData({ recordsLoading: true });
    wx.request({
      url: `${API_BASE_URL}${DISTRIBUTION_ENDPOINTS.records}?page=${page}&page_size=10`,
      method: 'GET',
      header: {
        Authorization: authHeader,
      },
      success: (res) => {
        const payload = res && res.data ? res.data : {};
        const ok = res.statusCode >= 200 && res.statusCode < 300 && payload.code === 1 && payload.data;
        if (ok) {
          const list = (payload.data.records || []).map((record) => {
            const status = formatCommissionStatus(record.commission_status);
            return {
              ...record,
              commissionLabel: formatAmount(record.commission_amount),
              orderAmountLabel: formatAmount(record.order_amount),
              createdLabel: formatDateTime(record.created_at),
              expireLabel: formatDateTime(record.expire_time),
              statusLabel: status.label,
              statusTheme: status.theme,
              typeLabel: formatCommissionType(record.commission_type),
            };
          });
          const nextRecords = refresh ? list : this.data.records.concat(list);
          const total = payload.data.total || nextRecords.length;
          this.setData({
            records: nextRecords,
            recordPage: page + 1,
            recordHasMore: nextRecords.length < total,
          });
          return;
        }
        wx.showToast({ title: payload.message || '获取分销记录失败', icon: 'none' });
      },
      fail: () => {
        wx.showToast({ title: '网络异常，请稍后重试', icon: 'none' });
      },
      complete: () => {
        this.setData({ recordsLoading: false });
      },
    });
  },

  fetchWithdrawals({ refresh } = {}) {
    const authHeader = getAuthHeader();
    if (!authHeader) {
      return;
    }
    const page = refresh ? 1 : this.data.withdrawalPage;
    if (this.data.withdrawalsLoading) {
      return;
    }
    this.setData({ withdrawalsLoading: true });
    wx.request({
      url: `${API_BASE_URL}${DISTRIBUTION_ENDPOINTS.withdrawals}?page=${page}&page_size=10`,
      method: 'GET',
      header: {
        Authorization: authHeader,
      },
      success: (res) => {
        const payload = res && res.data ? res.data : {};
        const ok = res.statusCode >= 200 && res.statusCode < 300 && payload.code === 1 && payload.data;
        if (ok) {
          const list = (payload.data.withdrawals || []).map((item) => {
            const status = formatWithdrawalStatus(item.status);
            const methodLabel = formatWithdrawalMethod(item.withdrawal_method);
            return {
              ...item,
              amountLabel: formatAmount(item.amount),
              methodLabel,
              statusLabel: status.label,
              statusTheme: status.theme,
              createdLabel: formatDateTime(item.created_at),
              processedLabel: item.processed_at ? formatDateTime(item.processed_at) : '—',
            };
          });
          const nextList = refresh ? list : this.data.withdrawals.concat(list);
          const total = payload.data.total || nextList.length;
          this.setData({
            withdrawals: nextList,
            withdrawalPage: page + 1,
            withdrawalHasMore: nextList.length < total,
          });
          return;
        }
        wx.showToast({ title: payload.message || '获取提现记录失败', icon: 'none' });
      },
      fail: () => {
        wx.showToast({ title: '网络异常，请稍后重试', icon: 'none' });
      },
      complete: () => {
        this.setData({ withdrawalsLoading: false });
      },
    });
  },
})
