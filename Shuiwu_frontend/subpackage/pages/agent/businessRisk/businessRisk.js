/**
 * businessRisk.js — 经营风险报告页面逻辑
 *
 * 功能：
 *   - 用户输入企业名称 + 纳税人识别号
 *   - 调用后端 /api/chashuibao/authorization 获取 H5 授权链接
 *   - 跳转到 taxAuthWebview 页让用户完成税局授权
 *   - 授权完成返回后，轮询 /api/chashuibao/business-risk/status/:orderNo 获取报告状态
 *   - 报告生成成功后展示预览/复制按钮
 */
import { API_BASE_URL } from '../../../../utils/config';

const POLL_INTERVAL_MS = 5000;
const POLL_TIMEOUT_MS = 10 * 60 * 1000;

const STATUS_TEXT_MAP = {
  pending: '生成中',
  success: '生成成功',
  failed: '生成失败',
};

const buildQuarterOptions = () => {
  const now = new Date();
  const currentYear = now.getFullYear();
  const yearGroups = [];
  for (let year = currentYear; year >= currentYear - 4; year -= 1) {
    const quarters = [];
    for (let quarter = 1; quarter <= 4; quarter += 1) {
      quarters.push({
        year: String(year),
        quarter: String(quarter),
        label: `Q${quarter}`,
        key: `${year}-${quarter}`,
        selected: false,
      });
    }
    yearGroups.push({ year: String(year), quarters });
  }
  return yearGroups;
};

const getDefaultQuarterSelection = (yearGroups = []) => {
  const now = new Date();
  const currentYear = String(now.getFullYear());
  const currentQuarter = String(Math.floor(now.getMonth() / 3) + 1);
  const defaultKey = `${currentYear}-${currentQuarter}`;
  const updated = yearGroups.map((group) => ({
    ...group,
    quarters: group.quarters.map((item) => ({
      ...item,
      selected: item.key === defaultKey,
    })),
  }));
  return {
    yearGroups: updated,
    selectedQuarterLabel: getSelectedLabel(updated),
  };
};

const getSelectedLabel = (yearGroups = []) => {
  const selected = [];
  yearGroups.forEach((group) => {
    group.quarters.forEach((item) => {
      if (item.selected) selected.push(`${item.year}年Q${item.quarter}`);
    });
  });
  return selected.join('、');
};

const getSelectedQuarterSection = (yearGroups = []) => {
  const result = [];
  yearGroups.forEach((group) => {
    group.quarters.forEach((item) => {
      if (item.selected) result.push({ year: item.year, quarter: item.quarter });
    });
  });
  return result;
};

const getAuthContext = () => {
  const userInfo = wx.getStorageSync('user_info');
  const userId = userInfo && userInfo.user_id ? userInfo.user_id : '';
  const token = wx.getStorageSync('access_token');
  if (!userId || !token) return null;
  const tokenType = String(wx.getStorageSync('token_type') || 'bearer');
  const normalizedType = tokenType.toLowerCase() === 'bearer' ? 'Bearer' : tokenType;
  return { userId, token, tokenType: normalizedType };
};

const buildQuery = (params = {}) =>
  Object.keys(params)
    .filter((k) => params[k] !== undefined && params[k] !== null && params[k] !== '')
    .map((k) => `${encodeURIComponent(k)}=${encodeURIComponent(params[k])}`)
    .join('&');

const normalizeStatus = (s = '') => String(s || '').toLowerCase();
const getStatusText = (s = '') => STATUS_TEXT_MAP[normalizeStatus(s)] || String(s || '--');
const getStatusClass = (s = '') => {
  const n = normalizeStatus(s);
  if (n === 'pending' || n === 'success' || n === 'failed') return n;
  return n ? 'unknown' : 'idle';
};
const normalizeListItem = (item = {}) => ({
  ...item,
  statusText: getStatusText(item.status),
  statusClass: getStatusClass(item.status),
});
const createError = (message, code) => {
  const e = new Error(message);
  e.code = code;
  return e;
};

Page({
  data: {
    // 表单输入
    taxpayerName: '',
    taxpayerNo: '',
    yearGroups: [],
    selectedQuarterLabel: '',
    quarterExpanded: false,

    // 授权流程状态
    fetchingAuth: false,
    authFetched: false,
    orderNo: '',
    initialUrl: '',

    // 轮询
    polling: false,

    // 当前报告状态
    currentStatus: '',
    currentStatusText: '未开始',
    currentStatusInfo: null,
    reportUrl: '',

    // 历史列表
    statusTabs: [
      { value: '', label: '全部' },
      { value: 'pending', label: '生成中' },
      { value: 'success', label: '成功' },
      { value: 'failed', label: '失败' },
    ],
    statusFilter: '',
    reports: [],
    page: 1,
    pageSize: 20,
    total: 0,
    hasMore: false,
    listLoading: false,
    loadingMore: false,
  },

  onLoad(options) {
    this.pollTimer = null;
    this.pollStartAt = 0;
    this.setData(getDefaultQuarterSelection(buildQuarterOptions()));
    // 从 taxAuthWebview 回调跳转过来时携带 orderNo
    if (options && options.orderNo) {
      const orderNo = decodeURIComponent(options.orderNo);
      this.setData({
        orderNo,
        authFetched: true,
        currentStatus: 'pending',
        currentStatusText: '授权完成，生成中',
      });
      this.startPolling(orderNo);
    }
    this.loadReportList(true, false);
  },

  onShow() {
    if (
      this.data.orderNo &&
      normalizeStatus(this.data.currentStatus) === 'pending' &&
      !this.data.polling
    ) {
      this.startPolling(this.data.orderNo);
    }
  },

  onHide() { this.stopPolling(); },
  onUnload() { this.stopPolling(); },

  onPullDownRefresh() {
    this.loadReportList(true, false).finally(() => wx.stopPullDownRefresh());
  },

  onTaxpayerNameInput(e) { this.setData({ taxpayerName: e.detail.value || '' }); },
  onTaxpayerNoInput(e) { this.setData({ taxpayerNo: e.detail.value || '' }); },
  onToggleQuarterExpand() { this.setData({ quarterExpanded: !this.data.quarterExpanded }); },
  onQuarterToggle(e) {
    const key = e.currentTarget.dataset.key;
    const yearGroups = this.data.yearGroups.map((group) => ({
      ...group,
      quarters: group.quarters.map((item) => ({
        ...item,
        selected: item.key === key ? !item.selected : item.selected,
      })),
    }));
    this.setData({ yearGroups, selectedQuarterLabel: getSelectedLabel(yearGroups) });
  },

  onStatusFilterTap(e) {
    const status = e.currentTarget.dataset.status || '';
    if (status === this.data.statusFilter) return;
    this.setData({ statusFilter: status });
    this.loadReportList(true, true);
  },
  onRefreshList() { this.loadReportList(true, true); },
  onLoadMore() { this.loadReportList(false, true); },

  // ——— 获取授权链接（经营风险报告使用 /api/chashuibao/authorization）———
  onGetAuthUrl() {
    if (this.data.fetchingAuth) return;

    const taxpayerName = String(this.data.taxpayerName || '').trim();
    const taxpayerNo = String(this.data.taxpayerNo || '').trim();
    const quarterSection = getSelectedQuarterSection(this.data.yearGroups);

    if (!taxpayerName) { wx.showToast({ title: '请输入企业名称', icon: 'none' }); return; }
    if (!taxpayerNo) { wx.showToast({ title: '请输入纳税人识别号', icon: 'none' }); return; }
    if (!quarterSection.length) { wx.showToast({ title: '请至少选择一个季度', icon: 'none' }); return; }

    const auth = this.ensureAuth(true);
    if (!auth) return;

    this.stopPolling();
    this.setData({
      fetchingAuth: true,
      orderNo: '',
      initialUrl: '',
      authFetched: false,
      currentStatus: '',
      currentStatusText: '未开始',
      currentStatusInfo: null,
      reportUrl: '',
    });

    wx.showLoading({ title: '获取中' });

    const cburl = `${API_BASE_URL}/h5/business-callback`;

    this.requestWithAuth(auth, {
      url: `${API_BASE_URL}/api/chashuibao/authorization`,
      method: 'POST',
      data: {
        taxpayerId: taxpayerNo,
        companyName: taxpayerName,
        reportType: '2',
        cburl,
        quarterSection,
      },
      timeout: 60000,
    })
      .then(({ ok, payload }) => {
        if (!ok || !payload.data) throw new Error(payload.message || '获取授权链接失败');
        const { orderNo, initialUrl } = payload.data;
        this.setData({
          orderNo: orderNo || '',
          initialUrl: initialUrl || '',
          authFetched: true,
          currentStatus: 'pending',
          currentStatusText: '等待授权',
        });
        wx.showToast({ title: '获取成功，请前往授权', icon: 'none' });
      })
      .catch((err) => {
        wx.showToast({ title: err.message || '获取授权链接失败', icon: 'none' });
      })
      .finally(() => {
        this.setData({ fetchingAuth: false });
        wx.hideLoading();
      });
  },

  onGoAuthorize() {
    const { initialUrl, orderNo } = this.data;
    if (!initialUrl) { wx.showToast({ title: '授权链接不存在', icon: 'none' }); return; }
    wx.navigateTo({
      url: `/subpackage/pages/agent/taxAuthWebview/taxAuthWebview?url=${encodeURIComponent(initialUrl)}&orderNo=${encodeURIComponent(orderNo)}&returnPage=businessRisk`,
    });
  },

  onResetAuth() {
    this.stopPolling();
    this.setData({
      authFetched: false,
      orderNo: '',
      initialUrl: '',
      currentStatus: '',
      currentStatusText: '未开始',
      currentStatusInfo: null,
      reportUrl: '',
    });
  },

  onRefreshStatus() {
    const { orderNo } = this.data;
    if (!orderNo) { wx.showToast({ title: '暂无订单可查询', icon: 'none' }); return; }
    this.fetchStatus(orderNo, true)
      .then((info) => {
        this.updateCurrentStatus(info);
        if (normalizeStatus(info.status) === 'pending') this.startPolling(orderNo);
      })
      .catch(() => {});
  },

  startPolling(orderNo) {
    if (!orderNo) return;
    this.stopPolling();
    this.pollStartAt = Date.now();
    this.setData({
      polling: true,
      currentStatus: 'pending',
      currentStatusText: getStatusText('pending'),
    });
    this.pollStatus(orderNo);
  },

  stopPolling() {
    if (this.pollTimer) { clearTimeout(this.pollTimer); this.pollTimer = null; }
    if (this.data.polling) this.setData({ polling: false });
  },

  pollStatus(orderNo) {
    const elapsed = Date.now() - (this.pollStartAt || Date.now());
    if (elapsed >= POLL_TIMEOUT_MS) {
      this.stopPolling();
      this.setData({ currentStatus: 'failed', currentStatusText: '生成超时' });
      wx.showToast({ title: '生成超时，请重试', icon: 'none' });
      return;
    }
    this.fetchStatus(orderNo, false)
      .then((info) => {
        this.updateCurrentStatus(info);
        const status = normalizeStatus(info.status);
        if (status === 'pending') { this.scheduleNextPoll(orderNo); return; }
        this.stopPolling();
        this.loadReportList(true, false);
        if (status === 'success') wx.showToast({ title: '报告生成成功', icon: 'success' });
        else if (status === 'failed') wx.showToast({ title: '报告生成失败', icon: 'none' });
      })
      .catch((err) => {
        if (err && err.code === 'NO_AUTH') { this.stopPolling(); return; }
        this.scheduleNextPoll(orderNo);
      });
  },

  scheduleNextPoll(orderNo) {
    this.pollTimer = setTimeout(() => this.pollStatus(orderNo), POLL_INTERVAL_MS);
  },

  fetchStatus(orderNo, showError = false) {
    const auth = this.ensureAuth(showError);
    if (!auth) return Promise.reject(createError('请先登录', 'NO_AUTH'));
    return this.requestWithAuth(auth, {
      url: `${API_BASE_URL}/api/chashuibao/business-risk/status/${encodeURIComponent(orderNo)}`,
      method: 'GET',
    })
      .then(({ ok, payload }) => {
        if (!ok || !payload.data) throw new Error(payload.message || '获取状态失败');
        return payload.data;
      })
      .catch((err) => {
        if (showError && err.code !== 'NO_AUTH') wx.showToast({ title: err.message || '获取状态失败', icon: 'none' });
        throw err;
      });
  },

  loadReportList(reset = true, showAuthTip = false) {
    if (reset && this.data.listLoading) return Promise.resolve();
    if (!reset && (this.data.loadingMore || !this.data.hasMore)) return Promise.resolve();

    const auth = this.ensureAuth(showAuthTip);
    if (!auth) {
      if (reset) this.setData({ reports: [], page: 1, total: 0, hasMore: false });
      return Promise.resolve();
    }

    const nextPage = reset ? 1 : this.data.page + 1;
    this.setData(reset ? { listLoading: true } : { loadingMore: true });

    const query = buildQuery({
      page: nextPage,
      page_size: this.data.pageSize,
      status: this.data.statusFilter,
    });

    return this.requestWithAuth(auth, {
      url: `${API_BASE_URL}/api/chashuibao/business-risk/list${query ? `?${query}` : ''}`,
      method: 'GET',
    })
      .then(({ ok, payload }) => {
        if (!ok || !payload.data) throw new Error(payload.message || '获取报告列表失败');
        const listData = payload.data || {};
        const sourceReports = Array.isArray(listData.reports) ? listData.reports : [];
        const normalized = sourceReports.map(normalizeListItem);
        const merged = reset ? normalized : this.data.reports.concat(normalized);
        const total = Number(listData.total || 0);
        const page = Number(listData.page || nextPage);
        const hasMore = merged.length < total;
        this.setData({ reports: merged, total, page, hasMore });
      })
      .catch((err) => {
        if (err.code !== 'NO_AUTH') wx.showToast({ title: err.message || '获取报告列表失败', icon: 'none' });
      })
      .finally(() => this.setData({ listLoading: false, loadingMore: false }));
  },

  onSelectReport(e) {
    const orderNo = String(e.currentTarget.dataset.orderNo || '');
    const status = normalizeStatus(e.currentTarget.dataset.status || '');
    this.stopPolling();
    this.setData({
      orderNo,
      authFetched: false,
      initialUrl: '',
      currentStatus: status,
      currentStatusText: getStatusText(status),
      currentStatusInfo: null,
      reportUrl: '',
    });
    if (orderNo) {
      this.fetchStatus(orderNo, true)
        .then((info) => {
          this.updateCurrentStatus(info);
          if (normalizeStatus(info.status) === 'pending') this.startPolling(orderNo);
        })
        .catch(() => {});
    }
  },

  onOpenReportUrl() {
    const reportUrl = this.getReportUrl();
    if (!reportUrl) { wx.showToast({ title: '暂无可预览报告', icon: 'none' }); return; }
    wx.showLoading({ title: '打开中' });
    wx.downloadFile({
      url: reportUrl,
      success: (res) => {
        if (res.statusCode === 200 && res.tempFilePath) {
          wx.openDocument({ filePath: res.tempFilePath, showMenu: true, fail: () => this.onCopyReportUrl() });
          return;
        }
        wx.showToast({ title: '下载失败', icon: 'none' });
      },
      fail: () => wx.showToast({ title: '下载失败', icon: 'none' }),
      complete: () => wx.hideLoading(),
    });
  },

  onCopyReportUrl() {
    const reportUrl = this.getReportUrl();
    if (!reportUrl) { wx.showToast({ title: '暂无报告链接', icon: 'none' }); return; }
    wx.setClipboardData({ data: reportUrl });
  },

  updateCurrentStatus(info) {
    const status = normalizeStatus(info.status);
    this.setData({
      currentStatus: status,
      currentStatusText: getStatusText(status),
      currentStatusInfo: info,
      reportUrl: info.report_url || this.data.reportUrl,
      orderNo: info.order_no || this.data.orderNo,
    });
  },

  getReportUrl() {
    return (this.data.currentStatusInfo && this.data.currentStatusInfo.report_url)
      || this.data.reportUrl
      || '';
  },

  ensureAuth(showTip = true) {
    const auth = getAuthContext();
    if (!auth && showTip) wx.showToast({ title: '请先登录', icon: 'none' });
    return auth;
  },

  requestWithAuth(auth, options = {}) {
    return new Promise((resolve, reject) => {
      wx.request({
        url: options.url,
        method: options.method || 'GET',
        data: options.data,
        timeout: options.timeout || 30000,
        header: {
          'content-type': 'application/json',
          Authorization: `${auth.tokenType} ${auth.token}`,
        },
        success: (res) => {
          const payload = res && res.data ? res.data : {};
          const ok =
            res.statusCode >= 200 &&
            res.statusCode < 300 &&
            (payload.code === 1 || payload.code === '1');
          resolve({ ok, payload, res });
        },
        fail: (err) => {
          reject(createError(err && err.errMsg ? err.errMsg : '网络异常，请稍后重试', 'NETWORK_ERROR'));
        },
      });
    });
  },
});
