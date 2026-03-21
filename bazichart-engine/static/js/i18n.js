/**
 * i18n.js — 多语言加载器
 * 从 /static/i18n/{lang}.json 加载文本，通过 data-i18n 属性渲染。
 *
 * 用法：
 *   HTML: <span data-i18n="common.login"></span>
 *   JS:   t('common.login')  // 返回翻译文本
 */

const I18n = (() => {
  let _strings = {};
  const _lang = document.documentElement.lang || 'zh-CN';

  /**
   * 按点号路径取值，如 t('common.login') → '登录'
   */
  function t(key, vars = {}) {
    const parts = key.split('.');
    let val = _strings;
    for (const p of parts) {
      if (val == null) return key;
      val = val[p];
    }
    if (typeof val !== 'string') return key;
    // 简单变量替换：{count} → vars.count
    return val.replace(/\{(\w+)\}/g, (_, k) => (k in vars ? vars[k] : `{${k}}`));
  }

  /**
   * 将 data-i18n 属性元素的 textContent 替换为对应翻译
   */
  function applyAll() {
    document.querySelectorAll('[data-i18n]').forEach(el => {
      const key = el.getAttribute('data-i18n');
      const translated = t(key);
      if (translated !== key) el.textContent = translated;
    });
  }

  /**
   * 加载语言文件并应用翻译
   * 在 base.html 底部自动调用
   */
  async function load(lang) {
    try {
      const resp = await fetch(`/static/i18n/${lang || _lang}.json`);
      if (!resp.ok) return;
      _strings = await resp.json();
      applyAll();
    } catch (e) {
      // 静默失败——硬编码文本仍可见
    }
  }

  // 挂到全局
  return { t, load, applyAll };
})();

// 页面加载后自动执行
document.addEventListener('DOMContentLoaded', () => I18n.load());
window.t = I18n.t;
