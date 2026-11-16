/*! Kobra X Printer Card – the Anycubic Kobra X with its multi-color unit drawn as one picture,
 *  live values inside. Served by the anycubic_kobra_x_lan integration.
 *
 *  type: custom:kobra-x-printer-card
 *    device:   <device_id of the printer>    (pick it in the card editor)
 *    view:     printer | details | camera    (picture / controls, filament and values / camera with overlay)
 *    plug:     switch.xyz                    (optional smart plug of the printer)
 *    power:    sensor.xyz                    (optional power sensor)
 *    preview:  true                          (show the job thumbnail on the printer screen)
 *    language: auto | cs | en
 *
 *  Idea and layout inspired by ossilampe/bambu-printer-card (MIT).
 *  MIT License
 */
(() => {
  const VERSION = '0.2.0';
  const TAG = 'kobra-x-printer-card';
  const DOMAIN = 'anycubic_kobra_x_lan';

  const L = {
    cs: {
      progress: 'Průběh', remaining: 'Zbývá', done: 'Hotovo v', layer: 'Vrstva', nozzle: 'Tryska', bed: 'Podložka', fan: 'Ventilátor', aux: 'Přídavný',
      empty: 'prázdný', emptyLong: 'Prázdný slot', unknownSlot: 'Neznámý / prázdný', active: 'aktivní', slot: 'Slot',
      offline: 'Tiskárna offline', off: 'vyp', on: 'zap', controls: 'Ovládání', pause: 'Pauza', resume: 'Pokračovat', stop: 'Stop',
      light: 'Světlo', camera: 'Kamera', plug: 'Zásuvka', filament: 'Filament', values: 'Hodnoty', humidity: 'Vlhkost', unit: 'Barevná jednotka', box: 'Box',
      qPause: 'Pozastavit tisk?', aPause: 'Pozastavit', qResume: 'Pokračovat v tisku?', aResume: 'Pokračovat', qStop: 'Opravdu zrušit tisk? Nejde to vrátit.', aStop: 'Zrušit tisk',
      qPlugOffPrint: 'Právě běží tisk! Přesto vypnout zásuvku?', qPlugOff: 'Vypnout zásuvku tiskárny?', qPlugOn: 'Zapnout zásuvku tiskárny?', aOff: 'Vypnout', aOn: 'Zapnout',
      confirm: 'Potvrďte prosím', cancel: 'Zrušit', speedHint: 'Rychlost jde změnit jen během tisku.',
      actual: 'Aktuálně', target: 'Cíl', job: 'Tisková úloha', speed: 'Rychlost', printTime: 'Doba tisku', used: 'Spotřeba', health: 'Stav',
      reason: 'Důvod', lastError: 'Poslední chyba', none: 'žádná', firmware: 'Firmware', connection: 'Spojení', online: 'online', offlineS: 'offline', ip: 'IP',
      power: 'Příkon', tomorrow: 'zítra', drying: 'Sušení', dryStart: 'Sušit', dryStop: 'Zastavit sušení', dryLeft: 'zbývá', autoFeed: 'Auto doplnění',
      qDryStart: 'Spustit sušení filamentu?', qDryStop: 'Zastavit sušení?', refresh: 'Obnovit', preview: 'Náhled',
      noDevice: 'V editoru karty vyberte tiskárnu Anycubic Kobra X.', notFound: 'Pro toto zařízení nebyly nalezeny entity integrace Anycubic Kobra X LAN (je nainstalovaná verze 0.2.0+?).',
      st: { printing: 'Tiskne', paused: 'Pozastaveno', pausing: 'Pozastavuje', resuming: 'Pokračuje', finished: 'Dokončeno', failed: 'Chyba', stopped: 'Zrušeno', idle: 'Připraveno',
        preheating: 'Předehřev', auto_leveling: 'Vyrovnání', downloading: 'Stahuje', checking: 'Kontrola', slicing: 'Slicuje', vibrating: 'Kalibrace vibrací', flow_calibrating: 'Kalibrace průtoku', drying: 'Suší', busy: 'Zaneprázdněna' },
      ed: { device: 'Tiskárna', view: 'Zobrazení', vPrinter: 'Obrázek tiskárny', vDetails: 'Ovládání, filament a hodnoty', vCamera: 'Kamera s hodnotami', plug: 'Zásuvka (volitelné)', power: 'Senzor příkonu (volitelné)', preview: 'Náhled modelu na displeji', lang: 'Jazyk', auto: 'Automaticky' },
    },
    en: {
      progress: 'Progress', remaining: 'Remaining', done: 'Done at', layer: 'Layer', nozzle: 'Nozzle', bed: 'Bed', fan: 'Fan', aux: 'Aux',
      empty: 'empty', emptyLong: 'Empty slot', unknownSlot: 'Unknown / empty', active: 'active', slot: 'Slot',
      offline: 'Printer offline', off: 'off', on: 'on', controls: 'Controls', pause: 'Pause', resume: 'Resume', stop: 'Stop',
      light: 'Light', camera: 'Camera', plug: 'Plug', filament: 'Filament', values: 'Values', humidity: 'Humidity', unit: 'Color unit', box: 'Box',
      qPause: 'Pause the print?', aPause: 'Pause', qResume: 'Resume the print?', aResume: 'Resume', qStop: 'Really cancel the print? This cannot be undone.', aStop: 'Cancel print',
      qPlugOffPrint: 'A print is running! Switch the plug off anyway?', qPlugOff: 'Switch the printer plug off?', qPlugOn: 'Switch the printer plug on?', aOff: 'Switch off', aOn: 'Switch on',
      confirm: 'Please confirm', cancel: 'Cancel', speedHint: 'The speed can only be changed while printing.',
      actual: 'Actual', target: 'Target', job: 'Print job', speed: 'Speed', printTime: 'Print time', used: 'Filament used', health: 'Health',
      reason: 'Reason', lastError: 'Last error', none: 'none', firmware: 'Firmware', connection: 'Connection', online: 'online', offlineS: 'offline', ip: 'IP',
      power: 'Power', tomorrow: 'tomorrow', drying: 'Drying', dryStart: 'Dry', dryStop: 'Stop drying', dryLeft: 'left', autoFeed: 'Auto refill',
      qDryStart: 'Start drying the filament?', qDryStop: 'Stop drying?', refresh: 'Refresh', preview: 'Preview',
      noDevice: 'Please pick an Anycubic Kobra X printer in the card editor.', notFound: 'No Anycubic Kobra X LAN entities were found for this device (is integration 0.2.0+ installed?).',
      st: { printing: 'Printing', paused: 'Paused', pausing: 'Pausing', resuming: 'Resuming', finished: 'Finished', failed: 'Failed', stopped: 'Cancelled', idle: 'Ready',
        preheating: 'Preheating', auto_leveling: 'Leveling', downloading: 'Downloading', checking: 'Checking', slicing: 'Slicing', vibrating: 'Vibration calibration', flow_calibrating: 'Flow calibration', drying: 'Drying', busy: 'Busy' },
      ed: { device: 'Printer', view: 'View', vPrinter: 'Printer picture', vDetails: 'Controls, filament and values', vCamera: 'Camera with values', plug: 'Smart plug (optional)', power: 'Power sensor (optional)', preview: 'Model preview on the screen', lang: 'Language', auto: 'Automatic' },
    },
  };

  const esc = (x) => String(x === undefined || x === null ? '' : x).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  const heat = (t, lo, hi) => { if (isNaN(t)) return '#6E8399'; const k = Math.max(0, Math.min(1, (t - lo) / (hi - lo))); const a = [79, 163, 247], b = [229, 72, 77]; return 'rgb(' + a.map((x, i) => Math.round(x + (b[i] - x) * k)).join(',') + ')'; };
  const remColor = (r) => (isNaN(r) ? '#6E8399' : r <= 15 ? '#E5484D' : r <= 30 ? '#F7AB3E' : '#4CC38A');
  const humColor = (h) => (isNaN(h) ? '#6E8399' : h >= 50 ? '#E5484D' : h >= 40 ? '#F7AB3E' : h >= 30 ? '#F7D04A' : '#4CC38A');
  const PHASE_COLOR = { printing: '#4FA3F7', prepare: '#F7AB3E', paused: '#F7AB3E', finished: '#4CC38A', failed: '#E5484D', stopped: '#E5484D', idle: '#8AA0B6', offline: '#4A5D70' };
  const PREPARE = ['preheating', 'auto_leveling', 'downloading', 'checking', 'slicing', 'vibrating', 'flow_calibrating', 'resuming', 'pausing'];
  const BAD = ['unknown', 'unavailable', '', 'None'];

  const CSS = `
  :host{display:block}
  .karta{background:#0F1A26;border:1px solid #1F3247;border-radius:14px;overflow:hidden;color:#FFF;font-family:Roboto,Arial,sans-serif;line-height:1.3}
  .pad{padding:14px 16px}
  .radek{display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap}
  .titulek{font-size:18px;font-weight:700;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1}
  .chip{display:inline-block;padding:4px 12px;border-radius:12px;font-size:12px;font-weight:700;color:#0F1A26;white-space:nowrap}
  .male{font-size:12px;color:#9FB3C8}
  .chyba{margin-top:6px;color:#FF9EA1;font-size:13px;font-weight:700}
  .lista{height:8px;border-radius:4px;background:#24384E;overflow:hidden;margin:10px 0 8px}
  .lista>div{height:100%;border-radius:4px;transition:width .6s}
  .hodnoty{display:grid;grid-template-columns:repeat(auto-fit,minmax(90px,1fr));gap:6px}
  .hodnota{background:#18293B;border:1px solid #24384E;border-radius:10px;padding:6px 8px;min-width:0}
  .hodnota b{display:block;font-size:15px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .hodnota span{font-size:11px;color:#8AA0B6;font-weight:700}
  svg{display:block;width:100%;height:auto}
  svg text{font-family:Roboto,Arial,sans-serif}
  [data-act]{cursor:pointer}
  .hlava{animation:hlava 6s ease-in-out infinite}
  @keyframes hlava{0%,100%{transform:translateX(-70px)}50%{transform:translateX(70px)}}
  .stul{animation:stul 2.4s ease-in-out infinite}
  @keyframes stul{0%,100%{transform:translateY(0)}50%{transform:translateY(5px)}}
  .puls{animation:puls 1.6s ease-in-out infinite}
  @keyframes puls{0%,100%{opacity:1}50%{opacity:.25}}
  .toc{animation:toc 1s linear infinite;display:inline-block}
  @keyframes toc{to{transform:rotate(360deg)}}
  .tlacitka{display:flex;flex-wrap:wrap;gap:8px}
  .tl{flex:1 1 90px;display:flex;align-items:center;justify-content:center;gap:6px;height:42px;border-radius:12px;border:1px solid #2B4560;background:#18293B;color:#FFF;font:700 13px Roboto,Arial,sans-serif;cursor:pointer;white-space:nowrap;padding:0 10px}
  .tl.zap{background:#2B4560;border-color:#4FA3F7}
  .tl.cerv{border-color:#E5484D;color:#FF9EA1}
  .tl[disabled]{opacity:.45;cursor:default}
  .tl ha-icon{--mdc-icon-size:20px}
  .tempo{display:flex;gap:6px;margin-top:8px;flex-wrap:wrap}
  .tempo .tl{height:34px;font-size:12px;flex:1 1 60px}
  .mrizka{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(300px,100%),1fr));gap:10px}
  .dlazdice{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(150px,100%),1fr));gap:10px}
  .dl{background:#18293B;border:1px solid #24384E;border-radius:12px;overflow:hidden;min-width:0}
  .dl>.pruh{height:5px}
  .dl>.obsah{padding:10px 12px}
  .dt{font-size:12px;font-weight:700;color:#8AA0B6;white-space:nowrap;display:flex;align-items:center;gap:6px}
  .dt ha-icon{--mdc-icon-size:16px}
  .dr{display:flex;justify-content:space-between;gap:8px;font-size:13px;margin-top:5px}
  .dr span:first-child{color:#9FB3C8}
  .dr span:last-child{font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .slot{display:grid;grid-template-columns:34px 1fr auto;gap:10px;align-items:center;padding:8px 0;border-top:1px solid #24384E}
  .barva{width:30px;height:30px;border-radius:50%;box-shadow:inset 0 0 0 2px rgba(255,255,255,.25)}
  .barva.prazdna{background:transparent!important;box-shadow:none;border:1px dashed #4A5D70}
  .sn{font-size:14px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .zbytek{text-align:right;font-size:13px;font-weight:700;min-width:52px}
  .zbytek .mb{height:5px;border-radius:3px;background:#24384E;margin-top:4px;overflow:hidden}
  .zbytek .mb>div{height:100%;border-radius:3px}
  .nadpis{font-size:13px;font-weight:700;color:#C9D6E3;margin:14px 0 8px;display:flex;align-items:center;gap:6px}
  .nadpis:first-child{margin-top:0}
  .susi{display:flex;gap:6px;margin-top:8px}
  .susi .tl{height:32px;font-size:12px}
  .kamera{position:relative;background:#000;aspect-ratio:16/9}
  .kamera hui-image,.kamera img{display:block;width:100%;height:100%;object-fit:contain}
  .prekryv{position:absolute;left:0;right:0;bottom:0;padding:8px 10px;background:linear-gradient(transparent,rgba(0,0,0,.75));display:flex;gap:6px;flex-wrap:wrap;font-size:12px}
  .prekryv span{background:rgba(15,26,38,.8);border-radius:10px;padding:3px 8px;font-weight:700}
  .nahled{width:100%;max-height:220px;object-fit:contain;border-radius:10px;background:#0B1016}
  `;

  // ---------- entity lookup: device + translation_key (= the integration's stable keys) ----------
  function resolve(hass, deviceId) {
    const m = {};
    Object.values(hass.entities || {}).forEach((e) => {
      if (e.device_id === deviceId && e.translation_key) m[e.entity_id.split('.')[0] + ':' + e.translation_key] = e.entity_id;
    });
    const boxes = [];
    for (let n = 1; n <= 4; n++) {
      const pre = n === 1 ? '' : 'box_' + n + '_';
      const slots = [];
      for (let s = 1; s <= 8; s++) { const e = m['sensor:box_' + n + '_slot_' + s]; if (e) slots.push(e); }
      if (!slots.length && !m['sensor:' + pre + 'box_temperature']) continue;
      boxes.push({
        nr: n, idx: n - 1, slots,
        temp: m['sensor:' + pre + 'box_temperature'], hum: m['sensor:' + pre + 'box_humidity'],
        drying: m['binary_sensor:' + pre + 'drying'], dryLeft: m['sensor:' + pre + 'drying_remaining_time'],
        dryStart: m['button:' + pre + 'drying_start'], dryStop: m['button:' + pre + 'drying_stop'],
        autoFeed: m['switch:' + pre + 'auto_feed'],
      });
    }
    const dev = (hass.devices || {})[deviceId] || {};
    return { m, boxes, model: dev.model || 'Kobra X', name: dev.name_by_user || dev.name || 'Anycubic Kobra X' };
  }

  class KobraXPrinterCard extends HTMLElement {
    static getConfigElement() { return document.createElement(TAG + '-editor'); }
    static getStubConfig(hass) {
      const ents = Object.values((hass && hass.entities) || {});
      const e = ents.find((x) => x.platform === DOMAIN && x.device_id);
      return { device: e ? e.device_id : '', view: 'printer' };
    }
    setConfig(c) {
      if (!c) throw new Error('Invalid configuration');
      this._c = Object.assign({ view: 'printer', language: 'auto', preview: true }, c);
      this._key = ''; this._r = null; this._rKey = '';
      if (!this.shadowRoot) { this.attachShadow({ mode: 'open' }); this.shadowRoot.addEventListener('click', (ev) => this._click(ev)); }
      if (this._h) this._render();
    }
    getCardSize() { return this._c && this._c.view === 'details' ? 9 : this._c && this._c.view === 'camera' ? 5 : 11; }
    getGridOptions() { return { columns: 'full', rows: 'auto' }; }
    set hass(h) {
      this._h = h;
      const rk = (this._c && this._c.device) + '|' + Object.keys(h.entities || {}).length + '|' + Object.keys(h.devices || {}).length;
      if (rk !== this._rKey) { this._rKey = rk; this._r = this._c && this._c.device ? resolve(h, this._c.device) : null; this._key = ''; }
      if (this._c && this._c.view === 'camera' && this._cam) this._cam.hass = h;
      const k = this._ids().map((e) => { const s = h.states[e]; return s ? s.state + '@' + s.last_updated : '-'; }).join('|') + '|' + (h.locale && h.locale.language);
      if (k === this._key) return;
      this._key = k;
      this._render();
    }
    get _t() {
      const lang = this._c.language && this._c.language !== 'auto' ? this._c.language : ((this._h && ((this._h.locale && this._h.locale.language) || this._h.language)) || 'en');
      return L[String(lang).slice(0, 2)] || L.en;
    }
    _ids() {
      const r = this._r; if (!r) return [];
      const l = Object.values(r.m);
      if (this._c.plug) l.push(this._c.plug);
      if (this._c.power) l.push(this._c.power);
      return l;
    }
    _e(k) { return this._r && this._r.m[k]; }
    _S(e) { return e ? this._h.states[e] : undefined; }
    _st(e) { const s = this._S(e); return s ? String(s.state) : 'unavailable'; }
    _n(e) { const s = this._S(e); return s ? parseFloat(s.state) : NaN; }
    _on(k) { return this._st(this._e(k)) === 'on'; }
    _int(x) { return isNaN(x) ? '--' : String(Math.round(x)); }
    _min(m) { if (isNaN(m)) return '--'; m = Math.max(0, Math.round(m)); return m >= 60 ? Math.floor(m / 60) + ' h ' + String(m % 60).padStart(2, '0') + ' min' : m + ' min'; }
    _dur(e) {
      let m = this._n(e); if (isNaN(m)) return '--';
      const u = ((this._S(e) || {}).attributes || {}).unit_of_measurement;
      if (u === 'h') m *= 60; else if (u === 's') m /= 60;
      return this._min(m);
    }
    _clock(e) {
      const d = new Date(this._st(e)); if (isNaN(d)) return '--';
      const t0 = new Date(); t0.setHours(0, 0, 0, 0); const d0 = new Date(d); d0.setHours(0, 0, 0, 0);
      const days = Math.round((d0 - t0) / 86400000);
      const hm = String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0');
      return days === 0 ? hm : days === 1 ? this._t.tomorrow + ' ' + hm : d.getDate() + '. ' + (d.getMonth() + 1) + '. ' + hm;
    }
    _jobName() {
      let v = this._st(this._e('sensor:print_task'));
      if (BAD.includes(v)) return '';
      v = v.split('/').pop().replace(/\.gcode(\.3mf)?$|\.3mf$/i, '').replace(/_(PLA|PETG|ABS|ASA|TPU|PA|PC)[^/]*$/i, '');
      return v;
    }
    _slot(e, box) {
      const s = this._S(e); const a = s ? s.attributes : {};
      const unknown = !s || BAD.includes(String(s.state));
      const loaded = Number(a.status) === 5;
      const empty = unknown || !loaded && !a.type;
      let c = a.color_hex || (Array.isArray(a.color) ? '#' + a.color.slice(0, 3).map((x) => Math.max(0, Math.min(255, +x || 0)).toString(16).padStart(2, '0')).join('') : '#888888');
      const rem = Number(a.consumables_percent);
      const sIdx = Number(a.slot_index);
      const act = box && box.loaded === sIdx && !empty;
      return { e, c, empty, unknown, type: a.type || '', sku: a.sku || '', rem: !isNaN(rem) && rem > 0 ? Math.min(100, rem) : NaN, act };
    }
    _boxLoaded() {
      const st = this._S(this._e('sensor:multi_color_box_status'));
      const list = (st && st.attributes && st.attributes.boxes) || [];
      return (i) => { const b = list[i]; return b ? Number(b.loaded_slot) : -1; };
    }
    _status() {
      const lan = this._e('binary_sensor:lan_connection');
      const ps = this._st(this._e('sensor:print_status'));
      const online = (lan ? this._st(lan) === 'on' : true) && this._st(this._e('sensor:nozzle_temperature')) !== 'unavailable';
      let phase = 'idle';
      if (this._on('binary_sensor:print_paused')) phase = 'paused';
      else if (this._on('binary_sensor:print_in_progress')) phase = PREPARE.includes(ps) ? 'prepare' : 'printing';
      else if (this._on('binary_sensor:print_failed')) phase = 'failed';
      else if (this._on('binary_sensor:print_cancelled')) phase = 'stopped';
      else if (this._on('binary_sensor:print_complete')) phase = 'finished';
      const active = ['printing', 'prepare', 'paused'].includes(phase);
      let prog = this._n(this._e('sensor:print_progress'));
      prog = (active || phase === 'finished') && !isNaN(prog) ? Math.max(0, Math.min(100, prog)) : phase === 'finished' ? 100 : 0;
      const t = this._t;
      let txt = phase === 'prepare' ? (t.st[ps] || ps.replace(/_/g, ' ')) : t.st[phase === 'paused' ? 'paused' : phase];
      if (phase === 'idle') { const ps2 = this._st(this._e('sensor:printer_state')); if (ps2 === 'busy') txt = t.st.busy; }
      return { phase, online, active, prog, col: online ? (PHASE_COLOR[phase] || '#8AA0B6') : PHASE_COLOR.offline, txt: online ? txt : t.offline };
    }
    _light() { return this._e('light:light_2') || this._e('light:light_1') || this._e('light:light_3'); }
    // ---------- actions ----------
    _click(ev) {
      const el = ev.composedPath().find((x) => x && x.dataset && x.dataset.act);
      if (!el || el.disabled) return;
      ev.stopPropagation();
      const d = el.dataset;
      if (d.act === 'info') { this.dispatchEvent(new CustomEvent('hass-more-info', { bubbles: true, composed: true, detail: { entityId: d.e } })); return; }
      if (d.act === 'svc') {
        const data = Object.assign({ entity_id: d.e }, d.data ? JSON.parse(d.data) : {});
        const go = () => this._h.callService(d.dom, d.svc, data);
        if (d.ask) this._ask(d.ask, d.yes).then((ok) => { if (ok) go(); }); else go();
      }
    }
    _ask(msg, yes) {
      const t = this._t;
      return new Promise((res) => {
        const o = document.createElement('div');
        o.style.cssText = 'position:fixed;inset:0;z-index:99999;background:rgba(0,0,0,.6);display:flex;align-items:center;justify-content:center;font-family:Roboto,Arial,sans-serif';
        const bs = 'height:42px;padding:0 20px;border-radius:10px;font:700 15px Roboto,Arial,sans-serif;cursor:pointer;';
        o.innerHTML = `<div style="background:#18293B;border:1px solid #2B4560;border-radius:14px;padding:18px;width:calc(100% - 48px);max-width:340px;color:#FFF;box-shadow:0 10px 30px rgba(0,0,0,.5)"><div style="font-size:17px;font-weight:700;margin-bottom:8px">${esc(t.confirm)}</div><div style="font-size:15px;color:#C9D6E3;line-height:1.4">${esc(msg)}</div><div style="display:flex;gap:10px;justify-content:flex-end;margin-top:18px"><button data-a="0" style="${bs}background:#0F1A26;color:#FFF;border:1px solid #2B4560">${esc(t.cancel)}</button><button data-a="1" style="${bs}background:#387DC5;color:#FFF;border:none">${esc(yes || 'OK')}</button></div></div>`;
        const fin = (ok) => { o.remove(); res(ok); };
        o.addEventListener('click', (e) => { const b = e.target.closest('button'); if (b) fin(b.dataset.a === '1'); else if (e.target === o) fin(false); });
        document.body.appendChild(o);
      });
    }
    // ---------- render ----------
    _render() {
      if (!this._h || !this._c || !this.shadowRoot) return;
      let html;
      try {
        if (!this._c.device) html = `<div class="pad male">${esc(this._t.noDevice)}</div>`;
        else if (!this._r || !this._e('sensor:print_status')) html = `<div class="pad male">${esc(this._t.notFound)}</div>`;
        else if (this._c.view === 'camera') { this._renderCamera(); return; }
        else html = this._c.view === 'details' ? this._details() : this._printer();
      } catch (x) { html = `<div class="pad">Kobra X Printer Card: ${esc(x.message)}</div>`; }
      this._cam = null;
      this.shadowRoot.innerHTML = `<style>${CSS}</style><div class="karta">${html}</div>`;
    }
    _header(S, withValues) {
      const t = this._t, E = (k) => this._e(k);
      const job = this._jobName();
      const title = (S.active || S.phase === 'finished') && job ? job : this._r.name;
      let h = `<div class="pad"><div class="radek"><div class="titulek">${esc(title)}</div><span class="chip" style="background:${S.col}">${esc(S.txt)}</span></div>`;
      const reason = this._st(E('sensor:print_reason'));
      if (!BAD.includes(reason) && (S.phase === 'paused' || S.phase === 'failed' || S.phase === 'stopped')) h += `<div class="chyba" data-act="info" data-e="${esc(E('sensor:print_reason'))}">⚠ ${esc(reason)}</div>`;
      else if (S.phase === 'failed' && !BAD.includes(this._st(E('sensor:last_print_error')))) h += `<div class="chyba" data-act="info" data-e="${esc(E('sensor:last_print_error'))}">⚠ ${esc(this._st(E('sensor:last_print_error')))}</div>`;
      if (withValues && (S.active || S.phase === 'finished')) {
        const lay = this._n(E('sensor:current_layer')), layT = this._n(E('sensor:total_layers'));
        h += `<div class="lista"><div style="width:${S.prog}%;background:${S.col}"></div></div><div class="hodnoty">`
          + `<div class="hodnota" data-act="info" data-e="${esc(E('sensor:print_progress'))}"><span>${t.progress}</span><b>${this._int(S.prog)} %</b></div>`
          + `<div class="hodnota" data-act="info" data-e="${esc(E('sensor:remaining_print_time'))}"><span>${t.remaining}</span><b>${S.phase === 'finished' ? '–' : this._dur(E('sensor:remaining_print_time'))}</b></div>`
          + `<div class="hodnota" data-act="info" data-e="${esc(E('sensor:estimated_finish'))}"><span>${t.done}</span><b>${S.phase === 'finished' ? '✓' : this._clock(E('sensor:estimated_finish'))}</b></div>`
          + `<div class="hodnota" data-act="info" data-e="${esc(E('sensor:current_layer'))}"><span>${t.layer}</span><b>${this._int(lay)} / ${this._int(layT)}</b></div></div>`;
      }
      return h + '</div>';
    }
    _pill(x, y, label, value, col, anchor, e) {
      const txt = label + ' ' + value; const w = Math.round(txt.length * 5.9 + 18); const x0 = anchor === 'end' ? x - w : x;
      return `<g${e ? ` data-act="info" data-e="${esc(e)}"` : ''}><rect x="${x0}" y="${y}" width="${w}" height="20" rx="10" fill="#0F1A26" fill-opacity="0.85" stroke="${col}" stroke-width="1.2"/><circle cx="${x0 + 10}" cy="${y + 10}" r="3.5" fill="${col}"/><text x="${x0 + 18}" y="${y + 14}" font-size="10.5" fill="#9FB3C8">${esc(label)} <tspan fill="#FFF" font-weight="700">${esc(value)}</tspan></text></g>`;
    }
    _spool(cx, cy, sl, gap, r) {
      r = r || 15;
      let s = `<g data-act="info" data-e="${esc(sl.e)}"><rect x="${cx - gap / 2 + 2}" y="${cy - r - 14}" width="${gap - 4}" height="${2 * r + 38}" fill="transparent"/>`;
      if (sl.empty) {
        s += `<circle cx="${cx}" cy="${cy}" r="${r + 1}" fill="none" stroke="#4A5D70" stroke-width="1.5" stroke-dasharray="3 3"/><text x="${cx}" y="${cy + 4}" font-size="10" fill="#6E8399" text-anchor="middle">${sl.unknown ? '?' : esc(this._t.empty)}</text>`;
      } else {
        const R = r + 3.5, C = 2 * Math.PI * R, dash = isNaN(sl.rem) ? C : C * sl.rem / 100;
        s += `<circle cx="${cx}" cy="${cy}" r="${R}" fill="none" stroke="#24303C" stroke-width="3"/>`
          + `<circle cx="${cx}" cy="${cy}" r="${R}" fill="none" stroke="${remColor(sl.rem)}" stroke-width="3" stroke-linecap="round" stroke-dasharray="${dash.toFixed(1)} ${C.toFixed(1)}" transform="rotate(-90 ${cx} ${cy})"${isNaN(sl.rem) ? ' stroke-opacity="0.35"' : ''}/>`
          + `<circle cx="${cx}" cy="${cy}" r="${r}" fill="${sl.c}"/><circle cx="${cx}" cy="${cy}" r="${r}" fill="url(#civkaG)"/>`
          + `<circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="#FFF" stroke-opacity="0.28"/><circle cx="${cx}" cy="${cy}" r="${r / 3}" fill="#1B2026" stroke="#5A6672" stroke-width="1.5"/>`;
        if (sl.act) s += `<circle class="puls" cx="${cx}" cy="${cy}" r="${R + 3}" fill="none" stroke="#FFF" stroke-width="1.8"/>`;
      }
      return s;
    }
    _printer() {
      const t = this._t, E = (k) => this._e(k);
      const S = this._status();
      const head = this._header(S, true);
      const lay = this._n(E('sensor:current_layer')), layT = this._n(E('sensor:total_layers'));
      const tN = this._n(E('sensor:nozzle_temperature')), zN = this._n(E('sensor:target_nozzle_temperature'));
      const tB = this._n(E('sensor:bed_temperature')), zB = this._n(E('sensor:target_bed_temperature'));
      const fan = this._n(E('sensor:fan_speed')), aux = this._n(E('sensor:aux_fan_speed'));
      const lightE = this._light(), light = this._st(lightE) === 'on';
      const printing = S.phase === 'printing';
      const loadedOf = this._boxLoaded();
      // ---- built-in color unit (box 1) and expansion boxes, drawn on top of the printer ----
      const boxes = this._r.boxes.map((b) => Object.assign({}, b, { loaded: loadedOf(b.idx) }));
      let partColor = '';
      boxes.forEach((b) => b.slots.forEach((e) => { const sl = this._slot(e, b); if (sl.act && !partColor) partColor = sl.c; }));
      if (!partColor) partColor = '#9AA6B2';
      const rows = Math.ceil(Math.max(0, boxes.length - 1) / 2);
      const topH = rows * 118; // expansion boxes above the printer
      let svgTop = '', pipes = '';
      boxes.slice(1).forEach((b, i) => {
        const row = Math.floor(i / 2), inRow = Math.min(2, boxes.length - 1 - row * 2);
        const w = inRow === 2 ? 188 : 320, x0 = inRow === 2 ? (i % 2 === 0 ? 8 : 204) : 40, y0 = 4 + row * 118;
        svgTop += this._boxSvg(b, x0, y0, w, 108, false);
        const xm = x0 + w / 2, act = b.loaded >= 0 && S.active;
        pipes += `<path d="M${xm} ${y0 + 108} C${xm} ${topH + 20} 200 ${topH + 4} 200 ${topH + 24}" fill="none" stroke="${act ? partColor : '#C9D6E3'}" stroke-opacity="${act ? 1 : 0.25}" stroke-width="${act ? 3 : 2}"/>`;
      });
      // ---- printer (A1-style open-frame bed slinger), drawn from y=0, shifted by Y ----
      const Y = topH + 10;
      const partH = (S.active || S.phase === 'finished') ? Math.round(S.prog * 0.9) : 0;
      const bedTop = 350;
      const gantryY = Math.max(150, bedTop - 34 - partH);
      const nC = heat(tN, 40, 260), bC = heat(tB, 25, 100);
      const unit = boxes[0];
      // filament rack with the built-in 4-color unit on top of the frame
      let pr = `<rect x="40" y="12" width="320" height="104" rx="12" fill="url(#jednotkaG)" stroke="#3A434D"/>`;
      if (unit) pr += this._boxSvg(unit, 40, 12, 320, 104, true);
      else pr += `<text x="200" y="68" font-size="12" fill="#6E8399" text-anchor="middle">${esc(t.unit)}</text>`;
      // frame uprights + top bar
      pr += `<rect x="52" y="116" width="16" height="292" rx="4" fill="url(#ramG)" stroke="#3A434D"/><rect x="332" y="116" width="16" height="292" rx="4" fill="url(#ramG)" stroke="#3A434D"/>`
        + `<rect x="60" y="130" width="2" height="270" fill="#4A535C"/><rect x="338" y="130" width="2" height="270" fill="#4A535C"/>`;
      // light glow
      if (light) pr += `<rect x="68" y="120" width="264" height="270" fill="url(#svetloG)"/>`;
      // part
      const yb = bedTop;
      if (partH > 0) pr += `<g ${printing ? 'class="stul"' : ''}><rect x="172" y="${yb - partH}" width="56" height="${partH}" rx="2" fill="${partColor}"/><rect x="172" y="${yb - partH}" width="56" height="${partH}" rx="2" fill="url(#vrstvyM)"/><rect x="172" y="${yb - partH}" width="56" height="${partH}" rx="2" fill="url(#dilG)"/></g>`;
      // bed (moves in Y -> small bounce while printing)
      pr += `<g ${printing ? 'class="stul"' : ''}><rect x="84" y="${yb}" width="232" height="9" rx="2" fill="#9AA3AB"/><rect x="78" y="${yb + 8}" width="244" height="8" rx="2" fill="#39414A"/></g>`;
      // base with screen
      pr += `<rect x="40" y="398" width="320" height="44" rx="10" fill="url(#ramG)" stroke="#3A434D"/>`
        + `<g data-act="info" data-e="${esc(E('sensor:print_progress'))}"><rect x="232" y="404" width="118" height="32" rx="5" fill="#070A0E" stroke="#4A5D70"/>`
        + (S.online ? `<text x="242" y="425" font-size="${S.active || S.phase === 'finished' ? 15 : 11}" font-weight="700" fill="${S.col}">${S.active || S.phase === 'finished' ? this._int(S.prog) + ' %' : esc(S.txt).slice(0, 15)}</text>`
          + (S.active ? `<text x="344" y="417" font-size="8.5" fill="#9FB3C8" text-anchor="end">${this._int(lay)}/${this._int(layT)}</text><text x="344" y="430" font-size="8.5" fill="#9FB3C8" text-anchor="end">${esc(this._dur(E('sensor:remaining_print_time')))}</text>` : '')
          : `<text x="242" y="424" font-size="12" fill="#4A5D70">${esc(t.off)}</text>`) + `</g>`
        + `<text x="54" y="425" font-size="12" font-weight="700" fill="#C9D6E3" letter-spacing="1">${esc(this._r.model.replace(/^Anycubic\s*/i, '').toUpperCase())}</text>`
        + `<rect x="150" y="436" width="70" height="3" rx="1.5" fill="${S.col}"${printing ? ' class="puls"' : ''}/>`;
      // X gantry (rises with Z) + toolhead
      pr += `<rect x="60" y="${gantryY}" width="280" height="10" rx="3" fill="#262B31" stroke="#3E464F"/>`
        + `<path d="M200 116 C 200 ${(116 + gantryY) / 2} 200 ${(116 + gantryY) / 2} 200 ${gantryY - 14}" fill="none" stroke="${S.active ? partColor : '#C9D6E3'}" stroke-opacity="${S.active ? 0.9 : 0.25}" stroke-width="2.5"/>`
        + `<g ${printing ? 'class="hlava"' : ''}><rect x="178" y="${gantryY - 18}" width="44" height="40" rx="6" fill="#DDE3E8" stroke="#9AA6B2"/><rect x="183" y="${gantryY - 11}" width="34" height="5" rx="2" fill="#2A3036"/><circle cx="210" cy="${gantryY + 8}" r="4.5" fill="none" stroke="#7D8893" stroke-width="1.5"/>`
        + `<path d="M193 ${gantryY + 22} L207 ${gantryY + 22} L203 ${gantryY + 30} L197 ${gantryY + 30} Z" fill="${nC}"/>` + (tN > 150 ? `<circle cx="200" cy="${gantryY + 31}" r="5" fill="${nC}" opacity="0.55"/>` : '') + `</g>`;
      // job preview on the screen side
      const prev = E('image:print_preview');
      const pst = this._S(prev);
      if (this._c.preview !== false && pst && pst.attributes && pst.attributes.entity_picture && S.active) {
        pr += `<g data-act="info" data-e="${esc(prev)}"><rect x="272" y="136" width="56" height="56" rx="8" fill="#0B1016" stroke="#4A5D70"/><image href="${esc(pst.attributes.entity_picture)}" x="275" y="139" width="50" height="50" preserveAspectRatio="xMidYMid meet"/></g>`;
      }
      // values
      const nT = E('number:target_nozzle_temperature_control') || E('sensor:target_nozzle_temperature');
      const bT = E('number:target_bed_temperature_control') || E('sensor:target_bed_temperature');
      pr += this._pill(76, Math.max(140, gantryY - 46), t.nozzle, this._int(tN) + (isNaN(zN) || zN <= 0 ? ' °C' : ' / ' + this._int(zN) + ' °C'), nC, 'start', nT)
        + this._pill(76, yb + 21, t.bed, this._int(tB) + (isNaN(zB) || zB <= 0 ? ' °C' : ' / ' + this._int(zB) + ' °C'), bC, 'start', bT)
        + (fan > 0 ? this._pill(326, Math.max(140, gantryY - 46) + (prev && S.active && this._c.preview !== false ? 60 : 0), t.fan, this._int(fan) + ' %', '#4FA3F7', 'end', E('number:model_fan_speed_control') || E('sensor:fan_speed')) : '')
        + (aux > 0 ? this._pill(326, Math.max(140, gantryY - 46) + (prev && S.active && this._c.preview !== false ? 84 : 24), t.aux, this._int(aux) + ' %', '#4FA3F7', 'end', E('number:aux_fan_speed_control') || E('sensor:aux_fan_speed')) : '');
      // light toggle
      if (lightE) pr += `<g data-act="svc" data-dom="light" data-svc="toggle" data-e="${esc(lightE)}"><circle cx="370" cy="150" r="13" fill="${light ? '#F7D04A' : '#18293B'}" stroke="${light ? '#F7D04A' : '#4A5D70'}"/><path d="M370 142 a5 5 0 0 1 3 9 v2 h-6 v-2 a5 5 0 0 1 3 -9z M367.5 155 h5 v2 h-5z" fill="${light ? '#0F1A26' : '#8AA0B6'}"/></g>`;
      const cam = E('switch:camera_stream');
      if (cam) { const co = this._st(cam) === 'on'; pr += `<g data-act="svc" data-dom="switch" data-svc="toggle" data-e="${esc(cam)}"><circle cx="370" cy="184" r="13" fill="${co ? '#4FA3F7' : '#18293B'}" stroke="${co ? '#4FA3F7' : '#4A5D70'}"/><rect x="362" y="179" width="11" height="10" rx="2" fill="${co ? '#0F1A26' : '#8AA0B6'}"/><path d="M373 182 l5 -3 v10 l-5 -3z" fill="${co ? '#0F1A26' : '#8AA0B6'}"/></g>`; }
      const H = 450 + Y;
      const off = S.online ? '' : `<rect x="0" y="0" width="400" height="${H}" fill="#0F1A26" fill-opacity="0.6"/><text x="200" y="${260 + Y}" font-size="22" font-weight="700" fill="#8AA0B6" text-anchor="middle">${esc(t.offline)}</text>`;
      const defs = `<defs>
        <linearGradient id="jednotkaG" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#353C44"/><stop offset="1" stop-color="#20252B"/></linearGradient>
        <linearGradient id="ramG" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2E343A"/><stop offset="1" stop-color="#16191D"/></linearGradient>
        <radialGradient id="svetloG" cx="0.5" cy="0.2" r="0.9"><stop offset="0" stop-color="#FFE8B8" stop-opacity="0.28"/><stop offset="1" stop-color="#FFE8B8" stop-opacity="0"/></radialGradient>
        <radialGradient id="civkaG" cx="0.35" cy="0.3" r="0.75"><stop offset="0" stop-color="#FFF" stop-opacity="0.35"/><stop offset="0.6" stop-color="#FFF" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity="0.3"/></radialGradient>
        <linearGradient id="dilG" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#000" stop-opacity="0.25"/><stop offset="0.4" stop-color="#FFF" stop-opacity="0.12"/><stop offset="1" stop-color="#000" stop-opacity="0.35"/></linearGradient>
        <pattern id="vrstvyM" width="4" height="3" patternUnits="userSpaceOnUse"><rect width="4" height="1" fill="#000" fill-opacity="0.18"/></pattern>
      </defs>`;
      const svg = `<svg viewBox="0 0 400 ${H}" xmlns="http://www.w3.org/2000/svg">${defs}${pipes}${svgTop}<g transform="translate(0 ${Y})">${pr}</g>${off}</svg>`;
      return head + `<div style="padding:0 10px 12px">${svg}</div>`;
    }
    _boxSvg(b, x0, y0, w, h, builtIn) {
      const t = this._t;
      const temp = this._n(b.temp), hum = this._n(b.hum), drying = this._st(b.drying) === 'on';
      let g = builtIn ? '' : `<rect x="${x0}" y="${y0}" width="${w}" height="${h}" rx="12" fill="url(#jednotkaG)" stroke="#3A434D"/>`;
      g += `<rect x="${x0 + 8}" y="${y0 + 8}" width="${w - 16}" height="${h - 34}" rx="9" fill="#0B1016" stroke="${drying ? '#F7AB3E' : '#2B3540'}"/>`
        + `<text x="${x0 + 12}" y="${y0 + h - 9}" font-size="12" font-weight="700" fill="#C9D6E3">${esc(b.nr === 1 ? t.unit : t.box + ' ' + b.nr)}</text>`;
      const wide = w >= 240;
      let right = '';
      if (b.hum && !isNaN(hum)) right += `<tspan fill="${humColor(hum)}">💧${this._int(hum)}%</tspan> `;
      if (b.temp && !isNaN(temp) && wide) right += `<tspan fill="#FFF">${this._int(temp)} °C</tspan>`;
      if (drying) right = `<tspan fill="#F7AB3E">♨${wide ? ' ' + esc(this._dur(b.dryLeft)) : ''}</tspan> ` + right;
      if (right) g += `<text x="${x0 + w - 12}" y="${y0 + h - 9}" font-size="11.5" font-weight="700" text-anchor="end" data-act="info" data-e="${esc(b.hum || b.temp)}">${right}</text>`;
      const n = Math.max(4, b.slots.length), gap = (w - 16) / n, off = (w - 16 - gap * b.slots.length) / 2;
      const r = builtIn ? 17 : 14, cy = y0 + 8 + (h - 34) / 2 - 6;
      b.slots.forEach((e, i) => {
        const sl = this._slot(e, b);
        const cx = Math.round(x0 + 8 + off + gap / 2 + gap * i);
        g += this._spool(cx, cy, sl, gap, r)
          + `<text x="${cx}" y="${cy + r + 15}" font-size="9.5" fill="${sl.act ? '#FFF' : '#8AA0B6'}" text-anchor="middle" font-weight="${sl.act ? 700 : 400}">${wide ? (i + 1) + ' · ' : ''}${sl.empty ? '–' : esc(sl.type || '?')}${isNaN(sl.rem) || sl.empty || !wide ? '' : ' ' + this._int(sl.rem) + '%'}</text></g>`;
      });
      return g;
    }
    _tile(title, icon, color, rows, e) {
      return `<div class="dl"${e ? ` data-act="info" data-e="${esc(e)}"` : ''}><div class="pruh" style="background:${color}"></div><div class="obsah"><div class="dt"><ha-icon icon="${icon}"></ha-icon>${esc(title)}</div>${rows.filter(Boolean).map((z) => `<div class="dr"><span>${esc(z[0])}</span><span${z[2] ? ` style="color:${z[2]}"` : ''}>${z[1]}</span></div>`).join('')}</div></div>`;
    }
    _btn(txt, icon, dom, svc, e, o) {
      o = o || {};
      if (!e) return '';
      return `<button class="tl${o.on ? ' zap' : ''}${o.red ? ' cerv' : ''}" data-act="svc" data-dom="${dom}" data-svc="${svc}" data-e="${esc(e)}"${o.ask ? ` data-ask="${esc(o.ask)}" data-yes="${esc(o.yes || 'OK')}"` : ''}${o.data ? ` data-data="${esc(JSON.stringify(o.data))}"` : ''}${o.disabled ? ' disabled' : ''}>${icon ? `<ha-icon icon="${icon}"></ha-icon>` : ''}${esc(txt)}</button>`;
    }
    _details() {
      const t = this._t, E = (k) => this._e(k), btn = this._btn.bind(this);
      const S = this._status();
      const ph = ((Date.now() % 1000) / 1000).toFixed(2);
      let h = `<div class="pad"><div class="nadpis"><ha-icon icon="mdi:gesture-tap-button"></ha-icon>${t.controls}</div><div class="tlacitka">`;
      if (S.phase === 'printing' || S.phase === 'prepare') h += btn(t.pause, 'mdi:pause', 'button', 'press', E('button:pause_print'), { ask: t.qPause, yes: t.aPause });
      if (S.phase === 'paused') h += btn(t.resume, 'mdi:play', 'button', 'press', E('button:resume_print'), { ask: t.qResume, yes: t.aResume });
      if (S.active) h += btn(t.stop, 'mdi:stop', 'button', 'press', E('button:cancel_print'), { red: 1, ask: t.qStop, yes: t.aStop });
      const lightE = this._light(), li = this._st(lightE) === 'on';
      h += btn(t.light, li ? 'mdi:lightbulb-on' : 'mdi:lightbulb-outline', 'light', 'toggle', lightE, { on: li });
      const ca = this._st(E('switch:camera_stream')) === 'on';
      h += btn(t.camera, ca ? 'mdi:cctv' : 'mdi:cctv-off', 'switch', 'toggle', E('switch:camera_stream'), { on: ca });
      if (this._c.plug && this._S(this._c.plug)) {
        const so = this._st(this._c.plug) === 'on';
        h += btn(t.plug, 'mdi:power-plug', this._c.plug.split('.')[0], so ? 'turn_off' : 'turn_on', this._c.plug, { on: so, red: so && S.active, ask: so ? (S.active ? t.qPlugOffPrint : t.qPlugOff) : t.qPlugOn, yes: so ? t.aOff : t.aOn });
      }
      h += btn(t.refresh, 'mdi:refresh', 'button', 'press', E('button:refresh_data'));
      h += `</div>`;
      const sel = this._S(E('select:print_speed_mode_select'));
      if (sel) {
        const opts = sel.attributes.options || [];
        if (opts.length) h += `<div class="tempo">` + opts.map((o) => btn(o, '', 'select', 'select_option', sel.entity_id, { on: sel.state === o, data: { option: o }, disabled: !S.active || sel.state === 'unavailable' })).join('') + `</div>`;
        if (!S.active) h += `<div class="male" style="margin-top:4px">${esc(t.speedHint)}</div>`;
      }
      // job preview
      const prev = this._S(E('image:print_preview'));
      if (this._c.preview !== false && prev && prev.attributes.entity_picture && prev.state !== 'unavailable') {
        h += `<div class="nadpis"><ha-icon icon="mdi:image-outline"></ha-icon>${t.preview}</div><img class="nahled" data-act="info" data-e="${esc(prev.entity_id)}" src="${esc(prev.attributes.entity_picture)}">`;
      }
      // filament
      const loadedOf = this._boxLoaded();
      const row = (sl, label) => {
        return `<div class="slot" data-act="info" data-e="${esc(sl.e)}"><div class="barva${sl.empty ? ' prazdna' : ''}" style="background:${sl.c}${sl.act ? ';box-shadow:0 0 0 3px #0F1A26,0 0 0 5px #FFF' : ''}"></div>`
          + `<div style="min-width:0"><div class="male">${esc(label)}${sl.act ? ` · <b style="color:#FFF">${t.active}</b>` : ''}</div><div class="sn">${sl.empty ? (sl.unknown ? t.unknownSlot : t.emptyLong) : esc(sl.type || '?')}</div><div class="male">${esc(sl.sku)}</div></div>`
          + `<div class="zbytek">${sl.empty ? '–' : isNaN(sl.rem) ? '?' : this._int(sl.rem) + ' %'}${sl.empty || isNaN(sl.rem) ? '' : `<div class="mb"><div style="width:${sl.rem}%;background:${remColor(sl.rem)}"></div></div>`}</div></div>`;
      };
      if (this._r.boxes.length) {
        h += `<div class="nadpis"><ha-icon icon="mdi:palette-swatch-variant"></ha-icon>${t.filament}</div><div class="mrizka">`;
        this._r.boxes.forEach((b0) => {
          const b = Object.assign({}, b0, { loaded: loadedOf(b0.idx) });
          const hum = this._n(b.hum), temp = this._n(b.temp), drying = this._st(b.drying) === 'on';
          h += `<div class="dl"><div class="obsah"><div class="radek"><div style="font-size:15px;font-weight:700">${esc(b.nr === 1 ? t.unit : t.box + ' ' + b.nr)}</div><div class="male">`
            + (b.hum && !isNaN(hum) ? `<span data-act="info" data-e="${esc(b.hum)}" style="color:${humColor(hum)};font-weight:700">💧 ${t.humidity} ${this._int(hum)} %</span>` : '')
            + (b.temp && !isNaN(temp) ? ` · <span data-act="info" data-e="${esc(b.temp)}">${this._int(temp)} °C</span>` : '') + `</div></div>`;
          b.slots.forEach((e, i) => { h += row(this._slot(e, b), t.slot + ' ' + (i + 1)); });
          if (b.dryStart || b.autoFeed) {
            h += `<div class="susi">`;
            if (drying) h += btn(t.dryStop + ' (' + this._dur(b.dryLeft) + ')', 'mdi:stop', 'button', 'press', b.dryStop, { on: 1, ask: t.qDryStop, yes: t.dryStop });
            else h += btn(t.dryStart, 'mdi:heat-wave', 'button', 'press', b.dryStart, { ask: t.qDryStart, yes: t.dryStart, disabled: S.active });
            if (b.autoFeed) { const af = this._st(b.autoFeed) === 'on'; h += btn(t.autoFeed, 'mdi:autorenew', 'switch', 'toggle', b.autoFeed, { on: af }); }
            h += `</div>`;
          }
          h += `</div></div>`;
        });
        h += `</div>`;
      }
      // tiles
      const tN = this._n(E('sensor:nozzle_temperature')), zN = this._n(E('sensor:target_nozzle_temperature'));
      const tB = this._n(E('sensor:bed_temperature')), zB = this._n(E('sensor:target_bed_temperature'));
      const fanRow = (label, k) => { const e = E(k); if (!e) return null; const x = this._n(e); return [label, (x > 0 ? `<span class="toc" style="animation-delay:-${ph}s">✻</span> ` : '') + this._int(x) + ' %']; };
      const lan = this._st(E('binary_sensor:lan_connection')) === 'on';
      const reason = this._st(E('sensor:print_reason')), lastErr = this._st(E('sensor:last_print_error'));
      h += `<div class="nadpis"><ha-icon icon="mdi:information-outline"></ha-icon>${t.values}</div><div class="dlazdice">`;
      h += this._tile(t.nozzle, 'mdi:printer-3d-nozzle-heat', heat(tN, 40, 260), [[t.actual, this._int(tN) + ' °C'], [t.target, isNaN(zN) || zN <= 0 ? t.off : this._int(zN) + ' °C']], E('number:target_nozzle_temperature_control') || E('sensor:nozzle_temperature'));
      h += this._tile(t.bed, 'mdi:radiator', heat(tB, 25, 100), [[t.actual, this._int(tB) + ' °C'], [t.target, isNaN(zB) || zB <= 0 ? t.off : this._int(zB) + ' °C']], E('number:target_bed_temperature_control') || E('sensor:bed_temperature'));
      h += this._tile(t.fan, 'mdi:fan', '#4FA3F7', [fanRow(t.fan, 'sensor:fan_speed'), fanRow(t.aux, 'sensor:aux_fan_speed')], E('number:model_fan_speed_control'));
      h += this._tile(t.job, 'mdi:file-cad-box', '#B98AF0', [
        [t.speed, esc(BAD.includes(this._st(E('sensor:print_speed_mode_name'))) ? '--' : this._st(E('sensor:print_speed_mode_name'))) + (isNaN(this._n(E('sensor:print_speed_pct'))) ? '' : ' · ' + this._int(this._n(E('sensor:print_speed_pct'))) + ' %')],
        E('sensor:print_time') ? [t.printTime, esc(this._dur(E('sensor:print_time')))] : null,
        E('sensor:filament_used') && !isNaN(this._n(E('sensor:filament_used'))) ? [t.used, this._int(this._n(E('sensor:filament_used'))) + ' g'] : null,
      ], E('sensor:print_task'));
      const bad = S.phase === 'failed' || (!BAD.includes(reason) && S.phase === 'paused');
      h += this._tile(t.health, 'mdi:shield-check', bad ? '#E5484D' : '#4CC38A', [
        [t.reason, BAD.includes(reason) ? t.none : esc(reason), BAD.includes(reason) ? '' : '#FF9EA1'],
        [t.lastError, BAD.includes(lastErr) ? t.none : esc(lastErr), BAD.includes(lastErr) ? '' : '#FF9EA1'],
        E('sensor:firmware_version') ? [t.firmware, esc(this._st(E('sensor:firmware_version')))] : null,
      ], E('event:print_event') || E('sensor:print_reason'));
      h += this._tile(t.connection, 'mdi:lan', lan ? '#4CC38A' : '#4A5D70', [[t.connection, lan ? t.online : t.offlineS, lan ? '' : '#FF9EA1'], E('sensor:ip') ? [t.ip, esc(this._st(E('sensor:ip')))] : null], E('binary_sensor:lan_connection'));
      if (this._c.power && this._S(this._c.power)) {
        const p = this._n(this._c.power);
        h += this._tile(t.power, 'mdi:flash', '#F7AB3E', [[t.power, isNaN(p) ? '--' : this._int(p) + ' W'], this._c.plug && this._S(this._c.plug) ? [t.plug, this._st(this._c.plug) === 'on' ? t.on : t.off] : null], this._c.power);
      }
      h += `</div></div>`;
      return h;
    }
    // camera view: live camera with the key values on top
    _renderCamera() {
      const t = this._t, E = (k) => this._e(k), S = this._status();
      const camE = E('camera:camera');
      if (!this._cam || this._camEntity !== camE) {
        this.shadowRoot.innerHTML = `<style>${CSS}</style><div class="karta"><div class="hl"></div><div class="kamera"></div></div>`;
        this._camEntity = camE;
        const box = this.shadowRoot.querySelector('.kamera');
        if (camE) {
          const img = document.createElement('hui-image');
          img.hass = this._h; img.cameraImage = camE; img.cameraView = 'live'; img.entity = camE;
          img.addEventListener('click', () => this.dispatchEvent(new CustomEvent('hass-more-info', { bubbles: true, composed: true, detail: { entityId: camE } })));
          box.appendChild(img);
          this._cam = img;
        } else { this._cam = { set hass(x) {} }; }
        const ov = document.createElement('div'); ov.className = 'prekryv'; box.appendChild(ov);
      }
      this.shadowRoot.querySelector('.hl').innerHTML = this._header(S, true);
      const tN = this._n(E('sensor:nozzle_temperature')), tB = this._n(E('sensor:bed_temperature'));
      this.shadowRoot.querySelector('.prekryv').innerHTML = `<span style="color:${S.col}">${esc(S.txt)}</span><span>${t.nozzle} ${this._int(tN)} °C</span><span>${t.bed} ${this._int(tB)} °C</span>`
        + (S.active ? `<span>${t.layer} ${this._int(this._n(E('sensor:current_layer')))}/${this._int(this._n(E('sensor:total_layers')))}</span>` : '');
    }
  }

  // ---------- visual editor ----------
  class KobraXPrinterCardEditor extends HTMLElement {
    setConfig(c) { this._c = Object.assign({}, c); this._draw(); }
    set hass(h) { this._h = h; this._draw(); }
    _draw() {
      if (!this._h || !this._c) return;
      const lang = String((this._h.locale && this._h.locale.language) || 'en').slice(0, 2);
      const t = (L[lang] || L.en).ed;
      if (!this._f) {
        this._f = document.createElement('ha-form');
        this._f.computeLabel = (s) => ({ device: t.device, view: t.view, plug: t.plug, power: t.power, preview: t.preview, language: t.lang })[s.name] || s.name;
        this._f.addEventListener('value-changed', (ev) => {
          this._c = Object.assign({}, this._c, ev.detail.value);
          this.dispatchEvent(new CustomEvent('config-changed', { detail: { config: this._c }, bubbles: true, composed: true }));
        });
        this.appendChild(this._f);
      }
      this._f.hass = this._h;
      this._f.data = Object.assign({ preview: true }, this._c);
      this._f.schema = [
        { name: 'device', required: true, selector: { device: { integration: DOMAIN } } },
        { name: 'view', selector: { select: { mode: 'dropdown', options: [{ value: 'printer', label: t.vPrinter }, { value: 'details', label: t.vDetails }, { value: 'camera', label: t.vCamera }] } } },
        { name: 'plug', selector: { entity: { domain: ['switch', 'light', 'input_boolean'] } } },
        { name: 'power', selector: { entity: { domain: 'sensor', device_class: 'power' } } },
        { name: 'preview', selector: { boolean: {} } },
        { name: 'language', selector: { select: { mode: 'dropdown', options: [{ value: 'auto', label: t.auto }, { value: 'cs', label: 'Čeština' }, { value: 'en', label: 'English' }] } } },
      ];
    }
  }

  if (!customElements.get(TAG)) customElements.define(TAG, KobraXPrinterCard);
  if (!customElements.get(TAG + '-editor')) customElements.define(TAG + '-editor', KobraXPrinterCardEditor);
  window.customCards = window.customCards || [];
  if (!window.customCards.find((c) => c.type === TAG)) window.customCards.push({ type: TAG, name: 'Kobra X Printer Card', description: 'Anycubic Kobra X with its color unit as one picture, live values, controls and filament', preview: false });
  console.info('%c KOBRA-X-PRINTER-CARD %c ' + VERSION, 'background:#4FA3F7;color:#0F1A26;font-weight:700', '');
})();
