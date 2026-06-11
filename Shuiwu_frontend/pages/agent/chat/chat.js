import { API_BASE_URL } from '../../../utils/config';
const ASSISTANT_AVATAR = 'https://tdesign.gtimg.com/site/chat-avatar.png';
const USER_AVATAR = 'https://tdesign.gtimg.com/site/chat-avatar.png';

const pad = (num) => (num < 10 ? `0${num}` : `${num}`);

const formatTime = (date) => `${pad(date.getHours())}:${pad(date.getMinutes())}`;

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

const getSessionId = () => {
  const pages = getCurrentPages();
  const current = pages && pages.length ? pages[pages.length - 1] : null;
  const options = current && current.options ? current.options : {};
  return options.sessionId || options.session_id || wx.getStorageSync('active_session_id') || '';
};

const arrayBufferToString = (buffer) => {
  if (!buffer) {
    return '';
  }
  if (typeof TextDecoder !== 'undefined') {
    return new TextDecoder('utf-8').decode(buffer);
  }
  const uint8Array = new Uint8Array(buffer);
  let result = '';
  for (let i = 0; i < uint8Array.length; i += 1) {
    result += String.fromCharCode(uint8Array[i]);
  }
  try {
    return decodeURIComponent(escape(result));
  } catch (error) {
    return result;
  }
};

const getMessageText = (content = []) => {
  if (!Array.isArray(content)) {
    return '';
  }
  return content
    .map((item) => {
      if (!item) {
        return '';
      }
      if (item.type === 'text' || item.type === 'markdown') {
        return item.data || '';
      }
      if (item.type === 'attachment' && Array.isArray(item.data)) {
        return item.data
          .map((file) => file.name || file.url || '')
          .filter(Boolean)
          .join(' ');
      }
      return '';
    })
    .filter(Boolean)
    .join('');
};

const mapHistoryMessages = (messages = []) => {
  return messages.slice().reverse().map((message) => ({
    avatar: message.role === 'assistant' ? ASSISTANT_AVATAR : '',
    datetime: message.timestamp || '',
    message: {
      role: message.role,
      status: 'complete',
      content: [
        {
          type: 'markdown',
          data: message.content || '',
        },
      ],
    },
  }));
};

Component({
  properties: {
    isActive: {
      type: Boolean,
      value: false,
      observer: function (v) {
        setTimeout(() => {
          this.setData({
            value: v
              ? '根据所提供的材料总结一篇文章，推荐春天户外郊游打卡目的地，需要符合小红书平台写作风格'
              : '',
          });
        }, 30);
      },
    },
  },
  data: {
    customActionBar: ['copy', 'good', 'bad'],
    chatList: [
      {
        avatar: ASSISTANT_AVATAR,
        // name: '税务智能体',
        // datetime: formatTime(new Date()),
        message: {
          role: 'assistant',
          status: 'complete',
          content: [
            {
              type: 'text',
              data: '你好，我是税务智能体，有问题可以直接问我。',
            },
          ],
        },
      },
    ],
    value: '',
    loading: false,
    disabled: false,
    inputStyle: '',
    attachmentsProps: {
      items: [],
      removable: true,
      imageViewer: true,
      addable: false,
    },
    renderPresets: [
      {
        name: 'send',
        type: 'icon',
      },
    ],
    fileList: [],
    visible: false,
    chatContentProps: {
      thinking: { maxHeight: 100, collapsed: true },
    },
    contentHeight: '100vh',
    sessionId: '',
    historyLoaded: false,
    historyLoading: false,
    // 配额不足弹窗
    quotaModalVisible: false,
    quotaMessage: '',
    // 普通模式提示
    basicModeVisible: false,
    basicModeTimer: null,
  },

  methods: {
    onCopyMessage(e) {
      const index = Number(e.currentTarget.dataset.index);
      const target = Number.isNaN(index) ? null : this.data.chatList[index];
      const content = target && target.message ? target.message.content : [];
      const text = getMessageText(content);
      if (!text) {
        Toast({
          context: this,
          selector: '#t-toast',
          message: '暂无可复制内容',
          theme: 'warning',
        });
        return;
      }
      wx.setClipboardData({
        data: text,
        success: () => {
          Toast({
            context: this,
            selector: '#t-toast',
            message: '已复制',
            theme: 'success',
          });
        },
        fail: () => {
          Toast({
            context: this,
            selector: '#t-toast',
            message: '复制失败',
            theme: 'error',
          });
        },
      });
    },
    onSend(e) {
      const { value } = e.detail;
      if (!value || value.trim() === '' || this.data.loading) return;

      const content = [
        {
          type: 'text',
          data: value.trim(),
        },
      ];
      const attachments = this.data.attachmentsProps.items.map((item) => {
        return {
          ...item,
          status: 'success',
        };
      });
      if (attachments.length) {
        content.unshift({
          type: 'attachment',
          data: attachments,
        });
      }

      const userMessage = {
        //avatar: USER_AVATAR,
        //name: '你',
        datetime: formatTime(new Date()),
        message: {
          role: 'user',
          status: 'complete',
          content,
        },
      };

      this.setData({
        attachmentsProps: {
          ...this.data.attachmentsProps,
          items: [],
        },
        fileList: [],
        chatList: [userMessage, ...this.data.chatList],
        value: '',
      });

      // 显示普通模式提示
      this.showBasicToast();

      this.sendMessage(value.trim());
    },

    onStop() {
      if (this.requestTask) {
        this.requestTask.abort();
        this.requestTask = null;
      }
      const chatList = this.data.chatList.slice();
      if (chatList[0] && chatList[0].message.role === 'assistant') {
        chatList[0].message.status = 'stop';
      }
      this.setData({
        chatList,
        loading: false,
        disabled: false,
      });
    },

    onFocus() {},

    onUpdateVisible(e) {
      const visible = e.detail;
      this.setData({ visible });
    },

    onFileDelete() {
      this.setData({
        attachmentsProps: {
          ...this.data.attachmentsProps,
          items: [],
        },
      });
    },

    onFileChange(e) {
      const { files } = e.detail;
      this.setData({ attachmentsProps: { ...this.data.attachmentsProps, items: files } });
      this.setData({ fileList: files });
    },

    sendMessage(message) {
      const auth = getAuthContext();
      if (!auth) {
        wx.showToast({ title: '请先登录', icon: 'none' });
        return;
      }

      const sessionId = this.data.sessionId || getSessionId();
      if (!sessionId) {
        wx.showToast({ title: '缺少会话ID', icon: 'none' });
        return;
      }

      const assistantMessage = {
        avatar: ASSISTANT_AVATAR,
        name: '税务智能体',
        datetime: formatTime(new Date()),
        message: {
          role: 'assistant',
          status: 'streaming',
          content: [
            {
              type: 'markdown',
              data: '',
            },
          ],
        },
      };

      this.setData({
        chatList: [assistantMessage, ...this.data.chatList],
        loading: true,
        disabled: true,
        sessionId,
      });

      let buffer = '';
      let assistantText = '';

      const updateAssistant = (status) => {
        const chatList = this.data.chatList.slice();
        if (!chatList.length) {
          return;
        }
        chatList[0].message.content[0].data = assistantText;
        if (status) {
          chatList[0].message.status = status;
        }
        this.setData({ chatList });
      };

      const handleChunk = (chunkText) => {
        // 先尝试直接解析为 JSON（处理非 SSE 格式的错误响应）
        try {
          const data = JSON.parse(chunkText);

          // 处理配额不足错误
          if (data.code === 'QUOTA_EXCEEDED') {
            updateAssistant('error');
            this.setData({
              loading: false,
              disabled: false,
              quotaModalVisible: true,
              quotaMessage: data.message || '今日聊天次数已用完，请开通会员继续使用',
            });
            return;
          }

          // 如果是其他格式的响应，尝试作为 SSE 处理
        } catch (e) {
          // 不是纯 JSON，继续按 SSE 格式处理
        }

        // SSE 格式处理
        buffer += chunkText;
        const lines = buffer.split(/\r?\n/);
        buffer = lines.pop() || '';
        lines.forEach((line) => {
          const trimmed = line.trim();
          if (!trimmed || !trimmed.startsWith('data:')) {
            return;
          }
          const raw = trimmed.replace(/^data:\s*/, '');
          if (!raw) {
            return;
          }
          let payload;
          try {
            payload = JSON.parse(raw);
          } catch (error) {
            return;
          }
          // 处理配额不足错误（SSE 格式）
          if (payload.code === 'QUOTA_EXCEEDED') {
            updateAssistant('error');
            this.setData({
              loading: false,
              disabled: false,
              quotaModalVisible: true,
              quotaMessage: payload.message || '今日聊天次数已用完，请开通会员继续使用',
            });
            return;
          }
          if (payload.type === 'content') {
            assistantText += payload.content || '';
            updateAssistant('streaming');
          }
          if (payload.type === 'completed') {
            updateAssistant('complete');
            this.setData({ loading: false, disabled: false });
          }
        });
      };

      this.requestTask = wx.request({
        url: `${API_BASE_URL}/api/chat/chat`,
        method: 'POST',
        header: {
          'content-type': 'application/json',
          Authorization: `${auth.tokenType} ${auth.token}`,
        },
        data: {
          session_id: sessionId,
          user_id: auth.userId,
          message,
          model_id: 'qwen-flash',
        },
        enableChunked: true,
        responseType: 'arraybuffer',
        success: (res) => {
          // 检查 HTTP 状态码
          if (res.statusCode !== 200) {
            // 非成功状态码，尝试解析错误响应
            updateAssistant('error');
            this.setData({ loading: false, disabled: false });

            if (res && res.data) {
              try {
                const chunkText = typeof res.data === 'string' ? res.data : arrayBufferToString(res.data);
                const errorData = JSON.parse(chunkText);

                // 处理配额不足错误
                if (errorData.code === 'QUOTA_EXCEEDED') {
                  this.setData({
                    quotaModalVisible: true,
                    quotaMessage: errorData.message || '今日聊天次数已用完，请开通会员继续使用',
                  });
                  return;
                }

                // 其他错误提示
                wx.showToast({ title: errorData.message || '请求失败', icon: 'none' });
              } catch (e) {
                wx.showToast({ title: '请求失败', icon: 'none' });
              }
            } else {
              wx.showToast({ title: '请求失败', icon: 'none' });
            }
            return;
          }

          // 正常流式响应
          if (res && res.data) {
            const chunkText = typeof res.data === 'string' ? res.data : arrayBufferToString(res.data);
            if (chunkText) {
              handleChunk(chunkText);
            }
          }
          if (this.data.loading) {
            updateAssistant('complete');
            this.setData({ loading: false, disabled: false });
          }
        },
        fail: () => {
          updateAssistant('error');
          this.setData({ loading: false, disabled: false });
          wx.showToast({ title: '网络异常，请稍后重试', icon: 'none' });
        },
      });

      if (this.requestTask && typeof this.requestTask.onChunkReceived === 'function') {
        this.requestTask.onChunkReceived((response) => {
          const chunkText = arrayBufferToString(response && response.data);
          if (chunkText) {
            handleChunk(chunkText);
          }
        });
      } else if (this.requestTask && typeof this.requestTask.onChunkedData === 'function') {
        this.requestTask.onChunkedData((response) => {
          const chunkText = arrayBufferToString(response && response.data);
          if (chunkText) {
            handleChunk(chunkText);
          }
        });
      }
    },

    loadHistory(sessionId) {
      const auth = getAuthContext();
      if (!auth || !sessionId || this.data.historyLoading) {
        return;
      }

      this.setData({ historyLoading: true });
      wx.showLoading({ title: '加载中' });
      wx.request({
        url: `${API_BASE_URL}/api/chat/sessions/${sessionId}/messages/simple?user_id=${encodeURIComponent(auth.userId)}`,
        method: 'GET',
        header: {
          Authorization: `${auth.tokenType} ${auth.token}`,
        },
        success: (res) => {
          const payload = res && res.data ? res.data : {};
          const ok = res.statusCode >= 200 && res.statusCode < 300 && payload.code === 1 && payload.data;
          if (ok) {
            const messages = payload.data.messages || [];
            if (messages.length) {
              const mapped = mapHistoryMessages(messages);
              this.setData({ chatList: mapped, historyLoaded: true });
              return;
            }
            this.setData({ historyLoaded: true });
            return;
          }
          wx.showToast({ title: payload.message || '获取历史消息失败', icon: 'none' });
        },
        fail: () => {
          wx.showToast({ title: '网络异常，请稍后重试', icon: 'none' });
        },
        complete: () => {
          this.setData({ historyLoading: false });
          wx.hideLoading();
        },
      });
    },

    refreshSession() {
      const sessionId = getSessionId();
      if (!sessionId) {
        return;
      }
      const shouldReload = sessionId !== this.data.sessionId || !this.data.historyLoaded;
      this.setData({ sessionId });
      if (shouldReload) {
        this.loadHistory(sessionId);
      }
    },

    // 配额弹窗操作
    onQuotaModalClose() {
      this.setData({ quotaModalVisible: false });
    },

    onGoToVip() {
      this.setData({ quotaModalVisible: false });
      wx.navigateTo({ url: '/subpackage/pages/mine/vip-buy/vip-buy' });
    },

    // 显示普通模式提示
    showBasicToast() {
      // 清除之前的定时器
      if (this.data.basicModeTimer) {
        clearTimeout(this.data.basicModeTimer);
      }
      // 显示提示
      this.setData({ basicModeVisible: true });
      // 2秒后自动隐藏
      const timer = setTimeout(() => {
        this.setData({ basicModeVisible: false });
      }, 2000);
      this.setData({ basicModeTimer: timer });
    },
  },
  lifetimes: {
    attached: function () {
      this.refreshSession();
      try {
        const contentHeight = `calc(100vh - 96rpx)`;
        this.setData({
          contentHeight: contentHeight,
        });
      } catch (error) {
        this.setData({
          contentHeight: 'calc(100vh - 96rpx)',
        });
      }
    },
  },
  pageLifetimes: {
    show: function () {
      this.refreshSession();
    },
  },
});
