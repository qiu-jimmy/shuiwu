// pages/vip-buy/vip-buy.js
import { API_BASE_URL, OSS_URL } from '../../../../utils/config';

// 小程序支付 AppID
const PAY_APP_ID = 'wx44805469e5b39573';
const formatMemberLevel = (level) => {
  const map = {
    free: '免费版',
    vip: 'VIP会员',
    vip_month: 'VIP月卡',
    vip_quarter: 'VIP季卡',
    vip_year: 'VIP年卡',
  };
  return map[level] || level || '未开通';
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

const formatPrice = (value) => {
  const price = Number(value || 0);
  if (Number.isNaN(price)) {
    return '0';
  }
  return price % 1 === 0 ? `${price.toFixed(0)}` : `${price.toFixed(1)}`;
};

const formatDuration = (type, days) => {
  const map = {
    month: '/月',
    quarter: '/季',
    year: '/年',
    lifetime: '/永久',
  };
  if (map[type]) {
    return map[type];
  }
  return days ? `/${days}天` : '';
};

const DURATION_LABEL_MAP = {
  month: '1个月',
  year: '1年',
};

const DURATION_TYPES = Object.keys(DURATION_LABEL_MAP);

const getVersionKey = (pkg) => {
  const configLevel = pkg && pkg.custom_config ? pkg.custom_config.level : '';
  if (configLevel) {
    return configLevel;
  }
  const packageId = pkg && pkg.package_id ? String(pkg.package_id) : '';
  if (packageId.endsWith('_month')) {
    return packageId.slice(0, -6);
  }
  if (packageId.endsWith('_year')) {
    return packageId.slice(0, -5);
  }
  return packageId;
};

const buildDurationOptions = (packages, selectedVersionKey) => DURATION_TYPES
  .filter((type) => packages.some((item) => item.package_type === type))
  .map((type) => {
    const matchedPackage = packages.find((item) => (
      item.package_type === type && getVersionKey(item) === selectedVersionKey
    ));
    return {
      package_type: type,
      name: DURATION_LABEL_MAP[type],
      package_id: matchedPackage ? matchedPackage.package_id : '',
      priceLabel: matchedPackage ? matchedPackage.priceLabel : '',
      badge: type === 'year' ? '推荐' : '',
    };
  });

const buildVersionOptions = (packages, durationType) => {
  if (!durationType) {
    return [];
  }
  const versionMap = new Map();
  packages.forEach((pkg) => {
    if (pkg.package_type !== durationType) {
      return;
    }
    const versionKey = getVersionKey(pkg);
    if (!versionKey || versionMap.has(versionKey)) {
      return;
    }
    versionMap.set(versionKey, {
      versionKey,
      package_id: pkg.package_id,
      name: pkg.name,
      priceLabel: pkg.priceLabel,
      priceValue: pkg.priceValue,
      badge: pkg.badge || '',
      sort_order: Number(pkg.sort_order || 0),
    });
  });
  return Array.from(versionMap.values()).sort((a, b) => {
    if (a.sort_order !== b.sort_order) {
      return a.sort_order - b.sort_order;
    }
    return a.priceValue - b.priceValue;
  });
};

const buildSelectionState = (packages, currentDurationType, currentVersionKey) => {
  const durationTypes = DURATION_TYPES.filter((type) => packages.some((item) => item.package_type === type));
  const preferredDurationType = durationTypes.some((type) => type === currentDurationType)
    ? currentDurationType
    : (durationTypes[0] || '');
  const versionOptions = buildVersionOptions(packages, preferredDurationType);
  const selectedVersionKey = versionOptions.some((item) => item.versionKey === currentVersionKey)
    ? currentVersionKey
    : (versionOptions[0] ? versionOptions[0].versionKey : '');
  const durationOptions = buildDurationOptions(packages, selectedVersionKey);
  let selectedDurationType = durationOptions.some(
    (item) => item.package_type === currentDurationType && item.package_id
  )
    ? currentDurationType
    : '';
  if (!selectedDurationType) {
    const availableDuration = durationOptions.find((item) => item.package_id);
    selectedDurationType = availableDuration
      ? availableDuration.package_type
      : (durationOptions[0] ? durationOptions[0].package_type : '');
  }
  const selectedDurationOption = durationOptions.find((item) => item.package_type === selectedDurationType);
  return {
    durationOptions,
    versionOptions,
    selectedDurationType,
    selectedVersionKey,
    selectedPackageId: selectedDurationOption ? selectedDurationOption.package_id : '',
  };
};

const buildBenefits = (pkg) => ([
  { label: '每日对话', value: pkg.max_daily_chats < 0 ? '不限' : `${pkg.max_daily_chats}次` },
  { label: '知识库数量', value: `${pkg.max_kb_count}个` },
  { label: '知识库文档', value: `${pkg.max_kb_documents}份` },
  { label: '文件容量', value: `${pkg.max_file_storage_mb}MB` },
  { label: '文件数量', value: `${pkg.max_file_count}个` },
  { label: 'RAG检索', value: pkg.enable_rag ? '支持' : '不支持' },
  { label: '联网搜索', value: pkg.enable_web_search ? '支持' : '不支持' },
  { label: 'MCP工具', value: pkg.enable_mcp_tools ? '支持' : '不支持' },
]);

const normalizePackage = (pkg) => {
  const priceValue = Number(pkg.price || 0);
  const badgeMap = {
    year: '推荐',
    quarter: '热门',
  };
  return {
    ...pkg,
    priceValue,
    priceLabel: formatPrice(priceValue),
    durationLabel: formatDuration(pkg.package_type, pkg.duration_days),
    dailyChatsLabel: pkg.max_daily_chats < 0 ? '不限' : `${pkg.max_daily_chats}/天`,
    badge: badgeMap[pkg.package_type] || '',
  };
};

Page({

  /**
   * 页面的初始数据
   */
  data: {
    // OSS图片地址前缀
    ossUrl: OSS_URL,
    activeTab: 'packages',
    packages: [],
    versionOptions: [],
    durationOptions: [],
    loading: false,
    selectedPackageId: '',
    selectedVersionKey: '',
    selectedDurationType: '',
    selectedPayMethod: '',
    agreementChecked: false,
    detailVisible: false,
    detailPackage: {
      benefits: [],
    },
    records: [],
    currentMemberLabel: '未开通',
  },

  /**
   * 生命周期函数--监听页面加载
   */
  onLoad(options) {
    this.loadUserInfo();
    this.loadPackages();
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
    this.loadUserInfo();
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
    this.loadPackages(() => {
      wx.stopPullDownRefresh();
    });
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

  },

  loadUserInfo() {
    const userInfo = wx.getStorageSync('user_info') || {};
    this.setData({
      currentMemberLabel: formatMemberLevel(userInfo.member_level),
    });
  },

  loadPackages(done) {
    const authHeader = getAuthHeader();
    if (!authHeader) {
      wx.showToast({ title: '请先登录', icon: 'none' });
      if (typeof done === 'function') done();
      return;
    }
    this.setData({ loading: true });
    wx.request({
      url: `${API_BASE_URL}/api/member/packages?status=active`,
      method: 'GET',
      header: {
        Authorization: authHeader,
      },
      success: (res) => {
        const payload = res && res.data ? res.data : {};
        const ok = res.statusCode >= 200 && res.statusCode < 300 && payload.code === 1 && payload.data;
        if (ok) {
          const packages = (payload.data.packages || [])
            .filter((item) => item.status === 'active')
            .sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0))
            .map(normalizePackage);
          const selectionState = buildSelectionState(
            packages,
            this.data.selectedDurationType,
            this.data.selectedVersionKey
          );
          this.setData({
            packages,
            ...selectionState,
          });
          return;
        }
        wx.showToast({ title: payload.message || '获取套餐失败', icon: 'none' });
      },
      fail: () => {
        wx.showToast({ title: '网络异常，请稍后重试', icon: 'none' });
      },
      complete: () => {
        this.setData({ loading: false });
        if (typeof done === 'function') done();
      },
    });
  },

  onTabChange(e) {
    const value = e.detail && e.detail.value ? e.detail.value : 'packages';
    this.setData({ activeTab: value });
  },

  onPackageSelect(e) {
    const versionKey = e.currentTarget.dataset.versionKey;
    if (!versionKey) {
      return;
    }
    const selectionState = buildSelectionState(
      this.data.packages,
      this.data.selectedDurationType,
      versionKey
    );
    this.setData(selectionState);
  },

  onDurationSelect(e) {
    const durationType = e.currentTarget.dataset.type;
    if (!durationType || durationType === this.data.selectedDurationType) {
      return;
    }
    const targetDuration = this.data.durationOptions.find((item) => item.package_type === durationType);
    if (!targetDuration || !targetDuration.package_id) {
      wx.showToast({ title: '该版本暂无此购买时长', icon: 'none' });
      return;
    }
    const selectionState = buildSelectionState(
      this.data.packages,
      durationType,
      this.data.selectedVersionKey
    );
    this.setData(selectionState);
  },

  onPayMethodSelect(e) {
    const method = e.currentTarget.dataset.method;
    if (!method) {
      return;
    }
    this.setData({ selectedPayMethod: method });
  },

  onAgreementToggle() {
    this.setData({ agreementChecked: !this.data.agreementChecked });
  },

  onPackageDetail(e) {
    const id = e.currentTarget.dataset.id;
    const target = this.data.packages.find((item) => item.package_id === id);
    if (!target) {
      return;
    }
    this.setData({
      detailVisible: true,
      detailPackage: {
        ...target,
        benefits: buildBenefits(target),
      },
    });
  },

  onDetailClose() {
    this.setData({ detailVisible: false });
  },

  onDetailVisibleChange(e) {
    const visible = e.detail ? e.detail.visible : false;
    this.setData({ detailVisible: visible });
  },

  onPurchaseTap(e) {
    if (!this.data.selectedPackageId) {
      wx.showToast({ title: '请选择订阅方式', icon: 'none' });
      return;
    }
    if (!this.data.selectedPayMethod) {
      wx.showToast({ title: '请选择支付方式', icon: 'none' });
      return;
    }
    if (!this.data.agreementChecked) {
      wx.showToast({ title: '请先勾选协议', icon: 'none' });
      return;
    }
    const id = e.currentTarget.dataset.id;
    const target = this.data.packages.find((item) => item.package_id === id);
    if (!target) {
      return;
    }
    if (Number(target.price) <= 0) {
      wx.showToast({ title: '已选择免费版', icon: 'success' });
      this.setData({ selectedPackageId: id });
      return;
    }

    // 开始支付流程
    this.doPayment(target);
  },

  // 完整支付流程
  async doPayment(pkg) {
    const authHeader = getAuthHeader();
    if (!authHeader) {
      wx.showToast({ title: '请先登录', icon: 'none' });
      return;
    }

    // 获取用户 openid
    const userInfo = wx.getStorageSync('user_info') || {};
    const openid = userInfo.wx_openid;
    if (!openid) {
      wx.showToast({ title: '未获取到微信授权信息，请重新登录', icon: 'none' });
      return;
    }

    wx.showLoading({ title: '创建订单中...', mask: true });

    try {
      // 步骤1: 创建订单
      const orderId = await this.createOrder(pkg.package_id);
      if (!orderId) {
        wx.hideLoading();
        return;
      }

      wx.showLoading({ title: '调起支付中...', mask: true });

      // 步骤2: 发起支付
      const payParams = await this.requestPayment(orderId, openid);
      if (!payParams) {
        wx.hideLoading();
        return;
      }

      wx.hideLoading();

      // 步骤3: 调起微信支付
      await this.invokeWechatPay(payParams, orderId);

    } catch (err) {
      wx.hideLoading();
      console.error('支付流程错误:', err);
    }
  },

  // 创建订单
  createOrder(packageId) {
    return new Promise((resolve) => {
      const authHeader = getAuthHeader();
      wx.request({
        url: `${API_BASE_URL}/api/member/orders`,
        method: 'POST',
        header: {
          'content-type': 'application/json',
          Authorization: authHeader,
        },
        data: {
          package_id: packageId,
          payment_method: 'wechat',
        },
        success: (res) => {
          const payload = res && res.data ? res.data : {};
          const ok = res.statusCode >= 200 && res.statusCode < 300 && payload.code === 1 && payload.data;
          if (ok && payload.data.order_id) {
            console.log('订单创建成功:', payload.data.order_id);
            resolve(payload.data.order_id);
            return;
          }
          wx.showToast({ title: payload.message || '创建订单失败', icon: 'none' });
          resolve(null);
        },
        fail: () => {
          wx.showToast({ title: '网络异常，请稍后重试', icon: 'none' });
          resolve(null);
        },
      });
    });
  },

  // 请求支付参数
  requestPayment(orderId, openid) {
    return new Promise((resolve) => {
      const authHeader = getAuthHeader();

      console.log('=== PAY_APP_ID 值 ===', PAY_APP_ID);
      console.log('=== 支付请求参数 ===', {
        order_id: orderId,
        openid: openid,
        appid: PAY_APP_ID,
      });

      wx.request({
        url: `${API_BASE_URL}/api/payments/jsapi`,
        method: 'POST',
        header: {
          'content-type': 'application/json',
          Authorization: authHeader,
        },
        data: {
          order_id: orderId,
          openid: openid,
          appid: PAY_APP_ID,
        },
        success: (res) => {
          const payload = res && res.data ? res.data : {};
          const ok = res.statusCode >= 200 && res.statusCode < 300 && payload.code === 1 && payload.data;
          if (ok && payload.data.pay_params) {
            console.log('获取支付参数成功');
            resolve(payload.data.pay_params);
            return;
          }
          wx.showToast({ title: payload.message || '获取支付参数失败', icon: 'none' });
          resolve(null);
        },
        fail: () => {
          wx.showToast({ title: '网络异常，请稍后重试', icon: 'none' });
          resolve(null);
        },
      });
    });
  },

  // 调起微信支付
  invokeWechatPay(payParams, orderId) {
    return new Promise((resolve) => {
      wx.requestPayment({
        ...payParams,
        success: (res) => {
          console.log('微信支付成功:', res);
          wx.showToast({ title: '支付成功', icon: 'success' });

          // 延迟查询订单状态
          setTimeout(() => {
            this.checkOrderStatus(orderId);
          }, 2000);

          // 支付成功后跳转到"我的"页面
          setTimeout(() => {
            wx.switchTab({
              url: '/pages/mine/mine/mine',
            });
          }, 1500);

          resolve(true);
        },
        fail: (err) => {
          console.error('微信支付失败:', err);
          if (err.errMsg === 'requestPayment:fail cancel') {
            wx.showToast({ title: '已取消支付', icon: 'none' });
          } else {
            wx.showToast({ title: '支付失败，请重试', icon: 'none' });
          }
          resolve(false);
        },
      });
    });
  },

  // 查询订单状态
  checkOrderStatus(orderId) {
    const authHeader = getAuthHeader();
    wx.request({
      url: `${API_BASE_URL}/api/payments/${orderId}/status`,
      method: 'GET',
      header: {
        Authorization: authHeader,
      },
      success: (res) => {
        const payload = res && res.data ? res.data : {};
        const ok = res.statusCode >= 200 && res.statusCode < 300 && payload.code === 1 && payload.data;
        if (ok && payload.data.trade_state === 'SUCCESS') {
          console.log('订单支付状态: 已支付');
          // 刷新用户信息（请求 api/auth/me）
          this.refreshUserProfile();
          // 刷新套餐列表
          this.loadPackages();
          // 可选：跳转到订单页面
          // wx.navigateTo({ url: '/subpackage/pages/mine/vip-order/vip-order' });
        } else {
          console.log('订单支付状态:', payload.data.trade_state);
        }
      },
      fail: () => {
        console.error('查询订单状态失败');
      },
    });
  },

  // 刷新用户信息（请求 api/auth/me）
  refreshUserProfile() {
    const authHeader = getAuthHeader();
    if (!authHeader) {
      console.warn('未登录，无法刷新用户信息');
      this.loadUserInfo();
      return;
    }

    wx.request({
      url: `${API_BASE_URL}/api/auth/me`,
      method: 'GET',
      header: {
        Authorization: authHeader,
      },
      success: (res) => {
        const payload = res && res.data ? res.data : {};
        const ok = res.statusCode >= 200 && res.statusCode < 300 && payload.code === 1 && payload.data;
        if (ok) {
          console.log('刷新用户信息成功', payload.data);
          // 先更新本地存储的用户信息
          wx.setStorageSync('user_info', payload.data);
          // 直接使用返回的数据更新界面，不依赖 storage 的异步更新
          this.setData({
            currentMemberLabel: formatMemberLevel(payload.data.member_level),
          });
        } else {
          console.error('刷新用户信息失败:', payload.message);
          this.loadUserInfo();
        }
      },
      fail: (err) => {
        console.error('刷新用户信息请求失败:', err);
        // 请求失败时仍然使用本地缓存
        this.loadUserInfo();
      },
    });
  },
})
