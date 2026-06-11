// pages/index/allAgent/allAgent.js
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
    // 所有数据列表
    agentList: [
      { id: 1, icon: OSS_URL+'/images/agent/hetong.png', text: '合同审查',explanation:'合同严审，权益保障（会员专享）'  },
      { id: 2, icon: OSS_URL+'/images/agent/AI.png', text: 'AI咨询',explanation:'智能咨询，高效答疑（普通用户）' },
      { id: 3, icon: OSS_URL+'/images/agent/wang.png', text: '万事通',explanation:'有问必答，事事精通（会员专享）' },
      { id: 4, icon: OSS_URL+'/images/agent/qiye.png', text: '企业体检',explanation:'企业诊断，健康赋能（会员专享）' }
    ],
    // 四个位置的索引（初始：左：0，前：1，右：2，后：3）
    leftIndex: 0,
    frontIndex: 1,
    rightIndex: 2,
    backIndex: 3,
    // 四个板块的位置（x, y）
    positions: {
      left: { x: -250, y: 36.6 },
      front: { x: 0, y: 100 },
      right: { x: 250, y: 36.6 },
      back: { x: 0, y: 0 }
    }, 
     // 四个板块的模糊和透明度效果
    effects: {
      left: { blur: 0, opacity: 1 },
      front: { blur: 0, opacity: 1 },
      right: { blur: 0, opacity: 1 },
      back: { blur: 7, opacity: 0.6 }
    },
    // 触摸相关
    touchStartX: 0,
    touchStartY: 0,
    isSwiping: false,
    // 切换动画状态
    isTransitioning: false,
    // 动画定时器
    animationTimer: null,
    creating: false
  },

  /**
   * 检查会员等级是否为免费版
   * @returns {boolean} 如果是免费版返回true，否则返回false
   */
  checkIsFreeMember() {
    try {
      const userInfo = wx.getStorageSync('user_info');
      if (!userInfo || typeof userInfo !== 'object') {
        // 如果没有用户信息，默认允许访问（可能是未登录状态，由其他逻辑处理）
        return false;
      }
      const memberLevel = userInfo.member_level || '';
      // 检查是否为免费版
      return String(memberLevel).toLowerCase() === 'free';
    } catch (e) {
      console.error('检查会员等级失败：', e);
      // 出错时默认允许访问
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
          // 用户点击了"开通会员"按钮，跳转到会员购买页面
          wx.navigateTo({
            url: '/subpackage/pages/mine/vip-buy/vip-buy'
          });
        }
      }
    });
  },

  /**
   * 处理 explanation 数据，拆分括号内容
   */
  processExplanationData() {
    const agentList = this.data.agentList.map(item => {
      const explanation = item.explanation || '';
      // 使用正则表达式匹配括号内的内容
      const match = explanation.match(/(.+?)（(.+?)）/);
      if (match) {
        const highlightText = match[2]; // 括号内的文本
        // 如果是"会员专享"，拆分成字符数组
        let highlightChars = [];
        if (highlightText === '会员专享') {
          highlightChars = highlightText.split('').map((char, index) => ({
            char: char,
            index: index
          }));
        }
        return {
          ...item,
          mainText: match[1], // 主文本（括号前的内容）
          highlightText: highlightText, // 括号内的文本
          highlightChars: highlightChars // 字符数组（仅当是"会员专享"时）
        };
      }
      // 如果没有匹配到括号，整个文本作为主文本
      return {
        ...item,
        mainText: explanation,
        highlightText: '',
        highlightChars: []
      };
    });
    this.setData({ agentList });
  },

  /**
   * 生命周期函数--监听页面加载
   */
  onLoad(options) {
    this.processExplanationData();
  },

  onAgentTap(e) {
    const item = e.currentTarget.dataset.item || {};
    const text = item.text || '';
    const isAiConsult = item.id === 2 || text.toLowerCase().includes('ai');
    
    // AI咨询功能允许免费用户使用，其他功能需要会员
    if (!isAiConsult) {
      // 检查会员等级
      if (this.checkIsFreeMember()) {
        // 如果是免费版，显示升级提示并阻止操作
        this.showVipUpgradeModal();
        return;
      }
    }
    
    // 合同审查功能
    if (item.id === 1 || text.includes('合同')) {
      wx.navigateTo({ url: '/subpackage/pages/agent/contractReview/contractReview' });
      return;
    }
    
    // 企业体检功能
    if (item.id === 4 || text.includes('企业体检')) {
      wx.navigateTo({ url: '/subpackage/pages/agent/corporateHealth/corporateHealth' });
      return;
    }
    
    const isHelper = item.id === 3 || text.includes('万事通');
    if (!isAiConsult && !isHelper) {
      return;
    }
    if (this.data.creating) {
      return;
    }
    const auth = getAuthContext();
    if (!auth) {
      wx.showToast({ title: '请先登录', icon: 'none' });
      return;
    }
    wx.showLoading({ title: '加载中' });
    this.setData({ creating: true });
    wx.request({
      url: `${API_BASE_URL}/api/chat/sessions`,
      method: 'POST',
      header: {
        'content-type': 'application/json',
        Authorization: `${auth.tokenType} ${auth.token}`,
      },
      data: {
        user_id: auth.userId,
        name: '',
      },
      success: (response) => {
        const payload = response && response.data ? response.data : {};
        const ok = response.statusCode >= 200 && response.statusCode < 300 && payload.code === 1 && payload.data;
        if (ok) {
          const sessionId = payload.data.session_id;
          const targetPage = isHelper ? '/pages/agent/chat-vip/chat-vip' : '/pages/agent/chat/chat';
          if (sessionId) {
            wx.setStorageSync('active_session_id', sessionId);
            wx.navigateTo({ url: `${targetPage}?sessionId=${encodeURIComponent(sessionId)}` });
            return;
          }
          wx.navigateTo({ url: targetPage });
          return;
        }
        wx.showToast({ title: payload.message || '创建会话失败', icon: 'none' });
      },
      fail: () => {
        wx.showToast({ title: '网络异常，请稍后重试', icon: 'none' });
      },
      complete: () => {
        this.setData({ creating: false });
        wx.hideLoading();
      },
    });
  },

  /**
   * 触摸开始事件
   */
  onTouchStart(e) {
    const touch = e.touches[0];
    this.setData({
      touchStartX: touch.clientX,
      touchStartY: touch.clientY,
      isSwiping: false
    });
  },

  /**
   * 触摸移动事件
   */
  onTouchMove(e) {
    const touch = e.touches[0];
    const deltaX = touch.clientX - this.data.touchStartX;
    const deltaY = Math.abs(touch.clientY - this.data.touchStartY);
    
    // 判断是否为水平滑动
    if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > 10) {
      this.setData({
        isSwiping: true
      });
    }
  },

  /**
   * 触摸结束事件
   */
  onTouchEnd(e) {
    if (!this.data.isSwiping) {
      return;
    }

    const touch = e.changedTouches[0];
    const deltaX = touch.clientX - this.data.touchStartX;
    const minSwipeDistance = 50; // 最小滑动距离

    // 左滑（deltaX < 0）
    if (deltaX < -minSwipeDistance) {
      this.swipeLeft();
    }
    // 右滑（deltaX > 0）
    else if (deltaX > minSwipeDistance) {
      this.swipeRight();
    }

    this.setData({
      isSwiping: false
    });
  },

  /**
   * 左滑切换（顺时针旋转）
   * 左 -> 后，后 -> 右，右 -> 前，前 -> 左
   */
  swipeLeft() {
    if (this.data.isTransitioning) {
      return;
    }
    
    this.setData({
      isTransitioning: true
    });
    
    // 清除之前的定时器
    if (this.data.animationTimer) {
      clearInterval(this.data.animationTimer);
    }
    
    const { positions, effects, agentList } = this.data;
    
    // 计算每个板块的目标位置和每步移动距离
    // 左 -> 后：(-250, 36.6) -> (0, 0)
    const leftToBack = {
      start: { x: positions.left.x, y: positions.left.y },
      end: { x: 0, y: 0 },
      step: { x: (0 - positions.left.x) / 40, y: (0 - positions.left.y) / 40 },
      // 模糊效果：从0增加到7，透明度从1减少到0.6
      blurStart: effects.left.blur,
      blurEnd: 7,
      blurStep: 7 / 40,
      opacityStart: effects.left.opacity,
      opacityEnd: 0.6,
      opacityStep: -0.4 / 40
    };
    
    // 后 -> 右：(0, 0) -> (250, 36.6)
    const backToRight = {
      start: { x: positions.back.x, y: positions.back.y },
      end: { x: 250, y: 36.6 },
      step: { x: (250 - positions.back.x) / 40, y: (36.6 - positions.back.y) / 40 },
      // 模糊效果：从7减少到0，透明度从0.6增加到1
      blurStart: effects.back.blur,
      blurEnd: 0,
      blurStep: -7 / 40,
      opacityStart: effects.back.opacity,
      opacityEnd: 1,
      opacityStep: 0.4 / 40   
     };
    
    // 右 -> 前：(250, 36.6) -> (0, 100)
    const rightToFront = {
      start: { x: positions.right.x, y: positions.right.y },
      end: { x: 0, y: 100 },
      step: { x: (0 - positions.right.x) / 40, y: (100 - positions.right.y) / 40 }
    };
    
    // 前 -> 左：(0, 100) -> (-250, 36.6)
    const frontToLeft = {
      start: { x: positions.front.x, y: positions.front.y },
      end: { x: -250, y: 36.6 },
      step: { x: (-250 - positions.front.x) / 40, y: (36.6 - positions.front.y) / 40 }
    };
    
    let step = 0;
    const totalSteps = 40;
    const stepInterval = 20; // 每步50ms，总共2秒（40步 * 50ms = 2000ms）
    
    const timer = setInterval(() => {
      step++;
      
      // 计算当前步的位置
      const currentPositions = {
        left: {
          x: leftToBack.start.x + leftToBack.step.x * step,
          y: leftToBack.start.y + leftToBack.step.y * step
        },
        back: {
          x: backToRight.start.x + backToRight.step.x * step,
          y: backToRight.start.y + backToRight.step.y * step
        },
        right: {
          x: rightToFront.start.x + rightToFront.step.x * step,
          y: rightToFront.start.y + rightToFront.step.y * step
        },
        front: {
          x: frontToLeft.start.x + frontToLeft.step.x * step,
          y: frontToLeft.start.y + frontToLeft.step.y * step
        }
      };

      // 计算当前步的模糊和透明度效果
      const currentEffects = {
        left: {
          blur: Number((leftToBack.blurStart + leftToBack.blurStep * step).toFixed(2)),
          opacity: Number((leftToBack.opacityStart + leftToBack.opacityStep * step).toFixed(2))
        },
        back: {
          blur: Number((backToRight.blurStart + backToRight.blurStep * step).toFixed(2)),
          opacity: Number((backToRight.opacityStart + backToRight.opacityStep * step).toFixed(2))
        },
        right: {
          blur: effects.right.blur,
          opacity: effects.right.opacity
        },
        front: {
          blur: effects.front.blur,
          opacity: effects.front.opacity
        }
      };

      this.setData({
       positions: currentPositions,
        effects: currentEffects
      });
      
      // 完成所有步骤
      if (step >= totalSteps) {
        clearInterval(timer);
        
        // 更新索引：左 -> 后，后 -> 右，右 -> 前，前 -> 左
        const { leftIndex, frontIndex, rightIndex, backIndex } = this.data;
        const newLeftIndex = frontIndex;
        const newFrontIndex = rightIndex;
        const newRightIndex = backIndex;
        const newBackIndex = leftIndex;
        
        // 重置位置和效果到最终状态
        this.setData({
          leftIndex: newLeftIndex,
          frontIndex: newFrontIndex,
          rightIndex: newRightIndex,
          backIndex: newBackIndex,
          positions: {
            left: { x: -250, y: 36.6 },
            front: { x: 0, y: 100 },
            right: { x: 250, y: 36.6 },
            back: { x: 0, y: 0 }
          },
          effects: {
            left: { blur: 0, opacity: 1 },
            front: { blur: 0, opacity: 1 },
            right: { blur: 0, opacity: 1 },
            back: { blur: 7, opacity: 0.6 }
          },
          isTransitioning: false,
          animationTimer: null
        });
      }
    }, stepInterval);
    
    this.setData({
      animationTimer: timer
    });
  },

  /**
   * 右滑切换（逆时针旋转）
   * 左 -> 前，前 -> 右，右 -> 后，后 -> 左
   */
  swipeRight() {
    if (this.data.isTransitioning) {
      return;
    }
    
    this.setData({
      isTransitioning: true
    });
    
    // 清除之前的定时器
    if (this.data.animationTimer) {
      clearInterval(this.data.animationTimer);
    }
    
    const { positions, effects, agentList } = this.data;
    
    // 计算每个板块的目标位置和每步移动距离
    // 左 -> 前：(-250, 36.6) -> (0, 100)
    const leftToFront = {
      start: { x: positions.left.x, y: positions.left.y },
      end: { x: 0, y: 100 },
      step: { x: (0 - positions.left.x) / 40, y: (100 - positions.left.y) / 40 }
    };
    
    // 前 -> 右：(0, 100) -> (250, 36.6)
    const frontToRight = {
      start: { x: positions.front.x, y: positions.front.y },
      end: { x: 250, y: 36.6 },
      step: { x: (250 - positions.front.x) / 40, y: (36.6 - positions.front.y) / 40 }
    };
    
    // 右 -> 后：(250, 36.6) -> (0, 0)
    const rightToBack = {
      start: { x: positions.right.x, y: positions.right.y },
      end: { x: 0, y: 0 },
      step: { x: (0 - positions.right.x) / 40, y: (0 - positions.right.y) / 40},
      // 模糊效果：从0增加到7，透明度从1减少到0.6
      blurStart: effects.right.blur,
      blurEnd: 7,
      blurStep: 7 / 40,
      opacityStart: effects.right.opacity,
      opacityEnd: 0.6,
      opacityStep: -0.4 / 40
    };
    
    // 后 -> 左：(0, 0) -> (-250, 36.6)
    const backToLeft = {
      start: { x: positions.back.x, y: positions.back.y },
      end: { x: -250, y: 36.6 },
      step: { x: (-250 - positions.back.x) /40, y: (36.6 - positions.back.y) / 40 },
      // 模糊效果：从7减少到0，透明度从0.6增加到1
      blurStart: effects.back.blur,
      blurEnd: 0,
      blurStep: -7 / 40,
      opacityStart: effects.back.opacity,
      opacityEnd: 1,
      opacityStep: 0.4 / 40
    };
    
    let step = 0;
    const totalSteps = 40;
    const stepInterval = 20; // 每步400ms，总共2秒
    
    const timer = setInterval(() => {
      step++;
      
      // 计算当前步的位置
      const currentPositions = {
        left: {
          x: leftToFront.start.x + leftToFront.step.x * step,
          y: leftToFront.start.y + leftToFront.step.y * step
        },
        front: {
          x: frontToRight.start.x + frontToRight.step.x * step,
          y: frontToRight.start.y + frontToRight.step.y * step
        },
        right: {
          x: rightToBack.start.x + rightToBack.step.x * step,
          y: rightToBack.start.y + rightToBack.step.y * step
        },
        back: {
          x: backToLeft.start.x + backToLeft.step.x * step,
          y: backToLeft.start.y + backToLeft.step.y * step
        }
      };

       // 计算当前步的模糊和透明度效果
       const currentEffects = {
        left: {
          blur: effects.left.blur,
          opacity: effects.left.opacity
        },
        front: {
          blur: effects.front.blur,
          opacity: effects.front.opacity
        },
        right: {
          blur: Number((rightToBack.blurStart + rightToBack.blurStep * step).toFixed(2)),
          opacity: Number((rightToBack.opacityStart + rightToBack.opacityStep * step).toFixed(2))
        },
        back: {
          blur: Number((backToLeft.blurStart + backToLeft.blurStep * step).toFixed(2)),
          opacity: Number((backToLeft.opacityStart + backToLeft.opacityStep * step).toFixed(2))
        }
      };

      this.setData({
        positions: currentPositions,
        effects: currentEffects
      });
      
      // 完成所有步骤
      if (step >= totalSteps) {
        clearInterval(timer);
        
        // 更新索引：左 -> 前，前 -> 右，右 -> 后，后 -> 左
        const { leftIndex, frontIndex, rightIndex, backIndex } = this.data;
        const newLeftIndex = backIndex;
        const newFrontIndex = leftIndex;
        const newRightIndex = frontIndex;
        const newBackIndex = rightIndex;
        
         // 重置位置和效果到最终状态
        this.setData({
          leftIndex: newLeftIndex,
          frontIndex: newFrontIndex,
          rightIndex: newRightIndex,
          backIndex: newBackIndex,
          positions: {
            left: { x: -250, y: 36.6 },
            front: { x: 0, y: 100 },
            right: { x: 250, y: 36.6 },
            back: { x: 0, y: 0 }
          },
          effects: {
            left: { blur: 0, opacity: 1 },
            front: { blur: 0, opacity: 1 },
            right: { blur: 0, opacity: 1 },
            back: { blur: 7, opacity: 0.6 }
          },
          isTransitioning: false,
          animationTimer: null
        });
      }
    }, stepInterval);
    
    this.setData({
      animationTimer: timer
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
    // 清除定时器
    if (this.data.animationTimer) {
      clearInterval(this.data.animationTimer);
    }
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
