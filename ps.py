import streamlit as st
import google.generativeai as genai
from PIL import Image
import docx
import PyPDF2
import io
import os
import time
from datetime import datetime

# ==========================================
# 0. 自动版本号生成逻辑
# ==========================================
def get_app_version():
    try:
        timestamp = os.path.getmtime(__file__)
        dt = datetime.fromtimestamp(timestamp)
        # 格式：v13.10.月日.时分
        build_ver = dt.strftime('%m%d.%H%M')
        return f"v13.10.{build_ver}", dt.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return "v13.10.Dev", "Unknown"

current_version, last_updated_time = get_app_version()

# ==========================================
# 1. 页面基础配置
# ==========================================
st.set_page_config(page_title=f"留学文书工具 {current_version}", layout="wide")

if 'generated_sections' not in st.session_state:
    st.session_state['generated_sections'] = {}
if 'motivation_trends' not in st.session_state:
    st.session_state['motivation_trends'] = ""
if 'translated_sections' not in st.session_state:
    st.session_state['translated_sections'] = {}
if 'step' not in st.session_state:
    st.session_state['step'] = 1

st.title(f"留学文书辅助写作工具 {current_version}")
st.markdown("---")

# ==========================================
# 2. 系统设置
# ==========================================
with st.sidebar:
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
    st.caption("**Update:** UI 重构：三栏式信息采集")

# ==========================================
# 3. 核心函数
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
# 4. 界面：信息采集 (UI 重构版)
# ==========================================
st.header("1. 信息采集与素材上传")

# 使用三列布局
col_student, col_counselor, col_target = st.columns(3)

# --- 第一栏：学生提供信息 ---
with col_student:
    st.markdown("### 🧑‍🎓 学生提供信息")
    st.caption("上传简历、素材表与成绩单")
    
    uploaded_material = st.file_uploader("📄 文书素材/简历 (Word/PDF)", type=['docx', 'pdf'])
    uploaded_transcript = st.file_uploader("🎓 成绩单 (截图/PDF)", type=['png', 'jpg', 'jpeg', 'pdf'])

# --- 第二栏：顾问指导意见 ---
with col_counselor:
    st.markdown("### 👨‍🏫 顾问指导意见")
    st.caption("设定文书的整体策略与调性")
    
    counselor_strategy = st.text_area(
        "💡 写作策略/人设强调", 
        height=200, 
        placeholder="例如：\n1. 强调量化背景\n2. 解释GPA劣势\n3. 突出某段实习的领导力..."
    )

# --- 第三栏：目标专业信息 ---
with col_target:
    st.markdown("### 🏫 目标专业信息")
    st.caption("输入目标学校与课程设置")
    
    target_school_name = st.text_input("🏛️ 目标学校 & 专业", placeholder="例如：UCL - MSc Business Analytics")
    
    st.markdown("**课程设置 (Curriculum):**")
    # 使用 Tabs 节省空间
    tab_text, tab_img = st.tabs(["文本粘贴", "图片上传"])
    
    with tab_text:
        target_curriculum_text = st.text_area("粘贴课程列表", height=100, placeholder="Core Modules: ...")
    
    with tab_img:
        uploaded_curriculum_images = st.file_uploader("上传课程截图", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

# 读取素材文本 (逻辑保持不变)
student_background_text = ""
if uploaded_material:
    if uploaded_material.name.endswith('.docx'):
        student_background_text = read_word_file(uploaded_material)
    elif uploaded_material.name.endswith('.pdf'):
        student_background_text = read_pdf_text(uploaded_material)

# ==========================================
# 5. 界面：模块选择
# ==========================================
st.markdown("---")
st.header("2. 写作模块选择")

modules = {
    "Motivation": "申请动机",
    "Academic": "本科学习经历",
    "Internship": "实习/工作经历",
    "Why_School": "Why School",
    "Career_Goal": "职业规划"
}

selected_modules = st.multiselect("选择模块：", list(modules.keys()), format_func=lambda x: modules[x], default=list(modules.keys()))

# ==========================================
# 6. 核心逻辑：生成 Prompt
# ==========================================
st.markdown("---")
st.header("3. 一键点击创作")

# 通用规则
CLEAN_OUTPUT_RULES = """
【🚨 绝对输出规则】
1. 只输出正文内容本身。
2. 严禁包含开场白、结尾语或结构说明。
3. 严禁使用 Markdown 格式（如加粗、列表符号、标题符号）。
4. 输出必须是纯文本。
5. 必须写成一个完整的、连贯的中文自然段。
"""

# --- 翻译规则 v13.9 (保持不变) ---
TRANSLATION_RULES = """
【Translation Task】
Translate the provided Chinese text into a professional, human-sounding Personal Statement paragraph.

【🚨 CRITICAL ANTI-AI STYLE GUIDE】
1. **KILL THE "AI SENTENCE PATTERN"**: 
   - **ABSOLUTELY FORBIDDEN**: The pattern "I did X, **thereby/thus/enabling** me to do Y." 
   - **SOLUTION**: Split into two sentences or use active verbs.

2. **SEMICOLONS (;) FOR FLOW**:
   - **MANDATORY**: When a sentence is grammatically complete but the thought is not finished (and leads directly into the next point), use a **semicolon (;)** to connect them.
   - *Example*: "The model failed initially; this failure forced me to re-evaluate the parameters." (Instead of "The model failed initially. This failure..." or "The model failed, thereby forcing...")

3. **ADVERB CONTROL (Nuanced)**:
   - **STRICTLY PROHIBITED**: Adverbs placed immediately before verbs or adjectives to intensify them (e.g., "deeply analyze", "perfectly align", "acutely aware", "carefully examined"). Use stronger verbs instead (e.g., "scrutinized" instead of "carefully examined").
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

【Input Text】:
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
    1. **核心概念植入**：在描述每门课时，必须提及该课程具体的**核心概念、模型、算法或理论名称**（例如：不要只说“学了统计学”，要说“掌握了假设检验(Hypothesis Testing)和多元回归分析(Multiple Regression)”）。
    2. **学术真实感**：结合学生素材，简述是如何理解或应用这些概念的（例如：通过期末项目、实验报告或特定课题）。
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
# 7. 界面：反馈、修改与翻译
# ==========================================
if st.session_state.get('generated_sections'):
    st.markdown("---")
    st.header("4. 审阅、精修与翻译")
    st.info("👇 左侧为中文初稿，修改满意后可点击右侧按钮进行翻译。")

    display_order = ["Motivation", "Academic", "Internship", "Why_School", "Career_Goal"]
    
    for module in display_order:
        if module in st.session_state['generated_sections']:
            with st.container():
                st.subheader(f"{modules[module]}")
                
                if module == "Motivation" and st.session_state.get('motivation_trends'):
                    with st.expander("📚 点击查看：行业趋势调研与参考源 (Reference)", expanded=True):
                        st.info(st.session_state['motivation_trends'])
                
                c1, c2 = st.columns([1, 1])
                
                with c1:
                    st.markdown("**中文草稿 (可编辑)**")
                    
                    if f"text_{module}" not in st.session_state:
                        st.session_state[f"text_{module}"] = st.session_state['generated_sections'][module]
                    
                    current_content = st.text_area(
                        f"中文内容 - {module}", 
                        key=f"text_{module}",
                        height=250
                    )
                    
                    st.session_state['generated_sections'][module] = current_content

                    fb_col1, fb_col2 = st.columns([3, 1])
                    with fb_col1:
                        feedback = st.text_input(f"修改建议 ({modules[module]}):", key=f"fb_{module}")
                    with fb_col2:
                        if st.button(f"🔄 AI重写", key=f"btn_{module}"):
                            if not feedback:
                                st.warning("请输入建议")
                            else:
                                if not api_key:
                                    st.error("需要 API Key")
                                else:
                                    with st.spinner("正在重写..."):
                                        revise_prompt = f"""
                                        【任务】根据反馈修改段落。
                                        【原段落】{current_content}
                                        【用户反馈】{feedback}
                                        {CLEAN_OUTPUT_RULES}
                                        """
                                        revised_text = get_gemini_response(revise_prompt)
                                        
                                        st.session_state['generated_sections'][module] = revised_text.strip()
                                        st.session_state[f"text_{module}"] = revised_text.strip()
                                        
                                        if module in st.session_state['translated_sections']:
                                            del st.session_state['translated_sections'][module]
                                        
                                        st.rerun()

                with c2:
                    st.markdown("**英文翻译 (Translation)**")
                    
                    if st.button(f"🇺🇸 翻译为英文", key=f"trans_btn_{module}"):
                        if not api_key:
                            st.error("需要 API Key")
                        else:
                            with st.spinner("Translating..."):
                                content_to_translate = st.session_state[f"text_{module}"]
                                full_trans_prompt = f"{TRANSLATION_RULES}\n{content_to_translate}"
                                trans_res = get_gemini_response(full_trans_prompt)
                                st.session_state['translated_sections'][module] = trans_res.strip()
                    
                    if module in st.session_state['translated_sections']:
                        st.markdown(st.session_state['translated_sections'][module])
                    else:
                        st.caption("点击上方按钮生成英文翻译")

    # ==========================================
    # 8. 导出
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
