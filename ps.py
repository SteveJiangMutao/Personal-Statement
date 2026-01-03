import streamlit as st
import google.generativeai as genai
from PIL import Image
import docx
import io

# ==========================================
# 1. 页面基础配置
# ==========================================
st.set_page_config(page_title="AI 留学文书深度生成器 (Pro)", page_icon="✍️", layout="wide")

if 'generated_sections' not in st.session_state:
    st.session_state['generated_sections'] = {}
if 'step' not in st.session_state:
    st.session_state['step'] = 1

st.title("✍️ AI 留学文书深度生成器 (混合输入版)")
st.markdown("---")

# ==========================================
# 2. 系统设置 (内置 Key)
# ==========================================
with st.sidebar:
    st.header("⚙️ 系统设置")
    api_key = "AIzaSyDQ51jjPXsbeboTG-qrpgvy-HAtM-NYHpU"
    st.success("✅ Key 已内置")
    # 必须使用 Pro 模型以处理多图和长文本
    model_name = st.selectbox("选择模型", ["gemini-3-pro-preview"], index=0)

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

def get_gemini_response(prompt, images=None, text_context=None):
    """
    images: 可以是单个 PIL Image，也可以是 PIL Image 的列表
    """
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    
    content = []
    content.append(prompt)
    
    if text_context:
        content.append(f"\n【参考文档/背景信息】:\n{text_context}")
    
    # 处理图片输入 (支持单图或多图列表)
    if images:
        if isinstance(images, list):
            content.extend(images)
        else:
            content.append(images)
        
    try:
        response = model.generate_content(content)
        return response.text
    except Exception as e:
        return f"Error: {str(e)}"

# ==========================================
# 4. 界面：信息采集
# ==========================================
st.header("1️⃣ 信息采集与素材上传")

col1, col2 = st.columns(2)

with col1:
    st.subheader("📂 学生素材")
    uploaded_word = st.file_uploader("上传文书信息收集表 (.docx)", type=['docx'])
    uploaded_transcript = st.file_uploader("上传成绩单截图 (单张)", type=['png', 'jpg', 'jpeg'])

with col2:
    st.subheader("🧠 顾问指导 & 目标")
    counselor_strategy = st.text_area("顾问指导思路 (Direction)", height=100, 
                                      placeholder="例如：强调量化分析潜力，弱化GPA...")
    target_school_name = st.text_input("目标学校 & 专业名称", placeholder="例如：UCL - MSc Business Analytics")
    
    # --- 修改点：支持文本 OR 图片 OR 两者皆有 ---
    st.markdown("**目标专业课程设置 (支持 文本粘贴 或 图片上传):**")
    target_curriculum_text = st.text_area("方式A: 粘贴课程列表文本", height=100, placeholder="Core Modules: ...")
    uploaded_curriculum_images = st.file_uploader("方式B: 上传课程列表截图 (支持多张)", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

# 读取 Word
word_content = ""
if uploaded_word:
    word_content = read_word_file(uploaded_word)

# ==========================================
# 5. 界面：模块选择
# ==========================================
st.markdown("---")
st.header("2️⃣ 写作模块选择")

modules = {
    "Motivation": "申请动机",
    "Academic": "本科学习经历",
    "Internship": "实习/工作经历",
    "Why_School": "Why School (基于课程)",
    "Career_Goal": "职业规划"
}

selected_modules = st.multiselect("选择模块：", list(modules.keys()), format_func=lambda x: modules[x], default=list(modules.keys()))

# ==========================================
# 6. 核心逻辑：生成 Prompt
# ==========================================
st.markdown("---")
st.header("3️⃣ AI 深度写作")

# 纯净输出规则
CLEAN_OUTPUT_RULES = """
【🚨 绝对输出规则 (违反将导致任务失败) 🚨】
1. **只输出正文内容本身**。
2. **严禁**包含任何开场白（如 "Here is the draft", "这是一段..."）。
3. **严禁**包含任何结尾语或 "设计思路"、"逻辑结构" 说明。
4. **严禁**使用 Markdown 加粗符号（即不要出现 **text**）。
5. **严禁**使用 Markdown 列表符号（如 - 或 1.）。
6. **严禁**使用 Markdown 标题符号（如 ###）。
7. 输出必须是**纯文本**，仅包含必要的标点符号。
8. 必须写成**一个完整的、连贯的中文自然段**。
"""

if st.button("🚀 开始生成初稿", type="primary"):
    # 检查必要输入
    # 逻辑：课程设置只要有 文本 或 图片 其中之一即可
    has_curriculum = target_curriculum_text or uploaded_curriculum_images
    
    if not uploaded_word or not uploaded_transcript or not has_curriculum:
        st.error("❌ 请确保：文书素材表、成绩单截图、目标课程信息 (文本或图片) 均已提供。")
        st.stop()
    
    # 准备图片对象
    transcript_img = Image.open(uploaded_transcript)
    curriculum_imgs = [Image.open(img) for img in uploaded_curriculum_images] if uploaded_curriculum_images else None
    
    progress_bar = st.progress(0)
    total_steps = len(selected_modules)
    current_step = 0

    # --- 定义 Prompt ---
    
    # 1. 动机
    prompt_motivation = f"""
    【任务】撰写 Personal Statement 的 "申请动机" 部分。
    【输入背景】
    - 顾问思路: {counselor_strategy}
    - 目标专业: {target_school_name}
    - 学生素材: 见附带文本
    【内容要求】
    1. 提取素材中触发兴趣的经历。
    2. 结合 {target_school_name} 所在领域的行业热点。
    3. 逻辑连接：兴趣 -> 热点 -> 申请必要性。
    4. 语气简洁凝练，开门见山。
    {CLEAN_OUTPUT_RULES}
    """

    # 2. 职业规划
    prompt_career = f"""
    【任务】撰写 "职业规划" (Career Goals) 部分。
    【输入背景】
    - 目标专业: {target_school_name}
    - 顾问思路: {counselor_strategy}
    【内容要求】
    1. 规划硕士毕业后的路径（应届生视角）。
    2. **必须包含**：具体的公司名字、具体的职位名称。
    3. 将工作内容和学习方向融合在一段话中。
    {CLEAN_OUTPUT_RULES}
    """

    # 3. 本科学习 (视觉 - 成绩单)
    prompt_academic = f"""
    【任务】撰写 "本科学习经历" (Academic Background) 部分。
    【输入背景】
    - 目标专业: {target_school_name}
    - 成绩单: 见附带图片
    【内容要求】
    1. 仔细阅读成绩单图片，筛选出与 {target_school_name} **高度相关**的课程。
    2. 将课程的关键概念、方法学融合成一段有逻辑的叙述。
    3. 强调课程间的联系（基础/进阶/交叉），体现学术深度。
    {CLEAN_OUTPUT_RULES}
    """

    # 4. Why School (混合输入：文本 + 图片)
    # 动态构建课程信息的提示词
    curriculum_text_prompt = ""
    if target_curriculum_text:
        curriculum_text_prompt = f"\n【目标课程文本列表】:\n{target_curriculum_text}\n"
    
    prompt_whyschool = f"""
    【任务】撰写 "Why School" 部分。
    【输入背景】
    - 目标学校: {target_school_name}
    - 顾问思路: {counselor_strategy}
    {curriculum_text_prompt}
    - 课程图片信息: 见附带图片 (如果有)
    
    【内容要求】
    1. **综合分析**：结合提供的文本列表和图片中的课程信息。
    2. **筛选**：从中挑选出 3-4 门与学生背景或未来规划最相关的特定课程。
    3. **阐述**：说明这些课程（提及具体课名或核心概念）为何吸引学生，以及能提供什么帮助。
    4. 语气朴素专业，议论为主，不要夸张。
    {CLEAN_OUTPUT_RULES}
    """

    # 5. 实习/工作
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
        
        # 决定传入哪组图片
        current_images = None
        if module == "Academic":
            current_images = transcript_img # 传成绩单
        elif module == "Why_School":
            current_images = curriculum_imgs # 传课程截图列表 (如果有)
        
        res = get_gemini_response(prompts_map[module], images=current_images, text_context=word_content)
        
        st.session_state['generated_sections'][module] = res.strip()
        progress_bar.progress(current_step / total_steps)

    st.success("✅ 初稿生成完毕！")

# ==========================================
# 7. 界面：反馈与修改
# ==========================================
if st.session_state.get('generated_sections'):
    st.markdown("---")
    st.header("4️⃣ 审阅与精修")
    st.info("👇 AI 已按纯净模式输出。如需修改，请在下方输入建议。")

    display_order = ["Motivation", "Academic", "Internship", "Why_School", "Career_Goal"]
    
    for module in display_order:
        if module in st.session_state['generated_sections']:
            with st.container():
                st.subheader(f"📄 {modules[module]}")
                
                current_content = st.session_state['generated_sections'][module]
                st.text_area(f"内容 ({module})", value=current_content, height=200, key=f"text_{module}")
                
                col_f1, col_f2 = st.columns([3, 1])
                with col_f1:
                    feedback = st.text_input(f"修改建议 ({modules[module]}):", key=f"fb_{module}")
                with col_f2:
                    if st.button(f"🔄 修改 {module}", key=f"btn_{module}"):
                        if not feedback:
                            st.warning("请输入建议")
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
                                st.rerun()

    # ==========================================
    # 8. 导出
    # ==========================================
    st.markdown("---")
    st.header("5️⃣ 最终导出")
    
    full_text = ""
    for module in display_order:
        if module in st.session_state['generated_sections']:
            full_text += st.session_state['generated_sections'][module] + "\n\n"
            
    st.download_button(
        label="📥 下载纯净文书 (.txt)",
        data=full_text,
        file_name=f"PS_{target_school_name}.txt",
        mime="text/plain",
        type="primary"
    )

