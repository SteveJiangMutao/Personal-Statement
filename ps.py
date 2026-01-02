import streamlit as st
import google.generativeai as genai
from PIL import Image
import docx
import io

# ==========================================
# 1. 页面基础配置与 Session State 初始化
# ==========================================
st.set_page_config(page_title="AI 留学文书深度生成器 (Pro)", page_icon="✍️", layout="wide")

# 初始化 Session State
if 'generated_sections' not in st.session_state:
    st.session_state['generated_sections'] = {}
if 'step' not in st.session_state:
    st.session_state['step'] = 1

st.title("✍️ AI 留学文书深度生成器 (Pro)")
st.markdown("---")

# ==========================================
# 2. 侧边栏：API 设置 (已内置 Key)
# ==========================================
with st.sidebar:
    st.header("⚙️ 系统设置")
    
    # --- 🔑 核心修改：直接内置 API Key ---
    api_key = "AIzaSyDQ51jjPXsbeboTG-qrpgvy-HAtM-NYHpU"
    st.success("✅ Key 已内置")
    
    # 模型选择 (保留 gemini-3-pro 以处理长文本和图片)
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
# 4. 界面：第一步 - 信息采集
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
# 5. 界面：第二步 - 模块选择
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
# 6. 核心逻辑：生成 Prompt 并写作
# ==========================================
st.markdown("---")
st.header("3️⃣ AI 深度写作")

if st.button("🚀 开始生成初稿", type="primary"):
    if not uploaded_word or not uploaded_transcript or not target_curriculum:
        st.error("❌ 请确保文书素材表、成绩单截图、目标课程设置均已填写/上传。")
        st.stop()
    
    image_obj = Image.open(uploaded_transcript)
    
    progress_bar = st.progress(0)
    total_steps = len(selected_modules)
    current_step = 0

    # --- 定义各个模块的 Prompt (强制自然段版) ---
    
    # 1. 动机
    prompt_motivation = f"""
    【任务】撰写 Personal Statement 的 "申请动机" 部分。
    【输入背景】
    - 顾问指导思路: {counselor_strategy}
    - 目标专业: {target_school_name}
    - 学生素材: 见附带文本
    【格式要求】
    - **必须写成一个完整的、连贯的中文自然段**。
    - **严禁**使用列表、要点（1. 2. 3.）或分段。
    【内容要求】
    1. 从素材中提取触发兴趣的经历。
    2. 结合 {target_school_name} 所在领域的行业热点或热门话题。
    3. 逻辑连接：学生兴趣 -> 行业热点 -> 申请该细分领域的必要性。
    4. 语气简洁凝练，开门见山，体现深度思考。
    """

    # 2. 职业规划
    prompt_career = f"""
    【任务】撰写 Personal Statement 的 "职业规划" (Career Goals) 部分。
    【输入背景】
    - 目标专业: {target_school_name}
    - 顾问思路: {counselor_strategy}
    【格式要求】
    - **必须写成一个完整的、连贯的中文自然段**。
    - **严禁**使用列表、要点或分段。
    【内容要求】
    1. 基于申请动机，规划一条切实可行的路径（应届生视角）。
    2. **必须包含**：具体的公司名字、具体的职位名称。
    3. 将工作内容描述和在岗位上的学习方向融合在这一段话中，不要罗列。
    """

    # 3. 本科学习 (视觉)
    prompt_academic = f"""
    【任务】撰写 Personal Statement 的 "本科学习经历" (Academic Background) 部分。
    【输入背景】
    - 目标专业: {target_school_name}
    - 成绩单: 见附带图片
    【格式要求】
    - **必须写成一个完整的、连贯的中文自然段**。
    - **严禁**简单的罗列课程名称。
    - **严禁**使用列表或分点。
    【内容要求】
    1. 仔细阅读成绩单，筛选出与 {target_school_name} 高度相关的课程模块。
    2. 将这些课程的关键概念、方法学融合成一段有逻辑的叙述。
    3. 强调课程之间的联系（如基础与进阶、理论与实践的交集），体现学术深度。
    """

    # 4. Why School
    prompt_whyschool = f"""
    【任务】撰写 Personal Statement 的 "Why School" 部分。
    【输入背景】
    - 目标学校: {target_school_name}
    - 目标课程设置: {target_curriculum}
    - 顾问思路: {counselor_strategy}
    【格式要求】
    - **必须写成一个完整的、连贯的中文自然段**。
    - **严禁**使用列表或分点。
    【内容要求】
    1. 根据目标课程设置，阐述对特定课程（提及关键概念/方法学）的兴趣。
    2. 说明这些课程对学生的具体帮助。
    3. 将上述内容与申请动机自然融合，语气朴素专业，以议论和分析为主，不要夸张。
    """

    # 5. 实习/工作
    prompt_internship = f"""
    【任务】撰写 Personal Statement 的 "实习/工作经历" (Professional Experience) 部分。
    【输入背景】
    - 学生素材: 见附带文本
    - 目标专业: {target_school_name}
    【格式要求】
    - **必须写成一个完整的、连贯的中文自然段**。
    - **严禁**流水账，**严禁**使用列表。
    【内容要求】
    1. 筛选最相关的经历，按时间顺序逻辑串联。
    2. 结构融合：背景 -> 职责 -> 技能 -> 攻读硕士的动机。
    3. 保留少量执行细节以保真，但重点在于逻辑梳理和反思。
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
        
        img_input = image_obj if module == "Academic" else None
        
        res = get_gemini_response(prompts_map[module], image_parts=img_input, text_context=word_content)
        
        st.session_state['generated_sections'][module] = res
        progress_bar.progress(current_step / total_steps)

    st.success("✅ 初稿生成完毕！请在下方查看并修改。")

# ==========================================
# 7. 界面：第四步 - 反馈与修改
# ==========================================
if st.session_state.get('generated_sections'):
    st.markdown("---")
    st.header("4️⃣ 审阅与精修 (Feedback Loop)")
    st.info("👇 AI 已将每个部分写成一个完整的自然段。如需调整，请在下方输入建议。")

    display_order = ["Motivation", "Academic", "Internship", "Why_School", "Career_Goal"]
    
    for module in display_order:
        if module in st.session_state['generated_sections']:
            with st.container():
                st.subheader(f"📄 {modules[module]}")
                
                current_content = st.session_state['generated_sections'][module]
                st.text_area(f"当前内容 ({module})", value=current_content, height=250, key=f"text_{module}")
                
                col_f1, col_f2 = st.columns([3, 1])
                with col_f1:
                    feedback = st.text_input(f"针对 {modules[module]} 的修改建议:", key=f"fb_{module}", placeholder="例如：增加一点关于xx项目的细节；语气再学术一点...")
                with col_f2:
                    if st.button(f"🔄 修改 {module}", key=f"btn_{module}"):
                        if not feedback:
                            st.warning("请先输入修改建议")
                        else:
                            with st.spinner(f"正在重写 {modules[module]}..."):
                                revise_prompt = f"""
                                【任务】根据反馈修改文书段落。
                                【原段落】{current_content}
                                【用户反馈】{feedback}
                                【严格约束】
                                1. **必须输出为一个完整的、连贯的中文自然段**。
                                2. **严禁**使用列表、要点或分行。
                                3. 严格遵循用户反馈进行调整。
                                """
                                revised_text = get_gemini_response(revise_prompt)
                                st.session_state['generated_sections'][module] = revised_text
                                st.rerun()

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
