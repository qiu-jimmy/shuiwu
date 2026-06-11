const Toast = require('tdesign-miniprogram/toast/index');
import { API_BASE_URL } from '../../../utils/config';
const ASSISTANT_AVATAR = 'https://tdesign.gtimg.com/site/chat-avatar.png';
const USER_AVATAR = 'https://tdesign.gtimg.com/site/chat-avatar.png';
const IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp'];
const IMAGE_MIME_MAP = {
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.gif': 'image/gif',
  '.webp': 'image/webp',
  '.bmp': 'image/bmp',
};
const REQUEST_TIMEOUT_MS = 5 * 60 * 1000;

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

/**
 * 从后端响应对象中提取业务错误码（兼容 code / error_code / data.code / message）
 */
const getResponseErrorCode = (obj) => {
  if (!obj || typeof obj !== 'object') return null;
  const code = obj.code || obj.errorCode || obj.error_code || (obj.data && (obj.data.code || obj.data.errorCode));
  if (code != null && String(code).trim()) return String(code).trim();
  const msg = obj.message || obj.msg || '';
  if (typeof msg !== 'string') return null;
  const m = String(msg).trim();
  if (['MEMBER_REQUIRED', 'PRIVILEGE_REQUIRED', 'QUOTA_EXCEEDED', 'PACKAGE_REQUIRED'].includes(m)) return m;
  return null;
};

/**
 * 处理对话接口返回的业务错误码，展示弹窗/提示并可选跳转会员页
 * @param {string} code 后端返回的 code
 * @returns {boolean} 是否已处理（true 表示应中止后续逻辑）
 */
const handleChatErrorCode = (code) => {
  if (!code || typeof code !== 'string') return false;
  const c = code.trim();
  if (c === 'MEMBER_REQUIRED') {
    wx.showModal({
      title: '提示',
      content: '此功能需要开通会员，请先升级会员',
      confirmText: '去充值',
      cancelText: '取消',
      success: (res) => {
        if (res.confirm) {
          wx.navigateTo({ url: '/subpackage/pages/mine/vip-buy/vip-buy' });
        }
      },
    });
    return true;
  }
  if (c === 'PRIVILEGE_REQUIRED') {
    wx.showToast({ title: '缺少权益', icon: 'none', duration: 2500 });
    return true;
  }
  if (c === 'QUOTA_EXCEEDED') {
    wx.showToast({ title: '当日额度不足', icon: 'none', duration: 2500 });
    return true;
  }
  if (c === 'PACKAGE_REQUIRED') {
    wx.showToast({ title: '当前套餐不满足要求', icon: 'none', duration: 2500 });
    return true;
  }
  return false;
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

const getFileName = (path, fallback = 'file') => {
  if (!path) {
    return fallback;
  }
  const normalized = path.replace(/\\/g, '/');
  const segments = normalized.split('/');
  return segments[segments.length - 1] || fallback;
};

const isTempPath = (value = '') => /^https?:\/\/tmp\//i.test(value) || /^wxfile:\/\//i.test(value);

const getFilePath = (item = {}) => {
  const candidate =
    item.path ||
    item.url ||
    item.tempFilePath ||
    item.localPath ||
    item.filePath ||
    item.thumbPath ||
    '';
  if (!candidate) {
    return '';
  }
  if (/^https?:\/\//i.test(candidate) && !isTempPath(candidate)) {
    return '';
  }
  return candidate;
};

const getFileExtension = (value = '') => {
  const index = value.lastIndexOf('.');
  if (index < 0) {
    return '';
  }
  return value.slice(index).toLowerCase();
};

const isImageItem = (item, path) => {
  const type = String(item.type || item.fileType || item.mediaType || item.mimeType || '').toLowerCase();
  if (type.startsWith('image') || type === 'image') {
    return true;
  }
  const extension = getFileExtension(path || item.name || item.fileName || '');
  return IMAGE_EXTENSIONS.includes(extension);
};

const getImageMimeType = (value = '') => {
  const extension = getFileExtension(value);
  return IMAGE_MIME_MAP[extension] || 'image/jpeg';
};

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

const buildAttachmentPayloads = (items = []) => {
  if (!items.length) {
    return Promise.resolve({ images: [], files: [], failed: 0 });
  }
  return Promise.all(
    items.map((item) => {
      const path = getFilePath(item);
      if (!path) {
        return Promise.resolve({ skipped: true });
      }
      const filename = item.name || item.fileName || getFileName(path);
      const isImage = isImageItem(item, path);
      const mimeType = isImage ? getImageMimeType(filename || path) : '';
      return readFileAsBase64(path)
        .then((fileBase64) => ({
          filename,
          file_base64: isImage ? `${fileBase64}` : fileBase64,
          isImage,
        }))
        .catch(() => ({ failed: true }));
    })
  ).then((results) => {
    const images = [];
    const files = [];
    let failed = 0;
    results.forEach((result) => {
      if (!result || result.skipped) {
        return;
      }
      if (result.failed) {
        failed += 1;
        return;
      }
      const entry = { filename: result.filename, file_base64: result.file_base64 };
      if (result.isImage) {
        images.push(entry);
      } else {
        files.push(entry);
      }
    });
    return { images, files, failed };
  });
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
  return messages
    .filter((message) => message && message.content != null)
    .slice()
    .reverse()
    .map((message) => {
      const content = [];
      const thinkingText = typeof message.thinking === 'string' ? message.thinking.trim() : '';
      if (thinkingText) {
        content.push({
          type: 'thinking',
          status: 'complete',
          data: {
            title: '思考完成',
            text: thinkingText,
          },
        });
      }
      content.push({
        type: 'markdown',
        data: message.content || '',
      });
      return {
        avatar: message.role === 'assistant' ? ASSISTANT_AVATAR : '',
        datetime: message.timestamp || '',
        message: {
          role: message.role,
          status: 'complete',
          content,
        },
      };
    });
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
    chatList: [], // 初始为空数组，确保欢迎界面先显示
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
    knowledgeBaseVisible: false,
    knowledgeBaseLoading: false,
    knowledgeBaseList: [],
    knowledgeBaseTab: 'system',
    knowledge_base: '',
    placeholder: '请输入消息...',
    textareaProps: {
      autosize: {
        maxHeight: 264,
        minHeight: 48, // 设置为0时，用自动计算height的高度
      }, // 默认为false
    },
    deepThinkActive: false,
    deepThink1Active: false,
    netSearchActive: false,
    showUploadMenu: true,
    showWelcome: true, // 控制欢迎界面显示
    gifKey: Date.now(), // GIF 加载的 key，用于强制重新加载
    gifPlayedOnce: false, // GIF 是否已播放一次
    gifSrc: 'https://tax-dragonai.oss-cn-heyuan.aliyuncs.com/user_files/user_2689ea75e1114ec4/2026/01/agent_peopel_dbfad8a6.gif', // GIF 图片地址
    staticImageSrc: 'https://tax-dragonai.oss-cn-heyuan.aliyuncs.com/user_files/user_2689ea75e1114ec4/2026/01/agent_people_709e5989.png', // 静态图片地址（GIF播放完成后显示）
    gifDuration: 800, // GIF 播放后开始淡出的时间点（毫秒）
    gifFadeOut: false, // GIF 淡出动画控制
    staticFadeIn: false, // 静态图片淡入动画控制
    fadeDuration: 200, // 淡入淡出动画时长（毫秒），超长时间实现无痕切换
    sessionName: '', // 当前会话名称
    // AI万事通高级模式提示
    premiumToastVisible: false,
    premiumToastTimer: null,
    // 快捷问题数据包
    quickQuestions: [
      // 个人常见税务问题
      '个人工资薪金的个人所得税，是如何计算扣除和缴纳的？',
      '年度个人所得税综合所得汇算清缴，哪些人需要办理，哪些人可以不用办理？',
      '个人取得的劳务报酬、稿酬、特许权使用费，怎么预扣预缴个税，年度汇算时又如何并入综合所得计税？',
      '个人出租房屋，需要缴纳哪些税费，有哪些税收优惠政策？',
      '个人转让自有住房，满足什么条件可以免征个人所得税和增值税？',
      '子女教育、赡养老人、住房贷款利息等个税专项附加扣除，申报条件和扣除标准分别是什么？',
      '个人取得的年终奖，选择单独计税还是并入综合所得计税，哪种方式更划算？',
      '灵活就业人员，自行缴纳社保的费用，能否在个税税前扣除？',
      // 企业及个体工商户常见税务问题
      '小规模纳税人与一般纳税人的认定标准是什么，两者在增值税计税、发票开具上有哪些区别？',
      '小微企业能享受哪些企业所得税、增值税的减免优惠政策，享受条件是什么？',
      '企业成本费用税前扣除，需要满足哪些要求，哪些支出不能税前扣除？',
      '增值税专用发票和普通发票，在开具、抵扣、报销上有什么不同？',
      '个体工商户的生产经营所得，个人所得税如何计算，有哪些核定征收和查账征收的规则？',
      '企业逾期申报、逾期缴纳税款，会产生哪些后果，如何处理？',
      '公司没有实际经营、没有收入，是否还需要进行税务申报和年报？',
      '企业收到的财政补贴、政府补助，是否需要缴纳企业所得税和增值税？',
    ],
    quickQuestionList: [], // 随机选择的3个快捷问题
  },

  methods: {
    onKnowledgeBaseClose() {
      this.setData({ knowledgeBaseVisible: false });
    },

    onKnowledgeBaseSelect(e) {
      const name = e.currentTarget.dataset.name;
      if (!name) {
        return;
      }
      this.setData({
        knowledge_base: name,
        deepThinkActive: true,
        knowledgeBaseVisible: false,
      });
    },

    onKnowledgeBaseTabTap(e) {
      const tab = e.currentTarget.dataset.tab;
      if (!tab) {
        return;
      }
      this.setData({
        knowledgeBaseTab: tab,
        knowledgeBaseList: [],
      });
      this.fetchKnowledgeBases(tab);
    },

    fetchKnowledgeBases(tab = this.data.knowledgeBaseTab) {
      const auth = getAuthContext();
      if (!auth) {
        wx.showToast({ title: '请先登录', icon: 'none' });
        return;
      }
      if (this.data.knowledgeBaseLoading) {
        return;
      }
      this.setData({ knowledgeBaseLoading: true });
      const endpoint = tab === 'system' ? '/api/knowledge-base/list/system' : '/api/knowledge-base/list/user';
      wx.request({
        url: `${API_BASE_URL}${endpoint}`,
        method: 'GET',
        header: {
          Authorization: `${auth.tokenType} ${auth.token}`,
        },
        timeout: REQUEST_TIMEOUT_MS,
        success: (res) => {
          const payload = res && res.data ? res.data : {};
          const ok = res.statusCode >= 200 && res.statusCode < 300 && payload.code === 1;
          if (ok) {
            const list = Array.isArray(payload.data) ? payload.data : [];
            const filtered = tab === 'system' ? list.filter((item) => item.is_system !== false) : list.filter((item) => !item.is_system);
            this.setData({ knowledgeBaseList: filtered.length ? filtered : list });
            return;
          }
          wx.showToast({ title: payload.message || '获取知识库失败', icon: 'none' });
        },
        fail: () => {
          wx.showToast({ title: '网络异常，请稍后重试', icon: 'none' });
        },
        complete: () => {
          this.setData({ knowledgeBaseLoading: false });
        },
      });
    },

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
    // 随机选择3个快捷问题
    selectQuickQuestions() {
      const { quickQuestions } = this.data;
      if (!quickQuestions || quickQuestions.length === 0) {
        return;
      }
      
      // 如果问题数量少于等于3个，直接返回所有问题
      if (quickQuestions.length <= 3) {
        this.setData({
          quickQuestionList: quickQuestions
        });
        return;
      }
      
      // 随机选择3个不重复的问题
      const shuffled = [...quickQuestions].sort(() => Math.random() - 0.5);
      const selected = shuffled.slice(0, 3);
      
      this.setData({
        quickQuestionList: selected
      });
    },

    // 点击快捷问题
    onQuickQuestionTap(e) {
      const { question } = e.currentTarget.dataset;
      if (!question || this.data.loading) {
        return;
      }
      
      // 模拟发送消息，直接调用 onSend 的逻辑
      const trimmedValue = question.trim();
      if (!trimmedValue) {
        return;
      }

      const content = [
        {
          type: 'text',
          data: trimmedValue,
        },
      ];

      const userMessage = {
        datetime: formatTime(new Date()),
        message: {
          role: 'user',
          status: 'complete',
          content,
        },
      };

      this.setData({
        chatList: [userMessage, ...this.data.chatList],
        value: '',
        showWelcome: false, // 隐藏欢迎界面
      });

      this.sendMessage(trimmedValue, []);
    },

    onSend(e) {
      const { value } = e.detail;
      const trimmedValue = value ? value.trim() : '';
      const currentAttachments = this.data.attachmentsProps.items || [];
      const uploadItems = this.data.fileList && this.data.fileList.length ? this.data.fileList : currentAttachments;
      if ((!trimmedValue && !uploadItems.length) || this.data.loading) return;

      const content = [
        {
          type: 'text',
          data: trimmedValue,
        },
      ];
      const attachments = currentAttachments.map((item) => {
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

      // 显示高级模式提示
      this.showPremiumToast();

      this.sendMessage(trimmedValue, uploadItems);
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

    onFocus() {
      // 当输入框获取焦点时，隐藏欢迎界面
      if (this.data.showWelcome) {
        this.setData({ showWelcome: false });
      }
    },

    // 启动 GIF 播放定时器
    startGifTimer() {
      // 清理之前的定时器
      if (this.gifTimer) {
        clearTimeout(this.gifTimer);
        this.gifTimer = null;
      }
      if (this.fadeTimer) {
        clearTimeout(this.fadeTimer);
        this.fadeTimer = null;
      }
      
      // 如果已经播放过，不再启动定时器
      if (this.data.gifPlayedOnce) {
        return;
      }
      
      console.log('Starting GIF timer, will switch to static image after', this.data.gifDuration, 'ms');
      
      // 设置定时器，在 GIF 播放完一次后开始淡入淡出切换
      this.gifTimer = setTimeout(() => {
        console.log('GIF playback completed, starting fade transition');
        // 触发淡入淡出动画
        this.setData({ 
          gifFadeOut: true, // GIF 开始淡出
          staticFadeIn: true, // 静态图片开始淡入
        });
        
        // 等待淡入淡出动画完成后，移除 GIF 元素
        this.fadeTimer = setTimeout(() => {
          console.log('Fade transition completed, removing GIF element');
          this.setData({ 
            gifPlayedOnce: true, // 标记为已播放，移除 GIF 元素
          });
          // 清理定时器
          if (this.fadeTimer) {
            clearTimeout(this.fadeTimer);
            this.fadeTimer = null;
          }
        }, this.data.fadeDuration); // 等待淡入淡出动画完成
        
        // 清理 GIF 定时器
        if (this.gifTimer) {
          clearTimeout(this.gifTimer);
          this.gifTimer = null;
        }
      }, this.data.gifDuration); // 1.67秒后开始切换
    },

    onGifLoad() {
      // GIF 加载成功
      console.log('GIF loaded');
    },

    onGifError(e) {
      // GIF 加载失败时的处理
      console.error('GIF load error:', e);
    },

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

    sendMessage(message, attachments = []) {
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
      let thinkingText = '';
      let streamErrorHandled = false;

      const requestWithAttachments = (images, files) => {
        const requestData = {
          session_id: sessionId,
          user_id: auth.userId,
          message: message || '',
          images,
          files,
          enable_search: this.data.netSearchActive,
          enable_rag: true,
        };
        if (this.data.knowledge_base) {
          requestData.knowledge_base = this.data.knowledge_base;
        }
        const endpoint = this.data.deepThink1Active ? '/api/chat/supervisor' : '/api/chat/full-feature';
        this.requestTask = wx.request({
          url: `${API_BASE_URL}${endpoint}`,
          method: 'POST',
          header: {
            'content-type': 'application/json',
            Authorization: `${auth.tokenType} ${auth.token}`,
          },
          data: requestData,
          enableChunked: true,
          responseType: 'arraybuffer',
          timeout: REQUEST_TIMEOUT_MS,
          success: (res) => {
            const statusOk = res && res.statusCode >= 200 && res.statusCode < 300;
            if (res && res.data !== undefined && res.data !== null) {
              let parsed = null;
              if (typeof res.data === 'object' && !(res.data instanceof ArrayBuffer)) {
                parsed = res.data;
              } else {
                const chunkText = typeof res.data === 'string' ? res.data : arrayBufferToString(res.data);
                if (chunkText) {
                  try {
                    parsed = JSON.parse(chunkText.trim());
                  } catch (e) {
                    parsed = null;
                  }
                  if (!parsed && chunkText) {
                    if (statusOk && !streamErrorHandled) {
                      handleChunk(chunkText);
                    }
                  }
                }
              }
              if (parsed && typeof parsed === 'object') {
                const errCode = getResponseErrorCode(parsed);
                if (errCode && handleChatErrorCode(errCode)) {
                  streamErrorHandled = true;
                  removeEmptyAssistantReply();
                  this.setData({ loading: false, disabled: false });
                  if (this.requestTask && typeof this.requestTask.abort === 'function') {
                    this.requestTask.abort();
                  }
                  return;
                }
                if (statusOk && !streamErrorHandled) {
                  const chunkText = typeof res.data === 'string' ? res.data : (res.data instanceof ArrayBuffer ? arrayBufferToString(res.data) : '');
                  if (chunkText) handleChunk(chunkText);
                }
              }
            }
            if (this.data.loading && !streamErrorHandled) {
              updateAssistant('complete');
              this.setData({ loading: false, disabled: false });
            }
          },
          fail: () => {
            if (streamErrorHandled) return;
            updateAssistant('error');
            this.setData({ loading: false, disabled: false });
            wx.showToast({ title: '网络异常，请稍后重试', icon: 'none' });
          },
        });

        const processChunk = (chunkText) => {
          if (!chunkText || streamErrorHandled) return;
          const trimmed = chunkText.trim();
          if (trimmed.startsWith('{')) {
            try {
              const parsed = JSON.parse(trimmed);
              const errCode = getResponseErrorCode(parsed);
              if (errCode && handleChatErrorCode(errCode)) {
                streamErrorHandled = true;
                removeEmptyAssistantReply();
                this.setData({ loading: false, disabled: false });
                if (this.requestTask && typeof this.requestTask.abort === 'function') {
                  this.requestTask.abort();
                }
                return;
              }
            } catch (e) { /* 非完整 JSON，继续按行解析 */ }
          }
          handleChunk(chunkText);
        };

        if (this.requestTask && typeof this.requestTask.onChunkReceived === 'function') {
          this.requestTask.onChunkReceived((response) => {
            const chunkText = arrayBufferToString(response && response.data);
            if (chunkText) processChunk(chunkText);
          });
        } else if (this.requestTask && typeof this.requestTask.onChunkedData === 'function') {
          this.requestTask.onChunkedData((response) => {
            const chunkText = arrayBufferToString(response && response.data);
            if (chunkText) processChunk(chunkText);
          });
        }
      };

      /** 移除列表顶部无内容的助手占位（如因错误未产生回复时），避免渲染空气泡 */
      const removeEmptyAssistantReply = () => {
        const chatList = this.data.chatList.slice();
        if (!chatList.length || chatList[0].message.role !== 'assistant') return;
        const content = chatList[0].message.content || [];
        const markdownItem = content.find((c) => c && c.type === 'markdown');
        const hasText = markdownItem && markdownItem.data && String(markdownItem.data).trim();
        if (!hasText) {
          chatList.shift();
          this.setData({ chatList });
        }
      };

      const updateAssistant = (status) => {
        const chatList = this.data.chatList.slice();
        if (!chatList.length) {
          return;
        }
        const contentItems = Array.isArray(chatList[0].message.content) ? chatList[0].message.content : [];
        let markdownItem = contentItems.find((item) => item && item.type === 'markdown');
        if (!markdownItem) {
          markdownItem = { type: 'markdown', data: '' };
          contentItems.push(markdownItem);
        }
        markdownItem.data = assistantText;
        if (thinkingText) {
          let thinkingItem = contentItems.find((item) => item && item.type === 'thinking');
          if (!thinkingItem) {
            thinkingItem = {
              type: 'thinking',
              status: 'complete',
              data: {
                title: '思考中',
                text: '',
              },
            };
            contentItems.unshift(thinkingItem);
          }
          if (!thinkingItem.data) {
            thinkingItem.data = { title: '思考中', text: '' };
          }
          thinkingItem.data.text = thinkingText;
          if (status === 'complete' || status === 'error') {
            thinkingItem.data.title = '思考完成';
          } else {
            thinkingItem.data.title = '思考中';
          }
        }
        chatList[0].message.content = contentItems;
        if (status) {
          chatList[0].message.status = status;
        }
        this.setData({ chatList });
      };

      const handleChunk = (chunkText) => {
        if (streamErrorHandled) return;
        buffer += chunkText;
        const lines = buffer.split(/\r?\n/);
        buffer = lines.pop() || '';
        lines.forEach((line) => {
          if (streamErrorHandled) return;
          const trimmed = line.trim();
          if (!trimmed) return;
          let raw = '';
          if (trimmed.startsWith('data:')) {
            raw = trimmed.replace(/^data:\s*/, '');
          } else if (trimmed.startsWith('{')) {
            raw = trimmed;
          }
          if (!raw) return;
          let payload;
          try {
            payload = JSON.parse(raw);
          } catch (error) {
            return;
          }
          const errCode = getResponseErrorCode(payload);
          if (errCode && handleChatErrorCode(errCode)) {
            streamErrorHandled = true;
            removeEmptyAssistantReply();
            this.setData({ loading: false, disabled: false });
            if (this.requestTask && typeof this.requestTask.abort === 'function') {
              this.requestTask.abort();
            }
            return;
          }
          if (payload.type === 'thinking') {
            thinkingText += payload.content || '';
            updateAssistant('streaming');
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

      if (!attachments.length) {
        requestWithAttachments([], []);
        return;
      }

      buildAttachmentPayloads(attachments)
        .then(({ images, files, failed }) => {
          if (failed) {
            wx.showToast({ title: '部分文件读取失败', icon: 'none' });
          }
          requestWithAttachments(images, files);
        })
        .catch(() => {
          wx.showToast({ title: '附件处理失败', icon: 'none' });
          requestWithAttachments([], []);
        });
    },

    loadHistory(sessionId) {
      const auth = getAuthContext();
      if (!auth || !sessionId || this.data.historyLoading) {
        return;
      }

      this.setData({ historyLoading: true });

      wx.request({
        url: `${API_BASE_URL}/api/chat/sessions/${sessionId}/messages?user_id=${encodeURIComponent(auth.userId)}`,
        method: 'GET',
        header: {
          Authorization: `${auth.tokenType} ${auth.token}`,
        },
        timeout: REQUEST_TIMEOUT_MS,
        success: (res) => {
          const payload = res && res.data ? res.data : {};
          const ok = res.statusCode >= 200 && res.statusCode < 300 && payload.code === 1 && payload.data;
          if (ok) {
            const messages = payload.data.messages || [];
            const sessionName = payload.data.name || '';
            
            // 检查是否应该显示欢迎界面
            const shouldShowWelcome = messages.length === 0 || sessionName === '新建会话';
            
            if (!shouldShowWelcome && messages.length) {
              // 有消息且不是新建会话，显示聊天记录
              const mapped = mapHistoryMessages(messages);
              this.setData({ 
                chatList: mapped, 
                historyLoaded: true, 
                showWelcome: false,
                sessionName: sessionName 
              });
              return;
            }
            // 如果消息为空或是新建会话，显示欢迎界面
            console.log('显示欢迎界面 - 会话名称:', sessionName, ', 消息数量:', messages.length);
            // 重置 GIF 状态，强制 GIF 重新加载
            this.setData({
              chatList: [],
              historyLoaded: true,
              showWelcome: true,
              sessionName: sessionName,
              gifKey: Date.now(), // 强制 GIF 重新加载
              gifPlayedOnce: false, // 重置播放状态
              gifFadeOut: false, // 重置淡出状态
              staticFadeIn: false, // 重置淡入状态
              gifSrc: 'https://tax-dragonai.oss-cn-heyuan.aliyuncs.com/user_files/user_2689ea75e1114ec4/2026/01/agent_peopel_dbfad8a6.gif', // 重置为GIF源
            });
            // 随机选择快捷问题
            this.selectQuickQuestions();
            // 启动 GIF 定时器
            this.startGifTimer();
            return;
          }
          // 加载失败时，显示欢迎界面
          this.setData({
            chatList: [],
            historyLoaded: true,
            showWelcome: true,
            gifKey: Date.now(),
            gifPlayedOnce: false,
            gifFadeOut: false,
            staticFadeIn: false,
            gifSrc: 'https://tax-dragonai.oss-cn-heyuan.aliyuncs.com/user_files/user_2689ea75e1114ec4/2026/01/agent_peopel_dbfad8a6.gif',
          });
          this.selectQuickQuestions();
          this.startGifTimer();
          wx.showToast({ title: payload.message || '获取历史消息失败', icon: 'none' });
        },
        fail: () => {
          // 网络失败时，显示欢迎界面
          this.setData({
            chatList: [],
            historyLoaded: true,
            showWelcome: true,
            gifKey: Date.now(),
            gifPlayedOnce: false,
            gifFadeOut: false,
            staticFadeIn: false,
            gifSrc: 'https://tax-dragonai.oss-cn-heyuan.aliyuncs.com/user_files/user_2689ea75e1114ec4/2026/01/agent_peopel_dbfad8a6.gif',
          });
          this.selectQuickQuestions();
          this.startGifTimer();
          wx.showToast({ title: '网络异常，请稍后重试', icon: 'none' });
        },
        complete: () => {
          this.setData({ historyLoading: false });
        },
      });
    },

    onDeepThinkTap() {
      if (this.data.deepThinkActive) {
        this.setData({
          deepThinkActive: false,
          knowledge_base: '',
          knowledgeBaseVisible: false,
        });
        return;
      }
      this.setData({ knowledgeBaseVisible: true });
      this.fetchKnowledgeBases(this.data.knowledgeBaseTab);
    },
  
    onNetSearchTap() {
      this.setData({ netSearchActive: !this.data.netSearchActive });
    },

    onDeepThinkTap1() {
      this.setData({ deepThink1Active: !this.data.deepThink1Active });
    },

    refreshSession() {
      const sessionId = getSessionId();
      if (!sessionId) {
        return;
      }
      const shouldReload = sessionId !== this.data.sessionId || !this.data.historyLoaded;
      this.setData({ sessionId });
      if (shouldReload) {
        // 加载历史消息，在加载完成后根据结果决定是否显示欢迎页
        this.loadHistory(sessionId);
      }
    },

    // 显示高级模式提示
    showPremiumToast() {
      // 清除之前的定时器
      if (this.data.premiumToastTimer) {
        clearTimeout(this.data.premiumToastTimer);
      }
      // 显示提示
      this.setData({ premiumToastVisible: true });
      // 2秒后自动隐藏
      const timer = setTimeout(() => {
        this.setData({ premiumToastVisible: false });
      }, 2000);
      this.setData({ premiumToastTimer: timer });
    },
  },
  lifetimes: {
    attached: function () {
      // 初始化状态，不显示欢迎界面，等待加载历史消息后再决定
      this.setData({
        showWelcome: false,
        chatList: [],
        historyLoaded: false,
      });
      // 随机选择快捷问题（预先准备好）
      this.selectQuickQuestions();
      // 刷新会话并加载历史消息
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
    detached: function () {
      // 组件销毁时清理定时器
      if (this.gifTimer) {
        clearTimeout(this.gifTimer);
        this.gifTimer = null;
      }
      if (this.fadeTimer) {
        clearTimeout(this.fadeTimer);
        this.fadeTimer = null;
      }
    },
  },
  pageLifetimes: {
    show: function () {
      // 每次页面显示时，刷新会话并加载历史消息
      // loadHistory 会根据结果决定是否显示欢迎页
      this.refreshSession();
    },
  },
});
