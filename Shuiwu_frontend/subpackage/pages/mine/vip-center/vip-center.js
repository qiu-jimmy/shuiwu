// pages/mine/vip-center/vip-center.js
import { API_BASE_URL } from '../../../../utils/config';

const getDefaultDisplay = () => ({
  levelLabel: '--',
  expireLabel: '--',
  validLabel: '未开通',
  validTheme: 'default',
  userId: '--',
  packageName: '--',
  packageDesc: '--',
  packageStatusLabel: '--',
});

const formatMemberLevel = (level) => {
  const map = {
    free: '免费版',
    basic: '基础版',
    pro: '专业版',
    premium: '尊享版',
    vip: 'VIP会员',
    vip_month: 'VIP月卡',
    vip_quarter: 'VIP季卡',
    vip_year: 'VIP年卡',
  };
  return map[level] || level || '--';
};

const formatExpireAt = (value) => {
  if (!value) {
    return '--';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  const pad = (num) => (num < 10 ? `0${num}` : `${num}`);
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
};

const formatDateTime = (value) => {
  if (!value) {
    return '--';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  const pad = (num) => (num < 10 ? `0${num}` : `${num}`);
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
};

const formatPackageStatus = (status) => {
  const map = {
    normal: '正常',
    disabled: '停用',
    expired: '已过期',
  };
  return map[status] || status || '--';
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

const clampPercent = (value) => {
  const num = Number(value);
  if (!Number.isFinite(num)) {
    return 0;
  }
  return Math.max(0, Math.min(100, Math.round(num)));
};

const toSafeNumber = (value, fallback = 0) => {
  const num = Number(value);
  return Number.isFinite(num) ? num : fallback;
};

const formatUsageNumber = (value, decimals = 0) => {
  const num = toSafeNumber(value, 0);
  if (decimals <= 0) {
    return num.toFixed(0);
  }
  return num % 1 === 0 ? num.toFixed(0) : num.toFixed(decimals);
};

const isUnlimited = (maxValue) => maxValue === null || maxValue === undefined || Number(maxValue) < 0;

const buildUsageItem = ({ key, label, used, max, unit = '', decimals = 0, enabled = true }) => {
  const usedNum = toSafeNumber(used, 0);
  const maxNum = toSafeNumber(max, 0);
  const unlimited = isUnlimited(max);

  if (!enabled) {
    return {
      key,
      label,
      enabled: false,
      unlimited: false,
      usedLabel: `${formatUsageNumber(usedNum, decimals)}${unit}`,
      totalLabel: '未开通',
      remainLabel: '--',
      percent: 0,
      percentLabel: '未开通',
    };
  }

  const remainNum = unlimited ? null : Math.max(0, maxNum - usedNum);
  const percent = unlimited
    ? 0
    : maxNum > 0
      ? clampPercent((usedNum / maxNum) * 100)
      : 0;

  return {
    key,
    label,
    enabled: true,
    unlimited,
    usedLabel: `${formatUsageNumber(usedNum, decimals)}${unit}`,
    totalLabel: unlimited ? '不限' : `${formatUsageNumber(maxNum, decimals)}${unit}`,
    remainLabel: unlimited ? '不限' : `${formatUsageNumber(remainNum, decimals)}${unit}`,
    percent,
    percentLabel: unlimited ? '不限' : `${percent}%`,
  };
};

const buildUsageItems = (stats = {}) => {
  const maxDailyChats = stats.max_daily_chats;

  return [
    buildUsageItem({
      key: 'todayChats',
      label: '今日对话',
      used: stats.today_chats,
      max: maxDailyChats,
      unit: '次',
    }),
    buildUsageItem({
      key: 'invoicePenetration',
      label: '发票穿透',
      used: stats.invoice_penetration_used,
      max: stats.max_invoice_penetration,
      unit: '次',
      enabled: !!stats.enable_invoice_penetration,
    }),
    buildUsageItem({
      key: 'panorama',
      label: '全景报告',
      used: stats.panorama_used,
      max: stats.max_panorama,
      unit: '次',
      enabled: !!stats.enable_panorama,
    }),
    buildUsageItem({
      key: 'businessRisk',
      label: '经营风险',
      used: stats.business_risk_used,
      max: stats.max_business_risk,
      unit: '次',
      enabled: !!stats.enable_business_risk,
    }),
  ];
};

const buildFeatureItems = (stats = {}) => {
  const customConfig = stats.custom_config || {};

  return [
    {
      key: 'rag',
      label: 'RAG 检索',
      enabled: !!stats.enable_rag,
    },
    {
      key: 'webSearch',
      label: '联网搜索',
      enabled: !!stats.enable_web_search,
    },
    {
      key: 'mcpTools',
      label: 'MCP 工具',
      enabled: !!stats.enable_mcp_tools,
    },
    {
      key: 'invoicePenetration',
      label: '发票穿透',
      enabled: !!stats.enable_invoice_penetration,
    },
    {
      key: 'panorama',
      label: '全景报告',
      enabled: !!stats.enable_panorama,
    },
    {
      key: 'businessRisk',
      label: '经营风险',
      enabled: !!stats.enable_business_risk,
    },
    {
      key: 'contractReview',
      label: '合同审查',
      enabled: !!customConfig.enable_contract_review,
    },
  ];
};

const buildSummaryRows = (info = {}, stats = {}) => {
  const packageInfo = info.package_info || {};
  const source = {
    ...packageInfo,
    ...stats,
  };

  return [
    { label: '用户ID', value: info.user_id || source.user_id || '--' },
    { label: '会员等级', value: formatMemberLevel(info.member_package_name || source.member_package_name) },
    { label: '到期时间', value: formatDateTime(info.member_expire_at || source.member_expire_at) },
    { label: '套餐状态', value: formatPackageStatus(packageInfo.status) },
  ];
};

const normalizeMemberInfo = (data = {}) => {
  const packageInfo = data.package_info || {};
  const valid = data.is_member_valid;

  const validLabel = valid === true ? '有效' : valid === false ? '已过期' : '--';
  const validTheme = valid === true ? 'success' : valid === false ? 'warning' : 'default';

  return {
    memberInfo: {
      ...data,
      package_info: packageInfo,
      usage_stats: data.usage_stats || {},
    },
    display: {
      levelLabel: formatMemberLevel(data.member_level),
      expireLabel: formatExpireAt(data.member_expire_at),
      validLabel,
      validTheme,
      userId: data.user_id || '--',
      packageName: packageInfo.package_name || '--',
      packageDesc: packageInfo.description || '--',
      packageStatusLabel: formatPackageStatus(packageInfo.status),
    },
  };
};

Page({
  data: {
    loading: false,
    statsLoading: false,
    isLogin: true,

    memberInfo: null,
    memberStats: null,

    display: getDefaultDisplay(),
    summaryRows: [],
    usageItems: [],
    featureItems: [],

    statsError: '',
    errorMessage: '',
  },

  onLoad() {
    this.loadAll();
  },

  onShow() {
    this.loadAll();
  },

  onPullDownRefresh() {
    this.loadAll().finally(() => {
      wx.stopPullDownRefresh();
    });
  },

  onBuyTap() {
    wx.navigateTo({ url: '/subpackage/pages/mine/vip-buy/vip-buy' });
  },

  onOrderTap() {
    wx.navigateTo({ url: '/subpackage/pages/mine/vip-order/vip-order' });
  },

  onLoginTap() {
    wx.navigateTo({ url: '/pages/mine/login/login' });
  },

  onReloadTap() {
    this.loadAll();
  },

  loadAll() {
    const authHeader = getAuthHeader();
    if (!authHeader) {
      this.setData({
        isLogin: false,
        memberInfo: null,
        memberStats: null,
        display: getDefaultDisplay(),
        summaryRows: [],
        usageItems: [],
        featureItems: [],
        statsError: '',
        errorMessage: '请先登录',
      });
      return Promise.resolve();
    }

    this.setData({
      isLogin: true,
      errorMessage: '',
    });

    return Promise.allSettled([
      this.fetchMemberInfo(authHeader),
      this.fetchMemberStats(authHeader),
    ]).then((results) => {
      const infoResult = results[0];
      const statsResult = results[1];

      const infoData = infoResult.status === 'fulfilled' ? infoResult.value : null;
      const statsData = statsResult.status === 'fulfilled' ? statsResult.value : null;

      if (infoData || statsData) {
        this.mergeDisplayData(infoData, statsData);
      }
    });
  },

  mergeDisplayData(infoData = null, statsData = null) {
    const finalInfo = infoData || this.data.memberInfo || null;
    const finalStats = statsData || this.data.memberStats || null;

    const nextData = {};

    if (finalInfo) {
      const normalizedInfo = normalizeMemberInfo(finalInfo);
      nextData.memberInfo = normalizedInfo.memberInfo;
      nextData.display = {
        ...this.data.display,
        ...normalizedInfo.display,
      };
    }

    if (finalStats) {
      nextData.memberStats = finalStats;
      nextData.usageItems = buildUsageItems(finalStats);
      nextData.featureItems = buildFeatureItems(finalStats);
      nextData.statsError = '';
    }

    if (finalInfo || finalStats) {
      const infoSource = finalInfo || {};
      const statsSource = finalStats || {};
      nextData.summaryRows = buildSummaryRows(infoSource, statsSource);
    }

    this.setData(nextData);
  },

  fetchMemberInfo(authHeader) {
    if (this.data.loading) {
      return Promise.reject(new Error('MEMBER_INFO_LOADING'));
    }

    this.setData({ loading: true });

    return new Promise((resolve, reject) => {
      wx.request({
        url: `${API_BASE_URL}/api/member/info`,
        method: 'GET',
        header: {
          Authorization: authHeader,
        },
        success: (res) => {
          const payload = res && res.data ? res.data : {};
          const ok = res.statusCode >= 200 && res.statusCode < 300 && payload.code === 1 && payload.data;

          if (ok) {
            this.setData({
              errorMessage: '',
            });
            resolve(payload.data);
            return;
          }

          if (res.statusCode === 401 || res.statusCode === 403) {
            this.setData({
              isLogin: false,
              memberInfo: null,
              memberStats: null,
              display: getDefaultDisplay(),
              summaryRows: [],
              usageItems: [],
              featureItems: [],
              statsError: '',
              errorMessage: '登录已失效',
            });
            reject(new Error('UNAUTHORIZED'));
            return;
          }

          const message = payload.message || '获取会员信息失败';
          this.setData({ errorMessage: message });
          reject(new Error(message));
        },
        fail: () => {
          const message = '网络异常，请稍后重试';
          this.setData({ errorMessage: message });
          reject(new Error(message));
        },
        complete: () => {
          this.setData({ loading: false });
        },
      });
    });
  },

  fetchMemberStats(authHeader) {
    if (this.data.statsLoading) {
      return Promise.reject(new Error('MEMBER_STATS_LOADING'));
    }

    this.setData({ statsLoading: true });

    return new Promise((resolve, reject) => {
      wx.request({
        url: `${API_BASE_URL}/api/member/stats`,
        method: 'GET',
        header: {
          Authorization: authHeader,
        },
        success: (res) => {
          const payload = res && res.data ? res.data : {};
          const ok = res.statusCode >= 200 && res.statusCode < 300 && payload.code === 1 && payload.data;

          if (ok) {
            resolve(payload.data);
            return;
          }

          if (res.statusCode === 401 || res.statusCode === 403) {
            this.setData({
              isLogin: false,
              memberInfo: null,
              memberStats: null,
              display: getDefaultDisplay(),
              summaryRows: [],
              usageItems: [],
              featureItems: [],
              statsError: '',
              errorMessage: '登录已失效',
            });
            reject(new Error('UNAUTHORIZED'));
            return;
          }

          const message = payload.message || '获取会员统计失败';
          this.setData({
            usageItems: [],
            featureItems: [],
            statsError: message,
          });
          reject(new Error(message));
        },
        fail: () => {
          const message = '网络异常，请稍后重试';
          this.setData({
            usageItems: [],
            featureItems: [],
            statsError: message,
          });
          reject(new Error(message));
        },
        complete: () => {
          this.setData({ statsLoading: false });
        },
      });
    });
  },
});
