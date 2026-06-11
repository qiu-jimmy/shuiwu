// pages/index/index/index.js
import { OSS_URL, API_BASE_URL } from '../../../utils/config';

Page({

  /**
   * 页面的初始数据
   */
  data: {
    // OSS图片地址前缀
    ossUrl: OSS_URL,
    searchValue: '',
    currentIndex: 0,
    // 通知相关
    noticeText: '【通知】欢迎使用智税引擎！我们致力于为您提供最专业的AI税务咨询服务。如有任何问题，请随时联系我们的客服团队。',
    fullNoticeText: '【通知】\n欢迎使用智税引擎！\n我们致力于为您提供最专业的AI税务咨询服务，让税务办理更高效、更省心。\n如有任何问题，请随时通过"问题反馈"入口联系我们的客服团队。\n感谢您的使用！',
    noticeScrollDuration: 20, // 滚动动画时长（秒）
    noticeTextStyle: 'animation-duration: 20s;', // 通知文字样式
    showNoticeModal: false, // 是否显示通知详情弹窗
    // 设备信息
    systemInfo: null,
    contentWrapperHeight: 0, // content-wrapper 的实际高度
  },

  /**
   * 搜索输入事件
   */
  onSearchInput(e) {
    this.setData({
      searchValue: e.detail.value
    });
  },

  /**
   * 搜索确认事件
   */
  onSearchConfirm(e) {
    const keyword = e.detail.value;
    console.log('搜索关键词:', keyword);
    // 这里可以添加搜索逻辑
  },

  /**
   * 导航栏点击事件
   */
  onNavTap(e) {
    const index = e.currentTarget.dataset.index;
    this.setData({
      currentIndex: index
    });
    // 这里可以添加切换分类后的逻辑，比如加载对应分类的数据
    console.log('切换到分类:', this.data.navList[index].name);
  },

  /**
   * 通知栏点击事件
   */
  onNoticeTap() {
    this.setData({
      showNoticeModal: true
    });
  },

  /**
   * 关闭通知详情弹窗
   */
  onCloseNoticeModal() {
    this.setData({
      showNoticeModal: false
    });
  },

  /**
   * 阻止事件冒泡
   */
  stopPropagation() {
    // 空函数，用于阻止事件冒泡
  },

  /**
   * 检测卡片点击事件
   */
  onDetectionCardTap() {
    // 该功能已关闭，不再显示提示
  },

  /**
   * 生命周期函数--监听页面加载
   *
   * 扫描 wxacode.getUnlimited 生成的小程序码进入时，
   * options.scene 就是生成时传入的 scene 字符串（即分销商推广码）。
   * 这里读取并保存到全局，供登录时作为 referral_code 传给后端。
   */
  onLoad(options) {
    // 读取扫码邀请码（wxacode.getUnlimited 的 scene 参数）
    if (options && options.scene) {
      const inviteCode = decodeURIComponent(options.scene);
      if (inviteCode) {
        const app = getApp();
        console.log('[首页] 检测到扫码邀请码:', inviteCode);
        app.globalData.pendingInviteCode = inviteCode;
      }
    }

    // 如果用户已登录但尚未绑定邀请人，尝试自动绑定上级
    this.tryAutoBindInviteForLoggedInUser();
    // 获取设备信息并计算容器高度
    this.getSystemInfoAndCalculateHeight();
  },

  /**
   * 获取系统信息并计算容器高度
   */
  getSystemInfoAndCalculateHeight() {
    const systemInfo = wx.getSystemInfoSync();
    const windowHeight = systemInfo.windowHeight; // 窗口高度（px）
    const windowWidth = systemInfo.windowWidth; // 窗口宽度（px）
    const statusBarHeight = systemInfo.statusBarHeight || 0; // 状态栏高度
    const safeArea = systemInfo.safeArea || {}; // 安全区域
    const safeAreaBottom = safeArea.bottom || windowHeight; // 安全区域底部
    
    // 将 px 转换为 rpx（假设设计稿宽度为 750rpx）
    const rpxRatio = 750 / windowWidth;
    const windowHeightRpx = windowHeight * rpxRatio;

    // 计算背景图片容器的高度（需要根据实际图片高度动态获取）
    // 注意：不要查询 content-wrapper，因为它的高度依赖于 contentWrapperHeight，
    // 会导致循环累积增加。只查询 home-bg-container 即可。
    const query = this.createSelectorQuery();
    query.select('.home-bg-container').boundingClientRect();
    query.exec((res) => {
      const bgContainerRect = res[0];

      // 如果查询成功，使用实际高度；否则使用估算值
      let contentWrapperHeight = 0;

      if (bgContainerRect && bgContainerRect.height > 0) {
        // 根据背景图片高度估算 content-wrapper 高度
        const bgHeightRpx = bgContainerRect.height * rpxRatio;
        contentWrapperHeight = windowHeightRpx - bgHeightRpx + 20; // +20 是因为 margin-top: -20rpx
      } else {
        // 如果查询不到，使用默认估算值
        // 假设背景图片占屏幕的 35-40%
        const bgHeightRpx = windowHeightRpx * 0.37;
        contentWrapperHeight = windowHeightRpx - bgHeightRpx + 20;
      }
      
      // 确保最小高度（至少占屏幕的 60%）
      const minHeight = windowHeightRpx * 0.6;
      contentWrapperHeight = Math.max(contentWrapperHeight, minHeight);
      
      // 确保最大高度不超过屏幕高度
      contentWrapperHeight = Math.min(contentWrapperHeight, windowHeightRpx * 0.95);
      
      this.setData({
        systemInfo: {
          windowWidth: windowWidth,
          windowHeight: windowHeight,
          pixelRatio: systemInfo.pixelRatio,
          screenWidth: systemInfo.screenWidth,
          screenHeight: systemInfo.screenHeight,
          statusBarHeight: statusBarHeight,
          safeAreaBottom: safeAreaBottom,
          rpxRatio: rpxRatio,
          platform: systemInfo.platform,
          system: systemInfo.system,
        },
        contentWrapperHeight: contentWrapperHeight,
      });
      
      // 通知 home-nav 组件更新高度
      const homeNavComponent = this.selectComponent('home-nav');
      if (homeNavComponent) {
        homeNavComponent.setContainerHeight(contentWrapperHeight);
      }
    });
  },

  /**
   * 已登录用户扫码后自动绑定邀请人
   *
   * 场景：
   * - 用户乙已在小程序中登录（本地有 access_token）
   * - 乙当前还没有 inviter_id
   * - 此时扫码甲的海报进入首页，希望自动建立乙→甲的绑定关系
   */
  tryAutoBindInviteForLoggedInUser() {
    try {
      const app = getApp();
      const inviteCode = app.globalData && app.globalData.pendingInviteCode;
      if (!inviteCode) {
        return;
      }

      // 读取本地登录态
      const accessToken = wx.getStorageSync('access_token');
      const tokenType = wx.getStorageSync('token_type') || 'Bearer';
      const userInfo = wx.getStorageSync('user_info') || null;

      // 必须满足：有登录态、有用户信息、当前还没有 inviter_id
      if (!accessToken || !userInfo || userInfo.inviter_id) {
        return;
      }

      console.log('[首页] 检测到已登录未绑定用户，尝试自动绑定邀请人，inviteCode =', inviteCode);

      wx.request({
        url: `${API_BASE_URL}/api/distribution/bind-invite-code`,
        method: 'POST',
        header: {
          Authorization: `${tokenType} ${accessToken}`,
          'content-type': 'application/json',
        },
        data: {
          invite_code: inviteCode,
        },
        success: (res) => {
          const payload = res && res.data ? res.data : {};
          // 后端约定：code === 1 表示成功
          if (payload.code === 1) {
            console.log('[首页] 自动绑定邀请人成功');
            // 清除已使用的邀请码，避免重复绑定
            app.globalData.pendingInviteCode = null;

            // 可选：更新本地 user_info 的 inviter_id，提升前端一致性
            try {
              const data = payload.data || {};
              const newInviterId = data.inviter_id || data.inviterId || userInfo.inviter_id;
              if (newInviterId) {
                const updatedUserInfo = {
                  ...userInfo,
                  inviter_id: newInviterId,
                };
                wx.setStorageSync('user_info', updatedUserInfo);
              }
            } catch (e) {
              console.log('[首页] 更新本地 user_info 邀请人信息失败，不影响主流程', e);
            }
          } else {
            console.log('[首页] 自动绑定邀请人失败:', payload.message || '未知错误');
            // 无论成功失败，都清除 pendingInviteCode，避免每次进入首页重复请求
            app.globalData.pendingInviteCode = null;
          }
        },
        fail: () => {
          console.log('[首页] 自动绑定邀请人请求失败');
        },
      });
    } catch (e) {
      console.log('[首页] 自动绑定邀请人异常，不影响主流程', e);
    }
  },

  /**
   * 生命周期函数--监听页面初次渲染完成
   */
  onReady() {
    // 计算通知文字滚动时长（根据文字长度动态调整）
    this.calculateNoticeScrollDuration();
    
    // 页面渲染完成后再次计算高度（此时节点已渲染）
    setTimeout(() => {
      this.getSystemInfoAndCalculateHeight();
    }, 100);
  },

  /**
   * 计算通知文字滚动时长
   */
  calculateNoticeScrollDuration() {
    // 根据文字长度计算滚动时长，确保滚动流畅
    const textLength = this.data.noticeText.length;
    // 假设每个字符宽度约14rpx，屏幕宽度约750rpx
    const estimatedWidth = textLength * 14;
    const screenWidth = 750;
    const scrollDistance = estimatedWidth + screenWidth; // 文字宽度 + 屏幕宽度
    // 滚动速度：约50rpx/秒
    const scrollSpeed = 50;
    const duration = Math.max(15, Math.ceil(scrollDistance / scrollSpeed));
    
    this.setData({
      noticeScrollDuration: duration,
      noticeTextStyle: `animation-duration: ${duration}s;`
    });
  },

  /**
   * 生命周期函数--监听页面显示
   */
  onShow() {
    // 页面显示时重新计算（处理从子页面返回的情况）
    // 使用延迟确保 DOM 完全渲染
    setTimeout(() => {
      this.getSystemInfoAndCalculateHeight();
    }, 300);

    // 热启动场景下再次尝试自动绑定（防止 pendingInviteCode 之前已写入）
    this.tryAutoBindInviteForLoggedInUser();

    // 监听窗口尺寸变化（包括屏幕旋转）
    if (this.onWindowResize) {
      wx.offWindowResize(this.onWindowResize);
    }
    this.onWindowResize = () => {
      // 延迟执行，确保窗口尺寸已更新
      setTimeout(() => {
        this.getSystemInfoAndCalculateHeight();
      }, 100);
    };
    wx.onWindowResize(this.onWindowResize);
  },

  /**
   * 生命周期函数--监听页面隐藏
   */
  onHide() {
    // 取消监听窗口尺寸变化
    if (this.onWindowResize) {
      wx.offWindowResize(this.onWindowResize);
      this.onWindowResize = null;
    }
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