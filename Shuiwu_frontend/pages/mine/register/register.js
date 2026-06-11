/**
 * 注册页面
 *
 * 功能说明：
 * - 支持用户手机号注册
 * - 处理分销邀请码自动绑定
 *
 * 注意：当前页面已关闭注册功能，仅保留代码以备后续启用
 *
 * 分销绑定逻辑：
 * 1. 页面加载时检查是否有待绑定的邀请码（来自扫码）
 * 2. 邀请码自动填充到表单中
 * 3. 注册时将邀请码传递给后端建立分销关系
 */

import { API_BASE_URL } from '../../../utils/config';

Page({
  data: {
    form: {
      phone: '',
      password: '',
      confirmPassword: '',
      nickname: '',
      referral_code: '', // 邀请码字段
    },
    loading: false,
    // 邀请码是否自动填充（用于UI显示）
    isAutoInviteCode: false,
  },

  /**
   * 页面加载
   * 检查是否有待绑定的分销邀请码
   */
  onLoad(options) {
    const app = getApp();
    let inviteCode = '';

    // 优先使用全局邀请码（扫码进入）
    if (app.globalData.pendingInviteCode) {
      inviteCode = app.globalData.pendingInviteCode;
      console.log('[注册] 检测到待绑定邀请码(global):', inviteCode);
    }

    // 其次使用URL参数邀请码（直接从链接带参数进入）
    if (options.invite_code) {
      inviteCode = options.invite_code;
      app.globalData.pendingInviteCode = options.invite_code;
      console.log('[注册] 检测到待绑定邀请码(url):', inviteCode);
    }

    // 自动填充邀请码
    if (inviteCode) {
      this.setData({
        'form.referral_code': inviteCode,
        isAutoInviteCode: true
      });
    }
  },

  onInputChange(event) {
    const field = event.currentTarget.dataset.field;
    const value = event.detail && event.detail.value !== undefined ? event.detail.value : '';
    if (!field) {
      return;
    }
    this.setData({ [`form.${field}`]: value });
  },

  /**
   * 提交注册
   */
  onSubmit() {
    if (this.data.loading) {
      return;
    }

    const phone = String(this.data.form.phone || '').trim();
    const password = String(this.data.form.password || '').trim();
    const confirmPassword = String(this.data.form.confirmPassword || '').trim();
    const nickname = String(this.data.form.nickname || '').trim();
    const referralCode = String(this.data.form.referral_code || '').trim();

    // 表单验证
    if (!/^1\d{10}$/.test(phone)) {
      wx.showToast({ title: '请输入正确手机号', icon: 'none' });
      return;
    }
    if (!password) {
      wx.showToast({ title: '请输入登录密码', icon: 'none' });
      return;
    }
    if (!confirmPassword) {
      wx.showToast({ title: '请再次输入密码', icon: 'none' });
      return;
    }
    if (password !== confirmPassword) {
      wx.showToast({ title: '两次输入密码不一致', icon: 'none' });
      return;
    }
    if (!nickname) {
      wx.showToast({ title: '请输入昵称', icon: 'none' });
      return;
    }

    this.setData({ loading: true });

    // 构建请求数据
    const requestData = {
      phone,
      password,
      nickname,
      sms_code: 'String',
    };

    // 如果有邀请码，传递给后端
    if (referralCode) {
      requestData.referral_code = referralCode;
      console.log('[注册] 注册携带邀请码:', referralCode);
    }

    wx.request({
      url: `${API_BASE_URL}/api/auth/register`,
      method: 'POST',
      header: {
        'content-type': 'application/json',
      },
      data: requestData,
      success: (res) => {
        const payload = res && res.data ? res.data : {};
        const ok = res.statusCode >= 200 && res.statusCode < 300 && payload.code === 1 && payload.data && payload.data.success;
        if (ok) {
          const data = payload.data || {};

          // 存储token和用户信息
          if (data.access_token) {
            wx.setStorageSync('access_token', data.access_token);
            wx.setStorageSync('token_type', data.token_type || 'bearer');
            wx.setStorageSync('expires_in', data.expires_in || 0);
          }
          if (data.user_info) {
            wx.setStorageSync('user_info', data.user_info);
          }

          // 清除已使用的邀请码
          const app = getApp();
          if (app.globalData.pendingInviteCode) {
            app.globalData.pendingInviteCode = null;
            console.log('[注册] 邀请码已使用，已清除');
          }

          wx.showToast({ title: payload.message || '注册成功', icon: 'success' });
          setTimeout(() => {
            wx.switchTab({ url: '/pages/mine/mine/mine' });
          }, 800);
          return;
        }
        wx.showToast({ title: payload.message || '注册失败', icon: 'none' });
      },
      fail: () => {
        wx.showToast({ title: '网络异常，请稍后重试', icon: 'none' });
      },
      complete: () => {
        this.setData({ loading: false });
      },
    });
  },

  /**
   * 返回登录页面
   */
  goToLogin() {
    wx.navigateBack();
  },
});
