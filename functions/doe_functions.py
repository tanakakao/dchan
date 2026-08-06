"""
このPythonファイルは、最適化デザインの生成を目的としたモジュールです。
主に、因子名、上限値、下限値、ステップサイズ、およびレベルに基づいて
最適化されたデザインを計算します。以下の機能を提供します。

主な機能:
1. make_label: 因子の名前と関連データに基づいてレベルエンコーディングとエンコードアイテムを生成します。
2. calculate_score: スケーリングされたデザイン行列からスコアを計算します。
3. optimal_design: 与えられた因子の設定を元に最適化デザインを生成します。
4. OptimalDesignクラス: 因子の設定とデザイン候補を生成するメソッドを持つクラスです。

使用するライブラリ:
- numpy: 数値計算のためのライブラリ。
- pandas: データ操作のためのライブラリ。
- typing: 型ヒントのための標準ライブラリ。

使用方法:
1. OptimalDesignクラスのインスタンスを生成します。
2. setメソッドを使用して因子の設定を行います。
3. candidateメソッドを呼び出すことで、最適化デザインの候補を生成します。
"""
from __future__ import annotations
from fractions import Fraction
from math import gcd
import random
import functools

import numpy as np
import pandas as pd
import itertools
from typing import List, Dict, Any, Tuple, Optional, Sequence, Union

def _lcm(a: int, b: int) -> int:
    return abs(a // gcd(a, b) * b) if a and b else 0


def _lcm_many(ints: Sequence[int]) -> int:
    return functools.reduce(_lcm, ints, 1)

def _normalize_mixture_constraints(
    factor_names: List[str],
    mixture_keys: Optional[Union[List[str], List[List[str]]]],
    sum_target: Optional[Union[float, List[float]]],
) -> Tuple[List[List[str]], List[List[int]], List[float]]:
    """
    mixture制約を常に複数グループ表現へ正規化する。

    受け入れる形式:
        1) mixture_keys=["A", "B", "C"], sum_target=1.0
        2) mixture_keys=[["A", "B", "C"], ["D", "E"]], sum_target=[1.0, 0.5]

    Returns:
        mixture_groups:
            例 [["A", "B", "C"], ["D", "E"]]
        mixture_keys_idxs:
            例 [[0, 1, 2], [3, 4]]
        sum_targets:
            例 [1.0, 0.5]

    Notes:
        現在の実装では、複数グループは「互いに非重複」である必要があります。
        同じ因子が複数グループにまたがる制約は、この独立サンプラ方式では扱いません。
    """
    if mixture_keys is None:
        if sum_target is not None:
            raise ValueError("sum_target が指定されていますが、mixture_keys が None です。")
        return [], [], []

    if len(mixture_keys) == 0:
        return [], [], []

    # 単一グループ: ["A", "B", "C"]
    if isinstance(mixture_keys[0], str):
        mixture_groups = [list(mixture_keys)]  # type: ignore[arg-type]
    else:
        mixture_groups = [list(group) for group in mixture_keys]  # type: ignore[arg-type]

    if sum_target is None:
        raise ValueError("mixture_keys を指定する場合は sum_target も指定してください。")

    if isinstance(sum_target, (int, float)):
        sum_targets = [float(sum_target)]
    else:
        sum_targets = [float(v) for v in sum_target]

    if len(mixture_groups) != len(sum_targets):
        raise ValueError(
            "mixture_keys のグループ数と sum_target の数が一致していません。"
        )

    mixture_keys_idxs: List[List[int]] = []
    used_cols: Dict[int, str] = {}

    for group_idx, group in enumerate(mixture_groups):
        if len(group) == 0:
            raise ValueError(f"{group_idx} 番目の mixture_keys グループが空です。")

        idxs = []
        for key in group:
            if key not in factor_names:
                raise ValueError(f"mixture_keys に存在しない因子名があります: {key}")
            col_idx = factor_names.index(key)

            if col_idx in used_cols:
                raise ValueError(
                    f"因子 '{key}' が複数の mixture グループに重複しています。"
                    " 現在の実装では非重複グループのみ対応です。"
                )
            used_cols[col_idx] = key
            idxs.append(col_idx)

        mixture_keys_idxs.append(idxs)

    return mixture_groups, mixture_keys_idxs, sum_targets

class DiscreteUniformConstrainedSampler:
    """
    離散一様サンプラ（各変数の刻みと範囲が異なるケースに対応）。

    問題設定:
        各変数 x_i は {low_i + k * step_i | k∈Z} かつ low_i ≤ x_i ≤ high_i を取り、
        Σ x_i = sum_value を満たす。
        有限個の解集合（格子点）から「厳密一様」にサンプリング。

    方式:
        - すべてを有理数として共通スケール L 倍で整数化
        - 変数変換: x_i = low_i + step_i * t_i (0 ≤ t_i ≤ tmax_i)
        - 和制約: Σ w_i * t_i = C（w_i = step_i/g, C = (S-Σlow_i)/g）
        - 後ろ向きDP（suffix DP）で「残り変数で達成できる通り数」を前計算 → 一様サンプル

    Note:
        - 厳密一様。unique=True で非復元（重複なし）も可（中規模まで）。
        - 規模が大きいとメモリ/時間が増えます。必要なら最適化版も用意できます。
    """

    # -----------------------------
    # コンストラクタ：前計算まで実施
    # -----------------------------
    def __init__(
        self,
        steps: Sequence[float],
        lows: Sequence[float],
        highs: Sequence[float],
        sum_value: float,
        denom_limit: int = 10**6,
        seed: Optional[int] = None,
    ) -> None:
        self.steps = list(steps)
        self.lows = list(lows)
        self.highs = list(highs)
        self.sum_value = float(sum_value)
        self.k = len(self.steps)

        if len(self.lows) != self.k or len(self.highs) != self.k:
            raise ValueError("steps, lows, highs の長さは同じにしてください。")
        if any(s <= 0 for s in self.steps):
            raise ValueError("全ての step_i は正である必要があります。")
        if any(lo > hi for lo, hi in zip(self.lows, self.highs)):
            raise ValueError("各変数で low_i ≤ high_i を満たしてください。")

        self.denom_limit = int(denom_limit)
        self._rng = random.Random(seed)

        # ---- 1) 有理数化 → 共通スケール L で整数化 ----
        fracs = []
        for arr in (self.steps, self.lows, self.highs, [self.sum_value]):
            fracs.extend(Fraction(x).limit_denominator(self.denom_limit) for x in arr)
        denoms = [f.denominator for f in fracs]
        L = _lcm_many(denoms)
        self.L = L

        def to_int(x: float) -> int:
            f = Fraction(x).limit_denominator(self.denom_limit)
            return f.numerator * (L // f.denominator)

        self.S = to_int(self.sum_value)
        self.s_int = [to_int(x) for x in self.steps]
        self.lo_int = [to_int(x) for x in self.lows]
        self.hi_int = [to_int(x) for x in self.highs]

        # 刻み・範囲チェック & tmax 計算
        tmax = []
        for i in range(self.k):
            rng = self.hi_int[i] - self.lo_int[i]
            if rng < 0:
                raise ValueError(f"var {i}: high_i < low_i")
            if rng % self.s_int[i] != 0:
                raise ValueError(
                    f"var {i}: (high_i - low_i) が step_i の整数倍ではありません。"
                )
            tmax.append(rng // self.s_int[i])
        self.tmax = tmax

        # 和制約を整数スケールで
        R = self.S - sum(self.lo_int)
        if R < 0:
            raise ValueError("sum_value が下限合計より小さいため実現不可能です。")
        self.R = R

        g = functools.reduce(gcd, self.s_int + [R])
        self.g = g
        if R % g != 0:
            raise ValueError("刻みのgcdが合わず、正確に和を満たす解が存在しません。")

        self.w = [si // g for si in self.s_int]  # 重み
        self.C = R // g                           # 目標和（縮約後）

        # ---- 2) suffix DP（i..末尾で合計 c を作る通り数）を前計算 ----
        C = self.C
        k = self.k
        ways_suffix = [None] * (k + 1)
        arrk = np.zeros(C + 1, dtype=object)
        arrk[0] = 1
        ways_suffix[k] = arrk
        for i in range(k - 1, -1, -1):
            wi = self.w[i]
            Ti = self.tmax[i]
            prev = ways_suffix[i + 1]
            cur = np.zeros(C + 1, dtype=object)

            if wi == 0:
                # ここに来るのは step=0 のときだが通常は発生しない想定
                for cc in range(C + 1):
                    cur[cc] = prev[cc] * (Ti + 1)
            else:
                for cc in range(C + 1):
                    max_t = min(Ti, cc // wi)
                    s_val = 0
                    d = cc
                    for _t in range(max_t + 1):
                        s_val += prev[d]
                        d -= wi
                    cur[cc] = s_val

            ways_suffix[i] = cur

        self.ways_suffix = ways_suffix
        self.total_solutions = int(ways_suffix[0][self.C])
        if self.total_solutions == 0:
            raise ValueError("与えられた条件では解が存在しません。")

    # -----------------------------
    # 公開メソッド
    # -----------------------------
    def set_seed(self, seed: int) -> None:
        """乱数シードを後から設定。"""
        self._rng.seed(seed)

    def conditions(self, include_integer: bool = False) -> Dict[str, Any]:
        """
        条件と派生量を辞書で返却（ログや可視化に便利）。

        Args:
            include_integer: True で整数スケールの内部量も含める

        Returns:
            dict
        """
        d = {
            "k": self.k,
            "steps": self.steps.copy(),
            "lows": self.lows.copy(),
            "highs": self.highs.copy(),
            "sum_value": self.sum_value,
            "L": self.L,
            "S": self.S,
            "tmax": self.tmax.copy(),
            "g": self.g,
            "w": self.w.copy(),
            "C": self.C,
            "total_solutions": self.total_solutions,
        }
        if include_integer:
            d.update(
                {
                    "s_int": self.s_int.copy(),
                    "lo_int": self.lo_int.copy(),
                    "hi_int": self.hi_int.copy(),
                }
            )
        return d

    def summary(self) -> str:
        """条件のテキスト要約（人間可読）。"""
        d = self.conditions(include_integer=False)
        lines = [
            f"k (variables): {d['k']}",
            f"sum_value: {d['sum_value']}",
            f"L (integer scale): {d['L']}",
            f"S (sum_value * L): {self.S}",
            f"g (gcd of steps & R): {d['g']}",
            f"C (target sum after gcd): {d['C']}",
            f"total_solutions: {d['total_solutions']}",
            f"steps: {d['steps']}",
            f"lows : {d['lows']}",
            f"highs: {d['highs']}",
            f"tmax: {d['tmax']}",
            f"weights w: {d['w']}",
        ]
        return "\n".join(lines)

    def sample(
        self,
        n: int = 1,
        as_int: bool = False,
        unique: bool = False,
        max_trials: int = 100_000,
    ) -> np.ndarray:
        """
        一様サンプリング。

        Args:
            n: 件数
            as_int: True なら整数スケール（単位 1/L）の値を返す
            unique: True なら非復元（重複なし）
            max_trials: unique=True の際の試行上限

        Returns:
            shape=(n, k) の ndarray
        """
        if unique and n > self.total_solutions:
            raise ValueError(f"n={n} は全解数 {self.total_solutions} を超えています。")

        samples_t = []
        seen = set()

        for _ in range(n):
            for _trial in range(max_trials):
                t_vec = self._draw_one_t()
                if not unique:
                    samples_t.append(t_vec)
                    break
                key = tuple(t_vec.tolist())
                if key not in seen:
                    seen.add(key)
                    samples_t.append(t_vec)
                    break
            else:
                raise RuntimeError("unique サンプルの収集が試行上限に達しました。")

        t_arr = np.vstack(samples_t) if samples_t else np.zeros((0, self.k), dtype=int)
        y_int = np.array(self.lo_int, dtype=int)[None, :] + (np.array(self.s_int, dtype=int)[None, :] * t_arr)
        return y_int if as_int else (y_int.astype(float) / self.L)

    # -----------------------------
    # 内部：1件サンプル（tベクトル）
    # -----------------------------
    def _draw_one_t(self) -> np.ndarray:
        k = self.k
        w = self.w
        tmax = self.tmax
        C = self.C
        ways_suffix = self.ways_suffix

        c = C
        t_out = np.zeros(k, dtype=int)
        for i in range(k):
            wi = w[i]
            Ti = tmax[i]
            rem = ways_suffix[i + 1]
            if wi == 0:
                chosen = self._rng.randrange(Ti + 1)
                t_out[i] = chosen
            else:
                max_t = min(Ti, c // wi)
                weights = [int(rem[c - t * wi]) for t in range(max_t + 1)]
                tot_w = sum(weights)
                u = self._rng.randrange(tot_w)
                acc = 0
                chosen = 0
                for t, wt in enumerate(weights):
                    acc += wt
                    if u < acc:
                        chosen = t
                        break
                t_out[i] = chosen
                c -= chosen * wi
        return t_out


def make_label(
    factor_names: List[str],
    x_upper: List[float],
    x_lower: List[float],
    x_step: List[float],
    x_levels: List[Optional[List[Any]]]
) -> Tuple[Dict[str, Dict[int, Any]], Dict[str, np.ndarray]]:
    """
    因子名に基づいてレベルエンコーディングとエンコードアイテムを生成する関数。

    Args:
        factor_names (List[str]): 因子の名前リスト。
        x_upper (List[float]): 各因子の上限値リスト。
        x_lower (List[float]): 各因子の下限値リスト。
        x_step (List[float]): 各因子のステップ値リスト。
        x_levels (List[Optional[List[Any]]]): 各因子のレベルリスト。

    Returns:
        Tuple[Dict[str, Dict[int, Any]], Dict[str, np.ndarray]]:
            - level_encodes: 因子名をキーとしたレベルエンコーディング辞書。
            - enc_items: 因子名をキーとしたエンコードアイテムの辞書。
    """
    
    level_encodes = {}
    enc_items = {}
    
    for i, f in enumerate(factor_names):
        # 引数の検証
        if len(x_upper) != len(factor_names) or len(x_lower) != len(factor_names) or len(x_step) != len(factor_names):
            raise ValueError("x_upper, x_lower, and x_step must have the same length as factor_names.")
        
        if x_levels[i] is not None:
            enc_dict = {j: k for j, k in enumerate(x_levels[i])}  # レベルをエンコード
            level_encodes[f] = enc_dict
            enc_items[f] = np.arange(len(x_levels[i]))  # エンコードアイテム
        else:
            level_encodes[f] = []  # レベルが指定されていない場合
            enc_items[f] = np.arange(x_lower[i], x_upper[i] + x_step[i] / 2, x_step[i])  # エンコードアイテムを生成
            
    return level_encodes, enc_items

def calculate_score(X_scaled: np.ndarray, opt_type: str) -> float:
    """
    スコアを計算するヘルパー関数。

    Args:
        X_scaled (np.ndarray): スケーリングされたデザイン行列。
        opt_type (str): 最適化タイプ。

    Returns:
        float: 計算されたスコア。
    """
    if opt_type == 'A':
        return -np.trace(np.linalg.inv(X_scaled.T @ X_scaled))
    elif opt_type == 'E':
        return np.linalg.eig(X_scaled.T @ X_scaled)[0].min()
    elif opt_type == 'I':
        return -np.diag(X_scaled @ np.linalg.inv(X_scaled.T @ X_scaled / X_scaled.shape[0]) @ X_scaled.T).mean()
    elif opt_type == 'minmax':
        return -np.diag(X_scaled.T @ X_scaled).max()
    else:  # opt_type == 'D'
        return np.linalg.det(X_scaled.T @ X_scaled)

def optimal_design(
    enc_items: Dict[str, np.ndarray],
    level_encodes: Dict[str, Dict[int, Any]],
    factor_names: List[str],
    mixture_keys_idxs: Optional[List[List[int]]] = None,
    samplers: Optional[List[DiscreteUniformConstrainedSampler]] = None,
    opt_type: str = 'D',
    n_iter: int = 200,
    n_samples: int = 30
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    最適化デザインを生成する関数。
    """

    best_score = None
    best_X = None

    for _ in range(n_iter):
        X = np.array([np.random.choice(enc_items[f], n_samples) for f in factor_names]).T

        if mixture_keys_idxs is not None and samplers is not None:
            if len(mixture_keys_idxs) != len(samplers):
                raise ValueError("mixture_keys_idxs と samplers の長さが一致していません。")

            for idxs, sampler in zip(mixture_keys_idxs, samplers):
                C = sampler.sample(n=n_samples, unique=False)
                for i, j in enumerate(idxs):
                    X[:, j] = C[:, i]

        X_std = X.std(axis=0)
        X_std[X_std == 0] = 1.0
        X_scaled = (X - X.mean(axis=0)) / X_std

        score = calculate_score(X_scaled, opt_type)

        if best_score is None or score > best_score:
            best_X = X
            best_score = score

    df = pd.DataFrame(best_X, columns=factor_names)
    df_cor = df.corr()

    for level in level_encodes:
        if len(level_encodes[level]) > 0:
            df[level] = df[level].apply(lambda x: level_encodes[level][int(x)])

    return df, df_cor

# def optimal_design(
#     enc_items: Dict[str, np.ndarray],
#     level_encodes: Dict[str, Dict[int, Any]],
#     factor_names: List[str],
#     mixture_keys: Optional[List[str]]=None,
#     sum_target: Optional[float]=None,
#     sum_tol: float = 1e-9,
#     opt_type: str = 'D',
#     n_iter: int = 200,
#     n_samples: int = 30,
# ) -> Tuple[pd.DataFrame, pd.DataFrame]:
#     """
#     提案版: Fedorov 交換（1点入替）で単調改良するサンプリング。
#     calculate_score は既存のものをそのまま利用します。
#     """
#     import itertools

#     rng = np.random.default_rng()
#     MAX_CAND = 20000  # 候補集合が大きすぎる場合の安全上限

#     # 1) 候補集合（直積）を作る（大きすぎればサブサンプル）
#     value_lists = [np.asarray(enc_items[f]) for f in factor_names]
#     sizes = [len(v) for v in value_lists]
#     total = int(np.prod(sizes)) if sizes else 0

#     if total == 0:
#         raise ValueError("候補集合が空です。enc_items を確認してください。")

#     if total <= MAX_CAND:
#         cand = np.array(list(itertools.product(*value_lists)), dtype=float)  # (N_cand, d)
#     else:
#         # 直積が巨大な場合はランダムに候補集合をサブサンプル
#         pool_n = min(MAX_CAND, max(10 * n_samples, n_samples))
#         cand = np.column_stack([
#             rng.choice(enc_items[f], size=pool_n) for f in factor_names
#         ])
#         # 行の重複除去（少しでも多様化）
#         cand = np.unique(cand, axis=0)
#         if cand.shape[0] < n_samples:
#             raise ValueError("サブサンプル候補が少なすぎます。MAX_CAND を増やしてください。")

#     if mixture_keys:
#         idxs = [factor_names.index(k) for k in mixture_keys]
#         s = cand[:, idxs].sum(axis=1)
#         mask = np.ones(cand.shape[0], dtype=bool)
#         mask &= np.abs(s - sum_target) <= sum_tol
#         cand = cand[mask]
            
#     # n_samples の妥当性
#     k = min(n_samples, cand.shape[0])
#     if k < 1:
#         raise ValueError("n_samples が小さすぎます。")

#     # スコア計算ヘルパ（既存の calculate_score をそのまま利用）
#     def _score(rows: np.ndarray) -> float:
#         X = rows
#         std = X.std(axis=0, ddof=0)
#         std[std == 0.0] = 1.0  # ゼロ割回避（定数列）
#         X_scaled = (X - X.mean(axis=0)) / std
#         return calculate_score(X_scaled, opt_type)

#     # 2) 初期設計をランダムに選ぶ（重複なし）
#     idx = rng.choice(cand.shape[0], size=k, replace=False)
#     best_score = _score(cand[idx])

#     # 3) Fedorov 交換（1点入替）: 改善がなくなるか n_iter 回で停止
#     it = 0
#     improved = True
#     all_ids = np.arange(cand.shape[0])
#     eps = 1e-12  # 改善判定の閾値（数値誤差対策）

#     while improved and it < n_iter:
#         improved = False
#         it += 1
#         # 各位置について、外して別候補に入替 → 最も改善するものだけ採択
#         for pos in range(k):
#             current = idx.copy()
#             pool = np.setdiff1d(all_ids, current, assume_unique=False)
#             cur_best = best_score
#             best_c = None
#             for c in pool:
#                 trial = current.copy()
#                 trial[pos] = c
#                 s = _score(cand[trial])
#                 if s > cur_best + eps:
#                     cur_best = s
#                     best_c = c
#             if best_c is not None:
#                 idx[pos] = best_c
#                 best_score = cur_best
#                 improved = True

#     # 4) 最良デザインの DataFrame と相関行列
#     best_X = cand[idx]
#     df = pd.DataFrame(best_X, columns=factor_names)
#     df_cor = df.corr()

#     # 5) カテゴリ因子は復号（level_encodes で元ラベルへ）
#     for col in factor_names:
#         enc = level_encodes.get(col, [])
#         if isinstance(enc, dict) and len(enc) > 0:
#             df[col] = df[col].apply(lambda x: enc[int(x)])

#     return df, df_cor


class OptimalDesign:
    def set(
        self,
        factor_names: List[str],
        x_upper: List[float],
        x_lower: List[float],
        x_step: List[float],
        x_levels: List[List[Any]],
        mixture_keys: Optional[Union[List[str], List[List[str]]]] = None,
        sum_target: Optional[Union[float, List[float]]] = None,
    ) -> None:
        """
        因子の設定を行うメソッド。

        Args:
            factor_names: 因子名のリスト
            x_upper: 各因子の上限値
            x_lower: 各因子の下限値
            x_step: 各因子のステップサイズ
            x_levels: 各因子のレベルリスト
            mixture_keys:
                単一グループなら ["A", "B", "C"]
                複数グループなら [["A", "B", "C"], ["D", "E"]]
            sum_target:
                単一グループなら 1.0
                複数グループなら [1.0, 0.5]
        """
        self.factor_names = factor_names
        self.level_encodes, self.enc_items = make_label(
            factor_names,
            x_upper,
            x_lower,
            x_step,
            x_levels
        )

        mixture_groups, mixture_keys_idxs, sum_targets = _normalize_mixture_constraints(
            factor_names=factor_names,
            mixture_keys=mixture_keys,
            sum_target=sum_target,
        )

        if mixture_groups:
            self.mixture_groups = mixture_groups
            self.mixture_keys_idxs = mixture_keys_idxs
            self.sum_targets = sum_targets
            self.samplers = []

            for group, target in zip(mixture_groups, sum_targets):
                self.samplers.append(
                    DiscreteUniformConstrainedSampler(
                        steps=[x_step[factor_names.index(c)] for c in group],
                        lows=[x_lower[factor_names.index(c)] for c in group],
                        highs=[x_upper[factor_names.index(c)] for c in group],
                        sum_value=target,
                        seed=None,
                    )
                )
        else:
            self.mixture_groups = None
            self.mixture_keys_idxs = None
            self.sum_targets = None
            self.samplers = None
    
    def candidate(
        self,
        opt_type: str,
        n_iter: int,
        n_samples: int,
    ) -> pd.DataFrame:
        self.df, self.df_cor = optimal_design(
            enc_items=self.enc_items,
            level_encodes=self.level_encodes,
            factor_names=self.factor_names,
            mixture_keys_idxs=self.mixture_keys_idxs,
            samplers=self.samplers,
            opt_type=opt_type,
            n_iter=n_iter,
            n_samples=n_samples
        )
        return self.df