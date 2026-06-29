import os
import datetime
import streamlit as st
import config
import nibabel as nib
import numpy as np
import matplotlib.pyplot as plt
import traceback
import io
import plotly.graph_objects as go
from utils.ui_utils import diagnosis_view_style
from image_processing.diagnosis_engine import DiagnosisEngine

# ==================== 1. PDF 报告生成引擎 ====================
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont


def register_chinese_font():
    """
    注册支持中文的字体，优先使用本地 ttf 文件，若不存在则使用 ReportLab 内建 CID 字体。
    返回字体名。
    """
    font_name = None
    
    root_dir = os.path.dirname(os.path.dirname(__file__)) # 获取根目录
    local_ttf = os.path.join(root_dir, "fonts", "WenYuanSerifSC-Medium.ttf")
    
    if os.path.exists(local_ttf):
        try:
            pdfmetrics.registerFont(TTFont('ChineseFont', local_ttf))
            font_name = 'ChineseFont'
            print(f"[PDF] 成功加载本地新字体: {local_ttf}")
            return font_name
        except Exception as e:
            print(f"[PDF] 本地新字体注册失败，转入备用逻辑: {e}")
    
    system_fonts = [
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
        "C:/Windows/Fonts/simsun.ttc"
    ]
    for sf in system_fonts:
        if os.path.exists(sf):
            try:
                pdfmetrics.registerFont(TTFont('ChineseFont', sf))
                font_name = 'ChineseFont'
                print(f"[PDF] 使用系统字体: {sf}")
                return font_name
            except:
                continue
    
    try:
        pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
        font_name = 'STSong-Light'
        print("[PDF] 使用内建 CID 字体 STSong-Light")
    except Exception as e:
        print(f"[PDF] 所有中文字体注册失败: {e}")
        font_name = 'Helvetica'
    
    return font_name


def generate_pdf_report(case_name, task_name, ai_reports, report_date):
    """
    全自动构建符合临床医疗规范的结构化 PDF 诊断报告。
    """
    font_name = register_chinese_font()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=54, leftMargin=54,
                            topMargin=54, bottomMargin=54)
    story = []

    # ==================== 【核心新增：校徽与校名横向并排】 ====================
    root_dir = os.path.dirname(os.path.dirname(__file__)) # 获取项目根目录

    logo_path = os.path.join(root_dir, "assets", "school_logo.png") 
    name_path = os.path.join(root_dir, "assets", "school_name.png") 

    if os.path.exists(logo_path) and os.path.exists(name_path):
        try:
            from reportlab.lib.utils import ImageReader
            
            # 1. 设定统一的显示高度（比如 35 像素高），让两张图看起来一样高
            target_h = 35
            
            # 计算校徽等比例宽度
            logo_reader = ImageReader(logo_path)
            logo_w, logo_h = logo_reader.getSize()
            target_logo_w = (logo_w / logo_h) * target_h
            logo_img = Image(logo_path, width=target_logo_w, height=target_h)
            
            # 计算校名等比例宽度
            name_reader = ImageReader(name_path)
            name_w, name_h = name_reader.getSize()
            target_name_w = (name_w / name_h) * target_h
            name_img = Image(name_path, width=target_name_w, height=target_h)
            
            header_table = Table([[logo_img, name_img]], colWidths=[target_logo_w + 5, target_name_w])
            
            # 设置表格样式：清除所有边框，控制对齐方式
            header_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # 垂直居中对齐
                ('ALIGN', (0, 0), (0, 0), 'RIGHT'),      # 第一列（校徽）靠右靠拢
                ('ALIGN', (1, 0), (1, 0), 'LEFT'),       # 第二列（校名）靠左靠拢
                ('LEFTPADDING', (0, 0), (-1, -1), 0),    # 清空内边距，防止被撑开
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ]))
            
            # 让整个拼好的车头组件在 PDF 页面中居中
            header_table.hAlign = 'CENTER'
            
            story.append(header_table)
            story.append(Spacer(1, 20)) # 在学校标志下方留出间距
            
        except Exception as e:
            print(f"[PDF] 学校标志（双图）加载失败: {e}")

    # ==================== 强制样式重写与间距锁死 ====================
    styles = getSampleStyleSheet()

    styles['Normal'].fontName = font_name
    styles['Normal'].fontSize = 10.5
    styles['Normal'].leading = 15
    styles['Normal'].textColor = colors.HexColor("#111827")
    styles['Normal'].charSpace = -0.2 

    body_style = ParagraphStyle(
        'MedicalBody',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=10.5,
        leading=15,
        textColor=colors.HexColor("#111827"),
        charSpace=-0.2  # 【核心修复】微调字间距，防止任何西文被撑开
    )
    if 'MedicalBody' in styles:
        styles['MedicalBody'] = body_style
    else:
        styles.add(body_style)

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName=font_name,
        fontSize=22,
        leading=26,
        alignment=1,
        spaceAfter=20,
        textColor=colors.HexColor("#0066CC"),
        charSpace=0 
    )

    h2_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontName=font_name,
        fontSize=14,
        leading=18,
        spaceBefore=15,
        spaceAfter=10,
        textColor=colors.HexColor("#1E3A8A"),
        charSpace=0
    )

    story.append(Paragraph("医学影像智能分析平台 — 结构化辅助诊断报告", title_style))
    story.append(Spacer(1, 10))

    meta_data = [
        [Paragraph(f"<b>分析病例 (Case Name):</b> {case_name}", body_style),
         Paragraph(f"<b>诊断项目 (Task Name):</b> {task_name}", body_style)],
        [Paragraph(f"<b>报告日期 (Date):</b> {report_date}", body_style),
         Paragraph(f"<b>诊断机制 (Method):</b> nnU-Net v2 自适应解剖网络", body_style)]
    ]
    t_meta = Table(meta_data, colWidths=[250, 250])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F3F4F6")),
        ('PADDING', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LINEBELOW', (0, -1), (-1, -1), 1, colors.HexColor("#0066CC")),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 20))

    story.append(Paragraph("一、 定量体积学放射组学分析 (Quantitative Analytics)", h2_style))

    table_data = [[Paragraph("<b>评估靶区 / 亚结构 (Anatomic Region)</b>", body_style),
                   Paragraph("<b>绝对体积 (Absolute Volume)</b>", body_style)]]

    status_summary = "未见明显恶性占位或边界异常。"
    for r in ai_reports:
        clean_r = r.replace("脑肿瘤分析完成。", "").replace("海马体分析完成。", "").replace(
            "心脏分析完成。", "").replace("前列腺分析完成。", "")
        if "ml" in clean_r:
            parts = clean_r.split("约") if "约" in clean_r else clean_r.split(":")
            region = parts[0].strip()
            vol_val = parts[1].strip() if len(parts) > 1 else parts[0]
            table_data.append([Paragraph(region, body_style), Paragraph(vol_val, body_style)])
        if "严重程度" in r or "建议" in r or "Warning" in r:
            status_summary = r

    t_metrics = Table(table_data, colWidths=[280, 220])
    t_metrics.setStyle(TableStyle([
        ('LINEABOVE', (0, 0), (-1, 0), 1.5, colors.HexColor("#111827")),
        ('LINEBELOW', (0, 0), (-1, 0), 1.0, colors.HexColor("#111827")),
        ('LINEBELOW', (0, -1), (-1, -1), 1.5, colors.HexColor("#111827")),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ]))
    story.append(t_metrics)
    story.append(Spacer(1, 20))

    story.append(Paragraph("二、 智能决策辅助意见 (AI Diagnostic Suggestions)", h2_style))
    story.append(Paragraph(f"<b>临床状态提示:</b> {status_summary}", body_style))
    story.append(Spacer(1, 15))

    story.append(Paragraph(
        "<i>*注：本报告由计算机深度学习辅助诊断系统自动生成，定量指标仅供临床科室审阅参考，最终确诊结论请以主治医师签章报告为准。</i>",
        body_style))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


# ==================== 2. 核心视图展示流 ====================

def show_diagnosis_page(theme="Dark"):
    diagnosis_view_style(theme)

    text_color = "#FFFFFF" if theme == "Dark" else "#111827"
    st.markdown(f"""
        <style>
            .stApp, .stMarkdown, p, div, span, button, select, label {{
                font-family: "Microsoft YaHei", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
            }}
            /* 强制覆盖数据面板 Alert 框里的暗蓝色，彻底看清字 */
            div[data-testid="stNotification"] p, 
            div[data-testid="stNotification"] span, 
            div[data-testid="stNotification"] div {{
                color: {text_color} !important;
                font-weight: 500 !important;
                font-size: 14.5px !important;
            }}
        </style>
    """, unsafe_allow_html=True)

    diag_engine = DiagnosisEngine()

    username = st.session_state.get("username", "admin")
    user_paths = config.get_user_paths(username)
    RAW_ROOT = user_paths["raw"]

    if os.path.exists(RAW_ROOT):
        raw_cases = [f for f in os.listdir(RAW_ROOT) if f.endswith(('.nii', '.nii.gz'))]
        raw_cases.sort()
    else:
        raw_cases = []

    # --- 顶部线性控制控制台 ---
    with st.container():
        c1, c2, c3, c4, c5 = st.columns([1, 2, 1.5, 1.5, 2])
        with c1:
            if st.button("⬅ 返回", use_container_width=True):
                st.session_state["step"] = "MENU"
                for k in ["diag_result_path", "diag_case_name", "diag_task_name", "cur_ai_reports"]:
                    st.session_state.pop(k, None)
                st.rerun()

        with c2:
            current_raw_val = st.session_state.get("current_raw")
            if raw_cases and current_raw_val in raw_cases:
                default_index = raw_cases.index(current_raw_val)
            else:
                default_index = 0

            selected_raw = st.selectbox(
                "raw_selector", 
                raw_cases if raw_cases else ["未检测到影像文件"],
                index=default_index,
                label_visibility="collapsed"
            )
            if raw_cases:
                st.session_state["current_raw"] = selected_raw

        with c3:
            task_options = ["海马体(hippocampus)","脑肿瘤(brainTumour)",  "心脏(heart)", "前列腺(prostate)", "脾脏(spleen)"]
            current_task_val = st.session_state.get("current_task", task_options[0])

            selected_task = st.selectbox(
                "task_selector", task_options,
                index=task_options.index(current_task_val) if current_task_val in task_options else 0,
                label_visibility="collapsed"
            )
            if selected_task != st.session_state.get("current_task"):
                st.session_state["current_task"] = selected_task
                for k in ["diag_result_path", "diag_case_name", "diag_task_name", "cur_ai_reports"]:
                    st.session_state.pop(k, None)
                st.rerun()

        with c4:
            if st.button("🔬 开始自动诊断", use_container_width=True):
                if raw_cases and selected_raw and selected_raw != "未检测到影像文件":
                    with st.spinner("正在调用相关模型..."):
                        try:
                            selected_file_path = os.path.join(RAW_ROOT, selected_raw)

                            task_mapping = {
                                "海马体(hippocampus)": "hippocampus",
                                "心脏(heart)": "heart",
                                "前列腺(prostate)": "prostate",
                                "脑肿瘤(brainTumour)": "brainTumour",
                                "脾脏(spleen)": "spleen"
                            }
                            engine_task_key = task_mapping.get(selected_task, "brainTumour")

                            diag_engine.set_model(engine_task_key)
                            
                            # 1. 运行推理，生成 mask 文件
                            out_mask_path = diag_engine.run_inference(selected_file_path)

                            if out_mask_path and os.path.exists(out_mask_path):
                            
                                temp_mask_img = nib.load(out_mask_path)
                                temp_mask_data = temp_mask_img.get_fdata()
                      
                                temp_spacing = temp_mask_img.header.get_zooms()[:3] 

                                task_mapping_reverse = {
                                    "海马体(hippocampus)": "hippocampus",
                                    "心脏(heart)": "heart",
                                    "前列腺(prostate)": "prostate",
                                    "脑肿瘤(brainTumour)": "brainTumour",
                                    "脾脏(spleen)": "spleen"
                                }
                                current_engine_key = task_mapping_reverse.get(selected_task, "brainTumour")
                                
                                temp_reports = diag_engine.ai_logic(temp_mask_data, task_key=current_engine_key, spacing=temp_spacing)

                                st.session_state["diag_result_path"] = out_mask_path
                                st.session_state["diag_case_name"] = selected_raw
                                st.session_state["diag_task_name"] = selected_task
                                st.session_state["cur_ai_reports"] = temp_reports  # 将生成的文本存入缓存
                                st.success("🎉 诊断成功！")
                                st.rerun()
                        except Exception as e:
                            st.error(f"❌ 诊断失败: {str(e)}")
                            st.code(traceback.format_exc())
                else:
                    st.warning("⚠️ 无法开始诊断：未检测到合法的待分析影像文件。")

        with c5:
            st.button(
                "数据分析中..." if "diag_result_path" in st.session_state else "📂 等待分析",
                disabled=True, use_container_width=True
            )

    st.markdown("--- ")

    # --- 4. 动态可视化与结果分发底座 ---
    if ("diag_result_path" in st.session_state and 
        "diag_case_name" in st.session_state and 
        "diag_task_name" in st.session_state):
        
        mask_path = st.session_state["diag_result_path"]
        active_case = st.session_state["diag_case_name"]
        active_task = st.session_state["diag_task_name"]
        raw_path = os.path.join(RAW_ROOT, active_case)

        if not os.path.exists(raw_path) or not os.path.exists(mask_path):
            st.info("💡 历史缓存文件已被清理，请重新点击“开始自动诊断”生成全新分析。")
            return

        raw_img = nib.load(raw_path)
        mask_img = nib.load(mask_path)
        raw_data = raw_img.get_fdata()
        mask_data = mask_img.get_fdata()

        zooms = raw_img.header.get_zooms()
        dx, dy = zooms[0], zooms[1]
        spacing_3d = zooms[:3] 

        task_mapping_reverse = {
            "海马体(hippocampus)": "hippocampus",
            "心脏(heart)": "heart",
            "前列腺(prostate)": "prostate",
            "脑肿瘤(brainTumour)": "brainTumour",
            "脾脏(spleen)": "spleen"
        }
        active_task_key = task_mapping_reverse.get(active_task, "brainTumour")

        if "cur_ai_reports" in st.session_state:
            ai_reports = st.session_state["cur_ai_reports"]
        else:
            ai_reports = diag_engine.ai_logic(mask_data, task_key=active_task_key, spacing=spacing_3d)

        view_left, view_right = st.columns([1, 1])

        with view_left:
            st.subheader("图像展示")

            coords = np.argwhere(mask_data > 0)
            if len(coords) > 0:
                z_slice = int(np.median(coords[:, 2]))
            else:
                z_slice = raw_data.shape[2] // 2

            raw_slice = raw_data[:, :, z_slice]
            mask_slice = mask_data[:, :, z_slice]

            raw_T = raw_slice.T
            mask_T = mask_slice.T

            fig = go.Figure()
            fig.add_trace(go.Heatmap(
                z=raw_T, colorscale='gray', showscale=False, x0=0, dx=dx, y0=0, dy=dy,
                hovertemplate='X: %{x:.2f} mm<br>Y: %{y:.2f} mm<br>Intensity: %{z:.0f}<extra></extra>',
                name='原始影像'
            ))

            if len(coords) > 0:
                masked = np.ma.masked_where(mask_T == 0, mask_T)
                fig.add_trace(go.Heatmap(
                    z=masked, colorscale='Jet', showscale=True, x0=0, dx=dx, y0=0, dy=dy, opacity=0.55,
                    hovertemplate='Label: %{z}<extra></extra>', name='分割区域',
                    colorbar=dict(title=dict(text='Label', font=dict(size=10)), tickfont=dict(size=9))
                ))

            fig.update_layout(
                xaxis_title='X (mm)', yaxis_title='Y (mm)',
                xaxis=dict(scaleanchor='y', scaleratio=1, constrain='domain'),
                yaxis=dict(constrain='domain'), width=600, height=600,
                margin=dict(l=10, r=10, t=30, b=10),
                template='plotly_dark' if theme == "Dark" else 'plotly_white', hovermode='closest'
            )
            st.plotly_chart(fig, use_container_width=False, config={'scrollZoom': True}, key="main_heatmap")

        with view_right:
            st.subheader("数据面板")
            st.markdown(f"**当前展示病例**: `{active_case}`")
            st.markdown(f"**当前展示任务**: `{active_task}`")
            st.markdown("---")
            # 提取渲染影像的真实三维空间分辨率 Spacing
            active_spacing = mask_img.header.get_zooms()[:3]
            # 传入真实的 active_spacing
            ai_reports = diag_engine.ai_logic(mask_data, task_key=active_task_key, spacing=active_spacing)

            for r in ai_reports:
                if "Warning" in r or "严重" in r: st.warning(r)
                elif "Healthy" in r or "成功" in r: st.success(r)
                else: st.info(r)

            report_date = datetime.date.today().strftime("%Y-%m-%d")

            pdf_data = generate_pdf_report(
                case_name=active_case,
                task_name=active_task,
                ai_reports=ai_reports,
                report_date=report_date
            )

            st.download_button(
                label="📥 导出临床诊断报告 (PDF)",
                data=pdf_data,
                file_name=f"AI_Report_{active_case.split('.')[0]}.pdf",
                mime="application/pdf",
                use_container_width=True,
                key="pdf_download_button"
            )
    else:
        st.info("💡 请在上方控制栏选择待分析病例与对应临床任务，随后点击“开始自动诊断”激活推理引擎。")
