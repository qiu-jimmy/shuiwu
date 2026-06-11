// pages/mine/password/password.js
import { API_BASE_URL } from '../../../../utils/config';

Page({
  data: {
    form: {
      oldPassword: '',
      newPassword: '',
      confirmPassword: '',
    },
    loading: false,
  },

  onInputChange(event) {
    const field = event.currentTarget.dataset.field;
    const value = event.detail && event.detail.value !== undefined ? event.detail.value : '';
    if (!field) {
      return;
    }
    this.setData({ [`form.${field}`]: value });
  },

  onSubmit() {
    if (this.data.loading) {
      return;
    }

    const oldPassword = String(this.data.form.oldPassword || '').trim();
    const newPassword = String(this.data.form.newPassword || '').trim();
    const confirmPassword = String(this.data.form.confirmPassword || '').trim();

    // 当前密码允许为空
    // if (!oldPassword) {
    //   wx.showToast({ title: '请输入当前密码', icon: 'none' });
    //   return;
    // }
    if (!newPassword) {
      wx.showToast({ title: '请输入新密码', icon: 'none' });
      return;
    }
    if (!confirmPassword) {
      wx.showToast({ title: '请再次输入新密码', icon: 'none' });
      return;
    }
    if (newPassword !== confirmPassword) {
      wx.showToast({ title: '两次输入的新密码不一致', icon: 'none' });
      return;
    }

    const token = wx.getStorageSync('access_token');
    if (!token) {
      wx.showToast({ title: '请先登录', icon: 'none' });
      wx.navigateTo({ url: '/pages/mine/login/login' });
      return;
    }

    const tokenType = String(wx.getStorageSync('token_type') || 'bearer');
    const normalizedType = tokenType.toLowerCase() === 'bearer' ? 'Bearer' : tokenType;

    this.setData({ loading: true });

    wx.request({
      url: `${API_BASE_URL}/api/auth/change-password`,
      method: 'POST',
      header: {
        'content-type': 'application/json',
        Authorization: `${normalizedType} ${token}`,
      },
      data: {
        old_password: oldPassword,
        new_password: newPassword,
      },
      success: (res) => {
        const payload = res && res.data ? res.data : {};
        const ok = res.statusCode >= 200 && res.statusCode < 300 && payload.code === 1;
        if (ok) {
          wx.showToast({ title: payload.message || '修改密码成功', icon: 'success' });
          setTimeout(() => {
            wx.navigateBack({ delta: 1 });
          }, 800);
          return;
        }
        wx.showToast({ title: payload.message || '修改失败', icon: 'none' });
      },
      fail: () => {
        wx.showToast({ title: '网络异常，请稍后重试', icon: 'none' });
      },
      complete: () => {
        this.setData({ loading: false });
      },
    });
  },
});
