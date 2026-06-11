// pages/mine/mcp-manager/mcp-manager.js
import { API_BASE_URL } from '../../../../utils/config';

const getAuthHeader = () => {
  const token = wx.getStorageSync('access_token');
  if (!token) {
    return '';
  }
  const tokenType = String(wx.getStorageSync('token_type') || 'bearer');
  const normalizedType = tokenType.toLowerCase() === 'bearer' ? 'Bearer' : tokenType;
  return `${normalizedType} ${token}`;
};

Page({
  data: {
    isLogin: false,
    loading: true,
    toolsLoading: false,
    mcpEnabled: false,
    toolsList: [],
    stats: {
      todayCalls: 0,
      monthCalls: 0,
      remainingCalls: '不限'
    },
    showUpgradeDialog: false
  },

  onLoad() {
    this.checkLoginStatus();
  },

  onShow() {
    if (this.data.isLogin) {
      this.loadMCPStatus();
      this.loadToolsList();
      this.loadUsageStats();
    }
  },

  checkLoginStatus() {
    const token = wx.getStorageSync('access_token');
    const isLogin = !!token;
    this.setData({ isLogin, loading: false });
    
    if (isLogin) {
      this.loadMCPStatus();
      this.loadToolsList();
      this.loadUsageStats();
    }
  },

  loadMCPStatus() {
    const authHeader = getAuthHeader();
    if (!authHeader) {
      this.setData({ mcpEnabled: false });
      return;
    }

    wx.request({
      url: `${API_BASE_URL}/api/member/stats`,
      method: 'GET',
      header: {
        Authorization: authHeader
      },
      success: (res) => {
        const payload = res && res.data ? res.data : {};
        const ok = res.statusCode >= 200 && res.statusCode < 300 && payload.code === 1;
        
        if (ok && payload.data) {
          const stats = payload.data;
          const mcpEnabled = !!stats.enable_mcp_tools;
          this.setData({ mcpEnabled });
        }
      },
      fail: (err) => {
        console.error('获取MCP状态失败：', err);
      }
    });
  },

  loadToolsList() {
    const authHeader = getAuthHeader();
    if (!authHeader) {
      return;
    }

    this.setData({ toolsLoading: true });

    wx.request({
      url: `${API_BASE_URL}/api/mcp/tools`,
      method: 'GET',
      header: {
        Authorization: authHeader
      },
      success: (res) => {
        const payload = res && res.data ? res.data : {};
        const ok = res.statusCode >= 200 && res.statusCode < 300;
        
        if (ok && payload.data) {
          const toolsList = Array.isArray(payload.data) ? payload.data : 
                           (payload.data.tools || payload.data.list || []);
          this.setData({ toolsList });
        }
      },
      fail: (err) => {
        console.error('获取工具列表失败：', err);
      },
      complete: () => {
        this.setData({ toolsLoading: false });
      }
    });
  },

  loadUsageStats() {
    const authHeader = getAuthHeader();
    if (!authHeader) {
      return;
    }

    wx.request({
      url: `${API_BASE_URL}/api/mcp/stats`,
      method: 'GET',
      header: {
        Authorization: authHeader
      },
      success: (res) => {
        const payload = res && res.data ? res.data : {};
        const ok = res.statusCode >= 200 && res.statusCode < 300;
        
        if (ok && payload.data) {
          this.setData({
            stats: {
              todayCalls: payload.data.today_calls || 0,
              monthCalls: payload.data.month_calls || 0,
              remainingCalls: payload.data.remaining_calls || '不限'
            }
          });
        }
      },
      fail: (err) => {
        console.error('获取使用统计失败：', err);
      }
    });
  },

  onToolSwitch(e) {
    const { name, index } = e.currentTarget.dataset;
    const { value } = e.detail;
    const toolsList = this.data.toolsList;
    
    if (toolsList[index]) {
      toolsList[index].enabled = value;
      this.setData({ toolsList });

      this.updateToolStatus(name, value);
    }
  },

  updateToolStatus(toolName, enabled) {
    const authHeader = getAuthHeader();
    if (!authHeader) {
      return;
    }

    wx.request({
      url: `${API_BASE_URL}/api/mcp/tools/${toolName}/toggle`,
      method: 'POST',
      header: {
        Authorization: authHeader,
        'Content-Type': 'application/json'
      },
      data: {
        enabled: enabled
      },
      success: (res) => {
        const payload = res && res.data ? res.data : {};
        const ok = res.statusCode >= 200 && res.statusCode < 300;
        
        if (ok) {
          wx.showToast({
            title: enabled ? '已启用' : '已禁用',
            icon: 'success'
          });
        } else {
          wx.showToast({
            title: payload.message || '操作失败',
            icon: 'none'
          });
          this.loadToolsList();
        }
      },
      fail: (err) => {
        console.error('更新工具状态失败：', err);
        wx.showToast({
          title: '网络错误',
          icon: 'none'
        });
        this.loadToolsList();
      }
    });
  },

  onLoginTap() {
    wx.navigateTo({
      url: '/pages/mine/login/login'
    });
  },

  onUpgradeTap() {
    this.setData({ showUpgradeDialog: true });
  },

  onConfirmUpgrade() {
    this.setData({ showUpgradeDialog: false });
    wx.navigateTo({
      url: '/subpackage/pages/mine/vip-buy/vip-buy'
    });
  },

  onCancelUpgrade() {
    this.setData({ showUpgradeDialog: false });
  },

  onPullDownRefresh() {
    if (this.data.isLogin) {
      this.loadMCPStatus();
      this.loadToolsList();
      this.loadUsageStats();
    }
    wx.stopPullDownRefresh();
  }
});
