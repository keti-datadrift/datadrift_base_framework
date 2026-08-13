// ddoc serve · GUI · Round 15 (+ Round 16 viz / i18n)
//
// Single-file JS that drives the 6 form builders, validation, CLI
// command preview, and result rendering against the REST endpoints
// shipped in Round 14. No frameworks; no build step.

(() => {
  'use strict';

  // ── Round-16 i18n ───────────────────────────────────────────────
  // Tiny string table — `?lang=ko` query (or localStorage cache)
  // switches headings/tab labels to Korean. Body labels (CLI option
  // names) stay verbatim because they map 1-to-1 to ddoc CLI flags.
  const I18N = {
    en: {
      'tab.drift':     'Analyze drift',
      'tab.eda':       'Analyze EDA',
      'tab.examples':  'Examples',
      'tab.report':    'Report',
      'tab.export':    'Export',
      'tab.fetch':     'Fetch',
      'tab.recipe':    'Recipe',
      'cli.title':     'Generated CLI command',
      'cli.copy':      'Copy',
      'cli.copied':    'copied',
      'submit':        'Submit',
      'submit.fix':    'fix the chips above',
      'result.title':  'Result',
      'result.download': 'Download envelope',
      'result.raw':    'Raw JSON',
      'auth.label':    'X-API-Key',
      'auth.clear':    'clear',
      'lang.toggle':   '한국어',
      'cli.hint':      'The form on the left maps 1-to-1 to ddoc CLI options. Submit calls the equivalent REST endpoint; this panel shows what you would run in a terminal for the same effect.',
    },
    ko: {
      'tab.drift':     '드리프트 분석',
      'tab.eda':       'EDA 분석',
      'tab.examples':  '예제 데이터',
      'tab.report':    '리포트',
      'tab.export':    '외부 발신',
      'tab.fetch':     '데이터 가져오기',
      'tab.recipe':    '레시피',
      'cli.title':     '생성된 CLI 명령어',
      'cli.copy':      '복사',
      'cli.copied':    '복사됨',
      'submit':        '실행',
      'submit.fix':    '위 오류 chip 을 먼저 해결해주세요',
      'result.title':  '결과',
      'result.download': 'envelope 다운로드',
      'result.raw':    '원본 JSON',
      'auth.label':    'X-API-Key',
      'auth.clear':    '지움',
      'lang.toggle':   'English',
      'cli.hint':      '좌측 form 은 ddoc CLI 옵션과 1대1 매핑됩니다. Submit 시 동일 동작의 REST endpoint 가 호출되며, 이 패널은 터미널에서 직접 입력할 동등한 명령어를 보여줍니다.',
    },
  };

  function detectLang() {
    const params = new URLSearchParams(location.search);
    const fromQuery = params.get('lang');
    if (fromQuery && I18N[fromQuery]) return fromQuery;
    const stored = localStorage.getItem('ddoc_serve_lang');
    if (stored && I18N[stored]) return stored;
    return 'en';
  }

  let LANG = detectLang();
  const t = (key) => (I18N[LANG] && I18N[LANG][key]) || I18N.en[key] || key;

  // ── State ────────────────────────────────────────────────────────
  const STATE = {
    health: null,
    detectors: null,        // /plugins/detectors response
    examples: null,         // /examples/scenarios response
    library: null,          // /recipes response (lazy-loaded on Recipe tab)
    activeTab: 'drift',
    forms: {},              // tab → {state object}
    apiKey: localStorage.getItem('ddoc_serve_api_key') || '',
    writeToken: localStorage.getItem('ddoc_serve_write_token') || '',
    adminToken: localStorage.getItem('ddoc_serve_admin_token') || '',
  };

  function libraryRecipeOptions() {
    const items = STATE.library?.recipes || [];
    return ['', ...items.map(r => r.name)];
  }

  // ── DOM helpers ──────────────────────────────────────────────────
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  function el(tag, attrs = {}, ...children) {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (k === 'class') node.className = v;
      else if (k === 'html') node.innerHTML = v;
      else if (k.startsWith('on') && typeof v === 'function') {
        node.addEventListener(k.slice(2).toLowerCase(), v);
      } else if (v !== false && v !== null && v !== undefined) {
        node.setAttribute(k, v === true ? '' : String(v));
      }
    }
    for (const child of children.flat()) {
      if (child == null) continue;
      node.appendChild(typeof child === 'string' ? document.createTextNode(child) : child);
    }
    return node;
  }

  // ── HTTP helpers (with auth) ────────────────────────────────────
  function authHeaders(extra = {}) {
    const out = { ...extra };
    if (STATE.apiKey) out['X-API-Key'] = STATE.apiKey;
    if (STATE.writeToken) out['X-Recipes-Write-Token'] = STATE.writeToken;
    if (STATE.adminToken) out['X-Recipes-Admin-Token'] = STATE.adminToken;
    return out;
  }

  async function api(method, path, body) {
    const init = {
      method,
      headers: authHeaders({ 'Content-Type': 'application/json' }),
    };
    if (body !== undefined) init.body = JSON.stringify(body);
    const r = await fetch(path, init);
    let json = null;
    try { json = await r.json(); } catch (_) { /* non-JSON */ }
    return { ok: r.ok, status: r.status, json };
  }

  // ── Bootstrap ────────────────────────────────────────────────────
  async function bootstrap() {
    const [health, detectors, examples, library] = await Promise.all([
      api('GET', '/healthz'),
      api('GET', '/plugins/detectors'),
      api('GET', '/examples/scenarios'),
      api('GET', '/recipes'),
    ]);
    STATE.health = health.json || {};
    STATE.detectors = detectors.json || { count: 0, registry: [] };
    STATE.examples = examples.json || { modalities: [], scenarios: [] };
    STATE.library = library.json || null;

    applyI18n();
    renderTopbar();
    renderForms();
    renderActiveTab();
  }

  function applyI18n() {
    document.documentElement.lang = LANG;
    // Tab labels.
    const tabKeys = { drift: 'tab.drift', eda: 'tab.eda', examples: 'tab.examples',
                      report: 'tab.report', export: 'tab.export', fetch: 'tab.fetch' };
    $$('#tabs .tab').forEach(b => {
      const k = tabKeys[b.dataset.tab];
      if (k) b.textContent = t(k);
    });
    // CLI panel header / button.
    const cliHeader = $('.cli-panel h3');
    if (cliHeader) cliHeader.textContent = t('cli.title');
    $('#copy-cli').textContent = t('cli.copy');
    const cliHintP = $('.cli-panel .hint');
    if (cliHintP) cliHintP.innerHTML = t('cli.hint');
    // Submit button label.
    $('#submit').textContent = t('submit');
    // Result heading + download.
    $('.result-panel h3').textContent = t('result.title');
    $('#result-download').textContent = t('result.download');
    const detailsSummary = $('.result-panel details summary');
    if (detailsSummary) detailsSummary.textContent = t('result.raw');
    // Auth label / clear button.
    const authLabel = $('#auth-block label');
    if (authLabel) {
      authLabel.firstChild.nodeValue = t('auth.label') + ' ';
    }
    $('#auth-clear').textContent = t('auth.clear');
    // Lang toggle button (rendered in topbar).
    const tog = $('#lang-toggle');
    if (tog) tog.textContent = t('lang.toggle');
  }

  // ── Topbar ───────────────────────────────────────────────────────
  function renderTopbar() {
    const h = STATE.health || {};
    const lib = STATE.library || {};
    const tags = [
      `v${h.ddoc_version || '?'}`,
      `${h.plugin_count ?? '?'} plugins`,
      `auth: ${h.auth_enabled ? 'ON' : 'OFF'}`,
    ];
    if (lib.write_enabled) tags.push('write: ON');
    if (lib.git_enabled) tags.push('git: ON');
    $('#meta').textContent = '· ' + tags.join(' · ');

    // Language toggle button (Round 16 — switches en ↔ ko).
    if (!$('#lang-toggle')) {
      const btn = el('button', {
        id: 'lang-toggle', class: 'link', style: 'margin-left: 0.6em;',
        onclick: () => {
          LANG = LANG === 'ko' ? 'en' : 'ko';
          localStorage.setItem('ddoc_serve_lang', LANG);
          applyI18n();
          // Re-render forms so labels update too where applicable.
          renderForms();
          renderActiveTab();
        },
      }, t('lang.toggle'));
      $('#topbar').appendChild(btn);
    }

    const authBlock = $('#auth-block');
    if (h.auth_enabled) {
      authBlock.hidden = false;
      const input = $('#api-key');
      input.value = STATE.apiKey;
      input.addEventListener('change', () => {
        STATE.apiKey = input.value.trim();
        localStorage.setItem('ddoc_serve_api_key', STATE.apiKey);
      });
      $('#auth-clear').addEventListener('click', () => {
        STATE.apiKey = '';
        input.value = '';
        localStorage.removeItem('ddoc_serve_api_key');
      });
    } else {
      authBlock.hidden = true;
    }
  }

  // ── Tab switching ────────────────────────────────────────────────
  $$('#tabs .tab').forEach(btn => {
    btn.addEventListener('click', async () => {
      STATE.activeTab = btn.dataset.tab;
      $$('#tabs .tab').forEach(b => b.classList.toggle('active', b === btn));
      $$('.builder').forEach(b => b.classList.toggle('active', b.dataset.builder === STATE.activeTab));
      // Lazy-load the library on first Recipe tab open.
      if (STATE.activeTab === 'recipe' && STATE.library === null) {
        const r = await api('GET', '/recipes');
        STATE.library = r.json || { recipes: [] };
        renderForms();   // re-render so dropdown picks up the new options
      }
      renderActiveTab();
    });
  });

  // ── Form schemas (one per tab) ──────────────────────────────────
  // Each schema: array of { name, label, type, opts?, default?, help?,
  // required?, depends? }. depends is a function that returns true to
  // show this field given the current form state.

  function detectorOptions() {
    const supported = new Set(['default']);
    for (const d of (STATE.detectors?.registry || [])) {
      for (const s of d.supported || []) supported.add(s);
    }
    return Array.from(supported);
  }

  // Sample recipe text shown by default in the recipe tab. Declared
  // before SCHEMAS to avoid the temporal-dead-zone gotcha.
  const SAMPLE_RECIPE_YAML = [
    'name: timeseries-drift-smoke',
    'vars:',
    '  data_root: /tmp/ddoc_recipe_smoke',
    'steps:',
    '  - id: gen_pair',
    '    run: examples.generate',
    '    with:',
    '      modality: timeseries',
    '      out: "${vars.data_root}"',
    '      scenario: shifted',
    '  - id: drift',
    '    run: analyze.drift',
    '    with:',
    '      data_path_ref: "${vars.data_root}/ref"',
    '      data_path_cur: "${vars.data_root}/cur"',
    '      quiet: true',
    '  - id: report_md',
    '    run: report.render',
    '    when: "${steps.drift.json.overall_score} > 0.1"',
    '    with:',
    '      input: "${steps.drift.output}"',
    '      out: /tmp/ddoc_recipe_smoke/report.md',
    '      format: md',
    '',
  ].join('\n');

  const SCHEMAS = {
    drift: {
      title: 'Analyze drift',
      help: 'Compare two datasets (path mode or snapshot mode). Path mode is the orchestrator-friendly form — pass concrete directories.',
      fields: [
        { name: 'data_path_ref', label: 'data-path-ref', type: 'text', help: 'Baseline directory (path mode)' },
        { name: 'data_path_cur', label: 'data-path-cur', type: 'text', help: 'Current directory (path mode)' },
        { name: 'baseline', label: 'baseline', type: 'text', help: 'Baseline snapshot ID/alias (snapshot mode — leave paths blank)' },
        { name: 'current', label: 'current', type: 'text', help: 'Current snapshot ID/alias (snapshot mode)' },
        { name: 'detector', label: 'detector', type: 'select', opts: () => detectorOptions(), default: 'default' },
        { name: 'fusion', label: 'fusion', type: 'select', opts: ['none', 'weighted', 'max', 'joint'], default: 'none' },
        { name: 'fusion_weights', label: 'fusion-weights', type: 'text', help: 'e.g. image=0.6,text=0.4 (only used when fusion ≠ none)' },
        { name: 'with_embeddings', label: 'with-embeddings', type: 'check', default: false, help: 'Path mode: load CLIP inline (vision/text)' },
        { name: 'quiet', label: 'quiet', type: 'check', default: true },
        { name: 'use_streaming', label: 'Use streaming (SSE)', type: 'check', default: false, help: 'Show NDJSON progress events live (uses /analyze/drift/stream)' },
        { name: 'timeout_sec', label: 'timeout-sec', type: 'text', default: '600' },
      ],
    },
    eda: {
      title: 'Analyze EDA',
      help: 'Run exploratory data analysis on a snapshot, the workspace, or an arbitrary path.',
      fields: [
        { name: 'snapshot', label: 'snapshot', type: 'text', help: 'Snapshot ID or alias (omit for path/workspace mode)' },
        { name: 'data_path', label: 'data-path', type: 'text', help: 'Path-mode input directory' },
        { name: 'invalidate_cache', label: 'invalidate-cache', type: 'check', default: false },
        { name: 'save_snapshot', label: 'save-snapshot', type: 'check', default: false },
        { name: 'strict_hash', label: 'strict-hash', type: 'check', default: false },
        { name: 'quiet', label: 'quiet', type: 'check', default: true },
        { name: 'timeout_sec', label: 'timeout-sec', type: 'text', default: '600' },
      ],
    },
    examples: {
      title: 'Examples · generate toy data',
      help: 'Materialize a (ref, cur) toy dataset pair for the given modality.',
      fields: [
        { name: 'modality', label: 'modality', type: 'select', opts: () => STATE.examples?.modalities || [], required: true },
        { name: 'scenario', label: 'scenario', type: 'select', opts: () => STATE.examples?.scenarios || [], default: 'shifted' },
        { name: 'out', label: 'out', type: 'text', required: true, help: 'Output dir; will contain ref/ and cur/ subdirs.' },
      ],
    },
    report: {
      title: 'Render report',
      help: 'Render a drift / EDA envelope JSON to HTML / PDF / Markdown.',
      fields: [
        { name: 'input', label: 'input', type: 'text', required: true, help: 'Path to a drift / EDA envelope JSON.' },
        { name: 'out', label: 'out', type: 'text', required: true, help: 'Output report path; format inferred from suffix unless explicit.' },
        { name: 'format', label: 'format', type: 'select', opts: ['', 'html', 'pdf', 'md'], help: 'Empty = infer from --out suffix.' },
        { name: 'title', label: 'title', type: 'text' },
        { name: 'timeout_sec', label: 'timeout-sec', type: 'text', default: '120' },
      ],
    },
    export: {
      title: 'Export drift report',
      help: 'Ship a drift envelope to file:// or keti_veritas (or any plugin-registered target).',
      fields: [
        { name: 'input', label: 'input', type: 'text', required: true, help: 'Drift envelope JSON path.' },
        { name: 'target', label: 'target', type: 'select', opts: ['file', 'keti_veritas'], default: 'file', required: true },
        { name: 'config_json', label: 'config (JSON)', type: 'textarea', help: 'file: {"out_dir":"…"}; keti_veritas: {"base_url":"http://…","api_key":"…"}' },
        { name: 'timeout_sec', label: 'timeout-sec', type: 'text', default: '120' },
      ],
    },
    fetch: {
      title: 'Fetch · materialize remote data',
      help: 'Pull data from a URI (file/s3/gs/http) into a local directory; built-in file:// fallback. Plugins may register more schemes.',
      fields: [
        { name: 'source_uri', label: 'source-uri', type: 'text', required: true, help: 'file:///path, bare path, or s3://… (plugin required for non-file).' },
        { name: 'dest', label: 'dest', type: 'text', required: true },
        { name: 'symlink', label: 'symlink', type: 'check', default: false, help: 'file:// only; create symlink instead of copy.' },
        { name: 'config_json', label: 'config (JSON)', type: 'textarea', help: 'Adapter-specific JSON; e.g. {"region":"us-east-1"} for s3.' },
        { name: 'timeout_sec', label: 'timeout-sec', type: 'text', default: '120' },
      ],
    },
    recipe: {
      title: 'Recipe · multi-step workflow',
      help: 'Paste a recipe YAML or specify a server-side path. ddoc executes the steps in order and shows per-step progress as SSE events.',
      fields: [
        // Round 20 — load from library dropdown (populated lazily on
        // tab activate via /recipes).
        { name: 'library_pick', label: 'load from library', type: 'select', opts: () => libraryRecipeOptions(), default: '' },
        { name: 'mode', label: 'input mode', type: 'select', opts: ['inline', 'path'], default: 'inline' },
        { name: 'yaml', label: 'YAML', type: 'textarea', default: SAMPLE_RECIPE_YAML, help: 'Top-level: name, vars, steps[]. Each step needs id + run + with.' },
        { name: 'path', label: 'recipe path', type: 'text', help: 'Server-side path to a YAML file (use this instead of YAML when --inline isn\'t convenient).' },
        { name: 'save_as', label: 'save as (name)', type: 'text', help: 'Round 20: save current YAML to library at /recipes/<name>. Requires DDOC_RECIPES_WRITE=1 server-side.' },
        { name: 'dry_run', label: 'dry-run', type: 'check', default: false, help: 'Resolve substitutions and print argv but skip subprocess execution.' },
        { name: 'use_streaming', label: 'Use streaming (SSE)', type: 'check', default: true, help: 'Show per-step progress live (uses /recipe/run/stream).' },
        { name: 'validate_only', label: 'validate only', type: 'check', default: false, help: 'Call /recipe/validate instead of running.' },
      ],
    },
  };

  // ── Form rendering ───────────────────────────────────────────────
  function renderForms() {
    for (const [tab, schema] of Object.entries(SCHEMAS)) {
      const root = $(`.builder[data-builder="${tab}"]`);
      root.innerHTML = '';
      root.appendChild(el('h2', {}, schema.title));
      if (schema.help) root.appendChild(el('p', { class: 'help' }, schema.help));

      const formState = {};
      STATE.forms[tab] = formState;

      const checkRow = el('div', { class: 'row-checkbox' });
      let hasCheckboxes = false;

      for (const f of schema.fields) {
        const def = (typeof f.default === 'function') ? f.default() : f.default;
        if (def !== undefined) formState[f.name] = def;

        if (f.type === 'check') {
          hasCheckboxes = true;
          const input = el('input', {
            type: 'checkbox', id: `${tab}-${f.name}`,
            checked: !!def,
          });
          input.addEventListener('change', () => {
            formState[f.name] = input.checked;
            updateCli();
            validate();
          });
          checkRow.appendChild(el('label', { for: input.id }, input, ` ${f.label}`));
          if (f.help) {
            const help = el('span', { class: 'help-inline' }, ` (${f.help})`);
            checkRow.lastChild.appendChild(help);
          }
          continue;
        }

        const fieldRow = el('div', { class: 'field' });
        fieldRow.appendChild(el('label', { for: `${tab}-${f.name}` }, f.label + (f.required ? ' *' : '')));

        let input;
        if (f.type === 'select') {
          const opts = (typeof f.opts === 'function') ? f.opts() : f.opts;
          input = el('select', { id: `${tab}-${f.name}` },
            ...opts.map(o => el('option', { value: o, selected: o === def }, o || '(infer)')));
        } else if (f.type === 'textarea') {
          input = el('textarea', { id: `${tab}-${f.name}` });
          if (def) input.value = def;
        } else {
          input = el('input', { type: 'text', id: `${tab}-${f.name}` });
          if (def !== undefined) input.value = def;
        }
        input.addEventListener('input', () => {
          formState[f.name] = input.value;
          updateCli();
          validate();
        });
        input.addEventListener('change', () => {
          formState[f.name] = input.value;
          updateCli();
          validate();
        });
        fieldRow.appendChild(input);
        if (f.help) {
          fieldRow.appendChild(el('span', { class: 'help-inline' }, f.help));
        }
        root.appendChild(fieldRow);
      }
      if (hasCheckboxes) root.appendChild(checkRow);
    }
    // Round 20 — recipe tab needs extra wiring beyond the generic
    // schema-driven form: load-from-library (dropdown change → fetch
    // /recipes/<name> and prefill YAML) and Save button.
    wireRecipeTab();
  }

  function wireRecipeTab() {
    const root = $('.builder[data-builder="recipe"]');
    if (!root) return;
    const formState = STATE.forms.recipe || {};

    const dropdown = $('#recipe-library_pick', root);
    if (dropdown && !dropdown.dataset._wired) {
      dropdown.dataset._wired = '1';
      dropdown.addEventListener('change', async () => {
        const pick = dropdown.value;
        if (!pick) return;
        const r = await api('GET', '/recipes/' + encodeURIComponent(pick));
        if (r.ok && r.json && r.json.yaml) {
          const yamlField = $('#recipe-yaml', root);
          if (yamlField) {
            yamlField.value = r.json.yaml;
            formState.yaml = r.json.yaml;
          }
          formState.save_as = pick;
          const saveAs = $('#recipe-save_as', root);
          if (saveAs) saveAs.value = pick;
          updateCli();
          validate();
        }
      });
    }

    // Inject Save + Round 21 controls (Delete / Restore latest / Diff
    // vs latest) into the actions row if not already present.
    if (!$('#recipe-save-btn')) {
      const saveBtn = el('button', {
        id: 'recipe-save-btn',
        type: 'button',
        class: 'recipe-save',
        onclick: () => saveRecipeFromForm(),
        title: 'PUT /recipes/<save_as> (requires DDOC_RECIPES_WRITE=1)',
      }, 'Save to library');
      saveBtn.classList.add('tab-only-recipe');
      $('.actions').appendChild(saveBtn);

      const diffBtn = el('button', {
        id: 'recipe-diff-btn',
        type: 'button',
        class: 'recipe-save',
        onclick: () => diffRecipeFromForm(),
        title: 'GET /recipes/<save_as>/diff — HEAD vs latest snapshot',
      }, 'Compare');
      diffBtn.classList.add('tab-only-recipe');
      $('.actions').appendChild(diffBtn);

      const restoreBtn = el('button', {
        id: 'recipe-restore-btn',
        type: 'button',
        class: 'recipe-save',
        onclick: () => restoreRecipeFromForm(),
        title: 'POST /recipes/<save_as>/restore/<latest snapshot>',
      }, 'Restore latest');
      restoreBtn.classList.add('tab-only-recipe');
      $('.actions').appendChild(restoreBtn);

      const deleteBtn = el('button', {
        id: 'recipe-delete-btn',
        type: 'button',
        class: 'recipe-save recipe-delete',
        onclick: () => deleteRecipeFromForm(),
        title: 'DELETE /recipes/<save_as> (auto-archives current first)',
      }, 'Delete');
      deleteBtn.classList.add('tab-only-recipe');
      $('.actions').appendChild(deleteBtn);
    }
    refreshSaveButtonVisibility();
    refreshWriteTokenInput();
  }

  // Round 22 — surface a write-token input only when the server
  // demands one (DDOC_RECIPES_WRITE_TOKEN env). Cached in localStorage
  // so users don't retype on every save.
  function refreshWriteTokenInput() {
    const required = !!(STATE.library && STATE.library.write_token_required);
    let row = $('#recipe-write-token-row');
    if (!required) {
      if (row) row.remove();
      return;
    }
    if (row) return;
    const input = el('input', {
      type: 'password',
      id: 'recipe-write-token-input',
      placeholder: 'X-Recipes-Write-Token',
      value: STATE.writeToken || '',
      style: 'flex:1;padding:0.4em 0.6em;border:1px solid var(--border);border-radius:var(--radius);',
    });
    input.addEventListener('input', () => {
      STATE.writeToken = input.value.trim();
      if (STATE.writeToken) localStorage.setItem('ddoc_serve_write_token', STATE.writeToken);
      else localStorage.removeItem('ddoc_serve_write_token');
    });
    row = el('div', {
      id: 'recipe-write-token-row',
      class: 'tab-only-recipe',
      style: 'display:flex;gap:0.5em;align-items:center;margin-top:0.5em;',
    },
      el('label', { for: 'recipe-write-token-input', style: 'color:var(--muted);font-size:12.5px;' },
        'write token'),
      input);
    const root = $('.builder[data-builder="recipe"]');
    if (root) root.appendChild(row);
  }

  function refreshSaveButtonVisibility() {
    const ids = ['#recipe-save-btn', '#recipe-diff-btn',
                 '#recipe-restore-btn', '#recipe-delete-btn',
                 '#recipe-write-token-row'];
    const show = STATE.activeTab === 'recipe';
    for (const id of ids) {
      const btn = $(id);
      if (!btn) continue;
      if (id === '#recipe-write-token-row') {
        btn.style.display = show ? 'flex' : 'none';
      } else {
        btn.style.display = show ? '' : 'none';
      }
    }
  }

  async function saveRecipeFromForm() {
    const formState = STATE.forms.recipe || {};
    const name = (formState.save_as || '').trim();
    if (!name) {
      alert('Set "save as (name)" before saving.');
      return;
    }
    const yaml = formState.yaml || '';
    if (!yaml.trim()) {
      alert('YAML is empty.');
      return;
    }
    const r = await api('PUT', '/recipes/' + encodeURIComponent(name), { yaml });
    showResult({ status: 'pending', body: { status: 'submitting…' } });
    renderResultBody(r);
    // Refresh the library so the dropdown picks up new entries.
    const lib = await api('GET', '/recipes');
    STATE.library = lib.json || STATE.library;
    renderForms();
  }

  // Round 21 — diff / restore / delete handlers.
  function _recipeNameFromForm(action) {
    const formState = STATE.forms.recipe || {};
    const name = (formState.save_as || '').trim();
    if (!name) {
      alert('Set "save as (name)" before ' + action + '.');
      return null;
    }
    return name;
  }

  async function diffRecipeFromForm() {
    const name = _recipeNameFromForm('comparing');
    if (!name) return;
    showResult({ status: 'pending', body: { status: 'diffing…' } });
    const r = await api('GET', '/recipes/' + encodeURIComponent(name) + '/diff');
    renderResultBody(r);
  }

  async function restoreRecipeFromForm() {
    const name = _recipeNameFromForm('restoring');
    if (!name) return;
    const versions = await api('GET',
      '/recipes/' + encodeURIComponent(name) + '/versions');
    const list = (versions.json && versions.json.versions) || [];
    if (!list.length) {
      alert('No archived versions for "' + name + '" yet.');
      return;
    }
    const ts = list[0].timestamp;
    if (!confirm('Restore "' + name + '" to snapshot ' + ts +
                 '?\n(current active will be archived first)')) return;
    showResult({ status: 'pending', body: { status: 'restoring…' } });
    const r = await api('POST',
      '/recipes/' + encodeURIComponent(name) +
      '/restore/' + encodeURIComponent(ts));
    renderResultBody(r);
    // Refresh form YAML from the restored content.
    if (r.ok) {
      const fetched = await api('GET', '/recipes/' + encodeURIComponent(name));
      if (fetched.ok && fetched.json && fetched.json.yaml) {
        const yamlField = document.querySelector('#recipe-yaml');
        const formState = STATE.forms.recipe || {};
        if (yamlField) yamlField.value = fetched.json.yaml;
        formState.yaml = fetched.json.yaml;
      }
    }
  }

  async function deleteRecipeFromForm() {
    const name = _recipeNameFromForm('deleting');
    if (!name) return;
    if (!confirm('Delete "' + name + '" from the library?\n' +
                 '(content is auto-archived under .history/ — recoverable via Restore)')) return;
    showResult({ status: 'pending', body: { status: 'deleting…' } });
    const r = await api('DELETE', '/recipes/' + encodeURIComponent(name));
    renderResultBody(r);
    if (r.ok) {
      const lib = await api('GET', '/recipes');
      STATE.library = lib.json || STATE.library;
      renderForms();
    }
  }

  function renderActiveTab() {
    updateCli();
    validate();
    hideResult();
    refreshSaveButtonVisibility();
  }

  // ── Validation ───────────────────────────────────────────────────
  function validateCurrent() {
    const tab = STATE.activeTab;
    const schema = SCHEMAS[tab];
    const state = STATE.forms[tab] || {};
    const errors = [];

    for (const f of schema.fields) {
      if (f.required) {
        const v = state[f.name];
        if (v === undefined || v === '' || v === null) {
          errors.push(`${f.label} is required`);
        }
      }
    }

    if (tab === 'drift') {
      const hasPaths = state.data_path_ref && state.data_path_cur;
      const hasSnaps = state.baseline && state.current;
      if (!hasPaths && !hasSnaps) {
        errors.push('Provide either both data-path-ref + data-path-cur (path mode) or both baseline + current (snapshot mode)');
      }
      if (state.fusion && state.fusion !== 'none' && state.fusion !== 'weighted' && state.fusion_weights) {
        errors.push('fusion-weights only applies when fusion=weighted');
      }
      const det = state.detector;
      if (det && det !== 'default') {
        const allow = detectorOptions();
        if (!allow.includes(det)) errors.push(`detector ${det} is not in /plugins/detectors`);
      }
    }
    if (tab === 'eda' && !state.snapshot && !state.data_path) {
      // Not an error — EDA's workspace mode (no snapshot, no path) is
      // legal — but warn if user clears both expecting a different mode.
    }
    if ((tab === 'export' || tab === 'fetch') && state.config_json) {
      try {
        const parsed = JSON.parse(state.config_json);
        if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
          errors.push('config must be a JSON object');
        }
      } catch (_) {
        errors.push('config: invalid JSON');
      }
    }
    if (state.timeout_sec !== undefined && state.timeout_sec !== '') {
      const t = Number(state.timeout_sec);
      if (!Number.isFinite(t) || t < 0) errors.push('timeout-sec must be a non-negative number');
    }

    return errors;
  }

  function validate() {
    const errors = validateCurrent();
    const errorsBox = $('#errors');
    errorsBox.innerHTML = '';
    for (const e of errors) {
      errorsBox.appendChild(el('span', { class: 'error-chip' }, e));
    }
    $('#submit').disabled = errors.length > 0;
    $('#submit-hint').textContent = errors.length ? 'fix the chips above' : '';
  }

  // ── argv builders + endpoint mappers ─────────────────────────────
  function buildArgv(tab, state) {
    const args = [];
    const pushOpt = (flag, val) => {
      if (val === undefined || val === null || val === '') return;
      args.push(flag, String(val));
    };
    const pushFlag = (flag, on) => { if (on) args.push(flag); };

    if (tab === 'drift') {
      args.push('analyze', 'drift');
      if (state.baseline) args.push(state.baseline);
      if (state.current) args.push(state.current);
      pushOpt('--data-path-ref', state.data_path_ref);
      pushOpt('--data-path-cur', state.data_path_cur);
      if (state.detector && state.detector !== 'default') pushOpt('--detector', state.detector);
      if (state.fusion && state.fusion !== 'none') pushOpt('--fusion', state.fusion);
      pushOpt('--fusion-weights', state.fusion_weights);
      pushFlag('--with-embeddings', state.with_embeddings);
      args.push('--json');
      pushFlag('--quiet', state.quiet);
      if (state.use_streaming) args.push('--ndjson-progress');
    } else if (tab === 'eda') {
      args.push('analyze', 'eda');
      if (state.snapshot) args.push(state.snapshot);
      pushOpt('--data-path', state.data_path);
      pushFlag('--invalidate-cache', state.invalidate_cache);
      pushFlag('--save-snapshot', state.save_snapshot);
      pushFlag('--strict-hash', state.strict_hash);
      args.push('--json');
      pushFlag('--quiet', state.quiet);
    } else if (tab === 'examples') {
      args.push('examples', 'generate', state.modality || '<modality>');
      pushOpt('--out', state.out);
      pushOpt('--scenario', state.scenario);
    } else if (tab === 'report') {
      args.push('report', 'render');
      pushOpt('-i', state.input);
      pushOpt('-o', state.out);
      pushOpt('--format', state.format);
      pushOpt('--title', state.title);
      args.push('--json');
    } else if (tab === 'export') {
      args.push('export', 'drift-report');
      if (state.input) args.push(state.input);
      pushOpt('--to', state.target);
      if (state.config_json) pushOpt('--config', state.config_json);
      args.push('--json');
    } else if (tab === 'fetch') {
      args.push('fetch');
      if (state.source_uri) args.push(state.source_uri);
      pushOpt('--dest', state.dest);
      pushFlag('--symlink', state.symlink);
      if (state.config_json) pushOpt('--config', state.config_json);
      args.push('--json');
    } else if (tab === 'recipe') {
      // CLI hint mirrors `ddoc recipe {validate,run} <path>` form.
      // For inline mode we suggest writing to a file first; the GUI's
      // actual submit hits the REST endpoint with the YAML body.
      const verb = state.validate_only ? 'validate' : 'run';
      args.push('recipe', verb);
      if (state.mode === 'path' && state.path) {
        args.push(state.path);
      } else if (state.mode === 'inline') {
        args.push('<recipe.yaml>');
      }
      if (verb === 'run') {
        if (state.dry_run) args.push('--dry-run');
        args.push('--json');
      } else {
        args.push('--json');
      }
    }
    return args;
  }

  function quoteArg(a) {
    if (/^[A-Za-z0-9_./:=,-]+$/.test(a)) return a;
    return `'${String(a).replace(/'/g, `'\\''`)}'`;
  }

  function updateCli() {
    const tab = STATE.activeTab;
    const args = buildArgv(tab, STATE.forms[tab] || {});
    $('#cli-hint').textContent = ['ddoc', ...args.map(quoteArg)].join(' ');
  }

  // ── Endpoint dispatch ───────────────────────────────────────────
  function buildRequest(tab, state) {
    const body = { ...state };
    if (tab === 'drift') {
      const useStream = !!body.use_streaming;
      delete body.use_streaming;
      body.timeout_sec = Number(body.timeout_sec) || 600;
      return { path: useStream ? '/analyze/drift/stream' : '/analyze/drift', body, sse: useStream };
    }
    if (tab === 'eda') {
      body.timeout_sec = Number(body.timeout_sec) || 600;
      return { path: '/analyze/eda', body, sse: false };
    }
    if (tab === 'examples') {
      return { path: '/examples/generate', body: {
        modality: body.modality, scenario: body.scenario, out: body.out,
      }, sse: false };
    }
    if (tab === 'report') {
      const out = {
        input: body.input, out: body.out,
        format: body.format || null, title: body.title || null,
        timeout_sec: Number(body.timeout_sec) || 120,
      };
      return { path: '/report/render', body: out, sse: false };
    }
    if (tab === 'export') {
      let cfg = null;
      if (body.config_json) {
        try { cfg = JSON.parse(body.config_json); } catch (_) { cfg = null; }
      }
      return {
        path: '/export/drift-report',
        body: {
          input: body.input, target: body.target,
          config: cfg, timeout_sec: Number(body.timeout_sec) || 120,
        },
        sse: false,
      };
    }
    if (tab === 'fetch') {
      let cfg = null;
      if (body.config_json) {
        try { cfg = JSON.parse(body.config_json); } catch (_) { cfg = null; }
      }
      return {
        path: '/fetch',
        body: {
          source_uri: body.source_uri, dest: body.dest,
          symlink: !!body.symlink, config: cfg,
          timeout_sec: Number(body.timeout_sec) || 120,
        },
        sse: false,
      };
    }
    if (tab === 'recipe') {
      const recipeBody = {};
      if (body.mode === 'inline') recipeBody.yaml = body.yaml;
      else if (body.mode === 'path' && body.path) recipeBody.path = body.path;
      recipeBody.dry_run = !!body.dry_run;
      if (body.validate_only) {
        return { path: '/recipe/validate', body: recipeBody, sse: false };
      }
      const useStream = !!body.use_streaming && !body.dry_run;
      return {
        path: useStream ? '/recipe/run/stream' : '/recipe/run',
        body: recipeBody,
        sse: useStream,
      };
    }
  }

  // ── Submit ──────────────────────────────────────────────────────
  $('#submit').addEventListener('click', async () => {
    const tab = STATE.activeTab;
    if (validateCurrent().length) return;
    const req = buildRequest(tab, STATE.forms[tab] || {});
    showResult({ status: 'pending', body: { status: 'submitting…' } });
    if (req.sse) {
      await streamRequest(req.path, req.body);
    } else {
      const r = await api('POST', req.path, req.body);
      renderResultBody(r);
    }
  });

  function showResult(initial) {
    $('#result-panel').hidden = false;
    $('#result-progress').hidden = true;
    $('#result-progress').innerHTML = '';
    $('#result-status').textContent = initial?.status || '';
    $('#result-status').className = '';
    $('#result-body').textContent = JSON.stringify(initial?.body ?? {}, null, 2);
    $('#result-download').hidden = true;
    $('#result-render').hidden = true;
  }
  function hideResult() { $('#result-panel').hidden = true; }

  function renderResultBody(r) {
    const ok = r.ok && r.json && r.json.status !== 'error';
    const statusEl = $('#result-status');
    statusEl.textContent = `HTTP ${r.status} ${ok ? 'OK' : (r.json?.error_code || 'error')}`;
    statusEl.className = ok ? 'ok' : 'err';
    $('#result-body').textContent = JSON.stringify(r.json ?? {}, null, 2);
    renderViz(r.json, ok);

    // Drift / EDA envelope: surface convenience actions.
    if (ok && r.json && (r.json.modality || r.json.modalities)) {
      const dl = $('#result-download');
      dl.hidden = false;
      dl.onclick = () => {
        const blob = new Blob([JSON.stringify(r.json, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = `${r.json.modality || 'envelope'}.json`;
        a.click();
        URL.revokeObjectURL(url);
      };
    } else {
      $('#result-download').hidden = true;
    }
  }

  // ── Round-16 result viz ─────────────────────────────────────────
  // Renders score / status / per-attribute bars from the envelope. Pure
  // CSS (no chart libs). Falls back to "raw only" when nothing to viz.
  function renderViz(envelope, ok) {
    const viz = $('#result-viz');
    viz.innerHTML = '';
    if (!envelope || typeof envelope !== 'object') { viz.hidden = true; return; }

    // Round 22 — recipe diff envelope: render unified-diff with line
    // colors (purely visual; raw text remains in #result-body).
    if (typeof envelope.diff === 'string' &&
        (typeof envelope.from !== 'undefined' || typeof envelope.to !== 'undefined')) {
      viz.appendChild(diffCard(envelope));
      viz.hidden = false;
      return;
    }

    // Multi-modal stack (drift): each modality gets its own card.
    if (envelope.modalities && typeof envelope.modalities === 'object') {
      const grid = el('div', { class: 'modality-grid' });
      for (const [name, sub] of Object.entries(envelope.modalities)) {
        grid.appendChild(modalityCard(name, sub));
      }
      viz.appendChild(grid);
      if (typeof envelope.fused_score === 'number') {
        viz.appendChild(fusionCard(envelope));
      }
      viz.hidden = false;
      return;
    }

    // Single-modality drift / EDA envelope (modality + overall_score
    // or files_analyzed/series_analyzed/...).
    if (envelope.modality) {
      viz.appendChild(modalityCard(envelope.modality, envelope));
      viz.hidden = false;
      return;
    }

    // Recipe envelope: list of step results.
    if (Array.isArray(envelope.steps) && envelope.steps.length) {
      viz.appendChild(recipeCard(envelope));
      viz.hidden = false;
      return;
    }

    // Status-only success (e.g. /report/render returns {status: success,
    // format, output_path, size_bytes}).
    if (ok && envelope.status === 'success' && envelope.output_path) {
      viz.appendChild(statusCard(envelope));
      viz.hidden = false;
      return;
    }

    viz.hidden = true;
  }

  function classifyScore(score) {
    if (score == null || !isFinite(score)) return 'normal';
    if (score < 0.15) return 'normal';
    if (score < 0.25) return 'warning';
    return 'critical';
  }

  function modalityCard(name, sub) {
    const card = el('div', { class: 'viz-card' });
    card.appendChild(el('h4', {}, name));

    if (sub.status === 'error') {
      card.appendChild(el('div', { class: 'big critical' }, 'error'));
      card.appendChild(el('div', { class: 'meta' },
        el('span', {}, el('b', {}, sub.error_code || 'error_code'), ': ', String(sub.message || ''))));
      return card;
    }

    const score = sub.overall_score;
    if (typeof score === 'number') {
      const cls = sub.status?.toLowerCase?.() || classifyScore(score);
      card.appendChild(el('div', { class: `big ${cls}` }, score.toFixed(4)));
      const metaParts = [];
      if (sub.status) metaParts.push([el('span', {}, el('b', {}, 'status'), ` ${sub.status}`)]);
      if (sub.embedding_drift_detector) metaParts.push([el('span', {}, el('b', {}, 'detector'), ` ${sub.embedding_drift_detector}`)]);
      if (typeof sub.files_added === 'number') metaParts.push([el('span', {}, el('b', {}, 'files'), ` +${sub.files_added}/-${sub.files_removed}/=${sub.files_common}`)]);
      if (metaParts.length) card.appendChild(el('div', { class: 'meta' }, ...metaParts.flat()));
    } else if (sub.summary) {
      // EDA envelope shape — show summary fields.
      const meta = el('div', { class: 'meta' });
      for (const [k, v] of Object.entries(sub.summary)) {
        meta.appendChild(el('span', {}, el('b', {}, k), ` ${formatVal(v)}`));
      }
      card.appendChild(meta);
    }

    // Attribute drifts → bars.
    if (sub.attribute_drifts && typeof sub.attribute_drifts === 'object') {
      const max = Math.max(0.001, ...Object.values(sub.attribute_drifts).map(Math.abs));
      const block = el('div', {});
      for (const [k, v] of Object.entries(sub.attribute_drifts)) {
        const pct = Math.min(100, Math.abs(v) / max * 100);
        const cls = classifyScore(Math.abs(v));
        block.appendChild(el('div', { class: 'bar-row' },
          el('span', { class: 'lbl' }, k),
          el('div', { class: `bar ${cls === 'critical' ? 'crit' : cls === 'warning' ? 'warn' : 'ok'}` },
            el('span', { style: `width:${pct}%` })),
          el('span', { class: 'val' }, formatVal(v)),
        ));
      }
      card.appendChild(block);
    }

    // Round 18 — embedding ensemble breakdown.
    if (sub.embedding_drift_detailed && typeof sub.embedding_drift_detailed === 'object') {
      card.appendChild(embeddingEnsembleBlock(sub.embedding_drift_detailed));
    }

    // Round 19 — modality-specific raw chart (timeseries first; other
    // modalities follow once their raw-data plumbing lands).
    if (name === 'timeseries' && sub.attribute_drifts) {
      card.appendChild(timeseriesAttributeChart(sub.attribute_drifts));
    }

    return card;
  }

  // Round-19 timeseries chart — pure SVG line plot of attribute drift
  // values. No external libs. Each attribute (mean / variance / skew /
  // kurt) becomes one point on the polyline; useful as a quick "where
  // did the drift come from" visual cue.
  function timeseriesAttributeChart(attribute_drifts) {
    const root = el('div', { class: 'ts-chart' });
    root.appendChild(el('h5', {}, 'attribute drift trace'));

    const entries = Object.entries(attribute_drifts).filter(([_, v]) => Number.isFinite(v));
    if (entries.length === 0) {
      root.appendChild(el('div', { class: 'hint' }, 'no numeric attributes to plot'));
      return root;
    }

    const W = 480, H = 120, padX = 40, padY = 12;
    const innerW = W - padX * 2, innerH = H - padY * 2;
    const values = entries.map(([_, v]) => Math.abs(v));
    const maxV = Math.max(0.001, ...values);

    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
    svg.setAttribute('width', '100%');
    svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');
    svg.classList.add('ts-svg');

    // Axes — minimal, just the baseline.
    const axis = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    axis.setAttribute('x1', padX); axis.setAttribute('y1', H - padY);
    axis.setAttribute('x2', W - padX); axis.setAttribute('y2', H - padY);
    axis.setAttribute('stroke', '#d6dae0');
    axis.setAttribute('stroke-width', '1');
    svg.appendChild(axis);

    // Gridlines at 25%, 50%, 75%.
    [0.25, 0.5, 0.75].forEach(frac => {
      const y = padY + innerH * (1 - frac);
      const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      line.setAttribute('x1', padX); line.setAttribute('y1', y);
      line.setAttribute('x2', W - padX); line.setAttribute('y2', y);
      line.setAttribute('stroke', '#eef0f4');
      line.setAttribute('stroke-width', '1');
      svg.appendChild(line);
    });

    // Build polyline + circles + labels.
    const points = entries.map(([_, v], i) => {
      const x = padX + (entries.length === 1 ? innerW / 2 : (i / (entries.length - 1)) * innerW);
      const y = padY + innerH * (1 - Math.abs(v) / maxV);
      return [x, y];
    });
    const poly = document.createElementNS('http://www.w3.org/2000/svg', 'polyline');
    poly.setAttribute('points', points.map(p => p.join(',')).join(' '));
    poly.setAttribute('fill', 'none');
    poly.setAttribute('stroke', '#2563eb');
    poly.setAttribute('stroke-width', '2');
    svg.appendChild(poly);

    entries.forEach(([k, v], i) => {
      const [x, y] = points[i];
      const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      circle.setAttribute('cx', x); circle.setAttribute('cy', y);
      circle.setAttribute('r', 3.5);
      circle.setAttribute('fill', '#2563eb');
      const title = document.createElementNS('http://www.w3.org/2000/svg', 'title');
      title.textContent = `${k} = ${formatVal(v)}`;
      circle.appendChild(title);
      svg.appendChild(circle);

      const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      label.setAttribute('x', x);
      label.setAttribute('y', H - 2);
      label.setAttribute('text-anchor', 'middle');
      label.setAttribute('font-size', '10');
      label.setAttribute('fill', '#6a7382');
      label.textContent = k.length > 9 ? k.slice(0, 9) + '…' : k;
      svg.appendChild(label);
    });

    // y-axis max label
    const yMax = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    yMax.setAttribute('x', padX - 4);
    yMax.setAttribute('y', padY + 4);
    yMax.setAttribute('text-anchor', 'end');
    yMax.setAttribute('font-size', '10');
    yMax.setAttribute('fill', '#6a7382');
    yMax.textContent = formatVal(maxV);
    svg.appendChild(yMax);

    root.appendChild(svg);
    return root;
  }

  // Render the per-component breakdown of an ensemble embedding-drift
  // result (Round-12 vision, Round-12 text). Two parts:
  //   1. Stacked contribution bar — width = weight × normalized score
  //   2. Per-metric row showing weight, normalized score, raw value
  function embeddingEnsembleBlock(detail) {
    const root = el('div', { class: 'ensemble-block' });
    root.appendChild(el('h5', {}, 'Embedding ensemble'));

    const weights = detail.weights || {};
    const normalized = detail.normalized_scores || {};
    const ensemble = +detail.ensemble_score || 0;
    const componentNames = Object.keys(weights);

    if (componentNames.length === 0) return root;

    // Stacked contribution bar.
    const stackedLabel = el('div', { class: 'ensemble-stacked-label' },
      `weighted contributions → ${ensemble.toFixed(4)}`);
    const stackedBar = el('div', { class: 'ensemble-stacked' });
    const palette = ['#2563eb', '#7c3aed', '#0891b2', '#059669', '#d97706', '#9d174d'];
    componentNames.forEach((name, i) => {
      const w = +weights[name] || 0;
      const n = +normalized[name] || 0;
      const contrib = Math.max(0, Math.min(1, w * n));
      if (contrib <= 0) return;
      stackedBar.appendChild(el('div', {
        class: 'ensemble-stacked-seg',
        style: `width:${(contrib * 100).toFixed(2)}%; background:${palette[i % palette.length]}`,
        title: `${name}: weight ${w.toFixed(2)} × normalized ${n.toFixed(3)} = ${contrib.toFixed(3)}`,
      }));
    });
    root.appendChild(stackedLabel);
    root.appendChild(stackedBar);

    // Per-metric breakdown table.
    const table = el('div', { class: 'ensemble-table' });
    table.appendChild(el('div', { class: 'ensemble-thead' },
      el('span', { class: 'lbl' }, 'metric'),
      el('span', {}, 'weight'),
      el('span', {}, 'normalized'),
      el('span', {}, 'raw'),
    ));
    componentNames.forEach((name, i) => {
      const w = +weights[name] || 0;
      const n = +normalized[name] || 0;
      const raw = detail[name];
      const dot = el('span', { class: 'ensemble-dot', style: `background:${palette[i % palette.length]}` });
      table.appendChild(el('div', { class: 'ensemble-trow' },
        el('span', { class: 'lbl' }, dot, name),
        el('span', { class: 'val' }, w.toFixed(2)),
        el('span', { class: 'val' }, n.toFixed(4)),
        el('span', { class: 'val' }, formatVal(raw)),
      ));
    });
    root.appendChild(table);

    return root;
  }

  function fusionCard(env) {
    const card = el('div', { class: 'viz-card' });
    card.appendChild(el('h4', {}, `Fusion (${env.fusion_strategy})`));
    const cls = classifyScore(env.fused_score);
    card.appendChild(el('div', { class: `big ${cls}` }, env.fused_score.toFixed(4)));
    const meta = el('div', { class: 'meta' });
    if (env.fusion_weights) {
      const w = Object.entries(env.fusion_weights).map(([k, v]) => `${k}=${(+v).toFixed(2)}`).join(' · ');
      meta.appendChild(el('span', {}, el('b', {}, 'weights'), ` ${w}`));
    }
    if (env.fusion_warnings && env.fusion_warnings.length) {
      meta.appendChild(el('span', {}, el('b', {}, '⚠'), ` ${env.fusion_warnings.length} warning(s)`));
    }
    card.appendChild(meta);
    return card;
  }

  function recipeCard(env) {
    const card = el('div', { class: 'viz-card' });
    card.appendChild(el('h4', {}, `Recipe · ${env.recipe || ''}`));
    const cls = env.status === 'success' ? 'normal' : 'critical';
    card.appendChild(el('div', { class: `big ${cls}` }, env.status));
    const meta = el('div', { class: 'meta' });
    meta.appendChild(el('span', {}, el('b', {}, 'steps'), ` ${env.steps.length}`));
    const ok = env.steps.filter(s => !s.skipped && s.returncode === 0).length;
    meta.appendChild(el('span', {}, el('b', {}, 'ok'), ` ${ok}/${env.steps.length}`));
    card.appendChild(meta);
    // Compact per-step list.
    const list = el('div', { class: 'meta', style: 'flex-direction:column;align-items:flex-start;gap:0.2em' });
    for (const s of env.steps) {
      const status = s.skipped ? 'dry' : (s.returncode === 0 ? 'ok' : 'fail');
      list.appendChild(el('span', {}, `[${status}] ${s.id} (${s.run})${s.elapsed_ms ? ` — ${s.elapsed_ms} ms` : ''}`));
    }
    card.appendChild(list);
    return card;
  }

  function statusCard(env) {
    const card = el('div', { class: 'viz-card' });
    card.appendChild(el('h4', {}, env.format ? `${env.format.toUpperCase()} report` : 'Result'));
    card.appendChild(el('div', { class: 'big normal' }, '✓'));
    const meta = el('div', { class: 'meta' });
    if (env.output_path) meta.appendChild(el('span', {}, el('b', {}, 'path'), ` ${env.output_path}`));
    if (env.size_bytes != null) meta.appendChild(el('span', {}, el('b', {}, 'size'), ` ${env.size_bytes} B`));
    if (env.target) meta.appendChild(el('span', {}, el('b', {}, 'target'), ` ${env.target}`));
    if (env.http_status) meta.appendChild(el('span', {}, el('b', {}, 'http'), ` ${env.http_status}`));
    card.appendChild(meta);
    return card;
  }

  // Round 22 — unified-diff card. Lines starting with '+' / '-' /
  // '@@' / 'diff/index' are colored.
  // Round 23 — for adjacent (-, +) line pairs, also highlight changed
  // *words* via an LCS-based token diff. No syntax highlighter
  // dependency.
  function diffCard(env) {
    const card = el('div', { class: 'viz-card diff-card' });
    const heading = `${env.name || 'recipe'} · ${env.from || 'HEAD'} → ${env.to || '∅'}`;
    card.appendChild(el('h4', {}, heading));
    if (env.identical) {
      card.appendChild(el('div', { class: 'big normal' }, 'identical'));
      return card;
    }
    if (!env.diff) {
      card.appendChild(el('div', { class: 'meta' },
        el('span', {}, env.note || 'no diff content')));
      return card;
    }

    const pre = el('pre', { class: 'diff-pre' });
    const lines = env.diff.split('\n');
    // Walk lines, pairing adjacent '-' then '+' for word-level diff.
    let i = 0;
    while (i < lines.length) {
      const line = lines[i];
      // File or hunk header — never word-diff.
      if (line.startsWith('+++') || line.startsWith('---')) {
        appendDiffLine(pre, line, 'diff-file');
        i++; continue;
      }
      if (line.startsWith('@@')) {
        appendDiffLine(pre, line, 'diff-hunk');
        i++; continue;
      }
      // Pair (-foo, +bar) → word-diffed pair.
      if (line.startsWith('-') &&
          i + 1 < lines.length && lines[i + 1].startsWith('+')) {
        const minusBody = line.slice(1);
        const plusBody = lines[i + 1].slice(1);
        const [delSpans, addSpans] = wordDiff(minusBody, plusBody);
        appendDiffLineSpans(pre, '-', delSpans, 'diff-del');
        appendDiffLineSpans(pre, '+', addSpans, 'diff-add');
        i += 2; continue;
      }
      let cls = 'diff-ctx';
      if (line.startsWith('+')) cls = 'diff-add';
      else if (line.startsWith('-')) cls = 'diff-del';
      appendDiffLine(pre, line, cls);
      i++;
    }
    card.appendChild(pre);
    return card;
  }

  function appendDiffLine(pre, text, cls) {
    pre.appendChild(el('span', { class: cls }, text));
    pre.appendChild(document.createTextNode('\n'));
  }

  function appendDiffLineSpans(pre, prefix, spans, cls) {
    const lineSpan = el('span', { class: cls });
    lineSpan.appendChild(document.createTextNode(prefix));
    for (const s of spans) {
      if (s.changed) {
        lineSpan.appendChild(el('mark', { class: 'diff-word' }, s.text));
      } else {
        lineSpan.appendChild(document.createTextNode(s.text));
      }
    }
    pre.appendChild(lineSpan);
    pre.appendChild(document.createTextNode('\n'));
  }

  // Token-level diff between two strings via classic LCS dynamic
  // programming. Tokens are word-or-whitespace runs so spacing is
  // preserved. Returns [delSpans, addSpans] where each span is
  // {text, changed}.
  function wordDiff(a, b) {
    const aTok = a.match(/\s+|\S+/g) || [];
    const bTok = b.match(/\s+|\S+/g) || [];
    const m = aTok.length, n = bTok.length;
    // dp[i][j] = LCS length of aTok[0..i] vs bTok[0..j]
    const dp = Array.from({ length: m + 1 }, () => new Int32Array(n + 1));
    for (let i = 1; i <= m; i++) {
      for (let j = 1; j <= n; j++) {
        if (aTok[i - 1] === bTok[j - 1]) dp[i][j] = dp[i - 1][j - 1] + 1;
        else dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
      }
    }
    // Backtrack — produce ops same/del/add per token.
    const ops = [];
    let i = m, j = n;
    while (i > 0 && j > 0) {
      if (aTok[i - 1] === bTok[j - 1]) {
        ops.push({ kind: 'same', a: aTok[i - 1] }); i--; j--;
      } else if (dp[i - 1][j] >= dp[i][j - 1]) {
        ops.push({ kind: 'del', a: aTok[i - 1] }); i--;
      } else {
        ops.push({ kind: 'add', b: bTok[j - 1] }); j--;
      }
    }
    while (i > 0) { ops.push({ kind: 'del', a: aTok[--i] }); }
    while (j > 0) { ops.push({ kind: 'add', b: bTok[--j] }); }
    ops.reverse();

    const delSpans = [], addSpans = [];
    let delBuf = '', delChanged = null;
    let addBuf = '', addChanged = null;
    const flush = (buf, changed, target) => {
      if (buf) target.push({ text: buf, changed });
    };
    for (const op of ops) {
      if (op.kind === 'same') {
        if (delChanged === true) { flush(delBuf, true, delSpans); delBuf = ''; }
        if (addChanged === true) { flush(addBuf, true, addSpans); addBuf = ''; }
        delChanged = false; addChanged = false;
        delBuf += op.a; addBuf += op.a;
      } else if (op.kind === 'del') {
        if (delChanged === false) { flush(delBuf, false, delSpans); delBuf = ''; }
        delChanged = true; delBuf += op.a;
      } else { // add
        if (addChanged === false) { flush(addBuf, false, addSpans); addBuf = ''; }
        addChanged = true; addBuf += op.b;
      }
    }
    flush(delBuf, !!delChanged, delSpans);
    flush(addBuf, !!addChanged, addSpans);
    return [delSpans, addSpans];
  }

  function formatVal(v) {
    if (typeof v === 'number') {
      const abs = Math.abs(v);
      return abs >= 1000 || (abs > 0 && abs < 0.001) ? v.toExponential(3) : v.toFixed(4);
    }
    return String(v);
  }

  async function streamRequest(path, body) {
    $('#result-progress').hidden = false;
    $('#result-progress').innerHTML = '';
    const addChip = (text, cls = 'progress-chip') => {
      $('#result-progress').appendChild(el('span', { class: cls }, text));
    };
    let resp;
    try {
      resp = await fetch(path, {
        method: 'POST',
        headers: authHeaders({ 'Content-Type': 'application/json', 'Accept': 'text/event-stream' }),
        body: JSON.stringify(body),
      });
    } catch (e) {
      addChip(`network error: ${e.message}`, 'progress-chip error');
      return;
    }
    if (!resp.ok) {
      let json = null;
      try { json = await resp.json(); } catch (_) {}
      renderResultBody({ ok: false, status: resp.status, json });
      return;
    }
    const reader = resp.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buf = '';
    let lastResult = null;
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      let idx;
      while ((idx = buf.indexOf('\n\n')) >= 0) {
        const block = buf.slice(0, idx);
        buf = buf.slice(idx + 2);
        const lines = block.split('\n');
        let event = 'message', data = '';
        for (const line of lines) {
          if (line.startsWith('event: ')) event = line.slice(7).trim();
          else if (line.startsWith('data: ')) data += line.slice(6);
        }
        if (!data) continue;
        let parsed;
        try { parsed = JSON.parse(data); } catch (_) { continue; }
        if (event === 'progress') {
          // analyze.drift/stream events: {progress, stage, message}
          // recipe/run/stream events:    {id, run, returncode, skipped, ...}
          if (typeof parsed.progress === 'number') {
            addChip(`${(parsed.progress * 100).toFixed(0)}% · ${parsed.stage}`);
          } else if (parsed.id) {
            const status = parsed.skipped
              ? `skip${parsed.skipped_reason ? '·' + parsed.skipped_reason : ''}`
              : (parsed.returncode === 0 ? 'ok' : `rc=${parsed.returncode}`);
            addChip(`${parsed.id} (${parsed.run}) — ${status}`);
          } else {
            addChip(JSON.stringify(parsed).slice(0, 80));
          }
        } else if (event === 'result') {
          lastResult = parsed;
          addChip(`100% · complete`);
        } else if (event === 'error') {
          lastResult = parsed;
          addChip(`error: ${parsed.error_code || parsed.error_type || 'unknown'}`, 'progress-chip error');
        }
      }
    }
    renderResultBody({ ok: lastResult && lastResult.status !== 'error', status: 200, json: lastResult });
  }

  // ── Copy CLI command ─────────────────────────────────────────────
  $('#copy-cli').addEventListener('click', async () => {
    const text = $('#cli-hint').textContent;
    try {
      await navigator.clipboard.writeText(text);
      const btn = $('#copy-cli');
      const orig = btn.textContent;
      btn.textContent = 'copied';
      setTimeout(() => (btn.textContent = orig), 1200);
    } catch (e) {
      alert('Clipboard API unavailable; select the text manually.');
    }
  });

  // ── Go ───────────────────────────────────────────────────────────
  bootstrap().catch(err => {
    document.body.innerHTML = `<pre style="padding:2em;color:#c4302b">bootstrap failed: ${err}</pre>`;
  });

})();
