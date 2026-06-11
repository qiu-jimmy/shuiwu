/**
 * TaxConsultantList.js — 税务师列表页面逻辑
 *
 * 功能：
 *   - 展示所有已认证的税务师列表
 *   - 支持分页加载（下拉刷新、上拉加载更多）
 *   - 根据用户身份显示"申请入驻"按钮或"已是税务师"标识
 *   - 点击申请入驻按钮跳转到申请页面
 *
 * API接口：
 *   - GET /api/tax_accountant/list - 获取税务师列表（公开接口）
 *   - GET /api/tax_accountant/my-application - 获取我的申请状态（需登录）
 */
import { API_BASE_URL } from '../../../../utils/config';

const getAuthContext = () => {
  const userInfo = wx.getStorageSync('user_info');
  const userId = userInfo && userInfo.user_id ? userInfo.user_id : '';
  const token = wx.getStorageSync('access_token');
  if (!userId || !token) {
    return null;
  }
  const tokenType = String(wx.getStorageSync('token_type') || 'bearer');
  const normalizedType = tokenType.toLowerCase() === 'bearer' ? 'Bearer' : tokenType;
  return { userId, token, tokenType: normalizedType };
};

// 隐藏手机号中间4位
const maskPhone = (phone) => {
  if (!phone || phone.length < 11) return phone;
  return phone.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2');
};

Page({
  data: {
    accountants: [],        // 税务师列表
    page: 1,                // 当前页码
    pageSize: 20,           // 每页数量
    total: 0,               // 总数
    hasMore: true,          // 是否还有更多
    loading: false,         // 加载状态
    isTaxAccountant: false, // 当前用户是否是税务师
    applicationStatus: null, // 申请状态 (null/pending/approved/rejected)
    showPhoneMap: {},       // 控制每个税务师手机号是否显示完整
  },

  onLoad() {
    this.loadAccountantList(true);
    this.checkUserStatus();
  },

  onShow() {
    // 页面显示时刷新用户状态（可能在其他页面申请后返回）
    this.checkUserStatus();
  },

  // 下拉刷新
  onPullDownRefresh() {
    this.loadAccountantList(true).finally(() => {
      wx.stopPullDownRefresh();
    });
  },

  // 上拉加载更多
  onReachBottom() {
    if (this.data.hasMore && !this.data.loading) {
      this.loadAccountantList(false);
    }
  },

  /**
   * 加载税务师列表
   * @param {boolean} reset - 是否重置列表
   */
  loadAccountantList(reset = false) {
    if (this.data.loading) {
      return Promise.resolve();
    }

    if (!reset && (!this.data.hasMore || this.data.loading)) {
      return Promise.resolve();
    }

    const nextPage = reset ? 1 : this.data.page + 1;
    this.setData({ loading: true });

    if (reset) {
      wx.showLoading({ title: '加载中...' });
    }

    return new Promise((resolve, reject) => {
      wx.request({
        url: `${API_BASE_URL}/api/tax_accountant/list`,
        method: 'GET',
        data: {
          page: nextPage,
          page_size: this.data.pageSize,
          status: 'active', // 只显示正常状态的税务师
        },
        success: (res) => {
          wx.hideLoading();
          const payload = res && res.data ? res.data : {};
          
          if (res.statusCode >= 200 && res.statusCode < 300 && payload.code === 1) {
            const listData = payload.data || {};
            const sourceAccountants = Array.isArray(listData.accountants) ? listData.accountants : [];
            
            // 处理数据，添加显示字段
            const processedAccountants = sourceAccountants.map(item => {
              // 处理专长领域：确保是数组格式
              let specialtyArray = [];
              if (Array.isArray(item.specialty_area)) {
                specialtyArray = item.specialty_area.filter(tag => tag && tag.trim());
              } else if (item.specialty_area) {
                // 如果是字符串，尝试按常见分隔符分割
                const specialtyStr = String(item.specialty_area);
                specialtyArray = specialtyStr.split(/[、,，;；]/).map(tag => tag.trim()).filter(tag => tag);
              }
              
              return {
                ...item,
                maskedPhone: maskPhone(item.phone || ''),
                specialty_area: specialtyArray, // 确保是数组，用于标签展示
              };
            });

            const total = Number(listData.total || 0);
            const page = Number(listData.page || nextPage);
            const pageSize = Number(listData.page_size || this.data.pageSize);
            const hasMore = processedAccountants.length + (reset ? 0 : this.data.accountants.length) < total;

            this.setData({
              accountants: reset ? processedAccountants : this.data.accountants.concat(processedAccountants),
              total,
              page,
              pageSize,
              hasMore,
              loading: false,
              showPhoneMap: reset ? {} : this.data.showPhoneMap, // 重置时清空手机号显示状态
            });

            resolve();
          } else {
            this.setData({ loading: false });
            wx.showToast({
              title: payload.message || '获取列表失败',
              icon: 'none',
            });
            reject(new Error(payload.message || '获取列表失败'));
          }
        },
        fail: (err) => {
          wx.hideLoading();
          this.setData({ loading: false });
          wx.showToast({
            title: '网络错误，请稍后重试',
            icon: 'none',
          });
          reject(err);
        },
      });
    });
  },

  /**
   * 检查用户状态（是否是税务师、申请状态）
   */
  checkUserStatus() {
    const auth = getAuthContext();
    if (!auth) {
      // 未登录，默认不是税务师
      this.setData({
        isTaxAccountant: false,
        applicationStatus: null,
      });
      return;
    }

    // 先从本地存储快速判断
    const userInfo = wx.getStorageSync('user_info') || {};
    const isTaxAccountant = userInfo.is_tax_accountant === true;

    // 调用API获取最新状态
    wx.request({
      url: `${API_BASE_URL}/api/tax_accountant/my-application`,
      method: 'GET',
      header: {
        'Authorization': `${auth.tokenType} ${auth.token}`,
      },
      success: (res) => {
        const payload = res && res.data ? res.data : {};
        
        if (res.statusCode >= 200 && res.statusCode < 300 && payload.code === 1) {
          const data = payload.data || {};
          const status = data.status || null;
          
          // 如果申请已通过，则用户是税务师
          const isTaxAccountantFromAPI = status === 'approved' || isTaxAccountant;
          
          this.setData({
            isTaxAccountant: isTaxAccountantFromAPI,
            applicationStatus: status,
          });
        } else {
          // API调用失败，使用本地存储的值
          this.setData({
            isTaxAccountant: isTaxAccountant,
            applicationStatus: null,
          });
        }
      },
      fail: () => {
        // API调用失败，使用本地存储的值
        this.setData({
          isTaxAccountant: isTaxAccountant,
          applicationStatus: null,
        });
      },
    });
  },

  /**
   * 点击申请入驻按钮
   */
  onApplyTap() {
    const auth = getAuthContext();
    if (!auth) {
      wx.showModal({
        title: '请先登录',
        content: '申请入驻需要登录，是否前往登录？',
        confirmText: '去登录',
        cancelText: '取消',
        success: (res) => {
          if (res.confirm) {
            wx.navigateTo({
              url: '/pages/mine/login/login',
              fail: () => {
                wx.reLaunch({ url: '/pages/mine/login/login' });
              },
            });
          }
        },
      });
      return;
    }

    // 检查申请状态
    if (this.data.applicationStatus === 'pending') {
      wx.showToast({
        title: '您的申请正在审核中，请耐心等待',
        icon: 'none',
        duration: 2500,
      });
      return;
    }

    if (this.data.isTaxAccountant) {
      wx.showToast({
        title: '您已经是税务师',
        icon: 'none',
      });
      return;
    }

    // 跳转到申请页面
    wx.navigateTo({
      url: '/subpackage/pages/index/TaxConsultantInput/TaxConsultantInput',
      fail: (err) => {
        console.error('跳转失败:', err);
        wx.redirectTo({
          url: '/subpackage/pages/index/TaxConsultantInput/TaxConsultantInput',
        });
      },
    });
  },

  /**
   * 点击查看/隐藏联系方式
   */
  onTogglePhone(e) {
    const accountantId = e.currentTarget.dataset.id;
    if (!accountantId) return;

    const showPhoneMap = { ...this.data.showPhoneMap };
    showPhoneMap[accountantId] = !showPhoneMap[accountantId];
    this.setData({ showPhoneMap });
  },


  /**
   * 点击复制电话
   */
  onCopyPhone(e) {
    const phone = e.currentTarget.dataset.phone;
    if (!phone) {
      wx.showToast({ title: '电话号码无效', icon: 'none' });
      return;
    }

    wx.setClipboardData({
      data: phone,
      success: () => {
        wx.showToast({ title: '已复制到剪贴板', icon: 'success' });
      },
      fail: () => {
        wx.showToast({ title: '复制失败', icon: 'none' });
      },
    });
  },
});
