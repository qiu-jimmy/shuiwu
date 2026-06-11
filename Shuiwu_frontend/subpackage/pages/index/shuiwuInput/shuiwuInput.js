// pages/index/shuiwuInput/shuiwuInput.js
const config = require('../../../../utils/config.js');

Page({

  /**
   * 页面的初始数据
   */
  data: {
    // 纳税人类型
    taxpayerType: 'small_scale',
    taxpayerTypeIndex: 0,
    taxpayerTypeOptions: [
      { value: 'small_scale', label: '小规模纳税人' },
      { value: 'general', label: '一般纳税人' }
    ],
    
    // 税期类型
    periodType: 'quarter',
    
    // 税期值
    periodValue: '',
    periodValueIndex: 0,
    currentPeriodLabel: '',
    quarterOptions: [],
    monthOptions: [],
    
    // 纳税人信息
    taxNo: '',
    companyName: '',
    taxpayerPhone: '', // 联系电话（必填）
    
    // 小规模纳税人数据
    smallScaleData: {
      // 3%征收率应税行为
      taxRate3: {
        totalIncomeWithTax: '',
        deductionAmount: ''
      },
      // 5%征收率应税行为
      taxRate5: {
        totalIncomeWithTax: '',
        deductionAmount: ''
      },
      // 小微企业免税销售额
      smallMicroExempt: {
        goodsAndLabor: '',
        serviceAndRealEstate: ''
      },
      // 未达起征点销售额
      belowThreshold: {
        goodsAndLabor: '',
        serviceAndRealEstate: ''
      },
      // 其他免税销售额
      otherExempt: {
        goodsAndLabor: '',
        serviceAndRealEstate: ''
      },
      // 本期应纳税额减征额
      taxReduction: {
        goodsAndLabor: '',
        serviceAndRealEstate: ''
      },
      // 本期预缴税额
      prepaidTax: {
        goodsAndLabor: '',
        serviceAndRealEstate: ''
      }
    },
    
    // 一般纳税人数据
    generalData: {
      // 销售额
      goodsSales: '',
      laborSales: '',
      exemptGoodsSales: '',
      exemptLaborSales: '',
      // 进项税额
      inputTaxCurrent: '',
      inputTaxPrevious: '',
      inputTaxTransfer: ''
    },
    
    // 备注
    userRemarks: '',
    
    // 提交状态
    submitting: false,
    
    // 表单验证状态
    isFormValid: false
  },

  /**
   * 生命周期函数--监听页面加载
   */
  onLoad(options) {
    const periodData = this.initPeriodOptions();
    
    // 设置默认税期为当前季度
    const now = new Date();
    const year = now.getFullYear();
    const month = now.getMonth() + 1;
    const quarter = Math.floor((month - 1) / 3) + 1;
    const periodValue = `${year}-${String(month).padStart(2, '0')}`;
    
    // 找到对应的索引
    const quarterIndex = periodData.quarterOptions.findIndex(item => item.value === `${year}-${String((quarter - 1) * 3 + 1).padStart(2, '0')}`);
    
    this.setData({
      quarterOptions: periodData.quarterOptions,
      monthOptions: periodData.monthOptions,
      periodValue: periodValue,
      periodValueIndex: quarterIndex >= 0 ? quarterIndex : 0,
      currentPeriodLabel: quarterIndex >= 0 ? periodData.quarterOptions[quarterIndex].label : periodData.quarterOptions[0].label
    });
    
    // 初始化表单验证状态
    this.updateFormValid();
  },

  /**
   * 初始化税期选项
   */
  initPeriodOptions() {
    const now = new Date();
    const currentYear = now.getFullYear();
    const currentMonth = now.getMonth() + 1;
    
    // 生成季度选项（最近2年,按起始月份）
    const quarterOptions = [];
    for (let year = currentYear - 1; year <= currentYear; year++) {
      for (let q = 1; q <= 4; q++) {
        const startMonth = (q - 1) * 3 + 1;
        quarterOptions.push({
          value: `${year}-${String(startMonth).padStart(2, '0')}`,
          label: `${year}年第${q}季度`,
          startDate: `${year}-${String(startMonth).padStart(2, '0')}`,
          endDate: `${year}-${String(startMonth + 2).padStart(2, '0')}`
        });
      }
    }
    
    // 生成月度选项（最近12个月）
    const monthOptions = [];
    for (let i = 11; i >= 0; i--) {
      const date = new Date(currentYear, currentMonth - 1 - i, 1);
      const year = date.getFullYear();
      const month = date.getMonth() + 1;
      monthOptions.push({
        value: `${year}-${String(month).padStart(2, '0')}`,
        label: `${year}年${month}月`,
        startDate: `${year}-${String(month).padStart(2, '0')}`,
        endDate: `${year}-${String(month).padStart(2, '0')}`
      });
    }
    
    return {
      quarterOptions,
      monthOptions
    };
  },

  /**
   * 选择纳税人类型
   */
  onTaxpayerTypeChange(e) {
    const index = parseInt(e.detail.value);
    const taxpayerType = this.data.taxpayerTypeOptions[index].value;
    
    // 一般纳税人只支持月度申报
    const periodType = taxpayerType === 'general' ? 'month' : this.data.periodType;
    
    this.setData({
      taxpayerTypeIndex: index,
      taxpayerType: taxpayerType,
      periodType: periodType
    });
    
    // 重新设置税期
    if (taxpayerType === 'general') {
      this.onPeriodTypeChange({ currentTarget: { dataset: { type: 'month' } } });
    }
    
    this.updateFormValid();
  },

  /**
   * 选择税期类型
   */
  onPeriodTypeChange(e) {
    const periodType = e.currentTarget.dataset.type;
    let periodValue = '';
    let periodValueIndex = 0;
    let currentPeriodLabel = '';
    
    // 根据税期类型设置默认值
    if (periodType === 'quarter') {
      const now = new Date();
      const year = now.getFullYear();
      const month = now.getMonth() + 1;
      const quarter = Math.floor((month - 1) / 3) + 1;
      const startMonth = (quarter - 1) * 3 + 1;
      periodValue = `${year}-${String(startMonth).padStart(2, '0')}`;
      periodValueIndex = this.data.quarterOptions.findIndex(item => item.value === periodValue);
      if (periodValueIndex < 0) periodValueIndex = 0;
      currentPeriodLabel = this.data.quarterOptions[periodValueIndex].label;
    } else if (periodType === 'month') {
      const now = new Date();
      const year = now.getFullYear();
      const month = now.getMonth() + 1;
      periodValue = `${year}-${String(month).padStart(2, '0')}`;
      periodValueIndex = this.data.monthOptions.findIndex(item => item.value === periodValue);
      if (periodValueIndex < 0) periodValueIndex = 0;
      currentPeriodLabel = this.data.monthOptions[periodValueIndex].label;
    }
    
    this.setData({
      periodType,
      periodValue,
      periodValueIndex,
      currentPeriodLabel
    });
    this.updateFormValid();
  },

  /**
   * 选择税期值
   */
  onPeriodValueChange(e) {
    const index = parseInt(e.detail.value);
    const options = this.data.periodType === 'quarter' ? this.data.quarterOptions : this.data.monthOptions;
    
    this.setData({
      periodValueIndex: index,
      periodValue: options[index].value,
      currentPeriodLabel: options[index].label
    });
    this.updateFormValid();
  },

  /**
   * 输入纳税人识别号
   */
  onTaxNoInput(e) {
    this.setData({
      taxNo: e.detail.value
    });
    this.updateFormValid();
  },

  /**
   * 输入企业名称
   */
  onCompanyNameInput(e) {
    this.setData({
      companyName: e.detail.value
    });
    this.updateFormValid();
  },

  /**
   * 输入联系电话
   */
  onTaxpayerPhoneInput(e) {
    this.setData({
      taxpayerPhone: e.detail.value
    });
    this.updateFormValid();
  },

  /**
   * 输入小规模纳税人信息
   */
  onSmallScaleInput(e) {
    const field = e.currentTarget.dataset.field;
    const value = e.detail.value;
    this.setData({
      [`smallScaleData.${field}`]: value
    });
    this.updateFormValid();
  },

  /**
   * 输入一般纳税人信息
   */
  onGeneralInput(e) {
    const field = e.currentTarget.dataset.field;
    const value = e.detail.value;
    this.setData({
      [`generalData.${field}`]: value
    });
    this.updateFormValid();
  },

  /**
   * 输入备注
   */
  onRemarksInput(e) {
    this.setData({
      userRemarks: e.detail.value
    });
  },

  /**
   * 检查表单是否完整（不显示提示）
   */
  checkFormValid() {
    // 基本字段验证
    if (!this.data.taxNo || !this.data.taxNo.trim()) return false;
    if (!this.data.companyName || !this.data.companyName.trim()) return false;
    if (!this.data.taxpayerPhone || !this.data.taxpayerPhone.trim()) return false;
    if (!this.data.periodValue) return false;
    
    // 小规模纳税人验证
    if (this.data.taxpayerType === 'small_scale') {
      // 至少需要填写一项销售额
      const hasIncome = this.data.smallScaleData.taxRate3.totalIncomeWithTax || 
                       this.data.smallScaleData.taxRate5.totalIncomeWithTax;
      if (!hasIncome) return false;
    }
    
    // 一般纳税人验证
    if (this.data.taxpayerType === 'general') {
      // 至少需要填写一项销售额
      const hasIncome = this.data.generalData.goodsSales || 
                       this.data.generalData.laborSales;
      if (!hasIncome) return false;
    }
    
    return true;
  },

  /**
   * 更新表单验证状态
   */
  updateFormValid() {
    const isFormValid = this.checkFormValid();
    this.setData({
      isFormValid: isFormValid
    });
  },

  /**
   * 验证表单（带提示）
   */
  validateForm() {
    if (!this.data.taxNo || !this.data.taxNo.trim()) {
      wx.showToast({
        title: '请输入纳税人识别号',
        icon: 'none'
      });
      return false;
    }
    
    // 纳税人识别号验证（15位或18位数字或字母）
    const taxNoReg = /^[A-Z0-9]{15}$|^[A-Z0-9]{18}$/;
    if (!taxNoReg.test(this.data.taxNo.trim().toUpperCase())) {
      wx.showToast({
        title: '请输入正确的纳税人识别号',
        icon: 'none'
      });
      return false;
    }
    
    if (!this.data.companyName || !this.data.companyName.trim()) {
      wx.showToast({
        title: '请输入企业名称',
        icon: 'none'
      });
      return false;
    }
    
    if (!this.data.taxpayerPhone || !this.data.taxpayerPhone.trim()) {
      wx.showToast({
        title: '请输入联系电话',
        icon: 'none'
      });
      return false;
    }
    
    // 手机号格式验证
    const phoneReg = /^1[3-9]\d{9}$/;
    if (!phoneReg.test(this.data.taxpayerPhone.trim())) {
      wx.showToast({
        title: '请输入正确的手机号',
        icon: 'none'
      });
      return false;
    }
    
    if (!this.data.periodValue) {
      wx.showToast({
        title: '请选择所属期',
        icon: 'none'
      });
      return false;
    }
    
    // 小规模纳税人验证
    if (this.data.taxpayerType === 'small_scale') {
      const hasIncome = this.data.smallScaleData.taxRate3.totalIncomeWithTax || 
                       this.data.smallScaleData.taxRate5.totalIncomeWithTax;
      if (!hasIncome) {
        wx.showToast({
          title: '请至少填写一项应税销售额',
          icon: 'none'
        });
        return false;
      }
    }
    
    // 一般纳税人验证
    if (this.data.taxpayerType === 'general') {
      const hasIncome = this.data.generalData.goodsSales || 
                       this.data.generalData.laborSales;
      if (!hasIncome) {
        wx.showToast({
          title: '请至少填写一项销售额',
          icon: 'none'
        });
        return false;
      }
    }
    
    return true;
  },

  /**
   * 构建请求数据（映射到后端 /api/tax-declaration/submit 接口格式）
   */
  buildRequestData() {
    const options = this.data.periodType === 'quarter' ? this.data.quarterOptions : this.data.monthOptions;
    const selectedPeriod = options[this.data.periodValueIndex];
    
    // 转换税期格式：季度转为 2024Q1 格式，月度保持 2024-01 格式
    let taxPeriod = '';
    if (this.data.periodType === 'quarter') {
      const year = parseInt(selectedPeriod.startDate.split('-')[0]);
      const month = parseInt(selectedPeriod.startDate.split('-')[1]);
      const quarter = Math.floor((month - 1) / 3) + 1;
      taxPeriod = `${year}Q${quarter}`;
    } else {
      taxPeriod = selectedPeriod.startDate; // 月度格式：2024-01
    }
    
    // 构建收入信息（income_info），将表单数据打包为 JSON
    let incomeInfo = {};
    
    if (this.data.taxpayerType === 'small_scale') {
      // 小规模纳税人收入信息
      incomeInfo = {
        taxpayer_type: 'small_scale',
        period_type: this.data.periodType, // 'quarter' 或 'month'
        // 3%征收率应税销售额
        tax_rate_3_income: this.data.smallScaleData.taxRate3.totalIncomeWithTax ? parseFloat(this.data.smallScaleData.taxRate3.totalIncomeWithTax) : 0,
        tax_rate_3_deduction: this.data.smallScaleData.taxRate3.deductionAmount ? parseFloat(this.data.smallScaleData.taxRate3.deductionAmount) : 0,
        // 5%征收率应税销售额
        tax_rate_5_income: this.data.smallScaleData.taxRate5.totalIncomeWithTax ? parseFloat(this.data.smallScaleData.taxRate5.totalIncomeWithTax) : 0,
        tax_rate_5_deduction: this.data.smallScaleData.taxRate5.deductionAmount ? parseFloat(this.data.smallScaleData.taxRate5.deductionAmount) : 0,
        // 免税销售额
        small_micro_exempt_goods: this.data.smallScaleData.smallMicroExempt.goodsAndLabor ? parseFloat(this.data.smallScaleData.smallMicroExempt.goodsAndLabor) : 0,
        small_micro_exempt_service: this.data.smallScaleData.smallMicroExempt.serviceAndRealEstate ? parseFloat(this.data.smallScaleData.smallMicroExempt.serviceAndRealEstate) : 0,
        below_threshold_goods: this.data.smallScaleData.belowThreshold.goodsAndLabor ? parseFloat(this.data.smallScaleData.belowThreshold.goodsAndLabor) : 0,
        below_threshold_service: this.data.smallScaleData.belowThreshold.serviceAndRealEstate ? parseFloat(this.data.smallScaleData.belowThreshold.serviceAndRealEstate) : 0,
        other_exempt_goods: this.data.smallScaleData.otherExempt.goodsAndLabor ? parseFloat(this.data.smallScaleData.otherExempt.goodsAndLabor) : 0,
        other_exempt_service: this.data.smallScaleData.otherExempt.serviceAndRealEstate ? parseFloat(this.data.smallScaleData.otherExempt.serviceAndRealEstate) : 0,
        // 减征和预缴
        tax_reduction_goods: this.data.smallScaleData.taxReduction.goodsAndLabor ? parseFloat(this.data.smallScaleData.taxReduction.goodsAndLabor) : 0,
        tax_reduction_service: this.data.smallScaleData.taxReduction.serviceAndRealEstate ? parseFloat(this.data.smallScaleData.taxReduction.serviceAndRealEstate) : 0,
        prepaid_tax_goods: this.data.smallScaleData.prepaidTax.goodsAndLabor ? parseFloat(this.data.smallScaleData.prepaidTax.goodsAndLabor) : 0,
        prepaid_tax_service: this.data.smallScaleData.prepaidTax.serviceAndRealEstate ? parseFloat(this.data.smallScaleData.prepaidTax.serviceAndRealEstate) : 0
      };
    } else if (this.data.taxpayerType === 'general') {
      // 一般纳税人收入信息
      incomeInfo = {
        taxpayer_type: 'general',
        // 销售额
        goods_sales: this.data.generalData.goodsSales ? parseFloat(this.data.generalData.goodsSales) : 0,
        labor_sales: this.data.generalData.laborSales ? parseFloat(this.data.generalData.laborSales) : 0,
        exempt_goods_sales: this.data.generalData.exemptGoodsSales ? parseFloat(this.data.generalData.exemptGoodsSales) : 0,
        exempt_labor_sales: this.data.generalData.exemptLaborSales ? parseFloat(this.data.generalData.exemptLaborSales) : 0,
        // 进项税额
        input_tax_current: this.data.generalData.inputTaxCurrent ? parseFloat(this.data.generalData.inputTaxCurrent) : 0,
        input_tax_previous: this.data.generalData.inputTaxPrevious ? parseFloat(this.data.generalData.inputTaxPrevious) : 0,
        input_tax_transfer: this.data.generalData.inputTaxTransfer ? parseFloat(this.data.generalData.inputTaxTransfer) : 0
      };
    }
    
    // 构建后端接口所需的数据格式
    const requestData = {
      taxpayer_name: this.data.companyName.trim(),
      taxpayer_id_card: this.data.taxNo.trim(),
      taxpayer_phone: this.data.taxpayerPhone.trim(),
      taxpayer_type: 'enterprise', // 固定为企业
      tax_type: 'vat', // 固定为增值税
      tax_period: taxPeriod,
      income_info: incomeInfo,
      deduction_info: {}, // 增值税暂不需要扣除信息
      user_remarks: this.data.userRemarks ? this.data.userRemarks.trim() : ''
    };
    
    return requestData;
  },

  /**
   * 提交表单
   */
  async submitForm() {
    if (this.data.submitting) {
      return;
    }

    if (!this.validateForm()) {
      return;
    }

    // 检查登录状态
    const token = wx.getStorageSync('access_token');
    if (!token) {
      wx.showModal({
        title: '请先登录',
        content: '提交申报需要登录，是否前往登录？',
        confirmText: '去登录',
        cancelText: '取消',
        success: (res) => {
          if (res.confirm) {
            wx.navigateTo({
              url: '/pages/mine/login/login',
              fail: () => {
                wx.reLaunch({ url: '/pages/mine/login/login' });
              }
            });
          }
        }
      });
      return;
    }

    this.setData({
      submitting: true
    });

    wx.showLoading({
      title: '提交中...',
      mask: true
    });

    // 构建请求数据
    const requestData = this.buildRequestData();

    // 调用后端接口
    wx.request({
      url: `${config.API_BASE_URL}/api/tax-declaration/submit`,
      method: 'POST',
      header: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      data: requestData,
      success: (res) => {
        wx.hideLoading();
        this.setData({
          submitting: false
        });

        if (res.statusCode >= 200 && res.statusCode < 300 && res.data && res.data.code === 1) {
          wx.showToast({
            title: res.data.message || '申报提交成功',
            icon: 'success',
            duration: 2000
          });

          // 延迟返回上一页
          setTimeout(() => {
            wx.navigateBack();
          }, 2000);
        } else {
          wx.showToast({
            title: res.data?.message || '提交失败，请重试',
            icon: 'none',
            duration: 2500
          });
        }
      },
      fail: (err) => {
        wx.hideLoading();
        this.setData({
          submitting: false
        });

        console.error('提交申报失败:', err);
        wx.showToast({
          title: '网络错误，请检查网络后重试',
          icon: 'none',
          duration: 2500
        });
      }
    });
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
   * 页面相关事件处理函数--监听用户下拉动作
   */
  onPullDownRefresh() {

  },

  /**
   * 页面上拉触底事件的处理函数
   */
  onReachBottom() {

  },

  /**
   * 用户点击右上角分享
   */
  onShareAppMessage() {

  }
})
