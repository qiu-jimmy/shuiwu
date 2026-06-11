// pages/mine/business-query/business-query.js
import { API_BASE_URL, OSS_URL } from '../../../../utils/config';

Page({

  /**
   * 页面的初始数据
   */
  data: {
    // OSS图片地址前缀
    ossUrl: OSS_URL,
    // 申报列表
    declarations: [],
    // 分页信息
    page: 1,
    pageSize: 8,
    total: 0,
    // 加载状态
    loading: false,
    hasMore: true,
    // 空状态
    isEmpty: false,
    // 详情弹窗
    showDetailModal: false,
    detailLoading: false,
    declarationDetail: null
  },

  /**
   * 生命周期函数--监听页面加载
   */
  onLoad(options) {
    this.loadDeclarations();
  },

  /**
   * 加载申报列表
   */
  loadDeclarations() {
    // 检查是否还有更多数据
    if (!this.data.hasMore && this.data.page > 1) {
      return;
    }

    // 检查登录状态
    const token = wx.getStorageSync('access_token');
    if (!token) {
      wx.showToast({
        title: '请先登录',
        icon: 'none'
      });
      setTimeout(() => {
        wx.navigateTo({
          url: '/pages/mine/login/login'
        });
      }, 1500);
      return;
    }

    this.setData({
      loading: true
    });

    wx.request({
      url: `${API_BASE_URL}/api/business-declaration/list`,
      method: 'GET',
      header: {
        'Authorization': `Bearer ${token}`
      },
      data: {
        page: this.data.page,
        page_size: this.data.pageSize
      },
      success: (res) => {
        this.setData({
          loading: false
        });

        if (res.statusCode === 200 && res.data.code === 1) {
          const { declarations, total, page, page_size } = res.data.data;
          
          // 处理申报列表数据
          const processedDeclarations = declarations.map(item => ({
            ...item,
            statusText: this.getStatusText(item.status),
            statusClass: this.getStatusClass(item.status),
            declarationTypeText: this.getDeclarationTypeText(item.declaration_type),
            formattedDate: this.formatDate(item.created_at)
          }));

          // 如果是第一页，直接替换；否则追加
          const newDeclarations = this.data.page === 1 
            ? processedDeclarations 
            : [...this.data.declarations, ...processedDeclarations];

          // 存储到本地缓存
          try {
            wx.setStorageSync('businessDeclarations', newDeclarations);
          } catch (e) {
            console.error('存储数据失败:', e);
          }

          this.setData({
            declarations: newDeclarations,
            total: total,
            hasMore: newDeclarations.length < total,
            isEmpty: newDeclarations.length === 0
          });
        } else {
          wx.showToast({
            title: res.data?.message || '加载失败',
            icon: 'none'
          });
        }
      },
      fail: (err) => {
        this.setData({
          loading: false
        });
        console.error('加载申报列表失败:', err);
        wx.showToast({
          title: '网络错误，请重试',
          icon: 'none'
        });
      }
    });
  },

  /**
   * 获取状态文本（状态筛选：pending, processing, completed, rejected, need_supplement）
   */
  getStatusText(status) {
    const statusMap = {
      'pending': '待审核',
      'processing': '处理中',
      'completed': '已完成',
      'rejected': '已拒绝',
      'need_supplement': '需补充',
      'approved': '已通过'
    };
    return statusMap[status] || status;
  },

  /**
   * 获取状态样式类
   */
  getStatusClass(status) {
    const classMap = {
      'pending': 'status-pending',
      'processing': 'status-processing',
      'completed': 'status-approved',
      'rejected': 'status-rejected',
      'need_supplement': 'status-need-supplement',
      'approved': 'status-approved'
    };
    return classMap[status] || 'status-pending';
  },

  /**
   * 获取申报类型文本
   */
  getDeclarationTypeText(declarationType) {
    const typeMap = {
      'annual_report': '年报',
      'change_registration': '变更登记',
      'deregistration': '注销登记',
      'tax_registration': '税务登记',
      'invoice_application': '发票申请'
    };
    return typeMap[declarationType] || declarationType;
  },

  /**
   * 格式化日期
   */
  formatDate(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hour = String(date.getHours()).padStart(2, '0');
    const minute = String(date.getMinutes()).padStart(2, '0');
    return `${year}-${month}-${day} ${hour}:${minute}`;
  },

  /**
   * 格式化日期（仅日期）
   */
  formatDateOnly(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  },

  /**
   * 格式化数字（金额）
   */
  formatNumber(num) {
    if (!num && num !== 0) return '0';
    return num.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  },

  /**
   * 点击申报项
   */
  onDeclarationTap(e) {
    const index = e.currentTarget.dataset.index;
    const declaration = this.data.declarations[index];
    this.loadDeclarationDetail(declaration.id);
  },

  /**
   * 加载申报详情
   */
  loadDeclarationDetail(declarationId) {
    // 检查登录状态
    const token = wx.getStorageSync('access_token');
    if (!token) {
      wx.showToast({
        title: '请先登录',
        icon: 'none'
      });
      return;
    }

    this.setData({
      detailLoading: true,
      showDetailModal: true
    });

    wx.request({
      url: `${API_BASE_URL}/api/business-declaration/${declarationId}`,
      method: 'GET',
      header: {
        'Authorization': `Bearer ${token}`
      },
      success: (res) => {
        this.setData({
          detailLoading: false
        });

        if (res.statusCode === 200 && res.data.code === 1) {
          const detail = res.data.data;
          
          // 处理详情数据
          const processedDetail = {
            ...detail,
            statusText: this.getStatusText(detail.status),
            statusClass: this.getStatusClass(detail.status),
            declarationTypeText: this.getDeclarationTypeText(detail.declaration_type),
            formattedDate: this.formatDate(detail.created_at),
            formattedApprovalDate: detail.approval_date ? this.formatDateOnly(detail.approval_date) : '',
            formattedProcessedAt: detail.processed_at ? this.formatDate(detail.processed_at) : '',
            // 处理申报信息
            declarationInfoList: this.formatDeclarationInfo(detail.declaration_type, detail.declaration_info)
          };

          this.setData({
            declarationDetail: processedDetail
          });
        } else {
          wx.showToast({
            title: res.data?.message || '加载详情失败',
            icon: 'none'
          });
          this.closeDetailModal();
        }
      },
      fail: (err) => {
        this.setData({
          detailLoading: false
        });
        console.error('加载申报详情失败:', err);
        wx.showToast({
          title: '网络错误，请重试',
          icon: 'none'
        });
        this.closeDetailModal();
      }
    });
  },

  /**
   * 格式化申报信息
   */
  formatDeclarationInfo(declarationType, declarationInfo) {
    if (!declarationInfo) return [];
    const list = [];

    if (declarationType === 'annual_report') {
      // 年报信息
      if (declarationInfo.annual_revenue) {
        list.push({ label: '年度营收', value: `¥${this.formatNumber(declarationInfo.annual_revenue)}` });
      }
      if (declarationInfo.profit) {
        list.push({ label: '利润', value: `¥${this.formatNumber(declarationInfo.profit)}` });
      }
      if (declarationInfo.employees) {
        list.push({ label: '员工人数', value: `${declarationInfo.employees}人` });
      }
      if (declarationInfo.rent) {
        list.push({ label: '租金', value: `¥${this.formatNumber(declarationInfo.rent)}` });
      }
      if (declarationInfo.utilities) {
        list.push({ label: '水电费', value: `¥${this.formatNumber(declarationInfo.utilities)}` });
      }
    } else if (declarationType === 'change_registration') {
      // 变更登记信息
      const changeTypeMap = {
        'address': '地址',
        'scope': '经营范围',
        'name': '名称',
        'operator': '经营者'
      };
      if (declarationInfo.change_type) {
        list.push({ label: '变更类型', value: changeTypeMap[declarationInfo.change_type] || declarationInfo.change_type });
      }
      if (declarationInfo.old_value) {
        list.push({ label: '变更前', value: declarationInfo.old_value });
      }
      if (declarationInfo.new_value) {
        list.push({ label: '变更后', value: declarationInfo.new_value });
      }
    } else if (declarationType === 'deregistration') {
      // 注销登记信息
      if (declarationInfo.deregistration_reason) {
        list.push({ label: '注销原因', value: declarationInfo.deregistration_reason });
      }
      if (declarationInfo.creditor_clearance !== undefined) {
        list.push({ label: '债权人清理', value: declarationInfo.creditor_clearance ? '是' : '否' });
      }
    } else if (declarationType === 'tax_registration') {
      // 税务登记信息
      if (declarationInfo.tax_type) {
        list.push({ label: '税种类型', value: declarationInfo.tax_type });
      }
      if (declarationInfo.tax_scope) {
        list.push({ label: '税务范围', value: declarationInfo.tax_scope });
      }
    } else if (declarationType === 'invoice_application') {
      // 发票申请信息
      if (declarationInfo.invoice_type) {
        list.push({ label: '发票类型', value: declarationInfo.invoice_type });
      }
      if (declarationInfo.invoice_amount) {
        list.push({ label: '发票金额', value: `¥${this.formatNumber(declarationInfo.invoice_amount)}` });
      }
      if (declarationInfo.invoice_purpose) {
        list.push({ label: '发票用途', value: declarationInfo.invoice_purpose });
      }
    }

    return list;
  },

  /**
   * 关闭详情弹窗
   */
  closeDetailModal() {
    this.setData({
      showDetailModal: false,
      declarationDetail: null
    });
  },

  /**
   * 阻止事件冒泡
   */
  stopPropagation() {
    // 空函数，用于阻止事件冒泡
  },

  /**
   * 预览批准凭证
   */
  onPreviewProof(e) {
    const url = e && e.currentTarget && e.currentTarget.dataset ? e.currentTarget.dataset.url : '';
    if (!url) {
      wx.showToast({ title: '暂无凭证', icon: 'none' });
      return;
    }

    wx.previewImage({
      urls: [url],
      current: url,
      fail: () => {
        wx.showToast({ title: '预览失败', icon: 'none' });
      },
    });
  },

  /**
   * 页面相关事件处理函数--监听用户下拉动作
   */
  onPullDownRefresh() {
    this.setData({
      page: 1,
      hasMore: true
    });
    this.loadDeclarations();
    wx.stopPullDownRefresh();
  },

  /**
   * 页面上拉触底事件的处理函数
   */
  onReachBottom() {
    if (this.data.hasMore && !this.data.loading) {
      this.setData({
        page: this.data.page + 1
      });
      this.loadDeclarations();
    }
  },

  /**
   * 生命周期函数--监听页面初次渲染完成
   */
  onReady() {

  },

  /**
   * 生命周期函数--监听页面显示
   */
  onShow() {
    // 每次显示时刷新列表
    if (this.data.declarations.length > 0) {
      this.setData({
        page: 1,
        hasMore: true
      });
      this.loadDeclarations();
    }
  },

  /**
   * 生命周期函数--监听页面隐藏
   */
  onHide() {

  },

  /**
   * 生命周期函数--监听页面卸载
   */
  onUnload() {

  },

  /**
   * 用户点击右上角分享
   */
  onShareAppMessage() {

  }
})
