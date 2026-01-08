---
theme: default
background: https://source.unsplash.com/1920x1080/?medical,spine
class: text-center
highlighter: shiki
lineNumbers: false
info: |
  ## 思春期特発性側弯症の真実：マーメイド図解版
  50年間の研究が明かした意外な事実をビジュアルで解説
drawings:
  persist: false
transition: slide-left
title: 思春期特発性側弯症の真実：マーメイド図解版
mdc: true
mermaid: true
exportFilename: '思春期特発性側弯症_マーメイド図解_プレゼンテーション'
download: true
---

# 思春期特発性側弯症の真実：マーメイド図解版

## 50年間の研究が明かした意外な事実をビジュアルで解説

<div class="pt-12">
  <span @click="$slidev.nav.next" class="px-2 py-1 rounded cursor-pointer" hover="bg-white bg-opacity-10">
    アイオワ大学50年追跡研究の成果 <carbon:arrow-right class="inline"/>
  </span>
</div>

<style>
.mermaid-container {
  display: flex;
  justify-content: center;
  align-items: center;
  margin: 20px auto;
}
.mermaid {
  max-width: 100%;
  height: auto;
}
.mermaid-small {
  transform: scale(0.8);
  transform-origin: center;
}
.mermaid-xsmall {
  transform: scale(0.65);
  transform-origin: center;
}
</style>

---
transition: fade-out
---

# 研究の歴史的変遷

<div class="mermaid-container" style="height: 450px;">

```mermaid
timeline
    title 思春期特発性側弯症研究の歴史
    
    1932-1948 : Arthur Steindler医師
               : 394人のAIS患者を診療
               : 詳細な記録を保持
    
    1950      : Ponseti & Friedman
               : 初回報告
               : 彎曲パターンの確立
    
    1968      : スウェーデン研究
               : 悲観的な予後報告
               : 混合病因の症例を含む
    
    1976-2003 : アイオワ大学
               : 50年間の追跡研究
               : 自然史の解明
    
    2007-2013 : BrAIST試験
               : 25施設での大規模研究
               : 装具治療の有効性証明
```

</div>

---

# 従来の誤解 vs 新たな発見

<div class="mermaid-container mermaid-small" style="height: 400px;">

```mermaid
graph LR
    A[1968年の研究] --> B[誤解の拡散]
    B --> C[悲観的な予後]
    C --> D[高い死亡率]
    C --> E[重篤な合併症]
    C --> F[心肺機能障害]
    
    G[アイオワ大学研究] --> H[真実の発見]
    H --> I[正常な生活]
    I --> J[就職・結婚可能]
    I --> K[子供を持てる]
    I --> L[一般人口と同等の死亡率]
    
    style A fill:#ffcccc
    style G fill:#ccffcc
    style C fill:#ff9999
    style I fill:#99ff99
```

</div>

<v-click>

## 💡 重要なポイント

**従来の悲観的な見方は混合病因の症例を含む研究による誤解**

</v-click>

---

# 彎曲角度別リスク分析

<div class="mermaid-container mermaid-small" style="height: 420px;">

```mermaid
graph TD
    A[AIS患者] --> B{骨格成熟時の彎曲角度}
    
    B --> C[30°未満]
    B --> D[30°-50°]
    B --> E[50°-75°]
    B --> F[75°以上]
    
    C --> C1[進行しにくい]
    C --> C2[経過観察]
    
    D --> D1[中等度リスク]
    D --> D2[装具治療検討]
    
    E --> E1[高い進行リスク]
    E --> E2[積極的治療]
    E --> E3[特に胸椎彎曲]
    
    F --> F1[手術適応]
    F --> F2[肺機能低下リスク]
    
    style C fill:#90EE90
    style D fill:#FFD700
    style E fill:#FFA500
    style F fill:#FF6347
```

</div>

---

# 未治療AISの実際のリスク

<div class="grid grid-cols-2 gap-4">

<div class="mermaid-container" style="height: 300px;">

```mermaid
pie title 未治療AIS患者の長期転帰
    "正常な機能維持" : 68
    "慢性背部痛" : 25
    "外見への不満" : 32
    "肺機能低下(大彎曲)" : 15
```

</div>

---

<div class="mermaid-container mermaid-xsmall" style="height: 300px;">

```mermaid
graph LR
    A[未治療AIS患者] --> B[68%が彎曲進行]
    A --> C[背部痛増加]
    A --> D[外見への不満]
    A --> E[50°以上で肺機能低下]
    
    F[しかし] --> G[正常な就労可能]
    F --> H[結婚・出産可能]
    F --> I[高齢まで活動的]
    
    style F fill:#98FB98
    style G fill:#98FB98
    style H fill:#98FB98
    style I fill:#98FB98
```

</div>

</div>

<v-click>

## 💡 重要な発見

**多くの患者は未治療でも正常な生活を送れる**

</v-click>

---

# BrAIST試験結果

<div class="mermaid-container mermaid-small" style="height: 450px;">

```mermaid
graph TD
    A[BrAIST試験] --> B[米国・カナダ25施設]
    A --> C[2007-2011年登録]
    
    D[装具治療群] --> E[成功率72%]
    F[観察群] --> G[成功率48%]
    
    H[装具装着時間] --> I{1日12.9時間以上}
    I -->|Yes| J[成功率90-93%]
    I -->|No| K[成功率低下]
    
    L[結論] --> M[装具治療の有効性証明]
    M --> N[レベルI証拠]
    
    style E fill:#90EE90
    style G fill:#FFB6C1
    style J fill:#00FF00
```

</div>

---

# 治療選択フローチャート

<div class="mermaid-container mermaid-xsmall" style="height: 480px;">

```mermaid
flowchart TD
    A[AIS診断] --> B{年齢・骨格成熟度}
    
    B --> C[10-15歳・未成熟]
    B --> D[成熟・成人]
    
    C --> E{Cobb角度}
    
    E --> F[20°未満]
    E --> G[20°-40°]
    E --> H[40°-50°]
    E --> I[50°以上]
    
    F --> F1[経過観察]
    G --> G1[装具治療]
    H --> H1[装具治療強化]
    I --> I1[手術検討]
    
    D --> J{現在のCobb角度}
    J --> K[50°未満]
    J --> L[50°以上進行性]
    
    K --> K1[経過観察]
    L --> L1[手術検討]
    
    style G1 fill:#87CEEB
    style H1 fill:#87CEEB
    style I1 fill:#FFA07A
    style L1 fill:#FFA07A
```

</div>

---

# 現代医療への影響

<div class="mermaid-container" style="height: 450px;">

```mermaid
mindmap
  root((50年研究の影響))
    手術適応標準化
      50°以上が閾値
      予防的固定術
      進行予防
    装具治療確立
      科学的根拠
      レベルI証拠
      個別化治療
    患者教育改善
      正確な情報提供
      根拠に基づく選択
      不安軽減
    医療政策変更
      スクリーニング見直し
      早期診断推進
      手術減少
```

</div>

---

# 治療成績の比較

<div class="grid grid-cols-3 gap-4">

<div>

## 🔍 観察のみ
**成功率：48%**

- 自然経過を観察
- 定期的な検査
- 進行時に治療検討

</div>

<div>

## 🦴 装具治療
**成功率：72%**

- 日中装着
- 定期的な調整
- **12.9時間以上で90-93%**

</div>

<div>

## ⚕️ 手術治療
**50°以上で適応**

- 器械固定術
- 進行予防
- 変形矯正

</div>

</div>

<v-click>

<div class="mermaid-container" style="height: 200px; margin-top: 20px;">

```mermaid
graph LR
    A[治療選択] --> B{成功率}
    B --> C[観察: 48%]
    B --> D[装具: 72%]
    B --> E[装具12.9h+: 90-93%]
    
    style C fill:#FFB6C1
    style D fill:#90EE90
    style E fill:#00FF00
```

</div>

</v-click>

---
layout: center
class: text-center
---

# まとめ

<v-clicks>

## 🎯 重要なポイント

**従来の悲観的な見方は誤解**

**未治療でも多くが正常な生活を送れる**

**装具治療は科学的に有効**

**適切な情報に基づく治療選択が重要**

## 🏆 50年間の継続研究の意義

**根拠に基づく医療の重要性を示す素晴らしい例**

</v-clicks>

<div class="mermaid-container mermaid-small" style="height: 250px; margin-top: 20px;">

```mermaid
graph LR
    A[50年研究] --> B[真実の解明]
    B --> C[適切な治療]
    C --> D[患者の幸福]
    
    style A fill:#87CEEB
    style B fill:#90EE90
    style C fill:#FFD700
    style D fill:#FF69B4
```

</div>

---
layout: center
class: text-center
---

# ありがとうございました

<div class="mermaid-container" style="height: 300px;">

```mermaid
graph TD
    A[Questions?] --> B[Discussion]
    B --> C[Future Research]
    
    style A fill:#87CEEB
    style B fill:#90EE90
    style C fill:#FFD700
```

</div>

<div class="pt-12">
  <span class="px-2 py-1 rounded cursor-pointer" hover="bg-white bg-opacity-10">
    ご質問をお待ちしております <carbon:arrow-right class="inline"/>
  </span>
</div>