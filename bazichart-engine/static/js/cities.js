// 三级联动城市选择
const CitiesModule = {
  async loadProvinces() {
    const resp = await fetch('/api/v2/cities/CN');
    if (!resp.ok) return [];
    return await resp.json();
  },

  async loadCities(province) {
    if (!province) return [];
    const resp = await fetch(`/api/v2/cities/CN/${encodeURIComponent(province)}`);
    if (!resp.ok) return [];
    return await resp.json();
  },

  async loadCounties(province, city) {
    if (!province || !city) return { counties: [], location: null };
    const resp = await fetch(`/api/v2/cities/CN/${encodeURIComponent(province)}/${encodeURIComponent(city)}`);
    if (!resp.ok) return { counties: [], location: null };
    return await resp.json();
  }
};
