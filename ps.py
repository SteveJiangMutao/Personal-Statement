import streamlit as st
import google.generativeai as genai
from PIL import Image
import docx
import io

# ==========================================
# 1. 页面基础配置与 Session State 初始化
# ==========================================
st.set_page_config(page_title="AI 留学文书深度生成器", page_icon="✍️", layout="wide")

# 初始化 Session State 用于存储生成的内容和修改记录
if 'generated_sections' not in st.session_state:
    st.session_state['generated_sections'] = {}
if 'step' not in st.session_state:
    st.session_state['step'] = 1

st.title("✍️ AI 留学文书深度生成器 (Pro)")
st.markdown("---")

# ==========================================
# 2. 侧边栏：API 设置
# ==========================================
with st.sidebar:
    st.header("⚙️ 系统设置")
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
        st.success("✅ Key 已加载")
    else:
        api_key = st.text_input("Gemini API Key", type="password")
    
    # 推荐使用 1.5 Pro 或 3.0 Pro，因为需要处理长文档和图片
    model_name = st.selectbox("选择模型", ["gemini-1.5-pro", "gemini-3-pro-preview"], index=0)

# ==========================================
# 3. 辅助函数
# ==========================================
def read_word_file(file):
    """读取 Word 文档内容"""
    try:
        doc = docx.Document(file)
        full_text = []
        for para in doc.paragraphs:
            full_text.append(para.text)
        return '\n'.join(full_text)
    except Exception as e:
        return f"Error reading Word file: {e}"

def get_gemini_response(prompt, image_parts=None, text_context=None):
    """调用 Gemini API"""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    
    content = []
    content.append(prompt)
    
    if text_context:
        content.append(f"\n【参考文档/背景信息】:\n{text_context}")
    
    if image_parts:
        content.append(image_parts)
        
    try:
        response = model.generate_content(content)
        return response.text
    except Exception as e:
        return f"Error: {str(e)}"

# ==========================================
# 4. 界面：第一步 - 信息采集 (Requirement 1)
# ==========================================
st.header("1️⃣ 信息采集与素材上传")

col1, col2 = st.columns(2)

with col1:
    st.subheader("📂 学生素材")
    uploaded_word = st.file_uploader("上传文书信息收集表 (.docx)", type=['docx'])
    uploaded_transcript = st.file_uploader("上传成绩单截图 (Image)", type=['png', 'jpg', 'jpeg'])

with col2:
    st.subheader("🧠 顾问指导 & 目标")
    counselor_strategy = st.text_area("顾问指导思路 (你的Direction)", height=150, 
                                      placeholder="例如：强调该生在量化分析方面的潜力，弱化GPA劣势，重点突出某段互联网大厂的实习...")
    target_school_name = st.text_input("目标学校 & 专业名称", placeholder="例如：UCL - MSc Business Analytics")
    target_curriculum = st.text_area("目标专业课程设置 (复制粘贴官网课程列表)", height=150, 
                                     placeholder="例如：Core modules: Data Mining, Econometrics... Electives: ...")

# 提取 Word 内容
word_content = ""
if uploaded_word:
    word_content = read_word_file(uploaded_word)
    with st.expander("查看已读取的文书素材"):
        st.text(word_content[:500] + "...")

# ==========================================
# 5. 界面：第二步 - 模块选择 (Requirement 2)
# ==========================================
st.markdown("---")
st.header("2️⃣ 写作模块选择")

modules = {
    "Motivation": "申请动机 (结合行业热点)",
    "Academic": "本科学习经历 (基于成绩单)",
    "Internship": "实习/工作经历 (基于素材表)",
    "Why_School": "Why School (基于课程匹配)",
    "Career_Goal": "职业规划 (具体职位与路径)"
}

selected_modules = st.multiselect("请勾选本篇文书需要包含的模块：", list(modules.keys()), format_func=lambda x: modules[x], default=list(modules.keys()))

# ==========================================
# 6. 核心逻辑：生成 Prompt 并写作 (Requirement 3-7)
# ==========================================
st.markdown("---")
st.header("3️⃣ AI 深度写作")

if st.button("🚀 开始生成初稿", type="primary"):
    if not api_key or not uploaded_word or not uploaded_transcript or not target_curriculum:
        st.error("❌ 请确保 API Key、文书素材表、成绩单截图、目标课程设置均已填写/上传。")
        st.stop()
    
    image_obj = Image.open(uploaded_transcript)
    
    # 进度条
    progress_bar = st.progress(0)
    total_steps = len(selected_modules)
    current_step = 0

    # --- 定义各个模块的 Prompt ---
    
    # 1. 动机 (Requirement 3)
    prompt_motivation = f"""
    【任务】撰写 Personal Statement 的 "申请动机" 部分。
    【输入背景】
    - 顾问指导思路: {counselor_strategy}
    - 目标专业: {target_school_name}
    - 学生素材: 见附带文本
    【要求】
    1. **提取素材**：从学生素材中找到触发其兴趣的经历。
    2. **结合行业热点 (Research)**：利用你的知识库，分析 {target_school_name} 所在领域目前的研究热点或业内热门话题。
    3. **逻辑连接**：将学生的细分兴趣与该行业热点连接，说明学生想通过硕士学位进入该细分领域。
    4. **语气**：简洁凝练，开门见山。让招生官一眼看出学生对该领域有深度思考。
    5. **语言**：中文，逻辑严密。
    """

    # 2. 职业规划 (Requirement 4)
    prompt_career = f"""
    【任务】撰写 Personal Statement 的 "职业规划" (Career Goals) 部分。
    【输入背景】
    - 目标专业: {target_school_name}
    - 顾问思路: {counselor_strategy}
    【要求】
    1. **基于动机**：承接上文的申请动机和方向。
    2. **应届生视角**：规划必须是硕士毕业应届生能力范围内可行的。
    3. **具体化 (Critical)**：必须包含具体的**公司名字**、**具体职位**。
    4. **内容**：精炼描述可能会从事的工作内容，以及在岗位上继续学习的方向。
    5. **语言**：中文，务实。
    """

    # 3. 本科学习 (Requirement 5 - 需视觉能力)
    prompt_academic = f"""
    【任务】撰写 Personal Statement 的 "本科学习经历" (Academic Background) 部分。
    【输入背景】
    - 目标专业: {target_school_name}
    - 成绩单: 见附带图片
    【要求】
    1. **视觉分析**：仔细阅读图片中的成绩单。
    2. **筛选**：挑选出与 {target_school_name} **高度相关**的课程模块，剔除不相关的。
    3. **深度阐述**：不要列举课程名。将相关课程组合，阐述这些课程教授了什么**关键概念**和**方法学**。
    4. **逻辑关联**：强调课程间的联系（如xx是xx的基础，或互为补充），不要平铺直叙。
    5. **语言**：中文，富有逻辑，学术化。
    """

    # 4. Why School (Requirement 6)
    prompt_whyschool = f"""
    【任务】撰写 Personal Statement 的 "Why School" 部分。
    【输入背景】
    - 目标学校: {target_school_name}
    - 目标课程设置: {target_curriculum}
    - 顾问思路: {counselor_strategy}
    【要求】
    1. **课程分析**：根据提供的目标课程设置，阐述为什么对这些课程感兴趣。
    2. **价值阐述**：说明这些硕士课程（关键概念/方法学）对学生有什么具体帮助。
    3. **逻辑组合**：将描述组合成自然的段落，强调课程间的联系，融入申请动机。
    4. **语气**：朴素、专业、议论和分析的语气。**严禁夸张**。
    5. **语言**：中文。
    """

    # 5. 实习/工作 (Requirement 7)
    prompt_internship = f"""
    【任务】撰写 Personal Statement 的 "实习/工作经历" (Professional Experience) 部分。
    【输入背景】
    - 学生素材: 见附带文本
    - 目标专业: {target_school_name}
    【要求】
    1. **筛选**：从素材中剔除不相关的经历，只保留与申请专业最相关的。
    2. **时间顺序**：按时间顺序梳理。
    3. **结构**：背景 -> 职责 -> 学到的技能 -> 进一步攻读硕士的动机。
    4. **风格**：不要流水账。要有逻辑地梳理。
    5. **细节**：保留少量执行细节以保证真实性，但不要过多。
    6. **语言**：中文。
    """

    # --- 循环生成 ---
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
        
        # 决定是否传入图片（只有 Academic 需要看成绩单）
        img_input = image_obj if module == "Academic" else None
        
        # 调用 AI
        res = get_gemini_response(prompts_map[module], image_parts=img_input, text_context=word_content)
        
        # 存入 Session State
        st.session_state['generated_sections'][module] = res
        progress_bar.progress(current_step / total_steps)

    st.success("✅ 初稿生成完毕！请在下方查看并修改。")

# ==========================================
# 7. 界面：第四步 - 反馈与修改 (Requirement 8)
# ==========================================
if st.session_state.get('generated_sections'):
    st.markdown("---")
    st.header("4️⃣ 审阅与精修 (Feedback Loop)")
    st.info("👇 你可以在下方针对每个模块提出修改建议，AI 将根据你的反馈重写。")

    # 按照逻辑顺序展示
    display_order = ["Motivation", "Academic", "Internship", "Why_School", "Career_Goal"]
    
    for module in display_order:
        if module in st.session_state['generated_sections']:
            with st.container():
                st.subheader(f"📄 {modules[module]}")
                
                # 显示当前内容
                current_content = st.session_state['generated_sections'][module]
                st.text_area(f"当前内容 ({module})", value=current_content, height=300, key=f"text_{module}")
                
                # 修改建议输入框
                col_f1, col_f2 = st.columns([3, 1])
                with col_f1:
                    feedback = st.text_input(f"针对 {modules[module]} 的修改建议/反馈:", key=f"fb_{module}", placeholder="例如：语气再强硬一点；补充一下关于xx课程的细节...")
                with col_f2:
                    if st.button(f"🔄 修改 {module}", key=f"btn_{module}"):
                        if not feedback:
                            st.warning("请先输入修改建议")
                        else:
                            with st.spinner(f"正在根据反馈重写 {modules[module]}..."):
                                # 构建修改 Prompt
                                revise_prompt = f"""
                                【任务】根据用户的反馈修改以下文书段落。
                                【原段落】
                                {current_content}
                                
                                【用户修改反馈】
                                {feedback}
                                
                                【要求】
                                1. 严格遵循用户的反馈进行修改。
                                2. 保持原文的逻辑结构（除非用户要求改变）。
                                3. 输出修改后的完整段落。
                                """
                                # 重新调用 AI (这里不需要传图片了，基于文本修改即可)
                                revised_text = get_gemini_response(revise_prompt)
                                st.session_state['generated_sections'][module] = revised_text
                                st.rerun() # 刷新页面显示新内容

    # ==========================================
    # 8. 最终导出
    # ==========================================
    st.markdown("---")
    st.header("5️⃣ 最终导出")
    
    full_text = ""
    for module in display_order:
        if module in st.session_state['generated_sections']:
            full_text += f"【{modules[module]}】\n"
            full_text += st.session_state['generated_sections'][module] + "\n\n"
            
    st.download_button(
        label="📥 下载完整文书 (.txt)",
        data=full_text,
        file_name=f"Personal_Statement_{target_school_name}.txt",
        mime="text/plain",
        type="primary"
    )