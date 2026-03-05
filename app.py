import streamlit as st
import google.generativeai as genai
from google.generativeai.types import RequestOptions # 이 줄을 추가합니다.
import tempfile
import os
import datetime

st.set_page_config(page_title="회의록 생성봇 노썬", layout="wide")
st.title("🎤 끝내주는 노썬 회의록 작성 봇")

# 0. 세션 상태 (Session State) 초기화: 회의록 누적 저장용
if "meeting_minutes" not in st.session_state:
    st.session_state.meeting_minutes = []

# 새 창(모달) 띄우기 함수 정의 (Streamlit 1.34 이상 지원)
@st.dialog("📋 넓은 화면으로 보기", width="large")
def show_large_minute(title, text, clean_text):
    st.subheader(title)
    st.markdown("---")
    st.markdown(text)
    st.markdown("---")
    st.markdown("**📋 슬랙 / 원노트에 복사하기** (아래 박스 클릭 후 Ctrl+A, Ctrl+C)")
    st.text_area("복사용 텍스트 (모달)", value=clean_text, height=300, label_visibility="collapsed")

# 1. 사이드바 설정 (API 키 입력 포함)
st.sidebar.header("설정")
user_api_key = st.sidebar.text_input("🔑 나만의 API 키 입력 (선택)", type="password", help="발급받은 구글 Gemini API 키가 있다면 입력해 제한 없이 사용하세요.")
format_selection = st.sidebar.selectbox("회의록 양식 선택", ["양식 1: 상세 개발 회의록", "양식 2: 핵심 요약", "양식 3: 전체 대화 기록 (무편집본)"])

st.sidebar.markdown("---")
st.sidebar.markdown("**ℹ️ 앱 정보**")
st.sidebar.caption("- **제작자:** ssun@madngine.com\n- **개발 지원 -노선영\n- **버전:** v1.1.0")

# 2. 기본/사용자 API 키 설정 및 환경 구성
try:
    # API 키처럼 보이는 문자열인지 대략적인 정규식 검사 또는 길이 검사
    if user_api_key and len(user_api_key.strip()) < 100 and user_api_key.startswith("AIza"):
        # 사용자가 올바른 형태의 키를 입력했을 경우
        genai.configure(api_key=user_api_key.strip())
        st.sidebar.success("✅ 사용자 API 키 적용 완료")
    else:
        # 내역이 없거나(비어있음) 잘못된 문자열을 복붙한 경우 기본 키로 롤백
        if user_api_key:
            st.sidebar.warning("⚠️ 입력하신 값이 올바른 구글 API 키 형식이 아닌 것 같습니다. (AIza로 시작해야 합니다.)\n기본 내장 키로 전환합니다.")
        MY_KEY = "AIzaSyA-nTcfCLLqneoN5F0LsZwZHACWnwKM7pY"
        genai.configure(api_key=MY_KEY)
except Exception as e:
    st.error(f"API 키 설정 오류: {e}")

# 3. 모델 설정
try:
    # 사용 가능한 최신 모델로 변경합니다 (이전 버전을 사용하면 404 에러 발생 가능)
    model = genai.GenerativeModel('gemini-2.5-flash')
except Exception as e:
    st.error(f"모델 설정 오류: {e}")

# 4. 파일 업로드
uploaded_file = st.file_uploader("회의 음성 파일 업로드 (mp3, wav, m4a)", type=['mp3', 'wav', 'm4a'])

if uploaded_file is not None:
    st.audio(uploaded_file)
    
    # 모델 선택 및 생성 버튼 (양식에 따라 동적 렌더링)
    button_clicked = False
    selected_model_name = ""
    
    st.markdown("---")
    if format_selection == "양식 1: 상세 개발 회의록":
        st.write("사용할 AI 모델을 선택하세요:")
        col1, col2, col3 = st.columns(3) # 컬럼을 3개로 나눕니다.
        with col1:
            if st.button("고품질(Pro) ✨", use_container_width=True, help="가장 똑똑하지만 생성이 느리고 무료 횟수 제한이 빡빡합니다."):
                button_clicked = True
                selected_model_name = 'gemini-2.5-pro'
        with col2:
            if st.button("고속(Flash) ⚡", use_container_width=True, help="속도와 품질의 밸런스가 좋습니다."):
                button_clicked = True
                selected_model_name = 'gemini-2.5-flash'
        with col3:
            if st.button("초절전(Lite) 🍃", use_container_width=True, help="가장 가볍고 빠르며 Quota 제한에 덜 걸립니다."):
                button_clicked = True
                selected_model_name = 'gemini-2.5-flash-lite'
    elif format_selection == "양식 2: 핵심 요약":
        st.write("사용할 AI 모델을 선택하세요:")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("핵심 요약(Flash) ⚡", use_container_width=True):
                button_clicked = True
                selected_model_name = 'gemini-2.5-flash' 
        with col2:
            if st.button("핵심 요약(Lite) 🍃", use_container_width=True):
                button_clicked = True
                selected_model_name = 'gemini-2.5-flash-lite' 
    else: # 양식 3: 전체 대화 기록
        st.write("사용할 AI 모델을 선택하세요:")
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("전체 기록(Pro) ✨", use_container_width=True, help="가장 똑똑하지만 생성이 느리고 무료 횟수 제한이 빡빡합니다."):
                button_clicked = True
                selected_model_name = 'gemini-2.5-pro'
        with col2:
            if st.button("전체 기록(Flash) ⚡", use_container_width=True, help="속도와 품질의 밸런스가 좋습니다."):
                button_clicked = True
                selected_model_name = 'gemini-2.5-flash'
        with col3:
            if st.button("전체 기록(Lite) 🍃", use_container_width=True, help="가장 가볍고 빠르며 Quota 제한에 덜 걸립니다."):
                button_clicked = True
                selected_model_name = 'gemini-2.5-flash-lite' 

    if button_clicked:
        import time
        import threading
        
        # 롤링 텍스트를 보여줄 컨테이너 생성
        status_placeholder = st.empty()
        
        # 애니메이션이 진행 중인지 체크할 플래그 리스트 (쓰레드 간 공유용)
        is_generating = [True]
        
        # 롤링 텍스트 목록 (점점 힘들어지는 노썬봇)
        loading_messages = [
            "노썬봇이 노트북 펼치는 중 💻...",
            "노썬봇이 회의록 상황 파악중 🤔...",
            "노썬봇이 회의록을 적다 지우는 중 📝...",
            "노썬봇: 무슨 말인지 모르겠는 중.. 😵‍💫...",
            "노썬봇: 대충 어떻게든 써보는 중 🫠...",
            "노썬봇이 마지막 영혼을 끌어모으는 중 👻..."
        ]

        def update_loading_message():
            # 텍스트가 순차적으로 나오도록 텀을 둡니다. (예: 4~5초 간격)
            idx = 0
            while is_generating[0]:
                msg = loading_messages[idx % len(loading_messages)]
                # spinner 룩앤필을 활용하기 위해 empty 안에 다시 spinner 할당
                with status_placeholder:
                    with st.spinner(msg):
                        time.sleep(3)
                idx += 1
                if idx >= len(loading_messages):
                    idx = len(loading_messages) - 1 # 마지막 메시지에 고정

        # 백그라운드 텍스트 체인저 실행
        loading_thread = threading.Thread(target=update_loading_message)
        # Streamlit 클라우드 환경 등 컨텍스트 문제 방지를 위해 간단한 우회나 st.add_script_run_ctx 지원 필요하지만,
        # 가장 안전한 st.status 방식 또는 직접 while문을 돌리는 방식 중
        # 멀티쓰레딩이 복잡하면 Streamlit 특성상 에러가 나기 쉬우므로 제너레이터 방식을 사용.
        # ----> 하지만 제미나이 생성은 블로킹 함수. 
        # 그러므로 여기서는 add_script_run_ctx를 씁니다.
        from streamlit.runtime.scriptrunner import add_script_run_ctx
        add_script_run_ctx(loading_thread)
        loading_thread.start()
        
        try:
                # 선택된 모델로 재설정 (일관성을 위해 temperature 속성을 낮게 설정)
                model = genai.GenerativeModel(
                    model_name=selected_model_name,
                    generation_config={"temperature": 0.2} # 0에 가까울수록 매번 일정한 결과 출력
                )
                
                # 5. 임시 파일 저장
                with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name

                # 6. 음성 파일 업로드 (Gemini 서버로 전달 시 한글 이름 에러를 방지하기 위해 display_name 지정)
                audio_file = audio_file = genai.upload_file(path=tmp_path, display_name="uploaded_audio_file")
                
                # 7. 프롬프트 설정 (여기서 'prompt'를 확실히 정의합니다!)
                if format_selection == "양식 1: 상세 개발 회의록":
                    prompt = """
당신은 전문적이고 꼼꼼한 IT 프로젝트 회의록 작성 AI입니다. 
제공된 오디오 파일을 듣고, 단순히 발언 내용을 나열하지 말고 **실제 회사에서 작성하는 형식의 회의록**처럼 핵심을 짚어 대화 요약 형식으로 작성해주세요.

**[작성 지침]**
1. **전체 맥락 파악:** 회의의 가장 중요한 핵심 안건과 방향성을 '전체 회의 주제 및 흐름' 항목에 먼저 요약하세요.
2. **주제별 대화 요약 형식:** 논의 내용을 부서별로 억지로 나누지 말고, **'실제 논의된 안건/주제'** 단위로 묶어주세요. 각 주제 안에서 "**[기획]이 이런 의견을 제시함 -> [개발]이 이에 대해 피드백을 줌 -> [결론] 이렇게 하기로 함**" 과 같이 부서/참석자 간의 티키타카(흐름)가 보이도록 요약하세요.
3. **양식 엄수:** 반드시 아래 [출력 마크다운 양식]의 뼈대를 100% 동일하게 유지하여 작성하세요. (단, '주제 1', '주제 2' 등의 제목은 실제 회의에서 다뤄진 구체적인 안건 이름으로 변경해서 작성할 것)
4. **날짜 유추 금지:** 오디오에서 날짜와년도가 명확하게 언급되지 않는 한, '일시' 항목에는 '미상'으로 기재하세요.

**[출력 마크다운 양식]** (이 줄 아래로 회의록 본문 시작. 양식의 뼈대를 변경하지 마세요)

## ◆ 회의 개요
- **일시:** (오디오에서 파악할 수 있는 경우 기재, 모르면 '미상')
- **참석자:** (파악 가능한 참석자/직급 기재)
- **주제:** (전체 회의의 핵심 주제 1줄 요약)

## ◆ 전체 회의 주제 및 흐름
- (여기에 전체 회의의 맥락, 배경, 그리고 가장 중요하게 다뤄진 안건이 무엇인지 2~3줄로 요약)

## ◆ 주요 안건별 논의 내용
### 1. (논의된 주제/안건 이름 작성)
- (대화 내용 요약: 예) **[기획]** ~제안 -> **[UI]** ~우려 표함 -> **[결론]** ~방향으로 확정)
- (추가 논의 내용...)

### 2. (논의된 주제/안건 이름 작성)
- (대화 내용 요약: 예) **[프로그램]** ~이슈 공유 -> **[PM]** ~요청 -> **[결론]** ~결정됨)
- (추가 논의 내용...)

(※ 안건 개수에 따라 3, 4... 추가 가능)

## ◆ 이슈 공유 후 결정된 사항
- (확정된 정책, 다음 할 일(To-Do), 변경 사항 등 구체적으로 기재)
- (결정된 사항이 없다면 '특별한 결정 사항 또는 이슈 없음'으로 기재)

## ◆ PM을 위한 핵심 챙김망 (Action Items)
- **[담당자/부서]** (해야 할 일 요약) / **기한:** (언급된 일정이나 다급도) / **리스크:** (예상되는 병목이나 문제점)
- **[담당자/부서]** (해야 할 일 요약) / **기한:** (언급된 일정이나 다급도) / **리스크:** (예상되는 병목이나 문제점)
"""
                elif format_selection == "양식 2: 핵심 요약":
                    prompt = """
당신은 회의 요약 AI입니다.
회의 내용을 듣고, 군더더기 없이 아래 양식에 맞춰서만 정확히 작성해주세요.

### 📝 핵심 요약
- (전체 내용을 3줄 이하로 요약)

### 🎯 중요 결정 사항
1. (가장 중요한 결정 사항이나 To-Do)
2. (두 번째로 중요한 결정 사항)
3. (세 번째로 중요한 사항, 없으면 생략)

### 🚨 PM을 위한 핵심 챙김망 (Action Items)
- **[담당자/부서]** (해야 할 일 요약) / **기한:** (언급된 일정이나 다급도) / **리스크:** (예상되는 병목이나 문제점)
- **[담당자/부서]** (해야 할 일 요약) / **기한:** (언급된 일정이나 다급도) / **리스크:** (예상되는 병목이나 문제점)
"""
                else: # 양식 3: 전체 대화 기록
                    prompt = """
당신은 회의 녹음을 듣고 모든 대화 내용을 빠짐없이 기록하는 전문 속기사 AI입니다.
주관적인 요약, 판단, 생략을 절대 하지 말고 들리는 모든 대화 내용을 시간 흐름에 따라 화자(발언자)별로 모조리 다 적어주세요.

**[작성 지침]**
1. **생략 금지:** 사소한 대화나 농담, 인사말 등을 포함하여 회의록 양식에 맞춰 최대한 모든 발언을 기록하세요.
2. **양식 엄수:** 반드시 아래 [출력 마크다운 양식]의 뼈대를 100% 동일하게 유지하여 작성하세요.
3. **날짜 유추 금지:** 오디오에서 날짜와 년도가 명확하게 언급되지 않는 한, '일시' 항목에는 '미상'으로 기재하세요.

**[출력 마크다운 양식]** (이 줄 아래로 회의록 본문 시작. 양식의 뼈대를 변경하지 마세요)

## ◆ 회의 개요
- **일시:** (오디오에서 파악할 수 있는 경우 기재, 모르면 '미상')
- **참석자:** (파악 가능한 참석자 전원 기재)
- **주제:** (전체 회의의 핵심 주제 1줄 요약)

## ◆ 전체 회의 스크립트 (무편집본)
- **[화자 A]** (발언 내용 전체 기록)
- **[화자 B]** (발언 내용 전체 기록)
- **[화자 A]** (발언 내용 전체 기록)
(위 형식으로 짧은 리액션을 제외한 모든 발언을 대본처럼 끝까지 기록)

## ◆ PM을 위한 핵심 챙김망 (Action Items)
- **[담당자/부서]** (해야 할 일 요약) / **기한:** (언급된 일정이나 다급도) / **리스크:** (예상되는 병목이나 문제점)
- (무편집본이라도 향후 업무를 위해 결정된 액션 아이템은 마지막에 3가지 이내로 요약해 주세요. 없으면 생략)
"""

                # 8. 결과 생성
                response = model.generate_content([prompt, audio_file])
                
                # 9. 세션 상태에 생성된 회의록 추가
                now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                st.session_state.meeting_minutes.append({
                    "original_name": uploaded_file.name,
                    "model": selected_model_name,
                    "format": format_selection,
                    "text": response.text,
                    "created_at": now_str,
                    "upload_name": getattr(audio_file, "name", None)
                })
                st.success(f"회의록 작성이 완료되었습니다! (사용 모델: {selected_model_name})")
                
                # 임시 파일 삭제
                os.remove(tmp_path)
                
        except Exception as e:
            error_msg = str(e)
            # 429 Quota 에러가 발생할 경우를 위한 안내 (주로 Pro 모델 무료 한도 초과 시 발생)
            if "429" in error_msg or "Quota exceeded" in error_msg:
                st.error("❌ 선택하신 AI 모델의 무료 제공량(Quota)을 초과했습니다.")
                st.info("💡 **해결 방법:** 당분간은 **'초절전(Lite) 🍃' 버튼**을 사용하시거나, 왼쪽 사이드바에 본인의 구글 API 키를 발급받아 등록해 보세요.")
            # 404 에러가 다시 발생할 경우를 위한 안내
            elif "404" in error_msg:
                st.error("오류가 발생했습니다 (404).")
                st.info("CMD창에서 'python -m pip install -U google-generativeai'를 실행한 뒤, 앱을 껐다 켜보세요.")
            else:
                st.error(f"분석 중 오류가 발생했습니다: {e}")
        finally:
            # 쓰레드 종료 신호
            is_generating[0] = False
            # 쓰레드가 종료될 때까지 대기 (UI 업데이트 겹침 방지)
            loading_thread.join()
            # 완료되면 빈 공간으로 롤링 텍스트 영역 제거 
            status_placeholder.empty()

# 화면에 세션 상태에 저장된 모든 회의록을 누적해서 렌더링
if st.session_state.meeting_minutes:
    st.markdown("---")
    st.subheader("📚 누적된 회의록 목록")
    
    # 최신 회의록이 맨 위에 오도록 역순으로 출력 (원하지 않으면 st.session_state.meeting_minutes 그대로 렌더링 가능)
    for idx, minute in enumerate(reversed(st.session_state.meeting_minutes)):
        # 최근 추가된 회의록은 스피너가 기본으로 열려있고, 나머지는 닫혀있도록 설정
        is_latest = (idx == 0)
        
        # 파일 이름에서 확장자 제외
        safe_name = minute["original_name"].rsplit('.', 1)[0]
        
        # 생성 시간 가져오기 (이전에 생성된 회의록은 없을 수 있으므로 get 사용)
        created_time = minute.get("created_at", "")
        time_str = f" [{created_time}]" if created_time else ""
        
        expander_title = f"{safe_name} ({minute['format']} / {minute['model']}){time_str}"
        
        with st.expander(expander_title, expanded=is_latest):
            # 1. 회의록 원본 출력 (스크롤바가 생기도록 컨테이너 크기 고정)
            with st.container(height=400):
                st.markdown(minute["text"])
            
            # 2. 복사용 텍스트를 미리 생성 (다운로드/모달 등을 위해 먼저 연산)
            clean_text = minute["text"]
            for bad_str in ["**", "## ", "### ", "#### "]:
                clean_text = clean_text.replace(bad_str, "")
                
            # 3. 버튼 배치 (한 줄 당 2개씩)
            st.markdown("<br>", unsafe_allow_html=True) # 약간의 여백
            col1, col2 = st.columns(2)
            with col1:
                # 다운로드 버튼
                download_file_name = f"{safe_name}_회의록.txt"
                st.download_button(
                    label="💾 텍스트 파일로 다운로드",
                    data=minute["text"],
                    file_name=download_file_name,
                    mime="text/plain",
                    # key 속성에 index를 포함하여 각 버튼을 고유하게 만듦
                    key=f"dl_btn_{idx}"
                )
            with col2:
                # 넓은 화면(모달 창)으로 열기 버튼
                if st.button("🖥️ 넓은 창(새 창)에서 보기", key=f"popup_btn_{idx}"):
                    show_large_minute(expander_title, minute["text"], clean_text)
                    
            # 4. 슬랙/원노트용 복사 기능 (마크다운 포맷 유지) - Expander 안쪽
            st.markdown("---")
            st.markdown("**📋 슬랙 / 원노트에 복사하기 (아래 박스를 클릭 후 Ctrl+A, Ctrl+C로 복사하세요)**")
            
            # 마우스 드래그 대신 편하게 스크롤 및 전체 복사가 가능하도록 text_area로 변경
            st.text_area("복사용 텍스트", value=clean_text, height=300, label_visibility="collapsed", key=f"copy_ta_{idx}")
            
            # 4. 음성 타임라인 Q&A (추가된 기능)
            upload_name = minute.get("upload_name")
            if upload_name:
                st.markdown("---")
                st.markdown("💬 **음성 타임라인 질문하기**")
                
                # Q&A 기록을 세션에 개별적으로 저장하기 위한 공간 확보
                qa_key = f"qa_history_{idx}"
                if qa_key not in st.session_state:
                    st.session_state[qa_key] = []
                    
                # 기존 질문/답변 내역 출력
                for qa in st.session_state[qa_key]:
                    st.info(f"👤 **질문:** {qa['q']}\n\n🤖 **답변:** {qa['a']}")
                
                # 새 질문 입력 폼
                with st.form(key=f"qa_form_{idx}"):
                    user_q = st.text_input("궁금한 점이나 몇 분 몇 초에 언급되었는지 물어보세요.", placeholder="예: 프로젝트 B 배포일에 대해 언제 언급됐어?")
                    submit_q = st.form_submit_button("질문하기")
                    
                    if submit_q and user_q:
                        with st.spinner("노썬봇이 음성 기록을 다시 뒤적이는 중.. 🎧"):
                            try:
                                qa_model = genai.GenerativeModel('gemini-2.5-flash')
                                old_audio = genai.get_file(upload_name)
                                
                                qa_prompt = f"""
당신은 위 회의록의 바탕이 된 원본 오디오에 대해 답변하는 도우미입니다.
사용자 질문: "{user_q}"

이 대화가 오디오의 '몇 분 몇 초(타임스탬프)' 쯤에서 언급되었는지 반드시 포함하여 답해주세요.
(예시: "해당 내용은 오디오 약 12분 30초 경에 A참석자가 발언했습니다.")
"""
                                qa_response = qa_model.generate_content([qa_prompt, old_audio])
                                st.session_state[qa_key].append({"q": user_q, "a": qa_response.text})
                                st.rerun() # 화면 즉시 갱신
                            except Exception as e:
                                st.error(f"질문 처리 중 오류 발생: {e}")