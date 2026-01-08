---
theme: default
background: https://source.unsplash.com/1920x1080/?medical,spine
class: text-center
highlighter: shiki
lineNumbers: false
info: |
  ## 思春期特発性側弯症の真実
  50年間の研究が明かした意外な事実
drawings:
  persist: false
transition: slide-left
title: 思春期特発性側弯症の真実
mdc: true
mermaid:
  theme: neutral
  startOnLoad: true
exportFilename: '思春期特発性側弯症_プレゼンテーション'
download: true
---

# 思春期特発性側弯症の真実

## 50年間の研究が明かした意外な事実

<div class="pt-12">
  <span @click="$slidev.nav.next" class="px-2 py-1 rounded cursor-pointer" hover="bg-white bg-opacity-10">
    アイオワ大学50年追跡研究の成果 <carbon:arrow-right class="inline"/>
  </span>
</div>

---
transition: fade-out
---

# 従来のイメージ vs 現実

<div class="grid grid-cols-2 gap-x-4">

<div>

## 😱 従来の誤解（1968年）

- 高い死亡率
- 重篤な呼吸器障害
- 心肺機能不全
- 早期死亡

<v-click>

**問題点：** 混合病因の症例を含む研究

</v-click>

</div>

<div>

<v-click>

## ✅ 実際の研究結果

- **一般人口と同等の死亡率**
- **正常な生活が可能**
- **就職・結婚・出産可能**
- **高齢まで活動的**

**根拠：** 394人、50年間追跡

</v-click>

</div>

</div>

---

# 研究の歴史的変遷

````md
<div class="grid grid-cols-1 gap-2 text-sm">

**📊 思春期特発性側弯症研究の歴史**

<div class="flex items-center justify-between p-2 bg-blue-100 rounded">
  <div class="font-bold">1932-1948</div>
  <div>Arthur Steindler医師 | 394人のAIS患者を診療</div>
</div>

<div class="flex items-center justify-between p-2 bg-green-100 rounded">
  <div class="font-bold">1950</div>
  <div>Ponseti & Friedman | 初回報告・彎曲パターン確立</div>
</div>

<div class="flex items-center justify-between p-2 bg-red-100 rounded">
  <div class="font-bold">1968</div>
  <div>スウェーデン研究 | 悲観的な予後報告（混合病因含む）</div>
</div>

<div class="flex items-center justify-between p-2 bg-yellow-100 rounded">
  <div class="font-bold">1976-2003</div>
  <div>アイオワ大学 | 50年間の追跡研究・自然史解明</div>
</div>

<div class="flex items-center justify-between p-2 bg-purple-100 rounded">
  <div class="font-bold">2007-2013</div>
  <div>BrAIST試験 | 25施設での装具治療有効性証明</div>
</div>

</div>
````

---

# 実際のリスクとは？

<div class="grid grid-cols-2 gap-4">

<div>

## 📊 数字で見る現実

<v-clicks>

- **68%** の患者で骨格成熟後も彎曲が進行
- **50°以上** で肺機能低下のリスク
- **32%** が外見への不満
- **慢性背部痛** の増加

</v-clicks>

</div>

<div>

<v-click>

````md
<div class="text-center">

**📊 未治療AIS患者の長期転帰**

<div class="grid grid-cols-2 gap-4 mt-4">

<div class="bg-green-200 p-4 rounded">
  <div class="text-3xl font-bold text-green-800">68%</div>
  <div class="text-sm">正常な機能維持</div>
</div>

<div class="bg-orange-200 p-4 rounded">
  <div class="text-3xl font-bold text-orange-800">32%</div>
  <div class="text-sm">外見への不満</div>
</div>

<div class="bg-yellow-200 p-4 rounded">
  <div class="text-3xl font-bold text-yellow-800">25%</div>
  <div class="text-sm">慢性背部痛</div>
</div>

<div class="bg-red-200 p-4 rounded">
  <div class="text-3xl font-bold text-red-800">15%</div>
  <div class="text-sm">肺機能低下<br/>（大彎曲）</div>
</div>

</div>

</div>
````

</v-click>

</div>

</div>

<v-click>

## 💡 重要なポイント

**彎曲角度によってリスクが大きく異なる**

</v-click>

---

# 彎曲角度別リスク分析

````md
<div class="text-center">

**🎯 彎曲角度別リスク分析**

<div class="grid grid-cols-4 gap-2 mt-4">

<div class="bg-green-200 p-3 rounded">
  <div class="font-bold text-green-800">30°未満</div>
  <div class="text-xs mt-2">進行しにくい</div>
  <div class="text-xs">経過観察</div>
</div>

<div class="bg-yellow-200 p-3 rounded">
  <div class="font-bold text-yellow-800">30°-50°</div>
  <div class="text-xs mt-2">中等度リスク</div>
  <div class="text-xs">装具治療検討</div>
</div>

<div class="bg-orange-200 p-3 rounded">
  <div class="font-bold text-orange-800">50°-75°</div>
  <div class="text-xs mt-2">高い進行リスク</div>
  <div class="text-xs">積極的治療</div>
</div>

<div class="bg-red-200 p-3 rounded">
  <div class="font-bold text-red-800">75°以上</div>
  <div class="text-xs mt-2">手術適応</div>
  <div class="text-xs">肺機能低下リスク</div>
</div>

</div>

<div class="mt-4 text-sm text-gray-600">
⬇️ AIS患者 → 骨格成熟時の彎曲角度によって治療方針が決定
</div>

</div>
````

---

# 🏥 装具治療の科学的証拠

## BrAIST試験（2007-2013年）

<div class="grid grid-cols-2 gap-4">

<div>

### 📋 研究概要
- **25施設**（米国・カナダ）
- **大規模無作為化対照試験**
- **レベルI証拠**

<v-click>

### 📈 結果
- **装具治療群：72%** 成功
- **観察群：48%** 成功
- **1日12.9時間以上装着：90-93%** 成功

</v-click>

</div>

<div>

<v-click>

````md
<div class="text-center">

**📈 BrAIST試験 結果**

<div class="grid grid-cols-2 gap-4 mt-4">

<div class="bg-green-200 p-4 rounded">
  <div class="font-bold text-green-800">装具治療群</div>
  <div class="text-3xl font-bold text-green-800 mt-2">72%</div>
  <div class="text-sm">成功率</div>
</div>

<div class="bg-pink-200 p-4 rounded">
  <div class="font-bold text-pink-800">観察群</div>
  <div class="text-3xl font-bold text-pink-800 mt-2">48%</div>
  <div class="text-sm">成功率</div>
</div>

</div>

<div class="bg-lime-200 p-4 rounded mt-4">
  <div class="font-bold text-lime-800">12.9時間以上装着</div>
  <div class="text-4xl font-bold text-lime-800 mt-2">90-93%</div>
  <div class="text-sm">成功率</div>
</div>

<div class="text-sm text-gray-600 mt-2">
2007-2011年 | 米国・カナダ25施設 | レベルI証拠
</div>

</div>
````

</v-click>

</div>

</div>

---

# 🎯 治療選択フローチャート

````md
<div class="text-center">

**🎯 治療選択フローチャート**

<div class="bg-blue-100 p-3 rounded mb-4">
  <div class="font-bold">AIS診断</div>
</div>

<div class="grid grid-cols-2 gap-4">

<div class="border-2 border-blue-300 p-3 rounded">
  <div class="font-bold text-blue-800">10-15歳・未成熟</div>
  
  <div class="grid grid-cols-2 gap-2 mt-3">
    <div class="bg-gray-100 p-2 rounded text-xs">
      <div class="font-bold">20°未満</div>
      <div>経過観察</div>
    </div>
    <div class="bg-sky-200 p-2 rounded text-xs">
      <div class="font-bold">20°-40°</div>
      <div>装具治療</div>
    </div>
    <div class="bg-sky-300 p-2 rounded text-xs">
      <div class="font-bold">40°-50°</div>
      <div>装具強化</div>
    </div>
    <div class="bg-orange-200 p-2 rounded text-xs">
      <div class="font-bold">50°以上</div>
      <div>手術検討</div>
    </div>
  </div>
</div>

<div class="border-2 border-green-300 p-3 rounded">
  <div class="font-bold text-green-800">成熟・成人</div>
  
  <div class="grid grid-cols-1 gap-2 mt-3">
    <div class="bg-gray-100 p-2 rounded text-xs">
      <div class="font-bold">50°未満</div>
      <div>経過観察</div>
    </div>
    <div class="bg-orange-200 p-2 rounded text-xs">
      <div class="font-bold">50°以上進行性</div>
      <div>手術検討</div>
    </div>
  </div>
</div>

</div>

</div>
````

---

# 🌟 現代医療への影響

<div class="grid grid-cols-2 gap-4">

<div>

## ✨ 医療現場の変革

<v-clicks>

1. **手術適応の標準化**
   - 50°以上が標準閾値

2. **装具治療の科学的根拠**
   - レベルI証拠で有効性確立

3. **患者教育の改善**
   - 正確な情報提供

</v-clicks>

</div>

<div>

<v-click>

````md
<div class="text-center">

**🌟 50年研究の影響**

<div class="grid grid-cols-2 gap-4 mt-4">

<div class="bg-blue-200 p-4 rounded">
  <div class="font-bold text-blue-800">手術適応標準化</div>
  <div class="text-sm mt-2">
    • 50°以上が閾値<br/>
    • 予防的固定術
  </div>
</div>

<div class="bg-green-200 p-4 rounded">
  <div class="font-bold text-green-800">装具治療確立</div>
  <div class="text-sm mt-2">
    • 科学的根拠<br/>
    • レベルI証拠
  </div>
</div>

<div class="bg-yellow-200 p-4 rounded">
  <div class="font-bold text-yellow-800">患者教育改善</div>
  <div class="text-sm mt-2">
    • 正確な情報提供<br/>
    • 不安軽減
  </div>
</div>

<div class="bg-purple-200 p-4 rounded">
  <div class="font-bold text-purple-800">医療政策変更</div>
  <div class="text-sm mt-2">
    • 早期診断推進<br/>
    • 手術減少
  </div>
</div>

</div>

</div>
````

</v-click>

</div>

</div>

---

# 📊 治療成績の比較

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

## 💡 重要な教訓

**適切な治療により多くの患者で手術を回避可能**

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

---
layout: center
class: text-center
---

# ありがとうございました

<div class="pt-12">
  <span class="px-2 py-1 rounded cursor-pointer" hover="bg-white bg-opacity-10">
    Questions? <carbon:arrow-right class="inline"/>
  </span>
</div>