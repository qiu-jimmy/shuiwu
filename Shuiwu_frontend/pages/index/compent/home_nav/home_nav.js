// pages/index/compent/home_nav/home_nav.js
import { OSS_URL } from '../../../../utils/config';

Component({
  /**
   * 组件的属性列表
   */
  properties: {
    // 容器高度（rpx）
    containerHeight: {
      type: Number,
      value: 0,
      observer: 'onContainerHeightChange'
    },
    // 系统信息
    systemInfo: {
      type: Object,
      value: null,
      observer: 'onSystemInfoChange'
    }
  },

  /**
   * 组件的初始数据
   */
  data: {
    // OSS图片地址前缀
    ossUrl: OSS_URL,
    animationClass: 'animate-first', // 动画类名，初始为第一次动画
    animatedTexts: [
      { key: 'zhi', text: '智', cls: 'animated-text-zhi' },
      { key: 'shui', text: '税', cls: 'animated-text-shui' },
      { key: 'yin', text: '引', cls: 'animated-text-yin' },
      { key: 'qing', text: '擎', cls: 'animated-text-qing' },
    ],
    navGridList: [
      { name: '数企云检', iconPath: '/images/nav/nav1.png' },
      { name: '智税星驻', iconPath: '/images/nav/nav2.png' },
      { name: '个人中枢', iconPath: '/images/nav/nav4.png' },
    ],
    // 动态计算的样式值
    navWrapperTop: '73%', // 导航栏顶部位置
    navGridTop: '73%', // 导航网格顶部位置
    containerHeight: 0, // 容器高度
    dynamicStyles: '', // 动态样式字符串
  },

  lifetimes: {
    ready() {
      this.startAnimation();
      // 如果没有传入容器高度，尝试自己获取
      if (!this.data.containerHeight) {
        this.calculateContainerHeight();
      }
    },
  },

  /**
   * 组件的方法列表
   */
  methods: {
    /**
     * 容器高度变化时的回调
     */
    onContainerHeightChange(newHeight) {
      if (typeof newHeight === 'number' && newHeight > 0) {
        this.setData({
          containerHeight: newHeight
        }, () => {
          this.updateDynamicStyles();
        });
      }
    },

    /**
     * 系统信息变化时的回调
     */
    onSystemInfoChange(newSystemInfo) {
      if (newSystemInfo && typeof newSystemInfo === 'object') {
        this.setData({
          systemInfo: newSystemInfo
        }, () => {
          this.updateDynamicStyles();
        });
      }
    },

    /**
     * 设置容器高度（供外部调用）
     */
    setContainerHeight(height) {
      // 确保传递的是有效的数字
      if (typeof height === 'number' && height > 0) {
        this.setData({
          containerHeight: height
        }, () => {
          // 在 setData 回调中执行样式更新，确保数据已更新
          this.updateDynamicStyles();
        });
      } else {
        // 如果高度无效，使用默认值
        this.setData({
          navWrapperTop: '58%',
          navGridTop: '58%',
        });
      }
    },

    /**
     * 计算容器高度（如果外部没有传入）
     */
    calculateContainerHeight() {
      const query = this.createSelectorQuery();
      query.select('.home-nav-root').boundingClientRect();
      query.exec((res) => {
        if (res && res[0]) {
          const rect = res[0];
          const systemInfo = wx.getSystemInfoSync();
          const rpxRatio = 750 / systemInfo.windowWidth;
          const height = rect.height * rpxRatio;
          if (height > 0) {
            this.setData({
              containerHeight: height
            });
            this.updateDynamicStyles();
          }
        }
      });
    },

    /**
     * 更新动态样式
     */
    updateDynamicStyles() {
      const { containerHeight, systemInfo } = this.data;

      // 如果没有系统信息，尝试从全局获取
      let actualSystemInfo = systemInfo;
      if (!actualSystemInfo) {
        actualSystemInfo = wx.getSystemInfoSync();
      }

      if (!containerHeight || containerHeight <= 0) {
        // 如果没有容器高度，使用默认值（整体上移）
        this.setData({
          navWrapperTop: '58%',
          navGridTop: '58%',
        });
        return;
      }

      // 根据容器高度和屏幕尺寸动态计算导航位置
      let adjustedNavTop = 58; // 默认值，整体上移

      if (actualSystemInfo) {
        const windowHeightPx = actualSystemInfo.windowHeight;

        // 根据屏幕高度动态调整导航位置
        // 小屏幕（如 iPhone SE）：进一步上移
        if (windowHeightPx < 600) {
          adjustedNavTop = 52;
        }
        // 中等屏幕（如 iPhone 12/13）：保持上移后的位置
        else if (windowHeightPx >= 600 && windowHeightPx < 900) {
          adjustedNavTop = 55;
        }
        // 大屏幕（如 iPhone Pro Max）：可以稍微下移一点
        else if (windowHeightPx >= 900) {
          adjustedNavTop = 58;
        }

        // 根据容器高度进一步微调
        // 如果容器高度较小，导航位置需要进一步上移
        if (containerHeight < 800) {
          adjustedNavTop = Math.max(48, adjustedNavTop - 8);
        } else if (containerHeight > 1200) {
          adjustedNavTop = Math.min(60, adjustedNavTop + 5);
        }

        // 计算向上偏移量（60rpx 对应的百分比）
        // 将 60rpx 转换为相对于容器高度的百分比
        const offsetPercent = -(60 / containerHeight) * 100;
        adjustedNavTop = adjustedNavTop - offsetPercent;
      }

      this.setData({
        navWrapperTop: `${adjustedNavTop}%`,
        navGridTop: `${adjustedNavTop}%`,
      });
    },
    startAnimation() {
      setTimeout(() => {
        this.setData({
          animationClass: 'animate-loop',
        });
      }, 12000);
    },

    onIndividualTap() {
      wx.navigateTo({
        url: '/subpackage/pages/index/individual/individual',
        fail: (err) => {
          console.error('跳转失败:', err);
          wx.redirectTo({
            url: '/subpackage/pages/index/individual/individual',
          });
        },
      });
    },

    onTaxMattersTap() {
      wx.navigateTo({
        url: '/subpackage/pages/index/allAgent/allAgent',
        fail: (err) => {
          console.error('跳转失败:', err);
          wx.redirectTo({
            url: '/subpackage/pages/index/allAgent/allAgent',
          });
        },
      });
    },

    onTaxDeclarationTap() {
      wx.navigateTo({
        url: '/subpackage/pages/index/allInput/allInput',
        fail: (err) => {
          console.error('跳转失败:', err);
          wx.redirectTo({
            url: '/subpackage/pages/index/allInput/allInput',
          });
        },
      });
    },

    /**
     * 检查会员等级是否为免费版
     * @returns {boolean} 如果是免费版返回 true，否则返回 false
     */
    checkIsFreeMember() {
      try {
        const userInfo = wx.getStorageSync('user_info');
        if (!userInfo || typeof userInfo !== 'object') {
          return false;
        }
        const memberLevel = userInfo.member_level || '';
        return String(memberLevel).toLowerCase() === 'free';
      } catch (e) {
        console.error('检查会员等级失败：', e);
        return false;
      }
    },

    /**
     * 显示会员升级提示弹窗
     */
    showVipUpgradeModal() {
      wx.showModal({
        title: '会员功能',
        content: '您还不是会员，建议充值开通会员以使用更多功能',
        confirmText: '开通会员',
        cancelText: '取消',
        success: (res) => {
          if (res.confirm) {
            wx.navigateTo({
              url: '/subpackage/pages/mine/vip-buy/vip-buy',
            });
          }
        },
      });
    },

    onNavGridTap(e) {
      const index = e.currentTarget.dataset.index;
      const navItem = this.data.navGridList[index];

      let url = '';
      if (navItem.name === '数企云检') {
        // 数企云检需要会员，先检测
        if (this.checkIsFreeMember()) {
          this.showVipUpgradeModal();
          return;
        }
        url = '/subpackage/pages/agent/reportSelector/reportSelector';
      } else if (navItem.name === '智税星驻') {
        // 智税星驻：跳转到税务师列表页面
        url = '/subpackage/pages/index/TaxConsultantList/TaxConsultantList';
      } else if (navItem.name === '个人中枢') {
        url = '/subpackage/pages/mine/userInfo/userInfo';
      }

      if (url) {
        wx.navigateTo({
          url: url,
          fail: (err) => {
            console.error('跳转失败:', err);
            wx.redirectTo({
              url: url,
            });
          },
        });
      }
    },
  },
});
