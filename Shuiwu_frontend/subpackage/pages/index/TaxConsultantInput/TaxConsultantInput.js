// pages/index/TaxConsultantInput/TaxConsultantInput.js
import { API_BASE_URL, OSS_URL } from '../../../../utils/config';

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

Page({

  /**
   * 页面的初始数据
   */
  data: {
    // OSS图片地址前缀
    ossUrl: OSS_URL,
    formData: {
      name: '', // 姓名
      birthDate: '', // 出生日期
      idCard: '', // 身份证号码
      address: '', // 现住地
      phone: '', // 手机号
      certificateNo: '', // 税务师职业资格证书编号
      certificateDate: '', // 税务师职业资格证书取得时间
      certificateImages: [], // 税务师职业资格证书照片
      experiences: [], // 工作经历（选填）
      expertise: '', // 擅长的税务业务领域
      settledIndex: -1, // 是否入驻索引
      additionalInfo: '', // 补充说明
    },
    settledOptions: ['是', '否'],
    agreementChecked: false, // 是否同意承诺
    isFormValid: false // 表单是否完整
  },

  /**
   * 生命周期函数--监听页面加载
   */
  onLoad(options) {
    this.checkLogin();
    this.updateFormValid();
  },

  /**
   * 检测用户是否登录，未登录则提示并跳转登录页
   */
  checkLogin() {
    const auth = getAuthContext();
    if (!auth) {
      wx.showModal({
        title: '请先登录',
        content: '提交税务师申请需要登录，是否前往登录？',
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
          } else {
            wx.navigateBack();
          }
        },
      });
      return false;
    }
    return true;
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

  },

  // ==================== 基本信息输入事件 ====================
  
  /**
   * 姓名输入
   */
  onNameInput(e) {
    this.setData({
      'formData.name': e.detail.value
    });
    this.updateFormValid();
  },

  /**
   * 出生日期选择
   */
  onBirthDateChange(e) {
    this.setData({
      'formData.birthDate': e.detail.value
    });
    this.updateFormValid();
  },

  /**
   * 身份证号码输入
   */
  onIdCardInput(e) {
    this.setData({
      'formData.idCard': e.detail.value
    });
    this.updateFormValid();
  },

  /**
   * 现住地输入
   */
  onAddressInput(e) {
    this.setData({
      'formData.address': e.detail.value
    });
    this.updateFormValid();
  },

  /**
   * 手机号输入
   */
  onPhoneInput(e) {
    this.setData({
      'formData.phone': e.detail.value
    });
    this.updateFormValid();
  },

  // ==================== 证书信息输入事件 ====================
  
  /**
   * 证书编号输入
   */
  onCertificateNoInput(e) {
    this.setData({
      'formData.certificateNo': e.detail.value
    });
    this.updateFormValid();
  },

  /**
   * 证书取得时间选择
   */
  onCertificateDateChange(e) {
    this.setData({
      'formData.certificateDate': e.detail.value
    });
    this.updateFormValid();
  },

  /**
   * 选择证书照片
   */
  chooseCertificateImage() {
    const maxCount = 3 - this.data.formData.certificateImages.length;
    wx.chooseImage({
      count: maxCount,
      sizeType: ['compressed'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        const tempFilePaths = res.tempFilePaths;
        const certificateImages = [...this.data.formData.certificateImages, ...tempFilePaths];
        this.setData({
          'formData.certificateImages': certificateImages
        });
        this.updateFormValid();
      },
      fail: (err) => {
        console.error('选择图片失败', err);
        wx.showToast({
          title: '选择图片失败',
          icon: 'none'
        });
      }
    });
  },

  /**
   * 预览证书照片
   */
  previewCertificateImage(e) {
    const index = e.currentTarget.dataset.index;
    wx.previewImage({
      current: this.data.formData.certificateImages[index],
      urls: this.data.formData.certificateImages
    });
  },

  /**
   * 删除证书照片
   */
  deleteCertificateImage(e) {
    const index = e.currentTarget.dataset.index;
    const certificateImages = this.data.formData.certificateImages.filter((item, i) => i !== index);
    this.setData({
      'formData.certificateImages': certificateImages
    });
    this.updateFormValid();
  },

  // ==================== 工作经历相关事件 ====================
  
  /**
   * 添加工作经历
   */
  addExperience() {
    const experiences = [...this.data.formData.experiences];
    experiences.push({
      startDate: '',
      endDate: '',
      company: '',
      position: '',
      workContent: ''
    });
    this.setData({
      'formData.experiences': experiences
    });
    this.updateFormValid();
  },

  /**
   * 删除工作经历
   */
  deleteExperience(e) {
    const index = e.currentTarget.dataset.index;
    const experiences = this.data.formData.experiences.filter((item, i) => i !== index);
    this.setData({
      'formData.experiences': experiences
    });
    this.updateFormValid();
  },

  /**
   * 工作经历开始时间选择
   */
  onExperienceStartDateChange(e) {
    const index = e.currentTarget.dataset.index;
    const experiences = this.data.formData.experiences;
    experiences[index].startDate = e.detail.value;
    this.setData({
      'formData.experiences': experiences
    });
    this.updateFormValid();
  },

  /**
   * 工作经历结束时间选择
   */
  onExperienceEndDateChange(e) {
    const index = e.currentTarget.dataset.index;
    const experiences = this.data.formData.experiences;
    experiences[index].endDate = e.detail.value;
    this.setData({
      'formData.experiences': experiences
    });
    this.updateFormValid();
  },

  /**
   * 工作经历单位输入
   */
  onExperienceCompanyInput(e) {
    const index = e.currentTarget.dataset.index;
    const experiences = this.data.formData.experiences;
    experiences[index].company = e.detail.value;
    this.setData({
      'formData.experiences': experiences
    });
    this.updateFormValid();
  },

  /**
   * 工作经历职务输入
   */
  onExperiencePositionInput(e) {
    const index = e.currentTarget.dataset.index;
    const experiences = this.data.formData.experiences;
    experiences[index].position = e.detail.value;
    this.setData({
      'formData.experiences': experiences
    });
    this.updateFormValid();
  },

  /**
   * 工作经历工作内容输入
   */
  onExperienceWorkContentInput(e) {
    const index = e.currentTarget.dataset.index;
    const experiences = this.data.formData.experiences;
    experiences[index].workContent = e.detail.value;
    this.setData({
      'formData.experiences': experiences
    });
    this.updateFormValid();
  },

  // ==================== 其他信息输入事件 ====================
  
  /**
   * 擅长领域输入
   */
  onExpertiseInput(e) {
    this.setData({
      'formData.expertise': e.detail.value
    });
    this.updateFormValid();
  },

  /**
   * 是否入驻选择
   */
  onSettledChange(e) {
    this.setData({
      'formData.settledIndex': parseInt(e.detail.value)
    });
    this.updateFormValid();
  },

  /**
   * 补充说明输入
   */
  onAdditionalInfoInput(e) {
    this.setData({
      'formData.additionalInfo': e.detail.value
    });
  },

  // ==================== 承诺确认 ====================

  /**
   * 切换承诺确认状态
   */
  onAgreementToggle() {
    this.setData({
      agreementChecked: !this.data.agreementChecked
    });
  },

  // ==================== 表单验证和提交 ====================

  /**
   * 检查表单是否完整（不显示提示）
   */
  checkFormValid() {
    const { formData } = this.data;

    // 必填字段
    if (!formData.name || formData.name.length < 2 || formData.name.length > 100) return false;
    if (!formData.idCard || formData.idCard.length < 15 || formData.idCard.length > 20) return false;
    if (!formData.phone || formData.phone.length < 11 || formData.phone.length > 20) return false;
    if (!formData.certificateNo) return false;
    if (formData.certificateImages.length === 0) return false;
    if (!formData.expertise) return false;

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
   * 验证表单
   */
  validateForm() {
    const { formData } = this.data;

    // 验证姓名 (2-100字符)
    if (!formData.name) {
      wx.showToast({ title: '请输入姓名', icon: 'none' });
      return false;
    }
    if (formData.name.length < 2 || formData.name.length > 100) {
      wx.showToast({ title: '姓名长度应为2-100个字符', icon: 'none' });
      return false;
    }

    // 验证身份证号 (15-20字符)
    if (!formData.idCard) {
      wx.showToast({ title: '请输入身份证号码', icon: 'none' });
      return false;
    }
    if (formData.idCard.length < 15 || formData.idCard.length > 20) {
      wx.showToast({ title: '身份证号长度应为15-20个字符', icon: 'none' });
      return false;
    }

    // 验证联系电话 (11-20字符)
    if (!formData.phone) {
      wx.showToast({ title: '请输入联系电话', icon: 'none' });
      return false;
    }
    if (formData.phone.length < 11 || formData.phone.length > 20) {
      wx.showToast({ title: '联系电话长度应为11-20个字符', icon: 'none' });
      return false;
    }

    // 验证证书编号
    if (!formData.certificateNo) {
      wx.showToast({ title: '请输入税务师职业资格证书编号', icon: 'none' });
      return false;
    }

    // 验证证书图片
    if (formData.certificateImages.length === 0) {
      wx.showToast({ title: '请上传税务师职业资格证书照片', icon: 'none' });
      return false;
    }

    // 验证擅长领域
    if (!formData.expertise) {
      wx.showToast({ title: '请输入擅长的税务业务领域', icon: 'none' });
      return false;
    }

    return true;
  },

  /**
   * 上传单个文件，返回 Promise  resolve(url) 或 reject(message)
   */
  uploadOneFile(filePath, accessToken) {
    return new Promise((resolve, reject) => {
      wx.uploadFile({
        url: `${API_BASE_URL}/api/files/upload`,
        filePath: filePath,
        name: 'file',
        formData: { original_filename: `tax_${Date.now()}.jpg` },
        header: { Authorization: `Bearer ${accessToken}` },
        success(res) {
          try {
            const data = typeof res.data === 'string' ? JSON.parse(res.data) : res.data;
            if (res.statusCode >= 200 && res.statusCode < 300 && data.code === 1) {
              const url = data.data?.file_url || data.data?.url || data.file_url || data.url || '';
              if (url) {
                resolve(url);
              } else {
                reject(data.message || '上传成功但未返回文件地址');
              }
            } else {
              reject(data.message || data.msg || '上传失败');
            }
          } catch (e) {
            reject('解析响应失败');
          }
        },
        fail(err) {
          reject(err.errMsg || '网络错误');
        },
      });
    });
  },

  /**
   * 先上传证书图片，再提交申请
   */
  async submitAfterUpload(accessToken) {
    const { formData } = this.data;
    const certPaths = formData.certificateImages || [];

    const certificateImageUrls = [];
    for (let i = 0; i < certPaths.length; i++) {
      try {
        const url = await this.uploadOneFile(certPaths[i], accessToken);
        certificateImageUrls.push(url);
      } catch (msg) {
        wx.hideLoading();
        wx.showToast({ title: msg || '证书图片上传失败', icon: 'none', duration: 2500 });
        return;
      }
    }

    const experiences = (formData.experiences || [])
      .filter((exp) => exp.startDate || exp.endDate || exp.company || exp.position || exp.workContent)
      .map((exp) => ({
        start_date: exp.startDate || '',
        end_date: exp.endDate || '',
        company: exp.company || '',
        position: exp.position || '',
        work_content: exp.workContent || '',
      }));

    const payload = {
      name: formData.name,
      birthDate: formData.birthDate || undefined,
      idCard: formData.idCard,
      address: formData.address || undefined,
      phone: formData.phone,
      certificateNo: formData.certificateNo,
      certificateDate: formData.certificateDate || undefined,
      certificateImages: certificateImageUrls,
      experiences: experiences.length ? experiences : undefined,
      expertise: formData.expertise,
      // 表单：0=是 1=否，接口：0=否 1=是
      settledIndex: formData.settledIndex === 0 ? 1 : formData.settledIndex === 1 ? 0 : undefined,
      additionalInfo: formData.additionalInfo || undefined,
    };

    wx.request({
      url: `${API_BASE_URL}/api/tax_accountant/apply`,
      method: 'POST',
      header: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${accessToken}`,
      },
      data: payload,
      success: (res) => {
        wx.hideLoading();
        const data = res.data;
        if (res.statusCode >= 200 && res.statusCode < 300 && data && data.code === 1) {
          wx.showToast({ title: data.message || '申请提交成功，请等待审核', icon: 'success' });
          setTimeout(() => {
            wx.navigateBack();
          }, 1500);
        } else {
          wx.showToast({
            title: (data && data.message) || '提交失败',
            icon: 'none',
            duration: 2500,
          });
        }
      },
      fail: (err) => {
        wx.hideLoading();
        wx.showToast({
          title: err.errMsg || '网络错误，请重试',
          icon: 'none',
          duration: 2500,
        });
      },
    });
  },

  /**
   * 提交表单
   */
  onSubmit() {
    const auth = getAuthContext();
    if (!auth) {
      this.checkLogin();
      return;
    }
    if (!this.validateForm()) {
      return;
    }

    wx.showLoading({ title: '提交中...', mask: true });
    this.submitAfterUpload(auth.token);
  },
})
