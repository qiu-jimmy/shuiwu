// pages/agent/contractReview/contractReview.js
import { API_BASE_URL } from '../../../../utils/config';
const DEFAULT_MESSAGE = '请帮我审查这份合同，指出其中的风险条款';
const DEFAULT_MODEL_ID = 'qwen-plus';

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

const getFileName = (path, fallback = 'contract') => {
  if (!path) {
    return fallback;
  }
  const normalized = path.replace(/\\/g, '/');
  const segments = normalized.split('/');
  return segments[segments.length - 1] || fallback;
};

Page({
  data: {
    fileName: '',
    output: '',
    loading: false,
  },

  onUnload() {
    if (this.requestTask) {
      this.requestTask.abort();
      this.requestTask = null;
    }
  },

  onSelectFile() {
    if (this.data.loading) {
      return;
    }
    wx.chooseMessageFile({
      count: 1,
      type: 'file',
      success: (res) => {
        const file = res.tempFiles && res.tempFiles[0] ? res.tempFiles[0] : null;
        if (!file) {
          return;
        }
        const filePath = file.path || file.tempFilePath || file.url || '';
        if (!filePath) {
          wx.showToast({ title: '未获取到文件路径', icon: 'none' });
          return;
        }
        this.setData({
          fileName: file.name || getFileName(filePath),
          output: '',
          loading: true,
        });
        this.readAndSendFile(filePath, file.name || getFileName(filePath));
      },
      fail: () => {
        wx.showToast({ title: '选择文件失败', icon: 'none' });
      },
    });
  },

  onCopyOutput() {
    const text = this.data.output || '';
    if (!text) {
      wx.showToast({ title: '暂无可复制内容', icon: 'none' });
      return;
    }
    wx.setClipboardData({
      data: text,
      success: () => {
        wx.showToast({ title: '已复制', icon: 'success' });
      },
      fail: () => {
        wx.showToast({ title: '复制失败', icon: 'none' });
      },
    });
  },

  readAndSendFile(filePath, fileName) {
    const auth = getAuthContext();
    if (!auth) {
      wx.showModal({
        title: '提示',
        content: '请先登录',
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
      this.setData({ loading: false });
      return;
    }

    const fileSystem = wx.getFileSystemManager();
    fileSystem.readFile({
      filePath,
      encoding: 'base64',
      success: (res) => {
        const base64 = res.data || '';
        if (!base64) {
          wx.showToast({ title: '文件内容为空', icon: 'none' });
          this.setData({ loading: false });
          return;
        }
        this.sendRequest(auth, fileName, base64);
      },
      fail: () => {
        wx.showToast({ title: '文件读取失败', icon: 'none' });
        this.setData({ loading: false });
      },
    });
  },

  sendRequest(auth, fileName, base64) {
    wx.showLoading({ title: '生成中' });
    let buffer = '';

    const handleChunk = (chunkText) => {
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
        if (payload.type === 'content') {
          this.setData({
            output: `${this.data.output}${payload.content || ''}`,
          });
        }
        if (payload.type === 'completed') {
          this.setData({ loading: false });
        }
      });
    };

    this.requestTask = wx.request({
      url: `${API_BASE_URL}/api/chat/contract-chat`,
      method: 'POST',
      header: {
        'content-type': 'application/json',
        Authorization: `${auth.tokenType} ${auth.token}`,
      },
      data: {
        user_id: auth.userId,
        message: DEFAULT_MESSAGE,
        model_id: DEFAULT_MODEL_ID,
        files: [
          {
            filename: fileName,
            file_base64: base64,
          },
        ],
      },
      timeout: 300000,
      enableChunked: true,
      responseType: 'arraybuffer',
      success: (res) => {
        wx.hideLoading();
        if (res && res.data) {
          let text = res.data;
          if (typeof res.data !== 'string') {
            text = arrayBufferToString(res.data);
          }
          if (text) {
            try {
              const data = JSON.parse(text.trim());
              if (data && data.code === 'PRIVILEGE_REQUIRED') {
                wx.showModal({
                  title: '提示',
                  content: data.message || '此功能需要开通相应权益',
                  confirmText: '去充值',
                  cancelText: '取消',
                  success: (modalRes) => {
                    if (modalRes.confirm) {
                      wx.navigateTo({ url: '/subpackage/pages/mine/vip-buy/vip-buy' });
                    }
                  },
                });
                this.setData({ loading: false });
                return;
              }
              if (data && data.code && data.code !== 1) {
                wx.showToast({ title: data.message || '请求失败', icon: 'none' });
                this.setData({ loading: false });
                return;
              }
            } catch (e) {
              // 不是 JSON，继续处理流式数据
            }
            handleChunk(text);
          }
        }
        if (this.data.loading) {
          this.setData({ loading: false });
        }
      },
      fail: () => {
        wx.hideLoading();
        this.setData({ loading: false });
        wx.showToast({ title: '网络异常，请稍后重试', icon: 'none' });
      },
    });

    if (this.requestTask && typeof this.requestTask.onChunkReceived === 'function') {
      this.requestTask.onChunkReceived((response) => {
        const chunkText = arrayBufferToString(response && response.data);
        if (chunkText) {
          try {
            const data = JSON.parse(chunkText.trim());
            if (data && data.code === 'PRIVILEGE_REQUIRED') {
              wx.hideLoading();
              wx.showModal({
                title: '提示',
                content: data.message || '此功能需要开通相应权益',
                confirmText: '去充值',
                cancelText: '取消',
                success: (modalRes) => {
                  if (modalRes.confirm) {
                    wx.navigateTo({ url: '/subpackage/pages/mine/vip-buy/vip-buy' });
                  }
                },
              });
              this.setData({ loading: false });
              this.requestTask.abort();
              return;
            }
          } catch (e) {
            // 不是 JSON，继续处理流式数据
          }
          handleChunk(chunkText);
        }
      });
    } else if (this.requestTask && typeof this.requestTask.onChunkedData === 'function') {
      this.requestTask.onChunkedData((response) => {
        const chunkText = arrayBufferToString(response && response.data);
        if (chunkText) {
          try {
            const data = JSON.parse(chunkText.trim());
            if (data && data.code === 'PRIVILEGE_REQUIRED') {
              wx.hideLoading();
              wx.showModal({
                title: '提示',
                content: data.message || '此功能需要开通相应权益',
                confirmText: '去充值',
                cancelText: '取消',
                success: (modalRes) => {
                  if (modalRes.confirm) {
                    wx.navigateTo({ url: '/subpackage/pages/mine/vip-buy/vip-buy' });
                  }
                },
              });
              this.setData({ loading: false });
              this.requestTask.abort();
              return;
            }
          } catch (e) {
            // 不是 JSON，继续处理流式数据
          }
          handleChunk(chunkText);
        }
      });
    }
  },
});
