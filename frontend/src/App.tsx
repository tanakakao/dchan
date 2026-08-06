import { FormEvent, useEffect, useMemo, useState } from "react";

type Factor = {
  id: number;
  name: string;
  kind: "numeric" | "categorical";
  lower: string;
  upper: string;
  step: string;
  levels: string;
};

type CandidateResponse = {
  candidates: Record<string, string | number>[];
  correlations: Record<string, Record<string, number | null>>;
};

type HealthStatus = "loading" | "ready" | "error";
type Theme = "light" | "dark";

const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8002";
const API_HOST = API_URL.replace(/^https?:\/\//, "");
const HEALTH_LABELS: Record<HealthStatus, string> = {
  loading: "確認中",
  ready: "接続済み",
  error: "エラー",
};
const initialFactors: Factor[] = [
  { id: 1, name: "Temperature", kind: "numeric", lower: "20", upper: "100", step: "10", levels: "" },
  { id: 2, name: "Time", kind: "numeric", lower: "1", upper: "10", step: "1", levels: "" },
  { id: 3, name: "Catalyst", kind: "categorical", lower: "", upper: "", step: "", levels: "A, B, C" },
];

/** Build and operate the optimal-design workspace. */
export default function App() {
  const [factors, setFactors] = useState<Factor[]>(initialFactors);
  const [method, setMethod] = useState("D");
  const [samples, setSamples] = useState(12);
  const [iterations, setIterations] = useState(200);
  const [result, setResult] = useState<CandidateResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [health, setHealth] = useState<HealthStatus>("loading");
  const [activeStep, setActiveStep] = useState(1);
  const [theme, setTheme] = useState<Theme>(() => window.localStorage.getItem("dchan-theme") === "dark" ? "dark" : "light");
  const columns = useMemo(() => result ? Object.keys(result.candidates[0] ?? {}) : [], [result]);
  const numericCount = factors.filter((factor) => factor.kind === "numeric").length;
  const categoricalCount = factors.length - numericCount;

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem("dchan-theme", theme);
  }, [theme]);

  useEffect(() => {
    let active = true;

    async function checkHealth() {
      try {
        const response = await fetch(`${API_URL}/health`);
        if (active) setHealth(response.ok ? "ready" : "error");
      } catch {
        if (active) setHealth("error");
      }
    }

    void checkHealth();
    const timer = window.setInterval(checkHealth, 30000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, []);

  /** Update one property on a factor row. */
  function updateFactor(id: number, patch: Partial<Factor>) {
    setFactors((current) => current.map((factor) => factor.id === id ? { ...factor, ...patch } : factor));
  }

  /** Add an empty numeric factor to the form. */
  function addFactor() {
    setFactors((current) => [
      ...current,
      { id: Date.now(), name: `Factor ${current.length + 1}`, kind: "numeric", lower: "0", upper: "10", step: "1", levels: "" },
    ]);
  }

  function openSection(step: number, sectionId: string) {
    setActiveStep(step);
    document.getElementById(sectionId)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  /** Submit the current factor settings to the optimization API. */
  async function generate(event: FormEvent) {
    event.preventDefault();
    setError("");
    setLoading(true);
    setActiveStep(2);
    const numericValue = (value: string) => value === "" ? null : Number(value);
    try {
      const response = await fetch(`${API_URL}/optimal-design/candidate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          factor_names: factors.map(({ name }) => name.trim()),
          x_lower: factors.map((factor) => factor.kind === "numeric" ? numericValue(factor.lower) : null),
          x_upper: factors.map((factor) => factor.kind === "numeric" ? numericValue(factor.upper) : null),
          x_step: factors.map((factor) => factor.kind === "numeric" ? numericValue(factor.step) : null),
          x_levels: factors.map((factor) => factor.kind === "categorical"
            ? factor.levels.split(",").map((level) => level.trim()).filter(Boolean)
            : null),
          opt_type: method,
          n_iter: iterations,
          n_samples: samples,
        }),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : "設定内容を確認してください。");
      setResult(body);
      setActiveStep(3);
      window.setTimeout(() => document.getElementById("results")?.scrollIntoView({ behavior: "smooth", block: "start" }), 0);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "候補点を生成できませんでした。");
    } finally {
      setLoading(false);
    }
  }

  /** Download generated candidates as a UTF-8 CSV file. */
  function downloadCsv() {
    if (!result) return;
    const escape = (value: string | number) => `"${String(value).replaceAll('"', '""')}"`;
    const csv = [columns.map(escape).join(","), ...result.candidates.map((row) => columns.map((key) => escape(row[key])).join(","))].join("\n");
    const link = document.createElement("a");
    link.href = URL.createObjectURL(new Blob([`\ufeff${csv}`], { type: "text/csv;charset=utf-8" }));
    link.download = "dchan-candidates.csv";
    link.click();
    URL.revokeObjectURL(link.href);
  }

  const workflow = [
    { id: "factors", label: "因子設定", detail: "変数と水準", icon: "◇" },
    { id: "settings", label: "生成条件", detail: "基準と計算量", icon: "⌘" },
    { id: "results", label: "生成結果", detail: "候補点一覧", icon: "◎" },
  ];

  return (
    <div className="app-root">
      <header className="app-header">
        <div className="brand-lockup">
          <div className="brand-mark" aria-hidden="true"><span>d</span></div>
          <div className="brand-wordmark">
            <h1>実験計画</h1>
            <p>Optimal Design Workbench · dchan</p>
          </div>
        </div>

        <div className="workflow-strip" aria-label="ワークフロー">
          {workflow.map((item, index) => {
            const step = index + 1;
            return (
              <div className="workflow-item" key={item.id}>
                <button
                  type="button"
                  className={`workflow-step ${activeStep === step ? "active" : ""} ${activeStep > step ? "complete" : ""}`}
                  onClick={() => openSection(step, item.id)}
                  disabled={step === 3 && !result}
                >
                  <span>{step}</span>
                  <strong>{item.label}</strong>
                </button>
                {index < workflow.length - 1 && <i />}
              </div>
            );
          })}
        </div>

        <div className="header-actions">
          <div className="runtime-pill" title={`API接続: ${API_URL}`}>
            <span className={`dot ${health}`} />
            <span className="runtime-copy">
              <small>API接続</small>
              <strong>{HEALTH_LABELS[health]}</strong>
            </span>
          </div>
          <button type="button" className="icon-button secondary" title="使い方" onClick={() => openSection(1, "guide")}>?</button>
          <button
            type="button"
            className="icon-button secondary theme-toggle"
            title={theme === "dark" ? "ライトテーマへ" : "ダークテーマへ"}
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          >
            {theme === "dark" ? "☀" : "☾"}
          </button>
        </div>
      </header>

      <main className="app-shell">
        <aside className="left-rail">
          <div className="rail-section-label">Workflow</div>
          <nav className="tabs" aria-label="ページナビゲーション">
            {workflow.map((item, index) => {
              const step = index + 1;
              return (
                <button
                  type="button"
                  className={`tab ${activeStep === step ? "active" : ""} ${activeStep > step ? "complete" : ""}`}
                  key={item.id}
                  onClick={() => openSection(step, item.id)}
                  disabled={step === 3 && !result}
                >
                  <span className="nav-icon">{item.icon}</span>
                  <span><strong>{item.label}</strong><small>{item.detail}</small></span>
                  <em>{step}</em>
                </button>
              );
            })}
          </nav>
          <div className="rail-spacer" />
          <div className="rail-note" id="guide">
            <div className="shield-icon">D</div>
            <div>
              <span>Design workflow</span>
              <strong>FastAPI + React</strong>
              <p>因子定義から最適な実験候補点の生成までを一つの画面で扱います。</p>
            </div>
          </div>
        </aside>

        <section className="content">
          <div className="content-inner">
            <div className="section-header">
              <div>
                <span className="eyebrow">OPTIMAL DESIGN WORKSPACE</span>
                <h2>実験計画をはじめる</h2>
                <p>因子と条件を設定し、情報量の高い実験候補点を効率的に生成します。</p>
              </div>
              <span className="status-chip">Dedicated port · 5175</span>
            </div>

            {error && (
              <div className="inline-alert error" role="alert">
                <span className="inline-alert-icon">!</span>
                <div><strong>候補点を生成できませんでした</strong><p>{error}</p></div>
                <button type="button" className="icon-button secondary" onClick={() => setError("")}>×</button>
              </div>
            )}

            <form onSubmit={generate}>
              <section className="panel" id="factors">
                <div className="panel-title">
                  <div className="panel-heading">
                    <span className="panel-index">01</span>
                    <div><span className="eyebrow">FACTORS</span><h3>因子を設定</h3><p>実験で変化させる数値因子またはカテゴリ因子を入力します。</p></div>
                  </div>
                  <button className="secondary" type="button" onClick={addFactor}>＋ 因子を追加</button>
                </div>
                <div className="factor-list">
                  {factors.map((factor, index) => (
                    <div className="factor-row" key={factor.id}>
                      <span className="factor-number">{String(index + 1).padStart(2, "0")}</span>
                      <label className="name-field"><span>因子名</span><input required value={factor.name} onChange={(event) => updateFactor(factor.id, { name: event.target.value })} /></label>
                      <label><span>種類</span><select value={factor.kind} onChange={(event) => updateFactor(factor.id, { kind: event.target.value as Factor["kind"] })}><option value="numeric">数値</option><option value="categorical">カテゴリ</option></select></label>
                      {factor.kind === "numeric" ? <>
                        <label><span>下限</span><input required type="number" step="any" value={factor.lower} onChange={(event) => updateFactor(factor.id, { lower: event.target.value })} /></label>
                        <label><span>上限</span><input required type="number" step="any" value={factor.upper} onChange={(event) => updateFactor(factor.id, { upper: event.target.value })} /></label>
                        <label><span>刻み</span><input required type="number" min="0" step="any" value={factor.step} onChange={(event) => updateFactor(factor.id, { step: event.target.value })} /></label>
                      </> : <label className="levels-field"><span>水準 <em>カンマ区切り</em></span><input required value={factor.levels} onChange={(event) => updateFactor(factor.id, { levels: event.target.value })} /></label>}
                      <button className="remove" type="button" aria-label={`${factor.name}を削除`} disabled={factors.length === 1} onClick={() => setFactors((current) => current.filter(({ id }) => id !== factor.id))}>×</button>
                    </div>
                  ))}
                </div>
              </section>

              <section className="panel" id="settings">
                <div className="panel-title">
                  <div className="panel-heading">
                    <span className="panel-index">02</span>
                    <div><span className="eyebrow">GENERATION</span><h3>生成条件</h3><p>最適化基準、候補点数、探索反復回数を設定します。</p></div>
                  </div>
                </div>
                <div className="settings-grid">
                  <label><span>最適化基準</span><select value={method} onChange={(event) => setMethod(event.target.value)}><option value="D">D-optimal（行列式を最大化）</option><option value="A">A-optimal</option><option value="E">E-optimal</option><option value="I">I-optimal</option><option value="minmax">Min-max</option></select></label>
                  <label><span>生成する候補点</span><div className="number-unit"><input type="number" min="1" value={samples} onChange={(event) => setSamples(Number(event.target.value))} /><b>点</b></div></label>
                  <label><span>探索反復回数</span><div className="number-unit"><input type="number" min="1" value={iterations} onChange={(event) => setIterations(Number(event.target.value))} /><b>回</b></div></label>
                </div>
                <div className="action-area">
                  <button className="primary" type="submit" disabled={loading}>{loading ? "候補点を計算中..." : "候補点を生成 →"}</button>
                  <p>条件数により計算に数秒かかる場合があります。</p>
                </div>
              </section>
            </form>

            {result && (
              <section id="results" className="panel results-panel">
                <div className="panel-title">
                  <div className="panel-heading">
                    <span className="panel-index complete">✓</span>
                    <div><span className="eyebrow">RESULT</span><h3>生成した候補点</h3><p>{result.candidates.length}点の実験条件を生成しました。</p></div>
                  </div>
                  <button className="secondary" type="button" onClick={downloadCsv}>CSVを保存</button>
                </div>
                <div className="table-wrap"><table><thead><tr><th>RUN</th>{columns.map((column) => <th key={column}>{column}</th>)}</tr></thead><tbody>{result.candidates.map((row, index) => <tr key={index}><td>{String(index + 1).padStart(2, "0")}</td>{columns.map((column) => <td key={column}>{row[column]}</td>)}</tr>)}</tbody></table></div>
              </section>
            )}
          </div>
        </section>

        <aside className="right-rail">
          <div className={`side-card runtime-card ${health}`}>
            <div className="side-card-title"><span>Runtime</span><strong>API接続</strong></div>
            <div className="runtime-large"><span className={`dot ${health}`} /><div><strong>FastAPI</strong><small>{HEALTH_LABELS[health]} · {API_HOST}</small></div></div>
          </div>

          <div className="side-card">
            <div className="side-card-title"><span>Design context</span><strong>現在の設定</strong></div>
            <div className="context-list">
              <div><span>Factors</span><strong>{factors.length}</strong></div>
              <div><span>Numeric</span><strong>{numericCount}</strong></div>
              <div><span>Categorical</span><strong>{categoricalCount}</strong></div>
              <div><span>Criterion</span><strong>{method.toUpperCase()}</strong></div>
              <div><span>Candidates</span><strong>{samples}</strong></div>
              <div><span>Iterations</span><strong>{iterations}</strong></div>
            </div>
          </div>

          <div className="side-card tips-card">
            <div className="side-card-title"><span>Result</span><strong>最新の生成結果</strong></div>
            {result ? <div className="context-list"><div><span>Rows</span><strong>{result.candidates.length}</strong></div><div><span>Status</span><strong className="success-text">Ready</strong></div></div> : <p>候補点を生成すると、結果の概要をここに表示します。</p>}
          </div>
        </aside>
      </main>

      <footer className="statusbar">
        <span><span className={`dot ${health}`} /> API接続 {HEALTH_LABELS[health]}</span>
        <span>{factors.length} factors</span>
        <span>{result ? `${result.candidates.length} candidates` : "No result"}</span>
        <span className="statusbar-stack">React · FastAPI · dchan</span>
      </footer>

      {loading && (
        <div className="overlay" role="status" aria-live="polite" aria-busy="true">
          <div className="busy-card"><div className="spinner" /><span className="eyebrow">PROCESSING</span><h3>候補点を生成しています</h3><p>設定した基準に基づいて実験候補点を探索しています。</p></div>
        </div>
      )}
    </div>
  );
}
