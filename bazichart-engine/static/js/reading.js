// Alpine.js 解读页组件
function readingApp() {
  return {
    // 状态：input | loading | result
    state: 'input',

    // 表单数据
    form: {
      gender: '男',
      calendar: 'solar',
      year: new Date().getFullYear() - 30,
      month: 1,
      day: 1,
      hour: null,        // null = 不知道
      hour_label: '不知道',
      province: '',
      city: '',
      county: '',
      early_zi: false,
      dst: false,
    },

    // 时辰选项
    shichen_options: [
      { label: '不知道', value: null },
      { label: '子时 (23:00-01:00)', value: 0 },
      { label: '丑时 (01:00-03:00)', value: 2 },
      { label: '寅时 (03:00-05:00)', value: 4 },
      { label: '卯时 (05:00-07:00)', value: 6 },
      { label: '辰时 (07:00-09:00)', value: 8 },
      { label: '巳时 (09:00-11:00)', value: 10 },
      { label: '午时 (11:00-13:00)', value: 12 },
      { label: '未时 (13:00-15:00)', value: 14 },
      { label: '申时 (15:00-17:00)', value: 16 },
      { label: '酉时 (17:00-19:00)', value: 18 },
      { label: '戌时 (19:00-21:00)', value: 20 },
      { label: '亥时 (21:00-23:00)', value: 22 },
    ],

    // 地址数据
    provinces: [],
    cities: [],
    counties: [],
    location: null,
    trueAolarPreview: null,

    // loading步骤
    loadingStep: 0,
    loadingSteps: [
      '正在计算四柱八字...',
      '正在查阅命理典籍...',
      '正在交叉验证多个命理体系...',
      '正在生成你的专属解读...',
    ],
    loadingTimer: null,

    // 结果
    result: null,
    error: null,

    // 高级选项
    showAdvanced: false,

    async init() {
      // 加载省份
      this.provinces = await CitiesModule.loadProvinces();
      // 检查年份是否在夏令时范围
      this.$watch('form.year', (val) => {
        if (val >= 1986 && val <= 1991) {
          this.form.dst = true;
        }
      });
    },

    async onProvinceChange() {
      this.form.city = '';
      this.form.county = '';
      this.cities = [];
      this.counties = [];
      this.location = null;
      if (this.form.province) {
        this.cities = await CitiesModule.loadCities(this.form.province);
      }
    },

    async onCityChange() {
      this.form.county = '';
      this.counties = [];
      this.location = null;
      if (this.form.province && this.form.city) {
        const data = await CitiesModule.loadCounties(this.form.province, this.form.city);
        this.counties = data.counties || [];
        this.location = data.location;
        this.updateTrueSolarPreview();
      }
    },

    updateTrueSolarPreview() {
      if (this.location && this.form.hour !== null) {
        const lng = this.location.lng;
        const offset = (lng - 120) * 4; // 分钟
        const totalMin = this.form.hour * 60 + offset;
        const h = Math.floor(((totalMin % 1440) + 1440) % 1440 / 60);
        const m = Math.floor(((totalMin % 60) + 60) % 60);
        this.trueAolarPreview = `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')} (经度校正 ${offset >= 0 ? '+' : ''}${offset.toFixed(0)}分钟)`;
      }
    },

    setGender(g) { this.form.gender = g; },

    setHour(opt) {
      this.form.hour = opt.value;
      this.form.hour_label = opt.label;
      this.updateTrueSolarPreview();
    },

    async submitReading() {
      this.error = null;
      this.state = 'loading';
      this.loadingStep = 0;

      // 循环显示loading步骤
      this.loadingTimer = setInterval(() => {
        this.loadingStep = (this.loadingStep + 1) % this.loadingSteps.length;
      }, 8000);

      try {
        const resp = await fetch('/api/v2/reading/free', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            gender: this.form.gender,
            calendar: this.form.calendar,
            year: parseInt(this.form.year),
            month: parseInt(this.form.month),
            day: parseInt(this.form.day),
            hour: this.form.hour,
            country: 'CN',
            province: this.form.province,
            city: this.form.city,
            county: this.form.county,
            early_zi: this.form.early_zi,
            dst: this.form.dst,
          })
        });

        clearInterval(this.loadingTimer);

        if (!resp.ok) {
          const err = await resp.json();
          throw new Error(err.detail || '解读失败');
        }

        this.result = await resp.json();
        this.state = 'result';

        // 滚动到顶部
        window.scrollTo({ top: 0, behavior: 'smooth' });

      } catch (e) {
        clearInterval(this.loadingTimer);
        this.error = e.message;
        this.state = 'input';
      }
    },

    reset() {
      this.state = 'input';
      this.result = null;
      this.error = null;
    },

    // 五行颜色映射
    wuxingClass(element) {
      const map = { '木': 'wuxing-wood', '火': 'wuxing-fire', '土': 'wuxing-earth', '金': 'wuxing-metal', '水': 'wuxing-water' };
      return map[element] || '';
    },

    stemColorStyle(color) {
      return `color: ${color || 'inherit'}`;
    },

    // 当前大运高亮
    isCurrentDayun(dayun) {
      return dayun.current === true;
    },

    // 置信度星星
    confidenceStars(confidence) {
      const stars = Math.round((confidence || 0.8) * 5);
      return '●'.repeat(stars) + '○'.repeat(5 - stars);
    },

    // 下载PDF
    async downloadPDF() {
      if (!this.result?.reading_id) return;
      window.open(`/api/v2/readings/${this.result.reading_id}/pdf`, '_blank');
    },

    // 是否已登录
    isLoggedIn() {
      return !!localStorage.getItem('bazi_token');
    },

    // 简单markdown渲染
    renderMarkdown(text) {
      if (!text) return '';
      return text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/^## (.*?)$/gm, '<h2>$1</h2>')
        .replace(/^### (.*?)$/gm, '<h3 style="color:var(--accent);font-size:16px;margin:20px 0 8px">$1</h3>')
        .replace(/\n\n/g, '</p><p>')
        .replace(/^(.+)$/gm, (m) => m.startsWith('<') ? m : m);
    }
  }
}
