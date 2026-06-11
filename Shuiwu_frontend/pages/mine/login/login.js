/**
 * 登录页面
 *
 * 功能说明：
 * - 支持账号密码登录
 * - 支持微信快捷登录
 * - 处理分销邀请码自动绑定
 *
 * 分销绑定逻辑：
 * 1. 页面加载时检查是否有待绑定的邀请码（来自扫码）
 * 2. 微信登录成功后自动传递邀请码给后端
 * 3. 账号密码登录成功后检查是否需要绑定邀请码
 */

import { API_BASE_URL } from '../../../utils/config';

Page({
  data: {
    form: {
      username: '',
      password: '',
    },
    loading: false,
    wxLoading: false,
    is_show: false,
    // 待绑定的邀请码（用于UI显示）
    pendingInviteCode: '',
    agreementChecked: false,
  },

  /**
   * 页面加载
   * 检查是否有待绑定的分销邀请码
   */
  onLoad(options) {
    const app = getApp();
    if (app.globalData.pendingInviteCode) {
      this.setData({ pendingInviteCode: app.globalData.pendingInviteCode });
      console.log('[登录] 检测到待绑定邀请码:', app.globalData.pendingInviteCode);
    }

    // 处理URL参数中的邀请码（直接从链接带参数进入登录页）
    if (options.invite_code) {
      this.setData({ pendingInviteCode: options.invite_code });
      app.globalData.pendingInviteCode = options.invite_code;
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
   * 微信快捷登录
   * 登录成功后自动携带邀请码（如果有）建立分销关系
   */
  onWechatLogin() {
    if (!this.data.agreementChecked) {
      wx.showToast({
        title: '请先阅读并同意《用户协议》和《隐私政策》',
        icon: 'none'
      });
      return;
    }

    if (this.data.wxLoading) {
      return;
    }

    this.setData({ wxLoading: true });

    const app = getApp();
    const pendingInviteCode = app.globalData.pendingInviteCode;

    // 获取微信登录code
    wx.login({
      success: (res) => {
        if (res.code) {
          // 构建请求数据
          const requestData = {
            code: res.code,
          };

          // 如果有待绑定的邀请码，传递给后端
          if (pendingInviteCode) {
            requestData.referral_code = pendingInviteCode;
            console.log('[登录] 微信登录携带邀请码:', pendingInviteCode);
          }

          // 发送code到后端换取token
          wx.request({
            url: `${API_BASE_URL}/api/auth/wechat-login`,
            method: 'POST',
            header: {
              'content-type': 'application/json',
            },
            data: requestData,
            success: (loginRes) => {
              const payload = loginRes && loginRes.data ? loginRes.data : {};
              const ok = loginRes.statusCode >= 200 && loginRes.statusCode < 300 && payload.data;
              if (ok && payload.data.access_token) {
                const data = payload.data;

                // 存储token和用户信息
                wx.setStorageSync('access_token', data.access_token);
                if (data.token_type) {
                  wx.setStorageSync('token_type', data.token_type);
                }
                if (data.expires_in) {
                  wx.setStorageSync('expires_in', data.expires_in);
                }
                if (data.user_info) {
                  wx.setStorageSync('user_info', data.user_info);
                }

                // 清除已使用的邀请码
                if (pendingInviteCode) {
                  app.globalData.pendingInviteCode = null;
                  console.log('[登录] 邀请码已使用，已清除');
                }

                // 判断是否为已绑定用户，显示相应提示
                if (data.user_info && data.user_info.inviter_id) {
                  wx.showToast({ title: '登录成功，已绑定邀请人', icon: 'success' });
                } else {
                  wx.showToast({ title: '登录成功', icon: 'success' });
                }

                setTimeout(() => {
                  wx.switchTab({ url: '/pages/mine/mine/mine' });
                }, 800);
              } else {
                wx.showToast({ title: payload.message || '登录失败', icon: 'none' });
              }
            },
            fail: () => {
              wx.showToast({ title: '网络异常，请稍后重试', icon: 'none' });
            },
            complete: () => {
              this.setData({ wxLoading: false });
            },
          });
        } else {
          wx.showToast({ title: '获取微信登录凭证失败', icon: 'none' });
          this.setData({ wxLoading: false });
        }
      },
      fail: () => {
        wx.showToast({ title: '微信登录失败', icon: 'none' });
        this.setData({ wxLoading: false });
      },
    });
  },

  /**
   * 账号密码登录
   * 登录成功后检查是否有待绑定的邀请码，如有则自动绑定
   */
  onSubmit() {
    if (!this.data.agreementChecked) {
      wx.showToast({
        title: '请先阅读并同意《用户协议》和《隐私政策》',
        icon: 'none'
      });
      return;
    }

    if (this.data.loading) {
      return;
    }

    const username = String(this.data.form.username || '').trim();
    const password = String(this.data.form.password || '').trim();

    if (!/^1\d{10}$/.test(username)) {
      wx.showToast({ title: '请输入正确手机号', icon: 'none' });
      return;
    }
    if (!password) {
      wx.showToast({ title: '请输入登录密码', icon: 'none' });
      return;
    }

    this.setData({ loading: true });

    wx.request({
      url: `${API_BASE_URL}/api/auth/login`,
      method: 'POST',
      header: {
        'content-type': 'application/json',
      },
      data: {
        username,
        password,
      },
      success: (res) => {
        const payload = res && res.data ? res.data : {};
        const ok = res.statusCode >= 200 && res.statusCode < 300 && payload.code === 1 && payload.data;
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

          // 检查是否有待绑定的邀请码，且用户未绑定过邀请人
          const app = getApp();
          const pendingInviteCode = app.globalData.pendingInviteCode;
          const hasInviter = !!(data.user_info && data.user_info.inviter_id);

          if (pendingInviteCode && !hasInviter) {
            // 登录成功后自动绑定邀请码
            this.bindInviteCodeAfterLogin(data.access_token);
          } else if (pendingInviteCode && hasInviter) {
            // 已有邀请人，清除待绑定邀请码
            app.globalData.pendingInviteCode = null;
            console.log('[登录] 用户已绑定邀请人，清除待绑定邀请码');
            wx.showToast({ title: payload.message || '登录成功', icon: 'success' });
          } else {
            wx.showToast({ title: payload.message || '登录成功', icon: 'success' });
          }

          setTimeout(() => {
            wx.switchTab({ url: '/pages/mine/mine/mine' });
          }, 800);
          return;
        }
        wx.showToast({ title: payload.message || '登录失败', icon: 'none' });
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
   * 登录后绑定邀请码
   * 用于账号密码登录场景，用户已有账号但扫码进入后需要绑定邀请人
   *
   * @param {string} token - 访问令牌
   */
  onAgreementToggle() {
    this.setData({
      agreementChecked: !this.data.agreementChecked
    });
  },

  onPrivacyTap() {
    wx.navigateTo({ url: '/pages/mine/privacy/privacy' });
  },

  onAgreementTap() {
    wx.navigateTo({ url: '/pages/mine/agreement/agreement' });
  },

  bindInviteCodeAfterLogin(token) {
    const app = getApp();
    const inviteCode = app.globalData.pendingInviteCode;

    if (!inviteCode || !token) return;

    wx.request({
      url: `${API_BASE_URL}/api/distribution/bind-invite-code`,
      method: 'POST',
      header: {
        'Authorization': `Bearer ${token}`,
        'content-type': 'application/json',
      },
      data: {
        invite_code: inviteCode,
      },
      success: (res) => {
        // 清除已使用的邀请码
        app.globalData.pendingInviteCode = null;

        if (res.data && res.data.code === 1) {
          console.log('[登录] 邀请码绑定成功');
          wx.showToast({ title: '登录成功，已绑定邀请人', icon: 'success' });
        } else {
          console.log('[登录] 邀请码绑定失败:', res.data && res.data.message);
        }
      },
      fail: () => {
        console.log('[登录] 邀请码绑定请求失败');
      }
    });
  },
});
