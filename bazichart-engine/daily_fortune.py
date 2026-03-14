from __future__ import annotations

from datetime import date as date_type, datetime
from hashlib import sha256
from random import Random
from typing import Any


TIANGAN = "甲乙丙丁戊己庚辛壬癸"
DIZHI = "子丑寅卯辰巳午未申酉戌亥"
STEM_WUXING = {
    "甲": "木",
    "乙": "木",
    "丙": "火",
    "丁": "火",
    "戊": "土",
    "己": "土",
    "庚": "金",
    "辛": "金",
    "壬": "水",
    "癸": "水",
}
GENERATES = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
CONTROLS = {"木": "土", "火": "金", "土": "水", "金": "木", "水": "火"}
LUCKY_COLORS = {
    "木": {"zh": "青绿色", "en": "Verdant Green"},
    "火": {"zh": "红色", "en": "Crimson Red"},
    "土": {"zh": "黄色", "en": "Earth Gold"},
    "金": {"zh": "白色", "en": "Ivory White"},
    "水": {"zh": "黑蓝色", "en": "Midnight Blue"},
}
LUCKY_DIRECTIONS = {
    "木": {"zh": "正东", "en": "East"},
    "火": {"zh": "正南", "en": "South"},
    "土": {"zh": "中宫", "en": "Center"},
    "金": {"zh": "正西", "en": "West"},
    "水": {"zh": "正北", "en": "North"},
}
LUCKY_NUMBERS = {"木": 3, "火": 9, "土": 5, "金": 7, "水": 1}
GENERAL_MESSAGES = {
    "木": [
        {"zh": "木气升发之日，适合启动新计划，循序渐进更容易见效。", "en": "Green forces rise today. Begin gently, and let steady steps become momentum."},
        {"zh": "今日木意渐旺，利于沟通协作和拓展新方向。", "en": "Growth leans your way. Speak, connect, and open one new path."},
        {"zh": "木性能量偏强，适合学习成长，也宜多亲近自然。", "en": "The day favors learning and renewal. Let your mind grow where the air is open."},
        {"zh": "春木有声，今天宜向前开枝散叶，把想法种进现实。", "en": "Springwood is speaking. Plant one idea in the real world and let it take root."},
        {"zh": "木气舒展之时，利结盟、利发愿，凡事以生长为先。", "en": "When wood stretches, alliances come easier. Choose what allows life to widen."},
        {"zh": "今日像清晨新枝，适合开启、接洽与温和推进。", "en": "This day feels like a fresh branch at dawn. Begin softly and move with grace."},
        {"zh": "木旺则生，适合布局长期目标，不必急着立刻求成。", "en": "Growth rewards patience today. Build for the long horizon, not for instant applause."},
        {"zh": "山林初醒之日，适合学习、面谈和打开新的可能。", "en": "The forest has just awakened. Study, meet, and let possibility breathe."},
        {"zh": "木意向上，宜把停滞之事轻轻推开，让节奏重新流动。", "en": "The upward current is alive. Nudge what has stalled and let rhythm return."},
        {"zh": "今日重在生发，适合写计划、见新友、走新路。", "en": "Today belongs to beginnings. Draft, meet, and walk one road you have not tried."},
        {"zh": "木气清润，利于修复关系，也利于让旧事抽出新芽。", "en": "Tender growth can mend old ties. What seemed finished may sprout again."},
        {"zh": "今天宜做有延续性的事，播种比收割更重要。", "en": "Favor what can continue beyond tonight. Sowing matters more than harvesting."},
        {"zh": "东方木旺，适合先动一小步，再让局面自然展开。", "en": "The east wind supports first steps. Begin small and trust expansion to follow."},
        {"zh": "枝叶向光，今天适合把压在心里的事说清楚。", "en": "Leaves turn toward light. Say clearly what has been living in your chest."},
        {"zh": "木日宜长不宜躁，把耐心当作最稳的力量。", "en": "This is a day for length, not haste. Let patience be your strongest form of power."},
    ],
    "火": [
        {"zh": "火旺之日，宜大胆行动，把握机遇，主动表达更容易被看见。", "en": "Fire crowns the day. Move boldly, speak clearly, and let yourself be seen."},
        {"zh": "今日火势明朗，适合推进卡住的事务，但要避免急躁。", "en": "Clarity burns bright today. Push what is stuck, but do not let haste scorch it."},
        {"zh": "火能量上扬，利执行与展示，重要决定宜趁势落实。", "en": "The flame rises. Act, present, decide — this is a day to make things real."},
        {"zh": "日光正盛之时，适合提速推进，把重点放在最关键的一步。", "en": "The noon sun asks for one decisive move. Put your force where it matters most."},
        {"zh": "火意通明，今天宜发声、宜出手，也宜把目标说得更明确。", "en": "Light favors candor. Speak, act, and name your aim without blur."},
        {"zh": "火旺则成势，适合冲刺、提案、展示与公开表达。", "en": "Momentum leans toward courage. Pitch, perform, and bring your work into the open."},
        {"zh": "今日有烈火开路之象，宜打破拖延，把犹豫化成动作。", "en": "A bright blaze clears the path. Turn delay into motion."},
        {"zh": "火在天中，适合把能量集中在最重要的人和事上。", "en": "Fire stands at the center of the sky. Spend yourself only on what truly matters."},
        {"zh": "今天宜主动照亮局面，但不必把自己烧得太急。", "en": "Light the room, not your nerves. Warmth works better than frenzy."},
        {"zh": "火气上行，适合签字、答复、定调，先行者更易得势。", "en": "The upward flame favors commitment. Answer, sign, and set the tone before the crowd does."},
        {"zh": "今日像午阳正炽，适合出面承担，也适合确立存在感。", "en": "Today is a blazing noon. Step forward and take visible responsibility."},
        {"zh": "火日利决断，拖久的事今天更适合当场定下。", "en": "This fire-day prefers resolution. What has waited too long wants a clean answer now."},
        {"zh": "光明之气偏盛，今天宜直面问题，不宜绕圈消耗。", "en": "The day rewards directness. Meet the issue in the open and stop circling it."},
        {"zh": "火力充盈，适合把准备已久的内容推到台前。", "en": "Your stored heat is ready. Bring forward what you have long prepared."},
        {"zh": "今天的关键是果敢，不是喧哗，点准一处就能见效。", "en": "What matters today is courage, not noise. One well-placed action can change the field."},
    ],
    "土": [
        {"zh": "土气稳重之日，适合整理秩序、夯实基础，凡事求稳更佳。", "en": "Earth steadies the day. Sort, anchor, and choose what can truly hold."},
        {"zh": "今日土势厚实，利于收尾总结，也适合处理现实问题。", "en": "The ground is strong today. Finish well and handle practical matters with calm hands."},
        {"zh": "土能量偏强，适合沉淀资源、修正细节，不宜操之过急。", "en": "Earth asks for patience. Consolidate, correct, and let thoroughness carry the weight."},
        {"zh": "厚土承载之日，适合落地、归档、理账和完成收束。", "en": "A carrying earth-day favors closure, records, accounts, and solid endings."},
        {"zh": "今日宜把地基打稳，少一些浮动，多一些确定。", "en": "Lay the foundation deeper today. Trade restlessness for certainty."},
        {"zh": "土气安定，适合处理住房、财务、合同和长期安排。", "en": "Stability is available. Home, money, contracts, and long plans all benefit."},
        {"zh": "今天更适合慢而准，不适合频繁改方向。", "en": "Move slowly and exactly. Frequent turns will cost more than they return."},
        {"zh": "山势稳固，今日利守成、利收纳、利把散乱归位。", "en": "The mountain stands firm. Keep what matters, store what is useful, return order to the scattered."},
        {"zh": "土旺之日，适合补漏洞、立规则、修正长期结构。", "en": "Earth favors repair and structure. Patch the cracks before reaching further."},
        {"zh": "今天像秋田归仓，适合把分散的资源重新聚拢。", "en": "Like grain returning to the storehouse, gather what has been spread too thin."},
        {"zh": "土日重在落实，说过的话最好今天就形成结果。", "en": "Earth values follow-through. Let your words become outcomes before night."},
        {"zh": "地气厚而不争，适合做那些看似平淡却最能定局的事。", "en": "The ground does not boast. Quiet work will shape more than dramatic effort."},
        {"zh": "今日宜向内整顿，把秩序感重新找回来。", "en": "Turn inward and restore order. Stability begins in the unseen places."},
        {"zh": "土能收心，适合从复杂里筛出真正要保留的部分。", "en": "Let earth settle the dust. Keep only what deserves to remain."},
        {"zh": "今天不必求快，能把一件事做实，就已经很有分量。", "en": "Speed is not the prize today. One solid act outweighs many restless ones."},
    ],
    "金": [
        {"zh": "金气肃清之日，适合做判断、立边界，简化事务更有效率。", "en": "Metal clears the air. Decide, define the line, and cut away excess."},
        {"zh": "今日金性能量明显，利于定标准、做取舍，但表达宜留余地。", "en": "Sharpness serves you today. Set standards, make choices, but leave a little mercy in your tone."},
        {"zh": "金势清明，适合处理合同、规则与关键决策。", "en": "The day is bright with precision. Contracts, rules, and key decisions are favored."},
        {"zh": "金风起时，今天适合切断拖累，保留真正重要的部分。", "en": "When the metal wind rises, release what drains you and keep what rings true."},
        {"zh": "今日宜断舍离，把模糊的界限收紧，把重点提纯。", "en": "Tighten the blurred edges. Purity comes through reduction."},
        {"zh": "金日贵在分明，适合审核、裁剪、谈原则与谈底线。", "en": "Clarity is the blessing of this day. Review, refine, and speak from principle."},
        {"zh": "今天像秋刃出鞘，适合快刀斩乱麻，但不宜情绪化决策。", "en": "A clean blade is available. Use it for confusion, not for anger."},
        {"zh": "金气凝练，适合做最后确认，去掉多余环节。", "en": "Condensed metal favors final checks and cleaner systems."},
        {"zh": "今日宜先辨是非轻重，再决定投入哪里。", "en": "Discern weight before effort. Not everything deserves your hand."},
        {"zh": "金能成器，适合打磨作品、修订表达、提升质量。", "en": "Metal makes a vessel by refinement. Polish the work, sharpen the language."},
        {"zh": "今天重在精准，不在铺开，聚焦反而更有力度。", "en": "Precision has more force than spread. Narrow your aim."},
        {"zh": "金日适合签约、复核、定价，也适合为自己立边界。", "en": "Sign, verify, price, and protect your own edges."},
        {"zh": "清肃之气当令，今天宜少说废话，多做关键动作。", "en": "The air is crisp enough for essential action. Waste fewer words."},
        {"zh": "今日适合把复杂问题拆开处理，次序会带来掌控感。", "en": "Disassemble complexity. Order will return your sense of control."},
        {"zh": "金势见锋，适合给长期拖延的事一个明确答案。", "en": "The blade is visible now. Give your delayed question a clear answer."},
    ],
    "水": [
        {"zh": "水气流动之日，适合思考、调研与调整节奏，顺势而为更顺畅。", "en": "Water moves through the day. Think, observe, and let timing do part of the work."},
        {"zh": "今日水势活跃，利于复盘、沟通和策略布局。", "en": "The current is alive. Reflect, converse, and shape your strategy."},
        {"zh": "水能量渐强，适合观察局势、整合信息，再决定下一步。", "en": "Water deepens before it acts. Gather the pattern, then choose your move."},
        {"zh": "江河有势之日，适合迂回推进，不必凡事正面碰撞。", "en": "Rivers know another way. Advance by curve rather than collision."},
        {"zh": "今天宜先看局、后出手，柔一点反而更容易到达。", "en": "See the whole field before you strike. Softness may reach farther."},
        {"zh": "水意深长，适合写作、思考、谈判与隐性布局。", "en": "Depth favors writing, thought, negotiation, and quiet design."},
        {"zh": "今日像夜潮渐满，适合收集信息，把分散线索串起来。", "en": "Like a tide at night, today gathers clues into a single shore."},
        {"zh": "水旺则智，适合复盘趋势，也适合留白等待更好时机。", "en": "Wisdom rises with the waters. Review the trend, then allow space."},
        {"zh": "今天更适合顺流调整，而不是强行硬推。", "en": "Adjust with the flow rather than forcing the river."},
        {"zh": "水日宜通不宜塞，把情绪和信息都保持流动。", "en": "Let both feeling and thought keep moving. Stagnation costs more today."},
        {"zh": "今日可多听少争，往往能在细微处先看出方向。", "en": "Listen more than you contend. Direction often appears in the subtle places."},
        {"zh": "水能润物，适合修复关系、缓和气氛与重新连接。", "en": "Water restores quietly. Mend, soften, and reconnect."},
        {"zh": "今天像云水相接，适合做策略，不急着亮全部底牌。", "en": "Cloud meets water today. Plan deeply; reveal slowly."},
        {"zh": "水势灵动，临机应变会比提前僵定更有效。", "en": "Fluid response will serve you better than rigid plans."},
        {"zh": "今日宜借势而行，把锋芒藏在更长远的布局里。", "en": "Travel with the current and hide your edge inside a longer design."},
    ],
}
PERSONAL_MESSAGES = {
    "生我": [
        {"zh": "当日{day_ganzhi}之气来生扶日主{day_master}，适合争取资源与外部支持。", "en": "The day nourishes your core. Ask, connect, and let support find you."},
        {"zh": "今日能量偏向助力，日主{day_master}更容易得到回应，宜主动推进关键事务。", "en": "Help moves toward you today. Advance what matters while the response is warm."},
        {"zh": "当日五行生身，利学习提升、人脉合作与重要沟通。", "en": "The current feeds your spirit. Learn, collaborate, and speak where it counts."},
        {"zh": "今日天时对日主{day_master}有扶持，适合把计划提上台面。", "en": "Time itself is lifting you. Bring your plan into the open."},
        {"zh": "外部气场偏向相助，日主{day_master}今天更容易借势成事。", "en": "Outer forces lean in your favor. Let momentum help carry the work."},
        {"zh": "生扶之日宜接人、借力、求解法，独斗不如联动。", "en": "Today is better for joining hands than proving you can stand alone."},
        {"zh": "今天更适合向外连接，支持会比预想来得更快。", "en": "Reach outward. Aid may arrive sooner than you expect."},
        {"zh": "日主{day_master}得助，适合谈条件、谈合作，也适合请益。", "en": "You are easier to receive today. Negotiate, partner, and ask the wise."},
        {"zh": "今天的运势像顺风，适合把最重要的一步走出去。", "en": "There is a tailwind here. Use it for the step that matters most."},
        {"zh": "当日之气补足你，宜学习、签约、争取和表达核心诉求。", "en": "What is lacking is being filled. Study, commit, ask, and name your true need."},
        {"zh": "今日贵在借势，资源、人脉、信息都可能成为助力。", "en": "Leverage is the key today. Resources, people, and timing can all help."},
        {"zh": "生身之日宜开口，也宜打开更大的格局，不必过度保守。", "en": "Speak and widen the frame. This is not the day for unnecessary caution."},
        {"zh": "日主{day_master}今天易得回响，重要消息适合主动发出。", "en": "Your signal travels well today. Send the message that needs a clear echo."},
        {"zh": "今天像有看不见的托举，做事会比平日更有底气。", "en": "Something unseen is holding you up. Act from that quiet confidence."},
        {"zh": "顺势之日不宜缩手，越主动越容易接到回应。", "en": "Do not shrink in a favorable current. Response follows movement."},
    ],
    "我克": [
        {"zh": "日主{day_master}可驾驭当日之气，财务与执行层面更易见成果。", "en": "You hold the reins today. Results favor practical movement and wise claiming."},
        {"zh": "今天属于可掌控的一天，适合谈结果、抓重点、推动落地。", "en": "This day answers to clear hands. Focus, negotiate, and bring things down to earth."},
        {"zh": "我克者为财，今日更适合资源调配和务实行动。", "en": "What you master can become value. Use the day for resource and return."},
        {"zh": "日主{day_master}今日有掌局之势，适合把松散事务一并收拢。", "en": "Your grip is stronger today. Gather what has been loose."},
        {"zh": "今天利拿结果，不利空谈，越务实越容易见回报。", "en": "Results love realism today. Less theory, more touch."},
        {"zh": "我克之日适合定预算、谈条件、收资源与抓节奏。", "en": "Budget, terms, assets, timing — all can be shaped in your favor."},
        {"zh": "今日更适合做决定的人，而不是等待的人。", "en": "This is a day for choosers, not for watchers."},
        {"zh": "掌控力上升，适合推进财务、交易、执行与收尾。", "en": "Your command is sharpened. Push money, exchange, execution, and closure."},
        {"zh": "日主{day_master}今天更能拿住局面，但也要避免过刚。", "en": "You can hold the field today, but strength works best without hardness."},
        {"zh": "今天适合把目标切成可执行动作，一步一收效。", "en": "Break the aim into acts. Let each step become visible gain."},
        {"zh": "我克为财，今天更容易把潜在机会变成实在结果。", "en": "Potential can become profit today if you touch it directly."},
        {"zh": "今日可优先处理现实收益，少分心，效率会更高。", "en": "Attend to what yields. Concentration is worth more than ambition right now."},
        {"zh": "你对局面的驾驭感增强，适合定方向、定资源、定人选。", "en": "You read the field well today. Set direction, assign resources, choose well."},
        {"zh": "今天利谈判、利推进，也利把边界说清楚。", "en": "Negotiate, advance, and state your terms with clean edges."},
        {"zh": "掌控之日宜稳中求进，越清楚越能得到实际成果。", "en": "Progress through clarity. Precision will return tangible reward."},
    ],
    "克我": [
        {"zh": "当日之气对日主{day_master}形成压力，宜稳住节奏，先难后易。", "en": "The day presses on you. Keep your pace steady and let pressure ripen into order."},
        {"zh": "今天容易感到被催逼，关键在于保留体力，不宜硬碰硬。", "en": "You may feel pushed. Guard your strength and do not answer force with force."},
        {"zh": "克身之日适合收敛锋芒，先处理确定性高的事项。", "en": "This is a day for measured edges. Begin with what is most certain."},
        {"zh": "外部压力偏强，日主{day_master}今天更适合先守后攻。", "en": "Outer pressure is high. Defend your center before you advance."},
        {"zh": "今日宜减法，不必事事回应，把力气留给关键处。", "en": "Choose subtraction. Not every call deserves your answer."},
        {"zh": "被克之日更考验分寸，先稳住情绪，局面才会转松。", "en": "Measure matters today. Calm is the hinge on which the field will loosen."},
        {"zh": "今天容易遇到推进阻力，先设边界再谈效率更好。", "en": "Resistance may greet you first. Boundaries before speed."},
        {"zh": "日主{day_master}今日不宜逞强，退半步反而更能掌握主动。", "en": "Do not prove yourself by force. One mindful step back may regain the lead."},
        {"zh": "今天要防过度消耗，能延期的争执尽量不要硬接。", "en": "Protect your reserves. Let needless conflicts wait."},
        {"zh": "克我之时宜谨慎答复，先观察对方真实意图。", "en": "Answer carefully. Watch for intent beneath the surface."},
        {"zh": "今天适合做风控、做备选方案，不适合孤注一掷。", "en": "Favor risk control and second plans. This is no day for all-in gestures."},
        {"zh": "外力偏重，宜重整次序，把最重要的事先护住。", "en": "Weight is in the air. Reorder and protect what must not be lost."},
        {"zh": "日主{day_master}今天更需要安静与清醒，而非盲目加速。", "en": "Quiet sight serves you better than blind speed."},
        {"zh": "面对压力时，节奏感会比爆发力更重要。", "en": "Under pressure, rhythm outlives force."},
        {"zh": "今天宜守心守序，先稳住自己，再稳住局面。", "en": "Keep your inner order. The outer order will follow."},
    ],
    "我生": [
        {"zh": "日主{day_master}向外泄秀，适合输出创意与表达，但也要注意精力分配。", "en": "Your energy pours outward today. Create, speak, but spend yourself with care."},
        {"zh": "今天更像付出型的一天，利分享、呈现与帮助他人。", "en": "This is a giving day. Offer, present, and help where you can."},
        {"zh": "我生之日宜做内容、复盘与沟通，不宜把日程排得过满。", "en": "Make, reflect, communicate — but leave room in the calendar for breath."},
        {"zh": "日主{day_master}今日更适合表达观点，把想法落成语言。", "en": "Your thoughts want form today. Let them become language."},
        {"zh": "今天适合输出、答疑、教学、汇报，也要给自己留余地。", "en": "Teach, explain, report — and still keep a corner of yourself unspent."},
        {"zh": "能量向外流动，适合创作与呈现，但不宜过度透支。", "en": "The stream runs outward. Make beauty, but do not empty the source."},
        {"zh": "我生日适合把沉淀已久的内容讲出来、写出来、做出来。", "en": "What has long rested in you is ready to be spoken or shaped."},
        {"zh": "今日利口才与灵感，但要防做得太多而顾不上回收。", "en": "Speech and inspiration are favored, yet do not forget to gather yourself back."},
        {"zh": "日主{day_master}今天适合给予，也适合把价值公开化。", "en": "Give what is true today, and let your value be visible."},
        {"zh": "今天你更像灯火，适合照亮别人，也别忘了补充自己。", "en": "You are lantern-like today. Illuminate, but refill the oil."},
        {"zh": "我生之时宜做公开表达，不宜长时间闷在心里。", "en": "Expression heals better than silence today."},
        {"zh": "今日适合发作品、做展示、做复盘，但别把全部能量一次耗尽。", "en": "Share the work, show the craft, but keep some flame for tomorrow."},
        {"zh": "今天重在输出，不在争胜，稳稳讲清楚就是力量。", "en": "Today strength lies in expression, not in conquest."},
        {"zh": "日主{day_master}今天更适合以柔和方式影响他人。", "en": "Influence travels farther today through gentleness than force."},
        {"zh": "你今天适合发散与创造，收尾和硬推进可以稍后安排。", "en": "Create first, close later. Let imagination lead for now."},
    ],
    "同我": [
        {"zh": "同气相求，日主{day_master}今日更容易获得共鸣与同伴支持。", "en": "Like calls to like. Companionship and resonance are easier to find today."},
        {"zh": "比和之日适合团队协作、资源互通，也要防止固执己见。", "en": "A shared current favors teamwork, though stubbornness may wear a friendly face."},
        {"zh": "今日与自身频率相近，适合强化已有节奏和长期计划。", "en": "The day hums in your own key. Strengthen what is already true."},
        {"zh": "同类之气相逢，日主{day_master}今天容易遇到懂你的人。", "en": "Your kind of weather is in the air. You may meet those who understand without effort."},
        {"zh": "今日利合伙、利对齐目标，也利巩固既有优势。", "en": "Partnership, alignment, and consolidation all carry good fortune now."},
        {"zh": "同我之日宜做团队动作，单点突破不如彼此借力。", "en": "Shared force works better than lone brilliance today."},
        {"zh": "今天更适合延续已有节奏，把熟悉的事做到更深。", "en": "Stay with what already has rhythm and deepen it."},
        {"zh": "同频之日容易有默契，也要留心避免谁都不肯退一步。", "en": "Harmony is close at hand, though pride may stand in the doorway."},
        {"zh": "日主{day_master}今天适合见老朋友、老客户、老搭档。", "en": "Old allies and familiar circles are especially useful today."},
        {"zh": "今天更利于守成中的增长，稳扎稳打会比冒进更好。", "en": "Growth through steadiness will serve you better than sudden leaps."},
        {"zh": "同类气场增强，利聚人、利协同，也利建立更稳的信任。", "en": "The familiar current strengthens trust and shared movement."},
        {"zh": "今日适合在熟悉领域精进，把已有资源再整合一次。", "en": "Refine within the known and gather your resources into one hand."},
        {"zh": "今天的好运来自同频，不必强行取悦，只需保持真实。", "en": "Fortune comes through resonance, not performance. Be true, not impressive."},
        {"zh": "日主{day_master}今日适合修复关系、重启合作与共同行动。", "en": "This is a good day to restore bonds and renew shared work."},
        {"zh": "同我之日宜抱团成势，也宜把边界和分工先谈清楚。", "en": "Gather strength together, but name roles and limits with care."},
    ],
}
BLESSINGS = [
    {"zh": "愿你今日所行皆坦途。", "en": "May every road beneath you open with ease."},
    {"zh": "愿你今天心定事成，步步有回应。", "en": "May calm guide your hands, and may each step answer back."},
    {"zh": "愿你在今日的节奏里，稳稳接住好运。", "en": "May you receive today’s fortune with steady hands."},
    {"zh": "愿你今日所想有光，所行有成。", "en": "May your thoughts find light, and your actions find form."},
    {"zh": "愿你心里有山，脚下有路。", "en": "May you carry a mountain within and still find the road ahead."},
    {"zh": "愿你今日所遇，皆能化作助力。", "en": "May whatever meets you turn quietly into support."},
    {"zh": "愿你眉目清明，前路自开。", "en": "May clarity live in your gaze, and the path unfold by itself."},
    {"zh": "愿你行至今日，风来不乱，雨至不惊。", "en": "May wind not scatter you, nor rain unsettle your spirit."},
    {"zh": "愿你把握机缘，也守住本心。", "en": "May you seize the hour without losing your center."},
    {"zh": "愿你今日有所得，也有所安。", "en": "May today bring both gain and rest."},
    {"zh": "愿你所走每一步，都落在明处。", "en": "May every step land in a place of light."},
    {"zh": "愿你今日进退有度，张弛有序。", "en": "May your movement today know both measure and grace."},
    {"zh": "愿你与好运相认，与自己和解。", "en": "May luck know your name, and may you be at peace with yourself."},
    {"zh": "愿你今日不负时辰，不负心意。", "en": "May you honor both the hour and the truth within it."},
    {"zh": "愿你所求不远，所愿不空。", "en": "May what you seek draw near, and what you hope not be hollow."},
    {"zh": "愿你心有定海针，身有凌云志。", "en": "May your heart stay anchored while your spirit rises high."},
    {"zh": "愿你今日逢山开路，遇水得桥。", "en": "May mountains part for you, and waters offer a bridge."},
    {"zh": "愿你在今天的风里，站得稳，也走得远。", "en": "May today’s winds steady you even as they carry you farther."},
    {"zh": "愿你今日眼中有光，手中有事，心中有定。", "en": "May there be light in your eyes, purpose in your hands, and calm in your chest."},
    {"zh": "愿你所经之处，皆有回响。", "en": "May every place you pass through answer your presence."},
    {"zh": "愿你今日所遇之人，多真诚，少虚耗。", "en": "May sincerity meet you more often than waste."},
    {"zh": "愿你胸中有丘壑，眉间见从容。", "en": "May depth dwell in you, and ease rest upon your brow."},
    {"zh": "愿你今日福至，所谋皆顺。", "en": "May blessing arrive, and may your plans move with less resistance."},
    {"zh": "愿你把纷扰放下，把清明留下。", "en": "May you set down the noise and keep only the clear."},
    {"zh": "愿你今日如松立风前，如水行山下。", "en": "May you stand like pine in wind and move like water beneath the hills."},
    {"zh": "愿你有力可出，有路可行。", "en": "May strength be available and the way remain open."},
    {"zh": "愿你今日收获答案，也收获宁静。", "en": "May today bring you both an answer and a still heart."},
    {"zh": "愿你心灯不灭，步履不停。", "en": "May the lamp within you stay lit, and your feet keep faith."},
    {"zh": "愿你今日自在如云，坚定如石。", "en": "May you be cloud-soft and stone-steadfast at once."},
    {"zh": "愿你今日见天地之阔，也见自己之明。", "en": "May you glimpse the wide sky — and your own brightness within it."},
]
WALLPAPER_TEXTS = {
    "木": [
        {"zh": "风起青枝\n今日向上", "en": "Green branches wake\nRise with them"},
        {"zh": "种一寸新绿\n等山河回应", "en": "Plant one small green\nLet the hills reply"},
        {"zh": "向光而生\n不问迟早", "en": "Grow toward light\nNever mind the hour"},
        {"zh": "山林有信\n今日启程", "en": "The forest has spoken\nBegin today"},
        {"zh": "枝叶舒展\n心也舒展", "en": "Leaves opening wide\nLet your heart do the same"},
        {"zh": "把春意握紧\n往前一步", "en": "Hold the spring close\nTake one clear step"},
        {"zh": "让生长发生\n让犹豫退场", "en": "Let growth take shape\nLet hesitation leave"},
        {"zh": "今日宜发芽\n也宜发声", "en": "A day to sprout\nA day to speak"},
        {"zh": "东风入怀\n万事可栽", "en": "East wind in your chest\nEverything can be planted"},
        {"zh": "木意正盛\n把路走宽", "en": "Wood rises full\nWiden the road"},
        {"zh": "新枝向天\n你也向前", "en": "New branches reach upward\nSo can you"},
        {"zh": "把今天种下\n把未来等来", "en": "Plant today well\nLet tomorrow arrive"},
        {"zh": "青山未老\n此心先行", "en": "The green hills endure\nGo with your heart first"},
        {"zh": "一念生春\n一步见光", "en": "One thought becomes spring\nOne step meets light"},
        {"zh": "风过林梢\n你正当时", "en": "Wind moves the trees\nYour time is now"},
    ],
    "火": [
        {"zh": "心有烈焰\n步步生光", "en": "Flame in your chest\nLight in each step"},
        {"zh": "把握火势\n向前而行", "en": "Catch the fire well\nMove forward cleanly"},
        {"zh": "今日燃起\n不再迟疑", "en": "Burn into motion\nLeave doubt behind"},
        {"zh": "让热望成真\n让行动落地", "en": "Let desire take form\nLet action touch earth"},
        {"zh": "日升南方\n你自明亮", "en": "The south grows bright\nSo do you"},
        {"zh": "向光而去\n向成而行", "en": "Walk toward brightness\nWalk toward completion"},
        {"zh": "以火为旗\n今日破局", "en": "Raise fire like a banner\nBreak the old pattern"},
        {"zh": "心灯点亮\n诸事可行", "en": "Light the inner lamp\nThe way opens"},
        {"zh": "敢于发光\n也敢定局", "en": "Dare to shine\nDare to decide"},
        {"zh": "火在胸中\n路在脚下", "en": "Fire in the chest\nRoad beneath the feet"},
        {"zh": "今日见光\n今日见成", "en": "See the light today\nSee the result today"},
        {"zh": "炽而不乱\n勇而有度", "en": "Burn without chaos\nBe brave with measure"},
        {"zh": "把热望举高\n把犹疑放下", "en": "Lift your longing higher\nLay your doubt down"},
        {"zh": "午阳正盛\n宜成大事", "en": "Noon sun at full height\nA day for larger things"},
        {"zh": "今日有火\n亦有方向", "en": "There is fire today\nAnd there is direction"},
    ],
    "土": [
        {"zh": "先把脚站稳\n再看山多高", "en": "Stand your ground first\nThen measure the mountain"},
        {"zh": "厚土无声\n万事可承", "en": "Deep earth speaks softly\nYet carries all things"},
        {"zh": "稳住此刻\n好运自来", "en": "Steady this moment\nFortune will come near"},
        {"zh": "山不必急\n路自会成", "en": "The mountain does not hurry\nThe road still appears"},
        {"zh": "今日宜扎根\n也宜安心", "en": "Root yourself today\nLet peace settle in"},
        {"zh": "把地基筑实\n把日子过稳", "en": "Build the foundation deep\nLive the day with steadiness"},
        {"zh": "土厚则安\n心定则成", "en": "Thick earth brings calm\nA settled heart brings results"},
        {"zh": "一步一个印\n自有回声", "en": "One footprint at a time\nThe echo will come"},
        {"zh": "慢一点\n更有力量", "en": "Go a little slower\nGrow a deeper strength"},
        {"zh": "把杂乱归位\n把心收回来", "en": "Put disorder in its place\nCall your heart back home"},
        {"zh": "今日向内稳\n明日向外开", "en": "Settle inward today\nOpen outward tomorrow"},
        {"zh": "厚积如山\n静待风起", "en": "Gather like a mountain\nWait for the wind wisely"},
        {"zh": "稳住节奏\n稳住自己", "en": "Steady the rhythm\nSteady yourself"},
        {"zh": "地气入心\n诸事可定", "en": "Earth enters the heart\nMany things can settle"},
        {"zh": "山河在下\n你自从容", "en": "Mountains beneath you\nComposure within you"},
    ],
    "金": [
        {"zh": "做清醒的人\n走清楚的路", "en": "Be clear in spirit\nWalk the clear road"},
        {"zh": "删繁就简\n直指要处", "en": "Cut down the excess\nTouch the essential"},
        {"zh": "今日宜决断\n不宜拖延", "en": "A day for decision\nNot for delay"},
        {"zh": "金风一起\n边界自明", "en": "When metal wind rises\nBoundaries become clear"},
        {"zh": "把杂音关掉\n听内心发令", "en": "Silence the static\nHear your inner command"},
        {"zh": "锋芒有度\n答案自现", "en": "Keep the edge measured\nThe answer will appear"},
        {"zh": "今日当取舍\n当定轻重", "en": "Choose what stays\nChoose what matters"},
        {"zh": "让标准发光\n让犹豫退场", "en": "Let your standards shine\nLet doubt step aside"},
        {"zh": "清风如刃\n斩断内耗", "en": "A clean wind like a blade\nCuts through inner waste"},
        {"zh": "留最重要的\n做最准确的", "en": "Keep what matters most\nDo what lands true"},
        {"zh": "把复杂剖开\n把方向看清", "en": "Open the complex thing\nSee the direction clearly"},
        {"zh": "金气清明\n不必回头", "en": "Metal air is clear\nNo need to turn back"},
        {"zh": "立住原则\n也立住自己", "en": "Stand in your principle\nStand in yourself"},
        {"zh": "今日宜定局\n不宜含糊", "en": "A day to settle things\nNot to blur them"},
        {"zh": "锋不必露\n势自可成", "en": "The blade need not show\nThe force will still form"},
    ],
    "水": [
        {"zh": "顺流而行\n自有答案", "en": "Follow the current\nThe answer will surface"},
        {"zh": "今日如水\n柔中见力", "en": "Be water today\nSoft, and still powerful"},
        {"zh": "慢一点看清\n再向前去", "en": "Look slowly, deeply\nThen move ahead"},
        {"zh": "云水相照\n心自有岸", "en": "Cloud and water mirror\nYour heart knows the shore"},
        {"zh": "不争一时\n但求到达", "en": "Do not rush the hour\nReach what is yours"},
        {"zh": "让情绪流走\n让清明留下", "en": "Let feeling flow through\nKeep what is clear"},
        {"zh": "今日宜观势\n再定方向", "en": "Read the current first\nThen choose direction"},
        {"zh": "水到深处\n自见天地", "en": "At the deepest water\nThe wide world appears"},
        {"zh": "先让心静\n再让路明", "en": "Still the heart first\nThen the path brightens"},
        {"zh": "今日随势\n不必硬推", "en": "Move with the tide today\nDo not force the river"},
        {"zh": "潮来有时\n你亦有时", "en": "The tide has its hour\nSo do you"},
        {"zh": "向宽处走\n向深处想", "en": "Walk toward openness\nThink toward depth"},
        {"zh": "把锋芒藏住\n把力量留长", "en": "Hide the sharp edge\nKeep the strength enduring"},
        {"zh": "水光在前\n步履自轻", "en": "Waterlight before you\nLet your steps grow light"},
        {"zh": "今日宜回旋\n也宜抵达", "en": "Curve if you must today\nBut still arrive"},
    ],
}


def _ganzhi_for_day(target_date: date_type) -> tuple[str, str]:
    base_date = date_type(1984, 2, 2)
    delta_days = (target_date - base_date).days
    return TIANGAN[delta_days % 10], DIZHI[delta_days % 12]


def _element_relation(day_master_element: str, day_element: str) -> str:
    if day_master_element == day_element:
        return "同我"
    if GENERATES[day_element] == day_master_element:
        return "生我"
    if GENERATES[day_master_element] == day_element:
        return "我生"
    if CONTROLS[day_master_element] == day_element:
        return "我克"
    return "克我"


def _pick(options: list[Any], seed_text: str) -> Any:
    rng = Random(int(sha256(seed_text.encode("utf-8")).hexdigest(), 16))
    return options[rng.randrange(len(options))]


def _localize(entry: Any, lang: str) -> Any:
    if isinstance(entry, dict) and "zh" in entry and "en" in entry:
        return entry["en"] if lang == "en" else entry["zh"]
    return entry


def _branch_bonus(branch: str) -> int:
    if branch in {"寅", "卯", "辰", "巳", "午"}:
        return 1
    if branch in {"申", "酉", "亥"}:
        return 0
    return -1


def _fortune_level(relation: str, branch: str) -> str:
    levels = ["凶", "小凶", "平", "小吉", "中吉", "上吉", "大吉"]
    base_map = {"生我": 5, "我克": 4, "克我": 1, "我生": 2, "同我": 4}
    index = max(0, min(6, base_map[relation] + _branch_bonus(branch)))
    return levels[index]


def _general_fortune(day_element: str, day_ganzhi: str, branch: str, date_str: str, lang: str) -> tuple[str, str, str]:
    general_message = _localize(_pick(GENERAL_MESSAGES[day_element], f"general:{date_str}:{day_ganzhi}"), lang)
    wallpaper_text = _localize(_pick(WALLPAPER_TEXTS[day_element], f"wallpaper:{date_str}:{day_ganzhi}"), lang)
    blessing = _localize(_pick(BLESSINGS, f"blessing:{date_str}:{branch}"), lang)
    return general_message, wallpaper_text, blessing


def generate_daily_fortune(date, user_bazi=None, lang="zh") -> dict:
    resolved_lang = "en" if lang == "en" else "zh"
    target_date = date if isinstance(date, date_type) else datetime.strptime(str(date), "%Y-%m-%d").date()
    day_stem, day_branch = _ganzhi_for_day(target_date)
    day_ganzhi = f"{day_stem}{day_branch}"
    day_element = STEM_WUXING[day_stem]
    general_message, wallpaper_text, blessing = _general_fortune(
        day_element, day_ganzhi, day_branch, target_date.isoformat(), resolved_lang
    )

    result = {
        "date": target_date.isoformat(),
        "day_ganzhi": day_ganzhi,
        "day_wuxing": day_element,
        "fortune_level": "小吉" if _branch_bonus(day_branch) >= 0 else "平",
        "lucky_color": _localize(LUCKY_COLORS[day_element], resolved_lang),
        "lucky_direction": _localize(LUCKY_DIRECTIONS[day_element], resolved_lang),
        "lucky_number": LUCKY_NUMBERS[day_element],
        "general_message": general_message,
        "wallpaper_text": wallpaper_text,
        "blessing": blessing,
    }

    if isinstance(user_bazi, dict):
        day_master = (
            user_bazi.get("day_master")
            or user_bazi.get("day_master_stem")
            or user_bazi.get("day", {}).get("heavenly_stem")
            or user_bazi.get("four_pillars", {}).get("day", {}).get("heavenly_stem")
        )
        if day_master in STEM_WUXING:
            day_master_element = STEM_WUXING[day_master]
            relation = _element_relation(day_master_element, day_element)
            result["fortune_level"] = _fortune_level(relation, day_branch)
            result["personal_message"] = _localize(
                _pick(PERSONAL_MESSAGES[relation], f"personal:{target_date.isoformat()}:{day_master}:{day_ganzhi}"),
                resolved_lang,
            ).format(day_master=day_master, day_ganzhi=day_ganzhi)

    return result
