(function () {
  const state = {
    athletes: [],
    teams: [],
    rifles: [],
    jackets: [],
    scopes: [],
    modes: [],
    include_unassigned: false,
    start: '',
    end: ''
  };

  const charts = {
    performance: null,
    comparison: null,
    team: null,
    scatter: null,
    heatmap: null,
    series: null
  };

  if (window.Highcharts && !Highcharts.SparkLine) {
    Highcharts.SparkLine = function (a, b, c) {
      const hasRenderTo = typeof a === 'string' || a.nodeName;
      const options = Highcharts.merge(
        {
          chart: {
            renderTo: hasRenderTo ? a : null,
            backgroundColor: null,
            borderWidth: 0,
            type: 'area',
            margin: [2, 0, 2, 0],
            height: 60,
            style: { overflow: 'visible' },
            skipClone: true
          },
          title: { text: null },
          credits: { enabled: false },
          xAxis: { visible: false },
          yAxis: { visible: false },
          legend: { enabled: false },
          tooltip: { enabled: false },
          plotOptions: {
            series: {
              animation: false,
              lineWidth: 1,
              shadow: false,
              marker: { enabled: false },
              states: { hover: { lineWidth: 1 } },
              fillOpacity: 0.2
            }
          }
        },
        b,
        c || {}
      );
      return hasRenderTo ? new Highcharts.Chart(options) : new Highcharts.Chart(
        Highcharts.merge(options, { chart: { renderTo: a } })
      );
    };
  }

  const el = (id) => document.getElementById(id);

  function toParams(payload) {
    const params = new URLSearchParams();
    if (payload.start) params.set('start', payload.start);
    if (payload.end) params.set('end', payload.end);
    if (payload.athletes.length) params.set('athlete_ids', payload.athletes.join(','));
    if (payload.teams.length) params.set('teams', payload.teams.join(','));
    if (payload.rifles.length) params.set('rifle_ids', payload.rifles.join(','));
    if (payload.jackets.length) params.set('jacket_ids', payload.jackets.join(','));
    if (payload.scopes.length) params.set('scope_ids', payload.scopes.join(','));
    if (payload.modes.length) params.set('modes', payload.modes.join(','));
    if (payload.include_unassigned) params.set('include_unassigned', '1');
    return params.toString();
  }

  function readStateFromUrl() {
    const params = new URLSearchParams(window.location.search);
    return {
      start: params.get('start') || '',
      end: params.get('end') || '',
      athletes: (params.get('athlete_ids') || '').split(',').filter(Boolean).map(Number),
      teams: (params.get('teams') || '').split(',').filter(Boolean),
      rifles: (params.get('rifle_ids') || '').split(',').filter(Boolean).map(Number),
      jackets: (params.get('jacket_ids') || '').split(',').filter(Boolean).map(Number),
      scopes: (params.get('scope_ids') || '').split(',').filter(Boolean).map(Number),
      modes: (params.get('modes') || '').split(',').filter(Boolean),
      include_unassigned: params.get('include_unassigned') === '1'
    };
  }

  function readStateFromStorage() {
    try {
      const raw = localStorage.getItem('analyticsFilters');
      return raw ? JSON.parse(raw) : {};
    } catch (e) {
      return {};
    }
  }

  function saveStateToStorage(payload) {
    localStorage.setItem('analyticsFilters', JSON.stringify(payload));
  }

  function applyStateToUrl(payload) {
    const query = toParams(payload);
    const url = query ? `${window.location.pathname}?${query}` : window.location.pathname;
    window.history.replaceState({}, '', url);
  }

  function populateSelect(selectEl, items, valueKey = 'id', labelKey = 'name') {
    if (!selectEl) return;
    selectEl.innerHTML = '';
    items.forEach((item) => {
      const option = document.createElement('option');
      option.value = item[valueKey];
      option.textContent = item[labelKey];
      selectEl.appendChild(option);
    });
  }

  function populateSimpleSelect(selectEl, items) {
    if (!selectEl) return;
    selectEl.innerHTML = '';
    items.forEach((item) => {
      const option = document.createElement('option');
      option.value = item;
      option.textContent = item;
      selectEl.appendChild(option);
    });
  }

  function setMultiSelectValues(selectEl, values) {
    if (!selectEl) return;
    Array.from(selectEl.options).forEach((opt) => {
      opt.selected = values.includes(Number(opt.value)) || values.includes(opt.value);
    });
  }

  function bindModes(modes, selected) {
    const container = el('filterModes');
    if (!container) return;
    container.innerHTML = '';
    modes.forEach((mode) => {
      const id = `mode-${mode}`;
      const wrapper = document.createElement('label');
      wrapper.className = 'form-check form-check-inline';
      wrapper.innerHTML = `
        <input class="form-check-input" type="checkbox" id="${id}" value="${mode}">
        <span class="form-check-label">${mode}</span>
      `;
      container.appendChild(wrapper);
      const input = wrapper.querySelector('input');
      input.checked = selected.includes(mode);
    });
  }

  function collectStateFromUI() {
    const payload = {
      start: el('filterStart').value || '',
      end: el('filterEnd').value || '',
      athletes: Array.from(el('filterAthletes').selectedOptions).map((opt) => Number(opt.value)),
      teams: Array.from(el('filterTeams').selectedOptions).map((opt) => opt.value),
      rifles: Array.from(el('filterRifles').selectedOptions).map((opt) => Number(opt.value)),
      jackets: Array.from(el('filterJackets').selectedOptions).map((opt) => Number(opt.value)),
      scopes: Array.from(el('filterScopes').selectedOptions).map((opt) => Number(opt.value)),
      modes: Array.from(document.querySelectorAll('#filterModes input:checked')).map((el) => el.value),
      include_unassigned: el('filterIncludeUnassigned').checked
    };
    return payload;
  }

  async function loadFilterOptions() {
    const res = await fetch('/analytics/filters');
    const data = await res.json();

    populateSelect(el('filterAthletes'), data.athletes, 'id', 'name');
    populateSimpleSelect(el('filterTeams'), data.teams);
    populateSelect(el('filterRifles'), data.rifles, 'id', 'name');
    populateSelect(el('filterJackets'), data.jackets, 'id', 'name');
    populateSelect(el('filterScopes'), data.scopes, 'id', 'name');

    const saved = readStateFromUrl();
    const stored = readStateFromStorage();
    const merged = {
      start: saved.start || stored.start || data.date_range.min || '',
      end: saved.end || stored.end || data.date_range.max || '',
      athletes: saved.athletes?.length ? saved.athletes : (stored.athletes || []),
      teams: saved.teams?.length ? saved.teams : (stored.teams || []),
      rifles: saved.rifles?.length ? saved.rifles : (stored.rifles || []),
      jackets: saved.jackets?.length ? saved.jackets : (stored.jackets || []),
      scopes: saved.scopes?.length ? saved.scopes : (stored.scopes || []),
      modes: saved.modes?.length ? saved.modes : (stored.modes || data.modes || ['training', 'competition']),
      include_unassigned: saved.include_unassigned ?? stored.include_unassigned ?? false
    };

    el('filterStart').value = merged.start || '';
    el('filterEnd').value = merged.end || '';
    setMultiSelectValues(el('filterAthletes'), merged.athletes);
    setMultiSelectValues(el('filterTeams'), merged.teams);
    setMultiSelectValues(el('filterRifles'), merged.rifles);
    setMultiSelectValues(el('filterJackets'), merged.jackets);
    setMultiSelectValues(el('filterScopes'), merged.scopes);
    bindModes(data.modes || ['training', 'competition', 'standard'], merged.modes || []);
    el('filterIncludeUnassigned').checked = merged.include_unassigned;

    return merged;
  }

  function renderSummary(summary, deltas) {
    el('metricAvgScore').textContent = summary.avg_score.toFixed(2);
    el('metricAvgShot').textContent = summary.avg_shot_score.toFixed(2);
    el('metricRange').textContent = `${summary.min_score.toFixed(0)} - ${summary.max_score.toFixed(0)}`;
    el('metricStdDev').textContent = summary.stddev.toFixed(2);
    el('metricDelta').textContent = deltas.delta.toFixed(2);
    el('metricTrainingAvg').textContent = deltas.training_avg.toFixed(2);
    el('metricCompetitionAvg').textContent = deltas.competition_avg.toFixed(2);
  }

  function renderPerformanceChart(payload) {
    const series = payload.series.map((s) => ({
      name: s.name,
      data: s.data,
      tooltip: { valueDecimals: 1 }
    }));

    if (payload.overall && payload.overall.length) {
      series.unshift({
        name: 'Overall',
        data: payload.overall,
        type: 'line',
        color: '#212529',
        dashStyle: 'ShortDot',
        visible: series.length === 0
      });
    }

    const annotations = [];
    if (payload.best_point) {
      annotations.push({
        labels: [{
          point: { xAxis: 0, yAxis: 0, x: payload.best_point.x, y: payload.best_point.y },
          text: payload.best_point.label
        }]
      });
    }
    if (payload.worst_point) {
      annotations.push({
        labels: [{
          point: { xAxis: 0, yAxis: 0, x: payload.worst_point.x, y: payload.worst_point.y },
          text: payload.worst_point.label
        }]
      });
    }

    charts.performance = Highcharts.stockChart('chartPerformance', {
      chart: {
        zoomType: 'x',
        panning: true,
        panKey: 'shift'
      },
      title: { text: null },
      rangeSelector: {
        selected: 1,
        buttons: [
          { type: 'week', count: 1, text: '1w' },
          { type: 'month', count: 1, text: '1m' },
          { type: 'month', count: 3, text: '3m' },
          { type: 'all', text: 'All' }
        ]
      },
      legend: { enabled: true },
      xAxis: { type: 'datetime' },
      yAxis: {
        title: { text: 'Total Score' }
      },
      tooltip: {
        shared: true,
        valueDecimals: 1
      },
      exporting: { enabled: true },
      annotations,
      series,
      responsive: {
        rules: [{
          condition: { maxWidth: 900 },
          chartOptions: {
            rangeSelector: { inputEnabled: false }
          }
        }]
      }
    });
  }

  function renderComparisonChart(payload) {
    charts.comparison = Highcharts.chart('chartComparison', {
      chart: { type: 'column' },
      title: { text: null },
      xAxis: { categories: payload.categories, title: { text: 'Athletes' } },
      yAxis: [{
        title: { text: 'Average Score' }
      }, {
        title: { text: 'Delta' },
        opposite: true
      }],
      tooltip: {
        shared: true,
        formatter: function () {
          let s = `<b>${this.x}</b>`;
          this.points.forEach((p) => {
            s += `<br/>${p.series.name}: <b>${p.y.toFixed(2)}</b>`;
          });
          return s;
        }
      },
      plotOptions: {
        column: {
          borderRadius: 4
        }
      },
      exporting: { enabled: true },
      series: payload.series,
      responsive: {
        rules: [{
          condition: { maxWidth: 700 },
          chartOptions: {
            legend: { enabled: false }
          }
        }]
      }
    });
  }

  function renderTeamChart(payload) {
    charts.team = Highcharts.chart('chartTeam', {
      chart: { type: 'column' },
      title: { text: null },
      xAxis: { categories: payload.categories },
      yAxis: { title: { text: 'Average Score' } },
      legend: { enabled: false },
      plotOptions: {
        series: { dataLabels: { enabled: true, format: '{point.y:.1f}' } }
      },
      tooltip: {
        formatter: function () {
          return `<b>${this.x}</b><br/>Avg score: ${this.y.toFixed(2)}`;
        }
      },
      drilldown: { series: payload.drilldown },
      exporting: { enabled: true },
      series: payload.series
    });
  }

  function renderScatterChart(payload) {
    charts.scatter = Highcharts.chart('chartScatter', {
      chart: { type: 'scatter', zoomType: 'xy', panning: true, panKey: 'shift' },
      title: { text: null },
      xAxis: { title: { text: 'Shot Score' }, min: 0, max: 10 },
      yAxis: { title: { text: 'Distance from center (mm)' } },
      tooltip: {
        formatter: function () {
          const p = this.point;
          return `<b>${p.athlete}</b><br/>Score: ${p.x}<br/>Distance: ${p.y.toFixed(2)} mm<br/>Mode: ${p.mode}`;
        }
      },
      exporting: { enabled: true },
      series: [{
        name: 'Shots',
        data: payload,
        color: 'rgba(13,110,253,0.55)',
        marker: { radius: 3 }
      }]
    });
  }

  function renderHeatmap(payload) {
    charts.heatmap = Highcharts.chart('chartHeatmap', {
      chart: { type: 'heatmap' },
      title: { text: null },
      xAxis: { categories: payload.xCategories, title: { text: 'Shot index' } },
      yAxis: { categories: payload.yCategories, title: { text: 'Score' }, reversed: true },
      colorAxis: {
        min: 0,
        minColor: '#f8f9fa',
        maxColor: '#0d6efd'
      },
      tooltip: {
        formatter: function () {
          return `Shot ${payload.xCategories[this.point.x]}, Score ${payload.yCategories[this.point.y]}: ${this.point.value}`;
        }
      },
      exporting: { enabled: true },
      series: [{
        name: 'Frequency',
        borderWidth: 1,
        data: payload.data,
        dataLabels: { enabled: false }
      }]
    });
  }

  function renderSeriesChart(payload) {
    charts.series = Highcharts.chart('chartSeries', {
      chart: { type: 'columnrange', inverted: false },
      title: { text: null },
      xAxis: { categories: payload.categories },
      yAxis: { title: { text: 'Total Score' } },
      tooltip: {
        shared: true,
        formatter: function () {
          const point = this.points[0].point;
          return `<b>${this.x}</b><br/>Min: ${point.low.toFixed(1)}<br/>Max: ${point.high.toFixed(1)}`;
        }
      },
      exporting: { enabled: true },
      series: [{
        name: 'Min/Max',
        data: payload.min.map((v, i) => [payload.min[i], payload.max[i]]),
        color: 'rgba(13,110,253,0.4)'
      }, {
        type: 'line',
        name: 'Average',
        data: payload.avg,
        color: '#0d6efd',
        marker: { enabled: true }
      }]
    });
  }

  function renderConsistency(payload) {
    const container = el('consistencyGauges');
    container.innerHTML = '';

    const overall = document.createElement('div');
    overall.className = 'col-12 col-md-4';
    overall.innerHTML = `
      <div class="gauge-card">
        <div class="gauge-title">Overall</div>
        <div id="gauge-overall"></div>
        <div class="gauge-sub">Std dev ${payload.overall.stddev.toFixed(2)}</div>
      </div>
    `;
    container.appendChild(overall);

    const items = payload.items || [];
    items.forEach((item, index) => {
      const col = document.createElement('div');
      col.className = 'col-12 col-md-4';
      col.innerHTML = `
        <div class="gauge-card">
          <div class="gauge-title">${item.name}</div>
          <div id="gauge-${index}"></div>
          <div class="gauge-sub">Std dev ${item.stddev.toFixed(2)}</div>
        </div>
      `;
      container.appendChild(col);
    });

    const gaugeOptions = {
      chart: { type: 'solidgauge', height: 160 },
      title: null,
      pane: {
        center: ['50%', '60%'],
        size: '100%',
        startAngle: -90,
        endAngle: 90,
        background: {
          backgroundColor: '#e9ecef',
          innerRadius: '60%',
          outerRadius: '100%',
          shape: 'arc'
        }
      },
      tooltip: { enabled: false },
      yAxis: {
        min: 0,
        max: 100,
        stops: [
          [0.3, '#dc3545'],
          [0.6, '#ffc107'],
          [1.0, '#198754']
        ],
        lineWidth: 0,
        tickWidth: 0,
        minorTickInterval: null,
        labels: { y: 16 }
      },
      plotOptions: {
        solidgauge: {
          dataLabels: {
            y: -15,
            borderWidth: 0,
            useHTML: true,
            format: '<div style="text-align:center"><span style="font-size:18px">{y:.0f}%</span></div>'
          }
        }
      },
      exporting: { enabled: true },
      credits: { enabled: false }
    };

    Highcharts.chart('gauge-overall', Highcharts.merge(gaugeOptions, {
      series: [{ name: 'Consistency', data: [payload.overall.index] }]
    }));

    items.forEach((item, index) => {
      Highcharts.chart(`gauge-${index}`, Highcharts.merge(gaugeOptions, {
        series: [{ name: 'Consistency', data: [item.index] }]
      }));
    });
  }

  function renderSparklines(list) {
    const table = el('sparklineTable');
    table.innerHTML = '';

    list.forEach((row, idx) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${row.name}</td>
        <td><span class="badge bg-secondary">${row.mode}</span></td>
        <td>${row.updated_at ? new Date(row.updated_at).toLocaleString() : 'N/A'}</td>
        <td><div id="spark-${idx}" class="sparkline"></div></td>
      `;
      table.appendChild(tr);

      Highcharts.SparkLine(`spark-${idx}`, {
        series: [{ data: row.data, color: '#0d6efd' }]
      });
    });
  }

  function renderAthleteTable(payload) {
    const table = el('athleteTable');
    table.innerHTML = '';
    const trendsMap = new Map((payload.trends || []).map((t) => [t.id, t]));
    payload.table.forEach((row) => {
      const trend = trendsMap.get(row.id);
      const icon = trend?.direction === 'up' ? 'bi-arrow-up-right text-success' :
        trend?.direction === 'down' ? 'bi-arrow-down-right text-danger' : 'bi-arrow-right text-muted';
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${row.name}</td>
        <td>${row.team || 'Unassigned'}</td>
        <td>${row.overall_avg.toFixed(2)}</td>
        <td>${row.min.toFixed(0)}</td>
        <td>${row.max.toFixed(0)}</td>
        <td>${row.stddev.toFixed(2)}</td>
        <td>${row.delta.toFixed(2)}</td>
        <td><i class="bi ${icon}"></i></td>
      `;
      table.appendChild(tr);
    });
  }

  async function loadAnalytics() {
    const payload = collectStateFromUI();
    saveStateToStorage(payload);
    applyStateToUrl(payload);

    const res = await fetch(`/analytics/data?${toParams(payload)}`);
    const data = await res.json();

    renderSummary(data.summary, data.training_vs_competition);
    renderPerformanceChart(data.time_series);
    renderComparisonChart(data.comparison);
    renderTeamChart(data.team);
    renderScatterChart(data.distribution.scatter);
    renderHeatmap(data.distribution.heatmap);
    renderSeriesChart(data.series_analysis);
    renderConsistency(data.consistency);
    renderSparklines(data.sparklines);
    renderAthleteTable(data.comparison);
  }

  function bindRealtimeUpdates() {
    const inputs = [
      el('filterStart'),
      el('filterEnd'),
      el('filterAthletes'),
      el('filterTeams'),
      el('filterRifles'),
      el('filterJackets'),
      el('filterScopes'),
      el('filterIncludeUnassigned')
    ];
    inputs.forEach((input) => {
      if (!input) return;
      input.addEventListener('change', debounce(loadAnalytics, 300));
    });
    document.querySelectorAll('#filterModes input').forEach((input) => {
      input.addEventListener('change', debounce(loadAnalytics, 300));
    });

    el('applyFilters').addEventListener('click', loadAnalytics);
    el('resetFilters').addEventListener('click', async () => {
      localStorage.removeItem('analyticsFilters');
      window.history.replaceState({}, '', window.location.pathname);
      const initial = await loadFilterOptions();
      applyStateToUrl(initial);
      await loadAnalytics();
    });
  }

  function debounce(fn, wait) {
    let t;
    return function (...args) {
      clearTimeout(t);
      t = setTimeout(() => fn.apply(this, args), wait);
    };
  }

  document.addEventListener('DOMContentLoaded', async () => {
    await loadFilterOptions();
    await loadAnalytics();
    bindRealtimeUpdates();
  });
})();
