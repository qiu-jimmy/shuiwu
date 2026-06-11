// pages/mine/mine/mine.js
import { API_BASE_URL, OSS_URL } from '../../../utils/config';

const getDefaultUser = () => ({
  name: "游客用户",
  status: "未登录",
  plan: "体验版",
  id: "TAX-20240108",
  desc: "登录后可同步订阅、会话与企业认证信息",
});

const getDefaultStats = () => ([
  { key: 'package', label: '套餐', value: '免费版' },
  { key: 'commission', label: '合作奖励', value: '0.00' },
  { key: 'points', label: '积分', value: '0.00' },
]);

const packageNameMap = {};
const POINTS_BALANCE_STORAGE_KEY = 'mine_points_balance';

const updatePackageNameMap = (packages = []) => {
  packages.forEach((pkg) => {
    if (!pkg || !pkg.package_id) {
      return;
    }
    packageNameMap[pkg.package_id] = pkg.name || pkg.package_id;
  });
};

const formatMemberLevel = (level) => {
  return packageNameMap[level] || level || '体验版';
};

const formatStatus = (status) => {
  const map = {
    normal: '正常',
    disabled: '已停用',
    locked: '已锁定',
  };
  return map[status] || status || '正常';
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

const normalizeUserInfo = (userInfo = {}) => ({
  ...userInfo,
  is_distributor: !!userInfo.is_distributor,
  distributor_code: userInfo.distributor_code ?? null,
  is_tax_accountant: !!userInfo.is_tax_accountant,
});

const formatDistributorStatus = (value) => (value ? '合作已开通' : '未开通合作');

const formatCommission = (value) => {
  const amount = Number(value);
  if (!Number.isFinite(amount)) {
    return '0.00';
  }
  return amount.toFixed(2);
};

const getCachedPointsBalance = () => {
  const cached = wx.getStorageSync(POINTS_BALANCE_STORAGE_KEY);
  if (cached === '' || cached === null || cached === undefined) {
    return '';
  }
  return formatCommission(cached);
};

const setCachedPointsBalance = (value) => {
  const normalized = formatCommission(value);
  wx.setStorageSync(POINTS_BALANCE_STORAGE_KEY, normalized);
  return normalized;
};

const formatExpireAt = (value) => {
  if (!value) {
    return '未设置';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  const pad = (num) => (num < 10 ? `0${num}` : `${num}`);
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
};

Page({
  data: {
    // OSS图片地址前缀
    ossUrl: OSS_URL,
    islogin: false,
    user: getDefaultUser(),
    loginBenefits: [
      {
        title: "个人信息管理",
        description: "完善头像、手机号、隐私与安全设置",
        icon: "user-checked",
      },
      {
        title: "会员与订阅中心",
        description: "查看套餐权益、续费与订阅记录",
        icon: "user-vip",
      },
      {
        title: "问题反馈",
        description: "在线反馈入口，问题处理进度可追踪",
        icon: "sticky-note",
      },
      {
        title: "合作服务",
        description: "生成邀请码，查看邀请与奖励结算",
        icon: "share",
      },
      {
        title: "税务师合作",
        description: "查看税务师合作信息",
        icon: "cooperate",
      },
    ],
    stats: getDefaultStats(),
    quickActions: [
      { text: "个人信息", icon: "user", url: "/subpackage/pages/mine/userInfo/userInfo" },
      { text: "会员中心", icon: "user-vip", url: "/subpackage/pages/mine/vip-center/vip-center" },
      { text: "积分商城", icon: "cart", url: "/subpackage/pages/mine/points-mall/points-mall" },
      { text: "知识库", icon: "file", url: "/subpackage/pages/file/KnowledgeBase/KnowledgeBase" },
      { text: "MCP工具", icon: "tools", url: "/subpackage/pages/mine/mcp-manager/mcp-manager" },
      { text: "合作中心", icon: "gift", url: "/subpackage/pages/mine/distribute/distribute" },
      { text: "报税申报查询", icon: "wealth", url: "/subpackage/pages/mine/tax-query/tax-query" },
      { text: "工商申报查询", icon: "institution", url: "/subpackage/pages/mine/business-query/business-query" },
      { text: "税务师合作", icon: "cooperate", url: "/subpackage/pages/mine/tax-cooperate/tax-cooperate" },
    ],
    groups: [
      {
        title: "账号与安全",
        items: [
          {
            title: "个人信息管理",
            icon: "user",
            description: "在此进行昵称、头像修改操作",
            url: "/subpackage/pages/mine/userInfo/userInfo",
          },
          {
            title: "密码修改",
            icon: "key",
            description: "在此进行密码修改操作",
            url: "/subpackage/pages/mine/password/password",
          },
        ],
      },
      {
        title: "会员与订阅",
        items: [
          {
            title: "会员中心",
            icon: "user-vip",
            description: "权益展示、会员等级与使用记录",
            url: "/subpackage/pages/mine/vip-center/vip-center",
          },
          {
            title: "会员购买",
            icon: "ticket",
            description: "月卡/季卡/年卡订阅",
            url: "/subpackage/pages/mine/vip-buy/vip-buy",
          },
          {
            title: "会员订单",
            icon: "cart",
            description: "查看会员订单信息",
            url: "/subpackage/pages/mine/vip-order/vip-order",
          },
        ],
      },
      {
        title: "问题与反馈",
        items: [
          {
            title: "问题反馈",
            icon: "sticky-note",
            description: "问题提交入口、问题反馈与处理进度",
            url: "/subpackage/pages/mine/question/question",
          }
        ],
      },
      {
        title: "服务与合作",
        items: [
          {
            title: "邀请合作",
            icon: "share",
            description: "邀请好友使用，查看邀请统计与奖励记录",
            url: "/subpackage/pages/mine/distribute/distribute",
          },
        ],
      },
    ],
  },
  onLoad() {
    this.loadPackages();
  },
  onShow() {
    this.hydratePointsFromStorage();
    this.loadUserProfile();
    this.loadPointsBalance();
  },
  onLoginTap() {
    wx.navigateTo({
      url: "/pages/mine/login/login",
    });
  },
  onLogoutTap() {
    wx.showModal({
      title: '确认退出登录',
      content: '退出后需要重新登录才能继续使用。',
      confirmText: '退出登录',
      success: (res) => {
        if (res.confirm) {
          this.clearLoginState();
          wx.showToast({ title: '已退出登录', icon: 'success' });
        }
      },
    });
  },
  onQuickActionClick(event) {
    const item = event.currentTarget.dataset.item || event.detail || {};
    this.navigateToItem(item);
  },
  onGroupItemClick(event) {
    const entry = event.currentTarget.dataset.entry || event.detail || {};
    this.navigateToItem(entry);
  },
  hydratePointsFromStorage() {
    const cachedPoints = getCachedPointsBalance();
    if (!cachedPoints) {
      return;
    }
    this.updatePointsStat(cachedPoints);
  },
  loadPackages() {
    const authHeader = getAuthHeader();
    if (!authHeader) {
      return;
    }
    wx.request({
      url: `${API_BASE_URL}/api/member/packages?status=active`,
      method: 'GET',
      header: {
        Authorization: authHeader,
      },
      success: (res) => {
        const payload = res && res.data ? res.data : {};
        const ok = res.statusCode >= 200 && res.statusCode < 300 && payload.code === 1 && payload.data;
        if (!ok) {
          return;
        }
        const packages = (payload.data.packages || [])
          .filter((item) => item.status === 'active');
        updatePackageNameMap(packages);

        const cachedUser = wx.getStorageSync('user_info');
        if (cachedUser) {
          const normalized = normalizeUserInfo(cachedUser);
          wx.setStorageSync('user_info', normalized);
          this.applyUserInfo(normalized);
        }
      },
    });
  },
  loadPointsBalance() {
    const authHeader = getAuthHeader();
    if (!authHeader) {
      this.updatePointsStat('0.00');
      return;
    }
    wx.request({
      url: `${API_BASE_URL}/api/user/points/balance`,
      method: 'GET',
      header: {
        Authorization: authHeader,
      },
      timeout: 10000,
      success: (res) => {
        const payload = res && res.data ? res.data : {};
        const ok = res.statusCode >= 200 && res.statusCode < 300;
        if (!ok) {
          return;
        }
        const balance = payload.points_balance ?? payload.pointsBalance;
        const normalizedPoints = setCachedPointsBalance(balance);
        this.updatePointsStat(normalizedPoints);
      },
      fail: (err) => {
        console.error('获取积分余额失败：', err);
      },
    });
  },
  loadUserProfile() {
    const token = wx.getStorageSync('access_token');
    if (!token) {
      this.resetUserState();
      return;
    }

    const cachedUser = wx.getStorageSync('user_info');
    if (cachedUser) {
      const normalized = normalizeUserInfo(cachedUser);
      wx.setStorageSync('user_info', normalized);
      this.applyUserInfo(normalized);
    }

    const tokenType = String(wx.getStorageSync('token_type') || 'bearer');
    const normalizedType = tokenType.toLowerCase() === 'bearer' ? 'Bearer' : tokenType;

    wx.request({
      url: `${API_BASE_URL}/api/auth/me`,
      method: 'GET',
      header: {
        Authorization: `${normalizedType} ${token}`,
      },
      timeout: 10000, // 设置超时时间为10秒
      success: (res) => {
        const payload = res && res.data ? res.data : {};
        const ok = res.statusCode >= 200 && res.statusCode < 300 && payload.code === 1 && payload.data;
        if (ok) {
          const normalized = normalizeUserInfo(payload.data);
          wx.setStorageSync('user_info', normalized);
          this.applyUserInfo(normalized);
          return;
        }
        if (res.statusCode === 401 || res.statusCode === 403) {
          this.clearLoginState();
        }
      },
      fail: (err) => {
        // 处理网络错误（连接超时、网络不可达等）
        console.error('获取用户信息失败：', err);
        // 如果已有缓存用户信息，继续使用缓存，不重置登录状态
        // 如果没有缓存，说明可能是首次加载，静默失败即可
        // 这样可以避免网络问题导致用户被强制退出登录
      },
    });
  },
  clearLoginState() {
    // 清空所有 storage 缓存
    try {
      wx.clearStorageSync();
    } catch (e) {
      console.error('清空缓存失败：', e);
      // 如果清空失败，尝试逐个删除关键项
      wx.removeStorageSync('access_token');
      wx.removeStorageSync('token_type');
      wx.removeStorageSync('expires_in');
      wx.removeStorageSync('user_info');
      wx.removeStorageSync('user_id');
      wx.removeStorageSync('fileList');
      wx.removeStorageSync('myKnowledgeList');
      wx.removeStorageSync('categoryList');
    }
    this.resetUserState();
  },
  resetUserState() {
    wx.removeStorageSync(POINTS_BALANCE_STORAGE_KEY);
    this.setData({
      islogin: false,
      user: getDefaultUser(),
      stats: getDefaultStats(),
    });
  },
  updatePointsStat(pointsValue) {
    const nextValue = pointsValue ?? '0.00';
    const currentStats = Array.isArray(this.data.stats) ? this.data.stats : getDefaultStats();
    let hit = false;
    const nextStats = currentStats.map((item) => {
      if (item.key === 'points' || item.label === '积分') {
        hit = true;
        return { ...item, key: 'points', value: nextValue };
      }
      return item;
    });
    if (!hit) {
      nextStats.push({ key: 'points', label: '积分', value: nextValue });
    }
    this.setData({
      stats: nextStats,
    });
  },
  applyUserInfo(userInfo) {
    // 生成用户描述信息
    let desc = '登录后可同步订阅、会话与企业认证信息';
    if (userInfo.phone) {
      desc = `手机号 ${userInfo.phone}`;
    } else if (userInfo.wx_openid) {
      desc = `微信用户`;
    }

    const profile = {
      name: userInfo.nickname || userInfo.phone || '已登录用户',
      status: formatStatus(userInfo.status),
      plan: formatMemberLevel(userInfo.member_package_name),
      id: userInfo.user_id || '',
      desc: desc,
      avatar_url: userInfo.avatar_url || '',
      isVip: userInfo.member_level !== 'free',
      isTaxAccountant: !!userInfo.is_tax_accountant,
    };
    const level = String(userInfo.member_level || '').toLowerCase();
    const isVip = level !== 'free';
    const planValue = formatMemberLevel(userInfo.member_package_name) || '免费版';
    const planLabel = isVip ? formatExpireAt(userInfo.member_expire_at) : '套餐';
    const cachedPoints = getCachedPointsBalance();
    const pointsFromProfile = formatCommission(userInfo.total_points ?? userInfo.points);
    const pointsValue = cachedPoints || pointsFromProfile;
    if (!cachedPoints) {
      setCachedPointsBalance(pointsFromProfile);
    }
    const stats = [
      { key: 'package', label: planLabel, value: planValue },
      { key: 'commission', label: '合作奖励', value: formatCommission(userInfo.total_commission) },
      { key: 'points', label: '积分', value: pointsValue },
    ];
    this.setData({
      islogin: true,
      user: profile,
      stats,
    });
  },
  onStatTap(event) {
    const key = event.currentTarget.dataset.key;
    if (key === 'points') {
      wx.navigateTo({ url: '/subpackage/pages/mine/point/point' });
    }
  },
  navigateToItem(item) {
    if (item && item.url) {
      wx.navigateTo({ url: item.url });
      return;
    }
  },
  onPrivacyTap() {
    wx.navigateTo({ url: '/pages/mine/privacy/privacy' });
  },
  onAgreementTap() {
    wx.navigateTo({ url: '/pages/mine/agreement/agreement' });
  },
});
