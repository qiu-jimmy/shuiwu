// individual.js
// 工商执照申请页面 - 管理执照办理表单数据、身份证与补充材料图片上传、表单校验及接口提交

const config = require('../../../../utils/config.js');

// 政治面貌与文化程度的枚举值映射（与后端约定的枚举字符串保持一致）
const POLITICAL_STATUS_MAP = ['masses', 'league_member', 'party_member', 'other'];
const EDUCATION_LEVEL_MAP  = ['high_school', 'junior_college', 'bachelor', 'postgraduate'];

Page({
  data: {
    // ---- 01 店铺信息 ----
    licenseStoreName:     '',   // 主字号（当前输入框值）
    licenseStoreNameList: [],   // 备用字号列表（可多条）

    // ---- 02 身份证信息 ----
    // 每张图片对象：{ tempPath, file_url, uploading, uploadSuccess, uploadError }
    idCardFrontImage: { tempPath: '', file_url: '', uploading: false, uploadSuccess: false, uploadError: null },
    idCardBackImage:  { tempPath: '', file_url: '', uploading: false, uploadSuccess: false, uploadError: null },
    idCardNumber:     '',
    idCardValidType:  'range',  // 'range' | 'long_term'
    idCardValidStart: '',
    idCardValidEnd:   '',

    // ---- 03 申请人基本信息 ----
    applicantName:          '',
    applicantPhone:         '',
    politicalStatusIndex:   -1,
    politicalStatusOptions: ['群众', '共青团员', '中共党员', '其他'],
    educationLevelIndex:    -1,
    educationLevelOptions:  ['高中及以下', '大专', '本科', '研究生及以上'],
    email: '',

    // ---- 04 补充材料 & 备注（选填） ----
    extraAttachments: [],  // [{ tempPath, file_url, uploading, uploadSuccess, uploadError }]
    userRemarks:      '',

    // ---- 协议 & 提交状态 ----
    agreeProtocol: false,
    submitting:    false,
    isFormValid:   false,
  },

  onLoad() {
    this.updateFormValid();
  },

  // ==================== 01 店铺信息 ====================

  onLicenseStoreNameInput(e) {
    this.setData({ licenseStoreName: e.detail.value });
    this.updateFormValid();
  },

  /** 将主输入框中的字号追加到备用列表并清空输入 */
  addMoreName() {
    const name = this.data.licenseStoreName.trim();
    if (!name) return;
    this.setData({
      licenseStoreNameList: [...this.data.licenseStoreNameList, name],
      licenseStoreName: '',
    });
    this.updateFormValid();
  },

  removeExtraName(e) {
    const idx = e.currentTarget.dataset.index;
    this.setData({ licenseStoreNameList: this.data.licenseStoreNameList.filter((_, i) => i !== idx) });
    this.updateFormValid();
  },

  // ==================== 02 身份证信息 ====================

  /** 选择身份证图片，type = 'front'（人像面）| 'back'（国徽面） */
  chooseIdCardImage(e) {
    const type = e.currentTarget.dataset.type;
    const key  = type === 'front' ? 'idCardFrontImage' : 'idCardBackImage';
    wx.chooseImage({
      count: 1,
      sizeType: ['compressed'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        this.setData({
          [key]: { tempPath: res.tempFilePaths[0], file_url: '', uploading: false, uploadSuccess: false, uploadError: null },
        });
        this.updateFormValid();
      },
    });
  },

  onIdCardNumberInput(e) {
    this.setData({ idCardNumber: e.detail.value });
    this.updateFormValid();
  },

  /** 切换有效期类型，切换时清空日期 */
  setValidType(e) {
    this.setData({ idCardValidType: e.currentTarget.dataset.type, idCardValidStart: '', idCardValidEnd: '' });
    this.updateFormValid();
  },

  onValidStartChange(e) {
    this.setData({ idCardValidStart: e.detail.value });
    this.updateFormValid();
  },

  onValidEndChange(e) {
    this.setData({ idCardValidEnd: e.detail.value });
    this.updateFormValid();
  },

  // ==================== 03 申请人基本信息 ====================

  onApplicantNameInput(e) {
    this.setData({ applicantName: e.detail.value });
    this.updateFormValid();
  },

  onApplicantPhoneInput(e) {
    this.setData({ applicantPhone: e.detail.value });
    this.updateFormValid();
  },

  onPoliticalStatusChange(e) {
    this.setData({ politicalStatusIndex: parseInt(e.detail.value) });
    this.updateFormValid();
  },

  onEducationLevelChange(e) {
    this.setData({ educationLevelIndex: parseInt(e.detail.value) });
    this.updateFormValid();
  },

  onEmailInput(e) {
    // 邮箱选填，不影响 isFormValid，仅在提交时做格式校验
    this.setData({ email: e.detail.value });
  },

  // ==================== 04 补充材料 & 备注 ====================

  chooseExtraAttachment() {
    const maxCount = 5 - this.data.extraAttachments.length;
    if (maxCount <= 0) {
      wx.showToast({ title: '最多上传 5 张', icon: 'none' });
      return;
    }
    wx.chooseImage({
      count: maxCount,
      sizeType: ['compressed'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        const newItems = res.tempFilePaths.map(path => ({
          tempPath: path, file_url: '', uploading: false, uploadSuccess: false, uploadError: null,
        }));
        this.setData({ extraAttachments: [...this.data.extraAttachments, ...newItems] });
      },
    });
  },

  previewExtraAttachment(e) {
    const idx  = e.currentTarget.dataset.index;
    const urls = this.data.extraAttachments.filter(a => a.tempPath).map(a => a.tempPath);
    wx.previewImage({ current: this.data.extraAttachments[idx].tempPath, urls });
  },

  removeExtraAttachment(e) {
    const idx = e.currentTarget.dataset.index;
    this.setData({ extraAttachments: this.data.extraAttachments.filter((_, i) => i !== idx) });
  },

  onRemarksInput(e) {
    this.setData({ userRemarks: e.detail.value });
  },

  // ==================== 协议 ====================

  toggleProtocol() {
    this.setData({ agreeProtocol: !this.data.agreeProtocol });
    this.updateFormValid();
  },

  openProtocol() {
    // 预留协议页跳转，后续由后端/运营提供协议 URL
    wx.showToast({ title: '协议内容准备中', icon: 'none' });
  },

  // ==================== 表单校验 ====================

  /** 静默校验：仅返回 true/false，用于控制按钮可用状态 */
  checkFormValid() {
    const d = this.data;
    const idCardReg = /(^\d{15}$)|(^\d{18}$)|(^\d{17}(\d|X|x)$)/;
    const phoneReg  = /^1[3-9]\d{9}$/;

    if (!d.licenseStoreName.trim() && d.licenseStoreNameList.length === 0) return false;
    if (!d.idCardFrontImage.tempPath || !d.idCardBackImage.tempPath)        return false;
    if (!idCardReg.test(d.idCardNumber.trim()))                             return false;
    if (d.idCardValidType === 'range' && (!d.idCardValidStart || !d.idCardValidEnd)) return false;
    if (!d.applicantName.trim())                                            return false;
    if (!phoneReg.test(d.applicantPhone.trim()))                            return false;
    if (d.politicalStatusIndex < 0)                                         return false;
    if (d.educationLevelIndex  < 0)                                         return false;
    if (!d.agreeProtocol)                                                   return false;
    return true;
  },

  updateFormValid() {
    this.setData({ isFormValid: this.checkFormValid() });
  },

  /** 提交前校验：带 Toast 提示，便于用户定位问题 */
  validateFormWithToast() {
    const d = this.data;
    const toast = (title) => { wx.showToast({ title, icon: 'none', duration: 2000 }); };
    const idCardReg = /(^\d{15}$)|(^\d{18}$)|(^\d{17}(\d|X|x)$)/;
    const phoneReg  = /^1[3-9]\d{9}$/;
    const emailReg  = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

    if (!d.licenseStoreName.trim() && d.licenseStoreNameList.length === 0) {
      toast('请填写营业执照办理字号'); return false;
    }
    if (!d.idCardFrontImage.tempPath || !d.idCardBackImage.tempPath) {
      toast('请上传完整的身份证人像面和国徽面'); return false;
    }
    if (!idCardReg.test(d.idCardNumber.trim())) {
      toast('请输入正确的身份证号码'); return false;
    }
    if (d.idCardValidType === 'range' && (!d.idCardValidStart || !d.idCardValidEnd)) {
      toast('请选择身份证起止日期'); return false;
    }
    if (!d.applicantName.trim()) {
      toast('请输入申请人姓名'); return false;
    }
    if (!phoneReg.test(d.applicantPhone.trim())) {
      toast('请输入正确的手机号'); return false;
    }
    if (d.politicalStatusIndex < 0) {
      toast('请选择政治面貌'); return false;
    }
    if (d.educationLevelIndex < 0) {
      toast('请选择文化程度'); return false;
    }
    if (d.email && !emailReg.test(d.email.trim())) {
      toast('邮箱格式不正确'); return false;
    }
    if (!d.agreeProtocol) {
      toast('请先阅读并勾选协议后再提交'); return false;
    }
    return true;
  },

  // ==================== 图片上传 ====================

  /** 上传单张图片，返回 Promise<fileUrl>，与原有文件上传接口保持一致 */
  uploadSingleImage(filePath, accessToken) {
    return new Promise((resolve, reject) => {
      wx.uploadFile({
        url:      `${config.API_BASE_URL}/api/files/upload`,
        filePath,
        name:     'file',
        formData: { original_filename: `id_card_${Date.now()}.jpg` },
        header:   { Authorization: `Bearer ${accessToken}` },
        success(res) {
          try {
            const data = typeof res.data === 'string' ? JSON.parse(res.data) : res.data;
            if (res.statusCode >= 200 && res.statusCode < 300 && data.code === 1) {
              const url = data.data?.file_url || data.data?.url || '';
              url ? resolve(url) : reject(data.message || '上传成功但未返回文件地址');
            } else {
              reject((data && (data.message || data.msg)) || '上传失败');
            }
          } catch {
            reject('解析响应失败');
          }
        },
        fail(err) { reject(err.errMsg || '网络错误'); },
      });
    });
  },

  /** 上传身份证正面/反面（跳过已上传成功的） */
  async uploadIdCardImages(token) {
    for (const key of ['idCardFrontImage', 'idCardBackImage']) {
      const img = this.data[key];
      if (!img.tempPath || img.uploadSuccess) continue;
      this.setData({ [`${key}.uploading`]: true });
      try {
        const url = await this.uploadSingleImage(img.tempPath, token);
        this.setData({ [`${key}.file_url`]: url, [`${key}.uploading`]: false, [`${key}.uploadSuccess`]: true });
      } catch (msg) {
        this.setData({ [`${key}.uploading`]: false, [`${key}.uploadError`]: msg });
        wx.showToast({ title: msg || '身份证上传失败', icon: 'none', duration: 2500 });
        return false;
      }
    }
    return true;
  },

  /** 上传补充材料（跳过已上传成功的） */
  async uploadExtraAttachments(token) {
    for (let i = 0; i < this.data.extraAttachments.length; i++) {
      const item = this.data.extraAttachments[i];
      if (item.uploadSuccess && item.file_url) continue;
      if (!item.tempPath) continue;

      this.setData({
        extraAttachments: this.data.extraAttachments.map((a, idx) =>
          idx === i ? { ...a, uploading: true, uploadError: null } : a),
      });
      try {
        const url = await this.uploadSingleImage(item.tempPath, token);
        this.setData({
          extraAttachments: this.data.extraAttachments.map((a, idx) =>
            idx === i ? { ...a, file_url: url, uploading: false, uploadSuccess: true } : a),
        });
      } catch (msg) {
        this.setData({
          extraAttachments: this.data.extraAttachments.map((a, idx) =>
            idx === i ? { ...a, uploading: false, uploadSuccess: false, uploadError: msg } : a),
        });
        wx.showToast({ title: msg || '补充材料上传失败', icon: 'none', duration: 2500 });
        return false;
      }
    }
    return true;
  },

  // ==================== 构建请求体 ====================

  buildRequestData() {
    const d = this.data;
    // 主字号优先放第一位，备用字号作为 list 的其余项
    const storeName    = d.licenseStoreName.trim();
    const allNames     = storeName ? [storeName, ...d.licenseStoreNameList] : [...d.licenseStoreNameList];

    return {
      declaration_type:          'license_application',     // 固定类型，后端按此路由到执照申请业务
      license_store_name:         allNames[0] || '',         // 主字号
      license_store_name_list:    allNames.slice(1),         // 备用字号（可为空数组）
      id_card_number:             d.idCardNumber.trim(),
      id_card_valid_type:         d.idCardValidType,
      id_card_valid_start:        d.idCardValidType === 'range' ? d.idCardValidStart : '',
      id_card_valid_end:          d.idCardValidType === 'range' ? d.idCardValidEnd   : '2099-12-31',
      id_card_front_url:          d.idCardFrontImage.file_url,
      id_card_back_url:           d.idCardBackImage.file_url,
      applicant_name:             d.applicantName.trim(),
      applicant_phone:            d.applicantPhone.trim(),
      political_status:           POLITICAL_STATUS_MAP[d.politicalStatusIndex] || '',
      education_level:            EDUCATION_LEVEL_MAP[d.educationLevelIndex]   || '',
      email:                      d.email.trim(),
      extra_attachments:          d.extraAttachments
                                    .filter(a => a.uploadSuccess && a.file_url)
                                    .map((a, i) => ({ file_url: a.file_url, name: `extra_${i + 1}.jpg` })),
      user_remarks:               d.userRemarks.trim(),
      agree_protocol:             true,
    };
  },

  // ==================== 提交 ====================

  async submitForm() {
    if (this.data.submitting) return;
    if (!this.validateFormWithToast()) return;
    await this.doSubmit();
  },

  async doSubmit() {
    const token = wx.getStorageSync('access_token');
    if (!token) {
      wx.showToast({ title: '请先登录', icon: 'none' });
      setTimeout(() => wx.navigateTo({ url: '/pages/mine/login/login' }), 1500);
      return;
    }

    this.setData({ submitting: true });
    wx.showLoading({ title: '提交中...', mask: true });

    // 先上传身份证图片
    const idOk = await this.uploadIdCardImages(token);
    if (!idOk) {
      wx.hideLoading();
      this.setData({ submitting: false });
      return;
    }

    // 再上传补充材料
    const extraOk = await this.uploadExtraAttachments(token);
    if (!extraOk) {
      wx.hideLoading();
      this.setData({ submitting: false });
      return;
    }

    wx.request({
      url:    `${config.API_BASE_URL}/api/business-declaration/submit`,
      method: 'POST',
      header: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      data:   this.buildRequestData(),
      success: (res) => {
        wx.hideLoading();
        this.setData({ submitting: false });
        if (res.statusCode === 200 || res.statusCode === 201) {
          wx.showToast({ title: '资料已提交，专员将尽快联系您', icon: 'success', duration: 2500 });
          setTimeout(() => wx.navigateBack(), 2500);
        } else {
          wx.showToast({ title: res.data?.message || '提交失败，请重试', icon: 'none', duration: 2000 });
        }
      },
      fail: () => {
        wx.hideLoading();
        this.setData({ submitting: false });
        wx.showToast({ title: '网络错误，请检查网络后重试', icon: 'none', duration: 2000 });
      },
    });
  },

  onShareAppMessage() {},
});
