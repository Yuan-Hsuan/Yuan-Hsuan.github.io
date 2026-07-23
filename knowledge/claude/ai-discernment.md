---
id: ai-discernment
domain: ai
title: Discernment
tags: [claude, ai-fluency, discernment, judgment]
mastery: 1
source: https://anthropic.skilljar.com/ai-fluency-framework-foundations/
visibility: public
---

## 1. The 3 Pillars of Discernment（辨識力的三根支柱）

*Discernment is a trigger, not the endpoint. It doesn't fix the problem; it tells you where to iterate.*

### Product Discernment — 評估產出品質

* Does it add tangible value? (有實質價值嗎？)
* Does it meet the exact requirements and specifications? (符合需求規格嗎？)
* Is it coherent and well-structured? (結構清晰、邏輯連貫嗎？)

**但「我怎麼知道?」** 這個問號本身就是重點：你判斷得出價值與對錯，是因為你懂這個領域；不熟的領域你根本看不出來——這條界線 §2 會講。

*Action:* Make prompts highly specific. Provide few-shot examples, set strict formatting constraints, or pinpoint the exact error and demand a revision.
產出爛通常是**指令太模糊**（輸出是輸入的鏡子）。回去把指令講更具體、給一兩個範例、指定格式，或直接圈出哪裡錯、要它重改。

### Process Discernment — 評估解題過程

* Did it take an inappropriate step or overstep its bounds? (步驟錯誤或越界？)
* Is there a logical inconsistency in its reasoning? (推理自相矛盾？)
* Did it get stuck on trivial details? (卡在細枝末節？)
* Is it trapped in circular reasoning? (鬼打牆／循環推論？)

*Action:* Don't wait for a flawed run to finish. Interrupt immediately. Break large tasks down, force the AI to "plan first, execute later" to expose its logic, or simply point out the misstep. If the context gets too polluted (dirty context), open a clean chat rather than fighting the existing state.
方法歪了**別等它跑完**。當場打斷：把大任務拆小步、要它「先講計畫再動手」把推理攤開來檢查、或直接點出錯的那一步。context 髒到救不動，就開一個乾淨對話重來，別硬凹。

### Performance Discernment — 評估互動表現

* Is the communication style and tone appropriate? (語氣與風格合適嗎？)
* Is the back-and-forth interaction efficient? (一來一往有效率嗎？)

*Action:* Define the persona upfront (e.g., "be concise," "act as a senior systems engineer," "ask before assuming"). If it drifts, correct it immediately with a hard constraint ("Too long, give me only the core bullet points").
一開始就把**角色／風格／長度**設好（「簡短」「像資深系統工程師講話」「先問我再假設」）；一飄掉就當場硬性糾正（「太長，只給我重點條列」）。這類用一句話設定就解掉大半。

## 2. Metacognition: Domain Knowledge vs. Discernment（後設認知：專業深度決定辨識力）

*Understanding the boundaries of your own evaluation skills.*

**1. Making Implicit Judgments Explicit（讓隱性判斷浮出水面）**
You often rely on intuition to spot a "code smell" or architectural flaw in an output. Forcing yourself to articulate *why* it is wrong (e.g., "I know this fails because of X constraint") turns unspoken expertise into concrete, reusable evaluation criteria.
你常靠直覺一眼看出「這 code 有味道」。逼自己講出「我是因為 X 限制才知道它錯」，就把說不出口的專業，變成可以重複使用、講得清楚的判斷標準。

**2. The Trap for Novices（外行人會怎麼卡住）**
AI is highly skilled at producing outputs that are confident, fluent, but factually incorrect. **Fluency does not equal accuracy（流暢 ≠ 正確）.** Without domain knowledge, novices will accept flawed logic because it simply sounds plausible. Only a domain expert can pierce through the confident hallucinations.
AI 超會產出「自信、通順、但錯」的東西。**流暢 ≠ 正確**——外行人沒有專業，會因為「聽起來很有道理」就照單全收；只有懂的人擋得住這種自信的幻覺。

**3. The Boundary of Discernment（你的判斷力上限 = 你的專業深度）**
Your ability to judge quality caps at your level of expertise. In areas where you are strong—like system infrastructure, embedded software, or backend integrations—your discernment is razor-sharp. In unfamiliar territories, your discernment is fundamentally unreliable.
你判斷品質的上限，就是你懂的深度。在你的強項（系統、韌體、後端整合）discernment 很利；踩進不熟的領域，它基本上不可靠。

**4. The Handoff: From Discernment to Diligence（Discernment 弱的地方，用 Diligence 補）**
True AI fluency is knowing where *not* to trust your own judgment. This is metacognition (thinking about your own thinking). When operating outside your primary domain, you must consciously shift strategies: stop relying on Discernment and start applying **Diligence** (external verification, cross-referencing official docs, or consulting experts). Do not let fluent errors lead you astray.
真正的 AI fluency，是知道「哪裡**不能**信自己的判斷」。離開主場時要自覺換策略：別再靠 discernment，改用 [[ai-diligence]]（外部查證、對照官方文件、問專家），別被流暢的錯誤帶走。
