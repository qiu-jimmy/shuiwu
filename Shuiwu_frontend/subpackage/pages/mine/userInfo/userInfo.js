// pages/mine/userInfo/userInfo.js
import { API_BASE_URL, OSS_URL } from '../../../../utils/config';

const IMAGE_MIME_MAP = {
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.gif': 'image/gif',
  '.webp': 'image/webp',
  '.bmp': 'image/bmp',
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

const updateStoredUserInfo = (patch) => {
  const userInfo = wx.getStorageSync('user_info');
  if (!userInfo) {
    return;
  }
  wx.setStorageSync('user_info', { ...userInfo, ...patch });
};

const getFileName = (path, fallback = 'avatar.png') => {
  if (!path) {
    return fallback;
  }
  const normalized = path.replace(/\\/g, '/');
  const segments = normalized.split('/');
  return segments[segments.length - 1] || fallback;
};

const getFileExtension = (value = '') => {
  const index = value.lastIndexOf('.');
  if (index < 0) {
    return '';
  }
  return value.slice(index).toLowerCase();
};

const getImageMimeType = (value = '') => IMAGE_MIME_MAP[getFileExtension(value)] || 'image/jpeg';

const readFileAsBase64 = (filePath) =>
  new Promise((resolve, reject) => {
    const fileSystem = wx.getFileSystemManager();
    fileSystem.readFile({
      filePath,
      encoding: 'base64',
      success: (res) => resolve(res.data || ''),
      fail: reject,
    });
  });
const formatDateTime = (value) => {
  if (!value) {
    return '—';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  const pad = (num) => (num < 10 ? `0${num}` : `${num}`);
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
};

const formatMemberLevel = (level) => {
  const map = {
    free: '免费版',
    basic: '基础版',
    pro: '专业版',
    premium: '尊享版',
  };
  return map[level] || level || '—';
};

const formatStatus = (status) => {
  const map = {
    normal: '正常',
    disabled: '已停用',
    locked: '已锁定',
  };
  return map[status] || status || '—';
};

const formatUserType = (type) => {
  const map = {
    individual: '个人用户',
    enterprise: '企业用户',
  };
  return map[type] || type || '—';
};

const getEmptyDisplay = () => ({
  name: '—',
  phone: '—',
  memberLevel: '—',
  userType: '—',
  status: '—',
  member_package_name:'_'
});

const getInfoItems = (userInfo) => {
  const items = [
    {
      label: '昵称',
      value: userInfo.nickname || userInfo.phone || '未设置',
      editable: true,
      action: 'nickname',
    },
    {
      label: '手机号',
      value: userInfo.phone || '未设置',
      editable: true,
      action: 'phone',
    },
  ];

  if (userInfo.is_distributor) {
    items.push({
      label: '我的邀请码',
      value: userInfo.distributor_code || '—',
      editable: false,
    });
  }

  items.push(
    {
      label: '用户类型',
      value: formatUserType(userInfo.user_type),
      editable: false,
    },
    {
      label: '会员套餐',
      value: formatMemberLevel(userInfo.member_package_name),
      editable: false,
    },
    {
      label: '账号状态',
      value: formatStatus(userInfo.status),
      editable: false,
    },
    {
      label: '注册时间',
      value: formatDateTime(userInfo.register_time),
      editable: false,
    },
    {
      label: '用户ID',
      value: userInfo.user_id || '—',
      editable: false,
    }
  );

  return items;
};

const getEmptyItems = () => ([
  { label: '昵称', value: '—', editable: true, action: 'nickname' },
  { label: '手机号', value: '—', editable: true, action: 'phone' },
  { label: '用户类型', value: '—', editable: false },
  { label: '会员等级', value: '—', editable: false },
  { label: '账号状态', value: '—', editable: false },
  { label: '注册时间', value: '—', editable: false },
  { label: '用户ID', value: '—', editable: false },
]);

Page({
  data: {
    isLogin: false,
    avatarUrl: '',
    coverUrl: `${OSS_URL}/images/数据时代.png`,
    display: getEmptyDisplay(),
    infoItems: getEmptyItems(),
    nicknameVisible: false,
    phoneVisible: false,
    formNickname: '',
    formPhone: '',
    updatingNickname: false,
    updatingPhone: false,
    updatingAvatar: false,
  },

  onShow() {
    this.loadUserInfo();
  },

  onLoginTap() {
    wx.navigateTo({
      url: "/pages/mine/login/login",
    });
  },

  onAvatarTap() {
    if (!this.data.isLogin) {
      wx.showToast({ title: '请先登录', icon: 'none' });
      return;
    }
    if (this.data.updatingAvatar) {
      return;
    }
    wx.chooseImage({
      count: 1,
      sizeType: ['compressed'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        const filePath = res.tempFilePaths && res.tempFilePaths.length ? res.tempFilePaths[0] : '';
        if (!filePath) {
          return;
        }
        this.uploadAvatar(filePath);
      },
    });
  },

  onInfoItemTap(e) {
    const action = e.currentTarget.dataset.action;
    if (!action) {
      return;
    }
    if (!this.data.isLogin) {
      wx.showToast({ title: '请先登录', icon: 'none' });
      return;
    }
    const userInfo = wx.getStorageSync('user_info') || {};
    if (action === 'nickname') {
      this.setData({
        nicknameVisible: true,
        formNickname: userInfo.nickname || '',
      });
      return;
    }
    if (action === 'phone') {
      this.setData({
        phoneVisible: true,
        formPhone: userInfo.phone || '',
      });
    }
  },

  onNicknameChange(e) {
    this.setData({ formNickname: e.detail.value });
  },

  onNicknameClose() {
    this.setData({ nicknameVisible: false });
  },

  onPhoneChange(e) {
    this.setData({ formPhone: e.detail.value });
  },

  onPhoneClose() {
    this.setData({ phoneVisible: false });
  },

  onNicknameSubmit() {
    if (this.data.updatingNickname) {
      return;
    }
    const nickname = String(this.data.formNickname || '').trim();
    if (!nickname) {
      wx.showToast({ title: '请输入昵称', icon: 'none' });
      return;
    }
    const authHeader = getAuthHeader();
    if (!authHeader) {
      wx.showToast({ title: '请先登录', icon: 'none' });
      return;
    }
    this.setData({ updatingNickname: true });
    wx.request({
      url: `${API_BASE_URL}/api/user/center/nickname`,
      method: 'PUT',
      header: {
        'content-type': 'application/json',
        Authorization: authHeader,
      },
      data: {
        nickname,
      },
      success: (res) => {
        const payload = res && res.data ? res.data : {};
        const ok = res.statusCode >= 200 && res.statusCode < 300 && payload.code === 1;
        if (ok) {
          updateStoredUserInfo({ nickname });
          wx.showToast({ title: payload.message || '昵称更新成功', icon: 'success' });
          this.setData({ nicknameVisible: false });
          this.loadUserInfo();
          return;
        }
        wx.showToast({ title: payload.message || '昵称更新失败', icon: 'none' });
      },
      fail: () => {
        wx.showToast({ title: '网络异常，请稍后重试', icon: 'none' });
      },
      complete: () => {
        this.setData({ updatingNickname: false });
      },
    });
  },

  onPhoneSubmit() {
    if (this.data.updatingPhone) {
      return;
    }
    const phone = String(this.data.formPhone || '').trim();
    if (!phone) {
      wx.showToast({ title: '请输入手机号', icon: 'none' });
      return;
    }
    if (!/^\d{11}$/.test(phone)) {
      wx.showToast({ title: '请输入正确的手机号', icon: 'none' });
      return;
    }
    const authHeader = getAuthHeader();
    if (!authHeader) {
      wx.showToast({ title: '请先登录', icon: 'none' });
      return;
    }
    this.setData({ updatingPhone: true });
    wx.request({
      url: `${API_BASE_URL}/api/user/center/phone`,
      method: 'PUT',
      header: {
        'content-type': 'application/json',
        Authorization: authHeader,
      },
      data: {
        phone,
      },
      success: (res) => {
        const payload = res && res.data ? res.data : {};
        const ok = res.statusCode >= 200 && res.statusCode < 300 && payload.code === 1;
        if (ok) {
          updateStoredUserInfo({ phone });
          wx.showToast({ title: payload.message || '手机号更新成功', icon: 'success' });
          this.setData({ phoneVisible: false });
          this.loadUserInfo();
          return;
        }
        wx.showToast({ title: payload.message || '手机号更新失败', icon: 'none' });
      },
      fail: () => {
        wx.showToast({ title: '网络异常，请稍后重试', icon: 'none' });
      },
      complete: () => {
        this.setData({ updatingPhone: false });
      },
    });
  },

  uploadAvatar(filePath) {
    const authHeader = getAuthHeader();
    if (!authHeader) {
      wx.showToast({ title: '请先登录', icon: 'none' });
      return;
    }
    const fileName = getFileName(filePath, 'avatar.png');
    const mimeType = getImageMimeType(fileName);
    this.setData({ updatingAvatar: true });
    readFileAsBase64(filePath)
      .then((base64) => {
        const avatarData = `data:${mimeType};base64,${base64}`;
        wx.request({
          url: `${API_BASE_URL}/api/user/center/avatar`,
          method: 'PUT',
          header: {
            'content-type': 'application/json',
            Authorization: authHeader,
          },
          data: {
            avatar_data: avatarData,
            file_name: fileName,
          },
          success: (res) => {
            const payload = res && res.data ? res.data : {};
            const ok = res.statusCode >= 200 && res.statusCode < 300 && payload.code === 1;
            if (ok) {
              const avatarUrl = payload.data && payload.data.avatar_url ? payload.data.avatar_url : '';
              if (avatarUrl) {
                updateStoredUserInfo({ avatar_url: avatarUrl });
              }
              wx.showToast({ title: payload.message || '头像更新成功', icon: 'success' });
              this.loadUserInfo();
              return;
            }
            wx.showToast({ title: payload.message || '头像更新失败', icon: 'none' });
          },
          fail: () => {
            wx.showToast({ title: '网络异常，请稍后重试', icon: 'none' });
          },
          complete: () => {
            this.setData({ updatingAvatar: false });
          },
        });
      })
      .catch(() => {
        this.setData({ updatingAvatar: false });
        wx.showToast({ title: '头像读取失败', icon: 'none' });
      });
  },

  loadUserInfo() {
    const userInfo = wx.getStorageSync('user_info');
    if (!userInfo) {
      this.setData({
        isLogin: false,
        avatarUrl: '',
        display: getEmptyDisplay(),
        infoItems: getEmptyItems(),
      });
      return;
    }
    const display = {
      name: userInfo.nickname || userInfo.phone || '未设置',
      phone: userInfo.phone || '未设置',
      memberLevel: formatMemberLevel(userInfo.member_level),
      member_package_name:userInfo.member_package_name,
      userType: formatUserType(userInfo.user_type),
      status: formatStatus(userInfo.status),
    };
    this.setData({
      isLogin: true,
      avatarUrl: userInfo.avatar_url || '',
      display,
      infoItems: getInfoItems(userInfo),
    });
  },
});
