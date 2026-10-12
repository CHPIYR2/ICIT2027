# EBRL 關聯判定規格（ebrl.contract.v1）

本規格描述已經實作並由 `tests/test_ebrl.py` 執行的規則。閾值是預先指定，不是 Sherlock 開發集調參結果。相容性不是因果。

## 兩個軸

- 處置：`L` 受支持的關聯、`N` 有可見反證的非關聯、`U` 證據不足。沒有出現在正例清單中，不得改記成 `N`。
- 語意上限：`R0` 沒有跨模態關聯；`R1` 只到共同出現或時間關係；`R2` 時間、資產與命令–變數語意支持有限關聯；`R3` 另有獨立操作回應；`R4` 另有獨立動作–效果來源。
- `R1` 的 `L` 是時間性 link，不是操作性 link。論文評分公式仍把任何有效的 `L` 算進 \(p_c\)。實作遵守該定義，並在報告文字裡禁止把 `R1`/`R2` 寫成執行或因果。
- 執行、完成、因果、資安是獨立旗標。`R2` 四個旗標都必須為假。IEC-104 COT 7 或 TCP ACK 不能把完成設為真。

## 可見證據如何做成決定

1. 命令交易依 flow、CA、IOA、type 與 5 秒間隔成組。重傳併入同一筆。Select 之後有 operate 才是一筆操作；只有 select 則為 `U`（`SELECT_WITHOUT_OPERATE`）。
2. 遙測必須有前後值。缺值保持缺值，不補 0。變化要超過單位 deadband，或是布林狀態翻轉。
3. 候選是 episode 配對：時間差不超過 30 秒，或資產相同／位於凍結的鄰接表。列舉本身不下關聯結論。
4. 反證優先於正關聯：
   - 映射明確指向不同且非鄰接資產，且時間接近 → `N` / `ASSET_CONTRADICTION`
   - 同資產但命令與變數在本體中不相容 → `N` / `SEMANTIC_INCOMPATIBILITY`
   - 同資產、語意相容、方向相反、品質可用 → `N` / `DIRECTION_CONTRADICTION`
   - 同資產、語意相容、效果時間早於命令超過 1 秒 → `N` / `TIME_ORDER_CONTRADICTION`
5. 下列情況是 `U`，不是 `N`：品質不良或過期、競爭命令中較差的一筆、只有鄰接資產、設定值與量測值同名不同 context、映射缺失但時間也不構成共同出現。
6. 同資產、語意相容、方向一致、命令早於效果超過 1 秒、品質可用 → `L` / `R2`。旗標全假。
7. 時間差落在 1 秒時鐘偏差內 → 最多 `L` / `R1`（順序未解）。不得升到 `R2`。
8. 只有當可見證據裡另有 `operational_response`（不是協定確認）才到 `R3`，並可設 execution。只有另有 `action_effect` 才到 `R4`，並可設 completion 與 causal。security 不由異常或事件標籤推出。

## Verifier

Verifier 不讀 evaluator-only 標籤，也不能把 `U` 改成 `N` 或把 `N` 改成 `L`。優先順序見 `configs/ebrl/verifier_rules.v1.json`。

- 結構壞、候選不符、證據 ID 不可見或角色錯誤：列無效。無效列沒有棄答分數。
- 沒有反證卻主張 `N`：降為 `U`。
- 層級高於可見上限，或用 ACK 主張執行／完成：降級並清除旗標。
- 多重失敗時採取最嚴格結果，並保留全部 finding 與原始提案。

Verifier 與規則 proposer 在合法提案上常常一致。這只表示提案沒有越界，不表示關聯在操作上為真。

## 三個可重播案例

合成事件，不是 Sherlock。以 P1 執行 `scripts/run_ebrl.py` 或 `scripts/evaluate_ebrl.py` 可重現。

1. `syn_open_supported`：開斷路器命令後，回報狀態由閉合變為開啟。發布 `L`/`R2`，旗標全假。報告寫明不成立執行、完成或因果。Artifact `8a073037e5a77d8249e96b7256f644586db82b5408d527ce6fb063cb47edfe45`。
2. `syn_deceptive_cooccurrence`：可見證據與案例 1 同型，所以政策上限仍是 `L`/`R2`；旁路的合成獨立標籤是操作上非關聯。Verifier 保留該列。這列在政策軸可接受，在事實軸是不支持的關聯。
3. `syn_wrong_asset`：命令映射到 `breaker_7`，電流變化在 `line_9`。發布 `N` / `ASSET_CONTRADICTION`。同一候選上，B1 仍會因為時間最近而給 `L`/`R1`。

另：`syn_operational_response` 在可見證據含獨立操作回應時到 `R3`，completion 仍為假。協定 ACK 本身到不了這一層。
