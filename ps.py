import streamlit as st
import google.generativeai as genai
from PIL import Image
import docx
import PyPDF2
import io
import os
import time
import random
from datetime import datetime

# ==========================================
# 0. 自动版本号生成逻辑
# ==========================================
def get_app_version():
    try:
        timestamp = os.path.getmtime(__file__)
        dt = datetime.fromtimestamp(timestamp)
        # 格式：v13.19.月日.时分
        build_ver = dt.strftime('%m%d.%H%M')
        return f"v13.19.{build_ver}", dt.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return "v13.19.Dev", "Unknown"

current_version, last_updated_time = get_app_version()

# ==========================================
# 1. 页面基础配置 & 终极 CSS 对齐
# ==========================================
st.set_page_config(page_title=f"留学文书工具 {current_version}", layout="wide")

# --- CSS Hack: 强制底部边框对齐 ---
st.markdown("""
<style>
    /* 1. 水平容器：强制子元素高度拉伸 */
    div[data-testid="stHorizontalBlock"] {
        align-items: stretch;
        height: auto;
    }

    /* 2. 列容器：设置为 Flex 布局，并强制高度 100% */
    div[data-testid="column"] {
        display: flex;
        flex-direction: column;
        height: 100%;
    }

    /* 3. 卡片容器 (带边框的)：强制占满剩余空间，确保高度一致 */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        flex-grow: 1;
        display: flex;
        flex-direction: column;
        height: 100%;
        min-height: 100%; /* 核心：强制最小高度也填满 */
    }
    
    /* 4. 内部内容容器：允许内容自然填充 */
    div[data-testid="stVerticalBlockBorderWrapper"] > div {
        flex-grow: 1;
    }

    /* 5. 紧凑化 Label 间距 */
    .stMarkdown p {
        margin-bottom: 0px;
    }
</style>
""", unsafe_allow_html=True)

# 初始化 Session State
if 'generated_sections' not in st.session_state:
    st.session_state['generated_sections'] = {}
if 'motivation_trends' not in st.session_state:
    st.session_state['motivation_trends'] = ""
if 'translated_sections' not in st.session_state:
    st.session_state['translated_sections'] = {}
if 'chat_histories' not in st.session_state:
    st.session_state['chat_histories'] = {} 

st.title(f"留学文书辅助写作工具 {current_version}")
st.markdown("---")

# ==========================================
# 2. 核心文案库 (幽默加载 + 情绪价值)
# ==========================================

# --- A. 幽默加载文案库 ---
FUNNY_LOADING_MESSAGES = [
    "☕️ 正在煮咖啡，顺便思考一下人生...",
    "🧠 正在和 Google 总部的服务器进行脑电波对接...",
    "🚀 正在以此生最快的速度翻阅整个互联网...",
    "🐢 别急，AI 也是需要喘口气的...",
    "🔥 为了这个问题，显卡正在微微发烫...",
    "🧙‍♂️ 正在召唤数据魔法，请勿打扰...",
    "🧐 正在假装很深沉地思考...",
    "💾 正在从赛博空间的角落里打捞数据...",
    "✨ 灵感正在加载中，进度 99%...",
    "🤖 正在学习如何像人类一样说话...",
    "📚 正在快速阅读 1000 本相关书籍...",
    "🪐 正在向外星文明发送求助信号...",
    "🍕 正在吃一口虚拟披萨补充能量...",
    "🎻 正在为您演奏一首数据交响曲...",
    "🏃‍♂️ 正在数据的海洋里狂奔...",
    "🧩 正在拼凑逻辑的碎片...",
    "🔋 正在给神经元充电...",
    "📡 正在校准卫星信号...",
    "🧹 正在清理思维里的杂草...",
    "🎲 正在掷骰子决定用哪个词（开玩笑的）..."
]

# --- B. 情绪价值文案库 (Daily Vibe) ---
DAILY_VIBES = [
    "🌟 Your story matters. \n你的故事值得被世界听见。",
    "☕️ Coffee in hand, confidence in mind. \n手中有咖啡，心中有梦想。",
    "🚀 One step closer to your dream school. \n每一个单词，都是通往梦校的阶梯。",
    "🌈 Trust the process. \n相信过程，结果自会发生。",
    "✨ Small steps, big dreams. \n今天的努力，是未来的伏笔。",
    "🎓 You are capable of amazing things. \n你比想象中更强大。",
    "💡 Shine bright. \n去发光吧，不仅是为了被看见。",
    "🛤️ The journey is the reward. \n申请季本身就是一场蜕变。",
    "💪 Keep going, you got this. \n坚持住，Offer 正在路上。",
    "🌍 The world is waiting for you. \n世界很大，等你探索。",
    "✒️ Write your own future. \n提笔，即是未来。",
    "🦁 Be bold, be you. \n勇敢做自己，这最动人。"
]

def get_random_loading_msg():
    return random.choice(FUNNY_LOADING_MESSAGES)

def stream_vibe_text():
    """生成器函数，用于产生打字机效果"""
    quote = random.choice(DAILY_VIBES)
    for word in quote.split(): 
        yield word + " "
        time.sleep(0.05) # 控制打字速度

# ==========================================
# 3. 系统设置 (侧边栏 - 含情绪价值模块)
# ==========================================
with st.sidebar:
    # --- 🌟 情绪价值模块 (Daily Vibe) ---
    st.markdown("### ✨ Daily Vibe")
    with st.container(border=True):
        st.write_stream(stream_vibe_text)
    
    st.markdown("---")
    
    st.header("系统设置")
    
    api_key = st.text_input("🔑 请输入 Google API Key", type="password", help="请在 Google AI Studio 申请 Key")
    
    if not api_key:
        st.warning("⚠️ 请输入 Key")
    else:
        st.success("✅ Key 已就绪")
    
    model_name = st.selectbox("选择模型", ["gemini-3-pro-preview"], index=0)
    
    st.markdown("---")
    st.markdown("### 关于")
    st.info(f"**当前版本:** {current_version}")
    st.caption(f"**最后更新:** {last_updated_time}")
    st.caption("**Update:** 新增英式/美式拼写切换功能")

# ==========================================
# 4. 核心函数
# ==========================================
def read_word_file(file):
    try:
        doc = docx.Document(file)
        full_text = []
        for para in doc.paragraphs:
            full_text.append(para.text)
        return '\n'.join(full_text)
    except Exception as e:
        return f"Error reading Word file: {e}"

def read_pdf_text(file):
    try:
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        return f"Error reading PDF file: {e}"

def get_gemini_response(prompt, media_content=None, text_context=None):
    if not api_key:
        return "Error: 请先在左侧侧边栏输入 API Key"
        
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    
    content = []
    content.append(prompt)
    
    if text_context:
        content.append(f"\n【参考文档/背景信息 (简历或素材表)】:\n{text_context}")
    
    if media_content:
        if isinstance(media_content, list):
            content.extend(media_content)
        else:
            content.append(media_content)
        
    try:
        response = model.generate_content(content)
        return response.text
    except Exception as e:
        return f"Error: {str(e)}"

# ==========================================
# 5. 界面：信息采集 (UI 终极对齐版)
# ==========================================
st.header("1. 信息采集与素材上传")

col_student, col_counselor, col_target = st.columns(3)

# --- 第一栏：学生提供信息 ---
with col_student:
    with st.container(border=True):
        st.markdown("### 学生提供信息")
        st.caption("上传简历、素材表与成绩单")
        
        uploaded_material = st.file_uploader("📄 文书素材/简历 (Word/PDF)", type=['docx', 'pdf'])
        uploaded_transcript = st.file_uploader("🎓 成绩单 (截图/PDF)", type=['png', 'jpg', 'jpeg', 'pdf'])

# --- 第二栏：顾问指导意见 ---
with col_counselor:
    with st.container(border=True):
        st.markdown("### 顾问指导意见")
        st.caption("设定文书的整体策略与调性")
        
        counselor_strategy = st.text_area(
            "💡 写作策略/人设强调", 
            height=280, 
            placeholder="例如：\n1. 强调量化背景\n2. 解释GPA劣势\n3. 突出某段实习的领导力..."
        )

# --- 第三栏：目标专业信息 ---
with col_target:
    with st.container(border=True):
        st.markdown("### 目标专业信息")
        st.caption("输入目标学校与课程设置")
        
        target_school_name = st.text_input("🏛️ 目标学校 & 专业", placeholder="例如：UCL - MSc Business Analytics")
        
        st.markdown("**📖 课程设置 (Curriculum)**") 
        
        tab_text, tab_img = st.tabs(["文本粘贴", "图片上传"])
        
        with tab_text:
            target_curriculum_text = st.text_area("粘贴课程列表", height=140, placeholder="Core Modules: ...", label_visibility="collapsed")
        
        with tab_img:
            uploaded_curriculum_images = st.file_uploader("上传课程截图", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True, label_visibility="collapsed")

# 读取素材文本
student_background_text = ""
if uploaded_material:
    if uploaded_material.name.endswith('.docx'):
        student_background_text = read_word_file(uploaded_material)
    elif uploaded_material.name.endswith('.pdf'):
        student_background_text = read_pdf_text(uploaded_material)

# ==========================================
# 6. 界面：写作设定 (新增拼写选项)
# ==========================================
st.markdown("---")
st.header("2. 写作设定") # 已重命名

modules = {
    "Motivation": "申请动机",
    "Academic": "本科学习经历",
    "Internship": "实习/工作经历",
    "Why_School": "Why School",
    "Career_Goal": "职业规划"
}

# 使用列布局来放置 模块选择 和 拼写选择
col_modules, col_style = st.columns([3, 1])

with col_modules:
    selected_modules = st.multiselect("选择模块：", list(modules.keys()), format_func=lambda x: modules[x], default=list(modules.keys()))

with col_style:
    # 新增：拼写风格选择
    spelling_preference = st.radio(
        "🔤 拼写偏好 (Spelling)",
        ["🇬🇧 英式 (British)", "🇺🇸 美式 (American)"],
        help="翻译时将严格遵循所选的拼写习惯 (如 colour vs color)"
    )

# ==========================================
# 7. 核心逻辑：生成 Prompt
# ==========================================
st.markdown("---")
st.header("3. 一键点击创作")

CLEAN_OUTPUT_RULES = """
【🚨 绝对输出规则】
1. 只输出正文内容本身。
2. 严禁包含开场白、结尾语或结构说明。
3. 严禁使用 Markdown 格式（如加粗、列表符号、标题符号）。
4. 输出必须是纯文本。
5. 必须写成一个完整的、连贯的中文自然段。
"""

# 注意：这里只定义基础规则，拼写规则会在点击翻译按钮时动态注入
TRANSLATION_RULES_BASE = """
【Translation Task】
Translate the provided Chinese text into a professional, human-sounding Personal Statement paragraph.

【🚨 CRITICAL ANTI-AI STYLE GUIDE】
1. **KILL THE "AI SENTENCE PATTERN"**: 
   - **ABSOLUTELY FORBIDDEN**: The pattern "I did X, **thereby/thus/enabling** me to do Y." 
   - **SOLUTION**: Split into two sentences or use active verbs.

2. **SEMICOLONS (;) FOR FLOW**:
   - **MANDATORY**: When a sentence is grammatically complete but the thought is not finished (and leads directly into the next point), use a **semicolon (;)** to connect them.
   - *Example*: "The model failed initially; this failure forced me to re-evaluate the parameters."

3. **ADVERB CONTROL (Nuanced)**:
   - **STRICTLY PROHIBITED**: Adverbs placed immediately before verbs or adjectives to intensify them (e.g., "deeply analyze", "perfectly align").
   - **ALLOWED**: "Robust" and "scalable" are permitted.

4. **VOCABULARY PURGE**: 
   - Avoid "delve into", "pivotal", "tapestry". Use precise, simple words.

【🚫 BANNED WORDS LIST (Strictly Prohibited)】
[Verbs]: delve into, uncover, reveal, recognize, master, refine, cultivate, address, bridge, spearhead, pioneer, align with, stems from, underscore, highlight
[Adjectives/Adverbs]: instrumental, pivotal, seamless, systematically, rigorously, profoundly, deeply, acutely, keenly, comprehensively, perfectly, meticulously
[Nouns]: paradigm, trajectory, aspirations, vision, landscape, tapestry, realm, foundation
[Connectors]: thereby, thus (when used with -ing), in turn
[Phrases]: "not only... but also", "Building on this", "rich tapestry", "testament to", "a wide array of"

【Formatting】
1. Output as ONE single paragraph.
2. Output the ENTIRE text in **Bold**.
3. No Markdown headers.
"""

if st.button("开始生成初稿", type="primary"):
    if not api_key:
        st.error("❌ 请先在左侧侧边栏输入有效的 Google API Key")
        st.stop()

    has_curriculum = target_curriculum_text or uploaded_curriculum_images
    
    if not uploaded_material or not uploaded_transcript or not has_curriculum:
        st.error("请确保：文书素材/简历、成绩单、目标课程信息 均已提供。")
        st.stop()
    
    # 准备媒体
    transcript_content = []
    if uploaded_transcript.type == "application/pdf":
        transcript_content.append({
            "mime_type": "application/pdf",
            "data": uploaded_transcript.getvalue()
        })
    else:
        transcript_content.append(Image.open(uploaded_transcript))

    curriculum_imgs = []
    if uploaded_curriculum_images:
        for img_file in uploaded_curriculum_images:
            curriculum_imgs.append(Image.open(img_file))
    
    progress_bar = st.progress(0)
    total_steps = len(selected_modules)
    current_step = 0

    # --- Prompt 定义 ---
    prompt_motivation = f"""
    【任务】撰写 Personal Statement 的 "申请动机" 部分。
    【步骤 1：深度调研】
    请先分析 {target_school_name} 所在领域的最新行业热点或学术趋势（列出 2-3 个）。
    **必须提供具体信息源**：
    - 具体的论文标题 (Title & Year)
    - 知名咨询机构报告名称 (如 McKinsey, Deloitte, Gartner)
    - 权威科技/商业新闻源 (如 TechCrunch, Bloomberg, Nature)
    - 简述该趋势与学生背景的关联。
    【步骤 2：撰写正文】
    基于上述趋势和学生素材，撰写一段中文申请动机。
    逻辑：学生过往经历 -> 观察到的行业痛点/趋势 -> 产生深造需求。
    【🚨 严格输出格式】
    请严格按照下方分隔符输出，不要包含其他内容：
    [TRENDS_START]
    (在此处列出调研的趋势和具体来源链接/标题)
    [TRENDS_END]
    [DRAFT_START]
    (在此处撰写正文段落，纯文本，无Markdown)
    [DRAFT_END]
    """

    prompt_career = f"""
    【任务】撰写 "职业规划" (Career Goals) 部分。
    【输入背景】
    - 目标专业: {target_school_name}
    - 顾问思路: {counselor_strategy}
    【内容要求】
    1. 规划硕士毕业后的路径（应届生视角）。
    2. **必须包含**：具体的公司名字、具体的职位名称。
    3. 将工作内容和未来继续学习方向融合在一段话中。
    {CLEAN_OUTPUT_RULES}
    """

    prompt_academic = f"""
    【任务】撰写 "本科学习经历" (Academic Background) 部分。
    【输入背景】
    - 目标专业: {target_school_name}
    - 核心依据 (成绩单): 见附带文件 (PDF或图片)
    - 辅助参考 (学生素材/简历): 见附带文本
    【核心原则：深度 > 数量】
    不要罗列课程名。只精选 **2-3 门** 与目标专业最强相关的核心课程进行深度描写。
    【内容要求 - 必须包含细节】
    1. **核心概念植入**：在描述每门课时，必须提及该课程具体的**核心概念、模型、算法或理论名称**。
    2. **学术真实感**：结合学生素材，简述是如何理解或应用这些概念的。
    3. **逻辑升华**：说明这些具体的知识点如何为你攻读 {target_school_name} 打下了坚实的学术基础。
    4. **禁止**：禁止写成课程清单（List），必须是连贯的学术反思叙述。
    {CLEAN_OUTPUT_RULES}
    """

    prompt_whyschool = f"""
    【任务】撰写 "Why School" 部分。
    【输入背景】
    - 目标学校: {target_school_name}
    - 顾问思路: {counselor_strategy}
    {f'【目标课程文本列表】:{target_curriculum_text}' if target_curriculum_text else ''}
    - 课程图片信息: 见附带图片
    【内容要求】
    1. 综合分析提供的文本列表和图片中的课程信息。
    2. 从中挑选 3-4 门与学生背景或规划最相关的特定课程。
    3. 说明这些课程（提及课名或概念）为何吸引学生及有何帮助。
    4. 语气朴素专业，议论为主。
    {CLEAN_OUTPUT_RULES}
    """

    prompt_internship = f"""
    【任务】撰写 "实习/工作经历" (Professional Experience) 部分。
    【输入背景】
    - 学生素材: 见附带文本
    - 目标专业: {target_school_name}
    【内容要求】
    1. 筛选最相关经历，按时间顺序逻辑串联。
    2. 结构：背景 -> 职责 -> 技能 -> 动机。
    3. 拒绝流水账，要有逻辑梳理和反思。
    {CLEAN_OUTPUT_RULES}
    """

    prompts_map = {
        "Motivation": prompt_motivation,
        "Career_Goal": prompt_career,
        "Academic": prompt_academic,
        "Why_School": prompt_whyschool,
        "Internship": prompt_internship
    }

    for module in selected_modules:
        current_step += 1
        st.toast(f"正在撰写: {modules[module]} ...")
        
        current_media = None
        if module == "Academic":
            current_media = transcript_content
        elif module == "Why_School":
            current_media = curriculum_imgs
        
        res = get_gemini_response(prompts_map[module], media_content=current_media, text_context=student_background_text)
        
        final_text = res.strip()
        
        if module == "Motivation":
            try:
                if "[TRENDS_START]" in res and "[DRAFT_START]" in res:
                    trends_part = res.split("[TRENDS_START]")[1].split("[TRENDS_END]")[0].strip()
                    draft_part = res.split("[DRAFT_START]")[1].split("[DRAFT_END]")[0].strip()
                    st.session_state['motivation_trends'] = trends_part
                    final_text = draft_part
                else:
                    final_text = res
            except:
                final_text = res

        st.session_state['generated_sections'][module] = final_text
        
        if f"text_{module}" in st.session_state:
            st.session_state[f"text_{module}"] = final_text
        
        if module in st.session_state['translated_sections']:
            del st.session_state['translated_sections'][module]
            
        progress_bar.progress(current_step / total_steps)

    st.success("初稿生成完毕！")

# ==========================================
# 8. 界面：反馈、修改与翻译 (交互升级 + 灵感助手)
# ==========================================
if st.session_state.get('generated_sections'):
    st.markdown("---")
    st.header("4. 审阅、精修与翻译")
    st.info("👇 左侧为中文初稿，支持【局部精修】；右侧可选【英文翻译】或【灵感助手】。")

    display_order = ["Motivation", "Academic", "Internship", "Why_School", "Career_Goal"]
    
    for module in display_order:
        if module in st.session_state['generated_sections']:
            with st.container():
                st.subheader(f"{modules[module]}")
                
                if module == "Motivation" and st.session_state.get('motivation_trends'):
                    with st.expander("📚 点击查看：行业趋势调研与参考源 (Reference)", expanded=True):
                        st.info(st.session_state['motivation_trends'])
                
                c1, c2 = st.columns([1, 1])
                
                # --- 左侧：中文编辑与精修 ---
                with c1:
                    st.markdown("**中文草稿 (可编辑)**")
                    
                    if f"text_{module}" not in st.session_state:
                        st.session_state[f"text_{module}"] = st.session_state['generated_sections'][module]
                    
                    current_content = st.text_area(
                        f"中文内容 - {module}", 
                        key=f"text_{module}",
                        height=350
                    )
                    st.session_state['generated_sections'][module] = current_content

                    # --- 局部精修面板 ---
                    with st.expander("🛠️ 修改工具箱", expanded=False):
                        tab_global, tab_local = st.tabs(["全局重写", "🔍 局部/细节精修"])
                        
                        with tab_global:
                            fb_global = st.text_input(f"整体修改意见", key=f"fb_glob_{module}")
                            if st.button("🔄 全局重写", key=f"btn_glob_{module}"):
                                if not fb_global:
                                    st.warning("请输入修改意见")
                                else:
                                    with st.spinner("正在全局重写..."):
                                        revise_prompt = f"""
                                        【任务】根据反馈重写整段内容。
                                        【原段落】{current_content}
                                        【用户反馈】{fb_global}
                                        {CLEAN_OUTPUT_RULES}
                                        """
                                        revised_text = get_gemini_response(revise_prompt)
                                        st.session_state[f"text_{module}"] = revised_text.strip()
                                        st.session_state['generated_sections'][module] = revised_text.strip()
                                        if module in st.session_state['translated_sections']:
                                            del st.session_state['translated_sections'][module]
                                        st.rerun()

                        with tab_local:
                            st.caption("复制上方你想改的那句话，粘贴到下方，然后写要求。")
                            col_target_text, col_instruction = st.columns(2)
                            with col_target_text:
                                target_segment = st.text_input("🎯 粘贴原文片段", key=f"target_{module}")
                            with col_instruction:
                                local_instruction = st.text_input("✍️ 怎么改？", key=f"instr_{module}")
                            
                            if st.button("✨ 仅修改选中部分", key=f"btn_loc_{module}"):
                                if not target_segment or not local_instruction:
                                    st.warning("请填写原文片段和修改意见")
                                else:
                                    with st.spinner("正在进行局部精修..."):
                                        partial_revise_prompt = f"""
                                        【任务】对文书段落进行局部精修。
                                        【完整原文】{current_content}
                                        【用户锁定的原文片段】"{target_segment}"
                                        【用户的修改批注】"{local_instruction}"
                                        【执行步骤】
                                        1. 在完整原文中定位该片段。
                                        2. 仅针对该片段应用用户的修改意见。
                                        3. 保持段落其他部分不变。
                                        4. 输出修改后的完整段落。
                                        {CLEAN_OUTPUT_RULES}
                                        """
                                        revised_text = get_gemini_response(partial_revise_prompt)
                                        st.session_state[f"text_{module}"] = revised_text.strip()
                                        st.session_state['generated_sections'][module] = revised_text.strip()
                                        if module in st.session_state['translated_sections']:
                                            del st.session_state['translated_sections'][module]
                                        st.rerun()

                # --- 右侧：翻译 与 灵感助手 (Tabs) ---
                with c2:
                    tab_trans, tab_chat = st.tabs(["🇺🇸 英文翻译", "🤖 灵感助手 (Chat)"])
                    
                    # Tab 1: 翻译
                    with tab_trans:
                        st.markdown("**英文翻译结果**")
                        if st.button(f"🚀 翻译此段", key=f"trans_btn_{module}"):
                            if not api_key:
                                st.error("需要 API Key")
                            else:
                                with st.spinner("Translating..."):
                                    # --- 动态注入拼写规则 ---
                                    spelling_instruction = ""
                                    if "British" in spelling_preference:
                                        spelling_instruction = "\n【SPELLING RULE】: STRICTLY use British English spelling (e.g., colour, analyse, programme, centre, organisation)."
                                    else:
                                        spelling_instruction = "\n【SPELLING RULE】: STRICTLY use American English spelling (e.g., color, analyze, program, center, organization)."
                                    
                                    content_to_translate = st.session_state[f"text_{module}"]
                                    
                                    # 组合完整 Prompt
                                    full_trans_prompt = f"{TRANSLATION_RULES_BASE}\n{spelling_instruction}\n【Input Text】:\n{content_to_translate}"
                                    
                                    trans_res = get_gemini_response(full_trans_prompt)
                                    st.session_state['translated_sections'][module] = trans_res.strip()
                        
                        if module in st.session_state['translated_sections']:
                            st.markdown(st.session_state['translated_sections'][module])
                            st.caption("💡 提示：如果修改了左侧中文，请重新点击翻译按钮。")
                        else:
                            st.info("👈 满意左侧中文稿后，点击上方按钮生成翻译。")

                    # Tab 2: 灵感助手 (Chat)
                    with tab_chat:
                        st.caption("🤔 遇到卡顿？在这里查资料、问同义词或寻找灵感。")
                        
                        if module not in st.session_state['chat_histories']:
                            st.session_state['chat_histories'][module] = []
                        
                        chat_container = st.container(height=250)
                        with chat_container:
                            for msg in st.session_state['chat_histories'][module]:
                                with st.chat_message(msg["role"]):
                                    st.markdown(msg["content"])
                        
                        user_query = st.text_input(f"向助手提问 ({modules[module]})", key=f"chat_in_{module}")
                        
                        if st.button("发送", key=f"chat_send_{module}"):
                            if not user_query:
                                st.warning("请输入问题")
                            elif not api_key:
                                st.error("需要 API Key")
                            else:
                                st.session_state['chat_histories'][module].append({"role": "user", "content": user_query})
                                
                                # 获取随机文案
                                loading_msg = get_random_loading_msg()
                                
                                # 强制 Spinner 包裹 API 调用
                                with st.spinner(loading_msg):
                                    chat_prompt = f"""
                                    你是一个专业的留学文书助手。用户正在撰写 '{modules[module]}' 部分。
                                    用户的问题是：{user_query}
                                    请提供简短、专业且有帮助的回答。
                                    """
                                    ai_reply = get_gemini_response(chat_prompt)
                                    
                                    st.session_state['chat_histories'][module].append({"role": "assistant", "content": ai_reply})
                                    st.rerun()

    # ==========================================
    # 9. 导出
    # ==========================================
    st.markdown("---")
    st.header("5. 最终导出")
    
    full_text = ""
    for module in display_order:
        if module in st.session_state.get('translated_sections', {}):
            full_text += f"--- {modules[module]} (English) ---\n"
            clean_en = st.session_state['translated_sections'][module].replace("**", "")
            full_text += clean_en + "\n\n"
        elif module in st.session_state['generated_sections']:
            full_text += f"--- {modules[module]} (中文草稿) ---\n"
            full_text += st.session_state['generated_sections'][module] + "\n\n"
            
    st.download_button(
        label="📥 下载文书 (.txt)",
        data=full_text,
        file_name=f"PS_{target_school_name}_{current_version}.txt",
        mime="text/plain",
        type="primary"
    )
