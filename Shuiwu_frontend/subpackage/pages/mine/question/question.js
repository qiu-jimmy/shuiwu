// pages/mine/question/question.js
import { API_BASE_URL } from '../../../../utils/config';

const QUESTION_TYPES = [
  { value: '功能建议', label: '功能建议' },
  { value: '功能异常', label: '功能异常' },
  { value: '数据问题', label: '数据问题' },
  { value: '账号问题', label: '账号问题' },
  { value: '其他', label: '其他' },
];

const STATUS_FILTERS = [
  { value: 'all', label: '全部' },
  { value: 'pending', label: '待处理' },
  { value: 'processing', label: '处理中' },
  { value: 'resolved', label: '已解决' },
  { value: 'closed', label: '已关闭' },
];

const STATUS_MAP = {
  pending: { label: '待处理', theme: 'warning' },
  processing: { label: '处理中', theme: 'warning' },
  resolved: { label: '已解决', theme: 'success' },
  closed: { label: '已关闭', theme: 'default' },
};

const FEEDBACK_ENDPOINTS = {
  submit: '/api/feedback/submit',
  list: '/api/feedback/my',
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

const formatDateTime = (value) => {
  if (!value) {
    return '-';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  const pad = (num) => (num < 10 ? `0${num}` : `${num}`);
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(
    date.getHours()
  )}:${pad(date.getMinutes())}`;
};

const getStatusMeta = (status) =>
  STATUS_MAP[status] || { label: status || '处理中', theme: 'default' };

const extractList = (data) => {
  if (Array.isArray(data)) {
    return data;
  }
  if (!data) {
    return [];
  }
  return (
    data.items ||
    data.list ||
    data.questions ||
    data.records ||
    data.rows ||
    data.feedbacks ||
    []
  );
};

const extractTotal = (data) => {
  if (!data || Array.isArray(data)) {
    return null;
  }
  return (
    data.total ||
    data.count ||
    data.total_count ||
    data.totalCount ||
    data.total_items ||
    null
  );
};

const normalizeQuestion = (item) => {
  const typeValue =
    item.feedback_type ||
    item.type ||
    item.question_type ||
    item.category ||
    item.category_type ||
    '其他';
  const statusValue = item.status || item.state || item.process_status;
  const statusMeta = getStatusMeta(statusValue);
  const content =
    item.feedback_content ||
    item.description ||
    item.content ||
    item.detail ||
    item.question_desc ||
    '';
  const adminReply = item.admin_reply || item.reply || item.reply_content || '';
  const repliedAt = item.replied_at || item.reply_time || item.repliedAt;
  const createdAt =
    item.created_at ||
    item.createdAt ||
    item.created_time ||
    item.create_time ||
    item.created ||
    item.time;
  return {
    ...item,
    typeLabel: item.type_label || item.typeLabel || typeValue,
    content,
    adminReply,
    repliedLabel: repliedAt ? formatDateTime(repliedAt) : '',
    statusLabel: item.status_label || item.statusLabel || statusMeta.label,
    statusTheme: item.status_theme || item.statusTheme || statusMeta.theme,
    createdLabel: formatDateTime(createdAt),
  };
};

Page({
  data: {
    questionTypes: QUESTION_TYPES,
    selectedType: QUESTION_TYPES[0].value,
    selectedTypeLabel: QUESTION_TYPES[0].label,
    typePickerVisible: false,
    typePickerValue: [QUESTION_TYPES[0].value],
    activeStatus: STATUS_FILTERS[0].value,
    description: '',
    submitting: false,
    submitDisabled: true,
    questions: [],
    listLoading: false,
    page: 1,
    pageSize: 20,
    hasMore: true,
  },

  onLoad() {
    this.fetchQuestions({ refresh: true });
  },

  onShow() {
    if (this.data.questions.length) {
      this.fetchQuestions({ refresh: true });
    }
  },

  onPullDownRefresh() {
    this.fetchQuestions({
      refresh: true,
      done: () => {
        wx.stopPullDownRefresh();
      },
    });
  },

  onReachBottom() {
    if (this.data.hasMore && !this.data.listLoading) {
      this.fetchQuestions({ refresh: false });
    }
  },

  onStatusChange(e) {
    const value = e && e.detail && e.detail.value ? e.detail.value : 'all';
    if (value === this.data.activeStatus) {
      return;
    }
    this.setData({
      activeStatus: value,
      questions: [],
      page: 1,
      hasMore: true,
    });
    this.fetchQuestions({ refresh: true });
  },

  onTypePickerOpen() {
    this.setData({
      typePickerVisible: true,
      typePickerValue: [this.data.selectedType],
    });
  },

  onTypePickerConfirm(e) {
    const detail = e && e.detail ? e.detail : {};
    const values = Array.isArray(detail.value) ? detail.value : [detail.value];
    const selected = values[0] || QUESTION_TYPES[0].value;
    const exists = QUESTION_TYPES.find((item) => item.value === selected);
    const nextType = exists ? selected : QUESTION_TYPES[0].value;
    const nextLabel = exists ? exists.label : QUESTION_TYPES[0].label;
    this.setData({
      selectedType: nextType,
      selectedTypeLabel: nextLabel,
      typePickerVisible: false,
      typePickerValue: [nextType],
    });
    this.updateSubmitState({ selectedType: nextType });
  },

  onTypePickerCancel() {
    this.setData({ typePickerVisible: false });
  },

  onTypePickerClose() {
    this.setData({ typePickerVisible: false });
  },

  onDescriptionChange(e) {
    const detail = e && e.detail ? e.detail : {};
    const value = detail.value != null ? detail.value : '';
    this.setData({ description: value });
    this.updateSubmitState({ description: value });
  },

  updateSubmitState(override = {}) {
    const selectedType =
      Object.prototype.hasOwnProperty.call(override, 'selectedType')
        ? override.selectedType
        : this.data.selectedType;
    const description =
      Object.prototype.hasOwnProperty.call(override, 'description')
        ? override.description
        : this.data.description;
    const disabled = !selectedType || !String(description || '').trim();
    if (disabled !== this.data.submitDisabled) {
      this.setData({ submitDisabled: disabled });
    }
  },

  onSubmit() {
    if (this.data.submitting) {
      return;
    }
    const type = this.data.selectedType;
    const description = String(this.data.description || '').trim();
    if (!type) {
      wx.showToast({ title: '请选择问题类型', icon: 'none' });
      return;
    }
    if (!description) {
      wx.showToast({ title: '请填写问题说明', icon: 'none' });
      return;
    }
    const authHeader = getAuthHeader();
    if (!authHeader) {
      wx.showToast({ title: '请先登录', icon: 'none' });
      return;
    }
    this.setData({ submitting: true });
    wx.request({
      url: `${API_BASE_URL}${FEEDBACK_ENDPOINTS.submit}`,
      method: 'POST',
      header: {
        Authorization: authHeader,
        'content-type': 'application/json',
      },
      data: {
        feedback_type: type,
        feedback_content: description,
      },
      success: (res) => {
        const payload = res && res.data ? res.data : {};
        const ok =
          res.statusCode >= 200 &&
          res.statusCode < 300 &&
          (payload.code === 1 || payload.success === true || payload.code === 0);
        if (ok) {
          wx.showToast({ title: payload.message || '提交成功', icon: 'success' });
          this.setData({ description: '' });
          this.updateSubmitState({ description: '' });
          this.fetchQuestions({ refresh: true });
          return;
        }
        wx.showToast({ title: payload.message || '提交失败', icon: 'none' });
      },
      fail: () => {
        wx.showToast({ title: '网络异常，请稍后重试', icon: 'none' });
      },
      complete: () => {
        this.setData({ submitting: false });
      },
    });
  },

  fetchQuestions({ refresh, done } = {}) {
    const authHeader = getAuthHeader();
    if (!authHeader) {
      wx.showToast({ title: '请先登录', icon: 'none' });
      if (typeof done === 'function') done();
      return;
    }
    const page = refresh ? 1 : this.data.page;
    if (this.data.listLoading) {
      if (typeof done === 'function') done();
      return;
    }
    this.setData({ listLoading: true });
    const queryParts = [`page=${page}`, `page_size=${this.data.pageSize}`];
    if (this.data.activeStatus && this.data.activeStatus !== 'all') {
      queryParts.push(`status=${encodeURIComponent(this.data.activeStatus)}`);
    }
    const query = queryParts.join('&');
    wx.request({
      url: `${API_BASE_URL}${FEEDBACK_ENDPOINTS.list}?${query}`,
      method: 'GET',
      header: {
        Authorization: authHeader,
      },
      success: (res) => {
        const payload = res && res.data ? res.data : {};
        const payloadData = payload.data != null ? payload.data : {};
        const list = Array.isArray(payloadData.feedbacks)
          ? payloadData.feedbacks
          : extractList(payloadData);
        const canUseList = Array.isArray(list);
        const ok =
          res.statusCode >= 200 &&
          res.statusCode < 300 &&
          (payload.code === 1 || payload.success === true || payload.code === 0 || canUseList);
        if (ok && canUseList) {
          const normalized = list.map(normalizeQuestion);
          const nextList = refresh ? normalized : this.data.questions.concat(normalized);
          const total = extractTotal(payloadData);
          const hasMore =
            typeof total === 'number'
              ? nextList.length < total
              : normalized.length >= this.data.pageSize;
          this.setData({
            questions: nextList,
            page: page + 1,
            hasMore,
          });
          return;
        }
        wx.showToast({ title: payload.message || '获取问题列表失败', icon: 'none' });
      },
      fail: () => {
        wx.showToast({ title: '网络异常，请稍后重试', icon: 'none' });
      },
      complete: () => {
        this.setData({ listLoading: false });
        if (typeof done === 'function') done();
      },
    });
  },
});
