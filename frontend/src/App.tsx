import { FormEvent, useMemo, useState } from "react";

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

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
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
  const columns = useMemo(() => result ? Object.keys(result.candidates[0] ?? {}) : [], [result]);

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

  /** Submit the current factor settings to the optimization API. */
  async function generate(event: FormEvent) {
    event.preventDefault();
    setError("");
    setLoading(true);
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

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#top"><span className="brand-mark">D</span><span>D-chan<small>Design Lab</small></span></a>
        <nav aria-label="メインナビゲーション">
          <a className="active" href="#design"><span>◈</span> 実験計画</a>
          <a href="#results"><span>▦</span> 生成結果</a>
          <a href="#guide"><span>○</span> 使い方</a>
        </nav>
        <div className="sidebar-note"><b>API status</b><span><i /> localhost:8000</span></div>
      </aside>

      <main id="top">
        <header><div><p className="eyebrow">OPTIMAL DESIGN WORKSPACE</p><h1>実験計画をはじめる</h1><p>因子と条件を設定し、効率的な実験候補点を生成します。</p></div><div className="header-badge"><span>?</span> ガイド</div></header>

        <form id="design" onSubmit={generate}>
          <section className="card">
            <div className="section-heading"><span className="step">01</span><div><h2>因子を設定</h2><p>実験で変化させる数値またはカテゴリを入力します。</p></div><button className="secondary" type="button" onClick={addFactor}>+　因子を追加</button></div>
            <div className="factor-list">
              {factors.map((factor, index) => (
                <div className="factor-row" key={factor.id}>
                  <span className="factor-number">{String(index + 1).padStart(2, "0")}</span>
                  <label className="name-field"><span>因子名</span><input required value={factor.name} onChange={(e) => updateFactor(factor.id, { name: e.target.value })} /></label>
                  <label><span>種類</span><select value={factor.kind} onChange={(e) => updateFactor(factor.id, { kind: e.target.value as Factor["kind"] })}><option value="numeric">数値</option><option value="categorical">カテゴリ</option></select></label>
                  {factor.kind === "numeric" ? <>
                    <label><span>下限</span><input required type="number" step="any" value={factor.lower} onChange={(e) => updateFactor(factor.id, { lower: e.target.value })} /></label>
                    <label><span>上限</span><input required type="number" step="any" value={factor.upper} onChange={(e) => updateFactor(factor.id, { upper: e.target.value })} /></label>
                    <label><span>刻み</span><input required type="number" min="0" step="any" value={factor.step} onChange={(e) => updateFactor(factor.id, { step: e.target.value })} /></label>
                  </> : <label className="levels-field"><span>水準 <em>カンマ区切り</em></span><input required value={factor.levels} onChange={(e) => updateFactor(factor.id, { levels: e.target.value })} /></label>}
                  <button className="remove" type="button" aria-label={`${factor.name}を削除`} disabled={factors.length === 1} onClick={() => setFactors((current) => current.filter(({ id }) => id !== factor.id))}>×</button>
                </div>
              ))}
            </div>
          </section>

          <section className="card settings">
            <div className="section-heading"><span className="step">02</span><div><h2>生成条件</h2><p>最適化の基準と計算量を設定します。</p></div></div>
            <div className="settings-grid">
              <label><span>最適化基準</span><select value={method} onChange={(e) => setMethod(e.target.value)}><option value="D">D-optimal（行列式を最大化）</option><option value="A">A-optimal</option><option value="E">E-optimal</option><option value="I">I-optimal</option><option value="minmax">Min-max</option></select></label>
              <label><span>生成する候補点</span><div className="number-unit"><input type="number" min="1" value={samples} onChange={(e) => setSamples(Number(e.target.value))} /><b>点</b></div></label>
              <label><span>探索反復回数</span><div className="number-unit"><input type="number" min="1" value={iterations} onChange={(e) => setIterations(Number(e.target.value))} /><b>回</b></div></label>
            </div>
          </section>

          {error && <div className="error" role="alert">{error}</div>}
          <div className="submit-area"><button className="primary" type="submit" disabled={loading}>{loading ? "計算中..." : "候補点を生成　→"}</button><p>計算に数秒かかる場合があります</p></div>
        </form>

        {result && <section id="results" className="card results">
          <div className="section-heading"><span className="step complete">✓</span><div><h2>生成した候補点</h2><p>{result.candidates.length}点の実験条件を生成しました。</p></div><button className="secondary" type="button" onClick={downloadCsv}>CSV を保存</button></div>
          <div className="table-wrap"><table><thead><tr><th>RUN</th>{columns.map((column) => <th key={column}>{column}</th>)}</tr></thead><tbody>{result.candidates.map((row, index) => <tr key={index}><td>{String(index + 1).padStart(2, "0")}</td>{columns.map((column) => <td key={column}>{row[column]}</td>)}</tr>)}</tbody></table></div>
        </section>}
        <footer id="guide">D-chan <span>/</span> Design smarter, learn faster.</footer>
      </main>
    </div>
  );
}
