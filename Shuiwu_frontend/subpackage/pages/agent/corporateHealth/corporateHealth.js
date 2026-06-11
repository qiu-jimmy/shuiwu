/**
 * corporateHealth.js — 企业全景报告页面逻辑
 *
 * 功能：
 *   - 用户输入企业名称，提交后由后端自动查询税号并生成全景报告
 *   - 通过轮询 /panoramic/status/:id 获取报告生成进度
 *   - 报告完成后跳转到报告详情页
 *
 * 注意：税号（taxpayerNo）字段已移除，由后端 chashuibao_service 自动处理
 */
import { API_BASE_URL } from '../../../../utils/config';

const POLL_INTERVAL_MS = 4000;
const POLL_TIMEOUT_MS = 5 * 60 * 1000;

const STATUS_TEXT_MAP = {
  pending: '生成中',
  success: '生成成功',
  failed: '生成失败',
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

const buildQuery = (params = {}) =>
  Object.keys(params)
    .filter((key) => params[key] !== undefined && params[key] !== null && params[key] !== '')
    .map((key) => `${encodeURIComponent(key)}=${encodeURIComponent(params[key])}`)
    .join('&');

const normalizeStatus = (status = '') => String(status || '').toLowerCase();

const getStatusText = (status = '') => STATUS_TEXT_MAP[normalizeStatus(status)] || String(status || '--');

const getStatusClass = (status = '') => {
  const normalized = normalizeStatus(status);
  if (normalized === 'pending' || normalized === 'success' || normalized === 'failed') {
    return normalized;
  }
  if (!normalized) {
    return 'idle';
  }
  return 'unknown';
};

const normalizeListItem = (item = {}) => ({
  ...item,
  statusText: getStatusText(item.status),
  statusClass: getStatusClass(item.status),
});

const toSafeJson = (value) => {
  try {
    return JSON.stringify(value || {}, null, 2);
  } catch (error) {
    return '{}';
  }
};

const parseGenerateIds = (data = {}) => ({
  recordId: data.id || data.report_record_id || data.reportRecordId || data.record_id || '',
  reportId: data.report_id || data.reportId || '',
});

const createError = (message, code) => {
  const error = new Error(message);
  error.code = code;
  return error;
};

Page({
  data: {
    taxpayerName: '',
    statusTabs: [
      { value: '', label: '全部' },
      { value: 'pending', label: '生成中' },
      { value: 'success', label: '成功' },
      { value: 'failed', label: '失败' },
    ],
    statusFilter: '',

    generating: false,
    listLoading: false,
    loadingMore: false,

    reports: [],
    page: 1,
    pageSize: 20,
    total: 0,
    hasMore: false,

    currentRecordId: '',
    currentReportId: '',
    currentStatus: '',
    currentStatusText: '未开始',
    currentStatusInfo: null,
    reportUrl: '',
  },

  onLoad() {
    this.pollTimer = null;
    this.pollStartAt = 0;
    this.loadReportList(true, false);
  },

  onShow() {
    if (
      this.data.currentRecordId &&
      normalizeStatus(this.data.currentStatus) === 'pending' &&
      !this.data.generating
    ) {
      this.startPolling(this.data.currentRecordId);
    }
  },

  onHide() {
    this.stopPolling();
  },

  onUnload() {
    this.stopPolling();
  },

  onPullDownRefresh() {
    this.loadReportList(true, false).finally(() => {
      wx.stopPullDownRefresh();
    });
  },

  onTaxpayerNameInput(e) {
    this.setData({ taxpayerName: e.detail.value || '' });
  },

  onStatusFilterTap(e) {
    const status = e.currentTarget.dataset.status || '';
    if (status === this.data.statusFilter) {
      return;
    }
    this.setData({ statusFilter: status });
    this.loadReportList(true, true);
  },

  onRefreshList() {
    this.loadReportList(true, true);
  },

  onLoadMore() {
    this.loadReportList(false, true);
  },

  onGenerateReport() {
    if (this.data.generating) {
      return;
    }

    const taxpayerName = String(this.data.taxpayerName || '').trim();

    if (!taxpayerName) {
      wx.showToast({ title: '请输入企业名称', icon: 'none' });
      return;
    }

    const auth = this.ensureAuth(true);
    if (!auth) {
      return;
    }

    this.stopPolling();
    this.setData({
      generating: true,
      currentRecordId: '',
      currentReportId: '',
      currentStatus: 'pending',
      currentStatusText: getStatusText('pending'),
      currentStatusInfo: null,
      reportUrl: '',
    });

    wx.showLoading({ title: '生成中' });
    // 注意：税号将由后端根据企业名称自动查询
    this.requestWithAuth(auth, {
      url: `${API_BASE_URL}/api/chashuibao/panoramic/generate`,
      method: 'POST',
      data: {
        taxpayerName,
      },
      timeout: 60000,
    })
      .then(({ ok, payload }) => {
        if (!ok || !payload.data) {
          throw new Error(payload.message || '生成全景报告失败');
        }

        const { recordId, reportId } = parseGenerateIds(payload.data);
        const generatedReportUrl = payload.data.report_url || payload.data.reportUrl || '';
        this.setData({
          currentRecordId: recordId,
          currentReportId: reportId,
          reportUrl: generatedReportUrl,
        });

        if (recordId) {
          this.startPolling(recordId);
          wx.showToast({ title: payload.message || '已开始生成', icon: 'none' });
          return;
        }

        this.setData({
          generating: false,
          currentStatus: reportId ? 'success' : '',
          currentStatusText: reportId ? getStatusText('success') : '已提交',
        });

        this.loadReportList(true, false);
      })
      .catch((error) => {
        this.setData({
          generating: false,
          currentStatus: 'failed',
          currentStatusText: getStatusText('failed'),
        });
        wx.showToast({ title: error.message || '生成失败', icon: 'none' });
      })
      .finally(() => {
        wx.hideLoading();
      });
  },

  onRefreshStatus() {
    const recordId = this.data.currentRecordId;
    if (!recordId) {
      wx.showToast({ title: '暂无可刷新记录', icon: 'none' });
      return;
    }

    this.fetchStatus(recordId, true)
      .then((statusInfo) => {
        this.updateCurrentStatus(statusInfo);
        const status = normalizeStatus(statusInfo.status);
        if (status === 'pending') {
          this.startPolling(recordId);
          return;
        }
      })
      .catch(() => {});
  },

  onSelectReport(e) {
    const recordId = String(e.currentTarget.dataset.recordId || '');
    const reportId = String(e.currentTarget.dataset.reportId || '');
    const status = normalizeStatus(e.currentTarget.dataset.status || '');

    this.stopPolling();
    this.setData({
      currentRecordId: recordId,
      currentReportId: reportId,
      currentStatus: status,
      currentStatusText: getStatusText(status),
      currentStatusInfo: null,
      reportUrl: '',
    });

    if (recordId) {
      this.fetchStatus(recordId, true)
        .then((statusInfo) => {
          this.updateCurrentStatus(statusInfo);
          const latestStatus = normalizeStatus(statusInfo.status);
          if (latestStatus === 'pending') {
            this.startPolling(recordId);
            return;
          }
        })
        .catch(() => {});
      return;
    }
  },

  onOpenReportUrl() {
    const reportUrl = this.getReportUrl();
    if (!reportUrl) {
      wx.showToast({ title: '暂无可预览报告', icon: 'none' });
      return;
    }

    wx.showLoading({ title: '打开中' });
    wx.downloadFile({
      url: reportUrl,
      success: (res) => {
        if (res.statusCode === 200 && res.tempFilePath) {
          wx.openDocument({
            filePath: res.tempFilePath,
            showMenu: true,
            fail: () => {
              this.onCopyReportUrl();
            },
          });
          return;
        }
        wx.showToast({ title: '下载失败', icon: 'none' });
      },
      fail: () => {
        wx.showToast({ title: '下载失败', icon: 'none' });
      },
      complete: () => {
        wx.hideLoading();
      },
    });
  },

  onCopyReportUrl() {
    const reportUrl = this.getReportUrl();
    if (!reportUrl) {
      wx.showToast({ title: '暂无报告链接', icon: 'none' });
      return;
    }
    wx.setClipboardData({ data: reportUrl });
  },

  startPolling(recordId) {
    if (!recordId) {
      return;
    }
    this.stopPolling();
    this.pollStartAt = Date.now();
    this.setData({
      generating: true,
      currentRecordId: recordId,
      currentStatus: 'pending',
      currentStatusText: getStatusText('pending'),
    });
    this.pollStatus(recordId);
  },

  stopPolling() {
    if (this.pollTimer) {
      clearTimeout(this.pollTimer);
      this.pollTimer = null;
    }
    if (this.data.generating) {
      this.setData({ generating: false });
    }
  },

  pollStatus(recordId) {
    const elapsed = Date.now() - (this.pollStartAt || Date.now());
    if (elapsed >= POLL_TIMEOUT_MS) {
      this.stopPolling();
      this.setData({
        currentStatus: 'failed',
        currentStatusText: '生成超时',
      });
      wx.showToast({ title: '生成超时，请重试', icon: 'none' });
      this.loadReportList(true, false);
      return;
    }

    this.fetchStatus(recordId, false)
      .then((statusInfo) => {
        this.updateCurrentStatus(statusInfo);
        const status = normalizeStatus(statusInfo.status);

        if (status === 'pending') {
          this.scheduleNextPoll(recordId);
          return;
        }

        this.stopPolling();
        this.loadReportList(true, false);

        if (status === 'success') {
          wx.showToast({ title: '报告生成成功', icon: 'success' });
          return;
        }

        if (status === 'failed') {
          wx.showToast({ title: '报告生成失败', icon: 'none' });
          return;
        }

        wx.showToast({ title: `状态：${statusInfo.status || '未知'}`, icon: 'none' });
      })
      .catch((error) => {
        if (error && error.code === 'NO_AUTH') {
          this.stopPolling();
          return;
        }
        this.scheduleNextPoll(recordId);
      });
  },

  scheduleNextPoll(recordId) {
    this.pollTimer = setTimeout(() => {
      this.pollStatus(recordId);
    }, POLL_INTERVAL_MS);
  },

  fetchStatus(recordId, showError = false) {
    const finalRecordId = String(recordId || '').trim();
    if (!finalRecordId) {
      return Promise.reject(createError('缺少记录ID', 'MISSING_ID'));
    }

    const auth = this.ensureAuth(showError);
    if (!auth) {
      return Promise.reject(createError('请先登录', 'NO_AUTH'));
    }

    return this.requestWithAuth(auth, {
      url: `${API_BASE_URL}/api/chashuibao/panoramic/status/${encodeURIComponent(finalRecordId)}`,
      method: 'GET',
    })
      .then(({ ok, payload }) => {
        if (!ok || !payload.data) {
          throw new Error(payload.message || '获取状态失败');
        }
        return payload.data;
      })
      .catch((error) => {
        if (showError && error.code !== 'NO_AUTH') {
          wx.showToast({ title: error.message || '获取状态失败', icon: 'none' });
        }
        throw error;
      });
  },

  loadReportList(reset = true, showAuthTip = false) {
    if (reset && this.data.listLoading) {
      return Promise.resolve();
    }
    if (!reset && (this.data.loadingMore || this.data.listLoading || !this.data.hasMore)) {
      return Promise.resolve();
    }

    const auth = this.ensureAuth(showAuthTip);
    if (!auth) {
      if (reset) {
        this.setData({
          reports: [],
          page: 1,
          total: 0,
          hasMore: false,
        });
      }
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
      url: `${API_BASE_URL}/api/chashuibao/panoramic/list${query ? `?${query}` : ''}`,
      method: 'GET',
    })
      .then(({ ok, payload }) => {
        if (!ok || !payload.data) {
          throw new Error(payload.message || '获取报告列表失败');
        }

        const listData = payload.data || {};
        const sourceReports = Array.isArray(listData.reports) ? listData.reports : [];
        const normalizedReports = sourceReports.map(normalizeListItem);
        const mergedReports = reset ? normalizedReports : this.data.reports.concat(normalizedReports);

        const total = Number(listData.total || 0);
        const page = Number(listData.page || nextPage);
        const pageSize = Number(listData.page_size || this.data.pageSize);
        const hasMore = mergedReports.length < total;

        this.setData({
          reports: mergedReports,
          total,
          page,
          pageSize,
          hasMore,
        });
      })
      .catch((error) => {
        if (error.code !== 'NO_AUTH') {
          wx.showToast({ title: error.message || '获取报告列表失败', icon: 'none' });
        }
      })
      .finally(() => {
        this.setData({
          listLoading: false,
          loadingMore: false,
        });
      });
  },

  updateCurrentStatus(statusInfo) {
    const status = normalizeStatus(statusInfo.status);
    this.setData({
      currentRecordId: statusInfo.id || this.data.currentRecordId,
      currentReportId: statusInfo.report_id || this.data.currentReportId,
      currentStatus: status,
      currentStatusText: getStatusText(status),
      currentStatusInfo: statusInfo,
      reportUrl: statusInfo.report_url || this.data.reportUrl,
    });
  },

  getReportUrl() {
    const fromStatus = this.data.currentStatusInfo && this.data.currentStatusInfo.report_url
      ? this.data.currentStatusInfo.report_url
      : '';
    return fromStatus || this.data.reportUrl || '';
  },

  ensureAuth(showTip = true) {
    const auth = getAuthContext();
    if (!auth && showTip) {
      wx.showToast({ title: '请先登录', icon: 'none' });
    }
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
        fail: (error) => {
          reject(createError(error && error.errMsg ? error.errMsg : '网络异常，请稍后重试', 'NETWORK_ERROR'));
        },
      });
    });
  },
});
