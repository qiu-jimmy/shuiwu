// pages/agent/agent/agent.js
import { API_BASE_URL, OSS_URL } from '../../../utils/config';
const DEFAULT_SUBTITLE = '智税引擎';

const pad = (num) => (num < 10 ? `0${num}` : `${num}`);

const isSameDay = (date, other) =>
  date.getFullYear() === other.getFullYear() &&
  date.getMonth() === other.getMonth() &&
  date.getDate() === other.getDate();

const getWeekStart = (date) => {
  const day = date.getDay();
  const diff = (day + 6) % 7;
  return new Date(date.getFullYear(), date.getMonth(), date.getDate() - diff);
};

const formatTime = (value) => {
  if (!value) {
    return '--';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  const now = new Date();
  if (isSameDay(date, now)) {
    return `${pad(date.getHours())}:${pad(date.getMinutes())}`;
  }
  const year = date.getFullYear() % 100;
  return `${pad(year)}/${pad(date.getMonth() + 1)}/${pad(date.getDate())}`;
};

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

const buildSections = (sessions = []) => {
  const now = new Date();
  const weekStart = getWeekStart(now);
  const monthStart = new Date(now.getFullYear(), now.getMonth(), 1);
  const sections = {
    今天: [],
    本周: [],
    本月: [],
    更早: [],
  };

  sessions.forEach((session) => {
    const updatedAt = new Date(session.updated_at);
    let group = '更早';
    if (!Number.isNaN(updatedAt.getTime())) {
      const dayStart = new Date(updatedAt.getFullYear(), updatedAt.getMonth(), updatedAt.getDate());
      if (isSameDay(updatedAt, now)) {
        group = '今天';
      } else if (dayStart >= weekStart) {
        group = '本周';
      } else if (dayStart >= monthStart) {
        group = '本月';
      }
    }

    sections[group].push({
      id: session.id || `${session.name || 'session'}-${session.updated_at || ''}`,
      title: session.name || '未命名会话',
      subtitle: DEFAULT_SUBTITLE,
      time: formatTime(session.updated_at),
    });
  });

  return Object.keys(sections)
    .filter((key) => sections[key].length)
    .map((key) => ({ title: key, items: sections[key] }));
};

Page({
  data: {
    // OSS图片地址前缀
    ossUrl: OSS_URL,
    chatSections: [],
    editMode: false,
    creating: false,
    loading: false,
  },

  onShow() {
    this.loadSessions();
  },

  onEditTap() {
    this.setData({ editMode: true });
  },

  onDoneTap() {
    this.setData({ editMode: false });
  },

  onClearTap() {
    if (!this.data.chatSections.length) {
      wx.showToast({ title: '暂无可清空内容', icon: 'none' });
      return;
    }
    const auth = getAuthContext();
    if (!auth) {
      wx.showToast({ title: '请先登录', icon: 'none' });
      return;
    }
    wx.showModal({
      title: '清空记录',
      content: '确定清空所有对话记录吗？',
      confirmText: '清空',
      success: (res) => {
        if (res.confirm) {
          wx.showLoading({ title: '正在清理' });
          wx.request({
            url: `${API_BASE_URL}/api/chat/sessions/all`,
            method: 'DELETE',
            header: {
              'content-type': 'application/json',
              Authorization: `${auth.tokenType} ${auth.token}`,
            },
            data: {
              user_id: auth.userId,
            },
            success: (response) => {
              const payload = response && response.data ? response.data : {};
              const ok = response.statusCode >= 200 && response.statusCode < 300 && payload.code === 1 && payload.data;
              if (ok) {
                this.setData({ chatSections: [], editMode: false });
                wx.showToast({ title: '清空成功', icon: 'success' });
                return;
              }
              wx.showToast({ title: '清空失败', icon: 'none' });
            },
            fail: () => {
              wx.showToast({ title: '网络异常，请稍后重试', icon: 'none' });
            },
            complete: () => {
              wx.hideLoading();
            },
          });
        }
      },
    });
  },

  onCreateTap() {
    if (this.data.creating) {
      return;
    }
    const auth = getAuthContext();
    if (!auth) {
      wx.showToast({ title: '请先登录', icon: 'none' });
      return;
    }
    wx.showLoading({ title: '加载中' });
    this.setData({ creating: true });
    wx.request({
      url: `${API_BASE_URL}/api/chat/sessions`,
      method: 'POST',
      header: {
        'content-type': 'application/json',
        Authorization: `${auth.tokenType} ${auth.token}`,
      },
      data: {
        user_id: auth.userId,
        name: '',
      },
      success: (response) => {
        const payload = response && response.data ? response.data : {};
        const ok = response.statusCode >= 200 && response.statusCode < 300 && payload.code === 1 && payload.data;
        if (ok) {
          wx.showToast({ title: payload.message || '创建会话成功', icon: 'success' });
          const sessionId = payload.data.session_id;
          if (sessionId) {
            const userInfo = wx.getStorageSync('user_info');
            const memberLevel = String(userInfo && userInfo.member_level ? userInfo.member_level : '').toLowerCase();
            const targetPage = memberLevel === 'free'
              ? '/pages/agent/chat/chat'
              : '/pages/agent/chat-vip/chat-vip';
            wx.setStorageSync('active_session_id', sessionId);
            wx.navigateTo({ url: `${targetPage}?sessionId=${encodeURIComponent(sessionId)}` });
            return;
          }
          this.loadSessions();
          return;
        }
        wx.showToast({ title: payload.message || '创建会话失败', icon: 'none' });
      },
      fail: () => {
        wx.showToast({ title: '网络异常，请稍后重试', icon: 'none' });
      },
      complete: () => {
        this.setData({ creating: false });
        wx.hideLoading();
      },
    });
  },

  onEditItemTap(event) {
    const sectionIndex = Number(event && event.currentTarget && event.currentTarget.dataset.section);
    const itemIndex = Number(event && event.currentTarget && event.currentTarget.dataset.index);
    if (Number.isNaN(sectionIndex) || Number.isNaN(itemIndex)) {
      return;
    }
    const section = this.data.chatSections[sectionIndex];
    const entry = section && section.items ? section.items[itemIndex] : null;
    if (!entry || !entry.id) {
      wx.showToast({ title: '未找到会话信息', icon: 'none' });
      return;
    }

    wx.showModal({
      title: '编辑会话名称',
      content: '',
      editable: true,
      placeholderText: '请输入新的会话名称',
      confirmText: '保存',
      success: (res) => {
        if (!res.confirm) {
          return;
        }
        const name = String(res.content || '').trim();
        if (!name) {
          wx.showToast({ title: '请输入新的会话名称', icon: 'none' });
          return;
        }
        if (name === entry.title) {
          wx.showToast({ title: '名称未改变', icon: 'none' });
          return;
        }
        this.updateSessionName(entry.id, name, sectionIndex, itemIndex);
      },
    });
  },

  onSessionTap(event) {
    if (this.data.editMode) {
      return;
    }
    const userInfo = wx.getStorageSync('user_info');
    const memberLevel = String(userInfo && userInfo.member_level ? userInfo.member_level : '').toLowerCase();
    const targetPage = memberLevel === 'free'
      ? '/pages/agent/chat/chat'
      : '/pages/agent/chat-vip/chat-vip';
    const sectionIndex = Number(event.currentTarget.dataset.section);
    const itemIndex = Number(event.currentTarget.dataset.index);
    const section = this.data.chatSections[sectionIndex];
    const entry = section && section.items ? section.items[itemIndex] : null;
    if (!entry || !entry.id) {
      wx.navigateTo({ url: targetPage });
      return;
    }
    wx.setStorageSync('active_session_id', entry.id);
    wx.navigateTo({ url: `${targetPage}?sessionId=${encodeURIComponent(entry.id)}` });
  },

  onDeleteItemTap(event) {
    const sectionIndex = Number(event.currentTarget.dataset.section);
    const itemIndex = Number(event.currentTarget.dataset.index);
    if (Number.isNaN(sectionIndex) || Number.isNaN(itemIndex)) {
      return;
    }
    const section = this.data.chatSections[sectionIndex];
    const entry = section && section.items ? section.items[itemIndex] : null;
    if (!entry || !entry.id) {
      wx.showToast({ title: '未找到会话信息', icon: 'none' });
      return;
    }
    const auth = getAuthContext();
    if (!auth) {
      wx.showToast({ title: '请先登录', icon: 'none' });
      return;
    }
    wx.showModal({
      title: '删除会话',
      content: '确定删除该会话记录吗？',
      confirmText: '删除',
      success: (res) => {
        if (res.confirm) {
          wx.showLoading({ title: '加载中' });
          wx.request({
            url: `${API_BASE_URL}/api/chat/sessions`,
            method: 'DELETE',
            header: {
              'content-type': 'application/json',
              Authorization: `${auth.tokenType} ${auth.token}`,
            },
            data: {
              session_id: entry.id,
              user_id: auth.userId,
            },
            success: (response) => {
              const payload = response && response.data ? response.data : {};
              const ok = response.statusCode >= 200 && response.statusCode < 300 && payload.code === 1 && payload.data;
              if (ok) {
                const sections = this.data.chatSections
                  .map((current, sIndex) => {
                    if (sIndex !== sectionIndex) {
                      return current;
                    }
                    const items = current.items.slice();
                    items.splice(itemIndex, 1);
                    return { ...current, items };
                  })
                  .filter((current) => current.items.length);
                this.setData({ chatSections: sections });
                wx.showToast({ title: payload.message || '删除成功', icon: 'success' });
                return;
              }
              wx.showToast({ title: payload.message || '删除失败', icon: 'none' });
            },
            fail: () => {
              wx.showToast({ title: '网络异常，请稍后重试', icon: 'none' });
            },
            complete: () => {
              wx.hideLoading();
            },
          });
        }
      },
    });
  },

  loadSessions() {
    const auth = getAuthContext();
    if (!auth) {
      this.setData({ chatSections: [] });
      return;
    }

    wx.showLoading({ title: '加载中' });
    this.setData({ loading: true });

    wx.request({
      url: `${API_BASE_URL}/api/chat/sessions?user_id=${encodeURIComponent(auth.userId)}`,
      method: 'GET',
      header: {
        Authorization: `${auth.tokenType} ${auth.token}`,
      },
      success: (res) => {
        const payload = res && res.data ? res.data : {};
        const ok = res.statusCode >= 200 && res.statusCode < 300 && payload.code === 1 && payload.data;
        if (ok) {
          const sessions = payload.data.sessions || [];
          const sorted = sessions.slice().sort((a, b) => {
            const timeA = new Date(a.updated_at).getTime();
            const timeB = new Date(b.updated_at).getTime();
            return (Number.isNaN(timeB) ? 0 : timeB) - (Number.isNaN(timeA) ? 0 : timeA);
          });
          this.setData({ chatSections: buildSections(sorted) });
          return;
        }
        wx.showToast({ title: payload.message || '获取会话列表失败', icon: 'none' });
      },
      fail: () => {
        wx.showToast({ title: '网络异常，请稍后重试', icon: 'none' });
      },
      complete: () => {
        this.setData({ loading: false });
        wx.hideLoading();
      },
    });
  },

  updateSessionName(sessionId, name, sectionIndex, itemIndex) {
    const auth = getAuthContext();
    if (!auth) {
      wx.showToast({ title: '请先登录', icon: 'none' });
      return;
    }

    wx.showLoading({ title: '加载中' });
    wx.request({
      url: `${API_BASE_URL}/api/chat/sessions`,
      method: 'PUT',
      header: {
        'content-type': 'application/json',
        Authorization: `${auth.tokenType} ${auth.token}`,
      },
      data: {
        session_id: sessionId,
        user_id: auth.userId,
        name,
      },
      success: (res) => {
        const payload = res && res.data ? res.data : {};
        const ok = res.statusCode >= 200 && res.statusCode < 300 && payload.code === 1 && payload.data;
        if (ok) {
          const newName = payload.data.name || name;
          this.setData({
            [`chatSections[${sectionIndex}].items[${itemIndex}].title`]: newName,
          });
          wx.showToast({ title:'更新成功', icon: 'success' });
          return;
        }
        wx.showToast({ title:'更新失败', icon: 'none' });
      },
      fail: () => {
        wx.showToast({ title: '网络异常，请稍后重试', icon: 'none' });
      },
      complete: () => {
        wx.hideLoading();
      },
    });
  },
});
